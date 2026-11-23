# Stage 5 — Genie Agent: make it queryable in natural language

Three Genie Agents sit on the governed data: Portfolio Risk (over the risk metric view fed by the Lakeflow pipeline), Project Controls (margin) and Jobsite Safety. Questions below were sent through the Genie Conversation API. The same question asked by different identities returns different rows, because Genie runs as the asker and Unity Catalog row filters apply.

Captured 2026-11-23 19:39 UTC by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.

### Control Tower — Portfolio Risk  ·  asked as: Presenter (ops leadership)

**Question:** Which projects need attention this week, and what's driving it?

Status: COMPLETED in 26s

**Genie's description:** You're asking to see which projects currently need attention this week based on their risk scores, and you want to know the main factor driving that risk for each project.

**SQL Genie wrote:**

```sql
WITH `attention_projects` AS (
  SELECT
    `project_id`,
    `project_name`,
    `market_sector`,
    `region`,
    MEASURE(`risk_score`) AS `risk_score`
  FROM `bhambs`.`construction_control_tower`.`project_risk_mv`
  WHERE `weeks_ago` = 0
    AND `project_id` IS NOT NULL
    AND `project_name` IS NOT NULL
    AND `market_sector` IS NOT NULL
    AND `region` IS NOT NULL
  GROUP BY ALL
  HAVING `risk_score` >= 55
),
`drivers` AS (
  SELECT
    `project_id`,
    `signal`,
    MEASURE(`risk_score`) AS `signal_points`,
    MEASURE(`signal_raw_value`) AS `signal_raw_value`
  FROM `bhambs`.`construction_control_tower`.`project_risk_mv`
  WHERE `weeks_ago` = 0
    AND `project_id` IS NOT NULL
    AND `signal` IS NOT NULL
  GROUP BY ALL
),
`ranked_drivers` AS (
  SELECT
    `project_id`,
    `signal`,
    `signal_points`,
    `signal_raw_value`,
    ROW_NUMBER() OVER (PARTITION BY `project_id` ORDER BY `signal_points` DESC, `signal` ASC) AS `driver_rank`
  FROM `drivers`
)
SELECT
  a.`project_name`,
  a.`market_sector`,
  a.`region`,
  a.`risk_score`,
  d.`signal` AS `top_driver_signal`,
  d.`signal_points` AS `top_driver_points`,
  d.`signal_raw_value` AS `top_driver_raw_value`
FROM `attention_projects` a
LEFT JOIN `ranked_drivers` d
  ON a.`project_id` = d.`project_id`
 AND d.`driver_rank` = 1
ORDER BY a.`risk_score` DESC, a.`project_name` ASC
```

**Rows returned — 5:**

```text
project_name                               | market_sector | region    | risk_score         | top_driver_signal | top_driver_points  | top_driver_raw_value
-------------------------------------------+---------------+-----------+--------------------+-------------------+--------------------+---------------------
Project Atlas — Data Center Campus, Bldg 3 | Data Center   | Northeast | 73.10000000000001  | cost              | 17.25              | 0.069
Project Helios — Hyperscale DC Phase 2     | Data Center   | Southwest | 64.655             | schedule          | 16.400000000000002 | 3.0
Project Vega — AI Data Hall                | Data Center   | Midwest   | 63.00999999999999  | cost              | 18.4               | 0.0736
One Market Plaza Renovation                | Commercial    | Southeast | 56.625             | cost              | 15.675             | 0.0627
Project Meridian — Regional Medical Center | Healthcare    | Midwest   | 55.370000000000005 | cost              | 19.3               | 0.0772
```
**Answer:**

```text
**Five projects need attention this week**. Examples include:
- **Project Atlas — Data Center Campus, Bldg 3** (Northeast, Data Center): **73.1** risk score, driven most by **cost** at **17.3 points** from **EAC 6.9% over budget**.
- **Project Helios — Hyperscale DC Phase 2** (Southwest, Data Center): **64.7** risk score, driven most by **schedule** at **16.4 points** with **3.0 days of critical-path float left**.
- **Project Vega — AI Data Hall** (Midwest, Data Center): **63.0** risk score, driven most by **cost** at **18.4 points** from **EAC 7.4% over budget**.
- **One Market Plaza Renovation** (Southeast, Commercial): **56.6** risk score, driven most by **cost** at **15.7 points** from **EAC 6.3% over budget**.
- **Project Meridian — Regional Medical Center** (Midwest, Healthcare): **55.4** risk score, driven most by **cost** at **19.3 points** from **EAC 7.7% over budget**.
Across these projects, **cost is the main driver in 4 of 5 cases**, while **schedule** is the top issue only for **Helios**.
```


### Control Tower — Portfolio Risk  ·  asked as: Presenter (ops leadership)

**Question:** Why did Project Atlas's risk score go up over the last 8 weeks?

Status: COMPLETED in 26s

**Genie's description:** You want to see which risk signals contributed to the increase in Project Atlas's risk score over the last 8 weeks.

**SQL Genie wrote:**

```sql
SELECT
  `signal`,
  MEASURE(`risk_score`) FILTER (WHERE `weeks_ago` = 0) AS `pts_now`,
  MEASURE(`risk_score`) FILTER (WHERE `weeks_ago` = 8) AS `pts_8w_ago`,
  MEASURE(`risk_score`) FILTER (WHERE `weeks_ago` = 0) - MEASURE(`risk_score`) FILTER (WHERE `weeks_ago` = 8) AS `pt_change`,
  MEASURE(`signal_raw_value`) FILTER (WHERE `weeks_ago` = 0) AS `raw_now`,
  MEASURE(`signal_raw_value`) FILTER (WHERE `weeks_ago` = 8) AS `raw_8w_ago`
FROM `bhambs`.`construction_control_tower`.`project_risk_mv`
WHERE `project_name` ILIKE '%Atlas%'
  AND `weeks_ago` IN (0, 8)
  AND `signal` IS NOT NULL
GROUP BY ALL
ORDER BY `pt_change` DESC
```

**Rows returned — 6:**

```text
signal    | pts_now            | pts_8w_ago         | pt_change           | raw_now   | raw_8w_ago
----------+--------------------+--------------------+---------------------+-----------+-----------
rfi       | 13.23              | 5.669999999999999  | 7.560000000000001   | 14.0      | 6.0
cost      | 17.25              | 10.45              | 6.800000000000001   | 0.069     | 0.0418
schedule  | 14.240000000000002 | 8.840000000000002  | 5.4                 | 4.8       | 9.3
safety    | 5.6000000000000005 | 2.8000000000000003 | 2.8000000000000003  | 4.0       | 2.0
submittal | 6.0                | 4.0                | 2.0                 | 6.0       | 4.0
co        | 16.78              | 17.86              | -1.0799999999999983 | 2080000.0 | 2213700.0
```
**Answer:**

```text
Project Atlas’s risk score went up over the last 8 weeks mainly because **older RFIs**, **cost pressure**, and **schedule deterioration** all worsened, while only **pending change-order exposure** improved slightly. Examples include:
- **RFI risk** rose by **7.6 points**, from **6** to **14 open RFIs older than 21 days**.
- **Cost risk** rose by **6.8 points**, from **4.2%** to **6.9% over budget**.
- **Schedule risk** rose by **5.4 points**, as critical-path float fell from **9.3 days** to **4.8 days**.
- **Safety risk** rose by **2.8 points**, from **2** to **4 observations/near-misses in the last 14 days**.
- **Submittal risk** rose by **2.0 points**, from **4** to **6 overdue submittals**.
Across all **6 signals**, the biggest increases came from RFIs and cost, which more than offset the modest improvement in change orders.
```


### Control Tower — Portfolio Risk  ·  asked as: Presenter (ops leadership)

**Question:** Which open RFIs on Project Atlas are tied to critical-path activities?

Status: COMPLETED in 19s

**Genie's description:** You want to see all open RFIs for Project Atlas that are linked to critical-path activities, including details like RFI ID, subject, activity name, and planned start and finish dates, ordered by the planned start date.

**SQL Genie wrote:**

```sql
SELECT `r`.`rfi_id`, `r`.`subject`, `s`.`activity_id`, `s`.`activity_name`, `s`.`planned_start`, `s`.`planned_finish`, `s`.`total_float_days`
FROM `bhambs`.`construction_control_tower`.`rfis` AS `r`
INNER JOIN `bhambs`.`construction_control_tower`.`schedule_activities` AS `s`
  ON `r`.`activity_id` = `s`.`activity_id`
INNER JOIN `bhambs`.`construction_control_tower`.`projects` AS `p`
  ON `r`.`project_id` = `p`.`project_id`
WHERE `p`.`name` ILIKE '%Atlas%'
  AND `r`.`status` = 'Open'
  AND `s`.`critical_flag` = true
  AND `s`.`planned_start` IS NOT NULL
ORDER BY `s`.`planned_start` ASC
```

**Rows returned — 9:**

```text
rfi_id   | subject                            | activity_id | activity_name                    | planned_start | planned_finish | total_float_days
---------+------------------------------------+-------------+----------------------------------+---------------+----------------+-----------------
RFI-0106 | Standpipe location                 | A101        | Elevated deck pour               | 2026-09-25    | 2026-10-04     | 0
RFI-0103 | Standpipe location                 | A101        | Elevated deck pour               | 2026-09-25    | 2026-10-04     | 0
RFI-0104 | Panel location conflict            | A100        | Feeder pulls                     | 2026-10-03    | 2026-11-06     | 1
RFI-0110 | Sprinkler head layout vs. ceiling  | A100        | Feeder pulls                     | 2026-10-03    | 2026-11-06     | 1
RFI-0391 | Duct bank routing vs. footing F-12 | A109        | Duct bank trenching - north yard | 2026-11-11    | 2026-11-21     | 2
RFI-0352 | Rock at pile caps PC-14–22         | A115        | Pile caps PC-14 to PC-22         | 2026-11-13    | 2026-11-23     | 4
RFI-0387 | Embed plate conflict at L2 beam    | A105        | Steel erection L2 (grid B)       | 2026-11-16    | 2026-11-26     | 0
RFI-0109 | Medical gas outlet count           | A105        | Steel erection L2 (grid B)       | 2026-11-16    | 2026-11-26     | 0
RFI-0114 | Utility crossing depth             | A103        | Mass excavation                  | 2026-12-14    | 2027-01-20     | 8
```
**Answer:**

```text
Project Atlas has **9 open RFIs** tied to activities marked critical in the schedule. Examples include:
- **RFI-0106** — **Standpipe location** on **Elevated deck pour** (starts **2026-09-25**, float **0 days**)
- **RFI-0103** — **Standpipe location** on **Elevated deck pour** (starts **2026-09-25**, float **0 days**)
- **RFI-0104** — **Panel location conflict** on **Feeder pulls** (starts **2026-10-03**, float **1 day**)
- **RFI-0110** — **Sprinkler head layout vs. ceiling** on **Feeder pulls** (starts **2026-10-03**, float **1 day**)
- **RFI-0391** — **Duct bank routing vs. footing F-12** on **Duct bank trenching - north yard** (starts **2026-11-11**, float **2 days**)
The most time-sensitive items are on **Elevated deck pour** and **Steel erection L2 (grid B)**, both showing **0 days of float**.
```


### Control Tower — Portfolio Risk  ·  asked as: Northeast PM (simulated)

**Question:** How many projects can I see, and which one has the highest risk score this week?

Status: COMPLETED in 21s

**Genie's description:** You want to know the total number of projects available and identify which project has the highest risk score for the current week.

**SQL Genie wrote:**

```sql
WITH `project_scores` AS (
  SELECT
    `project_id`,
    `project_name`,
    MEASURE(`risk_score`) AS `risk_score`
  FROM `bhambs`.`construction_control_tower`.`project_risk_mv`
  WHERE `weeks_ago` = 0
    AND `project_id` IS NOT NULL
    AND `project_name` IS NOT NULL
  GROUP BY ALL
), `project_count` AS (
  SELECT COUNT(*) AS `project_count`
  FROM `project_scores`
), `ranked` AS (
  SELECT
    `project_name`,
    `risk_score`,
    RANK() OVER (ORDER BY `risk_score` DESC) AS `risk_rank`
  FROM `project_scores`
  WHERE `risk_score` IS NOT NULL
)
SELECT
  c.`project_count`,
  r.`project_name`,
  r.`risk_score`
FROM `project_count` c
CROSS JOIN `ranked` r
WHERE r.`risk_rank` = 1
```

**Rows returned — 1:**

```text
project_count | project_name                               | risk_score
--------------+--------------------------------------------+------------------
11            | Project Atlas — Data Center Campus, Bldg 3 | 73.10000000000001
```
**Answer:**

```text
You can see **11 projects** this week. The project with the highest risk score this week is **Project Atlas — Data Center Campus, Bldg 3** with a risk score of **73.1**, which puts **Project Atlas — Data Center Campus, Bldg 3** in the **Critical** risk band.
```


### Control Tower — Portfolio Risk  ·  asked as: Atlas superintendent (simulated)

**Question:** How many projects can I see, and which one has the highest risk score this week?

Status: COMPLETED in 19s

**Genie's description:** You want to know how many projects are visible in the data this week and which project has the highest risk score among them.

**SQL Genie wrote:**

```sql
WITH `project_scores` AS (
  SELECT
    `project_id`,
    `project_name`,
    MEASURE(`risk_score`) AS `risk_score`
  FROM `bhambs`.`construction_control_tower`.`project_risk_mv`
  WHERE `weeks_ago` = 0
    AND `project_id` IS NOT NULL
    AND `project_name` IS NOT NULL
  GROUP BY ALL
), `ranked_projects` AS (
  SELECT
    `project_id`,
    `project_name`,
    `risk_score`,
    RANK() OVER (ORDER BY `risk_score` DESC) AS `risk_rank`
  FROM `project_scores`
), `project_count` AS (
  SELECT COUNT(*) AS `visible_project_count`
  FROM `project_scores`
)
SELECT
  pc.`visible_project_count`,
  rp.`project_id`,
  rp.`project_name`,
  rp.`risk_score`
FROM `ranked_projects` rp
CROSS JOIN `project_count` pc
WHERE rp.`risk_rank` = 1
```

**Rows returned — 1:**

```text
visible_project_count | project_id | project_name                               | risk_score
----------------------+------------+--------------------------------------------+------------------
1                     | P-1001     | Project Atlas — Data Center Campus, Bldg 3 | 73.10000000000001
```
**Answer:**

```text
You can see **1 project** this week. The project with the highest risk score this week is **Project Atlas — Data Center Campus, Bldg 3** (project ID **P-1001**) with a risk score of **73.1**, which is also the only visible project.
```


### Control Tower — Project Controls (Margin)  ·  asked as: Presenter (ops leadership)

**Question:** Which projects are breaching the margin fade threshold, and by how much?

Status: COMPLETED in 18s

**Genie's description:** You want to see the list of projects that are currently breaching the margin fade threshold, including details like project name, region, bid margin percentage, projected margin percentage, margin fade in points and dollars, and the percentage of contingency and buyout savings used.

**SQL Genie wrote:**

```sql
SELECT
  `project_name`,
  `region`,
  MEASURE(`bid_margin_pct`) AS `bid_margin_pct`,
  MEASURE(`projected_margin_pct`) AS `projected_margin_pct`,
  MEASURE(`margin_fade_pts`) AS `margin_fade_pts`,
  MEASURE(`margin_fade_usd`) AS `margin_fade_usd`,
  MEASURE(`cushion_used_pct`) AS `cushion_used_pct`
FROM `bhambs`.`construction_control_tower`.`project_margin_mv`
WHERE `months_ago` = 0
  AND `breaching_threshold` = TRUE
  AND `project_name` IS NOT NULL
GROUP BY ALL
HAVING `margin_fade_pts` IS NOT NULL
ORDER BY `margin_fade_pts` DESC
```

**Rows returned — 3:**

```text
project_name                               | region    | bid_margin_pct | projected_margin_pct | margin_fade_pts | margin_fade_usd      | cushion_used_pct
-------------------------------------------+-----------+----------------+----------------------+-----------------+----------------------+-----------------
Project Meridian — Regional Medical Center | Midwest   | 7.25           | 4.63                 | 2.62            | 1.4082343599999983E7 | 100.0
Project Atlas — Data Center Campus, Bldg 3 | Northeast | 5.53           | 3.11                 | 2.42            | 2.987913600000003E7  | 100.0
Project Vega — AI Data Hall                | Midwest   | 6.09           | 3.86                 | 2.23            | 1.681333939999997E7  | 100.0
```
**Answer:**

```text
**3 projects** are currently breaching the margin fade threshold in the latest WIP period, and all three have **100.0%** of cushion used.
- **Project Meridian — Regional Medical Center**: **2.6 points** of margin fade, about **$14.1M**
- **Project Atlas — Data Center Campus, Bldg 3**: **2.4 points** of margin fade, about **$29.9M**
- **Project Vega — AI Data Hall**: **2.2 points** of margin fade, about **$16.8M**
**Meridian** has the largest fade in points, while **Atlas** has the largest dollar impact.
```


### Control Tower — Jobsite Safety  ·  asked as: Presenter (ops leadership)

**Question:** How many near-misses were recorded on Project Atlas in the last 14 days, by category?

Status: COMPLETED in 28s

**Genie's description:** You want to see the number of near-miss safety observations recorded in the last 14 days for Project Atlas, broken down by category.

**SQL Genie wrote:**

```sql
SELECT `s`.`category`, COUNT(*) AS `near_miss_count` FROM `bhambs`.`construction_control_tower`.`safety_observations` AS `s` INNER JOIN `bhambs`.`construction_control_tower`.`projects` AS `p` ON `s`.`project_id` = `p`.`project_id` WHERE `p`.`name` ILIKE '%Atlas%' AND `s`.`near_miss_flag` = TRUE AND `s`.`date` BETWEEN date_sub(DATE '2026-11-09', 13) AND DATE '2026-11-09' AND `s`.`category` IS NOT NULL GROUP BY `s`.`category` ORDER BY `near_miss_count` DESC, `s`.`category`
```

**Rows returned — 1:**

```text
category        | near_miss_count
----------------+----------------
Fall protection | 2
```
**Answer:**

```text
Project Atlas recorded **2** near-misses in the last 14 days, all in the category **Fall protection**. Based on the visible result, **Fall protection** is the only near-miss category returned for Project Atlas in that period.
```
