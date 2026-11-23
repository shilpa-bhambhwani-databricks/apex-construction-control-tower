"""Genie Conversation API proxy.
Docs: https://docs.databricks.com/aws/en/genie/conversation-api
"""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .auth import user_client

router = APIRouter(prefix="/api/genie")
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")
MAX_ROWS = 50


class AskBody(BaseModel):
    question: str
    conversation_id: Optional[str] = None


@router.post("/ask")
def ask(body: AskBody, request: Request):
    if not GENIE_SPACE_ID:
        raise HTTPException(503, "GENIE_SPACE_ID is not configured")
    w = user_client(request)
    try:
        if body.conversation_id:
            msg = w.genie.create_message_and_wait(GENIE_SPACE_ID, body.conversation_id, body.question)
        else:
            msg = w.genie.start_conversation_and_wait(GENIE_SPACE_ID, body.question)
    except Exception as e:  # surface Genie/permission errors to the UI
        raise HTTPException(502, f"Genie error: {e}") from e

    text, sql, table, suggested = None, None, None, []
    for att in msg.attachments or []:
        if att.text and att.text.content:
            text = att.text.content
        if att.suggested_questions and att.suggested_questions.questions:
            suggested = list(att.suggested_questions.questions)
        if att.query:
            sql = att.query.query
            text = text or att.query.description
            try:
                res = w.genie.get_message_attachment_query_result(
                    GENIE_SPACE_ID, msg.conversation_id, msg.message_id or msg.id, att.attachment_id
                )
                sr = res.statement_response
                if sr and sr.manifest and sr.manifest.schema and sr.result:
                    cols = [c.name for c in sr.manifest.schema.columns or []]
                    table = {"columns": cols, "rows": (sr.result.data_array or [])[:MAX_ROWS]}
            except Exception:
                pass  # answer text + SQL are still useful without the result rows
    if msg.error and not (text or sql):
        raise HTTPException(502, f"Genie error: {msg.error}")
    return {
        "conversation_id": msg.conversation_id,
        "message_id": msg.message_id or msg.id,
        "text": text,
        "sql": sql,
        "table": table,
        "suggested_questions": suggested,
    }
