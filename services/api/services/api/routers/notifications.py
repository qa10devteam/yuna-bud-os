"""Faza 14 — Notifications router with SSE.

Fixes:
- Cursor pagination encodes (created_at, id) for proper tiebreaking
- All mutations scoped to both user_id AND org_id (tenant isolation)
- SSE stream returns graceful keepalive if notifications table missing
- /unread-count fast COUNT endpoint
- Concrete routes declared BEFORE parameterized routes
- Consistent {"error", "message"} error responses
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import AsyncGenerator

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])


# ─── helpers ──────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "body": row.body,
        "read": row.read,
        "link": row.link,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _decode_cursor(cursor: str) -> dict:
    """Decode base64-encoded JSON cursor. Raises HTTPException on bad input."""
    try:
        return json.loads(base64.b64decode(cursor).decode())
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_cursor", "message": "Nieprawidłowy cursor"},
        )


def _encode_cursor(row) -> str:
    """Encode (created_at, id) into a base64 JSON cursor."""
    cd = {"created_at": row.created_at.isoformat(), "id": str(row.id)}
    return base64.b64encode(json.dumps(cd).encode()).decode()


# ─── Concrete routes FIRST — prevents path-param shadowing ────────────────────

@router.get("/count")
@router.get("/unread-count")
def unread_count(user: AuthUser) -> dict:
    """Fast unread notification count for the authenticated user."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            count = conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM notifications"
                    " WHERE user_id = :user_id AND read = false"
                ),
                {"user_id": user.user_id},
            ).scalar() or 0
    except Exception:
        # Table may not exist yet in dev/test environments
        count = 0
    return {"unread_count": int(count)}


@router.get("/stream")
async def notification_stream(user: AuthUser) -> StreamingResponse:
    """SSE stream of new unread notifications. Gracefully handles missing table."""
    engine = get_engine()

    async def event_generator() -> AsyncGenerator[str, None]:
        yield 'data: {"type": "connected", "message": "SSE connected"}\n\n'

        last_ts: str | None = None
        while True:
            try:
                with engine.connect() as conn:
                    query = (
                        "SELECT id, type, title, body, link, created_at"
                        " FROM notifications"
                        " WHERE user_id = :uid AND read = false"
                    )
                    params: dict = {"uid": user.user_id}
                    if last_ts:
                        query += " AND created_at > :last_ts"
                        params["last_ts"] = last_ts
                    query += " ORDER BY created_at ASC LIMIT 10"
                    rows = conn.execute(sa.text(query), params).fetchall()

                for row in rows:
                    data = json.dumps({
                        "id": str(row.id),
                        "type": row.type,
                        "title": row.title,
                        "body": row.body,
                        "link": row.link,
                    })
                    last_ts = row.created_at.isoformat()
                    yield f"data: {data}\n\n"

            except Exception:
                # Table missing or transient DB error — send keepalive, keep loop alive
                yield 'data: {"type": "keepalive"}\n\n'

            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/read-all")
def mark_all_read(user: AuthUser) -> dict:
    """Mark all unread notifications as read — scoped to user AND org (tenant-safe)."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                "UPDATE notifications SET read = true"
                " WHERE user_id = :user_id"
                "   AND org_id = :org_id"
                "   AND read = false"
            ),
            {"user_id": user.user_id, "org_id": user.org_id},
        )
    return {"updated": result.rowcount}


# ─── List (cursor-paginated) ───────────────────────────────────────────────────

@router.get("")
def list_notifications(
    user: AuthUser,
    unread: bool | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List notifications with (created_at, id) cursor pagination.

    The cursor encodes the *last* item seen; the next page starts immediately
    after it using a stable (created_at DESC, id DESC) ordering.
    """
    engine = get_engine()

    conditions: list[str] = ["user_id = :user_id"]
    params: dict = {"user_id": user.user_id, "limit": limit + 1}

    if unread is True:
        conditions.append("read = false")

    if cursor:
        cd = _decode_cursor(cursor)
        # Tuple comparison: rows strictly before (created_at, id) in DESC order
        conditions.append(
            "(created_at < :cursor_ts::timestamptz"
            " OR (created_at = :cursor_ts::timestamptz AND id < :cursor_id::uuid))"
        )
        params["cursor_ts"] = cd["created_at"]
        params["cursor_id"] = cd["id"]

    where = " AND ".join(conditions)

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                f"SELECT id, type, title, body, read, link, created_at"
                f" FROM notifications"
                f" WHERE {where}"
                f" ORDER BY created_at DESC, id DESC"
                f" LIMIT :limit"
            ),
            params,
        ).fetchall()

    items = [_row_to_dict(r) for r in rows[:limit]]
    next_cursor = _encode_cursor(rows[limit - 1]) if len(rows) > limit else None

    return {"items": items, "next_cursor": next_cursor}


# ─── Single-item mutation ──────────────────────────────────────────────────────

@router.post("/{notification_id}/read")
def mark_read(notification_id: str, user: AuthUser) -> dict:
    """Mark a single notification as read — scoped to user AND org (tenant-safe)."""
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                "UPDATE notifications SET read = true"
                " WHERE id = :id"
                "   AND user_id = :user_id"
                "   AND org_id = :org_id"
                " RETURNING id"
            ),
            {"id": notification_id, "user_id": user.user_id, "org_id": user.org_id},
        ).fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Powiadomienie nie znalezione"},
        )
    return {"id": notification_id, "read": True}
