CREATE OR REPLACE TABLE access_scope (principal STRING, persona STRING, project_id STRING)
COMMENT 'Who can see which projects. project_id = * means all. Demo personas: presenter (ops leadership), simulated Northeast PM, simulated Atlas superintendent.'
;;
INSERT INTO access_scope
SELECT '<your-user-email>', 'Ops leadership', '*'
UNION ALL SELECT '<northeast-pm-sp-application-id>', 'Northeast PM (simulated)', project_id FROM projects WHERE region = 'Northeast'
UNION ALL SELECT '<superintendent-sp-application-id>', 'Atlas superintendent (simulated)', 'P-1001'
;;
CREATE OR REPLACE FUNCTION ct_row_scope(pid STRING) RETURNS BOOLEAN
COMMENT 'Row filter: a row is visible if the current user is mapped to its project (or to *) in access_scope.'
RETURN EXISTS (SELECT 1 FROM bhambs.construction_control_tower.access_scope a WHERE a.principal = current_user() AND (a.project_id = '*' OR a.project_id = pid))
;;
ALTER TABLE projects SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE project_signal_weekly SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE rfis SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE change_orders SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE submittals SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE schedule_activities SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE schedule_float_weekly SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE job_cost SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE safety_observations SET ROW FILTER ct_row_scope ON (project_id)
;;
GRANT USE CATALOG ON CATALOG bhambs TO `<northeast-pm-sp-application-id>`
;;
GRANT USE CATALOG ON CATALOG bhambs TO `<superintendent-sp-application-id>`
;;
GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA bhambs.construction_control_tower TO `<northeast-pm-sp-application-id>`
;;
GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA bhambs.construction_control_tower TO `<superintendent-sp-application-id>`
;;
SELECT persona, COUNT(*) AS projects FROM access_scope GROUP BY persona
