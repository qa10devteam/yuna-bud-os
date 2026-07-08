"""Sprint K12 — Intelligence Layer unit tests.
Covers: anomaly.py, forecaster.py, material_risk.py, analytics/win_probability.py
Strategy: mock get_engine to avoid real DB calls; test logic in isolation.
"""
from __future__ import annotations
import uuid
from unittest.mock import MagicMock, patch
import numpy as np
import pytest


def _make_engine(rows=None, fetchone_row=None, rowcount=1):
    conn = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = rows or []
    result.fetchone.return_value = fetchone_row
    result.rowcount = int(rowcount)  # always int, not MagicMock
    conn.execute.return_value = result
    conn.commit = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = lambda s: conn
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = ctx
    return engine, conn


# ─── forecaster helpers ──────────────────────────────────────────────────────

class TestForecasterHelpers:
    def test_quarter_to_index(self):
        from services.api.services.api.intelligence.forecaster import _quarter_to_index
        assert _quarter_to_index(1, 2024) == 2024 * 4 + 0  # kwartalnr-1 = 0

    def test_quarter_roundtrip(self):
        from services.api.services.api.intelligence.forecaster import (
            _quarter_to_index, _index_to_quarter,
        )
        for q, y in [(1, 2020), (2, 2023), (4, 2026)]:
            q2, y2 = _index_to_quarter(_quarter_to_index(q, y))
            assert (q2, y2) == (q, y)


class TestForecastIcbPrice:
    def _price_rows(self, n=12):
        """Return tuples matching icb_ceny_srednie columns used by forecaster:
        idx 0=symbol, 1=typ_rms, 2=kwartalnr, 3=kwartalrok, 4=cena_netto
        """
        rows = []
        for i in range(n):
            q = (i % 4) + 1
            y = 2023 + i // 4
            rows.append(("R001", "R", q, y, 40.0 + i * 0.5))
        return rows

    def test_returns_predictions(self):
        from services.api.services.api.intelligence import forecaster
        engine, conn = _make_engine(rows=self._price_rows(12))
        with patch.object(forecaster, "get_engine", return_value=engine):
            r = forecaster.forecast_icb_price(101, quarters_ahead=2)
        assert isinstance(r, dict)
        preds = r.get("predictions", [])
        assert len(preds) == 2
        for p in preds:
            assert p["lower"] <= p["price"] <= p["upper"]

    def test_positive_trend(self):
        from services.api.services.api.intelligence import forecaster
        rows = [("M002", "M", (i % 4) + 1, 2023 + i // 4, 100.0 + i * 2.0) for i in range(12)]
        engine, _ = _make_engine(rows=rows)
        with patch.object(forecaster, "get_engine", return_value=engine):
            r = forecaster.forecast_icb_price(200, quarters_ahead=4)
        assert r.get("trend_pct", 0) > 0

    def test_empty_data_graceful(self):
        from services.api.services.api.intelligence import forecaster
        engine, _ = _make_engine(rows=[])
        with patch.object(forecaster, "get_engine", return_value=engine):
            r = forecaster.forecast_icb_price(999)
        assert isinstance(r, dict)
        assert r.get("predictions", []) == [] or r == {}

    def test_cached_forecast_hit(self):
        from services.api.services.api.intelligence import forecaster
        from datetime import datetime
        # tuple: icb_id, symbol, typ_rms, forecast_year, forecast_quarter,
        #        predicted_price, price_lower, price_upper, trend_pct, created_at
        row = (101, "R001", "R", 2026, 3, 55.0, 52.0, 58.0, 2.5, datetime.now())
        engine, _ = _make_engine(fetchone_row=row)
        with patch.object(forecaster, "get_engine", return_value=engine):
            r = forecaster.get_cached_forecast(101, 2026, 3)
        assert r is not None
        assert r["predicted_price"] == 55.0

    def test_cached_forecast_miss(self):
        from services.api.services.api.intelligence import forecaster
        engine, _ = _make_engine(fetchone_row=None)
        with patch.object(forecaster, "get_engine", return_value=engine):
            r = forecaster.get_cached_forecast(999, 2030, 1)
        assert r is None

    def test_cache_forecasts(self):
        from services.api.services.api.intelligence import forecaster
        mock_forecast = {
            "icb_id": 101, "symbol": "R001", "typ_rms": "R", "trend_pct": 2.5,
            "predictions": [
                {"quarter": 1, "year": 2027, "price": 55.0, "lower": 52.0, "upper": 58.0}
            ],
        }
        engine, _ = _make_engine()
        with patch.object(forecaster, "get_engine", return_value=engine), \
             patch.object(forecaster, "forecast_icb_price", return_value=mock_forecast):
            count = forecaster.cache_forecasts([101], quarters_ahead=1)
        assert isinstance(count, int)


# ─── anomaly ─────────────────────────────────────────────────────────────────

class TestAnomaly:
    def test_zscore_pozycja_not_found(self):
        from services.api.services.api.intelligence import anomaly
        engine, _ = _make_engine(fetchone_row=None)
        with patch.object(anomaly, "get_engine", return_value=engine):
            r = anomaly.zscore_pozycja(str(uuid.uuid4()))
        assert isinstance(r, dict)

    def test_zscore_no_icb_links(self):
        from services.api.services.api.intelligence import anomaly
        row = MagicMock()
        row.r_jcena = 45.0; row.m_jcena = 120.0; row.s_jcena = 10.0
        row.icb_id_r = None; row.icb_id_m = None; row.icb_id_s = None
        row.opis = "Tynki"; row.jednostka = "m2"
        engine, _ = _make_engine(fetchone_row=row, rows=[])
        with patch.object(anomaly, "get_engine", return_value=engine):
            r = anomaly.zscore_pozycja(str(uuid.uuid4()))
        assert isinstance(r, dict)
        assert "is_anomaly" in r

    def test_get_anomalies_empty(self):
        from services.api.services.api.intelligence import anomaly
        engine, _ = _make_engine(rows=[])
        with patch.object(anomaly, "get_engine", return_value=engine):
            r = anomaly.get_anomalies(str(uuid.uuid4()), str(uuid.uuid4()))
        assert r == []

    def test_isolation_forest_too_small(self):
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest
        tiny = np.array([[1.0, 2.0], [3.0, 4.0]])
        assert _try_isolation_forest(tiny) is None

    def test_isolation_forest_valid_size(self):
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest
        matrix = np.random.rand(10, 3)
        result = _try_isolation_forest(matrix)
        if result is not None:
            assert len(result) == 10
            assert all(isinstance(v, bool) for v in result)


# ─── material_risk ────────────────────────────────────────────────────────────

class TestGetSeverity:
    def test_low(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(3.0) == "low"
        assert _get_severity(-3.0) == "low"

    def test_medium(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(7.5) == "medium"

    def test_high(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(15.0) == "high"

    def test_critical(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(25.0) == "critical"
        assert _get_severity(-25.0) == "critical"


class TestMaterialRisk:
    def test_get_active_alerts_empty(self):
        from services.api.services.api.intelligence import material_risk
        engine, _ = _make_engine(rows=[])
        with patch.object(material_risk, "get_engine", return_value=engine):
            r = material_risk.get_active_alerts(str(uuid.uuid4()))
        assert r == []

    def test_acknowledge_alert_success(self):
        from services.api.services.api.intelligence import material_risk
        engine, conn = _make_engine(rowcount=1)
        engine.begin.return_value = engine.connect.return_value  # begin() → same ctx
        with patch.object(material_risk, "get_engine", return_value=engine):
            ok = material_risk.acknowledge_alert(str(uuid.uuid4()), str(uuid.uuid4()))
        assert ok is True

    def test_acknowledge_alert_not_found(self):
        from services.api.services.api.intelligence import material_risk
        engine, conn = _make_engine(rowcount=0)
        engine.begin.return_value = engine.connect.return_value
        with patch.object(material_risk, "get_engine", return_value=engine):
            ok = material_risk.acknowledge_alert(str(uuid.uuid4()), str(uuid.uuid4()))
        assert ok is False

    def test_check_material_risks_no_pozycje(self):
        from services.api.services.api.intelligence import material_risk
        engine, _ = _make_engine(rows=[])
        with patch.object(material_risk, "get_engine", return_value=engine):
            r = material_risk.check_material_risks(str(uuid.uuid4()), str(uuid.uuid4()))
        assert r == []


# ─── analytics/win_probability.py ────────────────────────────────────────────

class TestWinProbabilityModel:
    def test_predict_untrained_fallback(self):
        from services.api.services.api.analytics.win_probability import WinProbabilityModel
        model = WinProbabilityModel()
        r = model.predict(markup=0.05, n_competitors=3)
        assert isinstance(r, dict)
        assert "win_probability" in r
        assert 0.0 <= r["win_probability"] <= 1.0

    def test_train_returns_dict(self):
        from services.api.services.api.analytics.win_probability import WinProbabilityModel
        model = WinProbabilityModel()
        bids = [
            {"markup": 0.05, "n_competitors": 3, "cpv_group": "45", "won": 1},
            {"markup": 0.10, "n_competitors": 5, "cpv_group": "45", "won": 0},
            {"markup": 0.08, "n_competitors": 4, "cpv_group": "45", "won": 1},
        ]
        stats = model.train(bids)
        assert isinstance(stats, dict)

    def test_train_and_predict(self):
        from services.api.services.api.analytics.win_probability import WinProbabilityModel
        model = WinProbabilityModel()
        bids = [
            {"markup": m, "n_competitors": 3, "cpv_group": "45", "won": int(m < 0.07)}
            for m in [0.03, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.04, 0.07, 0.09]
        ]
        model.train(bids)
        r = model.predict(markup=0.05, n_competitors=3)
        assert 0.0 <= r["win_probability"] <= 1.0

    def test_get_win_model(self):
        from services.api.services.api.analytics.win_probability import (
            get_win_model, WinProbabilityModel,
        )
        assert isinstance(get_win_model(), WinProbabilityModel)

    def test_monotonicity(self):
        from services.api.services.api.analytics.win_probability import WinProbabilityModel
        model = WinProbabilityModel()
        bids = [
            {"markup": m, "n_competitors": 3, "cpv_group": "45", "won": int(m < 0.08)}
            for m in [0.02, 0.04, 0.06, 0.07, 0.09, 0.11, 0.13, 0.03, 0.05, 0.08, 0.10, 0.12]
        ]
        model.train(bids)
        p_low = model.predict(markup=0.03, n_competitors=3)
        p_high = model.predict(markup=0.15, n_competitors=3)
        assert p_low["win_probability"] >= p_high["win_probability"]


# ─── intelligence/win_prob.py ────────────────────────────────────────────────

class TestWinProbModule:
    def test_compute_win_probability_fallback(self):
        from services.api.services.api.intelligence import win_prob
        engine, _ = _make_engine(rows=[])
        with patch.object(win_prob, "get_engine", return_value=engine):
            r = win_prob.compute_win_probability(500000.0, "45200")
        assert isinstance(r, dict)
        assert "quantiles" in r
        assert "sample_size" in r

    def test_estimate_win_prob_median(self):
        from services.api.services.api.intelligence import win_prob
        engine, _ = _make_engine(rows=[])
        with patch.object(win_prob, "get_engine", return_value=engine):
            p = win_prob.estimate_win_prob(97.1, "45200")
        assert 0.0 <= p <= 1.0
        assert abs(p - 0.5) < 0.2

    def test_estimate_win_prob_low_offer(self):
        from services.api.services.api.intelligence import win_prob
        engine, _ = _make_engine(rows=[])
        with patch.object(win_prob, "get_engine", return_value=engine):
            p = win_prob.estimate_win_prob(50.0, "45200")
        assert p >= 0.5

    def test_get_market_benchmarks_empty(self):
        from services.api.services.api.intelligence import win_prob
        engine, _ = _make_engine(rows=[], fetchone_row=None)
        with patch.object(win_prob, "get_engine", return_value=engine):
            r = win_prob.get_market_benchmarks("45200")
        assert isinstance(r, dict)
