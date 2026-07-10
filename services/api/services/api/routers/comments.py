"""Faza 48 — Team Collaboration: komentarze do tenderów, @mentions, historia."""
from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/comments", tags=["collaboration"])


# ─── Schemas ───────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body: str
    parent_id: str | None = None


class CommentUpdate(BaseModel):
    body: str


# ─── Helpers ───────────────────────────────────────────────────────────────

def _extract_mentions(body: str) -> list[str]:
    """Extract @username mentions from comment body."""
    return re.findall(r"@([a-zA-Z0-9_.-]+)", body)


def _encode_cursor(created_at: datetime | None, row_id: str) -> str:
    payload = {
        "created_at": created_at.isoformat() if created_at else None,
        "id": row_id,
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str | None, str | None]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return payload.get("created_at"), payload.get("id")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_cursor", "message": "Nieprawidłowy kursor paginacji"},
        )


def _table_exists(conn: Any, table_name: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=:t)"
        ),
        {"t": table_name},
    ).scalar()
    return bool(r)


def _validate_uuid(value: str, label: str = "id") -> None:
    try:
        uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_uuid", "message": f"Nieprawidłowy {label}: {value}"},
        )


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/{tender_id}")
def list_comments(
    tender_id: str,
    user: AuthUser,
    limit: int = Query(50, ge=1, le=500),
    cursor: str | None = Query(None, description="Kursor paginacji (base64 JSON)"),
) -> dict:
    """Lista komentarzy dla przetargu (z historią zmian) — tenant-isolated."""
    _validate_uuid(tender_id, "tender_id")

    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    cursor_ts: str | None = None
    cursor_id: str | None = None
    if cursor:
        cursor_ts, cursor_id = _decode_cursor(cursor)

    cursor_clause = (
        "AND (c.created_at, c.id::text) > (CAST(:cursor_ts AS TIMESTAMPTZ), :cursor_id)"
        if cursor_ts and cursor_id
        else ""
    )

    params: dict = {"tid": tender_id, "tenant_id": tenant_id, "limit": limit}
    if cursor_ts and cursor_id:
        params["cursor_ts"] = cursor_ts
        params["cursor_id"] = cursor_id

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                f"""
                SELECT c.id, c.tender_id, c.user_id, c.parent_id, c.body,
                       c.mentions, c.edited, c.created_at, c.updated_at,
                       u.email AS user_email
                FROM tender_comments c
                JOIN tender t ON t.id = c.tender_id AND t.tenant_id = :tenant_id
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.tender_id = :tid
                  {cursor_clause}
                ORDER BY c.created_at ASC, c.id ASC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()

        # Total count for tenant-isolated tender
        total = conn.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM tender_comments c
                JOIN tender t ON t.id = c.tender_id AND t.tenant_id = :tenant_id
                WHERE c.tender_id = :tid
                """
            ),
            {"tid": tender_id, "tenant_id": tenant_id},
        ).scalar()

    next_cursor: str | None = None
    if len(rows) == limit and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last.created_at, str(last.id))

    return {
        "tender_id": tender_id,
        "total": int(total or 0),
        "next_cursor": next_cursor,
        "comments": [
            {
                "id": str(r.id),
                "parent_id": str(r.parent_id) if r.parent_id else None,
                "user_id": str(r.user_id) if r.user_id else None,
                "user_email": r.user_email,
                "body": r.body,
                "mentions": list(r.mentions) if r.mentions else [],
                "edited": r.edited,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
    }


@router.post("/{tender_id}")
def create_comment(tender_id: str, comment: CommentCreate, user: AuthUser) -> dict:
    """Dodaj komentarz do przetargu (obsługa @mentions) — tenant-isolated."""
    _validate_uuid(tender_id, "tender_id")

    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    engine = get_engine()
    mentions = _extract_mentions(comment.body)
    rec_id = str(uuid.uuid4())

    with engine.connect() as conn:
        # Verify tender exists AND belongs to current tenant
        row = conn.execute(
            sa.text(
                "SELECT id FROM tender WHERE id = :id AND tenant_id = :tenant_id"
            ),
            {"id": tender_id, "tenant_id": tenant_id},
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Przetarg nie istnieje"},
            )

        if comment.parent_id:
            _validate_uuid(comment.parent_id, "parent_id")
            parent = conn.execute(
                sa.text(
                    "SELECT id FROM tender_comments WHERE id = :id AND tender_id = :tid"
                ),
                {"id": comment.parent_id, "tid": tender_id},
            ).fetchone()
            if not parent:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "message": "Komentarz nadrzędny nie istnieje"},
                )

        conn.execute(
            sa.text(
                """
                INSERT INTO tender_comments (id, tender_id, user_id, parent_id, body, mentions)
                VALUES (:id, :tender_id, :user_id, :parent_id, :body, :mentions)
                """
            ),
            {
                "id": rec_id,
                "tender_id": tender_id,
                "user_id": user.user_id,
                "parent_id": comment.parent_id,
                "body": comment.body,
                "mentions": mentions,
            },
        )
        conn.commit()

    # TODO: trigger notifications for @mentions (Faza 49)
    return {
        "id": rec_id,
        "tender_id": tender_id,
        "mentions": mentions,
        "status": "created",
    }


@router.patch("/{tender_id}/{comment_id}")
def update_comment(
    tender_id: str, comment_id: str, patch: CommentUpdate, user: AuthUser
) -> dict:
    """Edytuj komentarz (tylko autor lub admin/manager) — tenant-isolated."""
    _validate_uuid(tender_id, "tender_id")
    _validate_uuid(comment_id, "comment_id")

    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """
                SELECT c.user_id
                FROM tender_comments c
                JOIN tender t ON t.id = c.tender_id AND t.tenant_id = :tenant_id
                WHERE c.id = :id AND c.tender_id = :tid
                """
            ),
            {"id": comment_id, "tid": tender_id, "tenant_id": tenant_id},
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Komentarz nie istnieje"},
            )
        if str(row.user_id) != user.user_id and user.role not in ("admin", "manager"):
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "message": "Brak uprawnień do edycji komentarza"},
            )
        mentions = _extract_mentions(patch.body)
        conn.execute(
            sa.text(
                """
                UPDATE tender_comments
                SET body = :body, mentions = :mentions, edited = true, updated_at = now()
                WHERE id = :id
                """
            ),
            {"body": patch.body, "mentions": mentions, "id": comment_id},
        )
        conn.commit()

    return {"id": comment_id, "status": "updated", "edited": True}


@router.delete("/{tender_id}/{comment_id}")
def delete_comment(tender_id: str, comment_id: str, user: AuthUser) -> dict:
    """Usuń komentarz (autor lub admin/manager) — tenant-isolated."""
    _validate_uuid(tender_id, "tender_id")
    _validate_uuid(comment_id, "comment_id")

    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """
                SELECT c.user_id
                FROM tender_comments c
                JOIN tender t ON t.id = c.tender_id AND t.tenant_id = :tenant_id
                WHERE c.id = :id AND c.tender_id = :tid
                """
            ),
            {"id": comment_id, "tid": tender_id, "tenant_id": tenant_id},
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Komentarz nie istnieje"},
            )
        if str(row.user_id) != user.user_id and user.role not in ("admin", "manager"):
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "message": "Brak uprawnień do usunięcia"},
            )
        conn.execute(
            sa.text("DELETE FROM tender_comments WHERE id = :id"),
            {"id": comment_id},
        )
        conn.commit()

    return {"id": comment_id, "status": "deleted"}


@router.get("/{tender_id}/activity")
def tender_activity(
    tender_id: str,
    user: AuthUser,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Historia aktywności i zmian dla przetargu — tenant-isolated."""
    _validate_uuid(tender_id, "tender_id")

    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    engine = get_engine()
    with engine.connect() as conn:
        # Verify tender belongs to tenant before exposing activity
        if not conn.execute(
            sa.text("SELECT 1 FROM tender WHERE id = :tid AND tenant_id = :tenant_id"),
            {"tid": tender_id, "tenant_id": tenant_id},
        ).fetchone():
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Przetarg nie istnieje"},
            )

        comments = conn.execute(
            sa.text(
                """
                SELECT c.id, 'comment' AS type, c.body AS detail,
                       u.email AS actor, c.created_at
                FROM tender_comments c
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.tender_id = :tid
                ORDER BY c.created_at DESC LIMIT :limit
                """
            ),
            {"tid": tender_id, "limit": limit},
        ).fetchall()

        audit_rows: list = []
        if _table_exists(conn, "audit_log"):
            try:
                audit_rows = conn.execute(
                    sa.text(
                        """
                        SELECT id, 'audit' AS type,
                               action || ': ' || coalesce(entity, '') AS detail,
                               actor, at AS created_at
                        FROM audit_log
                        WHERE entity_id = CAST(:tid AS UUID)
                        ORDER BY at DESC LIMIT :limit
                        """
                    ),
                    {"tid": tender_id, "limit": limit},
                ).fetchall()
            except Exception:
                logger.warning(
                    "Could not read audit_log for tender_id=%s", tender_id, exc_info=True
                )

    activity = sorted(
        [
            {
                "id": str(r.id),
                "type": r.type,
                "detail": r.detail,
                "actor": r.actor,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in list(comments) + list(audit_rows)
        ],
        key=lambda x: x["created_at"] or "",
        reverse=True,
    )
    return {"tender_id": tender_id, "activity": activity[:limit]}
