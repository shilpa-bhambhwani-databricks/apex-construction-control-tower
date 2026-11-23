"""Capture text evidence that every stage of the Control Tower data journey actually ran.

Runs read-only checks against the live workspace and writes plain-text / markdown files into evidence/:
  01_lakeflow_pipeline.md   pipeline spec, update history, per-table row counts, data-quality results, event log
  02_unity_catalog.md       governed objects, row filters, metric view, per-identity results, lineage
  03_lakebase.md            operational app state in Lakebase Postgres (follow-ups, notifications, decisions)
  04_gen_ai.md              ai_parse_document output, AI Search retrieval, UC function tools, MLflow agent traces
  05_genie.md               natural-language questions answered by the Genie Agents (question, SQL, rows)
  06_app.md                 Databricks App status, resources, deployment and request log

Everything printed is real output from the run. User names, e-mail addresses, service-principal ids and cloud
storage paths are masked on the way out. Nothing is written to the workspace except the Genie conversations
the questions create.

Usage: DATABRICKS_PROFILE=<profile> python scripts/capture_evidence.py [section ...]     (default: all sections)
"""
from __future__ import annotations

import base64, datetime, os, re, subprocess, sys, time, traceback
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

PROFILE = os.environ.get("DATABRICKS_PROFILE", "apex-construction")
WH = os.environ.get("WAREHOUSE_ID", "df23f63620c4cbbf")
CATALOG, SCHEMA = os.environ.get("CATALOG", "bhambs"), os.environ.get("SCHEMA", "construction_control_tower")
FQ = f"{CATALOG}.{SCHEMA}"
PIPELINE_NAME, APP_NAME, LAKEBASE_PROJECT = "construction-control-tower-ingest", "construction-control-tower", "construction-control-tower"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence"
OUT.mkdir(exist_ok=True)
IDS = {n: (ROOT / "scripts" / f).read_text().strip() for n, f in
       (("risk", ".genie_space_id"), ("jobsite", ".genie_jobsite_id"), ("finance", ".genie_finance_id"), ("experiment", ".resolve_experiment_id"))}

me = WorkspaceClient(profile=PROFILE)
ME = me.current_user.me().user_name
sec = lambda k: base64.b64decode(me.secrets.get_secret("control-tower", k).value).decode()  # noqa: E731
MASK: dict[str, str] = {ME: "<presenter>"}


def scrub(s: str) -> str:
    for k, v in MASK.items():
        s = s.replace(k, v)
    s = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+", "<email>", s)
    for part in re.split(r"[._-]", ME.split("@")[0]):  # the presenter's own name, wherever it was typed into a request
        if len(part) >= 4:
            s = re.sub(re.escape(part), "presenter", s, flags=re.IGNORECASE)
    s = re.sub(r"(s3|s3a|abfss|gs)://[^\s'\"\]]+", "<cloud storage path>", s)
    return s


def sql(stmt: str, w: WorkspaceClient | None = None):
    w = w or me
    r = w.statement_execution.execute_statement(statement=stmt, warehouse_id=WH, catalog=CATALOG, schema=SCHEMA, wait_timeout="50s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(1)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(r.status.error.message if r.status.error else str(r.status.state))
    cols = [c.name for c in r.manifest.schema.columns] if r.manifest and r.manifest.schema else []
    return cols, [["" if v is None else str(v) for v in row] for row in ((r.result.data_array or []) if r.result else [])]


def grid(cols, rows, max_rows=60, max_width=110) -> str:
    rows_ = [[c.replace("\n", " ⏎ ")[:max_width] for c in r] for r in rows[:max_rows]]
    w = [max(len(c), *(len(r[i]) for r in rows_)) if rows_ else len(c) for i, c in enumerate(cols)]
    line = lambda r: " | ".join(f"{v:<{w[i]}}" for i, v in enumerate(r)).rstrip()  # noqa: E731
    out = [line(cols), "-+-".join("-" * x for x in w)] + [line(r) for r in rows_]
    if len(rows) > max_rows:
        out.append(f"... ({len(rows) - max_rows} more rows)")
    return "\n".join(out)


def q(title: str, stmt: str, w=None, note: str = "", **kw) -> str:
    """One evidence block: the SQL that ran and the rows that came back."""
    head = f"### {title}\n\n" + (f"{note}\n\n" if note else "") + f"```sql\n{stmt.strip()}\n```\n\n"
    try:
        cols, rows = sql(stmt, w)
        return head + f"Result — {len(rows)} row(s):\n\n```text\n{grid(cols, rows, **kw)}\n```\n"
    except Exception as e:  # keep going: a failed check is itself evidence
        return head + f"FAILED:\n\n```text\n{str(e)[:600]}\n```\n"


def sh(cmd: list[str], timeout=300) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    return (p.stdout + (p.stderr if p.returncode else "")).strip()


def write(name: str, title: str, intro: str, parts: list[str]) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"# {title}\n\n{intro.strip()}\n\nCaptured {stamp} by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.\n\n" + "\n".join(parts)
    (OUT / name).write_text(scrub(body).rstrip() + "\n")
    print(f"wrote evidence/{name}  ({len(body):,} chars)")


def personas():
    out = [("Presenter (ops leadership)", me)]
    for key, label in (("northeast_pm", "Northeast PM (simulated)"), ("superintendent", "Atlas superintendent (simulated)")):
        cid = sec(f"{key}_client_id")
        MASK[cid] = f"<{label}>"
        out.append((label, WorkspaceClient(host=me.config.host, client_id=cid, client_secret=sec(f"{key}_client_secret"), auth_type="oauth-m2m")))
    return out


# ───────────────────────────────────────────────────────────────── 01 Lakeflow
def lakeflow():
    p = next(x for x in me.pipelines.list_pipelines(filter=f"name LIKE '{PIPELINE_NAME}'"))
    pid = p.pipeline_id
    spec = me.pipelines.get(pid)
    s = spec.spec
    ups = list(me.pipelines.list_updates(pid).updates or [])
    done = [u for u in ups if str(u.state).endswith("COMPLETED")]
    latest = done[0].update_id
    parts = ["## Pipeline\n\n```text\n" + "\n".join([
        f"name        : {spec.name}", f"pipeline_id : {pid}", f"state       : {spec.state}",
        f"target      : {s.catalog}.{s.schema}", f"serverless  : {s.serverless}", f"continuous  : {s.continuous}",
        f"source      : {[lib.glob.include for lib in (s.libraries or []) if lib.glob]}",
        f"config      : {dict(s.configuration or {})}"]) + "\n```\n",
        "## Update history (newest first)\n\nThe first attempts failed — a streaming `read_files` source needs a directory or glob, not a single file path. "
        "The source was changed to glob patterns (`rfis*.parquet`) and every update since has completed. Failures are left in the record on purpose.\n\n```text\n"
        + grid(["update_id", "state", "cause", "started (UTC)"], [[u.update_id, str(u.state).split(".")[-1], str(u.cause).split(".")[-1],
               datetime.datetime.fromtimestamp(u.creation_time / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")] for u in ups]) + "\n```\n",
        q("Rows written per table, per update (pipeline event log)", f"""
SELECT substr(origin.update_id, 1, 8) AS update_id, regexp_extract(origin.flow_name, '([^.]+)$', 1) AS table_name,
       CAST(details:flow_progress.metrics.num_output_rows AS BIGINT) AS output_rows,
       CAST(details:flow_progress.data_quality.dropped_records AS BIGINT) AS dropped_rows
FROM event_log('{pid}')
WHERE event_type = 'flow_progress' AND details:flow_progress.metrics.num_output_rows IS NOT NULL
ORDER BY timestamp""", note="The first completed update ingests every raw file into bronze. Later updates write no bronze rows because no new files "
                            "landed — ingestion is incremental — and recompute only the silver materialized views."),
        q("Data-quality expectations, per update (pipeline event log)", f"""
SELECT substr(origin.update_id, 1, 8) AS update_id, regexp_extract(origin.flow_name, '([^.]+)$', 1) AS table_name,
       e.name AS expectation, e.passed_records AS passed, e.failed_records AS failed
FROM (SELECT origin, timestamp, explode(from_json(details:flow_progress.data_quality.expectations,
             'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS e
      FROM event_log('{pid}')
      WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL)
ORDER BY timestamp, table_name, expectation"""),
        q(f"Event log of the latest completed update ({latest[:8]})", f"""
SELECT date_format(timestamp, 'HH:mm:ss.SSS') AS time_utc, event_type, level, message
FROM event_log('{pid}')
WHERE origin.update_id = '{latest}' AND event_type IN ('create_update', 'update_progress', 'flow_progress', 'dataset_life_cycle', 'planning_information')
ORDER BY timestamp""", max_rows=120, max_width=150),
        q("Bronze keeps the source file and ingest time on every row", """
SELECT 'bronze_projects' AS table_name, regexp_extract(_source_file, '(/Volumes/.*)$', 1) AS source_file, COUNT(*) AS row_count, MIN(_ingested_at) AS ingested_at FROM bronze_projects GROUP BY ALL
UNION ALL SELECT 'bronze_project_signal_weekly', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_project_signal_weekly GROUP BY ALL
UNION ALL SELECT 'bronze_rfis', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_rfis GROUP BY ALL
UNION ALL SELECT 'bronze_change_orders', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_change_orders GROUP BY ALL
UNION ALL SELECT 'bronze_submittals', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_submittals GROUP BY ALL
UNION ALL SELECT 'bronze_schedule_activities', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_schedule_activities GROUP BY ALL
UNION ALL SELECT 'bronze_schedule_float_weekly', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_schedule_float_weekly GROUP BY ALL
UNION ALL SELECT 'bronze_job_cost', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_job_cost GROUP BY ALL
UNION ALL SELECT 'bronze_safety_observations', regexp_extract(_source_file, '(/Volumes/.*)$', 1), COUNT(*), MIN(_ingested_at) FROM bronze_safety_observations GROUP BY ALL"""),
        q("Sample rows — silver_project_signal_weekly (Project Atlas, latest week)", """
SELECT project_id, week, signal, sub_score, raw_value, weight
FROM silver_project_signal_weekly WHERE project_id = 'P-1001' AND week = DATE'2026-11-09' ORDER BY signal"""),
    ]
    write("01_lakeflow_pipeline.md", "Stage 1 — Lakeflow: ingest the raw data",
          "A serverless Lakeflow Spark Declarative Pipeline (`lakeflow/`) ingests the nine raw source-system extracts from a Unity Catalog volume "
          "into bronze streaming tables with Auto Loader, then builds quality-checked silver materialized views. The silver tables are the source "
          "of the governed risk metric view that the app and the Genie Agent read (see `02_unity_catalog.md`).", parts)


# ──────────────────────────────────────────────────────────── 02 Unity Catalog
def unity_catalog():
    who = personas()
    parts = [
        q("Everything lives in one governed schema", f"""
SELECT table_type, COUNT(*) AS objects, concat_ws(', ', sort_array(collect_list(table_name))) AS names
FROM {CATALOG}.information_schema.tables WHERE table_schema = '{SCHEMA}' GROUP BY table_type ORDER BY objects DESC""", max_width=420),
        q("Volumes (raw landing zone, documents, field photos)", f"""
SELECT volume_name, volume_type, comment FROM {CATALOG}.information_schema.volumes WHERE volume_schema = '{SCHEMA}' ORDER BY 1"""),
        q("Row filter attached to every project-scoped table — including the Lakeflow bronze and silver tables", f"""
SELECT table_name, regexp_extract(filter_name, '([^.]+)$', 1) AS row_filter, target_columns
FROM {CATALOG}.information_schema.row_filters WHERE table_schema = '{SCHEMA}' ORDER BY table_name"""),
        q("The row filter function", f"""
SELECT routine_name, routine_definition FROM {CATALOG}.information_schema.routines
WHERE routine_schema = '{SCHEMA}' AND routine_name = 'ct_row_scope'""", max_width=400),
        q("Who is mapped to which projects (access_scope)", """
SELECT persona, COUNT(*) AS mapped_projects, MAX(CASE WHEN project_id = '*' THEN 'all projects' ELSE 'listed projects only' END) AS scope
FROM access_scope GROUP BY persona ORDER BY 2 DESC"""),
        q("Governed tools the agents call (Unity Catalog functions)", f"""
SELECT routine_name, left(comment, 150) AS comment FROM {CATALOG}.information_schema.routines
WHERE routine_schema = '{SCHEMA}' ORDER BY 1""", max_width=160),
        q("Metric view definition — one governed definition of the risk score, sourced from the Lakeflow silver tables",
          "SHOW CREATE TABLE project_risk_mv", max_width=6000),
        q("Risk score — top projects this week", """
SELECT project_name, market_sector, region, ROUND(MEASURE(risk_score)) AS risk_score
FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL ORDER BY risk_score DESC LIMIT 8"""),
        q("Risk score — what is driving Project Atlas", """
SELECT signal, ROUND(MEASURE(risk_score), 1) AS points_now, ROUND(MEASURE(signal_raw_value), 2) AS raw_value
FROM project_risk_mv WHERE project_name LIKE 'Project Atlas%' AND weeks_ago = 0 GROUP BY ALL ORDER BY points_now DESC"""),
        q("Risk score — Project Atlas, last 8 weeks", """
SELECT weeks_ago, ROUND(MEASURE(risk_score)) AS atlas_score
FROM project_risk_mv WHERE project_name LIKE 'Project Atlas%' AND weeks_ago <= 8 GROUP BY ALL ORDER BY weeks_ago DESC"""),
        q("Risk score — by market sector", """
SELECT market_sector, MEASURE(project_count) AS projects, ROUND(MEASURE(risk_score)) AS avg_risk
FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL ORDER BY avg_risk DESC"""),
        "### Same queries, three identities — row-level security at every layer\n\n`scripts/verify_personas.py` runs each check as the presenter "
        "and as two simulated identities (service principals).\n\n```text\n" + sh([sys.executable, "scripts/verify_personas.py"]) + "\n```\n",
    ]
    for label, w in who:
        parts.append(q(f"As: {label}", """
SELECT MEASURE(project_count) AS projects_visible, ROUND(MEASURE(risk_score)) AS avg_risk,
       concat_ws(', ', sort_array(collect_set(region))) AS regions
FROM project_risk_mv WHERE weeks_ago = 0""", w))
    lin = []
    for t in ("silver_project_signal_weekly", "silver_projects", "project_risk_mv"):
        d = me.api_client.do("GET", "/api/2.0/lineage-tracking/table-lineage", body={"table_name": f"{FQ}.{t}", "include_entity_lineage": True})
        for side in ("upstreams", "downstreams"):
            for x in d.get(side, []):
                ti = x.get("tableInfo") or {}
                if ti.get("name"):
                    a, b = (f"{ti['name']} ({ti.get('table_type')})", t) if side == "upstreams" else (t, f"{ti['name']} ({ti.get('table_type')})")
                    lin.append(f"{a:<52} -->  {b}")
    parts.append("### Lineage recorded by Unity Catalog (table lineage API)\n\nRaw volume files → bronze → silver → metric view, captured automatically.\n\n```text\n"
                 + "\n".join(sorted(set(lin))) + "\n```\n")
    write("02_unity_catalog.md", "Stage 2 — Unity Catalog: govern it",
          "One schema holds the whole dataset: tables, pipeline tables, volumes, functions and metric views. A single row filter decides which "
          "projects each identity can see, and it is attached at every layer. The risk score is defined once, as a metric view, and that one "
          "definition is what the app, the agents and Genie all use.", parts)


# ─────────────────────────────────────────────────────────────────── 03 Lakebase
def lakebase():
    def psql(title, stmt, expanded=False):
        cmd = ["databricks", "psql", "--project", LAKEBASE_PROJECT, "-p", PROFILE, "--", "-d", "databricks_postgres"] + (["-x"] if expanded else []) + ["-c", stmt]
        out = "\n".join(l for l in sh(cmd).splitlines() if not re.match(r"^(Project|Branch|Endpoint|Connecting)", l))
        return f"### {title}\n\n```sql\n{stmt}\n```\n\n```text\n{out}\n```\n"
    parts = [
        psql("Lakebase is serverless Postgres", "select split_part(version(), ' on ', 1) as engine, current_database() as database"),
        psql("App-state tables", "select table_name, count(*) as columns from information_schema.columns where table_schema = 'control_tower' group by table_name order by 1"),
        psql("Rows written by the app", "select 'followups' as tbl, count(*) as rows, min(created_at)::date as first_write, max(created_at)::date as last_write from control_tower.followups "
             "union all select 'notifications', count(*), min(created_at)::date, max(created_at)::date from control_tower.notifications "
             "union all select 'decisions', count(*), min(created_at)::date, max(created_at)::date from control_tower.decisions"),
        psql("Follow-ups assigned from the Risk Radar (who assigned it is the signed-in or simulated identity)",
             "select id, project_id, item_ref, owner, due_date, note, status, created_by, source, created_at from control_tower.followups order by id", True),
        psql("Notifications queued for each follow-up",
             "select id, followup_id, recipient, channel, title, status from control_tower.notifications order by id"),
        psql("Human decision on an agent recommendation — stored with the MLflow trace id of the agent run it was based on",
             "select id, project_id, item_id, decision, left(rationale, 600) as rationale, decided_by, trace_id, created_at from control_tower.decisions order by id", True),
    ]
    write("03_lakebase.md", "Stage 3 — Lakebase: operational serving",
          "Lakebase (serverless Postgres) is the app's operational store. The lakehouse stays read-only for the app; every action a user takes — "
          "assigning a follow-up, notifying an owner, accepting or rejecting an agent recommendation — is a transactional write to Lakebase, keyed by "
          "the same `project_id` and item ids as the governed data, and read back on every page load. Queries below were run with `databricks psql`.", parts)


# ───────────────────────────────────────────────────────────────────── 04 Gen AI
def gen_ai():
    parts = [
        q("ai_parse_document output — contracts, specs, logs and standards parsed from PDFs in a volume", """
SELECT doc_name, size(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) AS parsed_elements,
       size(variant_get(parsed, '$.document.pages', 'ARRAY<VARIANT>')) AS pages
FROM parsed_documents ORDER BY doc_name"""),
        q("Parsed elements for one document (real ai_parse_document output)", """
SELECT pos AS element, e:type::string AS type, e:bbox[0].page_id::int + 1 AS page, left(e:content::string, 110) AS content
FROM parsed_documents LATERAL VIEW posexplode(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) t AS pos, e
WHERE doc_name = 'Subcontract_Keystone_Concrete.pdf' ORDER BY pos LIMIT 14""", max_width=112),
        q("Retrieval chunks behind the AI Search index", "SELECT doc_type, COUNT(*) AS chunks, COUNT(DISTINCT doc_name) AS documents FROM doc_chunks GROUP BY 1 ORDER BY 2 DESC"),
    ]
    try:
        ix = me.vector_search_indexes.get_index(f"{FQ}.doc_chunks_index")
        st = ix.status
        parts.append("### AI Search (vector) index status\n\n```text\n" + "\n".join([
            f"index          : {ix.name}", f"type           : {str(ix.index_type).split('.')[-1]}", f"endpoint       : {ix.endpoint_name}",
            f"ready          : {st.ready if st else None}", f"indexed rows   : {st.indexed_row_count if st else None}",
            f"embedding model: {ix.delta_sync_index_spec.embedding_source_columns[0].embedding_model_endpoint_name if ix.delta_sync_index_spec and ix.delta_sync_index_spec.embedding_source_columns else None}"]) + "\n```\n")
    except Exception as e:
        parts.append(f"### AI Search index status\n\nFAILED: `{str(e)[:300]}`\n")
    parts += [
        q("Semantic retrieval over the index — the question a project manager would ask", f"""
SELECT doc_name, page, section, left(text, 170) AS passage
FROM vector_search(index => '{FQ}.doc_chunks_index', query_text => 'How many days does the subcontractor have to give notice of a differing site condition?', num_results => 5)""",
          max_width=175),
        q("Agent tool: historical unit-cost benchmark (Unity Catalog function)", "SELECT * FROM get_unit_cost_baseline('03-3000', 'Northeast', 'rock removal')"),
        q("Agent tool: change order with line items (Unity Catalog function, row-filtered)", """
SELECT co_id, project_name, subcontractor, amount_requested, submitted_date, line, item_desc, quantity, unit, unit_rate, line_amount
FROM get_change_order('CO-0142')""", max_width=60),
    ]
    # Real agent runs, as logged by MLflow Tracing from the deployed app.
    try:
        import logging
        import mlflow
        from mlflow.tracing.client import TracingClient
        logging.getLogger("mlflow").setLevel(logging.ERROR)
        mlflow.set_tracking_uri(f"databricks://{PROFILE}")
        client = TracingClient()
        utc = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")  # noqa: E731
        infos, _ = client._search_traces(locations=[IDS["experiment"]], max_results=60, order_by=["timestamp_ms DESC"])
        rows = [[i.trace_id, utc(i.timestamp_ms), str(i.state).split(".")[-1], f"{(i.execution_time_ms or 0) / 1000:.1f}s",
                 (i.tags or {}).get("agent", ""), (i.request_preview or "").replace("\n", " ")[:80]] for i in infos]
        parts.append(f"### MLflow traces logged by the agents from the app (experiment {IDS['experiment']}, newest first) — {len(rows)} runs\n\n```text\n"
                     + grid(["trace_id", "started (UTC)", "state", "duration", "agent", "request"], rows, max_rows=30) + "\n```\n")
        dec = ""
        try:
            dec = sh(["databricks", "psql", "--project", LAKEBASE_PROJECT, "-p", PROFILE, "--", "-d", "databricks_postgres", "-At", "-c",
                      "select trace_id from control_tower.decisions order by id desc limit 1"]).splitlines()[-1].strip()
        except Exception:
            pass
        di = next((i for i in infos if i.trace_id == dec), None)
        if di:
            parts.append(f"### Agent run {dec} — the run behind the human decision stored in Lakebase (see 03_lakebase.md)\n\n```text\nstarted  : {utc(di.timestamp_ms)} UTC\n"
                         f"state    : {str(di.state).split('.')[-1]}\nduration : {(di.execution_time_ms or 0) / 1000:.1f}s\nagent    : {(di.tags or {}).get('agent', '')}\n```\n\n"
                         f"Request (preview kept by MLflow):\n\n```text\n{di.request_preview}\n```\n\nResponse (preview kept by MLflow):\n\n```text\n{di.response_preview}\n```\n")
        # Full span trees + verbatim model output for the newest run of each agent that still has span data stored.
        shown: set[str] = set()
        for t in client.search_traces(locations=[IDS["experiment"]], max_results=60, order_by=["timestamp_ms DESC"]):
            agent = (t.info.tags or {}).get("agent", "agent")
            if agent in shown or not t.data.spans:
                continue
            shown.add(agent)
            spans = t.data.spans
            root = next((x for x in spans if x.parent_id is None), spans[0])
            tree = "\n".join(f"  {str(x.span_type or ''):<11} {x.name[:58]:<58} {((x.end_time_ns or x.start_time_ns) - x.start_time_ns) / 1e9:6.1f}s" for x in spans)
            out = root.outputs.get("answer") if isinstance(root.outputs, dict) and root.outputs.get("answer") else root.outputs
            parts.append(f"### Agent run {t.info.trace_id} — newest `{agent}` run with full span data\n\n```text\nstarted  : {utc(t.info.timestamp_ms)} UTC\n"
                         f"state    : {str(t.info.state).split('.')[-1]}\nduration : {(t.info.execution_time_ms or 0) / 1000:.1f}s\nspans    : {len(spans)}\n{tree}\n```\n\n"
                         f"Request:\n\n```text\n{str(root.inputs)[:1500]}\n```\n\nModel output (verbatim, first 4,500 characters):\n\n```text\n{str(out)[:4500]}\n```\n")
    except Exception:
        parts.append("### MLflow traces\n\nFAILED:\n\n```text\n" + traceback.format_exc()[-900:] + "\n```\n")
    write("04_gen_ai.md", "Stage 4 — Gen AI: make it intelligent",
          "Contracts, subcontracts, specs, daily logs and safety standards are parsed with `ai_parse_document`, chunked with page and section, and "
          "indexed in AI Search. Two tool-calling agents (Project Resolve and Jobsite Intelligence) run on a Databricks-hosted foundation model, "
          "retrieve from that index, call governed Unity Catalog functions, and log every step with MLflow Tracing. The outputs below are real.", parts)


# ───────────────────────────────────────────────────────────────────── 05 Genie
def genie():
    who = dict(personas())
    asks = [
        ("risk", "Control Tower — Portfolio Risk", "Presenter (ops leadership)", "Which projects need attention this week, and what's driving it?"),
        ("risk", "Control Tower — Portfolio Risk", "Presenter (ops leadership)", "Why did Project Atlas's risk score go up over the last 8 weeks?"),
        ("risk", "Control Tower — Portfolio Risk", "Presenter (ops leadership)", "Which open RFIs on Project Atlas are tied to critical-path activities?"),
        ("risk", "Control Tower — Portfolio Risk", "Northeast PM (simulated)", "How many projects can I see, and which one has the highest risk score this week?"),
        ("risk", "Control Tower — Portfolio Risk", "Atlas superintendent (simulated)", "How many projects can I see, and which one has the highest risk score this week?"),
        ("finance", "Control Tower — Project Controls (Margin)", "Presenter (ops leadership)", "Which projects are breaching the margin fade threshold, and by how much?"),
        ("jobsite", "Control Tower — Jobsite Safety", "Presenter (ops leadership)", "How many near-misses were recorded on Project Atlas in the last 14 days, by category?"),
    ]
    parts = []
    for key, space, persona, question in asks:
        w, sid, t0 = who[persona], IDS[key], time.time()
        block = f"### {space}  ·  asked as: {persona}\n\n**Question:** {question}\n\n"
        try:
            m = w.genie.start_conversation_and_wait(sid, question)
            block += f"Status: {str(m.status).split('.')[-1]} in {time.time() - t0:.0f}s\n\n"
            for a in m.attachments or []:
                if a.text and a.text.content:
                    block += f"**Answer:**\n\n```text\n{a.text.content.strip()[:2500]}\n```\n\n"
                if a.query:
                    block += (f"**Genie's description:** {a.query.description}\n\n" if a.query.description else "") + f"**SQL Genie wrote:**\n\n```sql\n{(a.query.query or '').strip()}\n```\n\n"
                    r = w.genie.get_message_attachment_query_result(sid, m.conversation_id, m.message_id or m.id, a.attachment_id)
                    sr = r.statement_response
                    if sr and sr.result:
                        cols = [c.name for c in sr.manifest.schema.columns]
                        rows = [["" if v is None else str(v) for v in row] for row in (sr.result.data_array or [])]
                        block += f"**Rows returned — {len(rows)}:**\n\n```text\n{grid(cols, rows, max_rows=15, max_width=70)}\n```\n"
        except Exception as e:
            block += f"FAILED after {time.time() - t0:.0f}s:\n\n```text\n{str(e)[:500]}\n```\n"
        parts.append(block)
        print(f"  genie: {persona[:22]:<22} {question[:60]}")
    write("05_genie.md", "Stage 5 — Genie Agent: make it queryable in natural language",
          "Three Genie Agents sit on the governed data: Portfolio Risk (over the risk metric view fed by the Lakeflow pipeline), Project Controls "
          "(margin) and Jobsite Safety. Questions below were sent through the Genie Conversation API. The same question asked by different "
          "identities returns different rows, because Genie runs as the asker and Unity Catalog row filters apply.", parts)


# ─────────────────────────────────────────────────────────────────────── 06 App
def app():
    a = me.apps.get(APP_NAME)
    d = a.active_deployment
    res = []
    for r in a.resources or []:
        kind = next((k for k in ("sql_warehouse", "genie_space", "postgres", "database", "serving_endpoint", "secret", "uc_securable") if getattr(r, k, None)), "?")
        res.append([r.name, kind])
    logs = sh(["databricks", "apps", "logs", APP_NAME, "-p", PROFILE, "--tail-lines", "400"], timeout=120)
    lines = [re.sub(r"\b\d+\.\d+\.\d+\.\d+:\d+", "<proxy>", l)[:170] for l in logs.splitlines() if "[APP]" in l and ("/api/" in l or "startup complete" in l)]
    starts = [i for i, l in enumerate(lines) if "startup complete" in l]
    api = lines[starts[-2] if len(starts) >= 2 else (starts[-1] if starts else 0):][-80:]  # since the two most recent app starts
    parts = ["## App\n\n```text\n" + "\n".join([
        f"name             : {a.name}", f"url              : {a.url}", f"app status       : {str(a.app_status.state).split('.')[-1]} — {a.app_status.message}",
        f"compute          : {str(a.compute_status.state).split('.')[-1]}", f"deployment       : {d.deployment_id}  {str(d.status.state).split('.')[-1]} — {d.status.message}",
        f"deployed (UTC)   : {d.update_time}", f"user API scopes  : {list(a.effective_user_api_scopes or [])}"]) + "\n```\n",
        "## Resources bound to the app\n\nEach stage of the journey is a declared resource: the SQL warehouse reads governed data, the Genie Agent answers questions, "
        "Lakebase holds app state, and the serving endpoint runs the agents.\n\n```text\n" + grid(["resource", "type"], res) + "\n```\n",
        "## Request log from the running app\n\nAPI calls served since the two most recent app starts (each `startup complete` line is a deployment going live).\n\n```text\n" + ("\n".join(api) or "(no API requests in the current log window)") + "\n```\n"]
    write("06_app.md", "Stage 6 — Databricks App: surface it to the business",
          "A FastAPI + React Databricks App with three modules — Portfolio Risk Radar, Project Resolve and Jobsite Intelligence. It calls the SQL "
          "warehouse and Genie on behalf of the signed-in user, so Unity Catalog decides what each person sees.", parts)


SECTIONS = {"lakeflow": lakeflow, "unity_catalog": unity_catalog, "lakebase": lakebase, "gen_ai": gen_ai, "genie": genie, "app": app}
if __name__ == "__main__":
    for name in (sys.argv[1:] or list(SECTIONS)):
        try:
            SECTIONS[name]()
        except Exception:
            print(f"SECTION FAILED: {name}\n{traceback.format_exc()}")
