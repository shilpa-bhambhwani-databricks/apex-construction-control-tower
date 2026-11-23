"""Create/update the 'Control Tower — Project Controls (Margin)' Genie Agent for the Office of the CFO (Demo 2).
Over project_margin_mv + the finance tables + evidence chunks. Writes scripts/.genie_finance_id. Re-run to update in place.
Does not modify the Demo 1 Genie Agents."""
import json, os
from pathlib import Path
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
WH = "df23f63620c4cbbf"
S = "bhambs.construction_control_tower"
ID_FILE = Path(__file__).parent / ".genie_finance_id"
hid = lambda prefix, n: f"{prefix}{n:031x}"[-32:]  # noqa: E731

TABLES = {
    "project_margin_mv": "METRIC VIEW — single definition of WIP projected margin and margin fade. Prefer this for any margin question. ALWAYS filter months_ago = 0 for 'current'.",
    "cost_variance_log": "Why cost codes are over budget: amount by project, cost_code, period (month) and cause (price escalation/tariff, quantity overrun, labor productivity, logistics/freight/storage, schedule extension). Ties to job_cost EAC - budget.",
    "cost_codes": "Cost code names (CSI division).",
    "job_cost": "SAP job cost by project, cost_code, month: budget, committed, actual, eac (estimate at completion).",
    "purchase_orders": "Material POs: base_amount (bid unit price basis), price_escalation, tariff_surcharge, freight_and_storage, committed_amount, invoiced_amount, index_change_since_bid_pct, escalation_request_due (PO date + 10 days), escalation_request_filed_date (NULL = not filed).",
    "vendor_invoice_lines": "AP invoice lines: base_amount, price_escalation, tariff_surcharge, freight, storage_fee, line_total; source_document = invoice PDF name.",
    "commodity_index": "Monthly price indices (Jan 2024 = 100) by commodity.",
    "change_orders": "Change orders (Clearstory). Pending/Disputed with decision_date NULL = work performed but not yet in contract revenue (scope leakage).",
    "projects": "Projects: name, market_sector, region, contract_value, bid_margin_pct, pct_complete, project_executive.",
    "project_financials": "WIP inputs per project: bid_gross_profit, contingency_budget, buyout_savings, fade_alert_threshold_pts, project_controls_manager.",
    "finance_doc_chunks": "Text of evidence PDFs (supplier price/tariff notices, invoices, freight notices, contract excerpts, cost report narratives) with doc_name, page, section. Search with text ILIKE.",
    "doc_chunks": "Text of project contracts/subcontracts/specs (e.g. Atlas prime contract Article 7 steel escalation, Ironline subcontract Section 12). Search with text ILIKE.",
}

INSTRUCTIONS = """You are the Project Controls agent for a general contractor's Office of the CFO (finance, project controls, procurement).
Data is synthetic, as of 2026-11-09. Current WIP period = 2026-11-01 (months_ago = 0). August 2026 = months_ago = 3.

Definitions (always use these; the metric view project_margin_mv implements them):
- Bid margin = gross profit at bid / contract value. Projected margin = projected gross profit at completion / (contract value + approved CO revenue).
- Cost growth = SUM(EAC - budget) across cost codes (SAP job cost). Contingency + buyout savings ("the cushion") absorb cost growth first.
- Margin fade = cost growth (net of approved change-order revenue) that the cushion can no longer absorb. Fade in points = bid margin - projected margin.
- A job BREACHES when fade > 1.5 points (breaching_threshold = TRUE). cushion_used_pct > 90% = early warning.

How to answer the margin-fade cycle:
1. ALERT / screening ("which jobs are fading", "breached threshold"): project_margin_mv, months_ago = 0. Compare with the portfolio projected margin to show why the roll-up hides it.
2. WHY ("why did margin drop on X"): (a) trend of projected_margin_pct and cushion_used_pct by period (when did the cushion run out); (b) cost_variance_log for the latest period grouped by cause and by cost_code with cost_codes.description; (c) pending/disputed change_orders (decision_date IS NULL) as unbilled scope; lead with the top 3 drivers in dollars.
3. EVIDENCE: cite rows — PO ids, invoice ids with tariff_surcharge / price_escalation / storage_fee and their source_document, CO ids and age in days — and quote the contract clause or supplier notice from finance_doc_chunks / doc_chunks with doc_name and page.
4. ACTION: recommend specific recovery actions ranked by dollars and deadline: e.g. file steel escalation requests under Atlas Prime Contract Article 7 (increase above 5% of the index; written request with mill quotes within 10 days of each PO; recoverable = (index_change_since_bid_pct - 5)% x base_amount for POs whose escalation_request_due >= 2026-11-09 and not filed); push the oldest pending/disputed COs; give tariff notice under Meridian Prime Contract Article 8 (21 days); challenge storage charges where early delivery was not owner-directed (Meridian Article 9.2). Name the owner (project_controls_manager / project_executive). Never claim an action has been taken.
   For "what should we do" on Atlas use the pinned action query: priority 1 = Article 7 requests on POs still inside the 10-day window ONLY; priority 2 = pending/disputed COs;
   priority 3 = the missed-window POs as a lost-recovery / process lesson (not recoverable). Tariff surcharges are recovered through the Article 7 escalation request, not by disputing the invoice. Omit actions worth $0.
   For EVIDENCE questions, always include the governing clause text: query doc_chunks / finance_doc_chunks WHERE text ILIKE '%escalation%' (Atlas) or '%tariff%' / '%storage%' (Meridian).
5. SCALE ("across all jobs", "what if"): run the same logic portfolio-wide, e.g. a steel price shock on open commitments = (committed_amount - invoiced_amount) on cost_code 05-1200, exposure = pct x base_amount x (1 - invoiced_amount/committed_amount).

Language: use construction finance terms the audience uses (WIP, EAC, cost-to-complete, contingency drawdown, buyout, cost code, change order exposure, escalation clause, scope leakage, fade/gain).
Project names: users say "Atlas", "Meridian", "Vega" — match with project_name / name ILIKE '%Atlas%'.
Format money as $X.XM or $XK, margins to 2 decimals with %, points to 1 decimal. Lead with the answer, keep it short. Never invent numbers not in the data."""

EXAMPLES = [
    ("Which active jobs breached the margin-fade threshold this month, and how does that compare with the portfolio?",
     f"SELECT project_name, region, MEASURE(bid_margin_pct) AS bid_margin_pct, MEASURE(projected_margin_pct) AS projected_margin_pct,\n"
     f"  MEASURE(margin_fade_pts) AS fade_pts, ROUND(MEASURE(margin_fade_usd)/1e6, 1) AS fade_usd_m, MEASURE(cushion_used_pct) AS cushion_used_pct\n"
     f"FROM {S}.project_margin_mv WHERE months_ago = 0 AND breaching_threshold\nGROUP BY ALL ORDER BY fade_pts DESC"),
    ("What is the portfolio projected margin versus bid this month?",
     f"SELECT MEASURE(bid_margin_pct) AS bid_margin_pct, MEASURE(projected_margin_pct) AS projected_margin_pct, MEASURE(projects_breaching) AS jobs_breaching, MEASURE(project_count) AS jobs\n"
     f"FROM {S}.project_margin_mv WHERE months_ago = 0"),
    ("When did Atlas start to fade?",
     f"SELECT period, MEASURE(projected_margin_pct) AS projected_margin_pct, MEASURE(cushion_used_pct) AS cushion_used_pct, ROUND(MEASURE(cost_growth_usd)/1e6, 1) AS cost_growth_m\n"
     f"FROM {S}.project_margin_mv WHERE project_name ILIKE '%Atlas%' AND months_ago <= 5 GROUP BY ALL ORDER BY period"),
    ("Why did projected margin drop on Atlas? Break the cost growth down by cause and cost code.",
     f"SELECT v.cost_code, c.description, v.cause, ROUND(SUM(v.amount)/1e6, 1) AS usd_m\n"
     f"FROM {S}.cost_variance_log v JOIN {S}.cost_codes c USING (cost_code) JOIN {S}.projects p USING (project_id)\n"
     f"WHERE p.name ILIKE '%Atlas%' AND v.period = DATE'2026-11-01' GROUP BY ALL ORDER BY usd_m DESC LIMIT 8"),
    ("Which pending change orders on Atlas are work performed but not yet billed, and how old are they?",
     f"SELECT c.co_id, c.subcontractor, c.description, c.status, ROUND(c.amount_requested/1e3) AS amount_k, datediff(DATE'2026-11-09', c.submitted_date) AS age_days\n"
     f"FROM {S}.change_orders c JOIN {S}.projects p USING (project_id)\nWHERE p.name ILIKE '%Atlas%' AND c.decision_date IS NULL ORDER BY age_days DESC"),
    ("Which Atlas steel POs can still be claimed under the escalation clause, and how much did we miss?",
     f"SELECT po_id, po_date, ROUND(base_amount/1e6, 2) AS base_m, index_change_since_bid_pct, escalation_request_due,\n"
     f"  ROUND(GREATEST(index_change_since_bid_pct - 5, 0)/100 * base_amount/1e6, 2) AS recoverable_m,\n"
     f"  CASE WHEN escalation_request_due >= DATE'2026-11-09' THEN 'Open - file now' ELSE 'Window missed' END AS status\n"
     f"FROM {S}.purchase_orders WHERE project_id = 'P-1001' AND cost_code = '05-1200' AND escalation_request_filed_date IS NULL AND index_change_since_bid_pct > 5\nORDER BY po_date DESC"),
    ("What should we do this week to recover margin on Atlas?",
     f"WITH esc AS (\n"
     f"  SELECT COUNT(*) AS n, SUM(GREATEST(index_change_since_bid_pct - 5, 0)/100 * base_amount) AS usd, MIN(escalation_request_due) AS due\n"
     f"  FROM {S}.purchase_orders WHERE project_id = 'P-1001' AND cost_code = '05-1200' AND escalation_request_filed_date IS NULL\n"
     f"    AND index_change_since_bid_pct > 5 AND escalation_request_due >= DATE'2026-11-09'),\n"
     f"missed AS (\n"
     f"  SELECT COUNT(*) AS n, SUM(GREATEST(index_change_since_bid_pct - 5, 0)/100 * base_amount) AS usd\n"
     f"  FROM {S}.purchase_orders WHERE project_id = 'P-1001' AND cost_code = '05-1200' AND escalation_request_filed_date IS NULL\n"
     f"    AND index_change_since_bid_pct > 5 AND escalation_request_due < DATE'2026-11-09'),\n"
     f"cos AS (\n"
     f"  SELECT COUNT(*) AS n, SUM(amount_requested) AS usd, MAX(datediff(DATE'2026-11-09', submitted_date)) AS oldest_days\n"
     f"  FROM {S}.change_orders WHERE project_id = 'P-1001' AND decision_date IS NULL),\n"
     f"own AS (SELECT project_executive, project_controls_manager FROM {S}.project_margin_mv WHERE project_id = 'P-1001' AND months_ago = 0 GROUP BY ALL)\n"
     f"SELECT 1 AS priority, 'File Article 7 steel escalation requests (with mill quotes) on open POs' AS action, esc.n AS items, ROUND(esc.usd/1e6, 2) AS usd_m, CAST(esc.due AS STRING) AS deadline, own.project_controls_manager AS owner FROM esc, own\n"
     f"UNION ALL SELECT 2, 'Push pending / disputed change orders to approval (unbilled scope)', cos.n, ROUND(cos.usd/1e6, 2), concat('oldest ', cos.oldest_days, ' days'), own.project_executive FROM cos, own\n"
     f"UNION ALL SELECT 3, 'Process fix: escalation window missed on earlier steel POs - file with every future steel release', missed.n, ROUND(missed.usd/1e6, 2), 'ongoing', own.project_controls_manager FROM missed, own\n"
     f"ORDER BY priority"),
    ("Show the steel invoice lines carrying tariff surcharges on Atlas",
     f"SELECT invoice_id, po_id, invoice_date, ROUND(base_amount) AS base, ROUND(price_escalation) AS price_escalation, ROUND(tariff_surcharge) AS tariff_surcharge, ROUND(freight) AS freight, source_document\n"
     f"FROM {S}.vendor_invoice_lines WHERE project_id = 'P-1001' AND cost_code = '05-1200' AND tariff_surcharge > 0 ORDER BY invoice_date DESC LIMIT 10"),
    ("What does the Atlas prime contract say about steel escalation?",
     f"SELECT doc_name, page, section, text FROM {S}.doc_chunks WHERE text ILIKE '%escalation%' AND doc_type IN ('prime_contract', 'subcontract')"),
    ("If the steel tariff rises another 15%, what's the margin exposure across all active jobs with open steel commitments?",
     f"SELECT p.name, p.region, ROUND(SUM(po.committed_amount - po.invoiced_amount)/1e6, 1) AS open_steel_commitments_m,\n"
     f"  ROUND(0.15 * SUM(po.base_amount * (1 - po.invoiced_amount / po.committed_amount))/1e6, 2) AS exposure_m\n"
     f"FROM {S}.purchase_orders po JOIN {S}.projects p USING (project_id)\nWHERE po.cost_code = '05-1200' GROUP BY ALL HAVING open_steel_commitments_m > 0 ORDER BY exposure_m DESC"),
    ("Which jobs have burned through more than 90% of their contingency and buyout savings?",
     f"SELECT project_name, MEASURE(cushion_used_pct) AS cushion_used_pct, ROUND(MEASURE(cushion_remaining_usd)/1e6, 1) AS cushion_left_m, MEASURE(margin_fade_pts) AS fade_pts\n"
     f"FROM {S}.project_margin_mv WHERE months_ago = 0 GROUP BY ALL HAVING cushion_used_pct > 90 ORDER BY cushion_left_m"),
]
SAMPLES = [EXAMPLES[0][0], "Why did projected margin drop on Project Atlas?",
           "Show me the evidence behind the steel cost increase on Atlas", "What should we do this week to recover margin on Atlas?",
           EXAMPLES[9][0]]

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
title = "Control Tower — Project Controls (Margin)"
desc = "Office of the CFO: WIP projected margin, margin fade drivers, escalation and change-order recovery, portfolio exposure. Synthetic demo data."
if ID_FILE.exists():
    sid = ID_FILE.read_text().strip()
    w.genie.update_space(sid, serialized_space=payload, title=title, description=desc, warehouse_id=WH)
    print("updated space", sid)
else:
    sp = w.genie.create_space(WH, payload, title=title, description=desc)
    ID_FILE.write_text(sp.space_id)
    print("created space", sp.space_id)
