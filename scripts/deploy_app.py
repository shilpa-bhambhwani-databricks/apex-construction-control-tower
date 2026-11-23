"""Create/update the Databricks App with its resources + user authorization (OBO) scopes. Idempotent."""
import os
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import apps as A

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
NAME = "construction-control-tower"
SID = (Path(__file__).parent / ".genie_space_id").read_text().strip()
R = A.AppResource
resources = [
    R(name="sql-warehouse", sql_warehouse=A.AppResourceSqlWarehouse(id="df23f63620c4cbbf", permission=A.AppResourceSqlWarehouseSqlWarehousePermission.CAN_USE)),
    R(name="genie-space", genie_space=A.AppResourceGenieSpace(name="Control Tower — Portfolio Risk", space_id=SID, permission=A.AppResourceGenieSpaceGenieSpacePermission.CAN_RUN)),
    R(name="lakebase", postgres=A.AppResourcePostgres(branch="projects/construction-control-tower/branches/production",
                                                      database="projects/construction-control-tower/branches/production/databases/databricks-postgres",
                                                      permission=A.AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE)),
    R(name="resolve-model", serving_endpoint=A.AppResourceServingEndpoint(name="databricks-claude-sonnet-5-5", permission=A.AppResourceServingEndpointServingEndpointPermission.CAN_QUERY)),
] + [
    R(name=n, secret=A.AppResourceSecret(scope="control-tower", key=k, permission=A.AppResourceSecretSecretPermission.READ))
    for n, k in (("np-client-id", "northeast_pm_client_id"), ("np-client-secret", "northeast_pm_client_secret"),
                 ("supt-client-id", "superintendent_client_id"), ("supt-client-secret", "superintendent_client_secret"))
]
scopes = ["sql", "dashboards.genie"]
app = A.App(name=NAME, description="Construction Control Tower — rebrandable demo (Risk Radar · Resolve · Jobsite Intelligence). Synthetic data.",
            resources=resources, user_api_scopes=scopes)
existing = {a.name for a in w.apps.list()}
if NAME in existing:
    out = w.apps.update(NAME, app)
    print("updated app", NAME)
else:
    out = w.apps.create_and_wait(app)
    print("created app", NAME)
out = w.apps.get(NAME)
print("url:", out.url, "| sp:", out.service_principal_client_id, "| scopes:", out.effective_user_api_scopes, "| compute:", out.compute_status.state if out.compute_status else None)
