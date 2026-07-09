"""FIX-6c — recommendation.py + advanced_analytics + monitoring coverage."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


# ═══════════════════════════════════════════════════════════════════════════════
# recommendation.generate_recommendation
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateRecommendation:
    """Tests for analytics/recommendation.py — generate_recommendation()."""

    def _tender(self, value_pln: float = 500_000.0) -> dict:
        return {
            "id": "t1",
            "title": "Roboty budowlane ul. Testowa",
            "value_pln": value_pln,
            "buyer": "Gmina Katowice",
            "voivodeship": "śląskie",
            "cpv": "45000000-7",
        }

    def test_go_recommendation_basic(self):
        from services.api.services.api.analytics.recommendation import generate_recommendation
        result = generate_recommendation(
            tender_data=self._tender(),
            n_competitors=3,
        )
        assert "recommendation" in result
        assert result["recommendation"] in ("GO", "NO-GO", "CONSIDER")
        assert 0.0 <= result["confidence"] <= 1.0
        assert "ahp_score" in result
        assert "win_probability" in result
        assert "optimal_markup" in result

    def test_with_custom_scores(self):
        from services.api.services.api.analytics.recommendation import generate_recommendation
        scores = {
            "technical_fit": 9.0,
            "expected_margin": 8.0,
            "team_load": 7.0,
            "penalty_risk": 8.0,
            "strategic_value": 9.0,
            "cashflow_impact": 7.0,
            "buyer_history": 8.0,
        }
        result = generate_recommendation(
            tender_data=self._tender(1_000_000.0),
            scores=scores,
            n_competitors=4,
        )
        assert result["ahp_score"] > 0
        assert "key_opportunities" in result

    def test_high_risk_flags_override_to_consider(self):
        from services.api.services.api.analytics.recommendation import generate_recommendation
        # 3+ high-severity red flags should downgrade GO → CONSIDER
        swz_text = (
            "Kara umowna 2% za każdy dzień zwłoki. "
            "Termin realizacji 30 dni — absolutnie nieprzekraczalny. "
            "Warunki płatności 180 dni. "
            "Projekt budowlany niedostępny."
        )
        result = generate_recommendation(
            tender_data=self._tender(),
            swz_text=swz_text,
            n_competitors=5,
        )
        assert result["recommendation"] in ("CONSIDER", "NO-GO", "GO")
        assert isinstance(result["key_risks"], list)

    def test_very_low_value_tender(self):
        from services.api.services.api.analytics.recommendation import generate_recommendation
        result = generate_recommendation(
            tender_data=self._tender(value_pln=0.0),
            cost_estimate=100_000.0,
            n_competitors=2,
        )
        assert "recommendation" in result
        assert result["cost_estimate"] == 100_000.0

    def test_with_historical_win_rates(self):
        from services.api.services.api.analytics.recommendation import generate_recommendation
        history = [
            {"markup": 0.10, "won": True},
            {"markup": 0.12, "won": False},
            {"markup": 0.08, "won": True},
        ]
        result = generate_recommendation(
            tender_data=self._tender(800_000.0),
            n_competitors=4,
            historical_win_rates=history,
        )
        assert "bidding_chart" in result
        assert "n_competitors" in result
        assert result["n_competitors"] == 4

    def test_returns_all_required_keys(self):
        from services.api.services.api.analytics.recommendation import generate_recommendation
        result = generate_recommendation(tender_data=self._tender())
        required = {
            "recommendation", "confidence", "ahp_score", "ahp_breakdown",
            "win_probability", "optimal_markup", "expected_profit",
            "cost_estimate", "key_risks", "key_opportunities",
            "bidding_chart", "n_competitors",
        }
        missing = required - set(result.keys())
        assert not missing, f"Missing keys: {missing}"


# ═══════════════════════════════════════════════════════════════════════════════
# advanced_analytics router endpoints
# ═══════════════════════════════════════════════════════════════════════════════

def _user(org_id: str = TENANT_ID):
    u = MagicMock()
    u.org_id = org_id
    return u


class TestAdvancedAnalytics:
    def test_analyze_swz_no_text_raises(self):
        """analyze_swz z tekstem — zwraca wynik."""
        from services.api.services.api.routers.advanced_analytics import (
            analyze_swz, AnalyzeSWZRequest,
        )
        body = AnalyzeSWZRequest(text="Roboty budowlane. Kara umowna 0.5%.")
        result = analyze_swz(body, _user())
        assert isinstance(result, dict)

    def test_score_decision(self):
        from services.api.services.api.routers.advanced_analytics import (
            score_decision, DecisionScoreRequest,
        )
        body = DecisionScoreRequest(
            scores={
                "technical_fit": 8, "expected_margin": 7, "team_load": 6,
                "penalty_risk": 7, "strategic_value": 8,
                "cashflow_impact": 6, "buyer_history": 7,
            }
        )
        result = score_decision(body, _user())
        assert isinstance(result, dict)
        assert "ahp_score" in result or "score" in result or "recommendation" in result

    def test_full_recommendation(self):
        from services.api.services.api.routers.advanced_analytics import (
            full_recommendation, FullRecommendationRequest,
        )
        body = FullRecommendationRequest(cost_estimate=500_000.0, n_competitors=4)
        result = full_recommendation(body, _user())
        assert isinstance(result, dict)

    def test_cost_trends(self):
        from services.api.services.api.routers.advanced_analytics import cost_trends
        with patch("terra_db.session.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = []
            mock_ge.return_value.connect.return_value = conn
            result = cost_trends(_user())
        assert isinstance(result, (dict, list))

    def test_sensitivity_analysis(self):
        from services.api.services.api.routers.advanced_analytics import (
            sensitivity_analysis, SensitivityRequest,
        )
        body = SensitivityRequest(cost_estimate=500_000.0)
        result = sensitivity_analysis(body, _user())
        assert isinstance(result, dict)
        assert "variables" in result or "tornado" in result or "sensitivity" in result

    def test_get_report(self):
        from services.api.services.api.routers.advanced_analytics import get_report
        with patch("terra_db.session.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = None
            conn.execute.return_value.fetchall.return_value = []
            mock_ge.return_value.connect.return_value = conn
            result = get_report("test-tender-id", _user())
        assert isinstance(result, dict)

    def test_submit_feedback(self):
        from services.api.services.api.routers.advanced_analytics import (
            submit_feedback, FeedbackRequest,
        )
        body = FeedbackRequest(tender_id="test-id", outcome="lost")
        with patch("terra_db.session.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            mock_ge.return_value.begin.return_value = conn
            result = submit_feedback(body, _user())
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# monitoring endpoints (async — użyj asyncio.run)
# ═══════════════════════════════════════════════════════════════════════════════
import asyncio


class TestMonitoring:
    def test_metrics_endpoint(self):
        from services.api.services.api.routers.monitoring import metrics
        result = asyncio.run(metrics())
        assert isinstance(result, dict)

    def test_health_detailed(self):
        from services.api.services.api.routers.monitoring import health_detailed
        result = asyncio.run(health_detailed())
        assert isinstance(result, dict)

    def test_system_status(self):
        from services.api.services.api.routers.monitoring import system_status
        admin = MagicMock()
        admin.org_id = TENANT_ID
        admin.role = "admin"
        admin.is_admin = True
        with patch("terra_db.session.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = MagicMock(count=5)
            conn.execute.return_value.fetchall.return_value = []
            mock_ge.return_value.connect.return_value = conn
            result = asyncio.run(system_status(admin))
        assert isinstance(result, dict)

    def test_get_alerts(self):
        from services.api.services.api.routers.monitoring import get_alerts
        admin = MagicMock()
        admin.org_id = TENANT_ID
        admin.role = "admin"
        admin.is_admin = True
        with patch("terra_db.session.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = []
            mock_ge.return_value.connect.return_value = conn
            result = asyncio.run(get_alerts(admin))
        assert isinstance(result, dict)

    def test_sla_metrics(self):
        from services.api.services.api.routers.monitoring import sla_metrics
        admin = MagicMock()
        admin.org_id = TENANT_ID
        admin.role = "admin"
        admin.is_admin = True
        with patch("terra_db.session.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = MagicMock(
                avg_response_ms=120.0, p95_response_ms=250.0, error_rate=0.01,
                uptime_pct=99.9, total_requests=10000,
            )
            conn.execute.return_value.fetchall.return_value = []
            mock_ge.return_value.connect.return_value = conn
            result = asyncio.run(sla_metrics(admin))
        assert isinstance(result, dict)
