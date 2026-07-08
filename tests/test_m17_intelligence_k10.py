"""Sprint K10 tests — material_risk + forecaster + win_prob intelligence modules."""
import uuid
import pytest

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


# ─── material_risk ────────────────────────────────────────────────────────────

class TestMaterialRisk:
    def test_get_active_alerts_empty(self):
        from services.api.services.api.intelligence.material_risk import get_active_alerts
        alerts = get_active_alerts(TENANT_ID)
        assert isinstance(alerts, list)

    def test_get_active_alerts_limit(self):
        from services.api.services.api.intelligence.material_risk import get_active_alerts
        alerts = get_active_alerts(TENANT_ID, limit=5)
        assert isinstance(alerts, list)
        assert len(alerts) <= 5

    def test_acknowledge_nonexistent(self):
        from services.api.services.api.intelligence.material_risk import acknowledge_alert
        result = acknowledge_alert(str(uuid.uuid4()), TENANT_ID)
        assert result is False

    def test_check_material_risks_no_linked_pozycje(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        # Kosztorys with no icb_id_m links should return empty list
        result = check_material_risks(str(uuid.uuid4()), TENANT_ID)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_alerts_invalid_tenant(self):
        from services.api.services.api.intelligence.material_risk import get_active_alerts
        alerts = get_active_alerts("00000000-0000-0000-0000-000000000000")
        assert isinstance(alerts, list)
        assert len(alerts) == 0


# ─── forecaster ───────────────────────────────────────────────────────────────

class TestForecaster:
    def test_forecast_icb_price_no_data(self):
        from services.api.services.api.intelligence.forecaster import forecast_icb_price
        # ICB id that doesn't exist → graceful fallback
        result = forecast_icb_price(icb_id=9999999, quarters_ahead=4)
        # Should return dict or None — never crash
        assert result is None or isinstance(result, dict)

    def test_get_cached_forecast_missing(self):
        from services.api.services.api.intelligence.forecaster import get_cached_forecast
        result = get_cached_forecast(icb_id=9999999, year=2099, quarter=1)
        assert result is None

    def test_run_top_materials_forecast(self):
        from services.api.services.api.intelligence.forecaster import run_top_materials_forecast
        result = run_top_materials_forecast(limit=10)
        assert isinstance(result, dict)
        assert "cached" in result or "icb_ids" in result or "error" in result

    def test_cache_forecasts_empty_list(self):
        from services.api.services.api.intelligence.forecaster import cache_forecasts
        count = cache_forecasts(icb_ids=[])
        assert isinstance(count, int)
        assert count == 0

    def test_forecast_real_icb_item(self):
        """Try forecasting a real ICB id from DB — graceful even if insufficient data."""
        from services.api.services.api.intelligence.forecaster import forecast_icb_price
        from terra_db.session import get_engine
        import sqlalchemy as sa

        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT id_ceny FROM icb_ceny_srednie LIMIT 1"
            )).fetchone()

        if row is None:
            pytest.skip("No ICB data available")

        result = forecast_icb_price(icb_id=row.id_ceny, quarters_ahead=2)
        # May return None if <3 data points — that's fine
        assert result is None or isinstance(result, dict)
        if isinstance(result, dict):
            assert "icb_id" in result or "predictions" in result


# ─── win_prob ─────────────────────────────────────────────────────────────────

class TestWinProb:
    def test_compute_win_probability_no_data(self):
        from services.api.services.api.intelligence.win_prob import compute_win_probability
        result = compute_win_probability(
            estimated_value=500000.0,
            cpv_prefix="45999",  # unlikely to have data
        )
        assert isinstance(result, dict)
        assert "optimal_bid_pct" in result or "quantiles" in result or "error" in result

    def test_estimate_win_prob_fallback(self):
        from services.api.services.api.intelligence.win_prob import estimate_win_prob
        prob = estimate_win_prob(offer_pct=97.1, cpv_prefix="45999")
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_estimate_win_prob_low_offer(self):
        from services.api.services.api.intelligence.win_prob import estimate_win_prob
        prob_low = estimate_win_prob(offer_pct=80.0, cpv_prefix="45999")
        prob_high = estimate_win_prob(offer_pct=105.0, cpv_prefix="45999")
        # Lower offer → higher win prob
        assert prob_low >= prob_high

    def test_get_market_benchmarks(self):
        from services.api.services.api.intelligence.win_prob import get_market_benchmarks
        result = get_market_benchmarks(cpv_prefix="45")
        assert isinstance(result, dict)
        assert "count" in result

    def test_compute_win_real_cpv(self):
        from services.api.services.api.intelligence.win_prob import compute_win_probability
        result = compute_win_probability(
            estimated_value=1_000_000.0,
            cpv_prefix="45",  # broad CPV — likely has data
        )
        assert isinstance(result, dict)
