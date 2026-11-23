"""Create (or update) the 'Control Tower — Portfolio Risk' Genie Agent over the metric view + raw tables.
Writes the space id to scripts/.genie_space_id. Re-run to update instructions/examples in place."""
import json, os
from pathlib import Path
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
WH = "df23f63620c4cbbf"
S = "bhambs.construction_control_tower"
ID_FILE = Path(__file__).parent / ".genie_space_id"
hid = lambda prefix, n: f"{prefix}{n:031x}"[-32:]  # noqa: E731  (32-char lowercase hex)

TABLES = {
    "change_orders": "Change orders (Clearstory). Pending/disputed = decision_date IS NULL. amount_requested in USD.",
    "job_cost": "SAP job cost by project, cost_code, month (period): budget, committed, actual, eac (estimate at completion).",
    "project_risk_mv": "METRIC VIEW — single definition of the Project Risk Score (0-100) and its six signals. Prefer this for any risk-score question. Query with MEASURE(risk_score).",
    "projects": "Projects: name, market_sector, region, contract_value (USD), bid_margin_pct, pct_complete, project_executive, superintendent.",
    "rfis": "RFIs (Procore). Open + created_date older than 21 days = aging. activity_id links to schedule_activities.",
    "safety_observations": "Safety observations and near-misses (near_miss_flag).",
    "schedule_activities": "P6 activities: planned_start/finish, total_float_days, critical_flag.",
    "schedule_float_weekly": "Weekly P6 snapshot of critical-path float days per project.",
    "submittals": "Submittals (Procore). Overdue = returned_date IS NULL and required_on_site_date within 14 days or past.",
}
INSTRUCTIONS = """You are the Control Tower Portfolio Risk agent for a general contractor's operations leaders and project teams.
- Data is synthetic and current as of 2026-11-09 (Monday). "This week" = weeks_ago = 0 in project_risk_mv. "8 weeks ago" = weeks_ago = 8.
- ALWAYS use the metric view project_risk_mv for risk scores: MEASURE(risk_score). Grouping by signal gives each signal's contribution in points.
- Signals: rfi (open RFIs > 21 days), co (pending change-order exposure), submittal (overdue submittals), schedule (critical-path float consumed, P6), cost (EAC vs budget, SAP), safety (near-misses/observations, trailing 14 days).
- Risk bands: >= 70 Critical, 55-69 High, 40-54 Watch, < 40 On track. "Needs attention" = risk_score >= 55.
- Project names: users often say just "Atlas", "Helios", "Meridian" — match with project_name ILIKE '%Atlas%'.
- Questions may start with "[Context: project P-xxxx ...]" from the app — use that project_id as the default subject.
- When explaining WHY a score changed, compare weeks_ago = 0 vs weeks_ago = 8 by signal, then cite the underlying rows (RFI ids, CO ids and amounts, subcontractors).
- Explain signals in plain language using the underlying raw values (signal_raw_value), never as bare decimals:
  rfi → "N open RFIs older than 21 days"; co → "$X.XM pending change orders"; submittal → "N overdue submittals";
  schedule → "N.N days of critical-path float left"; cost → "EAC X.X% over budget" (raw is a fraction, multiply by 100); safety → "N observations/near-misses in the last 14 days".
- Format money as $X.XM or $XK, round points to one decimal. Keep answers short and lead with the answer. Never invent numbers not in the data."""
EXAMPLES = [
    ("Which projects need attention this week, and what's driving it?",
     f"SELECT project_name, market_sector, region, ROUND(MEASURE(risk_score)) AS risk_score\nFROM {S}.project_risk_mv WHERE weeks_ago = 0\nGROUP BY ALL HAVING risk_score >= 55 ORDER BY risk_score DESC"),
    ("Why did Atlas's risk score rise over the last 8 weeks?",
     f"SELECT signal,\n  ROUND(MEASURE(risk_score) FILTER (WHERE weeks_ago = 0), 1) AS pts_now,\n  ROUND(MEASURE(risk_score) FILTER (WHERE weeks_ago = 8), 1) AS pts_8w_ago\nFROM {S}.project_risk_mv WHERE project_name ILIKE '%Atlas%' AND weeks_ago IN (0, 8)\nGROUP BY ALL ORDER BY pts_now - pts_8w_ago DESC"),
    ("Which open RFIs on Atlas block critical-path work in the next 2 weeks?",
     f"SELECT r.rfi_id, r.subject, s.activity_name, s.planned_start, s.total_float_days\nFROM {S}.rfis r JOIN {S}.schedule_activities s ON r.activity_id = s.activity_id\nJOIN {S}.projects p ON r.project_id = p.project_id\nWHERE p.name ILIKE '%Atlas%' AND r.status = 'Open' AND s.critical_flag\n  AND s.planned_start <= DATE'2026-11-09' + INTERVAL 14 DAYS ORDER BY s.planned_start"),
    ("Which subcontractors account for the most pending CO dollars on data center jobs?",
     f"SELECT c.subcontractor, ROUND(SUM(c.amount_requested)/1e6, 2) AS pending_usd_m, COUNT(*) AS cos\nFROM {S}.change_orders c JOIN {S}.projects p ON c.project_id = p.project_id\nWHERE c.decision_date IS NULL AND p.market_sector = 'Data Center'\nGROUP BY c.subcontractor ORDER BY pending_usd_m DESC LIMIT 5"),
    ("Compare Atlas to the other data center projects on RFI turnaround",
     f"SELECT p.name, ROUND(percentile(datediff(r.closed_date, r.created_date), 0.5), 1) AS median_turnaround_days, COUNT(*) AS closed_rfis\nFROM {S}.rfis r JOIN {S}.projects p ON r.project_id = p.project_id\nWHERE p.market_sector = 'Data Center' AND r.closed_date >= DATE'2026-11-09' - INTERVAL 90 DAYS\nGROUP BY p.name ORDER BY median_turnaround_days DESC"),
    ("What's keeping Riverside on track?",
     f"WITH me AS (SELECT signal, MEASURE(signal_sub_score) AS s FROM {S}.project_risk_mv WHERE project_name ILIKE '%Riverside%' AND weeks_ago = 0 GROUP BY ALL),\n     pf AS (SELECT signal, MEASURE(signal_sub_score) AS s FROM {S}.project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL)\nSELECT me.signal, ROUND(me.s) AS riverside, ROUND(pf.s) AS portfolio_avg, ROUND(pf.s - me.s) AS better_by\nFROM me JOIN pf USING (signal) ORDER BY better_by DESC"),
]
SAMPLES = [e[0] for e in EXAMPLES[:4]]

space = {
    "version": 2,
    "config": {"sample_questions": [{"id": hid("1", i + 1), "question": [q]} for i, q in enumerate(SAMPLES)]},
    "data_sources": {"tables": [{"identifier": f"{S}.{t}", "description": [d]} for t, d in sorted(TABLES.items())]},
    "instructions": {
        "text_instructions": [{"id": hid("2", 1), "content": [INSTRUCTIONS]}],
        "example_question_sqls": [{"id": hid("3", i + 1), "question": [q], "sql": [sql]} for i, (q, sql) in enumerate(EXAMPLES)],
    },
}
payload = json.dumps(space)
title, desc = "Control Tower — Portfolio Risk", "Portfolio risk for construction projects: risk score, six signals, RFIs, COs, schedule, cost, safety. Synthetic demo data."
if ID_FILE.exists():
    sid = ID_FILE.read_text().strip()
    w.genie.update_space(sid, serialized_space=payload, title=title, description=desc, warehouse_id=WH)
    print("updated space", sid)
else:
    sp = w.genie.create_space(WH, payload, title=title, description=desc)
    ID_FILE.write_text(sp.space_id)
    print("created space", sp.space_id)
