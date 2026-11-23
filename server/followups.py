"""Assign follow-up & notify — the first real ACTION (agent action level 2: act inside Control Tower).

Authorization: before any write, check that the caller can SEE the project by querying it as that identity —
the Unity Catalog row filter decides (same rule as everywhere else). Lakebase itself is accessed by the app.
Notifications: in-app (Lakebase); email + Slack are queued in the same table and delivered together by one
Databricks job run (server/notify.py) — Slack only when SLACK_DESTINATION_ID is configured.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import PERSONAS, current_user, persona_of, user_client
from .db import pool
from .notify import SLACK_CHANNEL, deliver_async, slack_enabled
from .risk import _sql

router = APIRouter(prefix="/api")


class FollowupIn(BaseModel):
    project_id: str = Field(pattern=r"^P-\d{4}$")
    item_ref: Optional[str] = Field(default=None, max_length=40)
    owner: str = Field(min_length=2, max_length=80)
    due_date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=1000)
    source: str = Field(default="risk-radar", max_length=30)


def _visible_projects(request: Request) -> dict[str, str]:
    """Projects this identity can see — from the (cached) Risk Radar read, which UC row filters already scoped."""
    from .risk import projects
    return {p["id"]: p["name"] for p in projects(request)["projects"]}


def _actor(request: Request) -> tuple[str, str]:
    me = current_user(request)
    persona = persona_of(request)
    who = (me.get("email") or "unknown") if persona == "presenter" else PERSONAS[persona]["label"]
    return who, me.get("email") or ""


@router.post("/followups")
def create_followup(body: FollowupIn, request: Request):
    visible = _visible_projects(request)
    if body.project_id not in visible:
        raise HTTPException(403, "You don't have access to this project.")
    actor, presenter_email = _actor(request)
    due = body.due_date.isoformat() if body.due_date else "no due date"
    title = f"Follow-up assigned: {visible[body.project_id].split(' — ')[0]}{' · ' + body.item_ref if body.item_ref else ''}"
    text = f"{body.owner} — due {due}. {body.note or ''}".strip()
    with pool().connection() as conn:
        fid = conn.execute(
            "INSERT INTO control_tower.followups (project_id, item_ref, owner, owner_email, due_date, note, created_by, source) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (body.project_id, body.item_ref, body.owner, presenter_email, body.due_date, body.note, actor, body.source),
        ).fetchone()[0]
        # In-app notification for the owner; email queued to the presenter's inbox (demo owners are synthetic).
        conn.execute("INSERT INTO control_tower.notifications (followup_id, recipient, channel, title, body, status) VALUES (%s,%s,'in_app',%s,%s,'sent')",
                     (fid, body.owner, title, text))
        subj, msg = f"[Control Tower] {title}", f"For: {body.owner}\n{text}\nAssigned by: {actor}"
        nids, channels = [], ["in-app"]
        if presenter_email:
            nids.append(conn.execute("INSERT INTO control_tower.notifications (followup_id, recipient, channel, title, body, status) VALUES (%s,%s,'email',%s,%s,'queued') RETURNING id",
                                     (fid, presenter_email, subj, msg)).fetchone()[0])
            channels.append("email")
        if slack_enabled():
            nids.append(conn.execute("INSERT INTO control_tower.notifications (followup_id, recipient, channel, title, body, status) VALUES (%s,%s,'slack',%s,%s,'queued') RETURNING id",
                                     (fid, SLACK_CHANNEL or "slack", subj, msg)).fetchone()[0])
            channels.append("slack")
        conn.commit()
    # Run name = what Slack shows: who, what, when.
    run_name = f"Control Tower · {title} → {body.owner}, due {due}"
    deliver_async(nids, run_name, subj, msg, email=presenter_email or None, slack=slack_enabled())
    return {"id": fid, "title": title, "notified": channels, "slack_channel": SLACK_CHANNEL if slack_enabled() else None}


@router.get("/followups")
def list_followups(request: Request, project_id: Optional[str] = None):
    visible = _visible_projects(request)
    ids = [project_id] if project_id else list(visible)
    ids = [i for i in ids if i in visible]
    if not ids:
        return []
    with pool().connection() as conn:
        rows = conn.execute(
            "SELECT id, project_id, item_ref, owner, due_date, note, status, created_by, source, created_at "
            "FROM control_tower.followups WHERE project_id = ANY(%s) ORDER BY created_at DESC LIMIT 50", (ids,)).fetchall()
    cols = ["id", "project_id", "item_ref", "owner", "due_date", "note", "status", "created_by", "source", "created_at"]
    return [{**dict(zip(cols, r)), "project_name": visible.get(r[1], r[1])} for r in rows]


@router.get("/notifications")
def notifications(request: Request):
    visible = _visible_projects(request)
    with pool().connection() as conn:
        rows = conn.execute(
            "SELECT n.id, n.channel, n.title, n.body, n.status, n.created_at, f.project_id FROM control_tower.notifications n "
            "JOIN control_tower.followups f ON f.id = n.followup_id WHERE n.channel = 'in_app' AND f.project_id = ANY(%s) "
            "ORDER BY n.created_at DESC LIMIT 20", (list(visible),)).fetchall()
    return [dict(zip(["id", "channel", "title", "body", "status", "created_at", "project_id"], r)) for r in rows]
