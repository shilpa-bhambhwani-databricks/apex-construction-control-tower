"""Run SQL statements on the workspace SQL warehouse. Usage: run_sql.py file.sql [more.sql...]
Statements are split on lines containing only ';;'. Prints a short result per statement."""
import os, sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
WH = os.environ.get("WAREHOUSE_ID", "df23f63620c4cbbf")

def run(stmt: str):
    r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=WH, wait_timeout="50s", catalog=os.environ.get("CATALOG", "bhambs"), schema=os.environ.get("SCHEMA", "construction_control_tower"))
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        r = w.statement_execution.get_statement(r.statement_id)
    head = " ".join(stmt.split())[:90]
    if r.status.state != StatementState.SUCCEEDED:
        print(f"FAIL  {head}\n      {r.status.error.message if r.status.error else r.status.state}"); return False
    rows = (r.result.data_array or []) if r.result else []
    cols = [c.name for c in r.manifest.schema.columns] if r.manifest and r.manifest.schema else []
    print(f"OK    {head}" + (f"\n      {cols}\n      " + "\n      ".join(map(str, rows[:15])) if rows else ""))
    return True

ok = True
for f in sys.argv[1:]:
    for stmt in [s.strip() for s in open(f).read().split("\n;;\n") if s.strip()]:
        ok &= run(stmt)
sys.exit(0 if ok else 1)
