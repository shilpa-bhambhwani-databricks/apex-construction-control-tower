"""Resolve tab API: backlog + item detail (UC, as the selected identity), agent Q&A (MLflow-traced), decisions (Lakebase)."""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import resolve_agent
from .db import pool
from .followups import _actor, _visible_projects
from .risk import _sql, cached, sql_many
from .auth import user_client

router = APIRouter(prefix="/api/resolve")
ID_RE = re.compile(r"^(CO|RFI)-\d{4}$")
PID_RE = re.compile(r"^P-\d{4}$")


def _check_pid(pid: str):
    if not PID_RE.match(pid):
        raise HTTPException(400, "bad project id")


@router.get("/backlog")
def backlog(project_id: str, request: Request):
    _check_pid(project_id)
    return cached(request, ("resolve-backlog", project_id), lambda: _backlog(project_id, request))


def _backlog(project_id: str, request: Request) -> dict:
    w = user_client(request)
    q = sql_many(w, {"cos": f"""SELECT co_id AS id, 'CO' AS kind, description AS title, subcontractor, cost_code, status, amount_requested, submitted_date,
                         datediff(DATE'2026-11-09', submitted_date) AS days_pending
                       FROM change_orders WHERE project_id = '{project_id}' AND decision_date IS NULL ORDER BY amount_requested DESC LIMIT 8""",
                     "rfis": f"""SELECT rfi_id AS id, 'RFI' AS kind, subject AS title, discipline, status, created_date, due_date, ball_in_court,
                          datediff(DATE'2026-11-09', created_date) AS days_open, cost_impact_flag, schedule_impact_flag
                        FROM rfis WHERE project_id = '{project_id}' AND status = 'Open' AND created_date < DATE'2026-11-09' - INTERVAL 21 DAYS
                        ORDER BY (rfi_id IN ('RFI-0387','RFI-0391','RFI-0352')) DESC, created_date LIMIT 8"""})
    return {"project_id": project_id, "items": q["cos"] + q["rfis"]}


@router.get("/item")
def item(project_id: str, item_id: str, request: Request):
    _check_pid(project_id)
    if not ID_RE.match(item_id):
        raise HTTPException(400, "bad item id")
    return cached(request, ("resolve-item", project_id, item_id), lambda: _item(project_id, item_id, request))


def _item(project_id: str, item_id: str, request: Request) -> dict:
    w = user_client(request)
    qs = {"p": f"SELECT project_id, name, region FROM projects WHERE project_id = '{project_id}'",
          "floats": f"SELECT critical_path_float_days FROM schedule_float_weekly WHERE project_id = '{project_id}' AND week = DATE'2026-11-09'"}
    if item_id.startswith("CO"):
        qs["lines"] = f"SELECT * FROM get_change_order('{item_id}')"
        qs["cost"] = f"""SELECT ROUND(100 * (SUM(eac) - SUM(budget)) / SUM(budget), 1) AS overrun_pct FROM job_cost
                         WHERE project_id = '{project_id}' AND cost_code = (SELECT cost_code FROM change_orders WHERE co_id = '{item_id}' LIMIT 1)
                           AND period = (SELECT MAX(period) FROM job_cost WHERE project_id = '{project_id}')"""
    else:
        qs["rfi"] = f"""SELECT r.*, s.activity_name, s.planned_start, s.total_float_days, s.critical_flag FROM rfis r
                    LEFT JOIN schedule_activities s ON s.activity_id = r.activity_id WHERE r.rfi_id = '{item_id}' AND r.project_id = '{project_id}'"""
    q = sql_many(w, qs)
    p, floats = q["p"], q["floats"]
    if not p:
        raise HTTPException(403, "You don't have access to this project.")
    ctx = []
    if floats:
        ctx.append({"label": "Schedule", "value": f"{float(floats[0]['critical_path_float_days']):.1f} days of critical-path float left", "source": "P6"})
    if item_id.startswith("CO"):
        lines = q["lines"]
        if not lines:
            raise HTTPException(404, "Change order not found or not visible.")
        h = lines[0]
        cost = q["cost"]
        if cost and cost[0]["overrun_pct"] is not None:
            ctx.append({"label": "Budget", "value": f"{h['cost_code']} EAC already {cost[0]['overrun_pct']}% over budget", "source": "SAP"})
        if item_id == "CO-0142":
            ctx.append({"label": "Daily log", "value": "Rock first noted Oct 11 (17 days before COR)", "source": "Procore"})
        return {"id": item_id, "kind": "CO", "project": p[0], "header": {k: h[k] for k in ("co_id", "subcontractor", "cost_code", "description", "status", "amount_requested", "submitted_date")},
                "lines": [{k: l[k] for k in ("line", "item_desc", "unit", "quantity", "unit_rate", "line_amount")} for l in lines if l.get("line")], "context": ctx}
    r = q["rfi"]
    if not r:
        raise HTTPException(404, "RFI not found or not visible.")
    if r[0].get("activity_name"):
        ctx.append({"label": "Blocks", "value": f"{r[0]['activity_name']} starting {r[0]['planned_start']} ({r[0]['total_float_days']} d float)", "source": "P6"})
    return {"id": item_id, "kind": "RFI", "project": p[0], "header": {k: r[0].get(k) for k in ("rfi_id", "subject", "discipline", "status", "created_date", "due_date", "ball_in_court", "cost_impact_flag", "schedule_impact_flag")},
            "lines": [], "context": ctx}


class AskIn(BaseModel):
    project_id: str
    item_id: str
    question: str = Field(min_length=3, max_length=600)


@router.post("/ask")
def ask(body: AskIn, request: Request):
    detail = item(body.project_id, body.item_id, request)  # also enforces visibility as this identity
    actor, _ = _actor(request)
    summary = {"id": detail["id"], "kind": detail["kind"], "project": detail["project"], **detail["header"]}
    try:
        return resolve_agent.ask(summary, body.question, user_client(request), actor)
    except Exception as e:
        raise HTTPException(502, f"Resolve agent error: {e}") from e


class DecisionIn(BaseModel):
    project_id: str
    item_id: str
    decision: str = Field(pattern=r"^(Negotiate|Recommend approval|Reject|Assign follow-up|Draft response)$")
    rationale: Optional[str] = Field(default=None, max_length=1500)
    trace_id: Optional[str] = None


DDL = """CREATE TABLE IF NOT EXISTS control_tower.decisions (
  id BIGSERIAL PRIMARY KEY, project_id TEXT NOT NULL, item_id TEXT NOT NULL, decision TEXT NOT NULL, rationale TEXT,
  decided_by TEXT NOT NULL, trace_id TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"""


@router.post("/decisions")
def decide(body: DecisionIn, request: Request):
    if body.project_id not in _visible_projects(request):
        raise HTTPException(403, "You don't have access to this project.")
    actor, _ = _actor(request)
    with pool().connection() as conn:
        did = conn.execute("INSERT INTO control_tower.decisions (project_id, item_id, decision, rationale, decided_by, trace_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                           (body.project_id, body.item_id, body.decision, body.rationale, actor, body.trace_id)).fetchone()[0]
        conn.commit()
    return {"id": did, "decision": body.decision, "decided_by": actor}


@router.get("/decisions")
def decisions(project_id: str, request: Request):
    if project_id not in _visible_projects(request):
        return []
    with pool().connection() as conn:
        rows = conn.execute("SELECT id, item_id, decision, rationale, decided_by, trace_id, created_at FROM control_tower.decisions WHERE project_id = %s ORDER BY created_at DESC LIMIT 50", (project_id,)).fetchall()
    return [dict(zip(["id", "item_id", "decision", "rationale", "decided_by", "trace_id", "created_at"], r)) for r in rows]
