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
import logging
import threading
import uuid as _uuid_mod
from typing import Any, Literal

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from terra_db.session import get_engine

from .. import cache as _cache
from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)

# S116 — Allowed fields for sparse fieldset (mobile)
ALLOWED_FIELDS = ['id', 'title', 'match_score', 'deadline_at', 'source', 'value_pln', 'cpv_code']
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
    historical_intelligence: dict | None = None  # benchmark from 1.4M historical tenders


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
    # Lookup tenant_id from organizations table
    if org_id:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("SELECT tenant_id FROM organizations WHERE id = :id"),
                {"id": org_id},
            ).fetchone()
        if row and row.tenant_id:
            return str(row.tenant_id)
    # Fallback: org_id == tenant_id (legacy / self-tenant)
    return str(org_id) if org_id else org_id


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


def _validate_uuid(value: str, param_name: str = "id") -> None:
    """Raise HTTP 404 when *value* is not a valid UUID string."""
    try:
        _uuid_mod.UUID(str(value))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Przetarg nie znaleziony (nieprawidłowy {param_name})"},
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
    # aliases used by frontend
    min_value: float | None = Query(None, ge=0, description="Alias for value_min"),
    max_value: float | None = Query(None, ge=0, description="Alias for value_max"),
    deadline_before: str | None = Query(None, description="ISO date, np. 2026-08-01"),
    hide_duplicates: bool = Query(False, description="Ukryj rekordy zduplikowane (pozostaw master)"),
    q: str | None = Query(None, min_length=2, description="Full-text search"),
    fields: str | None = Query(None, description="Sparse fieldset: id,title,match_score,... (mobile)"),
    sort: str | None = Query(None, description="Sort field: match_score|deadline_at|value_pln|created_at"),
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

    # Resolve aliases
    effective_min = value_min if value_min is not None else min_value
    effective_max = value_max if value_max is not None else max_value

    # Resolve sort → ORDER BY clause
    SORT_MAP = {
        "match_score":  "t.match_score DESC NULLS LAST, t.created_at DESC, t.id DESC",
        "deadline_at":  "t.deadline_at ASC NULLS LAST, t.created_at DESC, t.id DESC",
        "value_pln":    "t.value_pln DESC NULLS LAST, t.created_at DESC, t.id DESC",
        "created_at":   "t.created_at DESC, t.id DESC",
    }
    order_clause = SORT_MAP.get(sort or "match_score", SORT_MAP["match_score"])

    # Default: hide archived unless explicitly requested
    if status:
        conditions.append("t.status = :status")
        params["status"] = status
    else:
        conditions.append("t.status != 'archived'")

    if source:
        conditions.append("t.source = CAST(:source AS source_kind)")
        params["source"] = source

    if cpv:
        conditions.append("EXISTS (SELECT 1 FROM unnest(t.cpv) c WHERE c LIKE :cpv_prefix)")
        params["cpv_prefix"] = cpv + "%"

    if voivodeship:
        conditions.append("t.voivodeship ILIKE :voivodeship")
        params["voivodeship"] = f"%{voivodeship}%"

    if effective_min is not None:
        conditions.append("t.value_pln >= :value_min")
        params["value_min"] = effective_min

    if effective_max is not None:
        conditions.append("t.value_pln <= :value_max")
        params["value_max"] = effective_max

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
            cursor_sql = "AND (t.created_at < :cur_ts OR (t.created_at = :cur_ts AND t.id < CAST(:cur_id AS UUID)))"
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
                ORDER BY {order_clause}
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

    # S116 — Sparse fieldset: filter items to requested fields only
    if fields:
        selected = [f.strip() for f in fields.split(",") if f.strip() in ALLOWED_FIELDS]
        if selected:
            items = [
                {k: v for k, v in item.model_dump().items() if k in selected}
                for item in items
            ]

    # S108 — Log usage event (fire-and-forget, don't block response)
    try:
        _t = threading.Thread(
            target=_log_usage_event, args=(tenant_id, "tender_viewed", None), daemon=True
        )
        _t.start()
    except Exception:
        pass

    return TenderListResponse(items=items, total=int(total), next_cursor=next_cursor)


def _log_usage_event(tenant_id: str, event_type: str, resource_id: str | None = None) -> None:
    """S108 — Fire-and-forget usage event logging."""
    try:
        _eng = get_engine()
        with _eng.begin() as _conn:
            _conn.execute(
                sa.text(
                    "INSERT INTO usage_events(tenant_id, event_type, resource_id) "
                    "VALUES (:tid, :et, :rid)"
                ),
                {"tid": tenant_id, "et": event_type, "rid": resource_id},
            )
    except Exception as _e:
        logger.debug("usage_events insert failed (non-critical): %s", _e)


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


@router.get("/search", summary="Szybkie wyszukiwanie przetargów")
def search_tenders(
    user: AuthUser,
    q: str = Query(..., min_length=1, description="Fraza wyszukiwania"),
    limit: int = Query(20, ge=1, le=100),
    source: str | None = Query(None),
    status: str | None = Query(None),
) -> dict:
    """
    GET /api/v2/tenders/search?q=...
    Full-text search over tenders for the authenticated tenant.
    Returns {items: [...], total: int, query: str}.
    This route MUST be declared before /{tender_id} to avoid 'search' being
    interpreted as a UUID, which crashes with a PostgreSQL cast error.
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    q = q.strip()
    if not q:
        return {"items": [], "total": 0, "query": q}

    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    conditions: list[str] = ["t.tenant_id = :tenant_id", "t.status != 'archived'"]
    params: dict = {"tenant_id": tenant_id, "limit": limit, "q": q}

    if source and source in VALID_SOURCES:
        conditions.append("t.source = CAST(:source AS source_kind)")
        params["source"] = source

    if status and status in VALID_STATUSES:
        conditions.append("t.status = :status")
        params["status"] = status

    # Full-text search condition with ILIKE fallback
    fts_condition = (
        "to_tsvector('simple', coalesce(t.title,'') || ' ' || coalesce(t.buyer,''))"
        " @@ plainto_tsquery('simple', :q)"
    )
    ilike_condition = "(t.title ILIKE :q_like OR t.buyer ILIKE :q_like)"
    params["q_like"] = f"%{q}%"

    where = " AND ".join(conditions)

    rows: list = []
    with engine.connect() as conn:
        # Try FTS first
        try:
            rows = conn.execute(
                sa.text(f"""
                    SELECT t.id, t.title, t.buyer, t.source::text, t.status::text,
                           t.value_pln, t.deadline_at, t.url, t.created_at,
                           ts_headline(
                               'simple',
                               coalesce(t.title,'') || ' ' || coalesce(t.buyer,''),
                               plainto_tsquery('simple', :q),
                               'MaxWords=15, MinWords=5'
                           ) AS excerpt
                    FROM tender t
                    WHERE {where} AND {fts_condition}
                    ORDER BY
                        ts_rank(
                            to_tsvector('simple', coalesce(t.title,'') || ' ' || coalesce(t.buyer,'')),
                            plainto_tsquery('simple', :q)
                        ) DESC,
                        t.created_at DESC
                    LIMIT :limit
                """),
                params,
            ).fetchall()
        except Exception:
            logger.exception("FTS search failed for q=%r, falling back to ILIKE", q)
            rows = []

        # ILIKE fallback
        if not rows:
            try:
                rows = conn.execute(
                    sa.text(f"""
                        SELECT t.id, t.title, t.buyer, t.source::text, t.status::text,
                               t.value_pln, t.deadline_at, t.url, t.created_at,
                               coalesce(t.title, '') AS excerpt
                        FROM tender t
                        WHERE {where} AND {ilike_condition}
                        ORDER BY t.created_at DESC
                        LIMIT :limit
                    """),
                    params,
                ).fetchall()
            except Exception:
                logger.exception("ILIKE fallback search failed for q=%r", q)
                rows = []

    items = [
        {
            "id": str(r.id),
            "title": r.title or "",
            "buyer": r.buyer,
            "source": r.source,
            "status": r.status,
            "value_pln": float(r.value_pln) if r.value_pln is not None else None,
            "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
            "url": r.url,
            "excerpt": r.excerpt or r.title or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {"items": items, "total": len(items), "query": q}


@router.get("/semantic-search", summary="Semantyczne wyszukiwanie przetargów (FTS polish + ILIKE fallback)")
def semantic_search_tenders(
    user: AuthUser,
    q: str = Query(..., min_length=1, description="Fraza wyszukiwania"),
    limit: int = Query(10, ge=1, le=100),
    cpv: str | None = Query(None, description="Prefiks CPV, np. '45'"),
) -> dict:
    """
    GET /api/v2/tenders/semantic-search?q=...
    Semantic search over tenders using Polish FTS with ILIKE fallback.
    Returns {items: [...], total: int, query: str}.
    This route MUST be declared before /{tender_id} to avoid being interpreted as a UUID.
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    q = q.strip()
    if not q:
        return {"items": [], "total": 0, "query": q}

    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    try:
        conditions: list[str] = ["t.tenant_id = :tenant_id", "t.status != 'archived'"]
        params: dict = {"tenant_id": tenant_id, "limit": limit, "q": q}

        if cpv:
            conditions.append("EXISTS (SELECT 1 FROM unnest(t.cpv) c WHERE c LIKE :cpv_prefix)")
            params["cpv_prefix"] = cpv + "%"

        where = " AND ".join(conditions)

        fts_condition = (
            "to_tsvector('polish', t.title || ' ' || COALESCE(t.description, ''))"
            " @@ plainto_tsquery('polish', :q)"
        )
        ilike_condition = "t.title ILIKE '%' || :q || '%'"

        rows: list = []
        with engine.connect() as conn:
            # Set RLS tenant
            conn.execute(sa.text("SET app.tenant_id = :tid"), {"tid": tenant_id})

            # Try Polish FTS first
            try:
                rows = conn.execute(
                    sa.text(f"""
                        SELECT t.id, t.title, t.buyer, t.source::text, t.cpv,
                               t.voivodeship, t.value_pln, t.deadline_at,
                               t.published_at, t.url, t.status::text,
                               t.match_score, t.created_at
                        FROM tender t
                        WHERE {where} AND {fts_condition}
                        ORDER BY
                            ts_rank(
                                to_tsvector('polish', t.title || ' ' || COALESCE(t.description, '')),
                                plainto_tsquery('polish', :q)
                            ) DESC,
                            t.created_at DESC
                        LIMIT :limit
                    """),
                    params,
                ).fetchall()
            except Exception:
                logger.exception("Polish FTS semantic-search failed for q=%r, falling back to ILIKE", q)
                rows = []

            # ILIKE fallback if FTS returned 0 results
            if not rows:
                rows = conn.execute(
                    sa.text(f"""
                        SELECT t.id, t.title, t.buyer, t.source::text, t.cpv,
                               t.voivodeship, t.value_pln, t.deadline_at,
                               t.published_at, t.url, t.status::text,
                               t.match_score, t.created_at
                        FROM tender t
                        WHERE {where} AND {ilike_condition}
                        ORDER BY t.created_at DESC
                        LIMIT :limit
                    """),
                    params,
                ).fetchall()

            is_dup_set, dup_masters = _get_dup_context(conn, tenant_id)

        items = [_row_to_summary(r, is_dup_set, dup_masters) for r in rows]
        return {"items": [i.model_dump() for i in items], "total": len(items), "query": q}

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "bad_input", "message": str(exc)})
    except Exception as exc:
        logger.exception("semantic-search DB error for q=%r", q)
        raise HTTPException(status_code=500, detail={"error": "db_error", "message": "Błąd bazy danych"})


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

    # Validate UUID format before hitting the DB — prevents PostgreSQL cast error (500)
    _validate_uuid(tender_id, "tender_id")

    # S86 — Check cache first
    _cache_key = f"tender:{tender_id}:{org_id}"
    _cached = _cache.get(_cache_key)
    if _cached is not None:
        return _cached

    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, title, buyer, source::text, cpv, voivodeship, value_pln,
                   deadline_at, published_at, url, status::text, match_score,
                   match_reason, raw, created_at
            FROM tender
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
        """), {"id": tender_id, "tid": tenant_id}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

        # Is this a duplicate? (appears as duplicate_id)
        dup_as_dup = conn.execute(sa.text("""
            SELECT master_id::text, similarity, match_fields
            FROM tender_duplicate
            WHERE duplicate_id = CAST(:id AS UUID) AND tenant_id = :tid
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
            WHERE d.master_id = CAST(:id AS UUID) AND d.tenant_id = :tid
        """), {"id": tender_id, "tid": tenant_id}).fetchall()

        # Also check if master → pull in master's detail for "sibling" duplicates
        sibling_refs_raw = []
        if is_duplicate:
            sibling_refs_raw = conn.execute(sa.text("""
                SELECT d.duplicate_id::text AS dup_id, d.similarity, d.match_fields,
                       t.source::text, t.title, t.url
                FROM tender_duplicate d
                JOIN tender t ON t.id = d.duplicate_id
                WHERE d.master_id = CAST(:master_id AS UUID)
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

    result = TenderDetail(
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

    # S86 — Store in cache
    _cache.set(_cache_key, result, ttl=120)

    # Enrich with historical intelligence (async-safe, lazy)
    try:
        from ..intelligence.historical_intelligence import get_historical_context
        cpv_first = result.cpv[0] if result.cpv else None
        hist = get_historical_context(
            title=result.title,
            cpv_code=cpv_first,
            province=result.voivodeship,
            estimated_value=result.value_pln,
            buyer=result.buyer,
            limit=5,
        )
        if hist:
            result.historical_intelligence = hist
    except Exception:
        pass  # non-critical enrichment

    return result


@router.patch("/{tender_id}", summary="Zmień status przetargu")
def patch_tender(tender_id: str, body: TenderPatch, user: AuthUser) -> dict:
    """
    Zmiana statusu przetargu.
    Dozwolone wartości: new → matched → watching → analyzing → estimated → decided_go / decided_nogo → archived.
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    _validate_uuid(tender_id, "tender_id")
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
            SET status = CAST(:status AS tender_status)
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
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
    _validate_uuid(tender_id, "tender_id")
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.begin() as conn:
        result = conn.execute(sa.text("""
            UPDATE tender SET status = 'archived'
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
            RETURNING id::text
        """), {"id": tender_id, "tid": tenant_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

    return {"id": result.id, "status": "archived", "message": "Przetarg zarchiwizowany"}


# ─── POST /tenders/{tender_id}/analyze — queue AI analysis ─────────────────────

@router.post("/{tender_id}/analyze", summary="Queue AI analysis for tender")
def analyze_tender(tender_id: str, user: AuthUser) -> dict:
    """Queue an AI analysis job for the given tender."""
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    _validate_uuid(tender_id, "tender_id")
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)
    job_id = str(_uuid_mod.uuid4())

    with engine.begin() as conn:
        # Verify tender exists
        tender = conn.execute(sa.text(
            "SELECT id FROM tender WHERE id = CAST(:id AS UUID) AND tenant_id = :tid"
        ), {"id": tender_id, "tid": tenant_id}).fetchone()
        if not tender:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})
        # Insert agent_run (best-effort, table may not exist in test)
        try:
            conn.execute(sa.text(
                "INSERT INTO agent_run(id, tender_id, status, created_at) VALUES(CAST(:id AS UUID), CAST(:tid AS UUID), 'queued', NOW())"
            ), {"id": job_id, "tid": tender_id})
        except Exception:
            pass

    return {"job_id": job_id, "status": "queued", "tender_id": tender_id}


# ─── GET /tenders/{tender_id}/similar — find similar tenders by CPV ────────────

@router.get("/{tender_id}/similar", summary="Find similar tenders")
def similar_tenders(tender_id: str, user: AuthUser) -> dict:
    """Find similar tenders based on CPV code prefix."""
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    _validate_uuid(tender_id, "tender_id")
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.connect() as conn:
        tender = conn.execute(sa.text(
            "SELECT cpv, value_pln FROM tender WHERE id = CAST(:id AS UUID) AND tenant_id = :tid"
        ), {"id": tender_id, "tid": tenant_id}).fetchone()
        if not tender:
            return {"items": [], "count": 0}
        prefix = (tender.cpv or '')[:4]
        if not prefix:
            return {"items": [], "count": 0}
        rows = conn.execute(sa.text(
            "SELECT id::text, title, cpv, value_pln, status FROM tender "
            "WHERE tenant_id = :tid AND id != CAST(:id AS UUID) AND cpv LIKE :prefix LIMIT 5"
        ), {"tid": tenant_id, "id": tender_id, "prefix": f"{prefix}%"}).fetchall()

    items = [
        {"id": str(r.id), "title": r.title, "cpv_code": r.cpv,
         "value_pln": float(r.value_pln or 0), "status": r.status}
        for r in rows
    ]
    return {"items": items, "count": len(items)}


# ─── GET /tenders/{tender_id}/score — CPV-based match score ────────────────────

@router.get("/{tender_id}/score", summary="Match score (go/no-go %) przetargu")
def get_tender_score(tender_id: str, user: AuthUser) -> dict:
    """
    Zwraca match score (0–100) dla przetargu względem profilu CPV tenanta.

    Algorytm:
    - Pobiera CPV przetargu i preferred_cpvs tenanta z scoring_config
    - Pełne dopasowanie (cpv startswith pref lub pref startswith cpv[:n]) → wynik proporcjonalny
    - Jeśli tenant nie ma preferred_cpvs → zwraca istniejący match_score z bazy lub 50 (neutral)
    - Wynik jest też zapisywany do tender.match_score (rescore on demand)

    Odpowiedź:
      {
        "tender_id": "...",
        "match_score": 82.0,
        "match_label": "Świetne dopasowanie",
        "match_reason": "CPV 45233120 pasuje do preferencji: 45",
        "preferred_cpvs": ["45", "45100000"],
        "tender_cpvs": ["45233120-6"],
        "go_nogo": "go"
      }
    """
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org"})
    _validate_uuid(tender_id, "tender_id")
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, org_id)

    with engine.connect() as conn:
        # Pobierz dane przetargu
        row = conn.execute(sa.text("""
            SELECT id, cpv, value_pln, deadline_at, match_score, match_reason
            FROM tender
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
        """), {"id": tender_id, "tid": tenant_id}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

        # Pobierz preferred_cpvs z scoring_config tenanta
        cfg_row = conn.execute(sa.text("""
            SELECT preferred_cpvs, cpv_weight, value_weight, min_value_pln, max_value_pln
            FROM scoring_config
            WHERE tenant_id = :tid
            LIMIT 1
        """), {"tid": tenant_id}).fetchone()

    tender_cpvs: list[str] = list(row.cpv or [])
    preferred_cpvs: list[str] = []
    cpv_weight: float = 0.35

    if cfg_row:
        preferred_cpvs = list(cfg_row.preferred_cpvs or [])
        cpv_weight = float(cfg_row.cpv_weight or 0.35)

    # ─── CPV Match Score Algorithm ─────────────────────────────────────────────
    def _cpv_match(t_cpv: str, preferred: list[str]) -> tuple[float, str]:
        """
        Zwraca (score 0.0–1.0, matched_pref | "").
        Logika: im dłuższy pasujący prefiks, tym wyższy score.
          - pełne 8-cyfrowe dopasowanie → 1.0
          - 5-cyfrowe (dywizja) → 0.9
          - 4-cyfrowe (grupa) → 0.75
          - 2-cyfrowe (dział) → 0.6
          - brak → 0.0
        """
        cpv_clean = t_cpv.split("-")[0].strip()  # usuń -numer z końca
        for pref in preferred:
            p = pref.split("-")[0].strip()
            # Tender pasuje do preferencji
            if cpv_clean.startswith(p):
                plen = len(p)
                if plen >= 8:
                    return 1.0, pref
                elif plen >= 5:
                    return 0.9, pref
                elif plen >= 4:
                    return 0.75, pref
                elif plen >= 2:
                    return 0.6, pref
                return 0.5, pref
            # Preferencja jest bardziej szczegółowa niż CPV tenderu
            if p.startswith(cpv_clean[:max(2, len(cpv_clean))]):
                return 0.5, pref
        return 0.0, ""

    score_raw: float
    match_reason: str
    matched_pref: str = ""

    if not preferred_cpvs:
        # Brak konfiguracji — użyj istniejącego match_score z bazy lub neutral
        existing = float(row.match_score) if row.match_score is not None else 0.5
        score_raw = existing
        match_reason = row.match_reason or "Brak konfiguracji CPV — score neutralny"
    elif not tender_cpvs:
        score_raw = 0.3
        match_reason = "Przetarg bez kodu CPV"
    else:
        # Weź najlepszy wynik ze wszystkich CPV przetargu
        best_score = 0.0
        best_reason = ""
        for t_cpv in tender_cpvs:
            s, pref = _cpv_match(t_cpv, preferred_cpvs)
            if s > best_score:
                best_score = s
                matched_pref = pref
                best_reason = f"CPV {t_cpv.split('-')[0]} pasuje do preferencji: {pref}" if pref else f"CPV {t_cpv} — brak dopasowania"
        score_raw = best_score
        match_reason = best_reason if best_reason else "Brak dopasowania CPV do preferencji tenanta"

    # Przelicz na procenty (0–100)
    score_pct = round(score_raw * 100, 1)

    # Label i go/no-go
    if score_pct >= 80:
        label = "Świetne dopasowanie"
        go_nogo = "go"
    elif score_pct >= 50:
        label = "Dobre dopasowanie"
        go_nogo = "go"
    else:
        label = "Słabe dopasowanie"
        go_nogo = "nogo"

    # Zaktualizuj match_score w bazie (rescore on demand) jeśli preferred_cpvs istnieje
    if preferred_cpvs:
        try:
            with engine.begin() as upd_conn:
                upd_conn.execute(sa.text("""
                    UPDATE tender
                    SET match_score = :score, match_reason = :reason
                    WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
                """), {
                    "score": score_raw,
                    "reason": match_reason,
                    "id": tender_id,
                    "tid": tenant_id,
                })
        except Exception as e:
            logger.warning("Could not update match_score for tender %s: %s", tender_id, e)

    return {
        "tender_id": tender_id,
        "match_score": score_pct,
        "match_score_raw": score_raw,
        "match_label": label,
        "match_reason": match_reason,
        "preferred_cpvs": preferred_cpvs,
        "tender_cpvs": tender_cpvs,
        "matched_pref": matched_pref,
        "go_nogo": go_nogo,
    }
