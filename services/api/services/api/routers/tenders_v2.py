"""Tenders API v2 — cursor pagination, multi-source (BZP/TED/BIP), dedup-aware.

Endpoints:
    GET  /api/v2/tenders                – lista z filtrami, cursor pagination
    GET  /api/v2/tenders/stats          – agregaty: per-source, per-status, top CPV
    GET  /api/v2/tenders/{id}           – szczegóły + duplikaty cross-source
    PATCH /api/v2/tenders/{id}          – zmiana statusu
    DELETE /api/v2/tenders/{id}         – soft delete (archived)
"""
from __future__ import annotations

import base64
import json
from typing import Any, Literal

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/tenders", tags=["tenders-v2"])

# ─── Constants ────────────────────────────────────────────────────────────────

VALID_STATUSES = frozenset({
    "new", "matched", "watching", "analyzing", "estimated",
    "decided_go", "decided_nogo", "archived",
})

VALID_SOURCES = frozenset({"bzp", "ted", "bip", "bk", "manual", "excel"})

SOURCE_LABEL: dict[str, str] = {
    "bzp": "BZP (e-Zamówienia)",
    "ted": "TED (UE)",
    "bip": "BIP (gminy)",
    "bk":  "Baza Konkurencyjności",
    "manual": "Ręczny import",
    "excel": "Import Excel",
}

# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class TenderSummary(BaseModel):
    id: str
    title: str
    buyer: str | None
    source: str
    source_label: str = ""
    cpv: list[str]
    voivodeship: str | None
    value_pln: float | None
    deadline_at: str | None
    published_at: str | None
    url: str | None
    status: str
    match_score: float | None
    is_duplicate: bool
    master_id: str | None          # set when this tender is a duplicate
    created_at: str


class TenderDetail(TenderSummary):
    match_reason: str | None
    raw: dict
    duplicates: list["DuplicateRef"]  # other sources referring same procurement


class DuplicateRef(BaseModel):
    id: str
    source: str
    source_label: str = ""
    title: str
    similarity: float
    match_fields: list[str]
    url: str | None


class TenderStatsResponse(BaseModel):
    total: int
    by_source: dict[str, int]
    by_status: dict[str, int]
    duplicate_pairs: int
    top_cpv: list[dict]           # [{cpv, count}]
    last_published_at: str | None


class TenderPatch(BaseModel):
    status: str | None = Field(None, description=f"One of: {', '.join(sorted(VALID_STATUSES))}")


class TenderListResponse(BaseModel):
    items: list[TenderSummary]
    total: int
    next_cursor: str | None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_tenant_id(engine, org_id: str) -> str:
    # Najpierw użyj org_id z JWT — to jest tenant_id w tabeli tender
    if org_id:
        return str(org_id)
    # Fallback: szukaj w tabeli organizations
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT tenant_id FROM organizations WHERE id = :id"),
            {"id": org_id},
        ).fetchone()
    return str(row.tenant_id) if row and row.tenant_id else org_id


def _row_to_summary(row: Any, is_dup_set: set[str], dup_masters: dict[str, str]) -> TenderSummary:
    rid = str(row.id)
    return TenderSummary(
        id=rid,
        title=row.title or "",
        buyer=row.buyer,
        source=row.source,
        source_label=SOURCE_LABEL.get(row.source, row.source),
        cpv=list(row.cpv) if row.cpv else [],
        voivodeship=row.voivodeship,
        value_pln=float(row.value_pln) if row.value_pln is not None else None,
        deadline_at=row.deadline_at.isoformat() if row.deadline_at else None,
        published_at=row.published_at.isoformat() if row.published_at else None,
        url=row.url,
        status=row.status,
        match_score=float(row.match_score) if row.match_score is not None else None,
        is_duplicate=rid in is_dup_set,
        master_id=dup_masters.get(rid),
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


def _get_dup_context(conn, tenant_id: str) -> tuple[set[str], dict[str, str]]:
    """
    Returns:
        is_dup_set   – set of tender IDs that are marked as duplicates
        dup_masters  – {duplicate_id: master_id}
    """
    rows = conn.execute(sa.text("""
        SELECT master_id::text, duplicate_id::text
        FROM tender_duplicate
        WHERE tenant_id = :tid
    """), {"tid": tenant_id}).fetchall()

    is_dup_set = {str(r.duplicate_id) for r in rows}
    dup_masters = {str(r.duplicate_id): str(r.master_id) for r in rows}
    return is_dup_set, dup_masters


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=TenderListResponse, summary="Lista przetargów")
def list_tenders(
    user: AuthUser,
    # Pagination
    cursor: str | None = Query(None, description="Opaque cursor (z poprzedniej strony)"),
    limit: int = Query(50, ge=1, le=200),
    # Filters
    status: str | None = Query(None, description="Status przetargu"),
    source: str | None = Query(None, description="Źródło: bzp|ted|bip|bk|manual|excel"),
    cpv: str | None = Query(None, description="Prefiks CPV, np. '45'"),
    voivodeship: str | None = Query(None, description="Województwo (częściowe dopasowanie)"),
    value_min: float | None = Query(None, ge=0),
    value_max: float | None = Query(None, ge=0),
    deadline_before: str | None = Query(None, description="ISO date, np. 2026-08-01"),
    hide_duplicates: bool = Query(False, description="Ukryj rekordy zduplikowane (pozostaw master)"),
    q: str | None = Query(None, min_length=2, description="Full-text search"),
) -> TenderListResponse:
    """
    Lista przetargów z cursor-based pagination.

    - `source` filtruje po źródle (bzp/ted/bip). Możliwy multi: `source=bzp&source=ted`.
    - `hide_duplicates=true` ukrywa duplikaty cross-source — pokazuje tylko master record.
    - Cursor jest nieprzezroczysty (base64 JSON), stable przy sortowaniu `created_at DESC, id DESC`.
    """
    engine = get_engine()
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Użytkownik nie należy do organizacji"})
    tenant_id = _resolve_tenant_id(engine, org_id)

    # Validate inputs
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_status", "message": f"Nieprawidłowy status: {status}. Dopuszczalne: {sorted(VALID_STATUSES)}"},
        )
    if source and source not in VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_source", "message": f"Nieprawidłowe źródło: {source}. Dopuszczalne: {sorted(VALID_SOURCES)}"},
        )

    conditions: list[str] = ["t.tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": limit + 1}

    # Default: hide archived unless explicitly requested
    if status:
        conditions.append("t.status = :status")
        params["status"] = status
    else:
        conditions.append("t.status != 'archived'")

    if source:
        conditions.append("t.source = :source::source_kind")
        params["source"] = source

    if cpv:
        conditions.append("EXISTS (SELECT 1 FROM unnest(t.cpv) c WHERE c LIKE :cpv_prefix)")
        params["cpv_prefix"] = cpv + "%"

    if voivodeship:
        conditions.append("t.voivodeship ILIKE :voivodeship")
        params["voivodeship"] = f"%{voivodeship}%"

    if value_min is not None:
        conditions.append("t.value_pln >= :value_min")
        params["value_min"] = value_min

    if value_max is not None:
        conditions.append("t.value_pln <= :value_max")
        params["value_max"] = value_max

    if deadline_before:
        conditions.append("t.deadline_at <= :deadline_before::timestamptz")
        params["deadline_before"] = deadline_before

    if hide_duplicates:
        # Exclude any tender that appears as duplicate_id in tender_duplicate
        conditions.append("""
            NOT EXISTS (
                SELECT 1 FROM tender_duplicate d
                WHERE d.duplicate_id = t.id AND d.tenant_id = :tenant_id
            )
        """)

    if q:
        conditions.append("""
            to_tsvector('simple', coalesce(t.title,'') || ' ' || coalesce(t.buyer,''))
            @@ plainto_tsquery('simple', :q)
        """)
        params["q"] = q

    # Cursor decode
    cursor_sql = ""
    if cursor:
        try:
            cd = json.loads(base64.b64decode(cursor).decode())
            cursor_sql = "AND (t.created_at < :cur_ts OR (t.created_at = :cur_ts AND t.id < :cur_id::uuid))"
            params["cur_ts"] = cd["created_at"]
            params["cur_id"] = cd["id"]
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_cursor", "message": "Nieprawidłowy cursor"})

    where = " AND ".join(conditions)

    with engine.connect() as conn:
        # Total count (no cursor — for display only, not re-computed on each page)
        count_params = {k: v for k, v in params.items() if k not in ("limit", "cur_ts", "cur_id")}
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM tender t WHERE {where}"),
            count_params,
        ).scalar() or 0

        rows = conn.execute(
            sa.text(f"""
                SELECT t.id, t.title, t.buyer, t.source::text, t.cpv, t.voivodeship,
                       t.value_pln, t.deadline_at, t.published_at, t.url, t.status::text,
                       t.match_score, t.created_at
                FROM tender t
                WHERE {where} {cursor_sql}
                ORDER BY t.created_at DESC, t.id DESC
                LIMIT :limit
            """),
            params,
        ).fetchall()

        is_dup_set, dup_masters = _get_dup_context(conn, tenant_id)

    items = [_row_to_summary(r, is_dup_set, dup_masters) for r in rows[:limit]]

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = base64.b64encode(
            json.dumps({"created_at": last.created_at.isoformat(), "id": str(last.id)}).encode()
        ).decode()

    return TenderListResponse(items=items, total=int(total), next_cursor=next_cursor)


@router.get("/stats", response_model=TenderStatsResponse, summary="Agregaty przetargów")
def tender_stats(user: AuthUser) -> TenderStatsResponse:
    """
    Agregaty dla dashboardu:
    - liczba per źródło (BZP / TED / BIP / …)
    - liczba per status
    - liczba unikalnych par duplikatów
    - top-10 kodów CPV
    - data ostatnio opublikowanego przetargu
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.connect() as conn:
        # Per-source counts
        source_rows = conn.execute(sa.text("""
            SELECT source::text, COUNT(*) AS cnt
            FROM tender
            WHERE tenant_id = :tid AND status != 'archived'
            GROUP BY source
        """), {"tid": tenant_id}).fetchall()
        by_source = {r.source: int(r.cnt) for r in source_rows}

        # Per-status counts
        status_rows = conn.execute(sa.text("""
            SELECT status::text, COUNT(*) AS cnt
            FROM tender
            WHERE tenant_id = :tid
            GROUP BY status
        """), {"tid": tenant_id}).fetchall()
        by_status = {r.status: int(r.cnt) for r in status_rows}

        # Total (non-archived)
        total = sum(by_source.values())

        # Duplicate pair count
        dup_count = conn.execute(sa.text("""
            SELECT COUNT(*) FROM tender_duplicate WHERE tenant_id = :tid
        """), {"tid": tenant_id}).scalar() or 0

        # Top CPV
        cpv_rows = conn.execute(sa.text("""
            SELECT c.cpv_code, COUNT(*) AS cnt
            FROM tender t, unnest(t.cpv) AS c(cpv_code)
            WHERE t.tenant_id = :tid AND t.status != 'archived'
            GROUP BY c.cpv_code
            ORDER BY cnt DESC
            LIMIT 10
        """), {"tid": tenant_id}).fetchall()
        top_cpv = [{"cpv": r.cpv_code, "count": int(r.cnt)} for r in cpv_rows]

        # Last published
        last_pub = conn.execute(sa.text("""
            SELECT MAX(published_at) FROM tender WHERE tenant_id = :tid
        """), {"tid": tenant_id}).scalar()

    return TenderStatsResponse(
        total=total,
        by_source={**{s: 0 for s in VALID_SOURCES}, **by_source},
        by_status=by_status,
        duplicate_pairs=int(dup_count),
        top_cpv=top_cpv,
        last_published_at=last_pub.isoformat() if last_pub else None,
    )


@router.get("/{tender_id}", response_model=TenderDetail, summary="Szczegóły przetargu")
def get_tender(tender_id: str, user: AuthUser) -> TenderDetail:
    """
    Szczegóły przetargu wraz z:
    - pełnymi danymi raw (JSON z BZP/TED/BIP)
    - listą duplikatów cross-source (`duplicates[]`)

    `duplicates` zawiera inne rekordy (z innego źródła) odnoszące się do tego samego zamówienia.
    Gdy bieżący rekord jest duplikatem, `is_duplicate=true` i `master_id` wskazuje na master.
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, title, buyer, source::text, cpv, voivodeship, value_pln,
                   deadline_at, published_at, url, status::text, match_score,
                   match_reason, raw, created_at
            FROM tender
            WHERE id = :id::uuid AND tenant_id = :tid
        """), {"id": tender_id, "tid": tenant_id}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

        # Is this a duplicate? (appears as duplicate_id)
        dup_as_dup = conn.execute(sa.text("""
            SELECT master_id::text, similarity, match_fields
            FROM tender_duplicate
            WHERE duplicate_id = :id::uuid AND tenant_id = :tid
            LIMIT 1
        """), {"id": tender_id, "tid": tenant_id}).fetchone()

        master_id = str(dup_as_dup.master_id) if dup_as_dup else None
        is_duplicate = master_id is not None

        # Duplicates of this tender (it is the master)
        dup_refs_raw = conn.execute(sa.text("""
            SELECT d.duplicate_id::text AS dup_id, d.similarity, d.match_fields,
                   t.source::text, t.title, t.url
            FROM tender_duplicate d
            JOIN tender t ON t.id = d.duplicate_id
            WHERE d.master_id = :id::uuid AND d.tenant_id = :tid
        """), {"id": tender_id, "tid": tenant_id}).fetchall()

        # Also check if master → pull in master's detail for "sibling" duplicates
        sibling_refs_raw = []
        if is_duplicate:
            sibling_refs_raw = conn.execute(sa.text("""
                SELECT d.duplicate_id::text AS dup_id, d.similarity, d.match_fields,
                       t.source::text, t.title, t.url
                FROM tender_duplicate d
                JOIN tender t ON t.id = d.duplicate_id
                WHERE d.master_id = :master_id::uuid
                  AND d.duplicate_id != :self_id::uuid
                  AND d.tenant_id = :tid
            """), {"master_id": master_id, "self_id": tender_id, "tid": tenant_id}).fetchall()

    def _dup_row(r: Any, is_master_ref: bool = False) -> DuplicateRef:
        return DuplicateRef(
            id=r.dup_id,
            source=r.source,
            source_label=SOURCE_LABEL.get(r.source, r.source),
            title=r.title or "",
            similarity=float(r.similarity),
            match_fields=list(r.match_fields) if r.match_fields else [],
            url=r.url,
        )

    duplicates = [_dup_row(r) for r in dup_refs_raw] + [_dup_row(r) for r in sibling_refs_raw]

    return TenderDetail(
        id=str(row.id),
        title=row.title or "",
        buyer=row.buyer,
        source=row.source,
        source_label=SOURCE_LABEL.get(row.source, row.source),
        cpv=list(row.cpv) if row.cpv else [],
        voivodeship=row.voivodeship,
        value_pln=float(row.value_pln) if row.value_pln is not None else None,
        deadline_at=row.deadline_at.isoformat() if row.deadline_at else None,
        published_at=row.published_at.isoformat() if row.published_at else None,
        url=row.url,
        status=row.status,
        match_score=float(row.match_score) if row.match_score is not None else None,
        is_duplicate=is_duplicate,
        master_id=master_id,
        created_at=row.created_at.isoformat() if row.created_at else "",
        match_reason=row.match_reason,
        raw=row.raw if isinstance(row.raw, dict) else {},
        duplicates=duplicates,
    )


@router.patch("/{tender_id}", summary="Zmień status przetargu")
def patch_tender(tender_id: str, body: TenderPatch, user: AuthUser) -> dict:
    """
    Zmiana statusu przetargu.
    Dozwolone wartości: new → matched → watching → analyzing → estimated → decided_go / decided_nogo → archived.
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_status", "message": f"Nieprawidłowy status: {body.status}"},
        )

    with engine.begin() as conn:
        result = conn.execute(sa.text("""
            UPDATE tender
            SET status = :status::tender_status
            WHERE id = :id::uuid AND tenant_id = :tid
            RETURNING id::text, status::text
        """), {"status": body.status, "id": tender_id, "tid": tenant_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

    return {"id": result.id, "status": result.status}


@router.delete("/{tender_id}", summary="Archiwizuj przetarg")
def delete_tender(tender_id: str, user: AuthUser) -> dict:
    """Soft delete — ustawia status = 'archived'. Odwracalne przez PATCH status=new."""
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.begin() as conn:
        result = conn.execute(sa.text("""
            UPDATE tender SET status = 'archived'
            WHERE id = :id::uuid AND tenant_id = :tid
            RETURNING id::text
        """), {"id": tender_id, "tid": tenant_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

    return {"id": result.id, "status": "archived", "message": "Przetarg zarchiwizowany"}
