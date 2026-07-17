"""OLAP analytics endpoints — market evolution, price index, cohort, seasonal patterns.

GET  /api/v2/analytics/olap
GET  /api/v2/analytics/price-index
GET  /api/v2/analytics/buyer-trajectory
GET  /api/v2/analytics/seasonal
GET  /api/v2/analytics/cohort
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from typing import Any, Optional
import sqlalchemy as sa

from terra_db.session import get_engine
from ..auth.deps import AuthUser, get_current_user

router = APIRouter(prefix="/api/v2/analytics", tags=["analytics-olap"])


@router.get("/olap")
def market_olap(
    user: AuthUser,
    cpv_division: Optional[str] = None,
    year: Optional[int] = None,
    group_by: str = Query("quarter", pattern="^(quarter|month|year)$"),
) -> list[dict[str, Any]]:
    """OLAP market evolution cube query."""
    engine = get_engine()
    conditions = ["year IS NOT NULL AND quarter IS NOT NULL AND cpv_division IS NOT NULL"]
    params: dict = {}
    
    if cpv_division:
        conditions.append("cpv_division = :cpv")
        params["cpv"] = cpv_division
    if year:
        conditions.append("year = :year")
        params["year"] = year

    where = " AND ".join(conditions)
    sql = sa.text(f"""
        SELECT year, quarter, cpv_division, tender_count, total_value, avg_value, 
               median_value, won_count, win_rate
        FROM v_market_olap
        WHERE {where} AND buyer IS NULL
        ORDER BY year DESC, quarter DESC, tender_count DESC
        LIMIT 200
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "year": r[0], "quarter": r[1], "cpv_division": r[2],
            "tender_count": r[3],
            "total_value": float(r[4]) if r[4] else 0,
            "avg_value": float(r[5]) if r[5] else 0,
            "median_value": float(r[6]) if r[6] else 0,
            "won_count": r[7], "win_rate": float(r[8]) if r[8] else 0,
        }
        for r in rows
    ]


@router.get("/price-index")
def price_index(user: AuthUser, cpv_group: Optional[str] = None) -> list[dict[str, Any]]:
    """CPV price index — quarterly price evolution with YoY delta."""
    engine = get_engine()
    conditions = ["1=1"]
    params: dict = {}
    if cpv_group:
        conditions.append("cpv_group = :cpv")
        params["cpv"] = cpv_group

    sql = sa.text(f"""
        SELECT cpv_group, quarter, avg_price, sample_size, 
               prev_quarter_price, price_change_pct
        FROM v_cpv_price_index
        WHERE {" AND ".join(conditions)}
        ORDER BY cpv_group, quarter DESC
        LIMIT 200
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "cpv_group": r[0],
            "quarter": r[1].isoformat() if r[1] else None,
            "avg_price": float(r[2]) if r[2] else 0,
            "sample_size": r[3],
            "prev_price": float(r[4]) if r[4] else None,
            "change_pct": float(r[5]) if r[5] else None,
        }
        for r in rows
    ]


@router.get("/buyer-trajectory")
def buyer_trajectory(
    user: AuthUser,
    buyer: Optional[str] = None,
    top_n: int = Query(10, le=50),
) -> list[dict[str, Any]]:
    """Buyer lifecycle trajectory — monthly activity trends."""
    engine = get_engine()
    if buyer:
        sql = sa.text("""
            SELECT buyer, month, monthly_tenders, cumulative_tenders, monthly_avg_value
            FROM v_buyer_trajectory
            WHERE buyer ILIKE '%' || :buyer || '%'
            ORDER BY month DESC
            LIMIT 50
        """)
        params = {"buyer": buyer}
    else:
        sql = sa.text("""
            SELECT buyer, month, monthly_tenders, cumulative_tenders, monthly_avg_value
            FROM v_buyer_trajectory
            WHERE buyer_rank <= :top
            ORDER BY buyer, month DESC
        """)
        params = {"top": top_n}

    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "buyer": r[0],
            "month": r[1].isoformat() if r[1] else None,
            "monthly_tenders": r[2],
            "cumulative": r[3],
            "avg_value": float(r[4]) if r[4] else 0,
        }
        for r in rows
    ]


@router.get("/seasonal")
def seasonal_patterns(user: AuthUser, cpv_division: Optional[str] = None) -> list[dict[str, Any]]:
    """Seasonal patterns — which months/days peak per CPV."""
    engine = get_engine()
    conditions = ["1=1"]
    params: dict = {}
    if cpv_division:
        conditions.append("cpv_division = :cpv")
        params["cpv"] = cpv_division

    sql = sa.text(f"""
        SELECT cpv_division, month, count, avg_value, seasonal_index
        FROM v_seasonal_patterns
        WHERE {" AND ".join(conditions)} AND day_of_week IS NULL
        ORDER BY cpv_division, month
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    
    if not rows:
        # Fallback: include day_of_week aggregation
        sql2 = sa.text(f"""
            SELECT cpv_division, month, SUM(count) as count, 
                   AVG(avg_value) as avg_value, AVG(seasonal_index) as seasonal_index
            FROM v_seasonal_patterns
            WHERE {" AND ".join(conditions)}
            GROUP BY cpv_division, month
            ORDER BY cpv_division, month
        """)
        with engine.connect() as conn:
            rows = conn.execute(sql2, params).fetchall()

    return [
        {
            "cpv_division": r[0],
            "month": r[1],
            "count": r[2],
            "avg_value": float(r[3]) if r[3] else 0,
            "seasonal_index": float(r[4]) if r[4] else 1.0,
        }
        for r in rows
    ]


@router.get("/cohort")
def buyer_cohort(user: AuthUser) -> list[dict[str, Any]]:
    """Buyer cohort analysis — first-seen month → lifecycle retention."""
    engine = get_engine()
    sql = sa.text("""
        SELECT cohort_month, months_since_first, active_buyers, tender_count, total_value
        FROM v_buyer_cohort
        WHERE months_since_first <= 12
        ORDER BY cohort_month DESC, months_since_first
        LIMIT 200
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [
        {
            "cohort_month": r[0].isoformat() if r[0] else None,
            "months_since_first": r[1],
            "active_buyers": r[2],
            "tender_count": r[3],
            "total_value": float(r[4]) if r[4] else 0,
        }
        for r in rows
    ]
