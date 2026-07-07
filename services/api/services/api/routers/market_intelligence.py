"""Faza 3 — Market Intelligence API.

Endpoints:
  GET /api/v2/intelligence/benchmark        — benchmark cen per CPV/region/kwartał
  GET /api/v2/intelligence/trends           — trendy rynkowe kwartalnie (mv_market_trend)
  GET /api/v2/intelligence/competitors/top  — top wykonawcy (mv_contractor_ranking)
  GET /api/v2/intelligence/buyers/top       — top zamawiający (mv_buyer_ranking)
  GET /api/v2/intelligence/prices/icb       — ceny Intercenbud z filtrem
  GET /api/v2/intelligence/prices/inflation — indeks inflacji cen ICB (mv_labor_inflation_index)
  GET /api/v2/intelligence/regional         — mapa cen regionalnych (mv_regional_price_level)
  GET /api/v2/intelligence/seasonality      — sezonowość przetargów per miesiąc
  GET /api/v2/intelligence/fts              — full-text search w historical_tenders (FTS)
  GET /api/v2/intelligence/summary          — agregowane KPI rynkowe dla dashboardu

Źródła: mv_tender_benchmark (6.6k), mv_market_trend, mv_contractor_ranking,
        mv_buyer_ranking, icb_ceny_srednie (784k), mv_labor_inflation_index,
        mv_regional_price_level, mv_competitor_recent_wins (91k), historical_tenders (1.4M)
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.deps import AuthUser
from terra_db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/intelligence", tags=["market-intelligence"])


def get_db():
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(get_db)]


# ─── Benchmark cen ────────────────────────────────────────────────────────────

@router.get("/benchmark", summary="Benchmark cen przetargów per CPV/region/kwartał")
def benchmark(
    user: AuthUser,
    db: DB,
    cpv_prefix: str = Query(..., min_length=2, description="CPV prefix np. '4523' lub '45'"),
    province: str | None = Query(None, description="Kod NUTS województwa np. 'PL22'"),
    quarters: int = Query(8, ge=1, le=20, description="Ile ostatnich kwartałów"),
):
    """Benchmark cen bezpośrednio z historical_tenders — dokładniejszy niż MV dla wąskich filtrów."""
    conditions = ["left(cpv_code, :cpv_len) = :cpv"]
    params: dict = {
        "cpv": cpv_prefix,
        "cpv_len": len(cpv_prefix),
        "quarters": quarters,
    }

    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT left(cpv_code, 5) AS cpv5, province,
               date_trunc('quarter', date::timestamp)::date AS quarter,
               count(*) AS n_tenders,
               round(avg(estimated_value)::numeric) AS avg_value,
               round(percentile_cont(0.5) WITHIN GROUP (ORDER BY estimated_value)::numeric) AS median_value,
               round(min(estimated_value)::numeric) AS min_value,
               round(max(estimated_value)::numeric) AS max_value,
               round(avg(offers_count)::numeric, 1) AS avg_competition,
               count(*) FILTER (WHERE procedure_result = 'zawarcieUmowy') AS n_won
        FROM historical_tenders
        WHERE {where}
          AND estimated_value IS NOT NULL AND estimated_value > 0
          AND date IS NOT NULL
          AND date >= (SELECT max(date) FROM historical_tenders) - (:quarters * INTERVAL '3 months')
        GROUP BY 1, 2, 3
        ORDER BY 3 DESC, 1
        LIMIT 200
    """), params).mappings().all()

    if not rows:
        return {"cpv_prefix": cpv_prefix, "province": province, "data": [], "total": 0}

    return {
        "cpv_prefix": cpv_prefix,
        "province": province,
        "data": [dict(r) for r in rows],
        "total": len(rows),
    }


# ─── Trendy rynkowe ───────────────────────────────────────────────────────────

@router.get("/trends", summary="Trendy rynkowe kwartalnie (mv_market_trend)")
def market_trends(
    user: AuthUser,
    db: DB,
    cpv_prefix: str | None = Query(None, description="CPV prefix np. '45'"),
    province: str | None = Query(None),
    quarters: int = Query(12, ge=1, le=24),
):
    """Dane z mv_market_trend — wstępnie zagregowane, sub-10ms."""
    conditions = ["quarter >= (SELECT max(quarter) FROM mv_market_trend) - ((:quarters - 1) * INTERVAL '3 months')"]
    params: dict = {"quarters": quarters}

    if cpv_prefix:
        conditions.append("left(cpv3, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix[:3]
        params["cpv_len"] = min(len(cpv_prefix), 3)

    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT cpv3, quarter,
               sum(n_tenders)::int AS n_tenders,
               round(sum(total_value_mln) * 1000000) AS total_value,
               round((sum(total_value_mln) * 1000000 / NULLIF(sum(n_tenders), 0))::numeric) AS avg_value,
               round(avg(avg_offers)::numeric, 1) AS avg_competition,
               sum(n_completed)::int AS n_completed
        FROM mv_market_trend
        WHERE {where}
        GROUP BY cpv3, quarter
        ORDER BY quarter DESC, cpv3
        LIMIT 300
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Top wykonawcy ────────────────────────────────────────────────────────────

@router.get("/competitors/top", summary="Top wykonawcy per CPV/region (mv_contractor_ranking)")
def top_competitors(
    user: AuthUser,
    db: DB,
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    limit: int = Query(20, le=100),
):
    """Dane z mv_contractor_ranking — wstępnie zagregowane."""
    conditions = ["contractor_nip IS NOT NULL"]
    params: dict = {"limit": limit}

    if cpv_prefix:
        conditions.append("left(cpv2, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix[:2]
        params["cpv_len"] = len(cpv_prefix[:2])
    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT contractor_nip AS nip, contractor_name,
               sum(won_tenders)::int AS wins,
               round(sum(won_value_mln) * 1000000) AS total_value,
               round((sum(won_value_mln) * 1000000 / NULLIF(sum(won_tenders), 0))::numeric) AS avg_value,
               round(avg(avg_competition)::numeric, 1) AS avg_competition,
               round(avg(win_rate_pct)::numeric, 1) AS win_rate_pct
        FROM mv_contractor_ranking
        WHERE {where}
        GROUP BY contractor_nip, contractor_name
        ORDER BY wins DESC
        LIMIT :limit
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Top zamawiający ──────────────────────────────────────────────────────────

@router.get("/buyers/top", summary="Top zamawiający per CPV/region (mv_buyer_ranking)")
def top_buyers(
    user: AuthUser,
    db: DB,
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    limit: int = Query(20, le=100),
):
    conditions = ["buyer_nip IS NOT NULL"]
    params: dict = {"limit": limit}

    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT buyer_nip, buyer AS buyer_name, province,
               total_tenders AS n_tenders,
               round(total_value_mln * 1000000) AS total_value,
               round(avg_value_k * 1000) AS avg_value,
               cpv_diversity
        FROM mv_buyer_ranking
        WHERE {where}
        ORDER BY total_value_mln DESC NULLS LAST
        LIMIT :limit
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Ceny ICB ─────────────────────────────────────────────────────────────────

@router.get("/prices/icb", summary="Ceny Intercenbud per kategoria/kwartał")
def icb_prices(
    user: AuthUser,
    db: DB,
    category: str | None = Query(None, description="np. beton_cement, robocizna"),
    typ_rms: str | None = Query(None, description="R=robocizna, M=materiał, S=sprzęt"),
    year: int | None = Query(None, ge=2010, le=2030),
    quarter: int | None = Query(None, ge=1, le=4),
    symbol: str | None = Query(None, description="Symbol ICB np. '1690000'"),
    limit: int = Query(100, le=500),
):
    conditions = ["1=1"]
    params: dict = {"limit": limit}

    if category:
        conditions.append("category = :category")
        params["category"] = category
    if typ_rms:
        if typ_rms.upper() not in ("R", "M", "S"):
            raise HTTPException(status_code=400, detail="typ_rms musi być R, M lub S")
        conditions.append("typ_rms = :typ_rms")
        params["typ_rms"] = typ_rms.upper()
    if year:
        conditions.append("kwartalrok = :year")
        params["year"] = year
    if quarter:
        conditions.append("kwartalnr = :quarter")
        params["quarter"] = quarter
    if symbol:
        conditions.append("symbol LIKE :symbol")
        params["symbol"] = f"{symbol}%"

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT symbol, indeks_eto, nazwa, typ_rms, category,
               cena_netto, cena_narzut, kwartalrok, kwartalnr
        FROM icb_ceny_srednie
        WHERE {where}
        ORDER BY kwartalrok DESC, kwartalnr DESC, symbol
        LIMIT :limit
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Inflacja ICB ─────────────────────────────────────────────────────────────

@router.get("/prices/inflation", summary="Indeks inflacji cen materiałów/robocizny ICB")
def price_inflation(
    user: AuthUser,
    db: DB,
    category: str | None = Query(None),
    typ_rms: str | None = Query(None, description="R|M|S"),
):
    """YoY i QoQ indeks zmian cen z mv_labor_inflation_index."""
    if typ_rms and typ_rms.upper() not in ("R", "M", "S"):
        raise HTTPException(status_code=400, detail="typ_rms musi być R, M lub S")

    conditions = ["1=1"]
    params: dict = {}

    if category:
        conditions.append("category = :category")
        params["category"] = category
    if typ_rms:
        conditions.append("typ_rms = :typ_rms")
        params["typ_rms"] = typ_rms.upper()

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT yr, q, typ_rms, category,
               avg_price, avg_price_markup, n_items,
               yoy_pct, qoq_pct
        FROM mv_labor_inflation_index
        WHERE {where}
        ORDER BY yr DESC, q DESC, typ_rms, category
        LIMIT 500
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Ceny regionalne ──────────────────────────────────────────────────────────

@router.get("/regional", summary="Mapa cen regionalnych per CPV/województwo (ICB koeficjent)")
def regional_prices(
    user: AuthUser,
    db: DB,
    cpv_prefix: str | None = Query(None, min_length=2),
    quarter: str | None = Query(None, description="Kwartał ISO np. '2025-01-01'"),
    nuts2_code: str | None = Query(None, description="Kod NUTS2 np. 'PL22'"),
):
    conditions = ["1=1"]
    params: dict = {}

    if cpv_prefix:
        conditions.append("cpv5 LIKE :cpv_q")
        params["cpv_q"] = f"{cpv_prefix}%"
    if quarter:
        conditions.append("quarter = :quarter")
        params["quarter"] = quarter
    if nuts2_code:
        conditions.append("nuts2_code = :nuts2_code")
        params["nuts2_code"] = nuts2_code

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT nuts2_code, voivodeship_pl, cpv5, quarter,
               n_tenders, avg_value, median_value, avg_competition, icb_labor_coeff
        FROM mv_regional_price_level
        WHERE {where}
        ORDER BY quarter DESC, nuts2_code, cpv5
        LIMIT 500
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Sezonowość ───────────────────────────────────────────────────────────────

@router.get("/seasonality", summary="Sezonowość przetargów per miesiąc roku")
def seasonality(
    user: AuthUser,
    db: DB,
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
):
    """Sezonowość ogłoszeń + wartości per miesiąc — agregat wieloletni."""
    conditions = ["date IS NOT NULL", "estimated_value IS NOT NULL", "estimated_value > 0"]
    params: dict = {}

    if cpv_prefix:
        conditions.append("left(cpv_code, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix
        params["cpv_len"] = len(cpv_prefix)
    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT EXTRACT(MONTH FROM date::date)::int AS month,
               count(*) AS n_tenders,
               round(avg(estimated_value)::numeric) AS avg_value,
               round(sum(estimated_value)::numeric) AS total_value,
               round(avg(offers_count)::numeric, 1) AS avg_competition
        FROM historical_tenders
        WHERE {where}
        GROUP BY 1 ORDER BY 1
    """), params).mappings().all()

    return {"data": [dict(r) for r in rows]}


# ─── Full-text search ─────────────────────────────────────────────────────────

@router.get("/fts", summary="Full-text search w 1.4M przetargów (GIN index)")
def fts_search(
    user: AuthUser,
    db: DB,
    q: str = Query(..., min_length=2, description="Zapytanie FTS np. 'remont drogi'"),
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    value_min: float | None = Query(None, ge=0),
    value_max: float | None = Query(None, ge=0),
    notice_type: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    conditions = ["title_tsv @@ plainto_tsquery('simple', :q)"]
    params: dict = {"q": q, "limit": limit, "offset": offset}

    if cpv_prefix:
        conditions.append("left(cpv_code, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix
        params["cpv_len"] = len(cpv_prefix)
    if province:
        conditions.append("province = :province")
        params["province"] = province
    if value_min is not None:
        conditions.append("estimated_value >= :value_min")
        params["value_min"] = value_min
    if value_max is not None:
        conditions.append("estimated_value <= :value_max")
        params["value_max"] = value_max
    if notice_type:
        conditions.append("notice_type = :notice_type")
        params["notice_type"] = notice_type

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT id, title, buyer, buyer_nip, province, cpv_code,
               estimated_value, date, notice_type, procedure_result,
               offers_count, contractor_name,
               ts_rank(title_tsv, plainto_tsquery('simple', :q)) AS rank
        FROM historical_tenders
        WHERE {where}
        ORDER BY rank DESC, date DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(
        f"SELECT count(*) FROM historical_tenders WHERE {where}"
    ), params).scalar()

    return {
        "query": q,
        "items": [dict(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


# ─── Summary KPI ─────────────────────────────────────────────────────────────

@router.get("/summary", summary="Agregowane KPI rynkowe dla dashboardu")
def market_summary(
    user: AuthUser,
    db: DB,
    cpv_prefix: str | None = Query(None, description="CPV prefix np. '45'"),
    province: str | None = Query(None),
):
    """Szybkie KPI: łączna liczba + wartość przetargów (1 rok), top CPV, top region."""
    conditions = ["date >= (SELECT max(date) FROM historical_tenders) - INTERVAL '1 year'"]
    params: dict = {}

    if cpv_prefix:
        conditions.append("left(cpv_code, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix
        params["cpv_len"] = len(cpv_prefix)
    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    kpi = db.execute(text(f"""
        SELECT
            count(*) AS n_tenders,
            count(*) FILTER (WHERE estimated_value IS NOT NULL) AS n_with_value,
            round(sum(estimated_value)::numeric / 1e6, 1) AS total_value_mln,
            round(avg(estimated_value)::numeric) AS avg_value,
            round(avg(offers_count)::numeric, 1) AS avg_competition,
            count(DISTINCT buyer_nip) AS n_buyers,
            count(DISTINCT contractor_national_id)
              FILTER (WHERE procedure_result = 'zawarcieUmowy') AS n_contractors
        FROM historical_tenders
        WHERE {where}
    """), params).mappings().one()

    top_cpv = db.execute(text(f"""
        SELECT left(cpv_code, 2) AS cpv2, count(*) AS n
        FROM historical_tenders
        WHERE {where} AND cpv_code IS NOT NULL
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5
    """), params).mappings().all()

    top_province = db.execute(text(f"""
        SELECT province, count(*) AS n
        FROM historical_tenders
        WHERE {where} AND province IS NOT NULL
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5
    """), params).mappings().all()

    return {
        "kpi": dict(kpi),
        "top_cpv": [dict(r) for r in top_cpv],
        "top_province": [dict(r) for r in top_province],
        "filters": {"cpv_prefix": cpv_prefix, "province": province},
    }


# ─── Sekocenbud search ─────────────────────────────────────────────────────────

@router.get("/sekocenbud", summary="Wyszukiwanie w bazie SEKOCENBUD (23 725 pozycji)")
def sekocenbud_search(
    user: AuthUser,
    db: DB,
    q: str = Query("", description="Fraza wyszukiwania w opisie lub symbolu"),
    chapter: str | None = Query(None, description="Filtr po chapter_name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """Full-text search w bazie SEKOCENBUD. Zwraca pozycje z ceną, jednostką i symbolem."""
    from sqlalchemy.sql import text

    params: dict = {"limit": limit, "offset": offset}
    where_parts = []

    if q:
        where_parts.append("(opis ILIKE :q OR symbol ILIKE :q OR katalog_code ILIKE :q)")
        params["q"] = f"%{q}%"
    if chapter:
        where_parts.append("chapter_name ILIKE :chapter")
        params["chapter"] = f"%{chapter}%"

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    rows = db.execute(text(f"""
        SELECT id, symbol, katalog_code, chapter_name, opis, jm, cena, rg, m, s
        FROM sekocenbud_items
        {where}
        ORDER BY symbol
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM sekocenbud_items {where}
    """), params).scalar()

    return {
        "total": total,
        "items": [dict(r) for r in rows],
    }
