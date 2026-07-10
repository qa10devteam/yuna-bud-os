"""Terra-OS Intelligence Router — /api/v2/intelligence/*

Endpointy:
  GET  /prices/icb            — wyszukiwanie ICB
  GET  /prices/inflation      — indeks inflacji kosztów budowlanych
  GET  /prices/trend          — trend ceny kategorii/symbolu
  GET  /prices/forecast       — prognoza ceny na N kwartałów
  GET  /prices/index          — zagregowany indeks R/M/S per kwartał
  GET  /material-risk         — Material Risk Score per kategorię
  GET  /narzuty               — narzuty ICB per branżę i kwartał
  GET  /regional              — współczynnik regionalny
  GET  /benchmark             — CPV × region benchmark (market_results)
  POST /anomaly/bid           — anomaly detection dla oferty
  POST /anomaly/kosztorys     — anomaly detection dla kosztorysu (lista pozycji)
  POST /win-probability       — P(win) dla naszej ceny
  GET  /robocizna-rates       — stawki robocizny per województwo
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.deps import AuthUser, get_current_user as _get_current_user

router = APIRouter(prefix="/api/v2/intelligence", tags=["intelligence"])


# ─── Lazy imports (moduły ICB mogą nie być dostępne w testach) ─────────────────

def _icb():
    from ..intelligence.icb_service import (
        search_icb, get_narzuty, get_all_narzuty,
        get_regional_coefficient, get_robocizna_rates,
        get_price_trend, get_latest_quarter, get_categories,
    )
    return {
        "search_icb": search_icb,
        "get_narzuty": get_narzuty,
        "get_all_narzuty": get_all_narzuty,
        "get_regional_coefficient": get_regional_coefficient,
        "get_robocizna_rates": get_robocizna_rates,
        "get_price_trend": get_price_trend,
        "get_latest_quarter": get_latest_quarter,
        "get_categories": get_categories,
    }


def _pi():
    from ..intelligence.price_intelligence import (
        get_inflation_index, get_material_risk_score, get_all_material_risks,
        forecast_price, get_price_index,
    )
    return {
        "get_inflation_index": get_inflation_index,
        "get_material_risk_score": get_material_risk_score,
        "get_all_material_risks": get_all_material_risks,
        "forecast_price": forecast_price,
        "get_price_index": get_price_index,
    }


def _bi():
    from ..intelligence.bid_intelligence import (
        get_cpv_benchmark, detect_bid_anomalies,
        estimate_win_probability, detect_kosztorys_anomalies,
    )
    return {
        "get_cpv_benchmark": get_cpv_benchmark,
        "detect_bid_anomalies": detect_bid_anomalies,
        "estimate_win_probability": estimate_win_probability,
        "detect_kosztorys_anomalies": detect_kosztorys_anomalies,
    }


# ─── Pydantic models ──────────────────────────────────────────────────────────

class BidAnomalyRequest(BaseModel):
    bid_price: float
    estimated_value: float
    cpv_prefix: str = "45"
    province: str | None = None
    n_competitors: int | None = None


class WinProbRequest(BaseModel):
    our_price: float
    estimated_value: float
    cpv_prefix: str = "45"
    province: str | None = None
    n_competitors: int = 4


class KosztorysItem(BaseModel):
    description: str
    unit: str = "szt"
    quantity: float = 1.0
    unit_price: float = 0.0
    category: str = "inne"


class KosztorysAnomalyRequest(BaseModel):
    items: list[KosztorysItem]
    cpv_prefix: str = "45"
    province: str | None = None


# ─── Endpointy ────────────────────────────────────────────────────────────────

@router.get("/prices/icb")
def api_search_icb(
    q: str = Query(..., description="Fraza wyszukiwania (nazwa materiału, robocizny, sprzętu)"),
    typ_rms: str | None = Query(None, description="R, M lub S"),
    category: str | None = Query(None),
    year: int = Query(2026),
    quarter: int = Query(2),
    limit: int = Query(20, le=100),
) -> dict:
    """Wyszukaj pozycje z bazy ICB (784k wierszy, Q1-2008→Q2-2026)."""
    try:
        svc = _icb()
        results = svc["search_icb"](q, typ_rms, year, quarter, category, limit)
        return {
            "query": q,
            "period": f"{year}-Q{quarter}",
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/inflation")
def api_inflation_index(
    category: str | None = Query(None),
    typ_rms: str | None = Query(None),
    quarters: int = Query(8, le=40),
) -> dict:
    """Indeks inflacji kosztów budowlanych z mv_labor_inflation_index."""
    try:
        pi = _pi()
        data = pi["get_inflation_index"](category, typ_rms, quarters)
        return {"data": data, "n": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/trend")
def api_price_trend(
    category: str | None = Query(None),
    symbol: str | None = Query(None),
    typ_rms: str = Query("M"),
    from_year: int = Query(2019),
) -> dict:
    """Trend ceny danej kategorii lub symbolu ICB od from_year."""
    try:
        svc = _icb()
        data = svc["get_price_trend"](symbol, category, typ_rms, from_year)
        return {
            "category": category,
            "symbol": symbol,
            "typ_rms": typ_rms,
            "from_year": from_year,
            "data": data,
            "n": len(data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/forecast")
def api_price_forecast(
    category: str | None = Query(None),
    symbol: str | None = Query(None),
    typ_rms: str = Query("M"),
    horizon: int = Query(4, le=12, description="Liczba kwartałów prognozy"),
) -> dict:
    """Prognoza ceny na kolejne N kwartałów (linear trend / Prophet)."""
    try:
        pi = _pi()
        return pi["forecast_price"](category, symbol, typ_rms, horizon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/index")
def api_price_index(
    quarters: int = Query(8, le=40),
) -> dict:
    """Zagregowany indeks cen R/M/S per kwartał."""
    try:
        pi = _pi()
        data = pi["get_price_index"](quarters)
        return {"data": data, "n": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/material-risk")
def api_material_risk(
    category: str | None = Query(None),
    quarters: int = Query(8, le=20),
) -> dict:
    """Material Risk Score dla kategorii(i) materiałów."""
    try:
        pi = _pi()
        if category:
            result = pi["get_material_risk_score"](category, quarters)
            return result
        else:
            results = pi["get_all_material_risks"](quarters)
            return {"risks": results, "n": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/narzuty")
def api_narzuty(
    branża: str = Query("roboty ogólnobudowlane"),
    year: int = Query(2026),
    quarter: int = Query(2),
    all: bool = Query(False, description="Zwróć wszystkie branże"),
) -> dict:
    """Narzuty ICB: Ko%, Z%, Kz% per branżę i kwartał."""
    try:
        svc = _icb()
        if all:
            data = svc["get_all_narzuty"](year, quarter)
            return {"data": data, "period": f"{year}-Q{quarter}"}
        else:
            return svc["get_narzuty"](year, quarter, branża)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regional")
def api_regional_coefficient(
    voivodeship: str = Query(...),
    rate_type: str = Query("Ogolne"),
    year: int = Query(2026),
    quarter: int = Query(2),
) -> dict:
    """Współczynnik regionalny ICB dla województwa i typu robót."""
    try:
        svc = _icb()
        coeff = svc["get_regional_coefficient"](voivodeship, rate_type, year, quarter)
        return {
            "voivodeship": voivodeship,
            "rate_type": rate_type,
            "period": f"{year}-Q{quarter}",
            "coefficient": coeff,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/robocizna-rates")
def api_robocizna_rates(
    voivodeship: str | None = Query(None),
    year: int = Query(2026),
    quarter: int = Query(2),
) -> dict:
    """Stawki robocizny kosztorysowej [zł/r-g] z korekcją regionalną."""
    try:
        svc = _icb()
        return svc["get_robocizna_rates"](voivodeship, year, quarter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark")
def api_benchmark(
    cpv_prefix: str = Query("45", description="Prefix CPV np. '45', '4523', '45230'"),
    province: str | None = Query(None),
    quarters: int = Query(8),
) -> dict:
    """CPV × region benchmark: rozkład wartości przetargów + win_ratio."""
    try:
        bi = _bi()
        return bi["get_cpv_benchmark"](cpv_prefix, province, quarters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
def api_categories() -> dict:
    """Lista dostępnych kategorii ICB."""
    try:
        svc = _icb()
        return {"categories": svc["get_categories"]()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomaly/bid")
def api_anomaly_bid(req: BidAnomalyRequest) -> dict:
    """Wykrywanie anomalii w cenie oferty przetargowej.

    Metody: z-score vs market_results, PZP Art.224 check, Benford.
    """
    try:
        bi = _bi()
        return bi["detect_bid_anomalies"](
            req.bid_price, req.estimated_value, req.cpv_prefix,
            req.province, req.n_competitors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomaly/kosztorys")
def api_anomaly_kosztorys(req: KosztorysAnomalyRequest) -> dict:
    """Wykrywanie anomalii w kosztorysie (lista pozycji).

    Per-item z-score vs ICB + Isolation Forest (sklearn).
    """
    try:
        bi = _bi()
        items_dicts = [it.model_dump() for it in req.items]
        return bi["detect_kosztorys_anomalies"](items_dicts, req.cpv_prefix, req.province)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/win-probability")
def api_win_probability(req: WinProbRequest) -> dict:
    """Szacuj P(win) dla naszej ceny ofertowej.

    Quantile model z market_results (2504 realnych wyników).
    Zwraca: p_win, sweet_spot, rekomendacja korekty ceny.
    """
    try:
        bi = _bi()
        return bi["estimate_win_probability"](
            req.our_price, req.estimated_value, req.cpv_prefix,
            req.province, req.n_competitors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── S48: ML Win Probability per tender_id ─────────────────────────────────────

from sqlalchemy import text as _sa_text
from terra_db.session import get_engine as _get_engine


@router.get("/win-prob/{tender_id}")
def get_win_prob_ml(tender_id: str, user: AuthUser = Depends(_get_current_user)) -> dict:
    """S48: Probabilistyczna ocena szansy wygranej dla przetargu (ML model)."""
    tenant_id = user.org_id if user else None
    try:
        from ..intelligence.win_prob_ml import predict_win_prob
        engine = _get_engine()
        with engine.connect() as conn:
            prob = predict_win_prob(tender_id, tenant_id, conn)
        return {
            "tender_id": tender_id,
            "win_probability": prob,
            "model": "logistic_regression",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
