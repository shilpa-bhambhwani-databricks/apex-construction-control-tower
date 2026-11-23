# Stage 3 — Lakebase: operational serving

Lakebase (serverless Postgres) is the app's operational store. The lakehouse stays read-only for the app; every action a user takes — assigning a follow-up, notifying an owner, accepting or rejecting an agent recommendation — is a transactional write to Lakebase, keyed by the same `project_id` and item ids as the governed data, and read back on every page load. Queries below were run with `databricks psql`.

Captured 2026-11-23 19:36 UTC by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.

### Lakebase is serverless Postgres

```sql
select split_part(version(), ' on ', 1) as engine, current_database() as database
```

```text
engine           |      database       
----------------------------+---------------------
 PostgreSQL 17.12 (4d8000a) | databricks_postgres
(1 row)
```

### App-state tables

```sql
select table_name, count(*) as columns from information_schema.columns where table_schema = 'control_tower' group by table_name order by 1
```

```text
table_name   | columns 
---------------+---------
 decisions     |       8
 followups     |      11
 notifications |       8
(3 rows)
```

### Rows written by the app

```sql
select 'followups' as tbl, count(*) as rows, min(created_at)::date as first_write, max(created_at)::date as last_write from control_tower.followups union all select 'notifications', count(*), min(created_at)::date, max(created_at)::date from control_tower.notifications union all select 'decisions', count(*), min(created_at)::date, max(created_at)::date from control_tower.decisions
```

```text
tbl      | rows | first_write | last_write 
---------------+------+-------------+------------
 followups     |    3 | 2026-11-09  | 2026-11-09
 notifications |    6 | 2026-11-09  | 2026-11-09
 decisions     |    1 | 2026-11-18  | 2026-11-18
(3 rows)
```

### Follow-ups assigned from the Risk Radar (who assigned it is the signed-in or simulated identity)

```sql
select id, project_id, item_ref, owner, due_date, note, status, created_by, source, created_at from control_tower.followups order by id
```

```text
-[ RECORD 1 ]------------------------------------------------------------------
id         | 1
project_id | P-1001
item_ref   | RFI-0387
owner      | Structural engineer (EOR)
due_date   | 2026-11-12
note       | Blocks Thursday crane pick — need embed plate answer
status     | Open
created_by | <presenter>
source     | risk-radar
created_at | 2026-11-09 21:50:25.801759+00
-[ RECORD 2 ]------------------------------------------------------------------
id         | 2
project_id | P-1001
item_ref   | Crane pick Thu
owner      | Ironline Steel foreman
due_date   | 2026-11-11
note       | Confirm lift plan + wind limits
status     | Open
created_by | Dana Morales (simulated)
source     | risk-radar
created_at | 2026-11-09 21:55:07.482923+00
-[ RECORD 3 ]------------------------------------------------------------------
id         | 3
project_id | P-1001
item_ref   | CO-0142
owner      | Project controls
due_date   | 2026-11-12
note       | Review Keystone unit rate vs. Northeast median before Thursday OAC
status     | Open
created_by | <presenter>
source     | risk-radar
created_at | 2026-11-09 21:56:45.471262+00
```

### Notifications queued for each follow-up

```sql
select id, followup_id, recipient, channel, title, status from control_tower.notifications order by id
```

```text
id | followup_id |            recipient             | channel |                               title                                | status 
----+-------------+----------------------------------+---------+--------------------------------------------------------------------+--------
  1 |           1 | Structural engineer (EOR)        | in_app  | Follow-up assigned: Project Atlas · RFI-0387                       | sent
  2 |           1 | <presenter> | email   | [Control Tower] Follow-up assigned: Project Atlas · RFI-0387       | queued
  3 |           2 | Ironline Steel foreman           | in_app  | Follow-up assigned: Project Atlas · Crane pick Thu                 | sent
  4 |           2 | <presenter> | email   | [Control Tower] Follow-up assigned: Project Atlas · Crane pick Thu | queued
  5 |           3 | Project controls                 | in_app  | Follow-up assigned: Project Atlas · CO-0142                        | sent
  6 |           3 | <presenter> | email   | [Control Tower] Follow-up assigned: Project Atlas · CO-0142        | queued
(6 rows)
```

### Human decision on an agent recommendation — stored with the MLflow trace id of the agent run it was based on

```sql
select id, project_id, item_id, decision, left(rationale, 600) as rationale, decided_by, trace_id, created_at from control_tower.decisions order by id
```

```text
-[ RECORD 1 ]--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
id         | 1
project_id | P-1001
item_id    | CO-0142
decision   | Negotiate
rationale  | - Entitlement looks supported under prime §4.3. Consider pricing at Exhibit B rates, which comes to $419,950 (283,200 + 111,800 + 24,950). That is $66,050 (13.6%) below the $486,000 requested . Exhibit B governs where it applies .+
           | - Before deciding, confirm the Owner notice was sent. Also review the late-notice waiver exposure for costs incurred between 11 and 23 Oct, and request daily logs, photos and quantity backup. The decision is yours.
decided_by | <presenter>
trace_id   | tr-aeccc0c6a24c6a3e02371cb2264c2eed
created_at | 2026-11-18 03:28:42.624486+00
```
