"""Resolve agent — glass-box, tool-calling agent for change orders and RFIs.

Model: Claude via Databricks AI Gateway (OpenAI-compatible). Tools:
  search_documents      AI Search (vector) over parsed contracts/specs/daily logs/letters → cited chunks (doc + page + section)
  find_similar_rfis     AI Search over historical RFI resolutions (institutional knowledge)
  get_change_order      UC function — CO header + line items, run AS THE USER (row-filtered)
  get_unit_cost_baseline UC function — 24-month P25/median/P75 benchmark, run AS THE USER
Every step is an MLflow 3 trace span (AGENT → CHAT_MODEL / RETRIEVER / TOOL) so IT can inspect exactly what the AI touched.
The agent RECOMMENDS; the human decides (decisions are logged in Lakebase, never written to Procore/Clearstory).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

import mlflow
from databricks.sdk import WorkspaceClient
from openai import OpenAI

from .auth import IS_DATABRICKS_APP, _local_client
from .risk import _sql

MODEL = os.environ.get("RESOLVE_MODEL", "databricks-claude-sonnet-5-5")
WORKSPACE_ID = os.environ.get("DATABRICKS_WORKSPACE_ID", "7474653951068148")
# Set AI_GATEWAY_URL to the endpoint's dedicated AI Gateway URL (endpoint page → Use endpoint → AI Gateway) to get Gateway
# rate limits/guardrails; otherwise use the workspace serving path (usage tracking is enabled on the endpoint).
GATEWAY_URL = os.environ.get("AI_GATEWAY_URL", "")
INDEX = os.environ.get("RESOLVE_INDEX", "bhambs.construction_control_tower.doc_chunks_index")
EXPERIMENT_ID = os.environ.get("RESOLVE_EXPERIMENT_ID", "3807042541599144")
MAX_ROUNDS = 6

SYSTEM = """You are the Resolve agent in a general contractor's Control Tower. You help project managers decide what to do about a change order (CO) or RFI.
Rules:
- Use tools to gather evidence BEFORE answering. For a CO: get_change_order; search_documents for the prime-contract coverage clause;
  search_documents (doc_types ["subcontract"]) for the subcontractor's notice clause AND, separately, for its "Exhibit B unit rates" (contract unit rates);
  search_documents (doc_types ["daily_log","letter","memo"]) for dated records to check notice timing; get_unit_cost_baseline for the largest priced line items.
  Compare requested unit rates to BOTH the subcontract's contract rate (if any) and the regional median.
- For an RFI: find_similar_rfis, then summarize the most relevant precedents (resolution, cost, schedule impact, turnaround).
- Every factual claim must carry a citation in square brackets: documents as [Doc name p.N §section], tool numbers as [get_unit_cost_baseline] or [get_change_order].
- Compute day counts and percentages explicitly (e.g. 23 Oct − 11 Oct = 12 days; 142/120 − 1 = +18%).
- Be concise — this is read on a big screen: max 2 bullets per section, each under 35 words, citations included. Lead with the finding.
- Output markdown with exactly these bold headers: **Coverage**, **Notice**, **Pricing**, **Recommendation**
  (for RFIs use **Precedents** and **Recommendation**). Lead each bullet with ✓ (supports the request) or ⚠ (review flag).
- You recommend; the PM decides. Never claim to approve or reject anything. Never invent clauses, dates, or numbers not returned by tools."""

TOOLS = [
    {"type": "function", "function": {"name": "search_documents", "description": "Semantic search over this project's contracts, subcontracts, specifications, daily logs, letters and memos. Returns chunks with doc name, page and section.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "doc_types": {"type": "array", "items": {"type": "string", "enum": ["prime_contract", "subcontract", "spec", "daily_log", "letter", "memo"]}}},
                                                     "required": ["query"]}}},
    {"type": "function", "function": {"name": "find_similar_rfis", "description": "Find past RFIs (all projects, incl. legacy Prolog) similar to a description, with their resolutions, cost and schedule impact.",
                                      "parameters": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}}},
    {"type": "function", "function": {"name": "get_change_order", "description": "Change order header and priced line items (subcontractor, cost code, quantities, unit rates, submitted date, project region).",
                                      "parameters": {"type": "object", "properties": {"co_id": {"type": "string"}}, "required": ["co_id"]}}},
    {"type": "function", "function": {"name": "get_unit_cost_baseline", "description": "Trailing-24-month awarded unit-rate benchmark: P25 / median / P75 and sample size n for a cost code, region and item keyword.",
                                      "parameters": {"type": "object", "properties": {"cost_code": {"type": "string"}, "region": {"type": "string"}, "item_keyword": {"type": "string"}}, "required": ["cost_code", "region", "item_keyword"]}}},
]


def _app_client() -> WorkspaceClient:
    return WorkspaceClient() if IS_DATABRICKS_APP else _local_client()


def _llm() -> OpenAI:
    w = _app_client()
    token = w.config.authenticate()["Authorization"].removeprefix("Bearer ")
    return OpenAI(api_key=token, base_url=GATEWAY_URL or f"{w.config.host.rstrip('/')}/serving-endpoints")


def _vs(query: str, filters: dict, k: int = 5) -> list[dict]:
    w = _app_client()
    r = w.vector_search_indexes.query_index(INDEX, columns=["chunk_id", "doc_name", "doc_type", "page", "section", "text"],
                                            query_text=query, filters_json=json.dumps(filters), num_results=k)
    cols = [c.name for c in r.manifest.columns]
    return [dict(zip(cols, row)) for row in (r.result.data_array or [])]


def _run_tool(name: str, args: dict, user_w: WorkspaceClient) -> Any:
    q = lambda s: s.replace("'", "''")  # noqa: E731  (tool args are interpolated as SQL string literals)
    if name == "search_documents":
        f = {"project_id": "P-1001"}
        if args.get("doc_types"):
            f["doc_type"] = args["doc_types"]
        else:
            f["doc_type NOT"] = "rfi"
        hits = _vs(args["query"], f)
        return [{"doc": h["doc_name"], "page": int(h["page"]) if h.get("page") is not None else None, "section": h.get("section"), "text": (h.get("text") or "")[:900]} for h in hits]
    if name == "find_similar_rfis":
        hits = _vs(args["description"], {"doc_type": "rfi"}, k=4)
        return [{"rfi": h["doc_name"], "text": h.get("text")} for h in hits]
    if name == "get_change_order":
        return _sql(user_w, f"SELECT * FROM get_change_order('{q(args['co_id'])}')")
    if name == "get_unit_cost_baseline":
        return _sql(user_w, f"SELECT * FROM get_unit_cost_baseline('{q(args['cost_code'])}', '{q(args['region'])}', '{q(args['item_keyword'])}')")
    raise ValueError(f"unknown tool {name}")


SPAN_TYPE = {"search_documents": "RETRIEVER", "find_similar_rfis": "RETRIEVER", "get_change_order": "TOOL", "get_unit_cost_baseline": "TOOL"}
STEP_LABEL = {"search_documents": "Searching contracts & specs", "find_similar_rfis": "Finding similar past RFIs",
              "get_change_order": "Reading change order line items", "get_unit_cost_baseline": "Pulling unit-cost baseline"}


def _setup_mlflow():
    if not IS_DATABRICKS_APP:
        os.environ.setdefault("DATABRICKS_CONFIG_PROFILE", os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(experiment_id=EXPERIMENT_ID)


def run_loop(system: str, tools: list, runner, user_content: Any, inputs: dict, tags: dict, labels: dict, span_types: dict, summarize) -> dict:
    """Shared, MLflow-traced tool-calling loop used by every Control Tower agent."""
    _setup_mlflow()
    client = _llm()
    steps: list[dict] = []
    messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": user_content}]
    with mlflow.start_span(name=tags.get("agent", "agent"), span_type="AGENT") as root:
        root.set_inputs(inputs)
        mlflow.update_current_trace(tags={"app": "construction-control-tower", **tags})
        answer = ""
        for rnd in range(MAX_ROUNDS):
            with mlflow.start_span(name=f"llm_round_{rnd + 1}", span_type="CHAT_MODEL") as s:
                s.set_inputs({"model": MODEL, "n_messages": len(messages)})
                t0 = time.time()
                resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools, max_tokens=1800)
                msg = resp.choices[0].message
                s.set_outputs({"tool_calls": [tc.function.name for tc in (msg.tool_calls or [])], "content": _text(msg.content)[:500],
                               "usage": resp.usage.model_dump() if resp.usage else None, "latency_s": round(time.time() - t0, 2)})
            if not msg.tool_calls:
                answer = _text(msg.content)
                break
            messages.append({"role": "assistant", "content": _text(msg.content), "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                with mlflow.start_span(name=tc.function.name, span_type=span_types.get(tc.function.name, "TOOL")) as ts:
                    ts.set_inputs(args)
                    t0 = time.time()
                    try:
                        result = runner(tc.function.name, args)
                    except Exception as e:  # surface tool errors to the model instead of failing the turn
                        result = {"error": str(e)[:300]}
                    ts.set_outputs(result)
                    dt = round(time.time() - t0, 2)
                steps.append({"tool": tc.function.name, "label": labels.get(tc.function.name, tc.function.name), "args": args, "latency_s": dt,
                              "summary": summarize(tc.function.name, result)})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, default=str)[:12000]})
        root.set_outputs({"answer": answer, "steps": [s["tool"] for s in steps]})
        trace_id = root.trace_id
    host = _app_client().config.host.rstrip("/")
    return {"answer": answer, "steps": steps, "trace_id": trace_id,
            "trace_url": f"{host}/ml/experiments/{EXPERIMENT_ID}/traces?selectedEvaluationId={trace_id}", "model": MODEL}


def ask(item: dict, question: str, user_w: WorkspaceClient, actor: str) -> dict:
    return run_loop(SYSTEM, TOOLS, lambda n, a: _run_tool(n, a, user_w), f"Item: {json.dumps(item)}\nQuestion: {question}",
                    {"item": item, "question": question, "user": actor}, {"agent": "resolve_agent", "tab": "resolve", "item": item.get("id", ""), "user": actor},
                    STEP_LABEL, SPAN_TYPE, _summarize)


def _text(content: Any) -> str:
    """Chat content may be a string or a list of content parts — return the text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(p.get("text", "") if isinstance(p, dict) else getattr(p, "text", "") or "" for p in content)


def _summarize(tool: str, result: Any) -> str:
    if isinstance(result, dict) and "error" in result:
        return "error: " + result["error"][:80]
    if tool == "search_documents":
        return ", ".join(sorted({f"{r['doc'].replace('.pdf', '')} p.{r['page']}" for r in result}))[:160]
    if tool == "find_similar_rfis":
        return ", ".join(r["rfi"] for r in result)
    if tool == "get_unit_cost_baseline" and result:
        r = result[0]
        return f"{r['item_desc']}: median ${r['median']} (P25 ${r['p25']}–P75 ${r['p75']}, n={r['n']})"
    if tool == "get_change_order" and result:
        return f"{result[0]['co_id']} · {result[0]['subcontractor']} · {len(result)} line items"
    return f"{len(result) if isinstance(result, list) else 1} result(s)"
