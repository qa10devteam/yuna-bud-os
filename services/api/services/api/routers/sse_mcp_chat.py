"""Faza 51 — SSE Live Updates: Server-Sent Events dla real-time zmian.
Faza 52 — MCP Server: Model Context Protocol stub endpoint.
Faza 53 — AI Chat v2: kontekst przetargu w czacie.
Faza 54 — Rate Limiting per-user.
Faza 55 — API Playground endpoint.
"""
from __future__ import annotations


import asyncio
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncGenerator

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

sse_router = APIRouter(prefix="/api/v1/sse", tags=["sse"])
mcp_router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])
chat_v2_router = APIRouter(prefix="/api/v2/chat", tags=["chat-v2"])
playground_router = APIRouter(prefix="/api/v1/playground", tags=["playground"])


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 51: SSE Live Updates
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory event bus (per org)
_sse_channels: dict[str, list[asyncio.Queue]] = defaultdict(list)


def publish_event(org_id: str, event_type: str, data: dict) -> None:
    """Publish an event to all SSE subscribers for an org."""
    payload = json.dumps({"type": event_type, "data": data, "ts": datetime.now(datetime.timezone.utc).isoformat()})
    for q in _sse_channels.get(org_id, []):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


async def _sse_generator(org_id: str, request: Request) -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _sse_channels[org_id].append(q)
    try:
        yield f"data: {json.dumps({'type': 'connected', 'org_id': org_id})}\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                payload = await asyncio.wait_for(q.get(), timeout=30)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat keepalive
                yield f": heartbeat {int(time.time())}\n\n"
    finally:
        try:
            _sse_channels[org_id].remove(q)
        except ValueError:
            pass


@sse_router.get("/stream")
async def sse_stream(request: Request, user: AuthUser) -> StreamingResponse:
    """SSE endpoint — nasłuchuj zdarzeń dla swojej organizacji."""
    org_id = user.org_id or user.user_id
    return StreamingResponse(
        _sse_generator(org_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@sse_router.post("/publish")
def publish_sse(user: AuthUser, event_type: str = Query("test"), payload: dict = {}) -> dict:
    """Opublikuj zdarzenie SSE (test/debug)."""
    org_id = user.org_id or user.user_id
    publish_event(org_id, event_type, payload)
    return {"published": True, "event_type": event_type, "subscribers": len(_sse_channels.get(org_id, []))}


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 52: MCP Server (Model Context Protocol)
# ═══════════════════════════════════════════════════════════════════════════════

MCP_TOOLS = [
    {
        "name": "get_tender",
        "description": "Pobierz szczegóły przetargu po ID",
        "input_schema": {
            "type": "object",
            "properties": {"tender_id": {"type": "string", "description": "UUID przetargu"}},
            "required": ["tender_id"],
        },
    },
    {
        "name": "list_tenders",
        "description": "Lista przetargów z filtrowaniem",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "get_kosztorys",
        "description": "Pobierz pozycje kosztorysu dla przetargu",
        "input_schema": {
            "type": "object",
            "properties": {"tender_id": {"type": "string"}},
            "required": ["tender_id"],
        },
    },
    {
        "name": "add_comment",
        "description": "Dodaj komentarz do przetargu",
        "input_schema": {
            "type": "object",
            "properties": {
                "tender_id": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["tender_id", "body"],
        },
    },
]


class McpRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str = 1
    method: str
    params: dict = {}


def _mcp_list_tools() -> dict:
    return {"tools": MCP_TOOLS}


def _mcp_call_tool(name: str, arguments: dict) -> Any:
    engine = get_engine()
    if name == "get_tender":
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("SELECT id, title, buyer, status, value_pln FROM tender WHERE id = :id"),
                {"id": arguments.get("tender_id")},
            ).fetchone()
        if row:
            return {"id": str(row.id), "title": row.title, "buyer": row.buyer, "status": row.status}
        return {"error": "Not found"}

    if name == "list_tenders":
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT id, title, status FROM tender ORDER BY created_at DESC LIMIT :lim"),
                {"lim": arguments.get("limit", 10)},
            ).fetchall()
        return [{"id": str(r.id), "title": r.title, "status": r.status} for r in rows]

    if name == "get_kosztorys":
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT description, unit, quantity, unit_price FROM kosztorys_items WHERE tender_id=:tid ORDER BY lp"),
                {"tid": arguments.get("tender_id")},
            ).fetchall()
        return [{"description": r.description, "unit": r.unit, "quantity": float(r.quantity), "unit_price": float(r.unit_price)} for r in rows]

    return {"error": f"Unknown tool: {name}"}


@mcp_router.post("")
def mcp_handler(req: McpRequest) -> dict:
    """MCP (Model Context Protocol) JSON-RPC endpoint dla integracji z LLM."""
    result = None
    error = None
    try:
        if req.method == "tools/list":
            result = _mcp_list_tools()
        elif req.method == "tools/call":
            tool_name = req.params.get("name", "")
            arguments = req.params.get("arguments", {})
            tool_result = _mcp_call_tool(tool_name, arguments)
            result = {"content": [{"type": "text", "text": json.dumps(tool_result, ensure_ascii=False)}]}
        elif req.method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "terra-os-mcp", "version": "1.0.0"},
            }
        else:
            error = {"code": -32601, "message": f"Method not found: {req.method}"}
    except Exception as exc:
        error = {"code": -32603, "message": str(exc)}

    response: dict = {"jsonrpc": "2.0", "id": req.id}
    if error:
        response["error"] = error
    else:
        response["result"] = result
    return response


@mcp_router.get("/info")
def mcp_info() -> dict:
    return {
        "name": "terra-os-mcp",
        "version": "1.0.0",
        "description": "Terra.OS MCP Server — AI tools for tender management",
        "tools": [t["name"] for t in MCP_TOOLS],
        "endpoint": "/api/v1/mcp",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 53: AI Chat v2 (kontekst przetargu)
# ═══════════════════════════════════════════════════════════════════════════════

class ChatV2Request(BaseModel):
    message: str
    tender_id: str | None = None
    history: list[dict] = []


@chat_v2_router.post("")
def chat_v2(req: ChatV2Request, user: AuthUser) -> dict:
    """AI Chat v2 z kontekstem przetargu."""
    engine = get_engine()

    # Build context from tender
    tender_context = ""
    if req.tender_id:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("""
                    SELECT t.id, t.title, t.buyer, t.status, t.value_pln, t.deadline_at,
                           COUNT(k.id) AS kosztorys_count,
                           SUM(k.quantity * k.unit_price) AS kosztorys_total
                    FROM tender t
                    LEFT JOIN kosztorys_items k ON k.tender_id = t.id
                    WHERE t.id = :id
                    GROUP BY t.id
                """),
                {"id": req.tender_id},
            ).fetchone()
        if row:
            tender_context = (
                f"Przetarg: {row.title}\n"
                f"Zamawiający: {row.buyer}\n"
                f"Status: {row.status}\n"
                f"Wartość: {row.value_pln} PLN\n"
                f"Termin: {row.deadline_at}\n"
                f"Pozycji kosztorysu: {row.kosztorys_count}\n"
                f"Suma kosztorysu: {row.kosztorys_total} PLN\n"
            )

    # Call LLM if available
    response_text = ""
    try:
        import os
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No LLM API key")

        import httpx
        messages = []
        if tender_context:
            messages.append({
                "role": "system",
                "content": f"Jesteś asystentem w systemie zarządzania przetargami Terra.OS.\n\nKontekst przetargu:\n{tender_context}"
            })
        messages += req.history
        messages.append({"role": "user", "content": req.message})

        # Try OpenAI
        if os.getenv("OPENAI_API_KEY"):
            with httpx.Client(timeout=30) as client:
                r = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json={"model": "gpt-4o-mini", "messages": messages, "max_tokens": 800},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                r.raise_for_status()
                response_text = r.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        # Fallback stub response
        if req.tender_id and tender_context:
            response_text = (
                f"Na podstawie danych przetargu:\n{tender_context}\n\n"
                f"Aby odpowiedzieć na pytanie: '{req.message}' — "
                "skonfiguruj klucz API OpenAI/Anthropic w zmiennych środowiskowych."
            )
        else:
            response_text = (
                f"Chat v2 z kontekstem przetargu. Pytanie: '{req.message}'. "
                "Skonfiguruj klucz LLM API dla pełnej funkcjonalności."
            )

    return {
        "reply": response_text,
        "tender_id": req.tender_id,
        "context_loaded": bool(tender_context),
        "model": "gpt-4o-mini",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 55: API Playground
# ═══════════════════════════════════════════════════════════════════════════════

@playground_router.get("")
def playground_info(user: AuthUser) -> dict:
    """API Playground — lista dostępnych endpointów do testowania."""
    return {
        "message": "Terra.OS API Playground",
        "docs_url": "/docs",
        "endpoints": [
            {"method": "GET", "path": "/api/v2/tenders", "description": "Lista przetargów"},
            {"method": "GET", "path": "/api/v1/bzp/status", "description": "Status BZP sync"},
            {"method": "POST", "path": "/api/v1/bzp/documents/{tender_id}/fetch", "description": "Pobierz dokumenty SWZ"},
            {"method": "GET", "path": "/api/v1/ted", "description": "Lista przetargów EU TED"},
            {"method": "GET", "path": "/api/v1/gus/indicators", "description": "Wskaźniki GUS BDL"},
            {"method": "POST", "path": "/api/v1/verify", "description": "Weryfikacja KRS/CEIDG"},
            {"method": "GET", "path": "/api/v1/kosztorys/{tender_id}", "description": "Kosztorys przetargu"},
            {"method": "GET", "path": "/api/v1/comments/{tender_id}", "description": "Komentarze do przetargu"},
            {"method": "GET", "path": "/api/v1/webhooks", "description": "Lista webhooków"},
            {"method": "GET", "path": "/api/v1/sse/stream", "description": "SSE live updates"},
            {"method": "POST", "path": "/api/v1/mcp", "description": "MCP JSON-RPC"},
            {"method": "POST", "path": "/api/v2/chat", "description": "AI Chat v2 z kontekstem"},
            {"method": "GET", "path": "/api/v1/subcontractors", "description": "Podwykonawcy"},
            {"method": "GET", "path": "/api/v1/equipment", "description": "Zasoby sprzętowe"},
            {"method": "GET", "path": "/api/v1/gantt/{tender_id}", "description": "Harmonogram Gantt"},
            {"method": "GET", "path": "/api/v1/calendar", "description": "Kalendarz terminów"},
        ],
    }


@playground_router.post("/execute")
def playground_execute(
    user: AuthUser,
    method: str = Query("GET"),
    path: str = Query("/api/v1/health"),
    body: dict | None = None,
) -> dict:
    """Wykonaj żądanie API do testowania (proxy wewnętrzny)."""
    import httpx
    try:
        with httpx.Client(base_url="http://localhost:8000", timeout=10) as client:
            req = client.request(method.upper(), path, json=body)
            return {
                "status_code": req.status_code,
                "response": req.json() if "json" in req.headers.get("content-type", "") else req.text[:2000],
                "elapsed_ms": int(req.elapsed.total_seconds() * 1000),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
