# Stage 1 — Lakeflow: ingest the raw data

A serverless Lakeflow Spark Declarative Pipeline (`lakeflow/`) ingests the nine raw source-system extracts from a Unity Catalog volume into bronze streaming tables with Auto Loader, then builds quality-checked silver materialized views. The silver tables are the source of the governed risk metric view that the app and the Genie Agent read (see `02_unity_catalog.md`).

Captured 2026-11-23 19:36 UTC by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.

## Pipeline

```text
name        : construction-control-tower-ingest
pipeline_id : c8a0222b-348b-413d-bb05-a0cda17c73d3
state       : PipelineState.IDLE
target      : bhambs.construction_control_tower
serverless  : True
continuous  : False
source      : ['/Workspace/Users/<presenter>/.bundle/construction-control-tower-ingest/demo/files/transformations/**']
config      : {'raw_path': '/Volumes/bhambs/construction_control_tower/raw/v1'}
```

## Update history (newest first)

The first attempts failed — a streaming `read_files` source needs a directory or glob, not a single file path. The source was changed to glob patterns (`rfis*.parquet`) and every update since has completed. Failures are left in the record on purpose.

```text
update_id                            | state     | cause            | started (UTC)
-------------------------------------+-----------+------------------+--------------------
a51bb91f-5b2d-496c-8278-138b78f9191a | COMPLETED | API_CALL         | 2026-11-23 19:27:37
61b080b3-118d-423a-9d32-4232a7b18ed3 | COMPLETED | RETRY_ON_FAILURE | 2026-11-23 16:49:54
5fefbcb9-a3e7-4786-882d-a4db466bf1c1 | FAILED    | RETRY_ON_FAILURE | 2026-11-23 16:48:24
ea1a4d34-eebb-45af-8c06-dae6f0d1b35e | FAILED    | RETRY_ON_FAILURE | 2026-11-23 16:47:35
76df3bb3-ddb7-4b77-9920-f3aee48b3ea5 | FAILED    | RETRY_ON_FAILURE | 2026-11-23 16:47:06
284f5f74-e09c-4f3b-bba7-fbd67310c5ff | FAILED    | API_CALL         | 2026-11-23 16:46:39
```

### Rows written per table, per update (pipeline event log)

The first completed update ingests every raw file into bronze. Later updates write no bronze rows because no new files landed — ingestion is incremental — and recompute only the silver materialized views.

```sql
SELECT substr(origin.update_id, 1, 8) AS update_id, regexp_extract(origin.flow_name, '([^.]+)$', 1) AS table_name,
       CAST(details:flow_progress.metrics.num_output_rows AS BIGINT) AS output_rows,
       CAST(details:flow_progress.data_quality.dropped_records AS BIGINT) AS dropped_rows
FROM event_log('c8a0222b-348b-413d-bb05-a0cda17c73d3')
WHERE event_type = 'flow_progress' AND details:flow_progress.metrics.num_output_rows IS NOT NULL
ORDER BY timestamp
```

Result — 13 row(s):

```text
update_id | table_name                   | output_rows | dropped_rows
----------+------------------------------+-------------+-------------
61b080b3  | bronze_schedule_float_weekly | 1040        | 0
61b080b3  | bronze_projects              | 40          | 0
61b080b3  | bronze_safety_observations   | 1082        | 0
61b080b3  | bronze_job_cost              | 5760        | 0
61b080b3  | bronze_change_orders         | 975         | 0
61b080b3  | bronze_submittals            | 1715        | 0
61b080b3  | bronze_project_signal_weekly | 6240        | 0
61b080b3  | bronze_rfis                  | 3540        | 0
61b080b3  | bronze_schedule_activities   | 960         | 0
61b080b3  | silver_projects              | 40          | 0
61b080b3  | silver_project_signal_weekly | 6240        | 0
a51bb91f  | silver_projects              | 40          | 0
a51bb91f  | silver_project_signal_weekly | 6240        | 0
```

### Data-quality expectations, per update (pipeline event log)

```sql
SELECT substr(origin.update_id, 1, 8) AS update_id, regexp_extract(origin.flow_name, '([^.]+)$', 1) AS table_name,
       e.name AS expectation, e.passed_records AS passed, e.failed_records AS failed
FROM (SELECT origin, timestamp, explode(from_json(details:flow_progress.data_quality.expectations,
             'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS e
      FROM event_log('c8a0222b-348b-413d-bb05-a0cda17c73d3')
      WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL)
ORDER BY timestamp, table_name, expectation
```

Result — 20 row(s):

```text
update_id | table_name                   | expectation             | passed | failed
----------+------------------------------+-------------------------+--------+-------
61b080b3  | silver_projects              | pct_complete_in_range   | 40     | 0
61b080b3  | silver_projects              | positive_contract_value | 40     | 0
61b080b3  | silver_projects              | valid_project_id        | 40     | 0
61b080b3  | silver_projects              | valid_region            | 40     | 0
61b080b3  | silver_project_signal_weekly | known_signal            | 6240   | 0
61b080b3  | silver_project_signal_weekly | raw_value_present       | 6240   | 0
61b080b3  | silver_project_signal_weekly | sub_score_in_range      | 6240   | 0
61b080b3  | silver_project_signal_weekly | valid_project_id        | 6240   | 0
61b080b3  | silver_project_signal_weekly | valid_week              | 6240   | 0
61b080b3  | silver_project_signal_weekly | weight_in_range         | 6240   | 0
a51bb91f  | silver_projects              | pct_complete_in_range   | 40     | 0
a51bb91f  | silver_projects              | positive_contract_value | 40     | 0
a51bb91f  | silver_projects              | valid_project_id        | 40     | 0
a51bb91f  | silver_projects              | valid_region            | 40     | 0
a51bb91f  | silver_project_signal_weekly | known_signal            | 6240   | 0
a51bb91f  | silver_project_signal_weekly | raw_value_present       | 6240   | 0
a51bb91f  | silver_project_signal_weekly | sub_score_in_range      | 6240   | 0
a51bb91f  | silver_project_signal_weekly | valid_project_id        | 6240   | 0
a51bb91f  | silver_project_signal_weekly | valid_week              | 6240   | 0
a51bb91f  | silver_project_signal_weekly | weight_in_range         | 6240   | 0
```

### Event log of the latest completed update (a51bb91f)

```sql
SELECT date_format(timestamp, 'HH:mm:ss.SSS') AS time_utc, event_type, level, message
FROM event_log('c8a0222b-348b-413d-bb05-a0cda17c73d3')
WHERE origin.update_id = 'a51bb91f-5b2d-496c-8278-138b78f9191a' AND event_type IN ('create_update', 'update_progress', 'flow_progress', 'dataset_life_cycle', 'planning_information')
ORDER BY timestamp
```

Result — 68 row(s):

```text
time_utc     | event_type           | level   | message
-------------+----------------------+---------+-----------------------------------------------------------------------------------------------------------------------------
19:27:37.913 | create_update        | INFO    | Update a51bb9 started by API_CALL.
19:27:39.983 | update_progress      | INFO    | Update a51bb9 is WAITING_FOR_RESOURCES.
19:27:51.828 | update_progress      | INFO    | Update a51bb9 is INITIALIZING.
19:28:04.804 | update_progress      | INFO    | Update a51bb9 is SETTING_UP_TABLES.
19:28:04.974 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_rfis` is active in the pipeline.
19:28:04.978 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_schedule_activities` is active in the pipeline.
19:28:04.984 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_change_orders` is active in the pipeline.
19:28:04.986 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_schedule_float_weekly` is active in the pipeline.
19:28:04.990 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_projects` is active in the pipeline.
19:28:04.991 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_job_cost` is active in the pipeline.
19:28:04.997 | dataset_life_cycle   | METRICS | Materialized View `bhambs`.`construction_control_tower`.`silver_projects` is active in the pipeline.
19:28:05.001 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_safety_observations` is active in the pipeline.
19:28:05.005 | dataset_life_cycle   | METRICS | Materialized View `bhambs`.`construction_control_tower`.`silver_project_signal_weekly` is active in the pipeline.
19:28:05.007 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_project_signal_weekly` is active in the pipeline.
19:28:05.008 | dataset_life_cycle   | METRICS | Streaming Table `bhambs`.`construction_control_tower`.`bronze_submittals` is active in the pipeline.
19:28:09.002 | update_progress      | INFO    | Update a51bb9 is RUNNING.
19:28:09.014 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_projects' is QUEUED.
19:28:09.018 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_project_signal_weekly' is QUEUED.
19:28:09.019 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_float_weekly' is QUEUED.
19:28:09.020 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_rfis' is QUEUED.
19:28:09.021 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_projects' is QUEUED.
19:28:09.023 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_safety_observations' is QUEUED.
19:28:09.024 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_project_signal_weekly' is QUEUED.
19:28:09.025 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_submittals' is QUEUED.
19:28:09.027 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_job_cost' is QUEUED.
19:28:09.028 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_change_orders' is QUEUED.
19:28:09.030 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_activities' is QUEUED.
19:28:09.229 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_float_weekly' is STARTING.
19:28:14.669 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_float_weekly' is RUNNING.
19:28:15.161 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_projects' is STARTING.
19:28:15.659 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_projects' is RUNNING.
19:28:15.983 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_job_cost' is STARTING.
19:28:16.393 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_job_cost' is RUNNING.
19:28:16.583 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_change_orders' is STARTING.
19:28:16.992 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_change_orders' is RUNNING.
19:28:17.167 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_safety_observations' is STARTING.
19:28:17.570 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_safety_observations' is RUNNING.
19:28:17.771 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_submittals' is STARTING.
19:28:18.346 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_submittals' is RUNNING.
19:28:18.514 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_project_signal_weekly' is STARTING.
19:28:18.976 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_projects' has COMPLETED.
19:28:18.988 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_float_weekly' has COMPLETED.
19:28:18.990 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_project_signal_weekly' is RUNNING.
19:28:18.993 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_job_cost' has COMPLETED.
19:28:19.161 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_rfis' is STARTING.
19:28:19.416 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_change_orders' has COMPLETED.
19:28:19.557 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_rfis' is RUNNING.
19:28:19.801 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_activities' is STARTING.
19:28:19.990 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_safety_observations' has COMPLETED.
19:28:20.206 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_activities' is RUNNING.
19:28:20.786 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_submittals' has COMPLETED.
19:28:21.396 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_project_signal_weekly' has COMPLETED.
19:28:22.019 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_rfis' has COMPLETED.
19:28:22.306 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_projects' is PLANNING.
19:28:22.689 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.bronze_schedule_activities' has COMPLETED.
19:28:25.238 | planning_information | INFO    | Flow 'bhambs.construction_control_tower.silver_projects' has been planned to be executed as COMPLETE_RECOMPUTE.
19:28:25.274 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_projects' is STARTING.
19:28:25.430 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_projects' is RUNNING.
19:28:26.350 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_project_signal_weekly' is PLANNING.
19:28:28.144 | planning_information | INFO    | Flow 'bhambs.construction_control_tower.silver_project_signal_weekly' has been planned to be executed as COMPLETE_RECOMPUTE.
19:28:28.147 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_project_signal_weekly' is STARTING.
19:28:28.179 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_project_signal_weekly' is RUNNING.
19:28:31.137 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_projects' has COMPLETED.
19:28:31.995 | flow_progress        | INFO    | Flow 'bhambs.construction_control_tower.silver_project_signal_weekly' has COMPLETED.
19:28:32.028 | flow_progress        | METRICS | Reported flow time metrics for flowName: 'bhambs.construction_control_tower.silver_projects'.
19:28:32.043 | flow_progress        | METRICS | Reported flow time metrics for flowName: 'bhambs.construction_control_tower.silver_project_signal_weekly'.
19:28:32.045 | flow_progress        | METRICS | Reported flow time metrics for flowName: 'pipelines.flowTimeMetrics.missingFlowName'.
19:28:32.050 | update_progress      | INFO    | Update a51bb9 is COMPLETED.
```

### Bronze keeps the source file and ingest time on every row

```sql
SELECT 'bronze_projects' AS table_name, regexp_extract(_source_file, '(/Volumes/.*)$', 1) AS source_file, COUNT(*) AS row_count, MIN(_ingested_at) AS ingested_at FROM bronze_projects GROUP BY ALL
UNION ALL SELECT 'bronze_project_signal_weekly', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_project_signal_weekly GROUP BY ALL
UNION ALL SELECT 'bronze_rfis', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_rfis GROUP BY ALL
UNION ALL SELECT 'bronze_change_orders', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_change_orders GROUP BY ALL
UNION ALL SELECT 'bronze_submittals', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_submittals GROUP BY ALL
UNION ALL SELECT 'bronze_schedule_activities', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_schedule_activities GROUP BY ALL
UNION ALL SELECT 'bronze_schedule_float_weekly', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_schedule_float_weekly GROUP BY ALL
UNION ALL SELECT 'bronze_job_cost', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_job_cost GROUP BY ALL
UNION ALL SELECT 'bronze_safety_observations', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_safety_observations GROUP BY ALL
```

Result — 9 row(s):

```text
table_name                   | source_file                                                                     | row_count | ingested_at
-----------------------------+---------------------------------------------------------------------------------+-----------+-------------------------
bronze_projects              | /Volumes/bhambs/construction_control_tower/raw/v1/projects.parquet              | 40        | 2026-11-23T16:53:09.336Z
bronze_project_signal_weekly | /Volumes/bhambs/construction_control_tower/raw/v1/project_signal_weekly.parquet | 6240      | 2026-11-23T16:53:12.867Z
bronze_rfis                  | /Volumes/bhambs/construction_control_tower/raw/v1/rfis.parquet                  | 3540      | 2026-11-23T16:53:13.613Z
bronze_change_orders         | /Volumes/bhambs/construction_control_tower/raw/v1/change_orders.parquet         | 975       | 2026-11-23T16:53:10.275Z
bronze_submittals            | /Volumes/bhambs/construction_control_tower/raw/v1/submittals.parquet            | 1715      | 2026-11-23T16:53:12.043Z
bronze_schedule_activities   | /Volumes/bhambs/construction_control_tower/raw/v1/schedule_activities.parquet   | 960       | 2026-11-23T16:53:14.527Z
bronze_schedule_float_weekly | /Volumes/bhambs/construction_control_tower/raw/v1/schedule_float_weekly.parquet | 1040      | 2026-11-23T16:53:09.336Z
bronze_job_cost              | /Volumes/bhambs/construction_control_tower/raw/v1/job_cost.parquet              | 5760      | 2026-11-23T16:53:09.648Z
bronze_safety_observations   | /Volumes/bhambs/construction_control_tower/raw/v1/safety_observations.parquet   | 1082      | 2026-11-23T16:53:11.152Z
```

### Sample rows — silver_project_signal_weekly (Project Atlas, latest week)

```sql
SELECT project_id, week, signal, sub_score, raw_value, weight
FROM silver_project_signal_weekly WHERE project_id = 'P-1001' AND week = DATE'2026-11-09' ORDER BY signal
```

Result — 6 row(s):

```text
project_id | week       | signal    | sub_score | raw_value | weight
-----------+------------+-----------+-----------+-----------+-------
P-1001     | 2026-11-09 | co        | 83.9      | 2080000.0 | 0.2
P-1001     | 2026-11-09 | cost      | 69.0      | 0.069     | 0.25
P-1001     | 2026-11-09 | rfi       | 88.2      | 14.0      | 0.15
P-1001     | 2026-11-09 | safety    | 56.0      | 4.0       | 0.1
P-1001     | 2026-11-09 | schedule  | 71.2      | 4.8       | 0.2
P-1001     | 2026-11-09 | submittal | 60.0      | 6.0       | 0.1
```
