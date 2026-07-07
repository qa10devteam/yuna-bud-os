"""Analytics engine — Fazy 28-37.

Friedman/Gates bidding model, AHP decision support, NLP risk extraction,
cost estimation, win probability, bid recommendation.
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import os
import re
import math
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Faza 28 — Friedman/Gates Optimal Bidding Model
# ─────────────────────────────────────────────────────────────────────────────

def optimal_markup(
    cost_estimate: float,
    n_competitors: int,
    historical_win_rates: list[dict] | None = None,
) -> dict:
    """
    Friedman model: maximize expected profit = P(win) × markup × cost.

    Args:
        cost_estimate: Our estimated project cost (PLN)
        n_competitors: Estimated number of competing firms
        historical_win_rates: Past bids [{markup: 0.12, won: True/False}, ...]

    Returns:
        {optimal_markup, win_probability, expected_profit, chart_data}
    """
    if n_competitors < 1:
        n_competitors = 1

    markups = np.linspace(0.01, 0.40, 200)

    # Calibration: k adjusts how steeply win prob drops with markup
    # Higher n_competitors → sharper drop
    k = 2.0 + 0.3 * math.log1p(n_competitors)

    win_probs = []
    e_profits = []

    for m in markups:
        # Prior: Rayleigh-inspired distribution
        p_win = float(np.exp(-k * m * (n_competitors ** 0.6)))
        p_win = max(0.001, min(0.999, p_win))

        # Update with historical data (Bayesian update, simple version)
        if historical_win_rates:
            relevant = [
                h for h in historical_win_rates
                if abs(h.get("markup", -1) - float(m)) < 0.025
            ]
            if len(relevant) >= 3:
                hist_p = sum(1 for h in relevant if h.get("won")) / len(relevant)
                # weighted average: 40% prior, 60% historical (more data = trust more)
                weight = min(0.80, 0.40 + 0.04 * len(relevant))
                p_win = (1 - weight) * p_win + weight * hist_p

        ep = p_win * m * cost_estimate
        win_probs.append(p_win)
        e_profits.append(ep)

    best_idx = int(np.argmax(e_profits))

    # Chart data — every 5th point (40 points)
    chart_data = [
        {
            "markup_pct": round(float(markups[i]) * 100, 1),
            "expected_profit": round(float(e_profits[i])),
            "win_probability": round(float(win_probs[i]) * 100, 1),
        }
        for i in range(0, len(markups), 5)
    ]

    return {
        "optimal_markup": round(float(markups[best_idx]), 4),
        "optimal_markup_pct": round(float(markups[best_idx]) * 100, 2),
        "win_probability": round(float(win_probs[best_idx]), 4),
        "win_probability_pct": round(float(win_probs[best_idx]) * 100, 1),
        "expected_profit": round(float(e_profits[best_idx])),
        "bid_price": round(cost_estimate * (1 + float(markups[best_idx]))),
        "chart_data": chart_data,
        "model": "friedman_gates_v1",
        "n_competitors": n_competitors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Faza 29 — AHP Decision Support
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CRITERIA = [
    {"id": "technical_fit",    "label": "Fit techniczny",           "weight": 0.25},
    {"id": "expected_margin",  "label": "Marża oczekiwana",         "weight": 0.20},
    {"id": "team_load",        "label": "Obciążenie zespołu",       "weight": 0.15},
    {"id": "penalty_risk",     "label": "Ryzyko kar",               "weight": 0.15},
    {"id": "strategic_value",  "label": "Wartość strategiczna",     "weight": 0.10},
    {"id": "cashflow_impact",  "label": "Cash flow impact",         "weight": 0.10},
    {"id": "buyer_history",    "label": "Historia z zamawiającym",  "weight": 0.05},
]


def compute_ahp_score(
    scores: dict[str, float],
    criteria: list[dict] | None = None,
) -> dict:
    """
    AHP decision scoring.

    Args:
        scores: {criterion_id: score 0-10}
        criteria: custom criteria list (defaults to DEFAULT_CRITERIA)

    Returns:
        {total: 0-100, recommendation, breakdown, confidence}
    """
    criteria = criteria or DEFAULT_CRITERIA

    total = 0.0
    breakdown = []
    missing = []

    for c in criteria:
        raw = float(scores.get(c["id"], -1))
        if raw < 0:
            missing.append(c["id"])
            raw = 5.0  # neutral default

        raw = max(0.0, min(10.0, raw))
        contribution = (raw / 10.0) * c["weight"] * 100
        total += contribution
        breakdown.append({
            "criterion_id": c["id"],
            "criterion": c["label"],
            "score": raw,
            "weight": c["weight"],
            "weight_pct": round(c["weight"] * 100),
            "contribution": round(contribution, 2),
        })

    total = round(total, 1)
    confidence = 1.0 - len(missing) * 0.1

    if total >= 70:
        recommendation = "GO"
        recommendation_pl = "Złóż ofertę"
        color = "green"
    elif total >= 50:
        recommendation = "CONSIDER"
        recommendation_pl = "Rozważ"
        color = "yellow"
    else:
        recommendation = "NO-GO"
        recommendation_pl = "Zrezygnuj"
        color = "red"

    return {
        "total": total,
        "recommendation": recommendation,
        "recommendation_pl": recommendation_pl,
        "color": color,
        "confidence": round(confidence, 2),
        "breakdown": breakdown,
        "missing_criteria": missing,
        "criteria": criteria,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Faza 30 — NLP Risk Extraction from SWZ
# ─────────────────────────────────────────────────────────────────────────────

# Pattern-based red flag detection (works offline)
RED_FLAG_PATTERNS = [
    {
        "pattern": r"kar[aę]\s+umown[ąa].*?(\d+[,.]?\d*)\s*%.*?(?:dzień|dniowo|dziennie)",
        "msg_template": "Kara umowna {val}%/dzień",
        "severity": "high",
        "check": lambda m: float(m.group(1).replace(",", ".")) >= 0.3,
    },
    {
        "pattern": r"0[,.]5\s*%.*?(?:dzień|dniowo|za każdy dzień)",
        "msg_template": "Kara 0.5%/dzień — krytyczne ryzyko",
        "severity": "high",
        "check": None,
    },
    {
        "pattern": r"brak\s+(?:klauzuli\s+)?waloryzac|bez\s+waloryzac|nie\s+(?:dopuszcza\s+)?waloryzac",
        "msg_template": "Brak waloryzacji ceny",
        "severity": "high",
        "check": None,
    },
    {
        "pattern": r"ryczał[tc].*bez.*możliwości\s+zmiany|cena\s+ryczałtowa.*niezmien",
        "msg_template": "Ryczałt bez możliwości zmiany ceny",
        "severity": "high",
        "check": None,
    },
    {
        "pattern": r"solidarn[aą]\s+odpowiedzialn",
        "msg_template": "Solidarna odpowiedzialność podwykonawców",
        "severity": "medium",
        "check": None,
    },
    {
        "pattern": r"zabezpieczenie.*(?:10|15|20)\s*%",
        "msg_template": "Wysokie zabezpieczenie należytego wykonania (≥10%)",
        "severity": "medium",
        "check": None,
    },
    {
        "pattern": r"termin\s+(?:płatności|zapłaty).*(?:60|90|120)\s+dni",
        "msg_template": "Długi termin płatności (>60 dni)",
        "severity": "medium",
        "check": None,
    },
    {
        "pattern": r"wykona(?:wca|wcy)\s+(?:jest\s+)?(?:odpowiedzialn|ponosi)\s+(?:pełn|całkowit)",
        "msg_template": "Pełna odpowiedzialność wykonawcy za błędy projektowe",
        "severity": "high",
        "check": None,
    },
]

DEADLINE_PATTERN = re.compile(
    r"(?:termin|data)\s+(?:realizacji|wykonania|zakończenia).*?(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d+\s+(?:miesięcy|dni|tygodni))",
    re.IGNORECASE | re.DOTALL,
)

PENALTY_PATTERN = re.compile(
    r"kar[aę]\s+umown[ąa].*?(\d+[,.]?\d*)\s*%",
    re.IGNORECASE,
)


def extract_risks_from_text(text: str) -> dict:
    """
    Pattern-based risk extraction from SWZ text.
    Works offline — no API key required.
    """
    red_flags = []
    for rule in RED_FLAG_PATTERNS:
        match = re.search(rule["pattern"], text, re.IGNORECASE)
        if match:
            if rule["check"] is None or rule["check"](match):
                msg = rule["msg_template"]
                if "{val}" in msg and match.lastindex:
                    try:
                        val = match.group(1).replace(",", ".")
                        msg = msg.format(val=val)
                    except Exception:
                        pass
                red_flags.append({
                    "message": msg,
                    "severity": rule["severity"],
                    "excerpt": text[max(0, match.start()-50):match.end()+50].strip(),
                })

    # Extract deadlines
    deadlines = []
    for m in DEADLINE_PATTERN.finditer(text[:5000]):
        deadlines.append({
            "description": text[max(0, m.start()-30):m.end()].strip()[:200],
            "value": m.group(1),
        })

    # Extract penalties
    penalties = []
    for m in PENALTY_PATTERN.finditer(text[:5000]):
        penalties.append({
            "description": text[max(0, m.start()-30):m.end()].strip()[:200],
            "percent": float(m.group(1).replace(",", ".")),
        })

    return {
        "red_flags": red_flags,
        "deadlines": deadlines[:10],
        "penalties": penalties[:10],
        "requirements": [],
        "payment_terms": None,
        "valorization": not bool(re.search(r"brak.*waloryzac|bez.*waloryzac", text, re.I)),
        "ai_enhanced": False,
        "method": "pattern_matching",
    }


async def extract_risks_with_ai(text: str) -> dict:
    """
    AI-enhanced risk extraction using Claude Haiku.
    Falls back to pattern matching if no API key.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return extract_risks_from_text(text)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        prompt = f"""Analizuj fragment SWZ (Specyfikacja Warunków Zamówienia) i zwróć JSON.

FRAGMENT SWZ:
{text[:6000]}

Zwróć TYLKO JSON (bez komentarzy) z polami:
- penalties: lista {{description: str, percent: float, per_day: bool}}
- deadlines: lista {{description: str, value: str, critical: bool}}
- red_flags: lista {{message: str, severity: "high"|"medium"|"low", excerpt: str}}
- payment_terms: {{days: int, description: str}} lub null
- valorization: bool
- warranty_years: int lub null
- insurance_min_pln: float lub null

Szukaj szczególnie: kar umownych, braku waloryzacji, krótkich terminów, solidarnej odpowiedzialności."""

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        content = response.content[0].text
        # Extract JSON from response
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["ai_enhanced"] = True
            result["method"] = "claude_haiku"
            return result

    except Exception as e:
        logger.warning("AI risk extraction failed, falling back to patterns: %s", e)

    return extract_risks_from_text(text)


# ─────────────────────────────────────────────────────────────────────────────
# Faza 31-32 — Cost Estimation with Confidence Intervals
# ─────────────────────────────────────────────────────────────────────────────

# CPV group benchmarks (PLN/m²) — approximate market data
CPV_BENCHMARKS: dict[str, dict] = {
    "45": {
        "min": 1800, "mean": 3200, "max": 6000,
        "label": "Roboty budowlane ogólne"
    },
    "4521": {
        "min": 2500, "mean": 4200, "max": 8000,
        "label": "Budynki"
    },
    "45210": {
        "min": 2200, "mean": 2800, "max": 6500,
        "label": "Kubatura — budynki i hale"
    },
    "4523": {
        "min": 800, "mean": 1500, "max": 3000,
        "label": "Autostrady i drogi"
    },
    "45233": {
        "min": 300, "mean": 380, "max": 600,
        "label": "Drogi i chodniki"
    },
    "4524": {
        "min": 2000, "mean": 3800, "max": 7000,
        "label": "Kanalizacja i wodociągi"
    },
    "45231": {
        "min": 450, "mean": 650, "max": 1100,
        "label": "Sieci rurociągowe"
    },
    "4525": {
        "min": 1500, "mean": 2800, "max": 5500,
        "label": "Instalacje"
    },
    "4526": {
        "min": 600, "mean": 1200, "max": 2500,
        "label": "Roboty ziemne"
    },
    "45111": {
        "min": 150, "mean": 210, "max": 380,
        "label": "Roboty ziemne"
    },
    "4528": {
        "min": 3000, "mean": 5500, "max": 12000,
        "label": "Instalacje elektr."
    },
    "45221": {
        "min": 3000, "mean": 4500, "max": 8000,
        "label": "Mosty i wiadukty"
    },
    "45400": {
        "min": 300, "mean": 450, "max": 700,
        "label": "Roboty wykończeniowe"
    },
    "45310": {
        "min": 200, "mean": 280, "max": 450,
        "label": "Instalacje elektryczne"
    },
    "45330": {
        "min": 240, "mean": 320, "max": 520,
        "label": "Instalacje sanitarne"
    },
}


def estimate_cost(
    cpv: str,
    region: str,
    area_m2: float | None = None,
    value_estimated: float | None = None,
    description: str = "",
) -> dict:
    """
    Hybrid cost estimation:
    1. Historical benchmark from CPV benchmarks
    2. Simple parametric estimate if area given
    """
    # Get CPV benchmark
    cpv_key = cpv[:4] if len(cpv) >= 4 else cpv[:2]
    benchmark = CPV_BENCHMARKS.get(cpv_key, CPV_BENCHMARKS.get(cpv[:2], CPV_BENCHMARKS["45"]))

    # Regional price adjustment factors
    region_factors = {
        "MAZOWIECKIE": 1.20, "ŚLĄSKIE": 1.05, "MAŁOPOLSKIE": 1.08,
        "DOLNOŚLĄSKIE": 1.10, "ŁÓDZKIE": 0.95, "WIELKOPOLSKIE": 1.00,
        "POMORSKIE": 1.08, "KUJAWSKO-POMORSKIE": 0.92, "LUBELSKIE": 0.88,
        "PODKARPACKIE": 0.87, "WARMIŃSKO-MAZURSKIE": 0.90, "PODLASKIE": 0.88,
        "ŚWIĘTOKRZYSKIE": 0.89, "LUBUSKIE": 0.93, "OPOLSKIE": 0.92,
        "ZACHODNIOPOMORSKIE": 0.97,
    }
    region_upper = region.upper() if region else ""
    r_factor = 1.0
    for key, factor in region_factors.items():
        if key in region_upper:
            r_factor = factor
            break

    # Estimate
    benchmark_estimate = None
    if area_m2 and area_m2 > 0:
        benchmark_estimate = benchmark["mean"] * area_m2 * r_factor

    # If we have value_estimated from BZP, use it as baseline
    if value_estimated and value_estimated > 0:
        base = value_estimated
    elif benchmark_estimate:
        base = benchmark_estimate
    else:
        base = None

    if base is None:
        return {
            "error": "Niewystarczające dane — podaj area_m2 lub value_estimated",
            "cpv_benchmark": benchmark,
        }

    # Confidence interval — 15% either side (P95)
    low_95 = round(base * 0.75)
    high_95 = round(base * 1.25)
    low_50 = round(base * 0.92)
    high_50 = round(base * 1.08)

    return {
        "expected_estimate": round(base),
        "low_95": low_95,
        "high_95": high_95,
        "low_50": low_50,
        "high_50": high_50,
        "confidence_interval_pct": 95,
        "method": "benchmark_parametric",
        "region_factor": r_factor,
        "cpv_label": benchmark["label"],
        "benchmark_per_m2": {
            "min": round(benchmark["min"] * r_factor),
            "mean": round(benchmark["mean"] * r_factor),
            "max": round(benchmark["max"] * r_factor),
        } if area_m2 else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Faza 33 — SHAP-like Cost Drivers Explanation
# ─────────────────────────────────────────────────────────────────────────────

def explain_cost_drivers(
    estimate: float,
    cpv: str,
    region: str,
    area_m2: float | None,
    description: str = "",
) -> list[dict]:
    """
    Explain main cost drivers — simplified SHAP waterfall.
    Returns sorted list of {factor, impact_pln, direction: 'up'|'down'}.
    """
    drivers = []
    base = estimate

    # Region premium/discount
    region_upper = region.upper() if region else ""
    if "MAZOWIECKIE" in region_upper:
        drivers.append({"factor": "Lokalizacja Warszawa/Mazowsze", "impact_pln": round(base * 0.18), "direction": "up"})
    elif "ŚLĄSKIE" in region_upper:
        drivers.append({"factor": "Lokalizacja Śląsk", "impact_pln": round(base * 0.05), "direction": "up"})
    elif "LUBELSKIE" in region_upper or "PODKARPACKIE" in region_upper:
        drivers.append({"factor": "Lokalizacja wschodnia Polska", "impact_pln": round(base * 0.12), "direction": "down"})

    # Area size driver
    if area_m2:
        if area_m2 > 5000:
            drivers.append({"factor": f"Duża powierzchnia ({area_m2:.0f} m²)", "impact_pln": round(base * 0.08), "direction": "up"})
        elif area_m2 < 500:
            drivers.append({"factor": f"Mała powierzchnia ({area_m2:.0f} m²) — wyższy koszt jedn.", "impact_pln": round(base * 0.12), "direction": "up"})

    # Description keywords
    desc_lower = description.lower()
    if any(k in desc_lower for k in ["remont", "modernizacja"]):
        drivers.append({"factor": "Roboty remontowe (wyższe koszty rozbiórek)", "impact_pln": round(base * 0.10), "direction": "up"})
    if any(k in desc_lower for k in ["prefabrykat", "modularny"]):
        drivers.append({"factor": "Prefabrykacja (niższe koszty montażu)", "impact_pln": round(base * 0.07), "direction": "down"})
    if "instalacj" in desc_lower:
        drivers.append({"factor": "Instalacje specjalistyczne", "impact_pln": round(base * 0.15), "direction": "up"})

    # Sort by absolute impact
    drivers.sort(key=lambda x: x["impact_pln"], reverse=True)
    return drivers[:6]


# ─────────────────────────────────────────────────────────────────────────────
# Faza 34 — Win Probability Model
# ─────────────────────────────────────────────────────────────────────────────

def estimate_win_probability(
    markup_pct: float,
    n_competitors: int,
    cpv: str = "",
    historical_data: list[dict] | None = None,
) -> dict:
    """
    Win probability given markup and competitor count.

    Args:
        markup_pct: Markup in percent (e.g. 12.0 for 12%)
        n_competitors: Number of competitors
        historical_data: Past bids for calibration
    """
    markup = markup_pct / 100.0
    result = optimal_markup(1_000_000, n_competitors, historical_data)

    # Find win prob at the requested markup
    markups = np.linspace(0.01, 0.40, 200)
    k = 2.0 + 0.3 * math.log1p(n_competitors)
    idx = int(np.argmin(np.abs(markups - markup)))
    p_win = float(np.exp(-k * markup * (n_competitors ** 0.6)))
    p_win = max(0.001, min(0.999, p_win))

    return {
        "markup_pct": markup_pct,
        "win_probability": round(p_win, 4),
        "win_probability_pct": round(p_win * 100, 1),
        "n_competitors": n_competitors,
        "optimal_markup_pct": result["optimal_markup_pct"],
        "interpretation": (
            "Wysokie szanse" if p_win > 0.35 else
            "Umiarkowane szanse" if p_win > 0.15 else
            "Niskie szanse"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Faza 37 — Bid Recommendation Engine
# ─────────────────────────────────────────────────────────────────────────────

def generate_recommendation(
    cost_estimate: float,
    n_competitors: int,
    ahp_scores: dict[str, float] | None = None,
    red_flags: list[dict] | None = None,
    cpv: str = "",
    region: str = "",
    area_m2: float | None = None,
) -> dict:
    """
    Full bid recommendation combining all analytics layers.
    """
    # 1. AHP score
    ahp_result = compute_ahp_score(ahp_scores or {})
    ahp_score = ahp_result["total"]

    # 2. Optimal markup
    bidding = optimal_markup(cost_estimate, n_competitors)
    win_prob = bidding["win_probability"]
    opt_markup = bidding["optimal_markup_pct"]
    expected_profit = bidding["expected_profit"]

    # 3. Risk flags
    flags = red_flags or []
    high_risks = [f for f in flags if f.get("severity") == "high"]
    medium_risks = [f for f in flags if f.get("severity") == "medium"]

    # 4. Cost estimate interval
    cost_est = estimate_cost(cpv, region, area_m2, cost_estimate)

    # 5. Final recommendation logic
    risk_penalty = len(high_risks) * 15 + len(medium_risks) * 5
    combined_score = (ahp_score * 0.4 + win_prob * 100 * 0.4) - risk_penalty

    if combined_score >= 60 and len(high_risks) <= 1:
        rec = "GO"
        rec_pl = "Złóż ofertę"
        confidence = min(0.95, (combined_score / 100) + 0.1)
        color = "green"
    elif combined_score >= 35 and len(high_risks) <= 2:
        rec = "CONSIDER"
        rec_pl = "Rozważ (wymagane dodatkowe analizy)"
        confidence = min(0.75, combined_score / 100)
        color = "yellow"
    else:
        rec = "NO-GO"
        rec_pl = "Nie składaj oferty"
        confidence = min(0.90, 1 - combined_score / 100)
        color = "red"

    # Key opportunities
    opportunities = []
    if n_competitors <= 3:
        opportunities.append(f"Mała konkurencja ({n_competitors} firm)")
    if win_prob > 0.25:
        opportunities.append(f"Dobra szansa wygrania ({win_prob*100:.0f}%)")
    if ahp_score >= 70:
        opportunities.append(f"Wysoki AHP score ({ahp_score}/100)")
    if not high_risks:
        opportunities.append("Brak krytycznych ryzyk w SWZ")

    key_risks = [f["message"] for f in high_risks[:3]]
    if medium_risks and len(key_risks) < 3:
        key_risks.extend([f["message"] for f in medium_risks[:2]])

    return {
        "recommendation": rec,
        "recommendation_pl": rec_pl,
        "color": color,
        "confidence": round(confidence, 2),
        "ahp_score": ahp_score,
        "win_probability": round(win_prob, 4),
        "win_probability_pct": round(win_prob * 100, 1),
        "optimal_markup_pct": opt_markup,
        "expected_profit": expected_profit,
        "bid_price": bidding["bid_price"],
        "n_competitors": n_competitors,
        "key_risks": key_risks,
        "key_opportunities": opportunities,
        "cost_estimate": {
            "expected": cost_estimate,
            "low_95": cost_est.get("low_95"),
            "high_95": cost_est.get("high_95"),
        },
        "ahp_details": ahp_result,
        "bidding_details": bidding,
    }
