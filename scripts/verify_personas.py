"""Prove Unity Catalog row-level security end to end, at every layer of the journey.

Runs the same queries as each demo identity — the presenter (ops leadership, sees everything), a simulated
Northeast project manager (Northeast projects only) and a simulated superintendent (Project Atlas only) — against:
  * the Lakeflow pipeline tables (bronze streaming table, silver materialized views)
  * the governed metric view the app and the Genie Agent use (project_risk_mv)
  * a detail table (rfis)

The simulated identities are service principals; their OAuth secrets live in the Databricks secret scope
`control-tower` (see setup_identities.py) and are only ever held in memory here — never printed.
Output identifies each identity by persona label, not by user name or application id.

Usage: DATABRICKS_PROFILE=<profile> python scripts/verify_personas.py
"""
import base64, os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

PROFILE = os.environ.get("DATABRICKS_PROFILE", "apex-construction")
WH = os.environ.get("WAREHOUSE_ID", "df23f63620c4cbbf")
CATALOG, SCHEMA = os.environ.get("CATALOG", "bhambs"), os.environ.get("SCHEMA", "construction_control_tower")
me = WorkspaceClient(profile=PROFILE)
sec = lambda k: base64.b64decode(me.secrets.get_secret("control-tower", k).value).decode()  # noqa: E731

CHECKS = [
    ("bronze_projects rows (Lakeflow streaming table)", "SELECT COUNT(*) FROM bronze_projects"),
    ("silver_projects rows (Lakeflow materialized view)", "SELECT COUNT(*) FROM silver_projects"),
    ("silver_project_signal_weekly distinct projects", "SELECT COUNT(DISTINCT project_id) FROM silver_project_signal_weekly"),
    ("project_risk_mv: projects this week", "SELECT MEASURE(project_count) FROM project_risk_mv WHERE weeks_ago = 0"),
    ("project_risk_mv: average risk score this week", "SELECT ROUND(MEASURE(risk_score)) FROM project_risk_mv WHERE weeks_ago = 0"),
    ("project_risk_mv: regions visible", "SELECT concat_ws(', ', sort_array(collect_set(region))) FROM project_risk_mv WHERE weeks_ago = 0"),
    ("rfis: open RFIs visible", "SELECT COUNT(*) FROM rfis WHERE status = 'Open'"),
]


def one(w, stmt):
    r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=WH, catalog=CATALOG, schema=SCHEMA, wait_timeout="50s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        return f"ERROR: {r.status.error.message if r.status.error else r.status.state}"[:80]
    return str(r.result.data_array[0][0])


identities = [("Presenter (ops leadership)", me)]
for key, label in (("northeast_pm", "Northeast PM (simulated)"), ("superintendent", "Atlas superintendent (simulated)")):
    identities.append((label, WorkspaceClient(host=me.config.host, client_id=sec(f"{key}_client_id"),
                                              client_secret=sec(f"{key}_client_secret"), auth_type="oauth-m2m")))

results = {label: [one(w, q) for _, q in CHECKS] for label, w in identities}
width = max(len(c) for c, _ in CHECKS)
cols = [label for label, _ in identities]
print(f"{'check':{width}} | " + " | ".join(f"{c:>32}" for c in cols))
print("-" * width + "-+-" + "-+-".join("-" * 32 for _ in cols))
for i, (name, _) in enumerate(CHECKS):
    print(f"{name:{width}} | " + " | ".join(f"{results[c][i]:>32}" for c in cols))
