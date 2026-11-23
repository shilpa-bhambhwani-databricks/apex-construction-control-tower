"""Ask the Genie Agent the same question as different identities."""
import base64, os, sys, time
from databricks.sdk import WorkspaceClient
from pathlib import Path
me = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "apex-construction"))
SID = (Path(__file__).parent / ".genie_space_id").read_text().strip()
sec = lambda k: base64.b64decode(me.secrets.get_secret("control-tower", k).value).decode()  # noqa: E731
q = sys.argv[1] if len(sys.argv) > 1 else "Which projects need attention this week, and what's driving it?"
who = sys.argv[2:] or ["presenter", "northeast_pm"]
for persona in who:
    w = me if persona == "presenter" else WorkspaceClient(host=me.config.host, client_id=sec(f"{persona}_client_id"), client_secret=sec(f"{persona}_client_secret"), auth_type="oauth-m2m")
    t0 = time.time()
    m = w.genie.start_conversation_and_wait(SID, q)
    print(f"\n=== {persona}  ({time.time()-t0:.0f}s)  status={m.status}")
    for a in m.attachments or []:
        if a.text and a.text.content: print("TEXT:", a.text.content[:700])
        if a.query:
            print("SQL:", (a.query.query or "")[:400].replace("\n", " "))
            r = w.genie.get_message_attachment_query_result(SID, m.conversation_id, m.message_id or m.id, a.attachment_id)
            sr = r.statement_response
            if sr and sr.result: print("ROWS:", (sr.result.data_array or [])[:8])
