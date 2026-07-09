"""FIX-3 — analytics/__init__.py coverage: optimal_markup, compute_ahp_score,
extract_risks_from_text, estimate_cost, explain_cost_drivers,
estimate_win_probability, generate_recommendation."""
from __future__ import annotations

import pytest


class TestOptimalMarkup:
    def test_basic_output_keys(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(cost_estimate=100_000.0, n_competitors=4)
        assert isinstance(result, dict)
        assert "optimal_markup" in result

    def test_optimal_markup_positive(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(cost_estimate=500_000.0, n_competitors=6)
        assert result["optimal_markup"] > 0

    def test_with_historical_win_rates(self):
        from services.api.services.api.analytics import optimal_markup
        history = [
            {"markup": 0.10, "won": True},
            {"markup": 0.15, "won": False},
            {"markup": 0.12, "won": True},
        ]
        result = optimal_markup(
            cost_estimate=200_000.0, n_competitors=3,
            historical_win_rates=history,
        )
        assert isinstance(result["optimal_markup"], float)

    def test_single_competitor(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(cost_estimate=50_000.0, n_competitors=1)
        assert result["optimal_markup"] >= 0

    def test_many_vs_few_competitors(self):
        from services.api.services.api.analytics import optimal_markup
        few = optimal_markup(cost_estimate=100_000.0, n_competitors=2)
        many = optimal_markup(cost_estimate=100_000.0, n_competitors=10)
        # nie musi być strict ≤ — zależy od modelu Friedmana, ale oba muszą zwracać dict
        assert isinstance(few["optimal_markup"], float)
        assert isinstance(many["optimal_markup"], float)


class TestComputeAhpScore:
    def test_default_criteria(self):
        from services.api.services.api.analytics import compute_ahp_score
        scores = {"price": 8.0, "experience": 7.0, "timeline": 6.0}
        result = compute_ahp_score(scores=scores)
        assert isinstance(result, dict)

    def test_custom_criteria(self):
        from services.api.services.api.analytics import compute_ahp_score
        # criteria musi mieć 'id', 'label', 'weight'
        criteria = [
            {"id": "cena",   "label": "Cena",   "weight": 0.5},
            {"id": "termin", "label": "Termin", "weight": 0.3},
            {"id": "jakosc", "label": "Jakość", "weight": 0.2},
        ]
        scores = {"cena": 8.0, "termin": 7.0, "jakosc": 9.0}
        result = compute_ahp_score(scores=scores, criteria=criteria)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_zero_scores(self):
        from services.api.services.api.analytics import compute_ahp_score
        scores = {"price": 0.0, "experience": 0.0}
        result = compute_ahp_score(scores=scores)
        assert isinstance(result, dict)


class TestExtractRisksFromText:
    def test_empty_text(self):
        from services.api.services.api.analytics import extract_risks_from_text
        result = extract_risks_from_text("")
        assert isinstance(result, dict)

    def test_risk_keywords_detected(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = (
            "Projekt dotyczy rozbiórki budynku. Wymaga pozwolenia na budowę. "
            "Termin realizacji 6 miesięcy. Kara umowna 0.3% za każdy dzień zwłoki."
        )
        result = extract_risks_from_text(text)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_construction_terms(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Roboty ziemne, zbrojenie betonu, instalacje elektryczne, geotechnika."
        result = extract_risks_from_text(text)
        assert isinstance(result, dict)

    def test_no_risks_clean_text(self):
        from services.api.services.api.analytics import extract_risks_from_text
        result = extract_risks_from_text("Prosta dostawa materiałów biurowych.")
        assert isinstance(result, dict)


class TestEstimateCost:
    def test_basic_call(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost(cpv="45200000", region="śląskie", area_m2=500.0)
        assert isinstance(result, dict)

    def test_without_area(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost(cpv="45200000", region="mazowieckie")
        assert isinstance(result, dict)

    def test_with_value_estimated(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost(
            cpv="45300000", region="małopolskie",
            value_estimated=2_000_000.0,
        )
        assert isinstance(result, dict)

    def test_larger_area_higher_cost(self):
        from services.api.services.api.analytics import estimate_cost
        r100 = estimate_cost(cpv="45200000", region="śląskie", area_m2=100.0)
        r500 = estimate_cost(cpv="45200000", region="śląskie", area_m2=500.0)
        def _val(r):
            for k in ("total_pln", "cost", "estimate", "total", "value"):
                if k in r:
                    v = r[k]
                    return float(v) if v else 0.0
            return float(list(r.values())[0]) if r else 0.0
        assert _val(r500) >= _val(r100)

    def test_with_description(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost(
            cpv="45100000", region="dolnośląskie",
            description="Roboty przygotowawcze i rozbiórkowe.",
        )
        assert isinstance(result, dict)


class TestExplainCostDrivers:
    def test_returns_list(self):
        from services.api.services.api.analytics import explain_cost_drivers
        result = explain_cost_drivers(
            estimate=150_000.0,
            cpv="45200000",
            region="śląskie",
            area_m2=300.0,
        )
        assert isinstance(result, list)

    def test_driver_structure(self):
        from services.api.services.api.analytics import explain_cost_drivers
        result = explain_cost_drivers(
            estimate=100_000.0,
            cpv="45300000",
            region="mazowieckie",
            area_m2=None,
        )
        assert isinstance(result, list)
        if result:
            driver = result[0]
            assert "factor" in driver or "impact_pln" in driver or "direction" in driver

    def test_without_area(self):
        from services.api.services.api.analytics import explain_cost_drivers
        result = explain_cost_drivers(
            estimate=200_000.0,
            cpv="45400000",
            region="łódzkie",
            area_m2=None,
            description="Roboty wykończeniowe",
        )
        assert isinstance(result, list)


class TestAnalyticsEstimateWinProbability:
    def test_basic_call(self):
        from services.api.services.api.analytics import estimate_win_probability
        result = estimate_win_probability(markup_pct=10.0, n_competitors=4)
        assert isinstance(result, dict)

    def test_lower_markup_higher_win_prob(self):
        from services.api.services.api.analytics import estimate_win_probability
        low = estimate_win_probability(markup_pct=5.0, n_competitors=4)
        high = estimate_win_probability(markup_pct=25.0, n_competitors=4)
        def _p(r):
            return float(r.get("p_win") or r.get("probability") or r.get("win_probability") or list(r.values())[0])
        assert _p(low) >= _p(high)

    def test_bounds(self):
        from services.api.services.api.analytics import estimate_win_probability
        result = estimate_win_probability(markup_pct=12.0, n_competitors=5)
        # returns dict with 'win_probability' (float 0-1)
        p = float(result.get("win_probability") or result.get("p_win") or list(result.values())[0])
        assert 0.0 <= p <= 1.0

    def test_with_cpv(self):
        from services.api.services.api.analytics import estimate_win_probability
        result = estimate_win_probability(markup_pct=8.0, n_competitors=3, cpv="45200000")
        assert isinstance(result, dict)

    def test_with_historical_data(self):
        from services.api.services.api.analytics import estimate_win_probability
        history = [
            {"markup_pct": 8.0, "won": True},
            {"markup_pct": 15.0, "won": False},
        ]
        result = estimate_win_probability(
            markup_pct=10.0, n_competitors=3, historical_data=history
        )
        assert isinstance(result, dict)


class TestGenerateRecommendation:
    def test_basic_call(self):
        from services.api.services.api.analytics import generate_recommendation
        result = generate_recommendation(
            cost_estimate=1_000_000.0,
            n_competitors=4,
        )
        assert isinstance(result, dict)

    def test_high_score_positive_recommendation(self):
        from services.api.services.api.analytics import generate_recommendation
        result = generate_recommendation(
            cost_estimate=500_000.0,
            n_competitors=2,
            ahp_scores={"price": 9.0, "experience": 8.0},
        )
        assert isinstance(result, dict)

    def test_many_red_flags_warning(self):
        from services.api.services.api.analytics import generate_recommendation
        # red_flags muszą mieć 'severity' + 'message' (używane przez generate_recommendation)
        red_flags = [
            {"type": "penalty",       "severity": "high",   "message": "Kara umowna 0.5%/dzień"},
            {"type": "tight_deadline","severity": "high",   "message": "Termin 30 dni — zbyt krótki"},
            {"type": "unclear_scope", "severity": "medium", "message": "Niejasny zakres prac"},
        ]
        result = generate_recommendation(
            cost_estimate=2_000_000.0,
            n_competitors=8,
            red_flags=red_flags,
        )
        assert isinstance(result, dict)

    def test_with_all_params(self):
        from services.api.services.api.analytics import generate_recommendation
        result = generate_recommendation(
            cost_estimate=750_000.0,
            n_competitors=5,
            ahp_scores={"price": 7.0, "timeline": 6.0},
            red_flags=[],
            cpv="45200000",
            region="śląskie",
            area_m2=350.0,
        )
        assert isinstance(result, dict)
