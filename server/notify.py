"""Email + Slack delivery for queued notifications — via Databricks job notifications (no SMTP, no Slack token in the app).

Each follow-up = ONE one-time serverless run of notifier/send_followup with
  email_notifications.on_success   = [recipient]                  (email)
  webhook_notifications.on_success = [SLACK_DESTINATION_ID]       (Slack, if configured)
Databricks sends both when the run finishes (~1 min); the run name carries the follow-up title, the run output holds
the full message. The Slack webhook URL lives in a workspace notification destination (admin-managed), never in the app.
Docs: https://docs.databricks.com/aws/en/jobs/notifications
      https://docs.databricks.com/aws/en/admin/workspace-settings/notification-destinations
Runs as the APP service principal in Databricks Apps (developer profile locally).
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from databricks.sdk.service import jobs as J

from .db import pool

log = logging.getLogger("notify")
NOTEBOOK = os.environ.get("NOTIFIER_NOTEBOOK", "/Workspace/Users/<your-user-email>/apps/construction-control-tower/notifier/send_followup")
SLACK_DESTINATION_ID = os.environ.get("SLACK_DESTINATION_ID", "").strip()
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "").strip()   # display only (e.g. "#control-tower-demo")


def slack_enabled() -> bool:
    return bool(SLACK_DESTINATION_ID)


def _client():
    from .auth import IS_DATABRICKS_APP, _local_client
    if IS_DATABRICKS_APP:
        from databricks.sdk import WorkspaceClient
        return WorkspaceClient()
    return _local_client()


def _send(notification_ids: list[int], run_name: str, title: str, body: str,
          email: Optional[str], slack: bool) -> None:
    status = "failed"
    try:
        run = _client().jobs.submit(
            run_name=run_name[:100],
            tasks=[J.SubmitTask(task_key="notify", notebook_task=J.NotebookTask(notebook_path=NOTEBOOK, base_parameters={"title": title, "message": body}))],
            email_notifications=J.JobEmailNotifications(on_success=[email], on_failure=[email]) if email else None,
            webhook_notifications=J.WebhookNotifications(on_success=[J.Webhook(id=SLACK_DESTINATION_ID)]) if slack else None,
        )
        status = "sent"
        log.info("notifications %s submitted as run %s", notification_ids, run.run_id)
    except Exception as e:  # never break the user's action because delivery failed
        log.warning("notifications %s failed: %s", notification_ids, e)
    with pool().connection() as conn:
        conn.execute("UPDATE control_tower.notifications SET status = %s WHERE id = ANY(%s)", (status, notification_ids))
        conn.commit()


def deliver_async(notification_ids: list[int], run_name: str, title: str, body: str,
                  email: Optional[str] = None, slack: bool = False) -> None:
    if notification_ids and (email or slack):
        threading.Thread(target=_send, args=(notification_ids, run_name, title, body, email, slack), daemon=True).start()
