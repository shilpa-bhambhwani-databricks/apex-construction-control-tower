"""Risk Radar data API — reads the UC metric view `project_risk_mv` AS THE SELECTED IDENTITY,
so Unity Catalog row filters decide which projects come back (no filtering in app code)."""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from fastapi import APIRouter, HTTPException, Request

from .auth import persona_of, user_client

router = APIRouter(prefix="/api/risk")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "df23f63620c4cbbf")
CATALOG, SCHEMA = os.environ.get("CT_CATALOG", "bhambs"), os.environ.get("CT_SCHEMA", "construction_control_tower")
CACHE_TTL = int(os.environ.get("CT_CACHE_TTL", "300"))   # synthetic data is static — 5 min per identity is safe
_cache: dict[tuple, tuple[float, object]] = {}
_pool = ThreadPoolExecutor(16)
_locks: dict[tuple, threading.Lock] = {}
_locks_guard = threading.Lock()

SIGNALS = ["rfi", "co", "submittal", "schedule", "cost", "safety"]


def _sql(w: WorkspaceClient, stmt: str) -> list[dict]:
    r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=WAREHOUSE_ID, catalog=CATALOG, schema=SCHEMA, wait_timeout="50s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(0.5)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise HTTPException(502, f"SQL failed: {r.status.error.message if r.status.error else r.status.state}")
    cols = [c.name for c in r.manifest.schema.columns]
    return [dict(zip(cols, row)) for row in (r.result.data_array or [])] if r.result else []


def sql_many(w: WorkspaceClient, queries: dict[str, str]) -> dict[str, list[dict]]:
    """Run independent statements in parallel — each endpoint waits for its slowest query, not the sum."""
    futs = {k: _pool.submit(_sql, w, q) for k, q in queries.items()}
    return {k: f.result() for k, f in futs.items()}


def identity_key(request: Request) -> tuple:
    """Cache key part: WHO is asking (row filters differ per identity)."""
    return (persona_of(request), request.headers.get("x-forwarded-email"))


def cached(request: Request, key: tuple, fn):
    """Per-identity TTL cache for read-only UC queries. Errors are never cached."""
    k = identity_key(request) + key
    hit = _cache.get(k)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    with _locks_guard:
        lock = _locks.setdefault(k, threading.Lock())
    with lock:  # single-flight: concurrent misses for the same key share one set of queries
        hit = _cache.get(k)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
        val = fn()
        _cache[k] = (time.time(), val)
        return val


def _plain(signal: str, raw: float) -> str:
    """Same plain-language wording the Genie Agent uses."""
    return {
        "rfi": f"{int(raw)} RFIs > 21 days",
        "co": f"${raw / 1e6:.1f}M pending COs",
        "submittal": f"{int(raw)} overdue submittals",
        "schedule": f"{raw:.1f} days critical-path float",
        "cost": f"EAC {raw * 100:.1f}% over budget",
        "safety": f"{int(raw)} safety obs. (14 d)",
    }[signal]


@router.get("/projects")
def projects(request: Request):
    return cached(request, ("risk-projects",), lambda: _projects(request))


def _projects(request: Request) -> dict:
    persona = persona_of(request)
    w = user_client(request)
    queries = {
        "signals": "SELECT project_id, signal, MEASURE(signal_sub_score) AS sub, MEASURE(signal_raw_value) AS raw, MEASURE(risk_score) AS pts "
                   "FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL",
        "trend": "SELECT project_id, weeks_ago, MEASURE(risk_score) AS score FROM project_risk_mv WHERE weeks_ago <= 8 GROUP BY ALL",
        "projects": "SELECT project_id, name, market_sector, region, contract_value, pct_complete FROM projects",
    }
    res = sql_many(w, queries)

    out: dict[str, dict] = {}
    for p in res["projects"]:
        out[p["project_id"]] = dict(id=p["project_id"], name=p["name"], sector=p["market_sector"], region=p["region"],
                                    contractValueM=round(float(p["contract_value"]) / 1e6), pctComplete=int(p["pct_complete"]),
                                    signals={}, contributions={}, raw={}, trend=[0.0] * 9, headline="", pendingCoUsd=0.0)
    for s in res["signals"]:
        o = out.get(s["project_id"])
        if not o:
            continue
        o["signals"][s["signal"]] = round(float(s["sub"]))
        o["contributions"][s["signal"]] = float(s["pts"])
        o["raw"][s["signal"]] = float(s["raw"])
        if s["signal"] == "co":
            o["pendingCoUsd"] = float(s["raw"])
    for t in res["trend"]:
        o = out.get(t["project_id"])
        if o:
            o["trend"][8 - int(t["weeks_ago"])] = round(float(t["score"]), 1)  # oldest → newest
    for o in out.values():
        top = sorted(o["contributions"].items(), key=lambda kv: kv[1], reverse=True)[:2]
        o["headline"] = " · ".join(_plain(k, o["raw"][k]) for k, _ in top)
        o["score"] = round(sum(o["contributions"].values()))
        o.pop("contributions"), o.pop("raw")

    return {"persona": persona, "as_of": "2026-11-09", "projects": sorted(out.values(), key=lambda o: -o["score"])}
