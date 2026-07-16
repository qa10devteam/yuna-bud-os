"""Faza 13 — BZP v2 sync endpoint + tenders listing."""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Query

from terra_db.session import get_engine
from ..auth.deps import AuthUser
from .bzp import _do_sync
from .tenders_v2 import TenderListResponse, list_tenders as _list_tenders

router = APIRouter(prefix="/api/v2/bzp", tags=["bzp-v2"])


@router.post("/sync")
def bzp_sync_v2(background_tasks: BackgroundTasks, user: AuthUser, days_back: int = 7) -> dict:
    """Ręczny trigger synchronizacji BZP."""
    background_tasks.add_task(_do_sync, days_back)
    return {
        "status": "started",
        "days_back": days_back,
        "message": f"Synchronizacja BZP uruchomiona — ostatnie {days_back} dni",
    }


@router.get("/status")
def bzp_status(user: AuthUser) -> dict:
    """Status ostatniej synchronizacji i liczba przetargów."""
    engine = get_engine()

    with engine.connect() as conn:
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM tender WHERE source='bzp'")
        ).scalar() or 0

        last_sync = conn.execute(
            sa.text(
                """SELECT MAX(created_at) as last_sync,
                          COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as today_count
                   FROM tender WHERE source='bzp'"""
            )
        ).fetchone()

        by_status = conn.execute(
            sa.text(
                "SELECT status, COUNT(*) as cnt FROM tender WHERE source='bzp' GROUP BY status ORDER BY cnt DESC"
            )
        ).fetchall()

    return {
        "total_tenders": int(total),
        "last_sync": last_sync.last_sync.isoformat() if last_sync and last_sync.last_sync else None,
        "synced_today": int(last_sync.today_count) if last_sync else 0,
        "by_status": [{"status": r.status, "count": int(r.cnt)} for r in by_status],
    }


@router.get("/tenders", response_model=TenderListResponse, summary="Przetargi z BZP")
def bzp_list_tenders(
    user: AuthUser,
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    cpv: str | None = Query(None),
    voivodeship: str | None = Query(None),
    value_min: float | None = Query(None, ge=0),
    value_max: float | None = Query(None, ge=0),
    deadline_before: str | None = Query(None),
    hide_duplicates: bool = Query(False),
    q: str | None = Query(None, min_length=2),
    sort: str | None = Query(None),
) -> TenderListResponse:
    """Lista przetargów z BZP (skrót do /api/v2/tenders?source=bzp)."""
    return _list_tenders(
        user=user,
        cursor=cursor,
        limit=limit,
        status=status,
        source="bzp",
        cpv=cpv,
        voivodeship=voivodeship,
        value_min=value_min,
        value_max=value_max,
        min_value=None,
        max_value=None,
        deadline_before=deadline_before,
        hide_duplicates=hide_duplicates,
        q=q,
        fields=None,
        sort=sort,
    )
