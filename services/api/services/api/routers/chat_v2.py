"""Chat V2 — multi-turn chat widget with context injection + tool calls.

POST /api/v2/chat/sessions              — create session
POST /api/v2/chat/sessions/{id}/messages — send message, SSE response
GET  /api/v2/chat/sessions/{id}         — get session history
GET  /api/v2/chat/sessions              — list sessions
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine
from services.ai.vllm_client import get_llm_client, TERRA_SYSTEM_PROMPT

router = APIRouter(prefix="/api/v2/chat", tags=["chat-v2"])
logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    tenant_id: str
    page_context: str | None = None
    tender_id: str | None = None


class SendMessageRequest(BaseModel):
    message: str


# ─── Tool implementations ────────────────────────────────────────────────────

def _tool_search_tenders(engine, tenant_id: str, query: str) -> str:
    """Internal tool: search tenders by keyword."""
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, title, value_pln, match_score
            FROM tender WHERE tenant_id=:tid
            AND to_tsvector('simple', COALESCE(title,'') || ' ' || COALESCE(buyer,''))
                @@ plainto_tsquery('simple', :q)
            ORDER BY match_score DESC NULLS LAST LIMIT 5
        """), {"tid": tenant_id, "q": query}).fetchall()
    if not rows:
        return "Nie znaleziono przetargów pasujących do zapytania."
    lines = [f"- {r[1]} (wartość: {r[2]} PLN, score: {r[3]})" for r in rows]
    return "Znalezione przetargi:\n" + "\n".join(lines)


def _tool_get_pipeline_kpi(engine, tenant_id: str) -> str:
    """Internal tool: pipeline stats."""
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT COUNT(*) as total,
                   COUNT(*) FILTER (WHERE status='won') as won,
                   SUM(value_pln) FILTER (WHERE status != 'new') as pipeline_val
            FROM tender WHERE tenant_id=:tid
        """), {"tid": tenant_id}).fetchone()
    return f"Pipeline: {row[0]} przetargów, {row[1]} wygranych, wartość pipeline: {row[2] or 0} PLN"


def _build_context(engine, session_data: dict) -> str:
    """Build context string from session metadata."""
    parts = []
    if session_data.get("page_context"):
        parts.append(f"Użytkownik jest na stronie: {session_data['page_context']}")
    if session_data.get("tender_id"):
        with engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT title, buyer, value_pln, deadline_at FROM tender WHERE id=:id"
            ), {"id": session_data["tender_id"]}).fetchone()
        if row:
            parts.append(f"Kontekst przetargu: {row[0]} | Zamawiający: {row[1]} | Wartość: {row[2]} PLN | Deadline: {row[3]}")
    return "\n".join(parts)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/sessions")
def create_session(body: CreateSessionRequest) -> dict:
    """Create a new chat session."""
    engine = get_engine()
    session_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO chat_session (id, tenant_id, page_context, tender_id)
            VALUES (:id, :tid, :ctx, :tender)
        """), {"id": session_id, "tid": body.tenant_id,
               "ctx": body.page_context, "tender": body.tender_id})
    return {"session_id": session_id}


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: str, body: SendMessageRequest) -> StreamingResponse:
    """Send a message and get SSE-streamed AI response."""
    engine = get_engine()

    # Load session
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT tenant_id, page_context, tender_id, messages, summary FROM chat_session WHERE id=:id"
        ), {"id": session_id}).fetchone()

    if not row:
        def err():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    tenant_id = str(row[0])
    session_data = {"page_context": row[1], "tender_id": str(row[2]) if row[2] else None}
    messages = row[3] if isinstance(row[3], list) else json.loads(row[3]) if row[3] else []
    summary = row[4] or ""

    # Add user message
    messages.append({"role": "user", "content": body.message, "ts": datetime.now(timezone.utc).isoformat()})

    # Build system prompt with context
    context = _build_context(engine, session_data)

    # Check if tool call needed
    tool_result = ""
    msg_lower = body.message.lower()
    if any(kw in msg_lower for kw in ["szukaj", "znajdź", "przetarg", "tender"]):
        tool_result = _tool_search_tenders(engine, tenant_id, body.message)
    elif any(kw in msg_lower for kw in ["pipeline", "kpi", "statystyk", "ile"]):
        tool_result = _tool_get_pipeline_kpi(engine, tenant_id)

    system = TERRA_SYSTEM_PROMPT + f"\n\nKONTEKST SESJI:\n{context}"
    if summary:
        system += f"\n\nPODSUMOWANIE WCZEŚNIEJSZYCH TUR:\n{summary}"
    if tool_result:
        system += f"\n\nWYNIK WYSZUKIWANIA (użyj do odpowiedzi):\n{tool_result}"

    # Build messages for LLM (last 10)
    llm_messages = [{"role": m["role"], "content": m["content"]} for m in messages[-10:]]
    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in llm_messages)

    llm = get_llm_client()

    def stream():
        full_response = []
        try:
            for token in llm.generate_stream(prompt, system=system):
                full_response.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Save assistant message
        assistant_msg = "".join(full_response)
        messages.append({"role": "assistant", "content": assistant_msg, "ts": datetime.now(timezone.utc).isoformat()})

        # Compress if > 20 messages
        new_summary = summary
        if len(messages) > 20:
            old_messages = messages[:-10]
            old_text = "\n".join(f"{m['role']}: {m['content'][:100]}" for m in old_messages)
            try:
                new_summary = llm.generate(
                    f"Podsumuj zwięźle tę rozmowę w 2-3 zdaniach:\n{old_text}",
                    system="Jesteś asystentem do podsumowań. Odpowiadaj po polsku."
                )
                messages_to_save = messages[-10:]
            except Exception:
                messages_to_save = messages
                new_summary = summary
        else:
            messages_to_save = messages

        with engine.begin() as conn:
            conn.execute(sa.text("""
                UPDATE chat_session
                SET messages=:msgs::jsonb, summary=:sum, updated_at=NOW()
                WHERE id=:id
            """), {"id": session_id, "msgs": json.dumps(messages_to_save),
                   "sum": new_summary})

        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    """Get session with full history."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id, tenant_id, page_context, tender_id, messages, summary, created_at, updated_at FROM chat_session WHERE id=:id"
        ), {"id": session_id}).fetchone()
    if not row:
        return {"error": "not_found"}
    return {
        "id": str(row[0]), "tenant_id": str(row[1]),
        "page_context": row[2], "tender_id": str(row[3]) if row[3] else None,
        "messages": row[4] if isinstance(row[4], list) else json.loads(row[4]) if row[4] else [],
        "summary": row[5],
        "created_at": str(row[6]), "updated_at": str(row[7]),
    }


@router.get("/sessions")
def list_sessions(tenant_id: str, limit: int = 20) -> list[dict]:
    """List recent chat sessions."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, page_context, tender_id, created_at, updated_at
            FROM chat_session WHERE tenant_id=:tid
            ORDER BY updated_at DESC LIMIT :lim
        """), {"tid": tenant_id, "lim": limit}).fetchall()
    return [
        {"id": str(r[0]), "page_context": r[1], "tender_id": str(r[2]) if r[2] else None,
         "created_at": str(r[3]), "updated_at": str(r[4])}
        for r in rows
    ]
