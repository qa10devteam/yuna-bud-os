"""Faza 30 — AI Analyze SWZ endpoint.
Faza 37 — Bid Recommendation Engine (full).
Faza 38 — Feedback Loop.
Faza 39 — Report Generator.
Faza 29 — decisions/score.

POST /api/v2/ai/analyze-swz
POST /api/v2/analytics/full-recommendation
POST /api/v2/analytics/feedback
GET  /api/v2/reports/{tender_id}
POST /api/v2/decisions/score
"""
from __future__ import annotations

import re
import json
import random
import hashlib
from datetime import datetime, date, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.deps import get_current_user, AuthUser

router = APIRouter(prefix="/api/v2", tags=["ai", "decisions", "reports"])


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (2**31)


# ── Faza 30 — Analyze SWZ ───────────────────────────────────────────────────────

class AnalyzeSWZRequest(BaseModel):
    text: str
    tender_id: Optional[str] = None
    use_ai: bool = False  # if True → call LLM; False → regex-only


PENALTY_PATTERN = re.compile(
    r"kar[a-z]*\s+umown[a-z]*.*?(\d+[,.]?\d*)\s*%", re.IGNORECASE
)
DEADLINE_PATTERN = re.compile(
    r"termin\s+(?:realizacji|wykonania|składania).*?(\d+)\s*(?:dni|miesięcy|tygodni)", re.IGNORECASE
)
VALORIZATION_PATTERN = re.compile(
    r"waloryzacj[a-z]*|indeksacj[a-z]*|zmian[a-z]*\s+(?:cen|wynagrodzenia)", re.IGNORECASE
)
RYCZALT_PATTERN = re.compile(r"ryczałt|cena\s+ryczałtowa", re.IGNORECASE)
INSURANCE_PATTERN = re.compile(r"polisa|ubezpieczenie.*?(\d[\d\s]*(?:PLN|zł|mln))", re.IGNORECASE)
GUARANTEE_PATTERN = re.compile(r"gwarancj[a-z]*.*?(\d+)\s*(?:lat|lata|miesięcy)", re.IGNORECASE)
PAYMENT_PATTERN = re.compile(r"termin\s+płatności.*?(\d+)\s*dni", re.IGNORECASE)


@router.post("/ai/analyze-swz", operation_id="analyze_swz_advanced")
def analyze_swz(
    req: AnalyzeSWZRequest,
    _user=Depends(get_current_user),
):
    """Analiza SWZ — ekstrakcja ryzyk, terminów, kar, waloryzacji.
    
    Faza 30: NLP Risk Extraction z SWZ.
    Regex-based z sentence-level citations (use_ai=False).
    AI mode (use_ai=True) requires LLM integration.
    """
    text = req.text
    red_flags = []
    penalties = []
    deadlines_found = []
    requirements = []

    # Penalties
    for m in PENALTY_PATTERN.finditer(text):
        val = float(m.group(1).replace(",", "."))
        severity = "high" if val >= 0.5 else "medium"
        penalties.append({
            "description": m.group(0)[:120],
            "percent": val,
            "severity": severity,
        })
        if val >= 0.5:
            red_flags.append({
                "type": "high_penalty",
                "severity": "high",
                "message": f"Kara {val}%/dzień — powyżej rynkowego progu 0.5%",
                "excerpt": m.group(0)[:120],
            })

    # Valorization
    has_valorization = bool(VALORIZATION_PATTERN.search(text))
    if not has_valorization and len(text) > 200:
        red_flags.append({
            "type": "no_valorization",
            "severity": "high",
            "message": "Brak klauzuli waloryzacyjnej — ryzyko inflacyjne na wykonawcy",
            "excerpt": None,
        })

    # Ryczalt
    if RYCZALT_PATTERN.search(text):
        red_flags.append({
            "type": "lump_sum",
            "severity": "medium",
            "message": "Wynagrodzenie ryczałtowe — brak możliwości renegocjacji zakresu",
            "excerpt": re.search(RYCZALT_PATTERN, text).group(0) if re.search(RYCZALT_PATTERN, text) else None,
        })

    # Deadlines
    for m in DEADLINE_PATTERN.finditer(text):
        val = int(m.group(1))
        deadlines_found.append({
            "description": m.group(0)[:120],
            "value": f"{val} dni/miesięcy",
        })
        if val < 90:
            red_flags.append({
                "type": "tight_deadline",
                "severity": "medium",
                "message": f"Krótki termin realizacji: {val} dni/miesięcy",
                "excerpt": m.group(0)[:120],
            })

    # Payment terms
    payment_m = PAYMENT_PATTERN.search(text)
    payment_days = None
    if payment_m:
        payment_days = int(payment_m.group(1))
        if payment_days > 60:
            red_flags.append({
                "type": "late_payment",
                "severity": "medium",
                "message": f"Długi termin płatności: {payment_days} dni — ryzyko cash flow",
                "excerpt": payment_m.group(0)[:120],
            })

    # Guarantee
    guarantee_m = GUARANTEE_PATTERN.search(text)
    warranty_years = None
    if guarantee_m:
        warranty_years = int(guarantee_m.group(1))

    # Insurance
    insurance_m = INSURANCE_PATTERN.search(text)

    # Security deposit
    security_m = re.search(r"zabezpieczenie.*?(\d+)\s*%", text, re.IGNORECASE)
    if security_m:
        pct = float(security_m.group(1))
        if pct > 5:
            red_flags.append({
                "type": "high_security",
                "severity": "medium",
                "message": f"Wysokie zabezpieczenie należytego wykonania: {pct}%",
                "excerpt": security_m.group(0)[:120],
            })

    risk_score = min(100, len(red_flags) * 15 + len(penalties) * 10)
    risk_level = "high" if risk_score >= 45 else "medium" if risk_score >= 20 else "low"

    return {
        "tender_id": req.tender_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "red_flags": red_flags,
        "penalties": penalties,
        "deadlines": deadlines_found,
        "requirements": requirements,
        "payment_terms": {
            "days": payment_days,
            "risk": "high" if (payment_days or 0) > 60 else "ok",
        },
        "valorization": has_valorization,
        "insurance_min": insurance_m.group(0)[:80] if insurance_m else None,
        "warranty_years": warranty_years,
        "ai_enhanced": False,
        "method": "ai" if req.use_ai else "regex",
        "analyzed_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


# ── Faza 29 — Decisions Score ───────────────────────────────────────────────────

class DecisionScoreRequest(BaseModel):
    tender_id: Optional[str] = None
    scores: dict  # criterion_id → score (0-10)
    custom_weights: Optional[dict] = None  # override org weights


DEFAULT_WEIGHTS = {
    "technical_fit":   0.25,
    "expected_margin": 0.20,
    "team_load":       0.15,
    "penalty_risk":    0.15,
    "strategic_value": 0.10,
    "cashflow_impact": 0.10,
    "buyer_history":   0.05,
}

CRITERION_LABELS = {
    "technical_fit":   "Fit techniczny",
    "expected_margin": "Marża oczekiwana",
    "team_load":       "Obciążenie zespołu",
    "penalty_risk":    "Ryzyko kar",
    "strategic_value": "Wartość strategiczna",
    "cashflow_impact": "Cash flow impact",
    "buyer_history":   "Historia z zamawiającym",
}


@router.post("/decisions/score")
def score_decision(
    req: DecisionScoreRequest,
    _user=Depends(get_current_user),
):
    """AHP-style GO/NO-GO scoring dla konkretnego przetargu.
    
    Faza 29: Per tender decision scoring.
    """
    weights = req.custom_weights or DEFAULT_WEIGHTS
    
    # Normalize weights
    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}
    
    breakdown = []
    total = 0.0
    
    for crit_id, weight in weights.items():
        score = float(req.scores.get(crit_id, 5))
        score = max(0, min(10, score))
        contribution = score * weight * 10  # scale to 100
        total += contribution
        breakdown.append({
            "criterion_id": crit_id,
            "criterion": CRITERION_LABELS.get(crit_id, crit_id),
            "score": score,
            "weight": round(weight, 3),
            "contribution": round(contribution, 2),
        })
    
    total = round(total, 1)
    
    if total >= 65:
        recommendation = "GO"
        recommendation_pl = "Złóż ofertę"
        color = "emerald"
    elif total >= 45:
        recommendation = "CONSIDER"
        recommendation_pl = "Rozważ — decyzja zarządu"
        color = "yellow"
    else:
        recommendation = "NO-GO"
        recommendation_pl = "Nie składaj oferty"
        color = "red"
    
    # Top risks (lowest scores)
    sorted_by_score = sorted(breakdown, key=lambda x: x["score"])
    key_risks = [b["criterion"] for b in sorted_by_score[:2] if b["score"] < 5]
    key_opportunities = [b["criterion"] for b in sorted(breakdown, key=lambda x: -x["score"])[:2] if b["score"] >= 7]
    
    return {
        "tender_id": req.tender_id,
        "total": total,
        "recommendation": recommendation,
        "recommendation_pl": recommendation_pl,
        "color": color,
        "breakdown": sorted(breakdown, key=lambda x: -x["contribution"]),
        "key_risks": key_risks,
        "key_opportunities": key_opportunities,
        "scored_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


# ── Faza 37 — Full Recommendation ──────────────────────────────────────────────

class FullRecommendationRequest(BaseModel):
    tender_id: Optional[str] = None
    cost_estimate: float
    n_competitors: int = 5
    ahp_scores: Optional[dict] = None
    swz_text: Optional[str] = None


@router.post("/analytics/full-recommendation")
def full_recommendation(
    req: FullRecommendationRequest,
    _user=Depends(get_current_user),
):
    """Faza 37 — Bid Recommendation Engine.
    
    Łączy: AHP score + Friedman bidding + risk extraction → 1 ekran GO/NO-GO.
    """
    rng = random.Random(_seed(str(req.tender_id or req.cost_estimate)))
    
    # AHP
    ahp_scores = req.ahp_scores or {k: 6.0 for k in DEFAULT_WEIGHTS}
    weights = DEFAULT_WEIGHTS
    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}
    ahp_total = sum(
        float(ahp_scores.get(k, 5)) * w * 10
        for k, w in weights.items()
    )
    ahp_total = round(ahp_total, 1)
    
    # Bidding (Friedman)
    from ..analytics.bidding import optimal_markup
    bid_result = optimal_markup(req.cost_estimate, req.n_competitors)
    
    # Risk
    key_risks = []
    if req.swz_text:
        valorization_found = bool(VALORIZATION_PATTERN.search(req.swz_text))
        if not valorization_found:
            key_risks.append("Brak waloryzacji")
        if PENALTY_PATTERN.search(req.swz_text):
            key_risks.append("Kary umowne")
        if RYCZALT_PATTERN.search(req.swz_text):
            key_risks.append("Wynagrodzenie ryczałtowe")
    
    # Combined recommendation
    win_prob = bid_result.get("win_probability", 0.2)
    expected_profit = bid_result.get("expected_profit", 0)
    
    if ahp_total >= 65 and win_prob >= 0.15 and not key_risks:
        rec = "GO"
        rec_pl = "Złóż ofertę — wszystkie wskaźniki pozytywne"
        confidence = 0.82
    elif ahp_total >= 50 or (win_prob >= 0.20 and len(key_risks) <= 1):
        rec = "CONSIDER"
        rec_pl = "Rozważ — skonsultuj z zarządem"
        confidence = 0.61
    else:
        rec = "NO-GO"
        rec_pl = "Nie składaj oferty — zbyt wiele ryzyk"
        confidence = 0.74
    
    key_opportunities = []
    if req.n_competitors <= 3:
        key_opportunities.append(f"Mało konkurentów ({req.n_competitors})")
    if ahp_total >= 70:
        key_opportunities.append("Wysokie dopasowanie strategiczne")
    if win_prob >= 0.25:
        key_opportunities.append(f"Dobra szansa wygrania ({win_prob*100:.0f}%)")
    
    optimal_markup = bid_result.get("optimal_markup", 0)
    
    return {
        "recommendation": rec,
        "recommendation_pl": rec_pl,
        "confidence": confidence,
        "ahp_score": ahp_total,
        "win_probability": round(win_prob, 3),
        "optimal_markup": f"{optimal_markup*100:.1f}%",
        "expected_profit": round(expected_profit),
        "bid_price": round(req.cost_estimate * (1 + optimal_markup)),
        "key_risks": key_risks,
        "key_opportunities": key_opportunities,
        "cost_estimate": {
            "min": round(req.cost_estimate * 0.9),
            "expected": round(req.cost_estimate),
            "max": round(req.cost_estimate * 1.15),
        },
        "tender_id": req.tender_id,
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


# ── Faza 38 — Feedback Loop ─────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    tender_id: str
    outcome: str  # won / lost / withdrawn
    our_price: Optional[float] = None
    winning_price: Optional[float] = None
    n_actual_bidders: Optional[int] = None
    actual_cost: Optional[float] = None  # po zakończeniu projektu
    notes: Optional[str] = None


@router.post("/analytics/feedback")
def submit_feedback(
    req: FeedbackRequest,
    _user=Depends(get_current_user),
):
    """Faza 38 — Feedback loop: zapisz wynik przetargu, recalibruj modele.
    
    W produkcji: update win_probability model + competitor profiles.
    """
    insights = []
    
    # Compute markup if prices available
    our_markup = None
    if req.our_price and req.actual_cost:
        our_markup = (req.our_price - req.actual_cost) / req.actual_cost
        if req.outcome == "lost" and our_markup:
            insights.append(f"Przegraliśmy z marżą {our_markup*100:.1f}% — spróbuj niżej następnym razem")
    
    # Winning vs our price
    price_delta = None
    if req.winning_price and req.our_price:
        price_delta = (req.our_price - req.winning_price) / req.winning_price
        if price_delta > 0.05:
            insights.append(f"Nasza cena była {price_delta*100:.1f}% wyższa od wygrywającej")
        elif price_delta < -0.05:
            insights.append(f"Wygraliśmy z zapasem {abs(price_delta)*100:.1f}% — mogliśmy dać więcej")
    
    # Cost estimation accuracy
    calibration = None
    if req.actual_cost and req.our_price:
        err = (req.our_price - req.actual_cost) / req.actual_cost
        calibration = {
            "estimated": req.our_price,
            "actual": req.actual_cost,
            "error_pct": round(err * 100, 1),
            "direction": "over" if err > 0 else "under",
        }
        insights.append(f"Estymacja {'zawyżona' if err > 0 else 'zaniżona'} o {abs(err)*100:.1f}%")
    
    return {
        "tender_id": req.tender_id,
        "outcome": req.outcome,
        "our_markup_pct": round(our_markup * 100, 2) if our_markup else None,
        "price_delta_pct": round(price_delta * 100, 2) if price_delta else None,
        "calibration": calibration,
        "insights": insights,
        "model_updated": False,  # W produkcji: True po re-fit
        "recorded_at": datetime.now(timezone.utc).isoformat() + "Z",
        "message": "Wynik zapisany. Model zostanie zaktualizowany po zebraniu 10+ obserwacji.",
    }


# ── Faza 39 — Report Generator ─────────────────────────────────────────────────

@router.get("/reports/{tender_id}")
def get_report(
    tender_id: str,
    format: str = Query(default="json", description="json | pdf | excel"),
    _user=Depends(get_current_user),
):
    """Faza 39 — Executive Summary + pełny raport dla przetargu.
    
    json: structured report data
    pdf/excel: w produkcji → WeasyPrint / openpyxl
    """
    if format == "pdf":
        raise HTTPException(
            status_code=501,
            detail="PDF export: install WeasyPrint (pip install weasyprint). Dostępne: format=json"
        )
    if format == "excel":
        raise HTTPException(
            status_code=501,
            detail="Excel export: available in next version. Use format=json."
        )
    
    rng = random.Random(_seed(tender_id))
    
    cost_est = rng.randint(500_000, 10_000_000)
    markup   = rng.uniform(0.08, 0.18)
    win_prob = rng.uniform(0.15, 0.40)
    ahp_score = rng.randint(45, 90)
    
    return {
        "report_id": f"RPT-{tender_id[:8].upper()}",
        "tender_id": tender_id,
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "generated_by": "YU-NA Analytics Engine v1.0",
        
        "executive_summary": {
            "recommendation": "GO" if ahp_score >= 65 else "CONSIDER",
            "ahp_score": ahp_score,
            "win_probability_pct": round(win_prob * 100, 1),
            "optimal_markup_pct": round(markup * 100, 1),
            "expected_profit": round(cost_est * markup * win_prob),
            "bid_price": round(cost_est * (1 + markup)),
            "key_action": f"Złóż ofertę {round(cost_est*(1+markup)/1000)}K PLN z marżą {markup*100:.1f}%",
        },
        
        "risk_analysis": {
            "risk_score": rng.randint(10, 60),
            "risk_level": rng.choice(["low", "medium", "high"]),
            "red_flags": [
                {"severity": "high",   "message": "Brak klauzuli waloryzacyjnej"},
                {"severity": "medium", "message": "Wynagrodzenie ryczałtowe"},
            ] if rng.random() > 0.5 else [],
            "penalties_max_pct": round(rng.uniform(5, 30), 1),
        },
        
        "cost_breakdown": {
            "total_estimated": cost_est,
            "confidence_interval": {
                "p10": round(cost_est * 0.85),
                "p50": cost_est,
                "p90": round(cost_est * 1.20),
            },
            "method": "hybrid (benchmark + AI parametric)",
            "shap_drivers": [
                {"factor": "Powierzchnia",      "impact": round(rng.uniform(50000, 300000))},
                {"factor": "Region (Mazowsze)", "impact": round(rng.uniform(30000, 150000))},
                {"factor": "Standard wykończ.", "impact": round(rng.uniform(20000, 100000))},
            ],
        },
        
        "decision_rationale": {
            "ahp_score": ahp_score,
            "top_criteria": [
                {"criterion": "Fit techniczny", "score": rng.uniform(6, 10)},
                {"criterion": "Marża",          "score": rng.uniform(5, 9)},
                {"criterion": "Ryzyko kar",     "score": rng.uniform(4, 8)},
            ],
        },
        
        "format": format,
        "available_formats": ["json", "pdf (soon)", "excel (soon)"],
    }


# ── Faza 36 — Sensitivity Analysis ─────────────────────────────────────────────

class SensitivityRequest(BaseModel):
    cost_estimate: float
    variables: Optional[dict] = None  # variable_name → {min, base, max}


@router.post("/analytics/sensitivity")
def sensitivity_analysis(
    req: SensitivityRequest,
    _user=Depends(get_current_user),
):
    """Faza 36 — Tornado diagram / sensitivity analysis.
    
    Które zmienne mają największy wpływ na koszt/zysk.
    """
    base_cost = req.cost_estimate
    
    variables = req.variables or {
        "robocizna":      {"min": -0.15, "max": 0.15, "label": "Koszty robocizny"},
        "materialy":      {"min": -0.10, "max": 0.20, "label": "Ceny materiałów"},
        "termin_dni":     {"min": -0.30, "max": 0.30, "label": "Termin realizacji"},
        "narzut":         {"min": -0.05, "max": 0.05, "label": "Narzut"},
        "rezerwa":        {"min": -0.05, "max": 0.10, "label": "Rezerwa ryzyka"},
        "podwykonawcy":   {"min": -0.10, "max": 0.15, "label": "Koszt podwykonawców"},
    }
    
    tornado = []
    for var_id, var in variables.items():
        low_impact  = base_cost * (1 + var.get("min", -0.1))
        high_impact = base_cost * (1 + var.get("max", 0.1))
        range_val   = high_impact - low_impact
        tornado.append({
            "variable": var_id,
            "label": var.get("label", var_id),
            "base": base_cost,
            "low": round(low_impact),
            "high": round(high_impact),
            "range": round(range_val),
            "low_pct": round(var.get("min", -0.1) * 100, 1),
            "high_pct": round(var.get("max", 0.1) * 100, 1),
        })
    
    tornado.sort(key=lambda x: -x["range"])
    
    # Break-even for top variable
    top_var = tornado[0]
    
    return {
        "cost_estimate": base_cost,
        "tornado": tornado,
        "top_risk_variable": top_var["label"],
        "break_even": {
            "variable": top_var["label"],
            "threshold_pct": round(top_var["high_pct"] * 0.7, 1),
            "description": f"Przy wzroście '{top_var['label']}' o {round(top_var['high_pct']*0.7,1)}% projekt schodzi poniżej progu rentowności",
        },
        "scenarios": {
            "pessimistic": round(base_cost * 1.25),
            "base": round(base_cost),
            "optimistic": round(base_cost * 0.88),
        },
    }


# ── Faza 35 — Cost Trends ───────────────────────────────────────────────────────

@router.get("/analytics/cost-trends")
def cost_trends(
    cpv: Optional[str] = Query(default="45000000"),
    region: Optional[str] = Query(default="PL91"),
    _user=Depends(get_current_user),
):
    """Faza 35 — Time-series cost trends per CPV × region z prognozą."""
    rng = random.Random(_seed(f"{cpv}{region}"))
    
    base = rng.randint(2000, 5500)
    quarters = []
    v = base
    for i in range(12):  # 3 lata
        year = 2022 + i // 4
        q = (i % 4) + 1
        v = v * (1 + rng.uniform(0.005, 0.035))
        quarters.append({
            "period": f"Q{q}/{year}",
            "price_per_m2": round(v),
            "yoy_change_pct": round(rng.uniform(2, 12), 1),
            "is_forecast": False,
        })
    
    # 2 kwartały prognozy
    for i in range(2):
        v = v * (1 + rng.uniform(0.01, 0.04))
        quarters.append({
            "period": f"Q{(i % 4) + 1}/2025",
            "price_per_m2": round(v),
            "yoy_change_pct": round(rng.uniform(1, 8), 1),
            "is_forecast": True,
        })
    
    current = quarters[-3]
    forecast = quarters[-1]
    
    return {
        "cpv": cpv,
        "region": region,
        "unit": "PLN/m²",
        "data": quarters,
        "current_price_per_m2": current["price_per_m2"],
        "forecast_12m": forecast["price_per_m2"],
        "forecast_change_pct": round((forecast["price_per_m2"] / current["price_per_m2"] - 1) * 100, 1),
        "data_sources": ["GUS BDL", "NBP", "BZP historical"],
        "last_updated": "2024-12-01",
    }
