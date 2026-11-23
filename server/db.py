"""Lakebase (Autoscaling Postgres) — Control Tower app state: follow-ups and in-app notifications.

Writes go ONLY to Lakebase (customer-owned app state); never to Procore/Clearstory/SAP.
Auth: OAuth token per pooled connection (fresh token on connect; recycle before 1h expiry).
In Databricks Apps the app service principal connects (PGUSER/PGHOST injected by the database resource);
locally the developer's CLI profile connects. Per-user authorization is enforced in the FastAPI routes.
"""
from __future__ import annotations

import os
from functools import lru_cache

import psycopg
from psycopg_pool import ConnectionPool

from .auth import IS_DATABRICKS_APP, _local_client

ENDPOINT_NAME = os.environ.get("LAKEBASE_ENDPOINT", "projects/construction-control-tower/branches/production/endpoints/primary")
PGHOST = os.environ.get("PGHOST", "<your-lakebase-endpoint-host>")
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")


def _client():
    if IS_DATABRICKS_APP:
        from databricks.sdk import WorkspaceClient
        return WorkspaceClient()  # app service principal
    return _local_client()


class OAuthConnection(psycopg.Connection):
    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):
        kwargs["password"] = _client().postgres.generate_database_credential(endpoint=ENDPOINT_NAME).token
        return super().connect(conninfo, **kwargs)


@lru_cache(maxsize=1)
def pool() -> ConnectionPool:
    user = os.environ.get("PGUSER") or _client().current_user.me().user_name
    p = ConnectionPool(
        conninfo=f"dbname={PGDATABASE} user={user} host={PGHOST} port={os.environ.get('PGPORT', '5432')} sslmode=require",
        connection_class=OAuthConnection, min_size=1, max_size=5, max_lifetime=2700, open=False,
        # Lakebase closes idle connections (scale-to-zero). Test each connection on checkout and replace dead ones,
        # so the first request after an idle period doesn't fail with AdminShutdown.
        check=ConnectionPool.check_connection,
    )
    p.open(wait=True, timeout=30)
    return p


SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS control_tower;
CREATE TABLE IF NOT EXISTS control_tower.followups (
  id           BIGSERIAL PRIMARY KEY,
  project_id   TEXT NOT NULL,
  item_ref     TEXT,                    -- e.g. RFI-0387, CO-0142, or 'project'
  owner        TEXT NOT NULL,           -- person/role assigned (synthetic in the demo)
  owner_email  TEXT,                    -- where the notification goes (demo: presenter's inbox)
  due_date     DATE,
  note         TEXT,
  status       TEXT NOT NULL DEFAULT 'Open',
  created_by   TEXT NOT NULL,           -- signed-in user or simulated persona
  source       TEXT NOT NULL DEFAULT 'risk-radar',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS control_tower.notifications (
  id           BIGSERIAL PRIMARY KEY,
  followup_id  BIGINT REFERENCES control_tower.followups(id),
  recipient    TEXT NOT NULL,
  channel      TEXT NOT NULL,           -- in_app | email | slack
  title        TEXT NOT NULL,
  body         TEXT,
  status       TEXT NOT NULL DEFAULT 'queued',   -- queued | sent | failed | read
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS followups_project_idx ON control_tower.followups(project_id);
"""


def init_schema() -> None:
    with pool().connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.commit()
