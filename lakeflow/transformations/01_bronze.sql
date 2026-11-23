-- BRONZE — raw ingestion with Auto Loader (STREAM read_files) from the Unity Catalog landing volume.
-- One streaming table per source-system feed. Files are picked up incrementally: when a new extract lands in the
-- volume (e.g. rfis_2026-11-16.parquet matches the rfis*.parquet pattern), the next pipeline update appends only
-- the new file. Every row keeps its source file + ingest time.
-- Every table carries the same Unity Catalog row filter as the rest of the dataset (ct_row_scope), so a user
-- only ever sees the projects they are mapped to — at every layer, not just the serving layer.
-- Docs: https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-streaming-table

CREATE OR REFRESH STREAMING TABLE bronze_projects
COMMENT 'Bronze: project master (ERP/Procore-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/projects*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_project_signal_weekly
COMMENT 'Bronze: weekly risk-signal snapshots (six signals per project per week), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/project_signal_weekly*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_rfis
COMMENT 'Bronze: RFIs (Procore-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/rfis*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_change_orders
COMMENT 'Bronze: change orders (change-management-system-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/change_orders*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_submittals
COMMENT 'Bronze: submittals (Procore-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/submittals*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_schedule_activities
COMMENT 'Bronze: schedule activities (P6-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/schedule_activities*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_schedule_float_weekly
COMMENT 'Bronze: weekly critical-path float snapshots (P6-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/schedule_float_weekly*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_job_cost
COMMENT 'Bronze: job cost by cost code and month (ERP-shaped: budget, committed, actual, EAC), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/job_cost*.parquet', format => 'parquet');

CREATE OR REFRESH STREAMING TABLE bronze_safety_observations
COMMENT 'Bronze: safety observations and near-misses (EHS-system-shaped), raw as landed. Synthetic.'
TBLPROPERTIES ('quality' = 'bronze')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT *, _metadata.file_path AS _source_file, _metadata.file_modification_time AS _source_modified_at, current_timestamp() AS _ingested_at
FROM STREAM read_files('${raw_path}/safety_observations*.parquet', format => 'parquet');
