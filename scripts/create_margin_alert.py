"""Create/update the daily 'Margin fade' SQL alert on project_margin_mv (Demo 2, step 1).
Created PAUSED so no email goes out until the presenter un-pauses it (or clicks Run now) before the demo.
Writes scripts/.margin_alert_id."""
import os
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
WH = "df23f63620c4cbbf"
ID_FILE = Path(__file__).parent / ".margin_alert_id"
PRESENTER = "<your-user-email>"

QUERY = """-- Margin fade watch: jobs whose WIP projected margin is > 1.5 pts below bid (single definition: project_margin_mv)
WITH j AS (
  SELECT project_name, MEASURE(bid_margin_pct) AS bid, MEASURE(projected_margin_pct) AS projected, MEASURE(margin_fade_usd) AS fade_usd
  FROM bhambs.construction_control_tower.project_margin_mv
  WHERE months_ago = 0 AND breaching_threshold GROUP BY ALL
), p AS (
  SELECT MEASURE(projected_margin_pct) AS portfolio_projected FROM bhambs.construction_control_tower.project_margin_mv WHERE months_ago = 0
)
SELECT COUNT(j.project_name) AS jobs_breaching,
       ROUND(SUM(j.fade_usd) / 1e6, 1) AS gross_profit_at_risk_m,
       MAX(p.portfolio_projected) AS portfolio_projected_margin_pct,
       array_join(collect_list(concat(j.project_name, ': ', CAST(j.projected AS STRING), '% vs ', CAST(j.bid AS STRING), '% bid')), ' | ') AS jobs
FROM j CROSS JOIN p"""

alert = sql.AlertV2(
    display_name="Margin fade watch — projected margin > 1.5 pts below bid",
    query_text=QUERY,
    warehouse_id=WH,
    custom_summary="Margin fade: jobs have fallen more than 1.5 pts below bid margin while the portfolio average still looks healthy",
    custom_description="Daily check on the WIP margin metric view (project_margin_mv). Ask Genie One: 'Why did projected margin drop on Project Atlas?'",
    evaluation=sql.AlertV2Evaluation(
        source=sql.AlertV2OperandColumn(name="jobs_breaching"),
        comparison_operator=sql.ComparisonOperator.GREATER_THAN,
        threshold=sql.AlertV2Operand(value=sql.AlertV2OperandValue(double_value=0)),
        empty_result_state=sql.AlertEvaluationState.OK,
        notification=sql.AlertV2Notification(notify_on_ok=False, subscriptions=[sql.AlertV2Subscription(user_email=PRESENTER)]),
    ),
    schedule=sql.CronSchedule(quartz_cron_schedule="0 0 6 * * ?", timezone_id="America/New_York", pause_status=sql.SchedulePauseStatus.PAUSED),
)
if ID_FILE.exists():
    a = w.alerts_v2.update_alert(ID_FILE.read_text().strip(), alert, update_mask="display_name,query_text,custom_summary,custom_description,evaluation,schedule")
    print("updated alert", a.id)
else:
    a = w.alerts_v2.create_alert(alert)
    ID_FILE.write_text(a.id)
    print("created alert", a.id)
print(f"{w.config.host}/sql/alerts-v2/{a.id}")
