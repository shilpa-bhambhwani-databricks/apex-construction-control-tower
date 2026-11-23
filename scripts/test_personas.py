"""Run the same metric-view query as each demo identity to prove row filters work (no app code)."""
import base64, os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

PROFILE = os.environ.get("DATABRICKS_PROFILE", "apex-construction")
WH = "df23f63620c4cbbf"
me = WorkspaceClient(profile=PROFILE)
sec = lambda k: base64.b64decode(me.secrets.get_secret("control-tower", k).value).decode()  # noqa: E731
Q = """SELECT current_user() AS who, MEASURE(project_count) AS projects, ROUND(MEASURE(risk_score)) AS avg_risk,
       (SELECT COUNT(*) FROM rfis WHERE status = 'Open') AS open_rfis
FROM project_risk_mv WHERE weeks_ago = 0"""

def run(w, label):
    r = w.statement_execution.execute_statement(statement=Q, warehouse_id=WH, catalog="bhambs", schema="construction_control_tower", wait_timeout="50s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        r = w.statement_execution.get_statement(r.statement_id)
    print(f"{label:34s}", r.result.data_array[0] if r.status.state == StatementState.SUCCEEDED else r.status.error.message)

run(me, "Presenter (ops leadership)")
for key, label in (("northeast_pm", "Simulated Northeast PM"), ("superintendent", "Simulated Atlas superintendent")):
    w = WorkspaceClient(host=me.config.host, client_id=sec(f"{key}_client_id"), client_secret=sec(f"{key}_client_secret"), auth_type="oauth-m2m")
    run(w, label)
