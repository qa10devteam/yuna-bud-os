"""Analytics router — Fazy 28-37, 40.

Endpoints: /api/v2/analytics/*, /api/v2/ai/analyze-swz
"""
from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from terra_db.session import get_engine
from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/analytics", tags=["analytics"])
ai_router = APIRouter(prefix="/api/v2/ai", tags=["ai"])


# ─── Request/Response schemas ──────────────────────────────────────────────

class OptimalMarkupRequest(BaseModel):
    cost_estimate: float
    n_competitors: int
    cpv: str = ""
    region: str = ""
    historical_win_rates: list[dict] | None = None


class AHPScoreRequest(BaseModel):
    tender_id: str | None = None
    scores: dict[str, float]
    custom_criteria: list[dict] | None = None


class RecommendationRequest(BaseModel):
    tender_id: str | None = None
    cost_estimate: float
    n_competitors: int
    ahp_scores: dict[str, float] | None = None
    cpv: str = ""
    region: str = ""
    area_m2: float | None = None


class CostEstimateRequest(BaseModel):
    tender_id: str | None = None
    cpv: str
    region: str = ""
    area_m2: float | None = None
    value_estimated: float | None = None
    description: str = ""


class AnalyzeSWZRequest(BaseModel):
    tender_id: str | None = None
    text: str
    use_ai: bool = True


class WinProbabilityRequest(BaseModel):
    markup_pct: float
    n_competitors: int
    cpv: str = ""


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/optimal-markup")
def calc_optimal_markup(body: OptimalMarkupRequest, current_user: AuthUser):
    """Faza 28 — Friedman/Gates optimal bidding model."""
    from ..analytics import optimal_markup
    return optimal_markup(
        cost_estimate=body.cost_estimate,
        n_competitors=body.n_competitors,
        historical_win_rates=body.historical_win_rates,
    )


@router.post("/ahp-score")
def calc_ahp_score(body: AHPScoreRequest, current_user: AuthUser):
    """Faza 29 — AHP decision support."""
    from ..analytics import compute_ahp_score
    return compute_ahp_score(
        scores=body.scores,
        criteria=body.custom_criteria,
    )


@router.get("/ahp-criteria")
def get_ahp_criteria(current_user: AuthUser):
    """Get default AHP criteria list."""
    from ..analytics import DEFAULT_CRITERIA
    return {"criteria": DEFAULT_CRITERIA}


@router.post("/cost-estimate")
def calc_cost_estimate(body: CostEstimateRequest, current_user: AuthUser):
    """Faza 31 — Hybrid cost estimation with confidence intervals."""
    from ..analytics import estimate_cost, explain_cost_drivers
    result = estimate_cost(
        cpv=body.cpv,
        region=body.region,
        area_m2=body.area_m2,
        value_estimated=body.value_estimated,
        description=body.description,
    )
    if "error" not in result and result.get("expected_estimate"):
        result["cost_drivers"] = explain_cost_drivers(
            estimate=result["expected_estimate"],
            cpv=body.cpv,
            region=body.region,
            area_m2=body.area_m2,
            description=body.description,
        )
    return result


@router.get("/cost-estimate")
def get_cost_estimate_via_query(
    cpv: str = "",
    nuts: str = "",
    value: float = 0.0,
    region: str = "",
    area_m2: float = 0.0,
    description: str = "",
):
    """GET convenience wrapper for cost-estimate — accepts query params, no auth required."""
    from ..analytics import estimate_cost
    # Map NUTS code to region name if region not explicitly provided
    _region = region or nuts or "mazowieckie"
    result = estimate_cost(
        cpv=cpv,
        region=_region,
        area_m2=area_m2,
        value_estimated=value,
        description=description,
    )
    return result


@router.get("/win-probability")
def calc_win_probability(
    current_user: AuthUser,
    markup: float,
    n_competitors: int,
    cpv: str = "",
):
    """Faza 34 — Win probability at a given markup."""
    from ..analytics import estimate_win_probability
    return estimate_win_probability(
        markup_pct=markup,
        n_competitors=n_competitors,
        cpv=cpv,
    )


@router.post("/recommendation")
def get_recommendation(body: RecommendationRequest, current_user: AuthUser):
    """Faza 37 — Full bid recommendation engine (GO/NO-GO)."""
    from ..analytics import generate_recommendation

    red_flags: list[dict] = []
    if body.tender_id:
        try:
            engine = get_engine()
            with engine.connect() as conn:
                risks = conn.execute(
                    text("""
                        SELECT kind, severity, message FROM discrepancy
                        WHERE tender_id = :tid ORDER BY severity
                    """),
                    {"tid": body.tender_id},
                ).fetchall()
                red_flags = [{"message": r.message, "severity": r.severity} for r in risks]
        except Exception:
            logger.warning(
                "Could not fetch red_flags for tender_id=%s", body.tender_id, exc_info=True
            )

    return generate_recommendation(
        cost_estimate=body.cost_estimate,
        n_competitors=body.n_competitors,
        ahp_scores=body.ahp_scores,
        red_flags=red_flags,
        cpv=body.cpv,
        region=body.region,
        area_m2=body.area_m2,
    )


@router.get("/dashboard")
def get_analytics_dashboard(current_user: AuthUser):
    """Faza 40 — Analytics dashboard KPIs (tenant-scoped)."""
    org_id = current_user.org_id
    if not org_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )

    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Pipeline value (sum of value_pln for active tenders scoped to tenant)
            pipeline_stats = conn.execute(
                text("""
                    SELECT
                        COUNT(*) AS active_bids,
                        COALESCE(SUM(CAST(t.value_pln AS NUMERIC)), 0) AS pipeline_value
                    FROM tender t
                    WHERE t.tenant_id = :tid
                      AND t.status NOT IN ('archived', 'decided_nogo')
                """),
                {"tid": org_id},
            ).fetchone()

            # Win rate (decided_go / total decided) — tenant-scoped
            decision_stats = conn.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'decided_go')  AS won,
                        COUNT(*) FILTER (WHERE status IN ('decided_go', 'decided_nogo')) AS total
                    FROM tender
                    WHERE tenant_id = :tid
                """),
                {"tid": org_id},
            ).fetchone()

            # Pipeline funnel — tenant-scoped
            funnel = conn.execute(
                text("""
                    SELECT status, COUNT(*) AS count
                    FROM tender
                    WHERE tenant_id = :tid
                    GROUP BY status
                    ORDER BY count DESC
                """),
                {"tid": org_id},
            ).fetchall()

        win_rate = 0.0
        if decision_stats and decision_stats.total > 0:
            win_rate = round(decision_stats.won / decision_stats.total * 100, 1)

        return {
            "pipeline_value": float(pipeline_stats.pipeline_value) if pipeline_stats else 0.0,
            "active_bids": int(pipeline_stats.active_bids) if pipeline_stats else 0,
            "win_rate_pct": win_rate,
            "avg_margin_pct": 12.5,  # placeholder until historical_bids table is populated
            "funnel": [{"status": r.status, "count": r.count} for r in funnel],
        }
    except Exception as exc:
        logger.error("analytics/dashboard failed for org_id=%s: %s", org_id, exc, exc_info=True)
        return {
            "pipeline_value": 0.0,
            "active_bids": 0,
            "win_rate_pct": 0.0,
            "avg_margin_pct": 0.0,
            "funnel": [],
            "error": str(exc),
        }


@router.get("/market-overview")
def get_market_overview():
    """Market overview — aggregate tender statistics. No auth required."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Detect the most recent year with data
            year_row = conn.execute(text("""
                SELECT COALESCE(MAX(EXTRACT(YEAR FROM published_at)), MAX(EXTRACT(YEAR FROM created_at)), 2024)::int
                FROM tender
            """)).scalar()
            data_year = int(year_row) if year_row else 2024

            # Total tenders + value
            totals = conn.execute(text("""
                SELECT COUNT(*) AS total_tenders,
                       COALESCE(SUM(value_pln), 0) AS total_value_pln
                FROM tender
                WHERE EXTRACT(YEAR FROM published_at) = :yr
                   OR (published_at IS NULL AND EXTRACT(YEAR FROM created_at) = :yr)
            """), {"yr": data_year}).fetchone()

            # Top CPV codes (cpv is an array; unnest it)
            top_cpv = conn.execute(text("""
                SELECT unnest(cpv) AS cpv_code, COUNT(*) AS cnt
                FROM tender
                WHERE cpv IS NOT NULL AND array_length(cpv, 1) > 0
                  AND (EXTRACT(YEAR FROM published_at) = :yr
                       OR (published_at IS NULL AND EXTRACT(YEAR FROM created_at) = :yr))
                GROUP BY cpv_code
                ORDER BY cnt DESC
                LIMIT 5
            """), {"yr": data_year}).fetchall()

            # Top regions
            top_regions = conn.execute(text("""
                SELECT voivodeship, COUNT(*) AS cnt
                FROM tender
                WHERE voivodeship IS NOT NULL AND voivodeship <> ''
                  AND (EXTRACT(YEAR FROM published_at) = :yr
                       OR (published_at IS NULL AND EXTRACT(YEAR FROM created_at) = :yr))
                GROUP BY voivodeship
                ORDER BY cnt DESC
                LIMIT 5
            """), {"yr": data_year}).fetchall()

        total_tenders = int(totals[0]) if totals else 0
        total_value = float(totals[1]) if totals else 0.0
        avg_per_tender = round(total_value / total_tenders, 2) if total_tenders > 0 else 0.0

        return {
            "total_tenders": total_tenders,
            "total_value_pln": total_value,
            "avg_per_tender": avg_per_tender,
            "top_cpv": [{"cpv": r[0], "count": r[1]} for r in top_cpv],
            "top_regions": [{"region": r[0], "count": r[1]} for r in top_regions],
            "period": str(data_year),
        }
    except Exception as exc:
        logger.warning("market-overview error: %s", exc, exc_info=True)
        return {
            "total_tenders": 0,
            "total_value_pln": 0.0,
            "avg_per_tender": 0.0,
            "top_cpv": [],
            "top_regions": [],
            "period": "2024",
            "error": str(exc),
        }


@router.get("/pipeline-funnel")
def get_pipeline_funnel(current_user: AuthUser):
    """Pipeline funnel — count per status (tenant-scoped)."""
    org_id = current_user.org_id
    if not org_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT status, COUNT(*) AS count
                FROM tender
                WHERE tenant_id = :tid
                GROUP BY status
            """),
            {"tid": org_id},
        ).fetchall()
    return {"funnel": [{"status": r.status, "count": r.count} for r in rows]}


# ─── AI router — SWZ analysis ─────────────────────────────────────────────

@ai_router.post("/analyze-swz")
async def analyze_swz(body: AnalyzeSWZRequest, current_user: AuthUser):
    """Faza 30 — NLP risk extraction from SWZ document text."""
    from ..analytics import extract_risks_with_ai, extract_risks_from_text

    if body.use_ai:
        result = await extract_risks_with_ai(body.text)
    else:
        result = extract_risks_from_text(body.text)

    # Persist red flags to discrepancy table when tender_id is provided
    if body.tender_id and result.get("red_flags"):
        try:
            engine = get_engine()
            severity_map = {"high": "block", "medium": "warn", "low": "info"}
            with engine.connect() as conn:
                for flag in result["red_flags"][:10]:
                    conn.execute(
                        text("""
                            INSERT INTO discrepancy (tenant_id, tender_id, kind, severity, message, provenance)
                            SELECT t.tenant_id, :tid, 'swz_risk', :sev, :msg, :prov::jsonb
                            FROM tender t WHERE t.id = :tid
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "tid": body.tender_id,
                            "sev": severity_map.get(flag.get("severity", "low"), "info"),
                            "msg": flag["message"],
                            "prov": '{"source": "ai_analysis"}',
                        },
                    )
                conn.commit()
        except Exception:
            # Non-fatal: log but don't fail the response
            logger.warning(
                "Failed to persist SWZ red_flags for tender_id=%s", body.tender_id, exc_info=True
            )

    return result
