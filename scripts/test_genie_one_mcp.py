"""Rehearse the ChatGPT path without ChatGPT: call the Genie One MCP server (the same endpoint the ChatGPT/Claude
Genie plugin uses) as the signed-in CLI user, ask the demo question, poll for the answer.

Usage: python scripts/test_genie_one_mcp.py ["question"]
Docs: https://docs.databricks.com/aws/en/agents/mcp-tools/genie-mcp
"""
import json
import subprocess
import sys
import time

PROFILE = "apex-construction"
PATH = "/ai-gateway/mcp-services/system.ai.genie_one_mcp"
Q = sys.argv[1] if len(sys.argv) > 1 else "What safety items and high-risk activities do we have this week on Project Atlas?"


def rpc(method: str, params: dict, rid: int) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
    out = subprocess.run(["databricks", "api", "post", PATH, "-p", PROFILE, "--json", body], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def text_of(res: dict) -> str:
    r = res.get("result", {})
    return "\n".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text")


t0 = time.time()
first = rpc("tools/call", {"name": "genie_ask", "arguments": {"question": Q}}, 1)
sc = first.get("result", {}).get("structuredContent") or {}
print("ask ->", json.dumps(sc)[:400] or text_of(first)[:400])
cid, rid = sc.get("conversation_id"), sc.get("response_id")
status = sc.get("status")
i = 2
while cid and status in ("in_progress", None) and time.time() - t0 < 240:
    time.sleep(4)
    res = rpc("tools/call", {"name": "genie_poll_response", "arguments": {"conversation_id": cid, "response_id": rid}}, i)
    i += 1
    sc = res.get("result", {}).get("structuredContent") or {}
    status = sc.get("status")
    steps = sc.get("progress_steps") or []
    if steps:
        print(f"[{time.time() - t0:5.0f}s] {status} · {json.dumps(steps[-1])[:200]}")
print(f"\n=== {status} after {time.time() - t0:.0f}s ===")
print(text_of(res)[:4000] if cid else text_of(first)[:4000])
print("\nstructured keys:", list(sc.keys()))
