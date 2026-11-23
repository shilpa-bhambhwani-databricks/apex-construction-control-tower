"""Create the two SIMULATED demo identities (service principals) and store their OAuth secrets
in the Databricks secret scope `control-tower`. Secrets are never printed. Idempotent:
existing SPs are reused; a new secret is only created if the scope has none for that SP."""
import os
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
SCOPE = "control-tower"
IDENTITIES = {
    "northeast_pm": "ct-demo-northeast-pm",
    "superintendent": "ct-demo-atlas-superintendent",
}

if SCOPE not in [s.name for s in w.secrets.list_scopes()]:
    w.secrets.create_scope(SCOPE)
    print(f"created secret scope {SCOPE}")
existing_keys = {k.key for k in w.secrets.list_secrets(SCOPE)}

for key, name in IDENTITIES.items():
    found = list(w.service_principals.list(filter=f'displayName eq "{name}"'))
    sp = found[0] if found else w.service_principals.create(display_name=name, active=True)
    print(f"{name}: id={sp.id} application_id={sp.application_id} ({'existing' if found else 'created'})")
    w.secrets.put_secret(SCOPE, f"{key}_client_id", string_value=sp.application_id)
    if f"{key}_client_secret" not in existing_keys:
        sec = w.service_principal_secrets_proxy.create(service_principal_id=sp.id)
        w.secrets.put_secret(SCOPE, f"{key}_client_secret", string_value=sec.secret)
        print(f"  stored new OAuth secret in {SCOPE}/{key}_client_secret")
    else:
        print(f"  secret already in scope — reused")
