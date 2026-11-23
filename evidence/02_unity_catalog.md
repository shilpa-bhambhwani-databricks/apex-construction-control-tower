# Stage 2 — Unity Catalog: govern it

One schema holds the whole dataset: tables, pipeline tables, volumes, functions and metric views. A single row filter decides which projects each identity can see, and it is attached at every layer. The risk score is defined once, as a metric view, and that one definition is what the app, the agents and Genie all use.

Captured 2026-11-23 19:38 UTC by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.

### Everything lives in one governed schema

```sql
SELECT table_type, COUNT(*) AS objects, concat_ws(', ', sort_array(collect_list(table_name))) AS names
FROM bhambs.information_schema.tables WHERE table_schema = 'construction_control_tower' GROUP BY table_type ORDER BY objects DESC
```

Result — 6 row(s):

```text
table_type        | objects | names
------------------+---------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
MANAGED           | 41      | __2959319a_a5ae_4dec_ad2d_d492b4e3b67f___online_index_view, __materialization_mat_c8a0222b_348b_413d_bb05_a0cda17c73d3_bronze_change_orders_1, __materialization_mat_c8a0222b_348b_413d_bb05_a0cda17c73d3_bronze_job_cost_1, __materialization_mat_c8a0222b_348b_413d_bb05_a0cda17c73d3_bronze_project_signal_weekly_1, __materialization_mat_c8a0222b_348b_413d_bb05_a0cda17c73d3_bronze_projects_1, __materialization_mat_c8a0222b
STREAMING_TABLE   | 9       | bronze_change_orders, bronze_job_cost, bronze_project_signal_weekly, bronze_projects, bronze_rfis, bronze_safety_observations, bronze_schedule_activities, bronze_schedule_float_weekly, bronze_submittals
MATERIALIZED_VIEW | 2       | silver_project_signal_weekly, silver_projects
METRIC_VIEW       | 2       | project_margin_mv, project_risk_mv
VIEW              | 1       | project_margin_monthly
FOREIGN           | 1       | doc_chunks_index
```

### Volumes (raw landing zone, documents, field photos)

```sql
SELECT volume_name, volume_type, comment FROM bhambs.information_schema.volumes WHERE volume_schema = 'construction_control_tower' ORDER BY 1
```

Result — 4 row(s):

```text
volume_name       | volume_type | comment
------------------+-------------+---------------------------------------------------------------------------------------------------------------
documents         | MANAGED     | Synthetic project documents for Resolve (contracts, subcontracts, specs, daily logs, letters)
field_photos      | MANAGED     | Field photos uploaded from Jobsite Intelligence (part of the project record)
finance_documents | MANAGED     | Demo 2 (CFO margin fade) evidence: supplier price notices, invoices, freight notices, contract excerpts, cost
raw               | MANAGED     | Landing zone for generated synthetic data
```

### Row filter attached to every project-scoped table — including the Lakeflow bronze and silver tables

```sql
SELECT table_name, regexp_extract(filter_name, '([^.]+)$', 1) AS row_filter, target_columns
FROM bhambs.information_schema.row_filters WHERE table_schema = 'construction_control_tower' ORDER BY table_name
```

Result — 30 row(s):

```text
table_name                   | row_filter   | target_columns
-----------------------------+--------------+---------------
bronze_change_orders         | ct_row_scope | project_id
bronze_job_cost              | ct_row_scope | project_id
bronze_project_signal_weekly | ct_row_scope | project_id
bronze_projects              | ct_row_scope | project_id
bronze_rfis                  | ct_row_scope | project_id
bronze_safety_observations   | ct_row_scope | project_id
bronze_schedule_activities   | ct_row_scope | project_id
bronze_schedule_float_weekly | ct_row_scope | project_id
bronze_submittals            | ct_row_scope | project_id
change_order_lines           | ct_row_scope | project_id
change_orders                | ct_row_scope | project_id
cost_variance_log            | ct_row_scope | project_id
finance_doc_chunks           | ct_row_scope | project_id
job_cost                     | ct_row_scope | project_id
jobsite_crews                | ct_row_scope | project_id
jobsite_day                  | ct_row_scope | project_id
jobsite_events               | ct_row_scope | project_id
jobsite_lookahead            | ct_row_scope | project_id
project_financials           | ct_row_scope | project_id
project_signal_weekly        | ct_row_scope | project_id
projects                     | ct_row_scope | project_id
purchase_orders              | ct_row_scope | project_id
rfis                         | ct_row_scope | project_id
safety_observations          | ct_row_scope | project_id
schedule_activities          | ct_row_scope | project_id
schedule_float_weekly        | ct_row_scope | project_id
silver_project_signal_weekly | ct_row_scope | project_id
silver_projects              | ct_row_scope | project_id
submittals                   | ct_row_scope | project_id
vendor_invoice_lines         | ct_row_scope | project_id
```

### The row filter function

```sql
SELECT routine_name, routine_definition FROM bhambs.information_schema.routines
WHERE routine_schema = 'construction_control_tower' AND routine_name = 'ct_row_scope'
```

Result — 1 row(s):

```text
routine_name | routine_definition
-------------+----------------------------------------------------------------------------------------------------------------------------------------------------------
ct_row_scope | EXISTS (SELECT 1 FROM bhambs.construction_control_tower.access_scope a WHERE a.principal = current_user() AND (a.project_id = '*' OR a.project_id = pid))
```

### Who is mapped to which projects (access_scope)

```sql
SELECT persona, COUNT(*) AS mapped_projects, MAX(CASE WHEN project_id = '*' THEN 'all projects' ELSE 'listed projects only' END) AS scope
FROM access_scope GROUP BY persona ORDER BY 2 DESC
```

Result — 3 row(s):

```text
persona                          | mapped_projects | scope
---------------------------------+-----------------+---------------------
Northeast PM (simulated)         | 11              | listed projects only
Atlas superintendent (simulated) | 1               | listed projects only
Ops leadership                   | 1               | all projects
```

### Governed tools the agents call (Unity Catalog functions)

```sql
SELECT routine_name, left(comment, 150) AS comment FROM bhambs.information_schema.routines
WHERE routine_schema = 'construction_control_tower' ORDER BY 1
```

Result — 3 row(s):

```text
routine_name           | comment
-----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------
ct_row_scope           | Row filter: a row is visible if the current user is mapped to its project (or to *) in access_scope.
get_change_order       | Resolve tool: change order header + line items (Clearstory). Row-filtered: only COs on projects the caller can see.
get_unit_cost_baseline | Resolve tool: trailing-24-month awarded unit-rate benchmark for a cost code + region + item keywords (every word must match; P25 / median / P75 and sa
```

### Metric view definition — one governed definition of the risk score, sourced from the Lakeflow silver tables

```sql
SHOW CREATE TABLE project_risk_mv
```

Result — 1 row(s):

```text
createtab_stmt
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
CREATE VIEW bhambs.construction_control_tower.project_risk_mv ( ⏎   project_id, ⏎   project_name COMMENT 'Project name, e.g. Project Atlas — Data Center Campus, Bldg 3', ⏎   market_sector COMMENT 'Data Center, Healthcare, Aviation, Commercial, Education', ⏎   region, ⏎   business_unit, ⏎   pct_complete, ⏎   week COMMENT 'Week-ending snapshot date (weekly, Mondays). Latest week is 2026-11-09.', ⏎   weeks_ago COMMENT '0 = current week, 8 = eight weeks ago. Use weeks_ago = 0 for \'this week\'.', ⏎   signal COMMENT 'rfi = open RFIs aging > 21 days; co = pending change-order exposure; submittal = overdue submittals; schedule = critical-path float consumed (P6); cost = EAC vs budget (SAP); safety = near-misses/observations trailing 14 days', ⏎   risk_score COMMENT 'Project Risk Score 0-100 = weighted sum of six signal sub-scores (weights rfi .15, co .20, submittal .10, schedule .20, cost .25, safety .10). Averaged across projects when grouped above project level. Grouped by signal it gives that signal\'s contribution in points.', ⏎   signal_sub_score COMMENT 'Signal sub-score 0-100 (higher = more risk). Group by signal.', ⏎   signal_raw_value COMMENT 'Underlying raw value of the signal: aging RFI count, pending CO dollars, overdue submittal count, float days, EAC overrun fraction, or 14-day observation count.', ⏎   project_count) ⏎ COMMENT 'Single definition of the Control Tower Project Risk Score (0-100) and its six signals. Used by the app, Genie, and MCP. Sources are the quality-checked silver tables built by the Lakeflow pipeline construction-control-tower-ingest. Data as of 2026-11-09 (synthetic).' ⏎ WITH METRICS ⏎ LANGUAGE YAML ⏎ AS ⏎ $$ ⏎ version: 1.1 ⏎  ⏎ source: bhambs.construction_control_tower.silver_project_signal_weekly ⏎  ⏎ joins: ⏎   - name: p ⏎     source: bhambs.construction_control_tower.silver_projects ⏎     "on": source.project_id = p.project_id ⏎  ⏎ comment: "Single definition of the Control Tower Project Risk Score (0-100) and its\ ⏎   \ six signals. Used by the app, Genie, and MCP. Sources are the quality-checked\ ⏎   \ silver tables built by the Lakeflow pipeline construction-control-tower-ingest.\ ⏎   \ Data as of 2026-11-09 (synthetic)." ⏎  ⏎ dimensions: ⏎   - name: project_id ⏎     expr: source.project_id ⏎  ⏎   - name: project_name ⏎     expr: p.name ⏎     comment: "Project name, e.g. Project Atlas — Data Center Campus, Bldg 3" ⏎  ⏎   - name: market_sector ⏎     expr: p.market_sector ⏎     comment: "Data Center, Healthcare, Aviation, Commercial, Education" ⏎  ⏎   - name: region ⏎     expr: p.region ⏎  ⏎   - name: business_unit ⏎     expr: p.business_unit ⏎  ⏎   - name: pct_complete ⏎     expr: p.pct_complete ⏎  ⏎   - name: week ⏎     expr: source.week ⏎     comment: "Week-ending snapshot date (weekly, Mondays). Latest week is 2026-11-09." ⏎  ⏎   - name: weeks_ago ⏎     expr: "CAST(datediff(DATE'2026-11-09', source.week) / 7 AS INT)" ⏎     comment: "0 = current week, 8 = eight weeks ago. Use weeks_ago = 0 for 'this week'." ⏎  ⏎   - name: signal ⏎     expr: source.signal ⏎     comment: rfi = open RFIs aging > 21 days; co = pending change-order exposure; ⏎       submittal = overdue submittals; schedule = critical-path float consumed (P6); ⏎       cost = EAC vs budget (SAP); safety = near-misses/observations trailing 14 days ⏎  ⏎ measures: ⏎   - name: risk_score ⏎     expr: "SUM(source.sub_score * source.weight) / COUNT(DISTINCT concat(source.project_id,\ ⏎       \ '|', CAST(source.week AS STRING)))" ⏎     comment: "Project Risk Score 0-100 = weighted sum of six signal sub-scores (weights\ ⏎       \ rfi .15, co .20, submittal .10, schedule .20, cost .25, safety .10). Averaged\ ⏎       \ across projects when grouped above project level. Grouped by signal it gives\ ⏎       \ that signal's contribution in points." ⏎  ⏎   - name: signal_sub_score ⏎     expr: AVG(source.sub_score) ⏎     comment: Signal sub-score 0-100 (higher = more risk). Group by signal. ⏎  ⏎   - name: signal_raw_value ⏎     expr: AVG(source.raw_value) ⏎     comment: "Underlying raw value of the signal: aging RFI count, pending CO dollars,\ ⏎       \ overdue submittal count, float days, EAC overrun fraction, or 14-day observation\ ⏎       \ count." ⏎  ⏎   - name: project_count ⏎     expr: COUNT(DISTINCT source.project_id) ⏎ $$ ⏎
```

### Risk score — top projects this week

```sql
SELECT project_name, market_sector, region, ROUND(MEASURE(risk_score)) AS risk_score
FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL ORDER BY risk_score DESC LIMIT 8
```

Result — 8 row(s):

```text
project_name                               | market_sector | region    | risk_score
-------------------------------------------+---------------+-----------+-----------
Project Atlas — Data Center Campus, Bldg 3 | Data Center   | Northeast | 73.0
Project Helios — Hyperscale DC Phase 2     | Data Center   | Southwest | 65.0
Project Vega — AI Data Hall                | Data Center   | Midwest   | 63.0
One Market Plaza Renovation                | Commercial    | Southeast | 57.0
Project Meridian — Regional Medical Center | Healthcare    | Midwest   | 55.0
Terminal C Modernization                   | Aviation      | Southeast | 54.0
Project Orion — Colocation Facility        | Data Center   | West      | 52.0
Bayfront Medical Office Building           | Healthcare    | Southeast | 49.0
```

### Risk score — what is driving Project Atlas

```sql
SELECT signal, ROUND(MEASURE(risk_score), 1) AS points_now, ROUND(MEASURE(signal_raw_value), 2) AS raw_value
FROM project_risk_mv WHERE project_name LIKE 'Project Atlas%' AND weeks_ago = 0 GROUP BY ALL ORDER BY points_now DESC
```

Result — 6 row(s):

```text
signal    | points_now | raw_value
----------+------------+----------
cost      | 17.3       | 0.07
co        | 16.8       | 2080000.0
schedule  | 14.2       | 4.8
rfi       | 13.2       | 14.0
submittal | 6.0        | 6.0
safety    | 5.6        | 4.0
```

### Risk score — Project Atlas, last 8 weeks

```sql
SELECT weeks_ago, ROUND(MEASURE(risk_score)) AS atlas_score
FROM project_risk_mv WHERE project_name LIKE 'Project Atlas%' AND weeks_ago <= 8 GROUP BY ALL ORDER BY weeks_ago DESC
```

Result — 9 row(s):

```text
weeks_ago | atlas_score
----------+------------
8         | 50.0
7         | 42.0
6         | 46.0
5         | 50.0
4         | 53.0
3         | 57.0
2         | 56.0
1         | 70.0
0         | 73.0
```

### Risk score — by market sector

```sql
SELECT market_sector, MEASURE(project_count) AS projects, ROUND(MEASURE(risk_score)) AS avg_risk
FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL ORDER BY avg_risk DESC
```

Result — 5 row(s):

```text
market_sector | projects | avg_risk
--------------+----------+---------
Data Center   | 8        | 50.0
Aviation      | 6        | 37.0
Healthcare    | 8        | 36.0
Education     | 9        | 32.0
Commercial    | 9        | 27.0
```

### Same queries, three identities — row-level security at every layer

`scripts/verify_personas.py` runs each check as the presenter and as two simulated identities (service principals).

```text
check                                             |       Presenter (ops leadership) |         Northeast PM (simulated) | Atlas superintendent (simulated)
--------------------------------------------------+----------------------------------+----------------------------------+---------------------------------
bronze_projects rows (Lakeflow streaming table)   |                               40 |                               11 |                                1
silver_projects rows (Lakeflow materialized view) |                               40 |                               11 |                                1
silver_project_signal_weekly distinct projects    |                               40 |                               11 |                                1
project_risk_mv: projects this week               |                               40 |                               11 |                                1
project_risk_mv: average risk score this week     |                             36.0 |                             33.0 |                             73.0
project_risk_mv: regions visible                  | Midwest, Northeast, Southeast, Southwest, West |                        Northeast |                        Northeast
rfis: open RFIs visible                           |                              436 |                              128 |                               18
```

### As: Presenter (ops leadership)

```sql
SELECT MEASURE(project_count) AS projects_visible, ROUND(MEASURE(risk_score)) AS avg_risk,
       concat_ws(', ', sort_array(collect_set(region))) AS regions
FROM project_risk_mv WHERE weeks_ago = 0
```

Result — 1 row(s):

```text
projects_visible | avg_risk | regions
-----------------+----------+-----------------------------------------------
40               | 36.0     | Midwest, Northeast, Southeast, Southwest, West
```

### As: Northeast PM (simulated)

```sql
SELECT MEASURE(project_count) AS projects_visible, ROUND(MEASURE(risk_score)) AS avg_risk,
       concat_ws(', ', sort_array(collect_set(region))) AS regions
FROM project_risk_mv WHERE weeks_ago = 0
```

Result — 1 row(s):

```text
projects_visible | avg_risk | regions
-----------------+----------+----------
11               | 33.0     | Northeast
```

### As: Atlas superintendent (simulated)

```sql
SELECT MEASURE(project_count) AS projects_visible, ROUND(MEASURE(risk_score)) AS avg_risk,
       concat_ws(', ', sort_array(collect_set(region))) AS regions
FROM project_risk_mv WHERE weeks_ago = 0
```

Result — 1 row(s):

```text
projects_visible | avg_risk | regions
-----------------+----------+----------
1                | 73.0     | Northeast
```

### Lineage recorded by Unity Catalog (table lineage API)

Raw volume files → bronze → silver → metric view, captured automatically.

```text
bronze_project_signal_weekly (STREAMING_TABLE)       -->  silver_project_signal_weekly
bronze_projects (STREAMING_TABLE)                    -->  silver_projects
project_signal_weekly (TABLE)                        -->  project_risk_mv
projects (TABLE)                                     -->  project_risk_mv
silver_project_signal_weekly                         -->  project_risk_mv (METRIC_VIEW)
silver_project_signal_weekly (TABLE)                 -->  project_risk_mv
silver_projects                                      -->  project_risk_mv (METRIC_VIEW)
silver_projects (TABLE)                              -->  project_risk_mv
```
