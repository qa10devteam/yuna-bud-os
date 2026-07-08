"""M1 — /ingest/run and /tenders/* endpoints."""
from __future__ import annotations

import base64
import json
import re
import unicodedata
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import get_current_user, AuthUser

router = APIRouter(prefix="/api/v1", tags=["zwiad"])


def _normalize_voiv(v: str) -> str:
    """Strip diacritics from a voivodeship name for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", v)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class IngestRunResponse(BaseModel):
    agent_run_id: str
    fetched: int
    created: int
    updated: int
    dropped: int
    errors: int
    bip_stored: int
    dedup_pairs: int


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
    source: str | None
    external_id: str | None
    published_at: str | None
    url: str | None


class TenderDetail(TenderListItem):
    raw: dict


class Page(BaseModel):
    items: list[Any]
    total: int
    cursor: str | None


class TenderPatch(BaseModel):
    status: str | None = None


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------

def _encode_cursor(created_at: Any, row_id: Any) -> str:
    """Encode a (created_at, id) pair as a URL-safe base64 JSON cursor."""
    payload = {"created_at": str(created_at) if created_at else None, "id": str(row_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str] | None:
    """Return (created_at_str, id_str) or None on malformed cursor."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return data["created_at"], data["id"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/ingest/run", response_model=IngestRunResponse, status_code=200)
def ingest_run(
    offline: bool = Query(default=True),
    days_back: int = Query(default=7, ge=1, le=90),
    include_bip: bool = Query(default=False),
    run_dedup: bool = Query(default=True),
) -> IngestRunResponse:
    """Trigger the ingestion pipeline."""
    from services.ingestion.pipeline import run_ingest
    engine = get_engine()
    run_id = str(uuid.uuid4())
    result = run_ingest(
        engine,
        days_back=days_back,
        offline=offline,
        include_bip=include_bip,
        run_dedup=run_dedup,
        bip_max_sites=50,
    )
    return IngestRunResponse(
        agent_run_id=run_id,
        fetched=result.raw_fetched,
        created=result.created,
        updated=result.updated,
        dropped=result.dropped_filter,
        errors=result.errors,
        bip_stored=getattr(result, "bip_stored", 0) or 0,
        dedup_pairs=getattr(result, "dedup_pairs", 0) or 0,
    )


@router.get("/tenders", response_model=Page)
def list_tenders(
    user: AuthUser,
    status: str | None = Query(default=None),
    cpv: str | None = Query(default=None),
    voivodeship: str | None = Query(default=None),
    source: str | None = Query(default=None),
    min_value: float | None = Query(default=None),
    max_value: float | None = Query(default=None),
    hide_duplicates: bool = Query(default=True),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    sort: str | None = Query(default=None),
) -> Page:
    from sqlalchemy import text
    engine = get_engine()
    tenant_id = str(user.org_id or "")

    conditions: list[str] = ["t.tenant_id = :tenant_id"]
    params: dict[str, Any] = {"limit": limit, "tenant_id": tenant_id}

    # Cursor-based keyset pagination (published_at DESC, id DESC)
    # Only applies when sort is by published_at (default); other sorts use offset via cursor.
    cursor_clause = ""
    cursor_offset = 0
    sort_key = sort or "published"
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded:
            c_at, c_id = decoded
            if sort_key == "published":
                # Keyset pagination by (published_at, id)
                cursor_clause = (
                    "AND (t.published_at < :cursor_at "
                    "OR (t.published_at = :cursor_at AND t.id < CAST(:cursor_id AS uuid)))"
                )
                params["cursor_at"] = c_at
                params["cursor_id"] = c_id
            else:
                # For non-published sorts, cursor encodes an offset
                try:
                    cursor_offset = int(c_at) if c_at else 0
                except (ValueError, TypeError):
                    cursor_offset = 0

    VALID_STATUSES = {"new", "matched", "watching", "analyzing", "estimated", "decided_go", "decided_nogo", "archived"}
    if status:
        if status not in VALID_STATUSES:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Valid values: {sorted(VALID_STATUSES)}"
            )
        conditions.append("t.status = CAST(:status AS tender_status)")
        params["status"] = status

    if voivodeship:
        conditions.append("(t.voivodeship ILIKE :voiv OR t.voivodeship ILIKE :voiv_plain)")
        params["voiv"] = f"%{voivodeship}%"
        params["voiv_plain"] = f"%{_normalize_voiv(voivodeship)}%"

    if source:
        conditions.append("t.source = CAST(:source AS source_kind)")
        params["source"] = source.lower()

    if cpv:
        codes = [c.strip() for c in cpv.split(",")]
        # A full CPV code looks like '45111200-0' (10 chars with dash) or
        # '45111200' (8 digits). Treat a single code without comma as a prefix
        # search if it's shorter than a full 8-digit CPV (i.e. < 9 chars before dash).
        if len(codes) == 1:
            code = codes[0]
            # Full CPV: 8 digits optionally followed by '-X' (e.g. '45111200-0')
            is_full_cpv = bool(re.match(r'^\d{8}(-\d)?$', code))
            if is_full_cpv:
                # Exact or near-exact: use array overlap
                conditions.append("t.cpv && :cpv_arr")
                params["cpv_arr"] = "{" + code + "}"
            else:
                # Prefix search: matches '45', '451', '4511', '45111200', etc.
                conditions.append(
                    "EXISTS (SELECT 1 FROM unnest(t.cpv) c WHERE c LIKE :cpv_prefix)"
                )
                params["cpv_prefix"] = code + "%"
        else:
            # Multiple comma-separated codes: exact array overlap
            conditions.append("t.cpv && :cpv_arr")
            params["cpv_arr"] = "{" + ",".join(codes) + "}"

    if min_value is not None:
        conditions.append("t.value_pln >= :min_value")
        params["min_value"] = min_value

    if max_value is not None:
        conditions.append("t.value_pln <= :max_value")
        params["max_value"] = max_value

    if hide_duplicates:
        conditions.append("t.duplicate_of IS NULL")

    where = " AND ".join(conditions)

    sort_map = {
        "match_score": "t.match_score DESC NULLS LAST, t.published_at DESC NULLS LAST, t.id DESC",
        "deadline":    "t.deadline_at ASC NULLS LAST, t.id DESC",
        "value":       "t.value_pln DESC NULLS LAST, t.id DESC",
        "published":   "t.published_at DESC NULLS LAST, t.id DESC",
    }
    order_clause = sort_map.get(sort_key, sort_map["published"])

    # Count uses base WHERE without cursor so total is always the full filtered count
    count_sql = f"SELECT COUNT(*) FROM tender t WHERE {where}"

    # For non-published sorts, use OFFSET-based pagination to avoid keyset issues
    if sort_key != "published" and cursor_offset > 0:
        params["offset_val"] = cursor_offset
        offset_clause = "OFFSET :offset_val"
    else:
        offset_clause = ""

    list_sql = f"""
        SELECT t.id, t.title, t.buyer, t.cpv, t.voivodeship,
               t.value_pln, t.deadline_at, t.status,
               t.match_score, t.match_reason,
               t.source, t.external_id, t.published_at, t.url
        FROM tender t
        WHERE {where} {cursor_clause}
        ORDER BY {order_clause}
        LIMIT :limit
        {offset_clause}
    """

    with engine.connect() as conn:
        total_row = conn.execute(text(count_sql), params).fetchone()
        total = int(total_row[0]) if total_row else 0
        rows = conn.execute(text(list_sql), params).fetchall()

    items: list[TenderListItem] = []
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
            source=row[10],
            external_id=row[11],
            published_at=str(row[12]) if row[12] else None,
            url=row[13],
        ))

    next_cursor: str | None = None
    if len(items) == limit and items:
        last = items[-1]
        if sort_key == "published":
            next_cursor = _encode_cursor(last.published_at, last.id)
        else:
            # Encode next offset as cursor for non-published sorts
            next_offset = cursor_offset + limit
            next_cursor = _encode_cursor(str(next_offset), last.id)

    return Page(items=items, total=total, cursor=next_cursor)


@router.get("/tenders/{tender_id}", response_model=TenderDetail)
def get_tender(
    tender_id: str,
    user: AuthUser,
) -> TenderDetail:
    """Fetch a single tender — tenant-isolated."""
    try:
        uuid.UUID(tender_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Tender not found"},
        )

    from sqlalchemy import text
    engine = get_engine()
    tenant_id = str(user.org_id or "")

    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT t.id, t.title, t.buyer, t.cpv, t.voivodeship,
                       t.value_pln, t.deadline_at, t.status,
                       t.match_score, t.match_reason,
                       t.source, t.external_id, t.published_at, t.url, t.raw
                FROM tender t
                WHERE t.id = :id AND t.tenant_id = :tenant_id
            """),
            {"id": tender_id, "tenant_id": tenant_id},
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Tender not found"},
        )

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


@router.patch("/tenders/{tender_id}")
def patch_tender(
    tender_id: str,
    body: TenderPatch,
    user: AuthUser,
) -> dict:
    """Partial update of a tender — tenant-isolated, enum-safe status cast."""
    try:
        uuid.UUID(tender_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Tender not found"},
        )

    if body.status is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_fields", "message": "No fields to update"},
        )

    import sqlalchemy as sa
    engine = get_engine()
    tenant_id = str(user.org_id or "")

    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                "UPDATE tender "
                "SET status = CAST(:status AS tender_status) "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            {"status": body.status, "id": tender_id, "tenant_id": tenant_id},
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Tender not found"},
            )

    return {"ok": True, "id": tender_id, "status": body.status}
