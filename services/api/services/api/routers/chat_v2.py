"""Chat V2 — multi-turn chat widget with context injection + tool calls.

POST /api/v2/chat/sessions              — create session
POST /api/v2/chat/sessions/{id}/messages — send message, SSE response
GET  /api/v2/chat/sessions/{id}         — get session history
GET  /api/v2/chat/sessions              — list sessions (auth-scoped)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import sqlalchemy as sa

from terra_db.session import get_engine
from services.ai.vllm_client import get_llm_client, TERRA_SYSTEM_PROMPT
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/chat", tags=["chat-v2"])
logger = logging.getLogger(__name__)

# ─── Keyword routing map ──────────────────────────────────────────────────────

_TOOL_MAP = {
    "search": ["szukaj", "znajdź", "przetarg", "tender", "nowe przetargi"],
    "kpi":    ["pipeline", "kpi", "statystyk", "ile przetarg", "wyniki"],
    "icb":    ["cena", "materiał", "cennik", "icb", "intercenbud", "koszt materiał",
               "ile kosztuje", "stawka", "robocizna", "kruszywo", "beton", "stal",
               "drewno", "izolacja", "ceramika", "instalacja"],
    "risk":   ["ryzyko", "zmienność", "volatile", "drożeje", "wzrost cen", "inflacja mat"],
    "competitor": ["konkurent", "konkurencja", "kto wygrał", "wygrała firma"],
}


def _classify_intent(msg: str) -> str | None:
    msg_lower = msg.lower()
    for tool, keywords in _TOOL_MAP.items():
        if any(kw in msg_lower for kw in keywords):
            return tool
    return None


# ─── Tool implementations ────────────────────────────────────────────────────

def _tool_search_tenders(engine, tenant_id: str, query: str) -> str:
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, title, value_pln, match_score, status, deadline_at
            FROM tender WHERE tenant_id=:tid
            AND to_tsvector('simple', COALESCE(title,'') || ' ' || COALESCE(buyer,''))
                @@ plainto_tsquery('simple', :q)
            ORDER BY match_score DESC NULLS LAST, created_at DESC LIMIT 6
        """), {"tid": tenant_id, "q": query}).fetchall()
    if not rows:
        return "Nie znaleziono przetargów pasujących do zapytania."
    lines = ["Znalezione przetargi:"]
    for r in rows:
        dl = f", deadline: {str(r[5])[:10]}" if r[5] else ""
        lines.append(f"- [{r[4]}] {r[1]} | {r[2] or '?'} PLN | score: {r[3]}{dl} | id:{r[0]}")
    return "\n".join(lines)


def _tool_get_pipeline_kpi(engine, tenant_id: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT COUNT(*) total,
                   COUNT(*) FILTER (WHERE status='won') won,
                   COUNT(*) FILTER (WHERE status='active') active,
                   COALESCE(SUM(value_pln) FILTER (WHERE status NOT IN ('lost','rejected')), 0) pipeline_val,
                   COALESCE(SUM(value_pln) FILTER (WHERE status='won'), 0) won_val
            FROM tender WHERE tenant_id=:tid
        """), {"tid": tenant_id}).fetchone()
    return (
        f"Pipeline ({tenant_id}): {row[0]} przetargów łącznie | "
        f"{row[2]} aktywnych | {row[1]} wygranych (wartość: {int(row[4]):,} PLN) | "
        f"wartość pipeline: {int(row[3]):,} PLN"
    )


def _tool_icb_prices(engine, query: str) -> str:
    with engine.connect() as conn:
        lq = conn.execute(sa.text(
            "SELECT kwartalrok, kwartalnr FROM icb_ceny_srednie ORDER BY kwartalrok DESC, kwartalnr DESC LIMIT 1"
        )).fetchone()
        if not lq:
            return "Brak danych ICB."
        rok, nr = lq[0], lq[1]
        rows = conn.execute(sa.text("""
            SELECT nazwa, symbol, jednostka, cena_netto, category
            FROM icb_ceny_srednie
            WHERE kwartalrok=:rok AND kwartalnr=:nr AND cena_netto > 0
              AND (nazwa ILIKE :q OR symbol ILIKE :q OR category ILIKE :q)
            ORDER BY cena_netto DESC LIMIT 8
        """), {"rok": rok, "nr": nr, "q": f"%{query}%"}).fetchall()
    if not rows:
        return f"Nie znaleziono materiałów ICB dla: {query}"
    lines = [f"Ceny materiałów ICB ({rok}-Q{nr}):"]
    for r in rows:
        lines.append(f"- {r[0]} [{r[1]}]: {float(r[3]):.2f} PLN/{r[2]} (kat: {r[4]})")
    return "\n".join(lines)


def _tool_material_risk(engine) -> str:
    from .icb_advanced import volatility_matrix
    try:
        matrix = volatility_matrix(quarters=4)
        high = [m for m in matrix if m["risk_level"] == "high"]
        if not high:
            return "Wszystkie kategorie materiałów: ryzyko cenowe NISKIE w ostatnich 4 kwartałach."
        lines = ["⚠️ Kategorie z WYSOKIM ryzykiem cenowym (CV > 0.15):"]
        for m in high[:8]:
            lines.append(f"- {m['category']} ({m['typ_rms']}): CV={m['cv']:.3f}, śr.cena={m['mean_price']:.2f}")
        return "\n".join(lines)
    except Exception as e:
        return f"Błąd analizy ryzyka: {e}"


def _tool_icb_cena(query: str) -> str:
    try:
        from ..intelligence.icb_service import search_icb, get_latest_quarter
        rok, nr = get_latest_quarter()
        results = search_icb(query, kwartalrok=rok, kwartalnr=nr, limit=5)
        if not results:
            return f"Nie znaleziono cen ICB dla: {query}"
        lines = [f"Ceny ICB ({rok}-Q{nr}) dla '{query}':"]
        for r in results:
            nazwa = r.get("nazwa") or r.get("name", "?")
            symbol = r.get("symbol", "")
            cena = r.get("cena_netto") or r.get("price", 0)
            jednostka = r.get("jednostka") or r.get("unit", "szt")
            kategoria = r.get("category", "")
            lines.append(f"- {nazwa} [{symbol}]: {float(cena):.2f} PLN/{jednostka} (kat: {kategoria})")
        return "\n".join(lines)
    except Exception as e:
        logger.warning("icb_cena tool failed: %s", e)
        return f"Błąd wyszukiwania ICB: {e}"


def _tool_competitor_wins(engine, tenant_id: str, query: str) -> str:
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT contractor_name, contractor_nip, COUNT(*) wins,
                   SUM(amount) total_val
            FROM historical_tenders
            WHERE title ILIKE :q OR contractor_name ILIKE :q
            GROUP BY contractor_name, contractor_nip
            ORDER BY total_val DESC LIMIT 6
        """), {"q": f"%{query}%"}).fetchall()
    if not rows:
        return f"Brak danych o wygranych dla: {query}"
    lines = [f"Wyniki historyczne dla '{query}':"]
    for r in rows:
        lines.append(f"- {r[0]} (NIP: {r[1]}): {r[2]} wygranych, wartość: {int(r[3] or 0):,} PLN")
    return "\n".join(lines)


def _build_context(engine, session_data: dict, tenant_id: str) -> str:
    """Build rich context string from session metadata + tender analysis."""
    parts = []
    if session_data.get("page_context"):
        parts.append(f"Użytkownik jest na stronie: {session_data['page_context']}")
    if session_data.get("tender_id"):
        try:
            with engine.connect() as conn:
                # Full tender context
                row = conn.execute(sa.text("""
                    SELECT title, buyer, value_pln, deadline_at, status, match_score,
                           nuts_code, cpv
                    FROM tender WHERE id=:id
                """), {"id": session_data["tender_id"]}).fetchone()
                if row:
                    parts.append(
                        f"PRZETARG: {row[0]}\n"
                        f"  Zamawiający: {row[1]} | Wartość: {row[2]} PLN | "
                        f"Deadline: {str(row[3])[:10] if row[3] else '?'} | "
                        f"Status: {row[4]} | Score dopasowania: {row[5]} | "
                        f"Region: {row[6]} | CPV: {row[7]}"
                    )
                # Analysis context if exists
                analysis = conn.execute(sa.text(
                    "SELECT summary_md AS summary FROM analysis WHERE tender_id=:id LIMIT 1"
                ), {"id": session_data["tender_id"]}).fetchone()
                if analysis:
                    parts.append(
                        f"ANALIZA AI: {str(analysis[0])[:400]}"
                    )
        except Exception as e:
            logger.warning("Context build failed: %s", e)
    return "\n".join(parts) if parts else ""


def _dispatch_tool(engine, tenant_id: str, intent: str, msg: str) -> str:
    """Dispatch to appropriate tool based on classified intent."""
    if intent == "search":
        return _tool_search_tenders(engine, tenant_id, msg)
    elif intent == "kpi":
        return _tool_get_pipeline_kpi(engine, tenant_id)
    elif intent == "icb":
        # Extract search term
        q = msg.lower()
        for stop in ["jaka jest cena", "ile kosztuje", "cennik", "cena", "materiał",
                     "stawka", "koszt"]:
            q = q.replace(stop, "").strip()
        search_q = q.strip() if len(q.strip()) > 2 else msg
        result = _tool_icb_cena(search_q)
        if "Błąd" in result or "Nie znaleziono" in result:
            result = _tool_icb_prices(engine, search_q)
        return result
    elif intent == "risk":
        return _tool_material_risk(engine)
    elif intent == "competitor":
        return _tool_competitor_wins(engine, tenant_id, msg)
    return ""


# ─── Endpoints ────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    page_context: str | None = None
    tender_id: str | None = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


@router.post("/sessions")
def create_session(body: CreateSessionRequest, user: AuthUser) -> dict:
    """Create a new chat session."""
    engine = get_engine()
    session_id = str(uuid.uuid4())
    tenant_id = str(user.org_id) if user.org_id else "demo"
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO chat_session (id, tenant_id, page_context, tender_id)
            VALUES (:id, :tid, :ctx, :tender)
        """), {"id": session_id, "tid": tenant_id,
               "ctx": body.page_context, "tender": body.tender_id})
    return {"session_id": session_id, "tenant_id": tenant_id}


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: str, body: SendMessageRequest, user: AuthUser) -> StreamingResponse:
    """Send a message and get SSE-streamed AI response."""
    engine = get_engine()
    tenant_id = str(user.org_id) if user.org_id else "demo"

    # Load session — verify ownership
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT tenant_id, page_context, tender_id, messages, summary FROM chat_session WHERE id=:id"
        ), {"id": session_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(row[0]) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    session_data = {"page_context": row[1], "tender_id": str(row[2]) if row[2] else None}
    messages: list = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
    summary = row[4] or ""

    # Add user message
    messages.append({"role": "user", "content": body.message, "ts": datetime.now(timezone.utc).isoformat()})

    # Build context + tool result
    context = _build_context(engine, session_data, tenant_id)
    intent = _classify_intent(body.message)
    tool_result = _dispatch_tool(engine, tenant_id, intent, body.message) if intent else ""

    # Compose system prompt
    system_parts = [TERRA_SYSTEM_PROMPT]
    if context:
        system_parts.append(f"\nKONTEKST SESJI:\n{context}")
    if summary:
        system_parts.append(f"\nPODSUMOWANIE WCZEŚNIEJSZYCH TUR:\n{summary}")
    if tool_result:
        system_parts.append(f"\nDANE Z SYSTEMU (użyj do konkretnej odpowiedzi):\n{tool_result}")
    system = "\n".join(system_parts)

    # Build proper messages array for LLM (last 12 turns, preserving role alternation)
    llm_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[-12:]
    ]

    llm = get_llm_client()

    def stream():
        full_response = []
        try:
            for token in llm.generate_stream_messages(llm_messages, system=system, max_tokens=4096):
                full_response.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            logger.exception("LLM stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Błąd AI — spróbuj ponownie.'})}\n\n"
            return

        # Save response
        assistant_msg = "".join(full_response)
        messages.append({"role": "assistant", "content": assistant_msg,
                         "ts": datetime.now(timezone.utc).isoformat()})

        # Rolling compression — keep last 12, summarize older
        new_summary = summary
        if len(messages) > 24:
            old_messages = messages[:-12]
            old_text = "\n".join(
                f"{m['role'].upper()}: {m['content'][:150]}" for m in old_messages
            )
            try:
                new_summary = llm.generate(
                    f"Podsumuj zwięźle tę rozmowę w 3-4 zdaniach, zachowaj kluczowe fakty:\n{old_text}",
                    system="Jesteś asystentem do podsumowań. Odpowiadaj po polsku. Bądź konkretny.",
                    max_tokens=512,
                )
                messages_to_save = messages[-12:]
            except Exception:
                messages_to_save = messages[-20:]
        else:
            messages_to_save = messages

        try:
            with engine.begin() as conn:
                conn.execute(sa.text("""
                    UPDATE chat_session
                    SET messages=cast(:msgs as jsonb), summary=:sum, updated_at=NOW()
                    WHERE id=:id
                """), {"id": session_id, "msgs": json.dumps(messages_to_save),
                       "sum": new_summary})
        except Exception as e:
            logger.error("Failed to save session: %s", e)

        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user: AuthUser) -> dict:
    """Get session with full history (auth-scoped)."""
    engine = get_engine()
    tenant_id = str(user.org_id) if user.org_id else "demo"
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id, tenant_id, page_context, tender_id, messages, summary, created_at, updated_at "
            "FROM chat_session WHERE id=:id"
        ), {"id": session_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(row[1]) != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "id": str(row[0]), "tenant_id": str(row[1]),
        "page_context": row[2],
        "tender_id": str(row[3]) if row[3] else None,
        "messages": row[4] if isinstance(row[4], list) else (json.loads(row[4]) if row[4] else []),
        "summary": row[5],
        "created_at": str(row[6]), "updated_at": str(row[7]),
    }


@router.get("/sessions")
def list_sessions(user: AuthUser, limit: int = 20) -> list[dict]:
    """List recent chat sessions (tenant auto-resolved from auth token)."""
    tenant_id = str(user.org_id) if user.org_id else "demo"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, page_context, tender_id, created_at, updated_at
            FROM chat_session WHERE tenant_id=:tid
            ORDER BY updated_at DESC LIMIT :lim
        """), {"tid": tenant_id, "lim": min(limit, 50)}).fetchall()
    return [
        {"id": str(r[0]), "page_context": r[1], "tender_id": str(r[2]) if r[2] else None,
         "created_at": str(r[3]), "updated_at": str(r[4])}
        for r in rows
    ]
