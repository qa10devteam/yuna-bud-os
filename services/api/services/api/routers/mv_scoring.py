"""Materialized Views + Scoring V3 endpoints.

GET /api/v2/mv/pipeline-kpi
GET /api/v2/mv/cpv-heatmap
GET /api/v2/mv/market-forecast
POST /api/v2/mv/refresh
GET /api/v2/scoring/v3/percentile
GET /api/v2/scoring/v3/hot-tenders
GET /api/v2/scoring/v3/market-median
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2", tags=["mv", "scoring-v3"])


# ─── Materialized Views ──────────────────────────────────────────────────────

@router.get("/mv/pipeline-kpi")
def pipeline_kpi(tenant_id: str) -> dict[str, Any]:
    """Pipeline KPI from materialized view."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT * FROM mv_pipeline_kpi WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).fetchone()

    if not row:
        return {
            "tenant_id": tenant_id,
            "active_count": 0,
            "pipeline_value": 0,
            "won_mtd": 0,
            "decided_mtd": 0,
            "avg_deal_size": 0,
            "total_won_value": 0,
            "win_rate_pct": 0,
        }

    keys = ["tenant_id", "active_count", "pipeline_value", "won_mtd",
            "decided_mtd", "avg_deal_size", "total_won_value"]
    data = dict(zip(keys, row))
    # Compute win rate
    decided = data.get("decided_mtd") or 0
    won = data.get("won_mtd") or 0
    data["win_rate_pct"] = round(won * 100 / decided, 1) if decided > 0 else 0
    # Convert Decimals
    for k in data:
        if hasattr(data[k], "quantize"):
            data[k] = float(data[k])
    return data


@router.get("/mv/cpv-heatmap")
def cpv_heatmap(cpv5: str | None = None, voivodeship: str | None = None) -> list[dict]:
    """CPV heatmap data."""
    engine = get_engine()
    sql = "SELECT cpv5, voivodeship, tender_count, avg_value, total_value FROM mv_cpv_heatmap WHERE 1=1"
    params: dict = {}
    if cpv5:
        sql += " AND cpv5 = :cpv5"
        params["cpv5"] = cpv5
    if voivodeship:
        sql += " AND voivodeship = :voiv"
        params["voiv"] = voivodeship
    sql += " ORDER BY tender_count DESC LIMIT 100"

    with engine.connect() as conn:
        rows = conn.execute(sa.text(sql), params).fetchall()

    return [
        {
            "cpv5": r[0], "voivodeship": r[1], "tender_count": r[2],
            "avg_value": float(r[3]) if r[3] else 0,
            "total_value": float(r[4]) if r[4] else 0,
        }
        for r in rows
    ]


@router.get("/mv/market-forecast")
def market_forecast(cpv5: str | None = None, limit: int = 24) -> list[dict]:
    """Monthly market forecast."""
    engine = get_engine()
    sql = "SELECT month, cpv5, tender_count, total_value, avg_value FROM mv_market_forecast WHERE 1=1"
    params: dict = {"lim": limit}
    if cpv5:
        sql += " AND cpv5 = :cpv5"
        params["cpv5"] = cpv5
    sql += " ORDER BY month DESC LIMIT :lim"

    with engine.connect() as conn:
        rows = conn.execute(sa.text(sql), params).fetchall()

    return [
        {
            "month": str(r[0])[:10] if r[0] else None,
            "cpv5": r[1],
            "tender_count": r[2],
            "total_value": float(r[3]) if r[3] else 0,
            "avg_value": float(r[4]) if r[4] else 0,
        }
        for r in rows
    ]


@router.post("/mv/refresh")
def refresh_mvs() -> dict:
    """Refresh all materialized views."""
    engine = get_engine()
    refreshed = []
    views = ["mv_pipeline_kpi", "mv_cpv_heatmap", "mv_market_forecast"]
    with engine.begin() as conn:
        for mv in views:
            try:
                conn.execute(sa.text(f"REFRESH MATERIALIZED VIEW {mv}"))
                refreshed.append(mv)
            except Exception as e:
                refreshed.append(f"{mv}: ERROR {e}")
    return {"refreshed": refreshed}


# ─── Scoring V3 (Window Functions) ───────────────────────────────────────────

@router.get("/scoring/v3/percentile")
def scoring_percentile(tenant_id: str, tender_id: str | None = None) -> list[dict]:
    """Score percentile ranking using window functions."""
    engine = get_engine()
    sql = """
        SELECT id, title, match_score,
            RANK() OVER (ORDER BY match_score DESC NULLS LAST) as rank_overall,
            COUNT(*) OVER () as total_count,
            ROUND(
                RANK() OVER (ORDER BY match_score DESC NULLS LAST) * 100.0
                / NULLIF(COUNT(*) OVER (), 0), 1
            ) as percentile_desc
        FROM tender
        WHERE tenant_id = :tid AND duplicate_of IS NULL AND match_score IS NOT NULL
        ORDER BY match_score DESC NULLS LAST
        LIMIT 50
    """
    params: dict = {"tid": tenant_id}

    with engine.connect() as conn:
        rows = conn.execute(sa.text(sql), params).fetchall()

    results = [
        {
            "id": str(r[0]), "title": r[1],
            "match_score": float(r[2]) if r[2] else 0,
            "rank": r[3], "total": r[4],
            "percentile": float(r[5]) if r[5] else 0,
        }
        for r in rows
    ]

    if tender_id:
        results = [r for r in results if r["id"] == tender_id] or results[:10]

    return results


@router.get("/scoring/v3/hot-tenders")
def hot_tenders(tenant_id: str, days: int = 14) -> list[dict]:
    """Hot tenders: high score + deadline within N days."""
    engine = get_engine()
    sql = """
        SELECT id, title, buyer, value_pln, match_score, deadline_at,
               deadline_at - NOW() as time_left
        FROM tender
        WHERE tenant_id = :tid
          AND duplicate_of IS NULL
          AND match_score > 0.4
          AND deadline_at IS NOT NULL
          AND deadline_at > NOW()
          AND deadline_at <= NOW() + :days * INTERVAL '1 day'
        ORDER BY match_score DESC, deadline_at ASC
        LIMIT 20
    """
    with engine.connect() as conn:
        rows = conn.execute(sa.text(sql), {"tid": tenant_id, "days": days}).fetchall()

    return [
        {
            "id": str(r[0]), "title": r[1], "buyer": r[2],
            "value_pln": float(r[3]) if r[3] else None,
            "match_score": float(r[4]) if r[4] else 0,
            "deadline_at": str(r[5]) if r[5] else None,
            "days_left": r[6].days if r[6] else None,
        }
        for r in rows
    ]


@router.get("/scoring/v3/market-median")
def market_median(cpv5: str) -> dict:
    """Market median value for a CPV prefix."""
    engine = get_engine()
    sql = """
        SELECT
            COUNT(*) as sample_size,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value_pln) as q1,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value_pln) as median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value_pln) as q3,
            AVG(value_pln) as mean
        FROM tender, LATERAL UNNEST(cpv) as cpv_code
        WHERE LEFT(cpv_code, 5) = :cpv5 AND value_pln IS NOT NULL AND value_pln > 0
    """
    with engine.connect() as conn:
        row = conn.execute(sa.text(sql), {"cpv5": cpv5}).fetchone()

    if not row or not row[0]:
        return {"cpv5": cpv5, "sample_size": 0}

    return {
        "cpv5": cpv5,
        "sample_size": row[0],
        "q1": float(row[1]) if row[1] else 0,
        "median": float(row[2]) if row[2] else 0,
        "q3": float(row[3]) if row[3] else 0,
        "mean": float(row[4]) if row[4] else 0,
    }
