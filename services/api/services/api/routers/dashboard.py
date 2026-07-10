"""
Dashboard router — statystyki ogólne dla użytkownika.

Endpoints:
    GET /api/v1/dashboard       — statystyki dla panelu głównego (v1)
    GET /api/v2/dashboard/stats — statystyki dla panelu głównego (v2)

S4-1 fix: all stats in a single CTE query (was 7 separate SELECTs → N+1).
S4-4 fix: in-process TTL cache 60s per org_id.
"""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter

from terra_db.session import get_engine
from ..auth.deps import AuthUser
from ..cache import get as cache_get, set as cache_set

router = APIRouter(tags=["dashboard"])

_CACHE_TTL = 60  # seconds


def _get_dashboard_data(tenant_id: str) -> dict:
    """Single-query dashboard stats via CTE — no N+1."""
    engine = get_engine()
    with engine.connect() as conn:
        # ── One CTE for all scalar aggregates ─────────────────────────────────
        agg = conn.execute(sa.text("""
            SELECT
                COUNT(*)                                                   AS total_tenders,
                COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE)   AS new_today,
                COUNT(*) FILTER (WHERE match_score > 0.6)                 AS high_score_count,
                ROUND(AVG(match_score)::numeric, 4)                       AS avg_score,
                COALESCE(SUM(value_pln) FILTER (WHERE value_pln IS NOT NULL), 0) AS pipeline_value,
                COUNT(DISTINCT buyer) FILTER (WHERE buyer IS NOT NULL)    AS unique_buyers
            FROM tender
            WHERE duplicate_of IS NULL
              AND tenant_id = :tid
        """), {"tid": tenant_id}).fetchone()

        total_tenders   = int(agg.total_tenders)   if agg else 0
        new_today       = int(agg.new_today)        if agg else 0
        high_score_count= int(agg.high_score_count) if agg else 0
        avg_score       = float(agg.avg_score)      if agg and agg.avg_score else None
        pipeline_value  = float(agg.pipeline_value) if agg else 0.0
        unique_buyers   = int(agg.unique_buyers)    if agg else 0

        # ── by_source (single GROUP BY) ───────────────────────────────────────
        source_rows = conn.execute(sa.text("""
            SELECT source::text, COUNT(*)
            FROM tender
            WHERE duplicate_of IS NULL AND tenant_id = :tid
            GROUP BY source
        """), {"tid": tenant_id}).fetchall()
        by_source = {r[0]: int(r[1]) for r in source_rows if r[0]}

        # ── top-5 by match_score ───────────────────────────────────────────────
        top_rows = conn.execute(sa.text("""
            SELECT id, title, source::text, value_pln, match_score, status::text
            FROM tender
            WHERE duplicate_of IS NULL
              AND match_score IS NOT NULL
              AND tenant_id = :tid
            ORDER BY match_score DESC
            LIMIT 5
        """), {"tid": tenant_id}).fetchall()
        top_tenders = [
            {
                "id": str(r.id),
                "title": r.title,
                "source": r.source,
                "value_pln": float(r.value_pln) if r.value_pln is not None else None,
                "match_score": float(r.match_score) if r.match_score is not None else None,
                "status": r.status,
            }
            for r in top_rows
        ]

    return {
        "total_tenders": total_tenders,
        "new_today": new_today,
        "high_score_count": high_score_count,
        "by_source": by_source,
        "top_tenders": top_tenders,
        "avg_score": avg_score,
        "pipeline_value": pipeline_value,
        "unique_buyers": unique_buyers,
    }


def _cached_dashboard(tenant_id: str) -> dict:
    """Return cached or fresh dashboard data (60s TTL)."""
    cache_key = f"dashboard:{tenant_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    data = _get_dashboard_data(tenant_id)
    cache_set(cache_key, data, ttl=_CACHE_TTL)
    return data


@router.get("/api/v1/dashboard")
def dashboard_stats_v1(user: AuthUser) -> dict:
    """Panel główny — statystyki przetargów (v1)."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    return _cached_dashboard(tenant_id)


@router.get("/api/v2/dashboard/stats")
def dashboard_stats_v2(user: AuthUser) -> dict:
    """Panel główny — statystyki przetargów (v2)."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    return _cached_dashboard(tenant_id)
