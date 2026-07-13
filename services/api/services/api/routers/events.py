"""Event Bus & Notification system — in-memory pub/sub + SSE stream for real-time updates.

Endpoints:
  GET  /api/v2/events/stream          — SSE stream of real-time events
  POST /api/v2/events/emit            — emit event (internal or from workers)
  GET  /api/v2/notifications          — user notifications (from DB)
  POST /api/v2/notifications/mark-read — mark notifications read
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2", tags=["events"])
logger = logging.getLogger(__name__)


# ── In-memory Event Bus ────────────────────────────────────────────────────────

class EventBus:
    """Simple async pub/sub for SSE streaming."""
    
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
    
    async def subscribe(self) -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.remove(queue)
    
    async def publish(self, event: dict):
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop if subscriber is too slow


_bus = EventBus()


# ── Models ─────────────────────────────────────────────────────────────────────

class EmitEvent(BaseModel):
    event_type: str  # tender.new, tender.updated, pipeline.changed, alert.deadline, agent.done
    payload: dict[str, Any] = {}
    tenant_id: Optional[str] = None


# ── SSE Stream ─────────────────────────────────────────────────────────────────

@router.get("/events/stream")
async def event_stream(request: Request):
    """Server-Sent Events stream for real-time updates."""
    
    async def generate() -> AsyncGenerator[str, None]:
        # Send initial heartbeat
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        
        async for event in _bus.subscribe():
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/events/emit")
async def emit_event(event: EmitEvent) -> dict[str, Any]:
    """Emit event to all connected SSE subscribers."""
    evt = {
        "type": event.event_type,
        "payload": event.payload,
        "timestamp": datetime.utcnow().isoformat(),
        "id": str(uuid.uuid4()),
    }
    await _bus.publish(evt)
    
    # Also persist significant events as notifications
    if event.event_type in ("alert.deadline", "tender.new", "agent.done"):
        _persist_notification(event.event_type, event.payload)
    
    return {"status": "emitted", "subscribers": len(_bus._subscribers), "event_id": evt["id"]}


# ── Notifications (persistent) ─────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
) -> list[dict[str, Any]]:
    """Get user notifications from DB."""
    engine = get_engine()
    
    where_clause = "WHERE read = false" if unread_only else ""
    
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT id, type, title, body, link, read, created_at
            FROM notifications
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :lim
        """), {"lim": limit}).fetchall()
    
    return [{
        "id": str(r[0]),
        "event_type": r[1],
        "title": r[2],
        "body": r[3],
        "link": r[4],
        "read": bool(r[5]),
        "created_at": r[6].isoformat() if r[6] else None,
    } for r in rows]


@router.post("/notifications/mark-read")
def mark_read(notification_ids: list[str] = []) -> dict[str, Any]:
    """Mark notifications as read."""
    engine = get_engine()
    
    if not notification_ids:
        # Mark all
        with engine.begin() as conn:
            result = conn.execute(sa.text("UPDATE notifications SET read = true WHERE read = false"))
        return {"marked": result.rowcount}
    
    with engine.begin() as conn:
        result = conn.execute(sa.text("""
            UPDATE notifications SET read = true
            WHERE id = ANY(:ids::uuid[]) AND read = false
        """), {"ids": notification_ids})
    
    return {"marked": result.rowcount}


def _persist_notification(event_type: str, payload: dict):
    """Store notification in DB."""
    titles = {
        "alert.deadline": f"Deadline: {payload.get('title', 'przetarg')[:50]}",
        "tender.new": f"Nowy przetarg: {payload.get('title', '')[:50]}",
        "agent.done": f"Analiza zakończona: {payload.get('title', '')[:50]}",
    }
    
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("""
                INSERT INTO notifications (id, type, title, body, link, read, created_at)
                VALUES (:id, :evt, :title, :body, :link, false, NOW())
            """), {
                "id": str(uuid.uuid4()),
                "evt": event_type,
                "title": titles.get(event_type, event_type),
                "body": payload.get("action_required", ""),
                "link": payload.get("tender_id", ""),
            })
    except Exception as e:
        logger.warning("Failed to persist notification: %s", e)
