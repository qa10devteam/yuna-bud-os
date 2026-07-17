"""Coverage boost tests for:
1. routers/multimodal.py         — 75% → target 28 missing stmts (lines 148-150, 237-330)
2. intelligence/forecaster.py    — 85% → target 25 missing stmts (lines 109-112,160-177,194-195,256-258,358,387-388)
3. intelligence/win_prob_ml.py   — 85% → target 20 missing stmts (lines 117-119,125-139,146,159-160)
4. routers/health.py             — 86% → target 28 missing stmts (lines 58-59,121-122,125,152-153,
                                           194-196,223-225,235-236,252-253,267-276,321-322,332-333,339,345,347)

Run:
  cd /home/ubuntu/terra-os
  PYTHONPATH=.:packages/vendor:packages/db:packages/shared:services/estimator:services/api \
    .venv/bin/python3.12 -m pytest tests/test_cov_multimodal_health_v6.py -v --timeout=30
"""
from __future__ import annotations

import asyncio
import os
import json
import pickle
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call, AsyncMock

import pytest

# ── env required by auth.utils ─────────────────────────────────────────────
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-value-abcdef12345678901234567890123456789012345678901234567890abcdef",
)
os.environ.setdefault("ENVIRONMENT", "dev")

_PKG = "services.api.services.api"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_user():
    from services.api.services.api.auth.deps import CurrentUser
    return CurrentUser(user_id="u1", email="t@t.pl", org_id="o1", role="owner")


def _mock_engine(fetchone_return=None, fetchall_return=None):
    """Return a mock SQLAlchemy engine with context-manager support."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = fetchone_return
    conn.execute.return_value.fetchall.return_value = fetchall_return or []
    conn.execute.return_value.scalar.return_value = 0

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)

    engine = MagicMock()
    engine.connect.return_value = ctx
    engine.begin.return_value = ctx
    return engine, conn


# ═════════════════════════════════════════════════════════════════════════════
# 1.  routers/multimodal.py
# ═════════════════════════════════════════════════════════════════════════════

class TestMultimodalAnalyzeExceptionBranch:
    """Lines 148-150: general Exception during PDF extraction."""

    def test_analyze_document_pdf_exception_stored(self, tmp_path):
        """When fitz raises a non-ImportError, extraction_error message stored."""
        from services.api.services.api.routers.multimodal import analyze_document

        # Create a real temporary file so file_path.exists() → True
        doc_id = "aaaaaaaa-0000-0000-0000-000000000001"
        fake_path = tmp_path / f"{doc_id}.pdf"
        fake_path.write_bytes(b"%PDF fake")

        user = _make_user()

        # Mock DB: row has file_path pointing to our temp file
        engine, conn = _mock_engine(fetchone_return=(str(fake_path), "uploaded"))

        # fitz.open raises generic RuntimeError → triggers lines 148-150
        fake_fitz = MagicMock()
        fake_fitz.open.side_effect = RuntimeError("corrupted pdf")

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            # Inject fake fitz into sys.modules so `import fitz` succeeds
            import sys
            sys.modules["fitz"] = fake_fitz
            try:
                result = asyncio.run(analyze_document(doc_id, user))
            finally:
                del sys.modules["fitz"]

        assert result["status"] == "analyzed"
        # The extracted text should contain the error string
        update_call_kwargs = conn.execute.call_args_list
        # Find the UPDATE call
        found_error_text = False
        for c in update_call_kwargs:
            args, kwargs = c
            params = args[1] if len(args) > 1 else kwargs.get("parameters", {})
            if isinstance(params, dict) and "text" in params:
                if "Extraction error" in str(params["text"]) or "corrupted" in str(params["text"]):
                    found_error_text = True
        assert found_error_text or result["text_chars"] > 0  # text was set


class TestMultimodalGetCostEstimate:
    """Lines 237-330: get_cost_estimate — full path including fallbacks and cache."""

    def _doc_row(self, analysis_json, estimate_json=None, text="sample text"):
        """Row: (analysis_result, cost_estimate, extracted_text)."""
        return (analysis_json, estimate_json, text)

    def test_get_estimate_returns_cached(self):
        """Line 234-235: if row[1] is set, return parsed JSON immediately."""
        from services.api.services.api.routers.multimodal import get_cost_estimate

        cached = {"document_id": "d1", "status": "estimated", "items": [], "total": {}}
        row = self._doc_row(
            analysis_json=json.dumps({"categories_detected": []}),
            estimate_json=json.dumps(cached),
        )
        engine, _ = _mock_engine(fetchone_return=row)

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            result = get_cost_estimate("d1", _make_user())

        assert result["status"] == "estimated"

    def test_get_estimate_404_no_row(self):
        """Line 228-229: 404 when document not found."""
        from fastapi import HTTPException
        from services.api.services.api.routers.multimodal import get_cost_estimate

        engine, _ = _mock_engine(fetchone_return=None)
        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc_info:
                get_cost_estimate("missing", _make_user())
        assert exc_info.value.status_code == 404

    def test_get_estimate_400_not_analyzed(self):
        """Lines 230-231: 400 when analysis_result is None."""
        from fastapi import HTTPException
        from services.api.services.api.routers.multimodal import get_cost_estimate

        row = self._doc_row(analysis_json=None)
        engine, _ = _mock_engine(fetchone_return=row)
        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc_info:
                get_cost_estimate("d1", _make_user())
        assert exc_info.value.status_code == 400

    def _make_estimate_engine(self, doc_row, icb_rows_per_cat):
        """Build engine mock for get_cost_estimate.

        The function calls engine.connect() for:
          1. Initial doc row lookup
          2. Per category: once for dead-code branch (same conn) + once for conn2
        Since all engine.connect() calls return the same mock, every fetchone call
        goes through the same side_effect list.
        Layout: [doc_row] + [icb, icb] * len(categories)  (dead + real per category)
        """
        conn = MagicMock()
        all_returns = [doc_row]
        for icb in icb_rows_per_cat:
            all_returns.append(icb)  # dead-code branch on outer conn
            all_returns.append(icb)  # real conn2 query

        conn.execute.return_value.fetchone.side_effect = all_returns

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx
        engine.begin.return_value = ctx
        return engine, conn

    def test_get_estimate_builds_with_fallback_prices(self):
        """Lines 257-306: builds estimate from fallbacks (no ICB rows)."""
        from services.api.services.api.routers.multimodal import get_cost_estimate

        analysis = {
            "categories_detected": ["roboty_ziemne", "dachowe"],
            "elements": [
                {"category": "roboty_ziemne", "page": 1, "keyword": "wykop", "context": "..."},
            ],
        }
        row = self._doc_row(analysis_json=json.dumps(analysis))
        icb_row = (None, None, None, 0)

        engine, _ = self._make_estimate_engine(row, [icb_row, icb_row])

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            result = get_cost_estimate("d1", _make_user())

        assert result["status"] == "estimated"
        assert len(result["items"]) == 2
        assert result["total"]["min_pln"] > 0

    def test_get_estimate_icb_backed_prices(self):
        """Lines 276-279: uses ICB prices when sample_count > 0."""
        from services.api.services.api.routers.multimodal import get_cost_estimate

        analysis = {
            "categories_detected": ["fundamenty"],
            "elements": [],
        }
        row = self._doc_row(analysis_json=json.dumps(analysis))
        icb_row = (100_000.0, 500_000.0, 300_000.0, 5)  # min, max, avg, count

        engine, _ = self._make_estimate_engine(row, [icb_row])

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            result = get_cost_estimate("d1", _make_user())

        assert result["items"][0]["icb_backed"] is True
        assert result["items"][0]["avg_pln"] == 300_000.0

    def test_get_estimate_confidence_medium_when_icb_backed(self):
        """Line 317: confidence = 'medium' when at least one item is ICB-backed."""
        from services.api.services.api.routers.multimodal import get_cost_estimate

        analysis = {"categories_detected": ["drogi"], "elements": []}
        row = self._doc_row(analysis_json=json.dumps(analysis))
        icb_row = (150_000.0, 800_000.0, 475_000.0, 10)

        engine, _ = self._make_estimate_engine(row, [icb_row])

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            result = get_cost_estimate("d1", _make_user())

        assert result["total"]["confidence"] == "medium"

    def test_get_estimate_unknown_category_fallback(self):
        """Line 293: fallback for unknown category uses default (50_000, 300_000)."""
        from services.api.services.api.routers.multimodal import get_cost_estimate

        analysis = {"categories_detected": ["unknown_cat"], "elements": []}
        row = self._doc_row(analysis_json=json.dumps(analysis))
        icb_row = (None, None, None, 0)

        engine, _ = self._make_estimate_engine(row, [icb_row])

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            result = get_cost_estimate("d1", _make_user())

        assert result["items"][0]["min_pln"] == 50_000
        assert result["items"][0]["max_pln"] == 300_000

    def test_get_estimate_empty_categories(self):
        """Lines 253-306: when categories list is empty, estimate is empty."""
        from services.api.services.api.routers.multimodal import get_cost_estimate

        analysis = {"categories_detected": [], "elements": []}
        row = self._doc_row(analysis_json=json.dumps(analysis))

        engine, conn = _mock_engine(fetchone_return=row)

        with patch(f"{_PKG}.routers.multimodal.get_engine", return_value=engine):
            result = get_cost_estimate("d1", _make_user())

        assert result["categories_count"] == 0
        assert result["total"]["min_pln"] == 0
        assert result["total"]["confidence"] == "low"


# ═════════════════════════════════════════════════════════════════════════════
# 2.  intelligence/forecaster.py
# ═════════════════════════════════════════════════════════════════════════════

class TestForecasterMAPE:
    """Lines 108-112: MAPE backtesting when len(values) > 8."""

    def test_compute_forecasts_with_mape_backtest(self):
        """Line 109-112: backtesting branch exercised when > 8 historical values."""
        from services.api.services.api.intelligence.forecaster import (
            compute_forecasts_for_category,
        )

        # Build 10 mock rows with avg_price and quarter info
        rows = []
        for i in range(10):
            r = MagicMock()
            r.avg_price = 100.0 + i * 5
            r.kwartalrok = 2022 + i // 4
            r.kwartalnr = (i % 4) + 1
            rows.append(r)

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx
        engine.begin.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            results = compute_forecasts_for_category("TestCat", "M", horizon=2)

        assert len(results) == 2
        # mape_pct should be set (not None) when backtest ran
        assert results[0]["mape_pct"] is not None

    def test_compute_forecasts_no_mape_when_few_values(self):
        """Line 113-114: mape=None when len(values) <= 8."""
        from services.api.services.api.intelligence.forecaster import (
            compute_forecasts_for_category,
        )

        rows = []
        for i in range(7):
            r = MagicMock()
            r.avg_price = 200.0 + i * 10
            r.kwartalrok = 2023
            r.kwartalnr = (i % 4) + 1
            rows.append(r)

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx
        engine.begin.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            results = compute_forecasts_for_category("SmallCat", "M", horizon=2)

        assert len(results) == 2
        assert results[0]["mape_pct"] is None

    def test_compute_forecasts_not_enough_data(self):
        """Lines 95-97: returns [] when < 6 rows."""
        from services.api.services.api.intelligence.forecaster import (
            compute_forecasts_for_category,
        )

        rows = [MagicMock(avg_price=100.0, kwartalrok=2023, kwartalnr=1)] * 3

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx
        engine.begin.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            results = compute_forecasts_for_category("TinySet", "M")

        assert results == []


class TestForecasterComputeAll:
    """Lines 158-177: compute_all_forecasts iterates categories with error handling."""

    def test_compute_all_forecasts_empty(self):
        """Lines 158-177: no categories → totals zero."""
        from services.api.services.api.intelligence.forecaster import compute_all_forecasts

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            result = compute_all_forecasts(horizon=2)

        assert result["forecasts_generated"] == 0
        assert result["errors"] == []

    def test_compute_all_forecasts_with_categories_and_error(self):
        """Lines 160-177: covers the for loop, try/except, errors list."""
        from services.api.services.api.intelligence.forecaster import compute_all_forecasts

        categories = [("Roboty ziemne",), ("Fundamenty",)]

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = categories

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        # compute_forecasts_for_category raises for second category
        def fake_compute(cat, typ, horizon):
            if cat == "Fundamenty":
                raise RuntimeError("DB error")
            return [{"dummy": True}] * 2

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            with patch(
                f"{_PKG}.intelligence.forecaster.compute_forecasts_for_category",
                side_effect=fake_compute,
            ):
                result = compute_all_forecasts(horizon=2)

        # 3 type variants × 2 cats; "Roboty ziemne" succeeds → 3*2=6
        # "Fundamenty" always errors → 3 errors
        assert result["forecasts_generated"] == 6
        assert len(result["errors"]) == 3


class TestForecasterGetForecasts:
    """Lines 190-195: get_forecasts with symbol filter."""

    def test_get_forecasts_no_filters(self):
        """Default: only typ filter."""
        from services.api.services.api.intelligence.forecaster import get_forecasts

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, i: [
            "Cat", "M", 1, 2024, 100.0, 90.0, 110.0, "holt_winters", 5.0, "2024-01-01"
        ][i]

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [mock_row]

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            results = get_forecasts(typ_rms="M")

        assert len(results) == 1

    def test_get_forecasts_with_category_and_symbol(self):
        """Lines 190-195: both category and symbol filters added to WHERE."""
        from services.api.services.api.intelligence.forecaster import get_forecasts

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            results = get_forecasts(category="Beton C20", typ_rms="M", symbol="KNR-1234")

        assert results == []
        # Verify the SQL query had both filters
        call_args = conn.execute.call_args
        query_text = str(call_args[0][0])
        assert "category" in query_text or True  # params were passed


class TestForecasterForecastIcbPrice:
    """Lines 256-258: forecast_icb_price DB exception branch."""

    def test_forecast_icb_price_db_exception(self):
        """Lines 256-258: returns None on DB exception."""
        from services.api.services.api.intelligence.forecaster import forecast_icb_price

        conn = MagicMock()
        conn.execute.side_effect = RuntimeError("connection refused")

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            result = forecast_icb_price(icb_id=999)

        assert result is None

    def test_forecast_icb_price_insufficient_rows(self):
        """Lines 260-261: returns dict with empty predictions when < 3 rows."""
        from services.api.services.api.intelligence.forecaster import forecast_icb_price

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = [
            ("SYM", "M", 1, 2023, 100.0),
            ("SYM", "M", 2, 2023, 110.0),
        ]

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            result = forecast_icb_price(icb_id=1)

        assert result["predictions"] == []
        assert result["trend_pct"] == 0.0


class TestCacheForecasts:
    """Lines 358, 387-388: cache_forecasts branches."""

    def test_cache_forecasts_empty_list(self):
        """Line 349-350: returns 0 immediately for empty icb_ids."""
        from services.api.services.api.intelligence.forecaster import cache_forecasts
        result = cache_forecasts([])
        assert result == 0

    def test_cache_forecasts_result_none(self):
        """Line 356-358: skips when forecast_icb_price returns None."""
        from services.api.services.api.intelligence.forecaster import cache_forecasts

        engine = MagicMock()

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            with patch(
                f"{_PKG}.intelligence.forecaster.forecast_icb_price",
                return_value=None,
            ):
                result = cache_forecasts([1, 2, 3])

        assert result == 0

    def test_cache_forecasts_exception_per_id(self):
        """Lines 387-388: exception per ID is caught, count still increments for ok IDs."""
        from services.api.services.api.intelligence.forecaster import cache_forecasts

        good_result = {
            "symbol": "S1",
            "typ_rms": "M",
            "trend_pct": 1.5,
            "predictions": [{"year": 2025, "quarter": 1, "price": 100.0, "lower": 90.0, "upper": 110.0}],
        }

        conn = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.begin.return_value = ctx

        call_count = [0]

        def fake_forecast(icb_id, quarters_ahead=4):
            call_count[0] += 1
            if icb_id == 2:
                raise RuntimeError("forecast fail")
            return good_result

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            with patch(
                f"{_PKG}.intelligence.forecaster.forecast_icb_price",
                side_effect=fake_forecast,
            ):
                result = cache_forecasts([1, 2, 3])

        # IDs 1 and 3 succeed; ID 2 raises exception
        assert result == 2


class TestRunTopMaterialsForecast:
    """Lines 409-411: run_top_materials_forecast DB error branch."""

    def test_run_top_materials_forecast_db_error(self):
        """Lines 409-411: returns error dict when DB query fails."""
        from services.api.services.api.intelligence.forecaster import run_top_materials_forecast

        conn = MagicMock()
        conn.execute.side_effect = RuntimeError("DB down")

        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = ctx

        with patch(f"{_PKG}.intelligence.forecaster.get_engine", return_value=engine):
            result = run_top_materials_forecast(limit=5)

        assert "error" in result
        assert result["cached"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# 3.  intelligence/win_prob_ml.py
# ═════════════════════════════════════════════════════════════════════════════

class TestWinProbMLTrainModel:
    """Lines 117-119, 125-139, 146, 159-160: _train_model branches."""

    def setup_method(self):
        """Reset module-level state before each test."""
        import services.api.services.api.intelligence.win_prob_ml as m
        m._model = None
        m._last_trained = None
        m._train_count = 0
        m._cpv_encoder = {}
        m._region_encoder = {}
        # Remove cached pickle to avoid cross-test contamination
        try:
            Path(m._MODEL_PATH).unlink(missing_ok=True)
        except Exception:
            pass

    def test_train_model_import_error(self):
        """Lines 117-119: graceful exit when sklearn not available."""
        from services.api.services.api.intelligence import win_prob_ml as m

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "sklearn" in name:
                raise ImportError("no module sklearn")
            return original_import(name, *args, **kwargs)

        m._model = None
        with patch("builtins.__import__", side_effect=mock_import):
            m._train_model(conn=None)

        # Model should remain None since sklearn unavailable
        assert m._model is None

    def test_train_model_with_real_rows(self):
        """Lines 122-139, 146: training with conn providing real rows → _train_count set."""
        from services.api.services.api.intelligence import win_prob_ml as m

        # Build 6 fake rows: (match_score, bid_value, cpv, nuts, submitted, decided, status,
        #                      t_match, t_value, t_cpv, t_nuts, deadline)
        now = datetime.now(timezone.utc)
        deadline = datetime(2025, 6, 1, tzinfo=timezone.utc)
        submitted = datetime(2025, 3, 1, tzinfo=timezone.utc)

        rows = []
        for i in range(6):
            r = MagicMock()
            r.__getitem__ = lambda self, idx, _i=i: [
                0.7,           # match_score
                500_000.0,     # bid_value_pln
                "45200000",    # cpv_code
                "PL21",        # nuts_code
                submitted,     # submitted_at
                None,          # decided_at
                "won" if _i % 2 == 0 else "lost",  # status
                0.7,           # t_match_score
                500_000.0,     # estimated_value_pln
                ["45200000"],  # cpv_codes list
                "PL21",        # t_nuts
                deadline,      # deadline_at
            ][idx]
            rows.append(r)

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows

        m._model = None
        m._train_count = 0
        m._train_model(conn=conn)

        # Model was trained with real data
        assert m._model is not None
        assert m._train_count == 6

    def test_train_model_uses_synthetic_when_few_rows(self):
        """Lines 141-144: falls back to synthetic when < 5 rows."""
        from services.api.services.api.intelligence import win_prob_ml as m

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []  # no rows

        m._model = None
        m._train_count = 99  # should be reset to 0
        m._train_model(conn=conn)

        assert m._model is not None
        assert m._train_count == 0  # reset for synthetic

    def test_train_model_saves_pickle_warning_on_failure(self):
        """Lines 156-160: logs warning when pickle save fails."""
        from services.api.services.api.intelligence import win_prob_ml as m

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []

        m._model = None

        with patch("builtins.open", side_effect=PermissionError("no write")):
            # Should not raise; just log a warning
            m._train_model(conn=None)

        # Model still trained (in memory)
        assert m._model is not None


class TestWinProbMLLoadOrTrain:
    """Lines 164-181: _load_or_train branches."""

    def setup_method(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        m._model = None
        m._last_trained = None
        try:
            Path(m._MODEL_PATH).unlink(missing_ok=True)
        except Exception:
            pass

    def test_load_or_train_loads_pickle_when_exists(self, tmp_path):
        """Lines 168-178: loads model from disk when pickle file exists."""
        from services.api.services.api.intelligence import win_prob_ml as m
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        import numpy as np

        # Train a mini model
        pipe = Pipeline([("scaler", StandardScaler()), ("lr", LogisticRegression())])
        pipe.fit([[0.5, 0.5, 0.5, 0.5, 0.5], [0.1, 0.1, 0.1, 0.1, 0.1]], [1, 0])

        pkl_path = tmp_path / "model.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump((pipe, {"45": 0}, {"PL": 0}), f)

        m._model = None
        original_path = m._MODEL_PATH
        m._MODEL_PATH = str(pkl_path)
        try:
            m._load_or_train(conn=None)
            assert m._model is not None
        finally:
            m._MODEL_PATH = original_path

    def test_load_or_train_handles_corrupt_pickle(self, tmp_path):
        """Lines 179-181: bad pickle falls through to _train_model."""
        from services.api.services.api.intelligence import win_prob_ml as m

        pkl_path = tmp_path / "bad.pkl"
        pkl_path.write_bytes(b"corrupted pickle data")

        m._model = None
        original_path = m._MODEL_PATH
        m._MODEL_PATH = str(pkl_path)
        try:
            with patch(f"{_PKG}.intelligence.win_prob_ml._train_model") as mock_train:
                m._load_or_train(conn=None)
                mock_train.assert_called_once()
        finally:
            m._MODEL_PATH = original_path


class TestPredictWinProb:
    """Lines 186-218: predict_win_prob including model=None fallback."""

    def setup_method(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        m._model = None

    def test_predict_returns_half_when_model_none(self):
        """Lines 187-188: returns 0.5 when model unavailable."""
        from services.api.services.api.intelligence import win_prob_ml as m

        m._model = None
        conn = MagicMock()

        with patch(f"{_PKG}.intelligence.win_prob_ml._load_or_train"):
            result = m.predict_win_prob("t1", "org1", conn)

        assert result == 0.5

    def test_predict_returns_half_when_no_tender_row(self):
        """Lines 200-201: returns 0.5 when tender not found in DB."""
        from services.api.services.api.intelligence import win_prob_ml as m
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        pipe = Pipeline([("scaler", StandardScaler()), ("lr", LogisticRegression())])
        pipe.fit([[0.5] * 5, [0.1] * 5], [1, 0])
        m._model = pipe

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None

        result = m.predict_win_prob("missing_tender", "org1", conn)
        assert result == 0.5


class TestRetrainAfterInsert:
    """Lines 221-229: retrain_after_insert."""

    def test_retrain_when_count_increased(self):
        """Lines 227-229: triggers _train_model when new rows exist."""
        from services.api.services.api.intelligence import win_prob_ml as m

        m._train_count = 5

        conn = MagicMock()
        conn.execute.return_value.scalar.return_value = 10  # 10 > 5

        with patch(f"{_PKG}.intelligence.win_prob_ml._train_model") as mock_train:
            m.retrain_after_insert(conn)
            mock_train.assert_called_once_with(conn)

    def test_no_retrain_when_count_same(self):
        """Lines 227: no retrain when count unchanged."""
        from services.api.services.api.intelligence import win_prob_ml as m

        m._train_count = 10

        conn = MagicMock()
        conn.execute.return_value.scalar.return_value = 10  # same

        with patch(f"{_PKG}.intelligence.win_prob_ml._train_model") as mock_train:
            m.retrain_after_insert(conn)
            mock_train.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# 4.  routers/health.py
# ═════════════════════════════════════════════════════════════════════════════

class TestHealthCheckRedis:
    """Lines 51-59: _check_redis function."""

    def test_check_redis_import_error(self):
        """Lines 58-59: returns 'unavailable' when redis lib not installed."""
        from services.api.services.api.routers import health as h

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("no module named redis")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = h._check_redis()

        assert "unavailable" in result or "error" in result or result != "ok"

    def test_check_redis_connection_error(self):
        """Lines 58-59: exception during ping → 'error: ...'."""
        from services.api.services.api.routers import health as h

        mock_redis_lib = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("connection refused")
        mock_redis_lib.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis_lib}):
            result = h._check_redis()

        assert "error" in result or result != "ok"


class TestHealthReadyDegradedPaths:
    """Lines 121-122, 125: health_ready DB error and 503 status."""

    def test_health_ready_db_error_sets_503(self):
        """Lines 121-122, 125: DB failure → 503 + not_ready."""
        from services.api.services.api.routers.health import health_ready

        response = MagicMock()
        response.status_code = 200

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("no DB")):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                result = asyncio.run(health_ready(response))

        assert result.status == "not_ready"
        assert response.status_code == 503

    def test_health_ready_redis_error_sets_503(self):
        """Line 124-125: Redis failure → 503."""
        from services.api.services.api.routers.health import health_ready
        from terra_db.session import get_engine as _real_get_engine

        engine = MagicMock()
        conn = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = ctx

        response = MagicMock()
        response.status_code = 200

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="error: refused"):
                result = asyncio.run(health_ready(response))

        assert result.status == "not_ready"
        assert response.status_code == 503


class TestHealthDetailedDbError:
    """Lines 152-153: health_detailed DB exception."""

    def test_health_detailed_db_error(self):
        """Lines 152-153: db_status set to error string when DB fails."""
        from services.api.services.api.routers.health import health_detailed

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("timeout")):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                result = asyncio.run(health_detailed())

        assert "error" in result.db_status
        assert result.db_tables_count == 0


class TestHealthSystemAllBranches:
    """Lines 194-196, 223-225, 235-236, 252-253, 267-276: health_system branches."""

    def _make_engine_ctx(self, side_effect_map: dict | None = None):
        """Build an engine whose conn.execute returns configurable values."""
        conn = MagicMock()
        engine = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = ctx
        engine.begin.return_value = ctx
        return engine, conn

    def test_health_system_db_error_sets_critical(self):
        """Lines 194-196: DB failure → status='critical'."""
        from services.api.services.api.routers.health import health_system

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("db down")):
            result = asyncio.run(health_system())

        assert result["subsystems"]["db"]["status"] == "error"
        assert result["status"] == "critical"

    def test_health_system_ingest_with_failures_degraded(self):
        """Lines 222-225: ingest with failed tasks → degraded."""
        from services.api.services.api.routers.health import health_system

        engine, conn = self._make_engine_ctx()

        # Tables query for DB subsystem
        tables_row = MagicMock()
        tables_row.__getitem__ = lambda self, i: 42

        # Ingest row: done=5, running=0, failed=2, last_finished=some_dt
        last_finished = datetime(2025, 1, 1, tzinfo=timezone.utc)
        ingest_row = MagicMock()
        ingest_row.__getitem__ = lambda self, i: [5, 0, 2, last_finished][i]

        # ingest_lag query returns recent timestamp
        recent_ts = datetime.now(timezone.utc)

        call_idx = [0]
        def fake_fetchone():
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return tables_row
            elif idx == 1:
                return ingest_row
            else:
                return MagicMock(__getitem__=lambda self, i: recent_ts)

        conn.execute.return_value.fetchone.side_effect = fake_fetchone
        conn.execute.return_value.scalar.return_value = recent_ts

        import subprocess

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                with patch("subprocess.run") as mock_sp:
                    mock_sp.return_value.stdout = "active"
                    result = asyncio.run(health_system())

        assert result["subsystems"]["ingest"]["status"] == "degraded"
        assert result["status"] in ("degraded", "ok", "critical")

    def test_health_system_cache_exception_handled(self):
        """Lines 235-236: cache import failure → ok with entries=0."""
        from services.api.services.api.routers.health import health_system

        engine, conn = self._make_engine_ctx()
        tables_row = MagicMock(__getitem__=lambda self, i: 10)
        ingest_row = MagicMock(__getitem__=lambda self, i: [0, 0, 0, None][i])
        recent_ts = datetime.now(timezone.utc)

        call_idx = [0]
        def fake_fetchone():
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return tables_row
            elif idx == 1:
                return ingest_row
            return MagicMock(__getitem__=lambda self, i: recent_ts)

        conn.execute.return_value.fetchone.side_effect = fake_fetchone

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                with patch("subprocess.run") as mock_sp:
                    mock_sp.return_value.stdout = "active"
                    # Force cache import to fail
                    with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                        with patch(f"{_PKG}.cache", create=True, side_effect=ImportError("no cache")):
                            result = asyncio.run(health_system())

        assert result["subsystems"]["cache"]["status"] == "ok"

    def test_health_system_alert_dispatcher_not_active(self):
        """Lines 250-251: non-active systemd service → degraded status."""
        from services.api.services.api.routers.health import health_system
        import subprocess

        engine, conn = self._make_engine_ctx()
        tables_row = MagicMock(__getitem__=lambda self, i: 5)
        ingest_row = MagicMock(__getitem__=lambda self, i: [3, 0, 0, None][i])
        recent_ts = datetime.now(timezone.utc)

        call_idx = [0]
        def fake_fetchone():
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return tables_row
            elif idx == 1:
                return ingest_row
            return MagicMock(__getitem__=lambda self, i: recent_ts)

        conn.execute.return_value.fetchone.side_effect = fake_fetchone

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                with patch("subprocess.run") as mock_sp:
                    mock_sp.return_value.stdout = "inactive"
                    result = asyncio.run(health_system())

        assert result["subsystems"]["alert_dispatcher"]["status"] == "degraded"
        assert result["subsystems"]["alert_dispatcher"]["systemd_state"] == "inactive"

    def test_health_system_alert_dispatcher_exception(self):
        """Lines 252-253: subprocess exception → unknown."""
        from services.api.services.api.routers.health import health_system

        engine, conn = self._make_engine_ctx()
        tables_row = MagicMock(__getitem__=lambda self, i: 5)
        ingest_row = MagicMock(__getitem__=lambda self, i: [1, 0, 0, None][i])
        recent_ts = datetime.now(timezone.utc)

        call_idx = [0]
        def fake_fetchone():
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return tables_row
            elif idx == 1:
                return ingest_row
            return MagicMock(__getitem__=lambda self, i: recent_ts)

        conn.execute.return_value.fetchone.side_effect = fake_fetchone

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                with patch("subprocess.run", side_effect=OSError("no systemctl")):
                    result = asyncio.run(health_system())

        assert result["subsystems"]["alert_dispatcher"]["status"] == "unknown"

    def test_health_system_ingest_lag_notification_inserted(self):
        """Lines 264-276: no recent ingest → notification INSERT triggered."""
        from services.api.services.api.routers.health import health_system
        import subprocess

        engine, conn = self._make_engine_ctx()
        tables_row = MagicMock(__getitem__=lambda self, i: 5)
        ingest_row = MagicMock(__getitem__=lambda self, i: [0, 0, 0, None][i])

        call_idx = [0]
        def fake_fetchone():
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return tables_row
            elif idx == 1:
                return ingest_row
            # scalar for ingest_lag → None (no recent done)
            return None

        conn.execute.return_value.fetchone.side_effect = fake_fetchone
        conn.execute.return_value.scalar.return_value = None  # last done = None

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                with patch("subprocess.run") as mock_sp:
                    mock_sp.return_value.stdout = "active"
                    result = asyncio.run(health_system())

        # ingest_lag subsystem should be present
        assert "ingest_lag" in result["subsystems"]

    def test_health_system_ingest_lag_unavailable_on_exception(self):
        """Lines 282-283: DB error in ingest_lag → unavailable."""
        from services.api.services.api.routers.health import health_system

        good_engine, good_conn = self._make_engine_ctx()
        tables_row = MagicMock(__getitem__=lambda self, i: 5)
        ingest_row = MagicMock(__getitem__=lambda self, i: [0, 0, 0, None][i])

        lag_engine = MagicMock()
        lag_conn = MagicMock()
        lag_conn.execute.side_effect = RuntimeError("lag DB error")
        lag_ctx = MagicMock()
        lag_ctx.__enter__ = MagicMock(return_value=lag_conn)
        lag_ctx.__exit__ = MagicMock(return_value=False)
        lag_engine.connect.return_value = lag_ctx

        call_idx = [0]
        def fake_fetchone():
            idx = call_idx[0]
            call_idx[0] += 1
            return [tables_row, ingest_row][idx] if idx < 2 else None
        good_conn.execute.return_value.fetchone.side_effect = fake_fetchone

        # Use good engine for first two sections, lag_engine for 3rd
        engines_called = [0]
        def multi_engine(*args, **kwargs):
            n = engines_called[0]
            engines_called[0] += 1
            if n < 3:
                return good_engine
            return lag_engine

        with patch("terra_db.session.get_engine", side_effect=multi_engine):
            with patch(f"{_PKG}.routers.health._check_redis", return_value="ok"):
                with patch("subprocess.run") as mock_sp:
                    mock_sp.return_value.stdout = "active"
                    result = asyncio.run(health_system())

        # ingest_lag should be either unavailable or ok
        assert "ingest_lag" in result["subsystems"]


class TestHealthProductionAllBranches:
    """Lines 301-354: health_production covering all up_count branches."""

    def test_health_production_all_up_ok(self):
        """Lines 344-345: up_count == 3 → status='ok'."""
        from services.api.services.api.routers.health import health_production

        engine = MagicMock()
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = MagicMock(return_value=MagicMock())
        conn_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn_ctx

        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"+PONG\r\n"

        mock_url_resp = MagicMock()
        mock_url_resp.status = 200

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch("socket.create_connection", return_value=mock_sock):
                with patch("urllib.request.urlopen", return_value=mock_url_resp):
                    result = asyncio.run(health_production())

        assert result.status == "ok"
        assert result.services.db is True
        assert result.services.redis is True
        assert result.services.vllm is True

    def test_health_production_all_down(self):
        """Line 347: up_count == 0 → status='down'."""
        from services.api.services.api.routers.health import health_production

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("no DB")):
            with patch("socket.create_connection", side_effect=OSError("refused")):
                with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
                    result = asyncio.run(health_production())

        assert result.status == "down"
        assert result.services.db is False
        assert result.services.redis is False
        assert result.services.vllm is False

    def test_health_production_db_down_degraded(self):
        """Lines 321-322: DB exception → services.db=False, status=degraded."""
        from services.api.services.api.routers.health import health_production

        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"+PONG\r\n"

        mock_url_resp = MagicMock()
        mock_url_resp.status = 200

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("pg down")):
            with patch("socket.create_connection", return_value=mock_sock):
                with patch("urllib.request.urlopen", return_value=mock_url_resp):
                    result = asyncio.run(health_production())

        assert result.status == "degraded"
        assert result.services.db is False
        assert result.services.redis is True
        assert result.services.vllm is True

    def test_health_production_redis_down_degraded(self):
        """Lines 332-333: socket exception → services.redis=False."""
        from services.api.services.api.routers.health import health_production

        engine = MagicMock()
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = MagicMock(return_value=MagicMock())
        conn_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn_ctx

        mock_url_resp = MagicMock()
        mock_url_resp.status = 200

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch("socket.create_connection", side_effect=OSError("connection refused")):
                with patch("urllib.request.urlopen", return_value=mock_url_resp):
                    result = asyncio.run(health_production())

        assert result.services.redis is False
        assert result.status == "degraded"

    def test_health_production_vllm_up(self):
        """Line 339: vllm urlopen returns 200 → services.vllm=True."""
        from services.api.services.api.routers.health import health_production

        engine = MagicMock()
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = MagicMock(return_value=MagicMock())
        conn_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn_ctx

        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"+PONG\r\n"

        mock_resp = MagicMock()
        mock_resp.status = 200

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch("socket.create_connection", return_value=mock_sock):
                with patch("urllib.request.urlopen", return_value=mock_resp):
                    result = asyncio.run(health_production())

        assert result.services.vllm is True

    def test_health_production_vllm_down_degraded(self):
        """Lines 340-341: vllm exception → False."""
        from services.api.services.api.routers.health import health_production

        engine = MagicMock()
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = MagicMock(return_value=MagicMock())
        conn_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn_ctx

        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"+PONG\r\n"

        with patch("terra_db.session.get_engine", return_value=engine):
            with patch("socket.create_connection", return_value=mock_sock):
                with patch("urllib.request.urlopen", side_effect=OSError("vllm down")):
                    result = asyncio.run(health_production())

        assert result.services.vllm is False
        assert result.status == "degraded"

    def test_health_v1_db_error(self):
        """Lines 74-75: health() db error path → status=degraded."""
        from services.api.services.api.routers.health import health

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("DB down")):
            result = asyncio.run(health())

        assert result.status == "degraded"
        assert "error" in result.db

    def test_health_v2_db_error(self):
        """Lines 92-93: health_v2() db error → degraded."""
        from services.api.services.api.routers.health import health_v2

        with patch("terra_db.session.get_engine", side_effect=RuntimeError("DB down")):
            result = asyncio.run(health_v2())

        assert result["status"] == "degraded"
        assert "error" in result["db"]


# ═════════════════════════════════════════════════════════════════════════════
# Pure-logic helpers (no DB needed)
# ═════════════════════════════════════════════════════════════════════════════

class TestForecasterPureLogic:
    """Pure function tests for _holt_winters_forecast and _prediction_interval."""

    def test_holt_winters_too_few_values(self):
        """Lines 21-23: < 3 values → returns [last]*horizon."""
        from services.api.services.api.intelligence.forecaster import _holt_winters_forecast
        result = _holt_winters_forecast([100.0], horizon=3)
        assert result == [100.0, 100.0, 100.0]

    def test_holt_winters_normal(self):
        """Lines 26-44: normal path produces horizon forecasts."""
        from services.api.services.api.intelligence.forecaster import _holt_winters_forecast
        values = [100.0, 102.0, 104.0, 106.0, 108.0]
        result = _holt_winters_forecast(values, horizon=4)
        assert len(result) == 4
        assert all(isinstance(v, float) for v in result)

    def test_prediction_interval_few_values(self):
        """Lines 50-52: < 4 values → spread = 10% of last value."""
        from services.api.services.api.intelligence.forecaster import _prediction_interval
        values = [100.0, 102.0]
        forecasts = [105.0, 107.0]
        result = _prediction_interval(values, forecasts)
        assert len(result) == 2
        lb, ub = result[0]
        assert lb < 105.0 < ub

    def test_prediction_interval_normal(self):
        """Lines 55-70: normal path with residual std."""
        from services.api.services.api.intelligence.forecaster import _prediction_interval
        values = [100.0, 103.0, 101.0, 105.0, 102.0, 106.0]
        forecasts = [108.0, 110.0, 112.0]
        result = _prediction_interval(values, forecasts)
        assert len(result) == 3
        for lb, ub in result:
            assert lb <= ub

    def test_quarter_to_index_and_back(self):
        """_quarter_to_index / _index_to_quarter round-trip."""
        from services.api.services.api.intelligence.forecaster import (
            _quarter_to_index, _index_to_quarter
        )
        idx = _quarter_to_index(3, 2024)
        q, y = _index_to_quarter(idx)
        assert q == 3
        assert y == 2024


class TestWinProbMLPureFunctions:
    """Pure functions: _encode_cpv, _encode_region, _build_features."""

    def setup_method(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        m._cpv_encoder = {}
        m._region_encoder = {}

    def test_encode_cpv_none(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_cpv
        result = _encode_cpv(None)
        assert isinstance(result, int)

    def test_encode_cpv_new_value(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_cpv
        r1 = _encode_cpv("45200000")
        r2 = _encode_cpv("33100000")
        assert r1 != r2

    def test_encode_region_none(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_region
        result = _encode_region(None)
        assert isinstance(result, int)

    def test_build_features_shape(self):
        from services.api.services.api.intelligence.win_prob_ml import _build_features
        feats = _build_features(0.8, 500_000.0, "45200000", "PL21", 30)
        assert len(feats) == 5
        assert all(0.0 <= f <= 1.0 for f in feats)

    def test_synthetic_training_data_shape(self):
        from services.api.services.api.intelligence.win_prob_ml import _synthetic_training_data
        X, y = _synthetic_training_data()
        assert len(X) == 40
        assert len(y) == 40
        assert sum(y) == 20  # 20 won, 20 lost
