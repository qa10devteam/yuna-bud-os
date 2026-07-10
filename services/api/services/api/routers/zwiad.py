"""M1 — /ingest/run (async) and /tenders/* endpoints."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import get_current_user, AuthUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["zwiad"])


def _normalize_voiv(v: str) -> str:
    """Strip diacritics from a voivodeship name for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", v)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class IngestRunResponse(BaseModel):
    """Legacy sync response — kept for backward compat."""
    agent_run_id: str
    fetched: int
    created: int
    updated: int
    dropped: int
    errors: int
    bip_stored: int
    dedup_pairs: int


class IngestTaskResponse(BaseModel):
    """Async task envelope — returned immediately on POST /ingest/run."""
    task_id: str
    status: str          # pending | running | done | failed
    progress: dict | None = None   # {step, pct, message}
    result: dict | None = None
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


# ---------------------------------------------------------------------------
# In-process progress store  (task_id → latest progress dict)
# Shared between background thread and SSE generator.
# ---------------------------------------------------------------------------
_PROGRESS: dict[str, dict] = {}
_PROGRESS_LOCK = threading.Lock()


def _set_progress(task_id: str, step: str, pct: int, message: str = "") -> None:
    with _PROGRESS_LOCK:
        _PROGRESS[task_id] = {"step": step, "pct": pct, "message": message}


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

# ---------------------------------------------------------------------------
# Ingest — Async (BPMN Sprint 1)
# ---------------------------------------------------------------------------

def _run_ingest_worker(task_id: str, tenant_id: str, params: dict) -> None:
    """Background thread — runs full pipeline and updates ingest_task row."""
    from services.ingestion.pipeline import run_ingest

    engine = get_engine()
    now = lambda: datetime.now(timezone.utc)  # noqa: E731

    def _update_task(**kw):
        sets = ", ".join(f"{k} = :{k}" for k in kw)
        with engine.begin() as conn:
            conn.execute(
                sa.text(f"UPDATE ingest_task SET {sets} WHERE id = :task_id"),
                {"task_id": task_id, **kw},
            )

    # S23: step→message map for granular SSE progress
    _STEP_MESSAGES = {
        "init": "Inicjalizacja...",
        "fetching_bzp": "Pobieranie BZP...",
        "fetching_ted": "Pobieranie TED...",
        "fetching_bip": "Pobieranie BIP...",
        "normalizing": "Normalizacja...",
        "scoring": "Scorowanie...",
        "upserting": "Zapisywanie...",
        "done": "Zakończono",
    }

    def _pipeline_progress_cb(step: str, pct: int) -> None:
        msg = _STEP_MESSAGES.get(step, step)
        _set_progress(task_id, step, pct, msg)

    try:
        _update_task(status="running", started_at=now())
        _set_progress(task_id, "init", 5, "Inicjalizacja...")

        result = run_ingest(
            engine,
            days_back=params.get("days_back", 7),
            offline=params.get("offline", False),
            include_bip=params.get("include_bip", False),
            include_ted=params.get("include_ted", True),
            run_dedup=params.get("run_dedup", True),
            bip_max_sites=50,
            tenant_id=tenant_id if tenant_id else None,  # S8: explicit tenant isolation
            progress_cb=_pipeline_progress_cb,  # S23: granular progress steps
        )

        _set_progress(task_id, "done", 100, f"Zakończono: +{result.created} nowych")
        result_dict = {
            "fetched": result.raw_fetched,
            "created": result.created,
            "updated": result.updated,
            "dropped": result.dropped_filter,
            "errors": result.errors,
            "bip_stored": getattr(result, "bip_stored", 0) or 0,
            "dedup_pairs": getattr(result, "dedup_pairs", 0) or 0,
        }
        _update_task(
            status="done",
            finished_at=now(),
            result=json.dumps(result_dict),
            progress=json.dumps({"step": "done", "pct": 100,
                                  "message": f"Zakończono: +{result.created} nowych"}),
        )
        logger.info("Ingest task %s done: %s", task_id, result_dict)

    except Exception as exc:
        err = str(exc)
        logger.exception("Ingest task %s failed: %s", task_id, err)
        _set_progress(task_id, "failed", 0, err)
        _update_task(status="failed", finished_at=now(), error=err)


@router.post("/ingest/run", response_model=IngestTaskResponse, status_code=202)
def ingest_run(
    background_tasks: BackgroundTasks,
    offline: bool = Query(default=False),
    days_back: int = Query(default=7, ge=1, le=90),
    include_bip: bool = Query(default=False),
    include_ted: bool = Query(default=True),
    run_dedup: bool = Query(default=True),
) -> IngestTaskResponse:
    """Async ingestion trigger — returns 202 + task_id immediately.

    Poll:       GET /api/v1/ingest/tasks/{task_id}
    Live SSE:   GET /api/v1/ingest/stream/{task_id}
    """
    engine = get_engine()
    task_id = str(uuid.uuid4())
    params = {
        "offline": offline, "days_back": days_back,
        "include_bip": include_bip, "include_ted": include_ted,
        "run_dedup": run_dedup,
    }

    from services.ingestion.repository import get_or_create_default_tenant
    tenant_id = get_or_create_default_tenant(engine)

    # S106 — Billing plan limit check
    with engine.connect() as _conn:
        # Resolve org_id from tenant_id
        _org_row = _conn.execute(
            sa.text("SELECT id FROM organizations WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        ).fetchone()
        if _org_row:
            _org_id = str(_org_row[0])
            _sub = _conn.execute(
                sa.text("SELECT plan FROM subscription WHERE org_id = :oid LIMIT 1"),
                {"oid": _org_id},
            ).fetchone()
            if _sub:
                _plan = _sub[0]
                # Plan limits (tenders_limit not in table — use defaults per plan)
                _plan_limits = {"free": 500, "starter": 2000, "pro": 20000, "enterprise": 999999}
                _tenders_limit = _plan_limits.get(_plan, 500)
                _count = _conn.execute(
                    sa.text("SELECT count(*) FROM tender WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                ).scalar() or 0
                if _count >= _tenders_limit:
                    raise HTTPException(status_code=402, detail="Plan limit exceeded")

    created_at = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO ingest_task (id, tenant_id, status, params, created_at)
                VALUES (:id, :tenant_id, 'pending', :params, :created_at)
            """),
            {"id": task_id, "tenant_id": tenant_id,
             "params": json.dumps(params), "created_at": created_at},
        )

    _set_progress(task_id, "pending", 0, "Oczekiwanie na start...")
    t = threading.Thread(
        target=_run_ingest_worker, args=(task_id, tenant_id, params),
        daemon=True, name=f"ingest-{task_id[:8]}",
    )
    t.start()
    logger.info("Ingest task %s started (thread %s)", task_id, t.name)

    return IngestTaskResponse(
        task_id=task_id, status="pending",
        progress={"step": "pending", "pct": 0, "message": "Oczekiwanie na start..."},
        created_at=created_at.isoformat(),
    )


def _jsonb(val) -> dict | None:
    """Parse JSONB column — Postgres returns dict directly, not string."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        return json.loads(val)
    return None


@router.get("/ingest/tasks/{task_id}", response_model=IngestTaskResponse)
def get_ingest_task(task_id: str) -> IngestTaskResponse:
    """Poll single ingest task status."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("""
                SELECT id, status, progress, result, error,
                       created_at, started_at, finished_at
                FROM ingest_task WHERE id = :task_id
            """),
            {"task_id": task_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    with _PROGRESS_LOCK:
        live = _PROGRESS.get(task_id)

    progress = live or _jsonb(row[2])
    return IngestTaskResponse(
        task_id=str(row[0]), status=row[1], progress=progress,
        result=_jsonb(row[3]),
        error=row[4],
        created_at=row[5].isoformat() if row[5] else None,
        started_at=row[6].isoformat() if row[6] else None,
        finished_at=row[7].isoformat() if row[7] else None,
    )


@router.get("/ingest/tasks", response_model=list[IngestTaskResponse])
def list_ingest_tasks(limit: int = Query(default=20, ge=1, le=100)) -> list[IngestTaskResponse]:
    """List recent ingest tasks, newest first."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, status, progress, result, error,
                       created_at, started_at, finished_at
                FROM ingest_task ORDER BY created_at DESC LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()

    return [
        IngestTaskResponse(
            task_id=str(r[0]), status=r[1],
            progress=_jsonb(r[2]),
            result=_jsonb(r[3]),
            error=r[4],
            created_at=r[5].isoformat() if r[5] else None,
            started_at=r[6].isoformat() if r[6] else None,
            finished_at=r[7].isoformat() if r[7] else None,
        )
        for r in rows
    ]


@router.get("/ingest/stream/{task_id}")
async def stream_ingest_task(task_id: str, request: Request) -> StreamingResponse:
    """SSE stream — real-time progress events for an ingest task.

    Event format:  data: {step, pct, message, status}\\n\\n
    Stream closes when status becomes done or failed.
    """
    engine = get_engine()

    async def _generator():
        prev_pct = -1
        ticks = 0

        yield f"data: {json.dumps({'step': 'connected', 'pct': 0, 'message': 'Podlaczono...'})}\n\n"

        while ticks < 300:
            if await request.is_disconnected():
                break

            with _PROGRESS_LOCK:
                prog = dict(_PROGRESS.get(task_id, {}))

            with engine.connect() as conn:
                row = conn.execute(
                    sa.text("SELECT status FROM ingest_task WHERE id = :tid"),
                    {"tid": task_id},
                ).fetchone()

            db_status = row[0] if row else "unknown"
            pct = prog.get("pct", 0)

            if pct != prev_pct or db_status in ("done", "failed"):
                yield f"data: {json.dumps({'step': prog.get('step', 'running'), 'pct': pct, 'message': prog.get('message', ''), 'status': db_status})}\n\n"
                prev_pct = pct

            if db_status in ("done", "failed"):
                break

            await asyncio.sleep(1)
            ticks += 1

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/ingest/cache/invalidate")
def invalidate_ingest_cache(user: AuthUser) -> dict:
    """Inwaliduje cache scorera dla tenanta (po zmianie scoring_config)."""
    from services.ingestion.scorer import invalidate_scorer_cache
    tenant_id = str(user.org_id or "")
    invalidate_scorer_cache(tenant_id)
    return {"ok": True, "invalidated_for": tenant_id}



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
        conditions.append("LOWER(TRIM(t.voivodeship)) = LOWER(TRIM(:voiv))")
        params["voiv"] = voivodeship.strip()

    if source:
        conditions.append("t.source = CAST(:source AS source_kind)")
        params["source"] = source.lower()

    if cpv:
        codes = [c.strip() for c in cpv.split(",")]
        if len(codes) == 1:
            code = codes[0]
            # Zawsze użyj LIKE — obsługuje prefixe (45, 451…) i pełne kody (45111200, 45111200-0)
            # Jeśli podany z myślnikiem (45111200-0) — exact match; bez — prefix
            if re.match(r'^\d{8}-\d$', code):
                # Exact match z myślnikiem (np. 45111200-0)
                conditions.append("t.cpv && :cpv_arr")
                params["cpv_arr"] = "{" + code + "}"
            else:
                # Prefix search (działa dla 45111200, 451, 45, itd.)
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
        "score":       "t.match_score DESC NULLS LAST, t.published_at DESC NULLS LAST, t.id DESC",
        "deadline":    "t.deadline_at ASC NULLS LAST, t.id DESC",
        "value":       "t.value_pln DESC NULLS LAST, t.id DESC",
        "value_desc":  "t.value_pln DESC NULLS LAST, t.id DESC",
        "value_asc":   "t.value_pln ASC NULLS LAST, t.id DESC",
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


# ─── BUG 2: Alias /api/v1/tenders/{tender_id}/documents ───────────────────────

@router.get("/tenders/{tender_id}/documents", tags=["bzp-documents"])
def get_tender_documents_alias(tender_id: str, user: AuthUser):
    """Alias dla /api/v1/bzp/documents/{tender_id} — lista pobranych dokumentów SWZ."""
    import sqlalchemy as sa
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, bzp_notice_id, doc_type, filename, url, fetched_at,
                       LENGTH(content) as content_length
                FROM bzp_documents
                WHERE tender_id = :tid
                ORDER BY fetched_at DESC
            """),
            {"tid": tender_id},
        ).fetchall()

    return {
        "tender_id": tender_id,
        "total": len(rows),
        "documents": [
            {
                "id": str(r.id),
                "notice_id": r.bzp_notice_id,
                "doc_type": r.doc_type,
                "filename": r.filename,
                "download_url": r.url,
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
                "size_bytes": r.content_length or 0,
            }
            for r in rows
        ],
    }
