"""Faza 3 — Tender Bookmarks / Pipeline API.

Endpoints:
  GET    /api/v2/bookmarks/stats       — statystyki kanban (count per stage + overdue)
  GET    /api/v2/bookmarks             — lista przetargów w pipeline (paginacja + filtry)
  POST   /api/v2/bookmarks             — dodaj przetarg do pipeline
  GET    /api/v2/bookmarks/{id}        — szczegóły z enrichment z historical_tenders
  PATCH  /api/v2/bookmarks/{id}        — zmień stage/priority/notes/tags/due_date
  DELETE /api/v2/bookmarks/{id}        — usuń z pipeline
  GET    /api/v2/bookmarks/export      — eksport do CSV (wszystkie w pipeline)

Tabela: tender_bookmark (UNIQUE idx per tenant+ht_id / tenant+tender_id)
Stage flow: watching → analyzing → bidding → won/lost/passed
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/bookmarks", tags=["tender-bookmarks"])

VALID_STAGES = ("watching", "analyzing", "bidding", "won", "lost", "passed")
VALID_SORT = {"priority", "created_at", "updated_at", "due_date", "ht_date"}


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


def _require_org(user: Any) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="Użytkownik nie należy do żadnej organizacji")
    return user.org_id


# ─── Schematy ─────────────────────────────────────────────────────────────────

class BookmarkCreate(BaseModel):
    ht_id: str | None = None
    tender_id: str | None = None
    stage: str = "watching"
    priority: int = Field(3, ge=1, le=5)
    notes: str | None = Field(None, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    due_date: str | None = None

    @model_validator(mode="after")
    def validate_source_and_stage(self) -> "BookmarkCreate":
        if not self.ht_id and not self.tender_id:
            raise ValueError("Podaj ht_id lub tender_id")
        if self.ht_id and self.tender_id:
            raise ValueError("Podaj tylko jedno: ht_id lub tender_id")
        if self.stage not in VALID_STAGES:
            raise ValueError(f"stage musi być jednym z: {VALID_STAGES}")
        return self


class BookmarkPatch(BaseModel):
    stage: str | None = None
    priority: int | None = Field(None, ge=1, le=5)
    notes: str | None = Field(None, max_length=5000)
    tags: list[str] | None = None
    due_date: str | None = None
    # NOTE: stage validated in endpoint (returns 400 not 422 for API consistency)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Statystyki kanban — count per stage + overdue")
def bookmark_stats(user: AuthUser, db: DB):
    org_id = _require_org(user)
    rows = db.execute(text("""
        SELECT stage,
               count(*) AS n,
               count(*) FILTER (WHERE due_date < CURRENT_DATE) AS overdue,
               count(*) FILTER (WHERE due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 7) AS due_soon,
               round(avg(priority)::numeric, 1) AS avg_priority
        FROM tender_bookmark
        WHERE tenant_id = :org_id
        GROUP BY stage
        ORDER BY
          CASE stage
            WHEN 'watching' THEN 1
            WHEN 'analyzing' THEN 2
            WHEN 'bidding' THEN 3
            WHEN 'won' THEN 4
            WHEN 'lost' THEN 5
            WHEN 'passed' THEN 6
            ELSE 99
          END
    """), {"org_id": org_id}).mappings().all()

    total = db.execute(text(
        "SELECT count(*) FROM tender_bookmark WHERE tenant_id = :org_id"
    ), {"org_id": org_id}).scalar()

    return {"stats": [dict(r) for r in rows], "total": total}


@router.get("", summary="Lista przetargów w pipeline")
def list_bookmarks(
    user: AuthUser,
    db: DB,
    stage: str | None = Query(None, description="Filtr stage"),
    priority: int | None = Query(None, ge=1, le=5, description="Filtr priority"),
    tag: str | None = Query(None, description="Filtr po tagu"),
    sort_by: str = Query("priority", description="Pole sortowania"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    org_id = _require_org(user)

    # Walidacja sort_by
    if sort_by not in VALID_SORT:
        sort_by = "priority"

    conditions = ["b.tenant_id = :org_id"]
    params: dict = {"org_id": org_id, "limit": limit, "offset": offset}

    if stage:
        if stage not in VALID_STAGES:
            raise HTTPException(status_code=400, detail=f"Nieprawidłowy stage: {stage}")
        conditions.append("b.stage = :stage")
        params["stage"] = stage
    if priority:
        conditions.append("b.priority = :priority")
        params["priority"] = priority
    if tag:
        conditions.append(":tag = ANY(b.tags)")
        params["tag"] = tag

    where = " AND ".join(conditions)

    # Bezpieczne sortowanie (whitelist powyżej)
    sort_col = {
        "priority": "b.priority",
        "created_at": "b.created_at",
        "updated_at": "b.updated_at",
        "due_date": "b.due_date",
        "ht_date": "ht.date",
    }[sort_by]
    nulls = "NULLS LAST" if order == "asc" else "NULLS FIRST"
    order_clause = f"{sort_col} {order.upper()} {nulls}"

    rows = db.execute(text(f"""
        SELECT b.id, b.stage, b.priority, b.notes, b.tags, b.due_date,
               b.ht_id, b.tender_id, b.created_at, b.updated_at,
               ht.title AS ht_title, ht.buyer AS ht_buyer,
               ht.province AS ht_province, ht.cpv_code AS ht_cpv,
               ht.estimated_value AS ht_value, ht.date AS ht_date,
               ht.notice_type AS ht_notice_type
        FROM tender_bookmark b
        LEFT JOIN historical_tenders ht ON ht.id = b.ht_id
        WHERE {where}
        ORDER BY {order_clause}, b.created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(
        f"SELECT count(*) FROM tender_bookmark b WHERE {where}"
    ), params).scalar()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/export", summary="Eksport pipeline do CSV")
def export_bookmarks(
    user: AuthUser,
    db: DB,
    stage: str | None = Query(None),
):
    org_id = _require_org(user)
    conditions = ["b.tenant_id = :org_id"]
    params: dict = {"org_id": org_id}

    if stage:
        if stage not in VALID_STAGES:
            raise HTTPException(status_code=400, detail=f"Nieprawidłowy stage: {stage}")
        conditions.append("b.stage = :stage")
        params["stage"] = stage

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT b.id, b.stage, b.priority, b.due_date, b.tags, b.notes,
               b.ht_id, b.created_at, b.updated_at,
               ht.title, ht.buyer, ht.province, ht.cpv_code,
               ht.estimated_value, ht.date AS ht_date
        FROM tender_bookmark b
        LEFT JOIN historical_tenders ht ON ht.id = b.ht_id
        WHERE {where}
        ORDER BY b.priority ASC, b.created_at DESC
    """), params).mappings().all()

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pipeline_export.csv"},
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Dodaj przetarg do pipeline")
def create_bookmark(body: BookmarkCreate, user: AuthUser, db: DB):
    org_id = _require_org(user)

    # Sprawdź duplikat — UNIQUE constraint jest na DB poziomie,
    # ale zwracamy czytelny 409 zamiast 500
    if body.ht_id:
        dup = db.execute(text("""
            SELECT id FROM tender_bookmark
            WHERE tenant_id = :org_id AND ht_id = :ht_id
        """), {"org_id": org_id, "ht_id": body.ht_id}).one_or_none()
    else:
        dup = db.execute(text("""
            SELECT id FROM tender_bookmark
            WHERE tenant_id = :org_id AND tender_id = :tender_id
        """), {"org_id": org_id, "tender_id": body.tender_id}).one_or_none()

    if dup:
        raise HTTPException(status_code=409, detail="Przetarg już w pipeline")

    row = db.execute(text("""
        INSERT INTO tender_bookmark (
            tenant_id, user_id, ht_id, tender_id,
            stage, priority, notes, tags, due_date
        ) VALUES (
            :org_id, :user_id, :ht_id, :tender_id,
            :stage, :priority, :notes, :tags, :due_date
        )
        RETURNING id, stage, priority, ht_id, tender_id, created_at
    """), {
        "org_id": org_id,
        "user_id": user.user_id,
        "ht_id": body.ht_id,
        "tender_id": body.tender_id,
        "stage": body.stage,
        "priority": body.priority,
        "notes": body.notes,
        "tags": body.tags,
        "due_date": body.due_date,
    }).mappings().one()
    db.commit()
    return dict(row)


@router.get("/{bookmark_id}", summary="Szczegóły bookmarku z enrichmentem")
def get_bookmark(bookmark_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    row = db.execute(text("""
        SELECT b.*,
               ht.title, ht.buyer, ht.buyer_nip, ht.province, ht.cpv_code,
               ht.estimated_value, ht.date AS ht_date, ht.notice_type,
               ht.procedure_result, ht.offers_count, ht.contractor_name
        FROM tender_bookmark b
        LEFT JOIN historical_tenders ht ON ht.id = b.ht_id
        WHERE b.id = :id AND b.tenant_id = :org_id
    """), {"id": str(bookmark_id), "org_id": org_id}).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Bookmark nie istnieje")
    return dict(row)


@router.patch("/{bookmark_id}", summary="Aktualizuj stage / notes / priority / tags")
def patch_bookmark(bookmark_id: UUID, body: BookmarkPatch, user: AuthUser, db: DB):
    org_id = _require_org(user)
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Brak pól do aktualizacji")

    # Explicit stage validation → 400 (nie 422 Pydantic)
    if "stage" in updates and updates["stage"] not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowy stage: {updates['stage']}. Dopuszczalne: {VALID_STAGES}")

    set_parts = ", ".join([f"{k} = :{k}" for k in updates])
    updates["id"] = str(bookmark_id)
    updates["org_id"] = org_id

    result = db.execute(text(
        f"UPDATE tender_bookmark SET {set_parts} WHERE id = :id AND tenant_id = :org_id"
    ), updates)
    db.commit()

    if getattr(result, "rowcount", 1) == 0:
        raise HTTPException(status_code=404, detail="Bookmark nie istnieje")

    return {"status": "ok", "id": str(bookmark_id), "updated_fields": list(updates.keys())}


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń z pipeline")
def delete_bookmark(bookmark_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    result = db.execute(text("""
        DELETE FROM tender_bookmark WHERE id = :id AND tenant_id = :org_id
    """), {"id": str(bookmark_id), "org_id": org_id})
    db.commit()
    if getattr(result, "rowcount", 1) == 0:
        raise HTTPException(status_code=404, detail="Bookmark nie istnieje")


# S38/S39: POST /{id}/watch — create a tender_alert from this bookmark

@router.post("/{bookmark_id}/watch", status_code=status.HTTP_201_CREATED, summary="Utwórz alert z bookmarku")
def watch_bookmark(bookmark_id: UUID, user: AuthUser, db: DB):
    """S38/S39: Create a tender_alert using the bookmark as a query template."""
    org_id = _require_org(user)

    # Load the bookmark and its tender info
    bm = db.execute(text("""
        SELECT b.id, b.ht_id, b.tender_id, b.tags, b.notes,
               ht.cpv_code AS ht_cpv, ht.province AS ht_province
        FROM tender_bookmark b
        LEFT JOIN historical_tenders ht ON ht.id = b.ht_id
        WHERE b.id = :id AND b.tenant_id = :org_id
    """), {"id": str(bookmark_id), "org_id": org_id}).mappings().one_or_none()

    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark nie istnieje")

    # Build alert name from bookmark id
    alert_name = f"Watch bookmark {str(bookmark_id)[:8]}"

    # Check for existing alert with same name
    dup = db.execute(text(
        "SELECT id FROM tender_alert WHERE tenant_id = :org_id AND name = :name"
    ), {"org_id": org_id, "name": alert_name}).one_or_none()
    if dup:
        return {"id": str(dup.id), "status": "already_exists"}

    # Build CPV and province filters from the linked tender
    cpv_prefixes = []
    if bm.get("ht_cpv"):
        cpv_prefixes = [str(bm["ht_cpv"])[:5]]  # 5-digit CPV prefix

    provinces = []
    if bm.get("ht_province"):
        provinces = [bm["ht_province"]]

    keywords = list(bm.get("tags") or [])

    row = db.execute(text("""
        INSERT INTO tender_alert (
            tenant_id, user_id, name, cpv_prefixes, provinces, keywords,
            is_active, frequency, channel
        ) VALUES (
            :org_id, :user_id, :name, :cpv_prefixes, :provinces, :keywords,
            true, 'daily', 'email'
        )
        RETURNING id, name, is_active, frequency, channel, created_at
    """), {
        "org_id": org_id,
        "user_id": user.user_id,
        "name": alert_name,
        "cpv_prefixes": cpv_prefixes,
        "provinces": provinces,
        "keywords": keywords,
    }).mappings().one()
    db.commit()
    return dict(row)
