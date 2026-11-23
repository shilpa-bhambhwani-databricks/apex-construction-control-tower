"""Create/update the 'Control Tower — Jobsite Safety' Genie Agent (for Genie One + ChatGPT/Claude via the Genie One MCP).
Same governed, row-filtered jobsite tables the app uses → same answers in the app and in ChatGPT. Writes scripts/.genie_jobsite_id."""
import json, os
from pathlib import Path
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
S, WH = "bhambs.construction_control_tower", "df23f63620c4cbbf"
ID_FILE = Path(__file__).parent / ".genie_jobsite_id"
hid = lambda prefix, n: f"{prefix}{n:031x}"[-32:]  # noqa: E731
TABLES = {
    "jobsite_crews": "Manpower by trade: planned vs actual yesterday (short_by > 0 = short-staffed).",
    "jobsite_day": "Per-project superintendent summary as of 2026-11-09: superintendent, weather, phase, 14-day near-miss count and theme.",
    "jobsite_events": "Deliveries and inspections scheduled today.",
    "jobsite_lookahead": "2-week lookahead: activity, when_label (Today/Tomorrow/Thu/Next Mon), planned_date, hazard, standard (OSHA/EHS), permit, risk_level, ready flag, and readiness checks *_ok / *_detail / *_owner / *_needed_by for info (RFIs), approvals (submittals), materials, float.",
    "projects": "Projects: name, market_sector, region, pct_complete, superintendent.",
    "safety_observations": "Safety observations and near-misses (near_miss_flag) by date, category, severity.",
}
INSTR = """You are the Jobsite Safety agent for construction superintendents. Data is synthetic, as of 2026-11-09 (Monday).
- "This week" = jobsite_lookahead when_label IN ('Today','Tomorrow','Thu'); "next 2 weeks" = all rows. High-risk = risk_level IN ('critical','serious').
- Users say "Atlas", "Meridian" etc. — match projects.name ILIKE '%Atlas%'. If the user can see only one project, use it by default.
- For readiness: an activity is not ready when ready = false; explain which check failed using *_detail, *_owner and *_needed_by.
- For safety: always mention the activity's standard and permit, and the 14-day near-miss count/theme from jobsite_day.
- Keep answers short and prioritized (Today first). Never invent data."""
EX = [("What safety items and high-risk activities do we have this week on Atlas?",
       f"SELECT l.when_label, l.activity, l.area, l.hazard, l.standard, l.permit, l.risk_level, l.ready, d.near_miss_count_14d, d.near_miss_theme\nFROM {S}.jobsite_lookahead l JOIN {S}.jobsite_day d USING (project_id) JOIN {S}.projects p USING (project_id)\nWHERE p.name ILIKE '%Atlas%' AND l.when_label IN ('Today','Tomorrow','Thu') AND l.risk_level IN ('critical','serious') ORDER BY l.planned_date"),
      ("What's not ready to start in the next 2 weeks on Atlas, and who owns it?",
       f"SELECT activity, when_label, info_detail, info_owner, approvals_detail, approvals_owner, materials_detail, float_detail\nFROM {S}.jobsite_lookahead l JOIN {S}.projects p USING (project_id)\nWHERE p.name ILIKE '%Atlas%' AND NOT l.ready ORDER BY planned_date"),
      ("Which trades were short-staffed yesterday?",
       f"SELECT p.name, c.trade, c.company, c.planned, c.actual_yesterday, c.short_by FROM {S}.jobsite_crews c JOIN {S}.projects p USING (project_id) WHERE c.short_by > 0 ORDER BY c.short_by DESC")]
space = {"version": 2,
         "config": {"sample_questions": [{"id": hid("1", i + 1), "question": [q]} for i, (q, _) in enumerate(EX)]},
         "data_sources": {"tables": [{"identifier": f"{S}.{t}", "description": [d]} for t, d in sorted(TABLES.items())]},
         "instructions": {"text_instructions": [{"id": hid("2", 1), "content": [INSTR]}],
                          "example_question_sqls": [{"id": hid("3", i + 1), "question": [q], "sql": [sql]} for i, (q, sql) in enumerate(EX)]}}
title, desc = "Control Tower — Jobsite Safety", "Project-aware jobsite safety and work readiness: 2-week lookahead, permits, standards, near-misses, crews. Synthetic demo data."
if ID_FILE.exists():
    sid = ID_FILE.read_text().strip(); w.genie.update_space(sid, serialized_space=json.dumps(space), title=title, description=desc, warehouse_id=WH); print("updated", sid)
else:
    sid = w.genie.create_space(WH, json.dumps(space), title=title, description=desc).space_id; ID_FILE.write_text(sid); print("created", sid)
