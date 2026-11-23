"""Jobsite Intelligence API — superintendent day (UC tables, as the selected identity) + Jobsite agent (optional photo)."""
from __future__ import annotations

import base64
import io
import re
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import jobsite_agent
from .auth import IS_DATABRICKS_APP, _local_client, user_client
from .followups import _actor
from .risk import _sql, cached, sql_many

router = APIRouter(prefix="/api/jobsite")
PID = re.compile(r"^P-\d{4}$")
PHOTO_VOLUME = "/Volumes/bhambs/construction_control_tower/field_photos"
MAX_PHOTO_BYTES = 4_500_000


def _pid(pid: str) -> str:
    if not PID.match(pid):
        raise HTTPException(400, "bad project id")
    return pid


@router.get("/day")
def day(project_id: str, request: Request):
    pid = _pid(project_id)
    return cached(request, ("jobsite-day", pid), lambda: _day(pid, request))


def _day(pid: str, request: Request) -> dict:
    w = user_client(request)
    q = sql_many(w, {
        "d": f"SELECT * FROM jobsite_day WHERE project_id = '{pid}'",
        "look": f"SELECT * FROM jobsite_lookahead WHERE project_id = '{pid}' ORDER BY seq",
        "crews": f"SELECT trade, company, planned, actual_yesterday FROM jobsite_crews WHERE project_id = '{pid}'",
        "events": f"SELECT time, kind, description FROM jobsite_events WHERE project_id = '{pid}' ORDER BY time",
    })
    d, look, crews, events = q["d"], q["look"], q["crews"], q["events"]
    if not d:
        raise HTTPException(403, "You don't have access to this project.")
    b = lambda v: str(v).lower() == "true"  # noqa: E731
    acts = [{
        "id": a["lookahead_id"], "name": a["activity"], "trade": a["trade"], "area": a["area"], "when": a["when_label"], "hazard": a["hazard"],
        "standard": a["standard"], "permit": a["permit"], "level": a["risk_level"],
        "checks": [{"label": lbl, "ok": b(a[f"{k}_ok"]), "detail": a[f"{k}_detail"], "owner": a.get(f"{k}_owner"), "neededBy": a.get(f"{k}_needed_by")}
                   for lbl, k in (("Info", "info"), ("Approvals", "approvals"), ("Materials", "materials"), ("Float", "float"))],
    } for a in look]
    x = d[0]
    return {"phase": x["phase"], "superintendent": x["superintendent"], "weather": x["weather"],
            "nearMisses": {"count": int(x["near_miss_count_14d"]), "theme": x["near_miss_theme"]}, "activities": acts,
            "crews": [{"trade": c["trade"], "company": c["company"], "planned": int(c["planned"]), "yesterday": int(c["actual_yesterday"])} for c in crews],
            "events": [{"time": e["time"], "what": e["description"], "kind": e["kind"]} for e in events]}


class AskIn(BaseModel):
    project_id: str
    question: str = Field(min_length=2, max_length=600)
    photo_data_url: Optional[str] = None


def _save_photo(pid: str, data_url: str) -> str:
    m = re.match(r"^data:image/(png|jpeg);base64,(.+)$", data_url, re.S)
    if not m:
        raise HTTPException(400, "Photo must be PNG or JPEG.")
    raw = base64.b64decode(m.group(2))
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "Photo too large (max ~4.5 MB).")
    path = f"{PHOTO_VOLUME}/{pid}/{time.strftime('%Y%m%d-%H%M%S')}.{'jpg' if m.group(1) == 'jpeg' else 'png'}"
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient() if IS_DATABRICKS_APP else _local_client()
    w.files.upload(path, io.BytesIO(raw), overwrite=True)
    return path


@router.post("/ask")
def ask(body: AskIn, request: Request):
    pid = _pid(body.project_id)
    w = user_client(request)
    p = _sql(w, f"SELECT project_id, name, market_sector, region, pct_complete FROM projects WHERE project_id = '{pid}'")
    if not p:
        raise HTTPException(403, "You don't have access to this project.")
    photo_path = _save_photo(pid, body.photo_data_url) if body.photo_data_url else None
    actor, _ = _actor(request)
    try:
        r = jobsite_agent.ask(p[0], body.question, w, actor, body.photo_data_url)
    except Exception as e:
        raise HTTPException(502, f"Jobsite agent error: {e}") from e
    return {**r, "photo_path": photo_path}
