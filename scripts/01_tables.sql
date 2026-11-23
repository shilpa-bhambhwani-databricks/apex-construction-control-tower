CREATE OR REPLACE TABLE projects COMMENT 'Synthetic projects (Procore/SAP-shaped). Shared demo dataset — brand-neutral.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/projects.parquet')
;;
CREATE OR REPLACE TABLE rfis COMMENT 'Synthetic RFIs (Procore-shaped). activity_id links to schedule_activities.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/rfis.parquet')
;;
CREATE OR REPLACE TABLE change_orders COMMENT 'Synthetic change orders (Clearstory-shaped). Pending = decision_date IS NULL.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/change_orders.parquet')
;;
CREATE OR REPLACE TABLE submittals COMMENT 'Synthetic submittals (Procore-shaped).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/submittals.parquet')
;;
CREATE OR REPLACE TABLE schedule_activities COMMENT 'Synthetic P6 activities.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/schedule_activities.parquet')
;;
CREATE OR REPLACE TABLE schedule_float_weekly COMMENT 'Weekly P6 snapshots: critical-path float days per project.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/schedule_float_weekly.parquet')
;;
CREATE OR REPLACE TABLE job_cost COMMENT 'Synthetic SAP job cost by cost code and month (budget, committed, actual, EAC).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/job_cost.parquet')
;;
CREATE OR REPLACE TABLE safety_observations COMMENT 'Synthetic safety observations and near-misses (Procore/Origami-shaped).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/safety_observations.parquet')
;;
CREATE OR REPLACE TABLE project_signal_weekly COMMENT 'Weekly risk-signal sub-scores (0-100) computed from the raw tables as of each week. Formulas in data_gen/generate.py SIGNAL_FORMULAS.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v1/project_signal_weekly.parquet')
;;
SELECT table_name, (SELECT 1) AS ok FROM information_schema.tables WHERE table_schema = 'construction_control_tower' ORDER BY 1
