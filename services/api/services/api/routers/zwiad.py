"""M1 — /ingest/run and /tenders/* endpoints."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from services.ingestion.pipeline import run_ingest
from services.ingestion.scorer import OwnerProfileSnap

router = APIRouter(prefix="/api/v1", tags=["zwiad"])


# ──────────────────────────────────────────────────────────────── #
# Schemas
# ──────────────────────────────────────────────────────────────── #

class IngestRunResponse(BaseModel):
    agent_run_id: str
    fetched: int
    created: int
    updated: int
    dropped: int
    errors: int


class TenderListItem(BaseModel):
    id: str
    title: str
    buyer: str | None
    cpv: list[str]
    voivodeship: str | None
    value_pln: float | None
    deadline_at: str | None
    status: str
    match_score: float
    match_reason: str | None


class TenderDetail(TenderListItem):
    source: str
    external_id: str
    published_at: str | None
    url: str | None
    raw: dict


class Page(BaseModel):
    items: list[Any]
    total: int
    cursor: str | None


# ──────────────────────────────────────────────────────────────── #
# POST /ingest/run
# ──────────────────────────────────────────────────────────────── #

@router.post("/ingest/run", response_model=IngestRunResponse, status_code=200)
def ingest_run(
    offline: bool = Query(default=True, description="Use fixtures instead of live BZP API"),
    days_back: int = Query(default=7, ge=1, le=90),
) -> IngestRunResponse:
    """Trigger ingestion pipeline: fetch → normalize → filter → score → upsert."""
    from services.ingestion.pipeline import run_ingest

    engine = get_engine()
    run_id = str(uuid.uuid4())

    result = run_ingest(engine, days_back=days_back, offline=offline)

    return IngestRunResponse(
        agent_run_id=run_id,
        fetched=result.raw_fetched,
        created=result.created,
        updated=result.updated,
        dropped=result.dropped_filter,
        errors=result.errors,
    )


# ──────────────────────────────────────────────────────────────── #
# GET /tenders
# ──────────────────────────────────────────────────────────────── #

@router.get("/tenders", response_model=Page)
def list_tenders(
    status: str | None = Query(default=None),
    cpv: str | None = Query(default=None, description="Comma-separated CPV codes"),
    voiv: str | None = Query(default=None, description="Voivodeship filter"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> Page:
    """List tenders ordered by match_score desc."""
    from sqlalchemy import text
    engine = get_engine()

    # Build WHERE clauses
    conditions = ["1=1"]
    params: dict[str, Any] = {"limit": limit, "offset": 0}

    if cursor:
        try:
            params["offset"] = int(cursor)
        except ValueError:
            pass

    if status:
        conditions.append("t.status = :status")
        params["status"] = status
    if voiv:
        conditions.append("t.voivodeship ILIKE :voiv")
        params["voiv"] = f"%{voiv}%"
    if cpv:
        codes = [c.strip() for c in cpv.split(",")]
        conditions.append("t.cpv && :cpv_arr")
        params["cpv_arr"] = "{" + ",".join(codes) + "}"

    where = " AND ".join(conditions)

    with engine.connect() as conn:
        total_row = conn.execute(
            text(f"SELECT COUNT(*) FROM tender t WHERE {where}"), params
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        rows = conn.execute(
            text(f"""
                SELECT t.id, t.title, t.buyer, t.cpv, t.voivodeship,
                       t.value_pln, t.deadline_at, t.status,
                       t.match_score, t.match_reason
                FROM tender t
                WHERE {where}
                ORDER BY t.match_score DESC NULLS LAST, t.published_at DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()

    next_offset = params["offset"] + limit
    items = []
    for row in rows:
        items.append(TenderListItem(
            id=str(row[0]),
            title=row[1],
            buyer=row[2],
            cpv=list(row[3]) if row[3] else [],
            voivodeship=row[4],
            value_pln=float(row[5]) if row[5] is not None else None,
            deadline_at=str(row[6]) if row[6] else None,
            status=row[7],
            match_score=float(row[8]) if row[8] is not None else 0.0,
            match_reason=row[9],
        ))

    return Page(
        items=items,
        total=total,
        cursor=str(next_offset) if next_offset < total else None,
    )


# ──────────────────────────────────────────────────────────────── #
# GET /tenders/{id}
# ──────────────────────────────────────────────────────────────── #

@router.get("/tenders/{tender_id}", response_model=TenderDetail)
def get_tender(tender_id: str) -> TenderDetail:
    """Get full tender details by ID."""
    import uuid as _uuid
    from sqlalchemy import text
    # Validate UUID format early — invalid UUID causes PG syntax error → 500
    try:
        _uuid.UUID(tender_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tender not found")

    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT t.id, t.title, t.buyer, t.cpv, t.voivodeship,
                       t.value_pln, t.deadline_at, t.status,
                       t.match_score, t.match_reason,
                       t.source, t.external_id, t.published_at, t.url, t.raw
                FROM tender t
                WHERE t.id = :id
            """),
            {"id": tender_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Tender not found")

    return TenderDetail(
        id=str(row[0]),
        title=row[1],
        buyer=row[2],
        cpv=list(row[3]) if row[3] else [],
        voivodeship=row[4],
        value_pln=float(row[5]) if row[5] is not None else None,
        deadline_at=str(row[6]) if row[6] else None,
        status=row[7],
        match_score=float(row[8]) if row[8] is not None else 0.0,
        match_reason=row[9],
        source=row[10] or "",
        external_id=row[11] or "",
        published_at=str(row[12]) if row[12] else None,
        url=row[13],
        raw=dict(row[14]) if row[14] else {},
    )


# ─── PATCH /tenders/{id} — update status ──────────────────────────────────────

class TenderPatch(BaseModel):
    status: str | None = None

@router.patch("/tenders/{tender_id}")
def patch_tender(tender_id: str, body: TenderPatch) -> dict:
    import sqlalchemy as sa
    engine = get_engine()
    updates = {}
    if body.status:
        updates["status"] = body.status
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(f"UPDATE tender SET status = :status WHERE id = :id"),
            {"status": body.status, "id": tender_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tender not found")
    return {"ok": True, "id": tender_id, "status": body.status}
