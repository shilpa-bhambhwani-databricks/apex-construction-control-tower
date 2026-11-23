CREATE OR REPLACE TABLE jobsite_day COMMENT 'Per-project superintendent day summary (as of 2026-11-09): superintendent, weather, phase, 14-day near-misses.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/jobsite_day.parquet')
;;
CREATE OR REPLACE TABLE jobsite_lookahead COMMENT '2-week lookahead per project with hazard, OSHA/EHS standard, required permit, and readiness checks (info=RFIs, approvals=submittals, materials, float) with owner and needed-by date.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/jobsite_lookahead.parquet')
;;
CREATE OR REPLACE TABLE jobsite_crews COMMENT 'Manpower by trade: planned vs actual yesterday (Procore daily log vs P6 resource plan).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/jobsite_crews.parquet')
;;
CREATE OR REPLACE TABLE jobsite_events COMMENT 'Deliveries and inspections scheduled today.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/jobsite_events.parquet')
;;
ALTER TABLE jobsite_day SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE jobsite_lookahead SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE jobsite_crews SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE jobsite_events SET ROW FILTER ct_row_scope ON (project_id)
;;
SELECT activity, when_label, risk_level, ready, info_detail, approvals_detail FROM jobsite_lookahead WHERE project_id = 'P-1001' ORDER BY seq
