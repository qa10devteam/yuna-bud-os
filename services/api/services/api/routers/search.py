"""Faza 15 — Full-Text Search router."""
from __future__ import annotations

import base64
import functools
import json
import logging
from datetime import datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query

from terra_db.session import get_engine
from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/search", tags=["search"])

# ─── Lazy FTS config (never called at import time) ─────────────────────────

@functools.lru_cache(maxsize=1)
def _fts_config() -> str:
    """Probe DB once for 'polish' FTS dictionary; fall back to 'simple'."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT to_tsvector('polish', 'test')"))
        return "polish"
    except Exception:
        return "simple"


# ─── Cursor helpers ────────────────────────────────────────────────────────

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


# ─── Endpoint ──────────────────────────────────────────────────────────────

@router.get("")
def search(
    user: AuthUser,
    q: str = Query(..., min_length=2, description="Fraza wyszukiwania"),
    type: str = Query("all", description="all|tenders|documents"),
    source: str | None = Query(None, description="Filtr źródła: bzp|ted|bip"),
    status: str | None = Query(None, description="Filtr statusu przetargu, np. active"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, description="Kursor paginacji (base64 JSON)"),
) -> dict:
    """Full-text search po przetargach i dokumentach z kursorową paginacją."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    fts = _fts_config()
    engine = get_engine()
    items: list[dict] = []

    # Decode cursor if provided
    cursor_ts: str | None = None
    cursor_id: str | None = None
    if cursor:
        cursor_ts, cursor_id = _decode_cursor(cursor)

    search_type = type if type in ("all", "tenders", "documents") else "all"

    # ── Tenders ──────────────────────────────────────────────────────────
    if search_type in ("tenders", "all"):
        # Build optional filter fragments
        source_clause = "AND t.source = :source" if source else ""
        status_clause = "AND t.status = :status" if status else ""
        cursor_clause = (
            "AND (t.created_at, t.id::text) < (:cursor_ts::timestamptz, :cursor_id)"
            if cursor_ts and cursor_id
            else ""
        )

        params: dict = {"tid": tenant_id, "q": q, "limit": limit}
        if source:
            params["source"] = source
        if status:
            params["status"] = status
        if cursor_ts and cursor_id:
            params["cursor_ts"] = cursor_ts
            params["cursor_id"] = cursor_id

        fts_rows: list = []
        with engine.connect() as conn:
            try:
                fts_rows = conn.execute(
                    sa.text(
                        f"""
                        SELECT t.id, t.title, t.buyer, t.status, t.url,
                               t.created_at, t.source,
                               ts_headline(
                                   '{fts}',
                                   coalesce(t.title,'') || ' ' || coalesce(t.buyer,''),
                                   plainto_tsquery('{fts}', :q),
                                   'MaxWords=15, MinWords=5'
                               ) AS excerpt
                        FROM tender t
                        WHERE t.tenant_id = :tid
                          {source_clause}
                          {status_clause}
                          {cursor_clause}
                          AND to_tsvector(
                              '{fts}',
                              coalesce(t.title,'') || ' ' || coalesce(t.buyer,'')
                          ) @@ plainto_tsquery('{fts}', :q)
                        ORDER BY
                            ts_rank(
                                to_tsvector('{fts}', coalesce(t.title,'') || ' ' || coalesce(t.buyer,'')),
                                plainto_tsquery('{fts}', :q)
                            ) DESC,
                            t.created_at DESC,
                            t.id DESC
                        LIMIT :limit
                        """
                    ),
                    params,
                ).fetchall()
            except Exception:
                logger.exception("FTS query failed for q=%r, falling back to ILIKE", exc_info=True)
                fts_rows = []

        # ILIKE fallback — produces a meaningful excerpt from the title
        if not fts_rows:
            with engine.connect() as conn:
                fts_rows = conn.execute(
                    sa.text(
                        f"""
                        SELECT t.id, t.title, t.buyer, t.status, t.url,
                               t.created_at, t.source,
                               coalesce(t.title, '') AS excerpt
                        FROM tender t
                        WHERE t.tenant_id = :tid
                          {source_clause}
                          {status_clause}
                          {cursor_clause}
                          AND (t.title ILIKE :q_like OR t.buyer ILIKE :q_like)
                        ORDER BY t.created_at DESC, t.id DESC
                        LIMIT :limit
                        """
                    ),
                    {**params, "q_like": f"%{q}%"},
                ).fetchall()

        for r in fts_rows:
            items.append(
                {
                    "id": str(r.id),
                    "type": "tender",
                    "title": r.title,
                    "excerpt": r.excerpt or r.title or "",
                    "url": f"/api/v2/tenders/{r.id}",
                    "status": r.status,
                    "source": r.source,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )

    # ── Documents ────────────────────────────────────────────────────────
    if search_type in ("documents", "all"):
        doc_cursor_clause = (
            "AND (td.created_at, td.id::text) < (:cursor_ts::timestamptz, :cursor_id)"
            if cursor_ts and cursor_id
            else ""
        )
        doc_params: dict = {"tid": tenant_id, "q_like": f"%{q}%", "limit": limit}
        if cursor_ts and cursor_id:
            doc_params["cursor_ts"] = cursor_ts
            doc_params["cursor_id"] = cursor_id

        with engine.connect() as conn:
            docs = conn.execute(
                sa.text(
                    f"""
                    SELECT td.id, td.filename, td.tender_id, td.mime, td.created_at
                    FROM tender_document td
                    JOIN tender t ON t.id = td.tender_id
                    WHERE t.tenant_id = :tid
                      {doc_cursor_clause}
                      AND td.filename ILIKE :q_like
                    ORDER BY td.created_at DESC, td.id DESC
                    LIMIT :limit
                    """
                ),
                doc_params,
            ).fetchall()

        for r in docs:
            items.append(
                {
                    "id": str(r.id),
                    "type": "document",
                    "title": r.filename,
                    "excerpt": f"Dokument przetargu {r.tender_id}",
                    "url": f"/api/v2/documents/{r.id}",
                    "mime": r.mime,
                    "source": None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )

    # Build next-page cursor from the last item
    next_cursor: str | None = None
    if len(items) == limit and items:
        last = items[-1]
        last_ts = last.get("created_at")
        last_id = last.get("id")
        if last_ts and last_id:
            next_cursor = _encode_cursor(
                datetime.fromisoformat(last_ts) if last_ts else None,
                last_id,
            )

    return {
        "items": items,
        "total": len(items),
        "query": q,
        "next_cursor": next_cursor,
    }
