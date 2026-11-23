# Stage 6 — Databricks App: surface it to the business

A FastAPI + React Databricks App with three modules — Portfolio Risk Radar, Project Resolve and Jobsite Intelligence. It calls the SQL warehouse and Genie on behalf of the signed-in user, so Unity Catalog decides what each person sees.

Captured 2026-11-23 20:27 UTC by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.

## App

```text
name             : construction-control-tower
url              : https://construction-control-tower-7474653951068148.aws.databricksapps.com
app status       : RUNNING — App has status: App is running
compute          : ACTIVE
deployment       : 01f1e776e30c11c1ba04d37cf6b45107  SUCCEEDED — App started successfully
deployed (UTC)   : 2026-11-23T19:49:26Z
user API scopes  : ['dashboards.genie', 'iam.access-control:read', 'iam.current-user:read', 'sql']
```

## Resources bound to the app

Each stage of the journey is a declared resource: the SQL warehouse reads governed data, the Genie Agent answers questions, Lakebase holds app state, and the serving endpoint runs the agents.

```text
resource           | type
-------------------+-----------------
sql-warehouse      | sql_warehouse
genie-space        | genie_space
lakebase           | postgres
resolve-model      | serving_endpoint
np-client-id       | secret
np-client-secret   | secret
supt-client-id     | secret
supt-client-secret | secret
```

## Request log from the running app

API calls served since the two most recent app starts (each `startup complete` line is a deployment going live).

```text
2026-11-23T19:26:50Z [APP] INFO:     Application startup complete.
2026-11-23T19:46:49Z [APP] INFO:     <proxy> - "GET /api/me HTTP/1.1" 200 OK
2026-11-23T19:46:51Z [APP] INFO:     <proxy> - "GET /api/risk/projects HTTP/1.1" 200 OK
2026-11-23T19:46:51Z [APP] INFO:     <proxy> - "GET /api/health HTTP/1.1" 200 OK
2026-11-23T19:46:51Z [APP] INFO:     <proxy> - "GET /api/notifications HTTP/1.1" 200 OK
2026-11-23T19:46:51Z [APP] INFO:     <proxy> - "GET /api/followups?project_id=P-1001 HTTP/1.1" 200 OK
2026-11-23T19:46:52Z [APP] INFO:     <proxy> - "GET /api/resolve/backlog?project_id=P-1001 HTTP/1.1" 200 OK
2026-11-23T19:46:52Z [APP] INFO:     <proxy> - "GET /api/jobsite/day?project_id=P-1001 HTTP/1.1" 200 OK
2026-11-23T19:46:53Z [APP] INFO:     <proxy> - "GET /api/resolve/item?project_id=P-1001&item_id=RFI-0387 HTTP/1.1" 200 OK
2026-11-23T19:46:54Z [APP] INFO:     <proxy> - "GET /api/resolve/item?project_id=P-1001&item_id=RFI-0352 HTTP/1.1" 200 OK
2026-11-23T19:46:54Z [APP] INFO:     <proxy> - "GET /api/resolve/item?project_id=P-1001&item_id=CO-0142 HTTP/1.1" 200 OK
2026-11-23T19:49:27Z [APP] INFO:     Application startup complete.
```
