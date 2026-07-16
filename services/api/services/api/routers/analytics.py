"""Faza 40 — Analytics Dashboard router.

KPIs, pipeline funnel, win-rate trend.
"""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser
from ..analytics.ahp import compute_ahp_score
from ..analytics.bidding import optimal_markup as calc_optimal_markup
from ..analytics.recommendation import generate_recommendation
from ..cache import api_cache, invalidate
from ..redis_cache import rcache_get, rcache_set, TTL_ANALYTICS_DASHBOARD

router = APIRouter(prefix="/api/v2/analytics", tags=["analytics"])


@router.post("/cache/invalidate")
def invalidate_analytics_cache(user: AuthUser) -> dict:
    """Inwaliduje cache analityki dla tenanta."""
    prefix = f"analytics:{user.org_id}"
    count = invalidate(prefix)
    return {"ok": True, "invalidated": count}


@router.get("/dashboard")
def analytics_dashboard(user: AuthUser) -> dict:
    """KPIs: pipeline_value, win_rate, active_bids, avg_margin. Cache TTL=120s (Redis) / 60s (in-process)."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    cache_key = f"analytics:{user.org_id}:dashboard"

    # Try Redis first (2min TTL), then in-process
    cached = rcache_get(cache_key)
    if cached is not None:
        return {**cached, "_cached": True}

    engine = get_engine()
    tenant_id = user.org_id

    with engine.connect() as conn:
        # Pipeline value (wszystkie aktywne przetargi)
        pipeline = conn.execute(
            sa.text(
                """SELECT
                     COALESCE(SUM(value_pln), 0) AS pipeline_value,
                     COUNT(*) AS active_bids
                   FROM tender
                   WHERE tenant_id = :tid
                     AND status NOT IN ('archived', 'decided_nogo')"""
            ),
            {"tid": tenant_id},
        ).fetchone()

        # Win rate: count decided_go vs decided_nogo in tender table
        # FIX: approval_request.payload has no 'org_id' key; use tender table with tenant_id
        decisions = conn.execute(
            sa.text(
                """SELECT
                     COUNT(*) FILTER (WHERE status = 'decided_go') AS won,
                     COUNT(*) FILTER (WHERE status = 'decided_nogo') AS lost,
                     COUNT(*) FILTER (WHERE status IN ('decided_go','decided_nogo')) AS total
                   FROM tender
                   WHERE tenant_id = :tid"""
            ),
            {"tid": tenant_id},
        ).fetchone()

        # Avg margin z wycen
        avg_margin = conn.execute(
            sa.text(
                """SELECT AVG(profit_pct) AS avg_margin
                   FROM estimate
                   WHERE tenant_id = :tid AND profit_pct IS NOT NULL"""
            ),
            {"tid": tenant_id},
        ).fetchone()

    win_rate = 0.0
    if decisions and decisions.total > 0:
        win_rate = float(decisions.won) / float(decisions.total)

    result = {
        "pipeline_value": float(pipeline.pipeline_value) if pipeline else 0.0,
        "active_bids": int(pipeline.active_bids) if pipeline else 0,
        "win_rate": round(win_rate, 4),
        "win_rate_pct": round(win_rate * 100, 1),
        "total_won": int(decisions.won) if decisions else 0,
        "total_lost": int(decisions.lost) if decisions else 0,
        "avg_margin": round(float(avg_margin.avg_margin), 2) if avg_margin and avg_margin.avg_margin else None,
    }
    # Cache in Redis (2min) + in-process (60s fallback)
    rcache_set(cache_key, result, ttl=TTL_ANALYTICS_DASHBOARD)
    return result


@router.get("/pipeline-funnel")
def pipeline_funnel(user: AuthUser) -> dict:
    """Ilości przetargów per status (lejek sprzedażowy). Cache TTL=30s."""
    if not user.org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    cache_key = f"analytics:{user.org_id}:funnel"
    from ..cache import get as cache_get, set as cache_set
    cached = cache_get(cache_key)
    if cached is not None:
        return {**cached, "_cached": True}

    engine = get_engine()
    tenant_id = user.org_id

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """SELECT status, COUNT(*) AS cnt
                   FROM tender
                   WHERE tenant_id = :tid
                   GROUP BY status
                   ORDER BY cnt DESC"""
            ),
            {"tid": tenant_id},
        ).fetchall()

    STATUS_ORDER = [
        "new", "matched", "watching", "analyzing", "estimated",
        "decided_go", "decided_nogo", "archived",
    ]
    counts = {r.status: int(r.cnt) for r in rows}

    result = {
        "funnel": [
            {"status": s, "count": counts.get(s, 0)}
            for s in STATUS_ORDER
        ],
        "total": sum(counts.values()),
    }
    cache_set(cache_key, result, ttl=30)
    return result


@router.get("/win-rate-trend")
def win_rate_trend(user: AuthUser, months: int = Query(6, ge=1, le=24)) -> dict:
    """Win rate per miesiąc (ostatnie N miesięcy)."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    """SELECT
                         TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') AS month,
                         COUNT(*) FILTER (WHERE status IN ('decided_go')) AS won,
                         COUNT(*) FILTER (WHERE status IN ('decided_nogo', 'archived')) AS lost,
                         COUNT(*) AS total
                       FROM tender
                       WHERE tenant_id = :tid
                         AND created_at >= NOW() - (:months || ' months')::interval
                       GROUP BY DATE_TRUNC('month', created_at)
                       ORDER BY month ASC"""
                ),
                {"tid": tenant_id, "months": months},
            ).fetchall()
    except Exception:
        rows = []

    return {
        "trend": [
            {
                "month": r.month,
                "won": int(r.won),
                "lost": int(r.lost),
                "total": int(r.total),
                "win_rate": round(float(r.won) / float(r.total), 4) if r.total > 0 else 0.0,
            }
            for r in rows
        ],
        "months": months,
    }


@router.get("/win-probability")
def win_probability_endpoint(
    user: AuthUser,
    markup: float = Query(..., description="Narzut jako decimal (np. 0.12 = 12%)"),
    cpv: str = Query("45", description="CPV prefix"),
    n_competitors: int = Query(4, ge=1, le=20),
) -> dict:
    """Prawdopodobieństwo wygrania dla danego narzutu."""
    from ..analytics.win_probability import get_win_model

    model = get_win_model()
    result = model.predict(markup, n_competitors, cpv)
    curve = model.predict_curve(n_competitors, cpv)

    return {
        **result,
        "curve": curve[::5],  # Co 5ty punkt
    }


class AHPRequest(BaseModel):
    scores: dict[str, float]
    criteria: list[dict] | None = None


@router.post("/ahp")
def ahp_score_endpoint(body: AHPRequest, user: AuthUser) -> dict:
    """Oblicz wynik AHP."""
    return compute_ahp_score(body.scores, body.criteria)


class BiddingRequest(BaseModel):
    cost_estimate: float
    n_competitors: int = 4
    historical_win_rates: list[dict] | None = None


@router.post("/bidding")
def bidding_endpoint(body: BiddingRequest, user: AuthUser) -> dict:
    """Optymalny narzut wg modelu Friedmana."""
    return calc_optimal_markup(body.cost_estimate, body.n_competitors, body.historical_win_rates)


class RecommendationRequest(BaseModel):
    scores: dict[str, float] | None = None
    cost_estimate: float | None = None
    n_competitors: int = 4
    historical_win_rates: list[dict] | None = None
    swz_text: str = ""


@router.post("/recommendation/{tender_id}")
def recommendation_endpoint(tender_id: str, body: RecommendationRequest, user: AuthUser) -> dict:
    """Pełna rekomendacja ofertowa dla przetargu."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    with engine.connect() as conn:
        tender = conn.execute(
            sa.text(
                "SELECT id, title, value_pln, status FROM tender WHERE id = :id AND tenant_id = :tid"
            ),
            {"id": tender_id, "tid": tenant_id},
        ).fetchone()

    if not tender:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Przetarg nie znaleziony"})

    tender_data = {
        "id": str(tender.id),
        "title": tender.title,
        "value_pln": float(tender.value_pln) if tender.value_pln else None,
        "status": tender.status,
    }

    result = generate_recommendation(
        tender_data=tender_data,
        scores=body.scores,
        cost_estimate=body.cost_estimate,
        n_competitors=body.n_competitors,
        historical_win_rates=body.historical_win_rates,
        swz_text=body.swz_text,
    )

    return result


class RiskRequest(BaseModel):
    text: str
    use_ai: bool = False


@router.post("/risk-extract")
def risk_extract(body: RiskRequest, user: AuthUser) -> dict:
    """Wyciągnij ryzyka z tekstu SWZ."""
    from ..analytics.risk_extractor import extract_risks_from_text, extract_risks_with_ai

    if body.use_ai:
        return extract_risks_with_ai(body.text)
    return extract_risks_from_text(body.text)
