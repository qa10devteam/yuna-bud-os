"""Faza 16 — Audit Log router."""
from __future__ import annotations

import base64
import json
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/audit", tags=["audit"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class AuditItem(BaseModel):
    id: str
    at: str | None
    actor: str | None
    action: str | None
    entity: str | None
    entity_id: str | None
    detail: dict


class AuditListResponse(BaseModel):
    items: list[AuditItem]
    total: int
    limit: int
    cursor: str | None
    # Deprecated field kept for backward compatibility
    offset: int | None = None


# ---------------------------------------------------------------------------
# Cursor helpers  (at DESC, id DESC)
# ---------------------------------------------------------------------------

def _encode_cursor(at: Any, row_id: Any) -> str:
    payload = {"at": str(at) if at else None, "id": str(row_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str] | None:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return data["at"], data["id"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=AuditListResponse)
def list_audit(
    user: AuthUser,
    tender_id: str | None = Query(None, description="Filter by related tender UUID"),
    actor: str | None = Query(None, description="Filter by actor (user email / system)"),
    entity: str | None = Query(None, description="Filter by entity table name, e.g. 'tender'"),
    action: str | None = Query(None, description="Filter by action verb, e.g. 'status_change'"),
    cursor: str | None = Query(None, description="Opaque pagination cursor (preferred)"),
    limit: int = Query(50, ge=1, le=500),
    # Legacy offset param — honoured when cursor is absent, ignored otherwise
    offset: int = Query(0, ge=0, description="[Deprecated] Use cursor instead"),
) -> AuditListResponse:
    engine = get_engine()
    tenant_id = user.org_id

    conditions: list[str] = ["tenant_id = :tenant_id"]
    params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit}

    if tender_id:
        # Use CAST instead of ::uuid to be param-safe
        conditions.append("entity_id = CAST(:tender_id AS uuid)")
        params["tender_id"] = tender_id

    if actor:
        conditions.append("actor ILIKE :actor")
        params["actor"] = f"%{actor}%"

    if entity:
        conditions.append("entity = :entity")
        params["entity"] = entity

    if action:
        conditions.append("action = :action")
        params["action"] = action

    where = " AND ".join(conditions)

    # Cursor-based pagination takes precedence over legacy offset
    cursor_clause = ""
    use_offset = 0
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded:
            c_at, c_id = decoded
            # DESC ordering: next page rows come strictly after the cursor position
            cursor_clause = (
                "AND (at < :cursor_at "
                "OR (at = :cursor_at AND id < CAST(:cursor_id AS uuid)))"
            )
            params["cursor_at"] = c_at
            params["cursor_id"] = c_id
        # ignore legacy offset when cursor is present
    else:
        use_offset = offset

    params["offset"] = use_offset

    # Total always counts without cursor so the number is stable across pages
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset", "cursor_at", "cursor_id")}
    with engine.connect() as conn:
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM audit_log WHERE {where}"),
            count_params,
        ).scalar() or 0

        rows = conn.execute(
            sa.text(
                f"""SELECT id, at, actor, action, entity, entity_id, detail
                   FROM audit_log
                   WHERE {where} {cursor_clause}
                   ORDER BY at DESC, id DESC
                   LIMIT :limit OFFSET :offset"""
            ),
            params,
        ).fetchall()

    items: list[AuditItem] = [
        AuditItem(
            id=str(r.id),
            at=r.at.isoformat() if r.at else None,
            actor=r.actor,
            action=r.action,
            entity=r.entity,
            entity_id=str(r.entity_id) if r.entity_id else None,
            detail=r.detail if isinstance(r.detail, dict) else {},
        )
        for r in rows
    ]

    # Build next cursor from the last row returned
    next_cursor: str | None = None
    if len(items) == limit and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last.at, last.id)

    return AuditListResponse(
        items=items,
        total=int(total),
        limit=limit,
        cursor=next_cursor,
        offset=use_offset if not cursor else None,
    )


# ---------------------------------------------------------------------------
# S32/S33: /trail convenience endpoint
# ---------------------------------------------------------------------------

@router.get("/trail")
def get_audit_trail(
    user: AuthUser,
    limit: int = 50,
    entity_kind: str | None = None,
) -> list[dict]:
    """S32/S33: Simplified audit trail — last N entries filtered by entity_kind."""
    engine = get_engine()
    params: dict = {"tid": str(user.org_id), "lim": limit}
    q = "SELECT * FROM audit_log WHERE tenant_id = :tid"
    if entity_kind:
        q += " AND entity = :ek"
        params["ek"] = entity_kind
    q += " ORDER BY at DESC LIMIT :lim"
    with engine.connect() as conn:
        rows = conn.execute(sa.text(q), params).fetchall()
    return [dict(r._mapping) for r in rows]
