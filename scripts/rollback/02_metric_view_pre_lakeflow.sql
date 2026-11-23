CREATE OR REPLACE VIEW project_risk_mv
WITH METRICS
LANGUAGE YAML
COMMENT 'Single definition of the Control Tower Project Risk Score (0-100) and its six signals. Used by the app, Genie, and MCP. Data as of 2026-11-09 (synthetic).'
AS $$
version: 1.1
source: bhambs.construction_control_tower.project_signal_weekly
joins:
  - name: p
    source: bhambs.construction_control_tower.projects
    on: source.project_id = p.project_id
dimensions:
  - name: project_id
    expr: source.project_id
  - name: project_name
    expr: p.name
    comment: "Project name, e.g. Project Atlas — Data Center Campus, Bldg 3"
  - name: market_sector
    expr: p.market_sector
    comment: "Data Center, Healthcare, Aviation, Commercial, Education"
  - name: region
    expr: p.region
  - name: business_unit
    expr: p.business_unit
  - name: pct_complete
    expr: p.pct_complete
  - name: week
    expr: source.week
    comment: "Week-ending snapshot date (weekly, Mondays). Latest week is 2026-11-09."
  - name: weeks_ago
    expr: CAST(datediff(DATE'2026-11-09', source.week) / 7 AS INT)
    comment: "0 = current week, 8 = eight weeks ago. Use weeks_ago = 0 for 'this week'."
  - name: signal
    expr: source.signal
    comment: "rfi = open RFIs aging > 21 days; co = pending change-order exposure; submittal = overdue submittals; schedule = critical-path float consumed (P6); cost = EAC vs budget (SAP); safety = near-misses/observations trailing 14 days"
measures:
  - name: risk_score
    expr: SUM(source.sub_score * source.weight) / COUNT(DISTINCT concat(source.project_id, '|', CAST(source.week AS STRING)))
    comment: "Project Risk Score 0-100 = weighted sum of six signal sub-scores (weights rfi .15, co .20, submittal .10, schedule .20, cost .25, safety .10). Averaged across projects when grouped above project level. Grouped by signal it gives that signal's contribution in points."
  - name: signal_sub_score
    expr: AVG(source.sub_score)
    comment: "Signal sub-score 0-100 (higher = more risk). Group by signal."
  - name: signal_raw_value
    expr: AVG(source.raw_value)
    comment: "Underlying raw value of the signal: aging RFI count, pending CO dollars, overdue submittal count, float days, EAC overrun fraction, or 14-day observation count."
  - name: project_count
    expr: COUNT(DISTINCT source.project_id)
$$
