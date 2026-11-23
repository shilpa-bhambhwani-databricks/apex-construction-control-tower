"""Jobsite Intelligence agent — does everything a standards-only safety assistant does (EHS standards + OSHA answers)
and adds THIS project's context: 2-week lookahead with readiness checks, near-misses, crews, deliveries/inspections, photos.

Tools run AS THE SELECTED IDENTITY (row filters → a superintendent only sees their project). Standards come from the
governed AI Search index (doc_type = 'ehs'). Same shared MLflow-traced loop as Resolve.
"""
from __future__ import annotations

import json
from typing import Any

from databricks.sdk import WorkspaceClient

from .resolve_agent import _vs, run_loop
from .risk import _sql

SYSTEM = """You are Jobsite Intelligence, a field assistant for construction superintendents.
You answer safety and work-readiness questions using the company EHS standards and OSHA 29 CFR 1926 (search_standards), PLUS this project's
own context: the 2-week lookahead with readiness checks (get_lookahead), today's crews/deliveries/inspections and weather (get_jobsite_day), and
recent safety observations (get_recent_observations). Always gather project context before answering a project question.
Rules:
- Cite standards as [EHS-xx §title] and OSHA sections as written in the standard (e.g. [OSHA 1926.652(a)(1)]); cite project data as [lookahead], [observations], [jobsite_day].
- Separate company-standard requirements from OSHA requirements when both apply. Never invent regulation text or section numbers.
- Superintendent-ready: short, prioritized, plain language. Max ~180 words unless asked for a toolbox talk.
- For a toolbox talk: title, then 6 bullets — hazard, controls & permit, why it matters here (recent near-misses), conditions today, new workers, stop-work authority.
- For a photo: list what you can see that is a hazard (or say none visible), the matching standard, and the project activity it relates to. Say clearly that a
  photo check is an aid and does not declare an area safe.
- Drafts only: never claim anything was submitted to Procore or signed off."""

TOOLS = [
    {"type": "function", "function": {"name": "get_lookahead", "description": "This project's 2-week lookahead: activity, when, trade, area, hazard, standard, required permit, risk level, and readiness checks (RFIs, submittals, materials, float) with owner and needed-by.",
                                      "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {"name": "get_jobsite_day", "description": "Today's superintendent summary: weather, phase, 14-day near-miss count/theme, crews planned vs actual, deliveries and inspections.",
                                      "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {"name": "get_recent_observations", "description": "Safety observations and near-misses on this project in the last N days, grouped by category and severity.",
                                      "parameters": {"type": "object", "properties": {"project_id": {"type": "string"}, "days": {"type": "integer"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {"name": "search_standards", "description": "Search the company EHS field standards (with OSHA 29 CFR 1926 references) for requirements on a topic.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]
LABELS = {"get_lookahead": "Reading 2-week lookahead (P6)", "get_jobsite_day": "Checking crews, deliveries, weather", "get_recent_observations": "Reviewing recent near-misses", "search_standards": "Searching EHS standards & OSHA"}
SPANS = {"search_standards": "RETRIEVER"}


def _pid(a: dict) -> str:
    pid = str(a.get("project_id", ""))
    if not (len(pid) == 6 and pid.startswith("P-") and pid[2:].isdigit()):
        raise ValueError("project_id must look like P-1001")
    return pid


def _runner(user_w: WorkspaceClient):
    def run(name: str, a: dict) -> Any:
        if name == "get_lookahead":
            return _sql(user_w, f"SELECT * EXCEPT (project_id) FROM jobsite_lookahead WHERE project_id = '{_pid(a)}' ORDER BY seq")
        if name == "get_jobsite_day":
            pid = _pid(a)
            return {"day": _sql(user_w, f"SELECT * FROM jobsite_day WHERE project_id = '{pid}'"),
                    "crews": _sql(user_w, f"SELECT trade, company, planned, actual_yesterday, short_by FROM jobsite_crews WHERE project_id = '{pid}'"),
                    "events": _sql(user_w, f"SELECT time, kind, description FROM jobsite_events WHERE project_id = '{pid}' ORDER BY time")}
        if name == "get_recent_observations":
            days = max(1, min(int(a.get("days") or 14), 90))
            return _sql(user_w, f"""SELECT category, severity, SUM(CASE WHEN near_miss_flag THEN 1 ELSE 0 END) AS near_misses, COUNT(*) AS observations
                                    FROM safety_observations WHERE project_id = '{_pid(a)}' AND date >= DATE'2026-11-09' - INTERVAL {days} DAYS
                                    GROUP BY ALL ORDER BY near_misses DESC, observations DESC""")
        if name == "search_standards":
            return [{"section": h.get("section"), "text": (h.get("text") or "")[:1200]} for h in _vs(a["query"], {"doc_type": "ehs"}, k=3)]
        raise ValueError(f"unknown tool {name}")
    return run


def _summarize(tool: str, r: Any) -> str:
    if isinstance(r, dict) and "error" in r:
        return "error: " + r["error"][:80]
    if tool == "get_lookahead":
        return f"{len(r)} activities · {sum(1 for x in r if str(x.get('ready')).lower() == 'false')} not ready"
    if tool == "get_jobsite_day":
        return f"{len(r['crews'])} crews · {len(r['events'])} deliveries/inspections"
    if tool == "get_recent_observations":
        return f"{sum(int(x['near_misses']) for x in r)} near-misses · {sum(int(x['observations']) for x in r)} observations"
    if tool == "search_standards":
        return ", ".join(x["section"] or "" for x in r)[:140]
    return ""


def ask(project: dict, question: str, user_w: WorkspaceClient, actor: str, image_data_url: str | None = None) -> dict:
    text = f"Project: {json.dumps(project)}\nQuestion: {question}"
    content: Any = text if not image_data_url else [{"type": "text", "text": text + "\n(A field photo is attached.)"},
                                                    {"type": "image_url", "image_url": {"url": image_data_url}}]
    return run_loop(SYSTEM, TOOLS, _runner(user_w), content, {"project": project, "question": question, "photo": bool(image_data_url), "user": actor},
                    {"agent": "jobsite_agent", "tab": "jobsite", "item": project.get("project_id", ""), "user": actor}, LABELS, SPANS, _summarize)
