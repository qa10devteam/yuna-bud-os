"""ICB Advanced Router — pełne wykorzystanie InterCenBud 784k rekordów.

Endpoints:
  POST /api/v2/icb/forecast/compute       — oblicz prognozy dla wszystkich kategorii
  GET  /api/v2/icb/forecast               — pobierz prognozę cen
  GET  /api/v2/icb/search                 — semantyczne wyszukiwanie pozycji
  GET  /api/v2/icb/categories             — lista kategorii + stats
  GET  /api/v2/icb/category/{cat}/detail  — szczegóły kategorii z trendem
  GET  /api/v2/icb/compare                — porównanie cen regionalne
  GET  /api/v2/icb/basket                 — koszyk materiałów (NPV analiza)
  POST /api/v2/icb/kosztorys-autofill     — auto-fill cen z ICB do kosztorysu
  GET  /api/v2/icb/dashboard              — dashboard z kluczowymi wskaźnikami
  GET  /api/v2/icb/robocizna/map          — mapa stawek robocizny per region
  GET  /api/v2/icb/volatility-matrix      — macierz zmienności cen
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/icb", tags=["icb-advanced"])
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /forecast/compute
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/forecast/compute")
def compute_forecasts(horizon: int = 4) -> dict:
    """Uruchom Holt-Winters forecasting dla wszystkich kategorii × R/M/S."""
    from ..intelligence.forecaster import compute_all_forecasts
    result = compute_all_forecasts(horizon)
    return result


@router.get("/forecast")
def get_forecast(
    category: str | None = None,
    typ_rms: str = "M",
) -> list[dict]:
    """Pobierz prognozy cen z icb_forecast."""
    from ..intelligence.forecaster import get_forecasts
    return get_forecasts(category, typ_rms)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /search — trigram + ILIKE fuzzy search po 784k pozycjach
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/search")
def search_icb_prices(
    q: str = Query(..., min_length=2, description="Szukana fraza"),
    typ_rms: str | None = Query(None, description="R, M, or S"),
    category: str | None = None,
    quarter: str | None = Query(None, description="np. 2026-2"),
    limit: int = 30,
) -> dict:
    """Fuzzy search po ICB cenach średnich. Zwraca pozycje z cenami + trend info."""
    from ..intelligence.icb_service import search_icb, get_latest_quarter

    if quarter:
        parts = quarter.split("-")
        rok, nr = int(parts[0]), int(parts[1])
    else:
        rok, nr = get_latest_quarter()

    results = search_icb(q, typ_rms=typ_rms, kwartalrok=rok, kwartalnr=nr, category=category, limit=limit)

    # Enrich with previous quarter for comparison
    if results and rok > 2008:
        prev_nr = nr - 1 if nr > 1 else 4
        prev_rok = rok if nr > 1 else rok - 1
        engine = get_engine()
        symbols = [r["symbol"] for r in results if r.get("symbol")]
        if symbols:
            with engine.connect() as conn:
                placeholders = ",".join(f":s{i}" for i in range(len(symbols)))
                params = {f"s{i}": s for i, s in enumerate(symbols)}
                params["rok"] = prev_rok
                params["nr"] = prev_nr
                prev_rows = conn.execute(sa.text(f"""
                    SELECT symbol, cena_netto FROM icb_ceny_srednie
                    WHERE symbol IN ({placeholders}) AND kwartalrok=:rok AND kwartalnr=:nr
                """), params).fetchall()
                prev_map = {r[0]: float(r[1]) for r in prev_rows if r[1]}

            for r in results:
                prev = prev_map.get(r.get("symbol"))
                if prev and prev > 0:
                    r["prev_quarter_price"] = prev
                    r["qoq_change_pct"] = round((r["cena_netto"] - prev) / prev * 100, 2)

    return {
        "quarter": f"{rok}-Q{nr}",
        "count": len(results),
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /categories — stats per category
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/categories")
def icb_categories() -> list[dict]:
    """Lista kategorii ICB z liczbą pozycji i średnimi cenami."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            WITH latest AS (
                SELECT kwartalrok, kwartalnr FROM icb_ceny_srednie
                ORDER BY kwartalrok DESC, kwartalnr DESC LIMIT 1
            )
            SELECT c.category,
                   COUNT(*) as count,
                   ROUND(AVG(c.cena_netto)::numeric, 2) as avg_price,
                   ROUND(MIN(c.cena_netto)::numeric, 2) as min_price,
                   ROUND(MAX(c.cena_netto)::numeric, 2) as max_price,
                   COUNT(DISTINCT c.symbol) as unique_symbols
            FROM icb_ceny_srednie c
            JOIN latest l ON c.kwartalrok = l.kwartalrok AND c.kwartalnr = l.kwartalnr
            WHERE c.category IS NOT NULL AND c.cena_netto > 0
            GROUP BY c.category
            ORDER BY count DESC
        """)).fetchall()

    return [
        {
            "category": r[0], "count": r[1],
            "avg_price": float(r[2]) if r[2] else 0,
            "min_price": float(r[3]) if r[3] else 0,
            "max_price": float(r[4]) if r[4] else 0,
            "unique_symbols": r[5],
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /category/{cat}/detail — trend + top pozycje
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/category/{category}/detail")
def category_detail(category: str, quarters: int = 12) -> dict:
    """Szczegóły kategorii: trend cenowy, top materiały, zmienność."""
    engine = get_engine()
    with engine.connect() as conn:
        # Trend per quarter
        trend = conn.execute(sa.text("""
            SELECT kwartalrok, kwartalnr,
                   ROUND(AVG(cena_netto)::numeric, 4) as avg_price,
                   ROUND(STDDEV(cena_netto)::numeric, 4) as std_price,
                   COUNT(*) as n
            FROM icb_ceny_srednie
            WHERE category = :cat AND typ_rms = 'M' AND cena_netto > 0
            GROUP BY kwartalrok, kwartalnr
            ORDER BY kwartalrok DESC, kwartalnr DESC
            LIMIT :q
        """), {"cat": category, "q": quarters}).fetchall()

        # Top 10 most expensive
        top = conn.execute(sa.text("""
            WITH latest AS (
                SELECT kwartalrok, kwartalnr FROM icb_ceny_srednie
                ORDER BY kwartalrok DESC, kwartalnr DESC LIMIT 1
            )
            SELECT c.nazwa, c.symbol, c.jednostka, c.cena_netto
            FROM icb_ceny_srednie c JOIN latest l ON c.kwartalrok=l.kwartalrok AND c.kwartalnr=l.kwartalnr
            WHERE c.category = :cat AND c.typ_rms = 'M' AND c.cena_netto > 0
            ORDER BY c.cena_netto DESC LIMIT 10
        """), {"cat": category}).fetchall()

        # Most volatile (highest QoQ change)
        volatile = conn.execute(sa.text("""
            WITH price_data AS (
                SELECT symbol, kwartalrok, kwartalnr, cena_netto
                FROM icb_ceny_srednie
                WHERE category = :cat AND typ_rms = 'M' AND cena_netto > 0
                  AND kwartalrok >= 2024
            )
            SELECT symbol,
                   ROUND((MAX(cena_netto) - MIN(cena_netto)) / NULLIF(AVG(cena_netto), 0) * 100, 2) as price_range_pct
            FROM price_data
            WHERE symbol IS NOT NULL
            GROUP BY symbol
            HAVING COUNT(*) >= 4
            ORDER BY price_range_pct DESC
            LIMIT 10
        """), {"cat": category}).fetchall()

    return {
        "category": category,
        "trend": [
            {"period": f"{r[0]}-Q{r[1]}", "avg_price": float(r[2]), "std": float(r[3]) if r[3] else 0, "n": r[4]}
            for r in trend
        ],
        "top_expensive": [
            {"nazwa": r[0], "symbol": r[1], "jednostka": r[2], "cena_netto": float(r[3])}
            for r in top
        ],
        "most_volatile": [
            {"symbol": r[0], "price_range_pct": float(r[1])}
            for r in volatile
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /compare — porównanie regionalne
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/compare")
def compare_regional(
    category: str = "murarstwo",
    typ_rms: str = "M",
) -> dict:
    """Porównanie cen z uwzględnieniem współczynników regionalnych."""
    from ..intelligence.icb_service import get_latest_quarter, get_regional_coefficient

    rok, nr = get_latest_quarter()
    engine = get_engine()

    with engine.connect() as conn:
        base = conn.execute(sa.text("""
            SELECT ROUND(AVG(cena_netto)::numeric, 2) as avg_price
            FROM icb_ceny_srednie
            WHERE category = :cat AND typ_rms = :typ
              AND kwartalrok = :rok AND kwartalnr = :nr AND cena_netto > 0
        """), {"cat": category, "typ": typ_rms, "rok": rok, "nr": nr}).scalar()

    if not base:
        return {"error": "no data", "category": category}

    base_price = float(base)
    regions = [
        "mazowieckie", "śląskie", "dolnośląskie", "małopolskie",
        "wielkopolskie", "pomorskie", "łódzkie", "kujawsko-pomorskie",
        "lubelskie", "podkarpackie", "warmińsko-mazurskie",
        "zachodniopomorskie", "opolskie", "świętokrzyskie",
        "podlaskie", "lubuskie",
    ]

    results = []
    for reg in regions:
        coeff = get_regional_coefficient(reg, "Ogolne", rok, nr)
        results.append({
            "voivodeship": reg,
            "coefficient": coeff,
            "adjusted_price": round(base_price * coeff, 2),
            "diff_vs_national_pct": round((coeff - 1.0) * 100, 2),
        })

    results.sort(key=lambda x: x["coefficient"], reverse=True)
    return {
        "category": category,
        "typ_rms": typ_rms,
        "quarter": f"{rok}-Q{nr}",
        "national_avg": base_price,
        "regions": results,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# POST /basket — koszyk materiałów z prognozą kosztu
# ═══════════════════════════════════════════════════════════════════════════════

class BasketItem(BaseModel):
    symbol: str | None = None
    query: str | None = None
    category: str | None = None
    typ_rms: str | None = None
    quantity: float = 1.0
    unit: str = "szt"


class BasketRequest(BaseModel):
    items: list[BasketItem]
    voivodeship: str | None = None


@router.post("/basket")
def compute_basket(body: BasketRequest) -> dict:
    """Oblicz koszt koszyka materiałów z cenami ICB + korekta regionalna."""
    from ..intelligence.icb_service import get_latest_quarter, search_icb, get_icb_price, get_regional_coefficient

    rok, nr = get_latest_quarter()
    coeff = 1.0
    if body.voivodeship:
        coeff = get_regional_coefficient(body.voivodeship, "Ogolne", rok, nr)

    results = []
    total_cost = 0.0

    for item in body.items:
        if item.symbol:
            price_data = get_icb_price(item.symbol, rok, nr)
        elif item.query:
            matches = search_icb(item.query, kwartalrok=rok, kwartalnr=nr, limit=1)
            price_data = matches[0] if matches else None
        elif item.category:
            matches = search_icb(item.category.replace('_', ' '), typ_rms=item.typ_rms, kwartalrok=rok, kwartalnr=nr, limit=1)
            price_data = matches[0] if matches else None
        else:
            continue

        if price_data:
            unit_price = price_data["cena_netto"] * coeff
            line_cost = unit_price * item.quantity
            total_cost += line_cost
            results.append({
                "nazwa": price_data["nazwa"],
                "symbol": price_data["symbol"],
                "unit_price": round(unit_price, 2),
                "quantity": item.quantity,
                "unit": price_data.get("jednostka", item.unit),
                "line_cost": round(line_cost, 2),
            })
        else:
            results.append({
                "query": item.query or item.symbol,
                "error": "not_found",
            })

    return {
        "quarter": f"{rok}-Q{nr}",
        "voivodeship": body.voivodeship,
        "regional_coefficient": coeff,
        "items": results,
        "total_cost": round(total_cost, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# POST /kosztorys-autofill — auto uzupełnianie kosztorysu cenami ICB
# ═══════════════════════════════════════════════════════════════════════════════

class AutofillRequest(BaseModel):
    kosztorys_id: str
    voivodeship: str | None = None
    override_existing: bool = False


@router.post("/kosztorys-autofill")
def kosztorys_autofill(body: AutofillRequest) -> dict:
    """Auto-fill puste ceny w kosztorysie używając ICB + korekta regionalna."""
    from ..intelligence.icb_service import get_latest_quarter, search_icb, get_regional_coefficient

    engine = get_engine()
    rok, nr = get_latest_quarter()
    coeff = get_regional_coefficient(body.voivodeship or "mazowieckie", "Ogolne", rok, nr)

    with engine.connect() as conn:
        # Fetch pozycje kosztorysu bez ceny (lub wszystkie jeśli override)
        if body.override_existing:
            filter_clause = ""
        else:
            filter_clause = "AND (kp.m_jcena IS NULL OR kp.m_jcena = 0)"

        rows = conn.execute(sa.text(f"""
            SELECT kp.id, kp.opis, kp.symbol_katalog, kp.jednostka
            FROM kosztorys_pozycja kp
            WHERE kp.kosztorys_id = :kid {filter_clause}
        """), {"kid": body.kosztorys_id}).fetchall()

    filled = 0
    not_found = 0
    updates = []

    for row in rows:
        # Try by symbol first, then by description
        symbol = row[2]
        opis = row[1]

        price_data = None
        if symbol:
            matches = search_icb(symbol, kwartalrok=rok, kwartalnr=nr, limit=1)
            if matches and matches[0].get("cena_netto", 0) > 0:
                price_data = matches[0]

        if not price_data and opis:
            # Try fuzzy search by description
            matches = search_icb(opis[:60], kwartalrok=rok, kwartalnr=nr, limit=1)
            if matches and matches[0].get("cena_netto", 0) > 0:
                price_data = matches[0]

        if price_data:
            adjusted_price = round(price_data["cena_netto"] * coeff, 2)
            updates.append({
                "id": row[0],
                "icb_price": adjusted_price,
                "icb_symbol": price_data["symbol"],
                "icb_nazwa": price_data["nazwa"],
            })
            filled += 1
        else:
            not_found += 1

    # Apply updates
    if updates:
        with engine.begin() as conn:
            for u in updates:
                conn.execute(sa.text("""
                    UPDATE kosztorys_pozycja
                    SET m_jcena = :price, uwagi = COALESCE(uwagi, '') || ' [ICB: ' || :sym || ']'
                    WHERE id = :id
                """), {"price": u["icb_price"], "sym": u["icb_symbol"], "id": u["id"]})

    return {
        "kosztorys_id": body.kosztorys_id,
        "total_positions": len(rows),
        "filled_from_icb": filled,
        "not_found": not_found,
        "regional_coefficient": coeff,
        "quarter": f"{rok}-Q{nr}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /dashboard — agregowany dashboard ICB
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
def icb_dashboard() -> dict:
    """Dashboard z kluczowymi wskaźnikami cenowymi z InterCenBud."""
    engine = get_engine()
    with engine.connect() as conn:
        # Total stats
        stats = conn.execute(sa.text("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT symbol) as symbols,
                   COUNT(DISTINCT category) as categories,
                   MIN(kwartalrok) as from_year,
                   MAX(kwartalrok) as to_year
            FROM icb_ceny_srednie
        """)).fetchone()

        # Latest quarter avg per typ_rms
        latest = conn.execute(sa.text("""
            WITH lq AS (
                SELECT kwartalrok, kwartalnr FROM icb_ceny_srednie
                ORDER BY kwartalrok DESC, kwartalnr DESC LIMIT 1
            )
            SELECT c.typ_rms,
                   ROUND(AVG(c.cena_netto)::numeric, 2) as avg,
                   ROUND(MIN(c.cena_netto)::numeric, 2) as min,
                   ROUND(MAX(c.cena_netto)::numeric, 2) as max,
                   COUNT(*) as n
            FROM icb_ceny_srednie c JOIN lq ON c.kwartalrok=lq.kwartalrok AND c.kwartalnr=lq.kwartalnr
            WHERE c.cena_netto > 0
            GROUP BY c.typ_rms
        """)).fetchall()

        # YoY inflation index
        inflation = conn.execute(sa.text("""
            WITH q1 AS (
                SELECT AVG(cena_netto) as avg1 FROM icb_ceny_srednie
                WHERE kwartalrok=2026 AND kwartalnr=2 AND typ_rms='M' AND cena_netto > 0
            ), q2 AS (
                SELECT AVG(cena_netto) as avg2 FROM icb_ceny_srednie
                WHERE kwartalrok=2025 AND kwartalnr=2 AND typ_rms='M' AND cena_netto > 0
            )
            SELECT ROUND(((q1.avg1 - q2.avg2) / NULLIF(q2.avg2, 0) * 100)::numeric, 2) as yoy_pct
            FROM q1, q2
        """)).scalar()

        # Narzuty summary
        narzuty = conn.execute(sa.text("""
            SELECT nazwa, koszty_posrednie, zysk, koszty_zakupu
            FROM icb_narzuty
            WHERE kwartalrok=2026 AND kwartalnr=2
            ORDER BY nazwa LIMIT 10
        """)).fetchall()

        # Regional spread
        regions = conn.execute(sa.text("""
            SELECT voivodeship, ROUND(AVG(coefficient)::numeric, 4) as avg_coeff
            FROM intercenbud_regional_rates
            WHERE quarter LIKE '2026%'
            GROUP BY voivodeship
            ORDER BY avg_coeff DESC
        """)).fetchall()

    return {
        "overview": {
            "total_records": stats[0],
            "unique_symbols": stats[1],
            "categories": stats[2],
            "data_from": stats[3],
            "data_to": stats[4],
        },
        "latest_quarter_by_type": [
            {"typ_rms": r[0], "avg_price": float(r[1]), "min": float(r[2]),
             "max": float(r[3]), "count": r[4]}
            for r in latest
        ],
        "yoy_inflation_pct": float(inflation) if inflation else None,
        "narzuty": [
            {"branża": r[0], "ko_pct": float(r[1]), "z_pct": float(r[2]), "kz_pct": float(r[3])}
            for r in narzuty
        ],
        "regional_coefficients": [
            {"voivodeship": r[0], "avg_coefficient": float(r[1])}
            for r in regions
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /robocizna/map — stawki robocizny per region
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/robocizna/map")
def robocizna_map() -> dict:
    """Mapa stawek robocizny kosztorysowej per województwo z ICB."""
    from ..intelligence.icb_service import get_latest_quarter

    rok, nr = get_latest_quarter()
    engine = get_engine()

    with engine.connect() as conn:
        # Get avg R rates for latest quarter
        national = conn.execute(sa.text("""
            SELECT ROUND(AVG(cena_netto)::numeric, 2) as avg_r,
                   ROUND(MIN(cena_netto)::numeric, 2) as min_r,
                   ROUND(MAX(cena_netto)::numeric, 2) as max_r
            FROM icb_ceny_srednie
            WHERE typ_rms = 'R' AND kwartalrok = :rok AND kwartalnr = :nr AND cena_netto > 0
        """), {"rok": rok, "nr": nr}).fetchone()

        # Regional coefficients with rate types
        regions = conn.execute(sa.text("""
            SELECT voivodeship, rate_type, coefficient
            FROM intercenbud_regional_rates
            WHERE quarter = :q
            ORDER BY voivodeship, rate_type
        """), {"q": f"{rok}-{nr}"}).fetchall()

    base_rate = float(national[0]) if national and national[0] else 52.0

    # Group by voivodeship
    region_map: dict[str, dict] = {}
    for r in regions:
        voi = r[0]
        if voi not in region_map:
            region_map[voi] = {"voivodeship": voi, "coefficients": {}}
        region_map[voi]["coefficients"][r[1]] = float(r[2])
        if r[1] == "Ogolne":
            region_map[voi]["stawka_r"] = round(base_rate * float(r[2]), 2)

    return {
        "quarter": f"{rok}-Q{nr}",
        "national_avg_r": base_rate,
        "min_r": float(national[1]) if national and national[1] else None,
        "max_r": float(national[2]) if national and national[2] else None,
        "regions": list(region_map.values()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET /volatility-matrix — macierz zmienności cen
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/volatility-matrix")
def volatility_matrix(quarters: int = 8) -> list[dict]:
    """Macierz zmienności (CV) per category × typ_rms za ostatnich N kwartałów."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            WITH recent AS (
                SELECT DISTINCT kwartalrok, kwartalnr
                FROM icb_ceny_srednie
                ORDER BY kwartalrok DESC, kwartalnr DESC
                LIMIT :n
            )
            SELECT c.category, c.typ_rms,
                   ROUND(AVG(c.cena_netto)::numeric, 2) as mean_price,
                   ROUND(STDDEV(c.cena_netto)::numeric, 2) as std_price,
                   ROUND((STDDEV(c.cena_netto) / NULLIF(AVG(c.cena_netto), 0))::numeric, 4) as cv,
                   COUNT(*) as n
            FROM icb_ceny_srednie c
            JOIN recent r ON c.kwartalrok = r.kwartalrok AND c.kwartalnr = r.kwartalnr
            WHERE c.category IS NOT NULL AND c.cena_netto > 0
            GROUP BY c.category, c.typ_rms
            ORDER BY cv DESC NULLS LAST
        """), {"n": quarters}).fetchall()

    return [
        {
            "category": r[0], "typ_rms": r[1],
            "mean_price": float(r[2]) if r[2] else 0,
            "std_price": float(r[3]) if r[3] else 0,
            "cv": float(r[4]) if r[4] else 0,
            "n": r[5],
            "risk_level": "high" if r[4] and float(r[4]) > 0.3 else ("medium" if r[4] and float(r[4]) > 0.15 else "low"),
        }
        for r in rows
    ]
