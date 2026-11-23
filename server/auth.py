"""Workspace clients.

Real users: Genie/SQL calls run AS THE SIGNED-IN USER (on-behalf-of-user auth) so Unity Catalog
row filters apply automatically. Docs: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth

Demo mode: the header switch can make the backend act as a SIMULATED identity (service principal)
instead — ct-demo-northeast-pm or ct-demo-atlas-superintendent. Same row filters, enforced by UC.
Their OAuth credentials live in the Databricks secret scope `control-tower` (or env vars in the App).
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache

from databricks.sdk import WorkspaceClient
from fastapi import HTTPException, Request

IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"
SECRET_SCOPE = "control-tower"

PERSONAS = {
    "presenter": {"label": "Signed-in user", "role": "Ops leadership", "scope": "All projects"},
    "northeast_pm": {"label": "Northeast PM (simulated)", "role": "Project Manager", "scope": "Region: Northeast"},
    "superintendent": {"label": "Dana Morales (simulated)", "role": "Superintendent", "scope": "Project: Atlas"},
}


def _host() -> str:
    host = os.environ.get("DATABRICKS_HOST", "")
    if host:
        return host if host.startswith("http") else f"https://{host}"
    return _local_client().config.host


@lru_cache(maxsize=1)
def _local_client() -> WorkspaceClient:
    return WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))


def _secret(key: str) -> str:
    env = os.environ.get(f"CT_{key.upper()}")
    if env:
        return env
    v = _local_client().secrets.get_secret(SECRET_SCOPE, key).value  # local dev: read with the developer's profile
    return base64.b64decode(v).decode()


@lru_cache(maxsize=4)
def _persona_client(persona: str) -> WorkspaceClient:
    return WorkspaceClient(host=_host(), client_id=_secret(f"{persona}_client_id"),
                           client_secret=_secret(f"{persona}_client_secret"), auth_type="oauth-m2m")


def persona_of(request: Request) -> str:
    p = request.headers.get("x-demo-persona", "presenter")
    return p if DEMO_MODE and p in PERSONAS else "presenter"


def user_client(request: Request) -> WorkspaceClient:
    """Client for data/Genie calls: the selected simulated persona, else the signed-in user (OBO)."""
    persona = persona_of(request)
    if persona != "presenter":
        return _persona_client(persona)
    if IS_DATABRICKS_APP:
        token = request.headers.get("x-forwarded-access-token")
        if not token:
            raise HTTPException(401, "No user token forwarded — enable user authorization on the app.")
        return WorkspaceClient(host=_host(), token=token, auth_type="pat")
    return _local_client()


def current_user(request: Request) -> dict:
    persona = persona_of(request)
    email = request.headers.get("x-forwarded-email")
    if not email and not IS_DATABRICKS_APP:
        email = _local_client().current_user.me().user_name
    return {"email": email, "persona": persona, **PERSONAS[persona], "demo_mode": DEMO_MODE,
            "personas": [{"id": k, **v} for k, v in PERSONAS.items()] if DEMO_MODE else []}
