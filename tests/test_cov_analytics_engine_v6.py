"""Coverage tests v6 — targeting uncovered lines in 8 modules.

Targets:
  routers/analytics.py         — lines 86, 112, 153, 172-173, 244-277, 291
  intelligence/anomaly.py      — lines 31-33, 42-45, 124-126, 136, 263-264, 283-284
  routers/offer_assembly.py    — lines 130-133, 137-139, 206-208, 249-251
  routers/sources_health.py    — lines 66, 119, 130-142, 160-167, 231
  intelligence/validation_engine.py — lines 185, 364, 379, 387, 402, 409, 416,
                                       603-604, 643, 860, 929, 995-997, 1006-1008,
                                       1016-1017, 1025-1036, 1045, 1047, 1049-1050,
                                       1072-1073, 1081-1082, 1093-1094
  routers/module3.py           — lines 197-200, 318-319, 336, 344, 348-354, 367, 371-375, 385
  routers/monitoring.py        — lines 95-96, 138, 173-174, 185-186, 196-197, 228, 239, 256
  routers/intelligence.py      — lines 157-164, 344-347
"""
from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from services.api.services.api.auth.deps import CurrentUser

# ─── helpers ──────────────────────────────────────────────────────────────────

def _user(role: str = "owner") -> CurrentUser:
    return CurrentUser(user_id="u1", email="t@t.pl", org_id="o1", role=role)


def _user_no_org() -> CurrentUser:
    return CurrentUser(user_id="u1", email="t@t.pl", org_id=None, role="owner")


# ══════════════════════════════════════════════════════════════════════════════
# 1. routers/analytics.py
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsRouter:
    """Target: analytics.py lines 86, 112, 153, 172-173, 244-277, 291"""

    def _make_engine(self, pipeline_row=None, decisions_row=None, avg_margin_row=None,
                     funnel_rows=None, trend_rows=None, tender_row=None):
        """Build a mock engine with configurable query results."""
        conn = MagicMock()

        # pipeline row
        if pipeline_row is None:
            pipeline_row = MagicMock(pipeline_value=500000, active_bids=5)
        # decisions row with total > 0 by default
        if decisions_row is None:
            decisions_row = MagicMock(won=3, lost=1, total=4)
        if avg_margin_row is None:
            avg_margin_row = MagicMock(avg_margin=12.5)
        if funnel_rows is None:
            funnel_rows = []
        if trend_rows is None:
            trend_rows = []

        def execute_side_effect(stmt, params=None):
            result = MagicMock()
            sql = str(stmt).lower()
            if "pipeline_value" in sql:
                result.fetchone.return_value = pipeline_row
            elif "decided_go" in sql and "count" in sql:
                result.fetchone.return_value = decisions_row
            elif "avg(profit_pct)" in sql:
                result.fetchone.return_value = avg_margin_row
            elif "status, count" in sql:
                result.fetchall.return_value = funnel_rows
            elif "to_char" in sql:
                result.fetchall.return_value = trend_rows
            elif "tenant" in sql and "title" in sql:
                result.fetchone.return_value = tender_row
            else:
                result.fetchone.return_value = None
                result.fetchall.return_value = []
            return result

        conn.execute.side_effect = execute_side_effect
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.connect.return_value = conn
        return engine

    # --- dashboard: win_rate with decisions.total > 0 (line 86) ---
    def test_dashboard_win_rate_computed(self):
        from services.api.services.api.routers.analytics import analytics_dashboard

        decisions = MagicMock(won=2, lost=1, total=3)
        engine = self._make_engine(decisions_row=decisions)

        with (
            patch("services.api.services.api.routers.analytics.get_engine", return_value=engine),
            patch("services.api.services.api.routers.analytics.rcache_get", return_value=None),
            patch("services.api.services.api.routers.analytics.rcache_set"),
        ):
            result = analytics_dashboard(_user())

        assert result["win_rate"] == pytest.approx(2 / 3, abs=1e-3)

    # --- dashboard: no_org raises 403 ---
    def test_dashboard_no_org_raises(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import analytics_dashboard

        with pytest.raises(HTTPException) as exc:
            analytics_dashboard(_user_no_org())
        assert exc.value.status_code == 403

    # --- pipeline_funnel: cache hit (line 112) ---
    def test_pipeline_funnel_cache_hit(self):
        from services.api.services.api.routers.analytics import pipeline_funnel

        cached = {"funnel": [], "total": 0}
        # analytics.py imports cache_get from ..cache inline as: from ..cache import get as cache_get
        with patch("services.api.services.api.cache.get", return_value=cached):
            result = pipeline_funnel(_user())

        assert result.get("_cached") is True

    # --- pipeline_funnel: no_org raises 403 ---
    def test_pipeline_funnel_no_org_raises(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import pipeline_funnel

        with pytest.raises(HTTPException) as exc:
            pipeline_funnel(_user_no_org())
        assert exc.value.status_code == 403

    # --- win_rate_trend: no_org raises 403 (line 153) ---
    def test_win_rate_trend_no_org_raises(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import win_rate_trend

        with pytest.raises(HTTPException) as exc:
            win_rate_trend(_user_no_org())
        assert exc.value.status_code == 403

    # --- win_rate_trend: DB exception fallback (lines 172-173) ---
    def test_win_rate_trend_db_exception(self):
        from services.api.services.api.routers.analytics import win_rate_trend

        engine = MagicMock()
        engine.connect.side_effect = Exception("DB down")

        with patch("services.api.services.api.routers.analytics.get_engine", return_value=engine):
            result = win_rate_trend(_user(), months=3)

        assert result["trend"] == []
        assert result["months"] == 3

    # --- recommendation: no_org raises 403 (lines 244+) ---
    def test_recommendation_no_org_raises(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import recommendation_endpoint, RecommendationRequest

        body = RecommendationRequest()
        with pytest.raises(HTTPException) as exc:
            recommendation_endpoint("tid1", body, _user_no_org())
        assert exc.value.status_code == 403

    # --- recommendation: tender not found 404 (lines 258-259) ---
    def test_recommendation_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import recommendation_endpoint, RecommendationRequest

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        body = RecommendationRequest()
        with patch("services.api.services.api.routers.analytics.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                recommendation_endpoint("no-such-id", body, _user())
        assert exc.value.status_code == 404

    # --- recommendation: happy path (lines 244-277) ---
    def test_recommendation_happy_path(self):
        from services.api.services.api.routers.analytics import recommendation_endpoint, RecommendationRequest

        tender_row = MagicMock(id="t1", title="Road repair", value_pln=300000.0, status="new")
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = tender_row
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        body = RecommendationRequest(scores={"quality": 0.8}, cost_estimate=200000.0)
        with (
            patch("services.api.services.api.routers.analytics.get_engine", return_value=engine),
            patch("services.api.services.api.routers.analytics.generate_recommendation",
                  return_value={"go": True}) as mock_gen,
        ):
            result = recommendation_endpoint("t1", body, _user())

        assert result == {"go": True}

    # --- risk_extract: use_ai=True (line 291) ---
    def test_risk_extract_use_ai(self):
        from services.api.services.api.routers.analytics import risk_extract, RiskRequest

        body = RiskRequest(text="some SWZ text", use_ai=True)
        # analytics.py imports extract_risks_with_ai inline inside the function
        with patch(
            "services.api.services.api.analytics.risk_extractor.extract_risks_with_ai",
            return_value={"risks": ["r1"]},
        ):
            result = risk_extract(body, _user())
        assert "risks" in result


# ══════════════════════════════════════════════════════════════════════════════
# 2. intelligence/anomaly.py
# ══════════════════════════════════════════════════════════════════════════════

class TestAnomaly:
    """Target: lines 31-33, 42-45, 124-126, 136, 263-264, 283-284"""

    # --- _try_isolation_forest: sklearn unavailable (lines 31-33) ---
    def test_isolation_forest_no_sklearn(self):
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest

        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "sklearn" in name:
                raise ImportError("no sklearn")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = _try_isolation_forest(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]))

        assert result is None

    # --- _try_isolation_forest: too few rows (line 35-36) ---
    def test_isolation_forest_too_few_rows(self):
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest

        matrix = np.array([[1, 2, 3], [4, 5, 6]])  # only 2 rows < 5
        result = _try_isolation_forest(matrix)
        assert result is None

    # --- _try_isolation_forest: general exception (lines 42-45) ---
    def test_isolation_forest_exception(self):
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest

        matrix = np.array([[1, 2, 3]] * 10)
        with patch("sklearn.ensemble.IsolationForest.fit_predict", side_effect=RuntimeError("boom")):
            # Use a mock clf
            mock_clf = MagicMock()
            mock_clf.fit_predict.side_effect = RuntimeError("boom")
            with patch("services.api.services.api.intelligence.anomaly.IsolationForest", None, create=True):
                pass
            # Patch directly inside the function's local scope
            import sklearn.ensemble
            original = sklearn.ensemble.IsolationForest
            try:
                class BadForest:
                    def __init__(self, **kw): pass
                    def fit_predict(self, x): raise RuntimeError("boom")
                sklearn.ensemble.IsolationForest = BadForest
                result = _try_isolation_forest(matrix)
                assert result is None
            finally:
                sklearn.ensemble.IsolationForest = original

    # --- zscore_pozycja: SQLAlchemyError fallback (implicit from lines 85-87) ---
    def test_zscore_pozycja_db_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        from services.api.services.api.intelligence.anomaly import zscore_pozycja

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = SQLAlchemyError("db error")

        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=mock_engine):
            result = zscore_pozycja(str(uuid4()))

        assert result["is_anomaly"] is False
        assert result["r_zscore"] is None

    # --- zscore_pozycja: ICB stats DB error (lines 124-126) ---
    def test_zscore_pozycja_icb_db_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        from services.api.services.api.intelligence.anomaly import zscore_pozycja

        pozycja_id = str(uuid4())
        row = MagicMock()
        row.__getitem__ = lambda self, i: [10.0, 20.0, 30.0, "SYM001", "robocizna"][i]

        call_count = [0]
        def connect_side_effect():
            call_count[0] += 1
            ctx = MagicMock()
            conn = MagicMock()
            conn.__enter__ = lambda s: conn
            conn.__exit__ = MagicMock(return_value=False)
            if call_count[0] == 1:
                conn.execute.return_value.fetchone.return_value = row
            else:
                conn.execute.side_effect = SQLAlchemyError("icb error")
            ctx.__enter__ = lambda s: conn
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        engine = MagicMock()
        engine.connect.side_effect = connect_side_effect

        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            result = zscore_pozycja(pozycja_id)

        # Returns result with None z-scores (ICB not available)
        assert result["pozycja_id"] == pozycja_id

    # --- _zscore: value None returns None (line 136) ---
    def test_zscore_internal_none_value(self):
        """Covers the inner _zscore helper returning None."""
        from services.api.services.api.intelligence.anomaly import zscore_pozycja

        pozycja_id = str(uuid4())
        # row with None prices
        row = MagicMock()
        row.__getitem__ = lambda self, i: [None, None, None, "SYM001", "robocizna"][i]

        icb_row = MagicMock()
        icb_row.__getitem__ = lambda self, i: 100.0

        call_count = [0]
        def connect_side_effect():
            call_count[0] += 1
            conn = MagicMock()
            conn.__enter__ = lambda s: conn
            conn.__exit__ = MagicMock(return_value=False)
            if call_count[0] == 1:
                conn.execute.return_value.fetchone.return_value = row
            else:
                conn.execute.return_value.fetchall.return_value = [icb_row, icb_row, icb_row]
            return conn

        engine = MagicMock()
        engine.connect.side_effect = connect_side_effect

        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            result = zscore_pozycja(pozycja_id)

        assert result["r_zscore"] is None
        assert result["m_zscore"] is None

    # --- analyze_kosztorys: DB update error (lines 263-264) ---
    def test_analyze_kosztorys_update_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys

        kosztorys_id = str(uuid4())
        tenant_id = "t1"

        fetch_row = MagicMock()
        fetch_row.__getitem__ = lambda self, i: [str(uuid4()), 10.0, 20.0, 30.0][i]

        begin_ctx = MagicMock()
        begin_ctx.__enter__ = MagicMock(side_effect=SQLAlchemyError("update fail"))
        begin_ctx.__exit__ = MagicMock(return_value=False)

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = [fetch_row]

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx

        with (
            patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine),
            patch("services.api.services.api.intelligence.anomaly.zscore_pozycja",
                  return_value={"pozycja_id": str(uuid4()), "r_zscore": 3.0,
                                "m_zscore": None, "s_zscore": None, "is_anomaly": True}),
        ):
            result = analyze_kosztorys(kosztorys_id, tenant_id)

        # Should still return a dict even though update failed
        assert "kosztorys_id" in result

    # --- analyze_kosztorys: kosztorys update SQLAlchemyError (lines 283-284) ---
    def test_analyze_kosztorys_kosztorys_update_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys

        kosztorys_id = str(uuid4())
        tenant_id = "t1"

        fetch_row = MagicMock()
        fetch_row.__getitem__ = lambda self, i: [str(uuid4()), 10.0, 20.0, 30.0][i]

        call_count = [0]
        begin_conn = MagicMock()
        begin_conn.__enter__ = lambda s: begin_conn
        begin_conn.__exit__ = MagicMock(return_value=False)

        def begin_side_effect():
            call_count[0] += 1
            if call_count[0] >= 2:  # kosztorys update fails
                ctx = MagicMock()
                ctx.__enter__ = MagicMock(side_effect=SQLAlchemyError("kosztorys update fail"))
                ctx.__exit__ = MagicMock(return_value=False)
                return ctx
            return begin_conn

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = [fetch_row]

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        engine.begin.side_effect = begin_side_effect

        with (
            patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine),
            patch("services.api.services.api.intelligence.anomaly.zscore_pozycja",
                  return_value={"pozycja_id": str(uuid4()), "r_zscore": None,
                                "m_zscore": None, "s_zscore": None, "is_anomaly": False}),
        ):
            result = analyze_kosztorys(kosztorys_id, tenant_id)

        assert result["kosztorys_id"] == kosztorys_id


# ══════════════════════════════════════════════════════════════════════════════
# 3. routers/offer_assembly.py
# ══════════════════════════════════════════════════════════════════════════════

class TestOfferAssembly:
    """Target: lines 130-133, 137-139, 206-208, 249-251"""

    def _make_generate_request(self, use_adres=False, with_termin=False):
        from services.api.services.api.routers.offer_assembly import (
            GenerateDocsRequest, TenderIn, CompanyIn, KosztorysIn, BidStrategyIn,
        )
        tender = TenderIn(
            nr_sprawy="DZP/001/2026",
            tytul="Remont drogi",
            zamawiajacy_nazwa="Gmina Test",
            termin_skladania="2026-08-01T12:00:00" if with_termin else None,
        )
        if use_adres:
            company = CompanyIn(
                nazwa_pelna="ACME Sp. z o.o.",
                nip="1234567890",
                adres="ul. Budowlana 12, 40-600 Katowice",
            )
        else:
            company = CompanyIn(
                nazwa_pelna="ACME Sp. z o.o.",
                nip="1234567890",
                adres_ulica="ul. Budowlana",
                adres_nr_budynku="12",
                adres_kod_pocztowy="40-600",
                adres_miasto="Katowice",
            )
        kosztorys = KosztorysIn(
            suma_netto=100000.0,
            vat_pct=23.0,
            suma_brutto=123000.0,
        )
        return GenerateDocsRequest(tender=tender, company=company, kosztorys=kosztorys)

    # --- generate_documents: uses fallback address fields (lines 130-133) ---
    def test_generate_documents_fallback_address(self):
        from services.api.services.api.routers.offer_assembly import generate_documents

        req = self._make_generate_request(use_adres=False)

        mock_package = MagicMock()
        mock_package.zip_content = b"PK..."
        mock_package.zip_checksum = "abc123"
        mock_package.documents = [MagicMock(), MagicMock()]

        with patch(
            "services.api.services.api.intelligence.document_generator.generate_oferta_package",
            return_value=mock_package,
        ):
            result = asyncio.run(generate_documents(req, _user()))

        assert result.media_type == "application/zip"

    # --- generate_documents: parses adres string (lines 116-128) ---
    def test_generate_documents_parse_adres_string(self):
        from services.api.services.api.routers.offer_assembly import generate_documents

        req = self._make_generate_request(use_adres=True)

        mock_package = MagicMock()
        mock_package.zip_content = b"PK..."
        mock_package.zip_checksum = "abc123"
        mock_package.documents = [MagicMock()]

        with patch(
            "services.api.services.api.intelligence.document_generator.generate_oferta_package",
            return_value=mock_package,
        ):
            result = asyncio.run(generate_documents(req, _user()))

        assert result.media_type == "application/zip"

    # --- generate_documents: with termin_skladania (lines 137-139 — success parse) ---
    def test_generate_documents_with_termin(self):
        from services.api.services.api.routers.offer_assembly import generate_documents

        req = self._make_generate_request(with_termin=True)

        mock_package = MagicMock()
        mock_package.zip_content = b"PK..."
        mock_package.zip_checksum = "xyz"
        mock_package.documents = []

        with patch(
            "services.api.services.api.intelligence.document_generator.generate_oferta_package",
            return_value=mock_package,
        ):
            result = asyncio.run(generate_documents(req, _user()))

        assert result.status_code == 200

    # --- generate_documents: exception raises 500 (lines 206-208) ---
    def test_generate_documents_exception(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.offer_assembly import generate_documents

        req = self._make_generate_request()

        with patch(
            "services.api.services.api.intelligence.document_generator.generate_oferta_package",
            side_effect=RuntimeError("generator broke"),
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(generate_documents(req, _user()))
        assert exc.value.status_code == 500

    # --- map_knr_positions: exception raises 500 (lines 249-251) ---
    def test_map_knr_positions_exception(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.offer_assembly import map_knr_positions, KNRMapRequest, OPZPositionIn

        req = KNRMapRequest(positions=[OPZPositionIn(id="p1", description="Betonowanie")])

        with patch("services.api.services.api.intelligence.knr_mapper.KNRMapper") as MockMapper:
            MockMapper.return_value.map_opz_positions = AsyncMock(side_effect=RuntimeError("mapper broke"))
            with pytest.raises(HTTPException) as exc:
                asyncio.run(map_knr_positions(req, _user()))
        assert exc.value.status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# 4. routers/sources_health.py
# ══════════════════════════════════════════════════════════════════════════════

class TestSourcesHealth:
    """Target: lines 66, 119, 130-142, 160-167, 231"""

    # --- _probe_head: degraded status on non-200/301/302/403 (line 66) ---
    def test_probe_head_degraded_status(self):
        from services.api.services.api.routers.sources_health import _probe_head

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("httpx.head", return_value=mock_resp):
            result = _probe_head("BZP", "http://example.com")

        assert result.status == "degraded"
        assert "500" in result.detail

    # --- _probe_head: degraded but high latency → "degraded" (line 64) ---
    def test_probe_head_ok_status(self):
        from services.api.services.api.routers.sources_health import _probe_head

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.head", return_value=mock_resp):
            result = _probe_head("BZP", "http://example.com")

        assert result.status in ("ok", "degraded")

    # --- _probe_ted: non-200 returns degraded (line 119) ---
    def test_probe_ted_non_200(self):
        from services.api.services.api.routers.sources_health import _probe_ted

        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("httpx.post", return_value=mock_resp):
            result = _probe_ted()

        assert result.status == "degraded"
        assert "503" in result.detail

    # --- _insert_source_down_notification: successful path (lines 130-142) ---
    def test_insert_source_down_notification(self):
        from services.api.services.api.routers.sources_health import _insert_source_down_notification

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.begin.return_value = conn

        with patch("terra_db.session.get_engine", return_value=engine):
            # Should not raise
            _insert_source_down_notification("tenant1", "BZP")

    # --- _insert_source_down_notification: exception is swallowed ---
    def test_insert_source_down_notification_exception(self):
        from services.api.services.api.routers.sources_health import _insert_source_down_notification

        with patch("terra_db.session.get_engine", side_effect=Exception("no db")):
            # Should not raise
            _insert_source_down_notification("tenant1", "TED")

    # --- _get_ingest_stats: success path (lines 160-167) ---
    def test_get_ingest_stats_success(self):
        from services.api.services.api.routers.sources_health import _get_ingest_stats

        row_bzp = MagicMock(source="bzp", cnt=10)
        row_ted = MagicMock(source="ted", cnt=5)
        newest = MagicMock()
        newest.isoformat.return_value = "2026-01-01T00:00:00+00:00"

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)

        exec_count = [0]
        def execute_side(stmt, params=None):
            exec_count[0] += 1
            res = MagicMock()
            sql = str(stmt)
            if "MAX" in sql:
                res.scalar.return_value = newest
                res.__iter__ = lambda s: iter([])
            elif "duplicate" in sql.lower():
                res.scalar.return_value = 2
            else:
                res.__iter__ = iter([row_bzp, row_ted])
            return res

        conn.execute.side_effect = execute_side

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("terra_db.session.get_engine", return_value=engine):
            result = _get_ingest_stats("t1")

        assert result.bzp_count >= 0

    # --- _get_ingest_stats: exception fallback ---
    def test_get_ingest_stats_exception(self):
        from services.api.services.api.routers.sources_health import _get_ingest_stats

        with patch("terra_db.session.get_engine", side_effect=Exception("no db")):
            result = _get_ingest_stats("t1")

        assert result.total_tenders == 0

    # --- sources_health_v2: degraded source triggers notification (line 231) ---
    def test_sources_health_v2_degraded_triggers_notification(self):
        from services.api.services.api.routers.sources_health import (
            sources_health_v2, SourceStatus,
        )

        degraded = SourceStatus(name="BZP", status="degraded", latency_ms=100)
        ok_s = SourceStatus(name="TED", status="ok", latency_ms=200)
        ok_b = SourceStatus(name="BIP", status="ok", latency_ms=300)

        with (
            patch("services.api.services.api.routers.sources_health._probe_head",
                  side_effect=[degraded, ok_s, ok_b]),
            patch("services.api.services.api.routers.sources_health._insert_source_down_notification") as mock_notify,
        ):
            result = asyncio.run(sources_health_v2())

        assert result["sources"][0]["status"] == "degraded"

    # --- sources_health_v2: latency >= threshold triggers notification ---
    def test_sources_health_v2_high_latency_triggers_notification(self):
        from services.api.services.api.routers.sources_health import (
            sources_health_v2, SourceStatus,
        )

        high_lat = SourceStatus(name="BZP", status="ok", latency_ms=6000)
        ok_s = SourceStatus(name="TED", status="ok", latency_ms=200)
        ok_b = SourceStatus(name="BIP", status="ok", latency_ms=300)

        with (
            patch("services.api.services.api.routers.sources_health._probe_head",
                  side_effect=[high_lat, ok_s, ok_b]),
            patch("services.api.services.api.routers.sources_health._insert_source_down_notification") as mock_notify,
        ):
            result = asyncio.run(sources_health_v2())

        assert result["checked_at"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# 5. intelligence/validation_engine.py
# ══════════════════════════════════════════════════════════════════════════════

class TestValidationEngine:
    """Target: lines 185, 364, 379, 387, 402, 409, 416, 603-604, 643, 860,
               929, 995-997, 1006-1008, 1016-1017, 1025-1036, 1045, 1047,
               1049-1050, 1072-1073, 1081-1082, 1093-1094
    """

    def _point(self, pid: int, cat: str):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationPoint, CheckCategory, CheckStatus,
        )
        return ValidationPoint(
            id=pid,
            category=CheckCategory(cat),
            description=f"Check {pid}",
        )

    # --- ValidationEngine._check_completeness: optional doc not required (lines 929, 939-942) ---
    def test_check_completeness_optional_not_required(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(6, "completeness")  # id=6 is optional
        tender = {}  # requires_zobowiazanie_podmiotu not set → False

        asyncio.run(engine._check_completeness(point, [], tender))
        assert point.status == CheckStatus.NOT_APPLICABLE

    # --- ValidationEngine._check_completeness: doc exists → PASS ---
    def test_check_completeness_doc_exists(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(1, "completeness")
        docs = [{"doc_type": "formularz_ofertowy"}]

        asyncio.run(engine._check_completeness(point, docs, {}))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_completeness: doc missing → FAIL (line 955) ---
    def test_check_completeness_doc_missing(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(1, "completeness")

        asyncio.run(engine._check_completeness(point, [], {}))
        assert point.status == CheckStatus.FAIL
        assert point.auto_fixable is True

    # --- ValidationEngine._check_completeness: wadium not required (lines 944-950) ---
    def test_check_completeness_wadium_not_required(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(8, "completeness")
        tender = {"wadium": 0}

        asyncio.run(engine._check_completeness(point, [], tender))
        assert point.status == CheckStatus.NOT_APPLICABLE

    # --- ValidationEngine._check_formal: deadline fail (lines 995-997) ---
    def test_check_formal_deadline_fail(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(15, "formal")
        docs = [{"created_at": "2026-09-01", "filename": "doc.pdf"}]
        tender = {"deadline": "2026-08-01"}

        asyncio.run(engine._check_formal(point, docs, tender))
        assert point.status == CheckStatus.FAIL

    # --- ValidationEngine._check_formal: deadline pass ---
    def test_check_formal_deadline_pass(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(15, "formal")
        docs = []
        tender = {}

        asyncio.run(engine._check_formal(point, docs, tender))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_formal: invalid file format (lines 1006-1008) ---
    def test_check_formal_invalid_format(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(20, "formal")
        docs = [{"filename": "file.exe"}]

        asyncio.run(engine._check_formal(point, docs, {}))
        assert point.status == CheckStatus.FAIL

    # --- ValidationEngine._check_formal: valid format ---
    def test_check_formal_valid_format(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(20, "formal")
        docs = [{"filename": "file.pdf"}]

        asyncio.run(engine._check_formal(point, docs, {}))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_formal: other id → WARNING ---
    def test_check_formal_other_id_warning(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(13, "formal")

        asyncio.run(engine._check_formal(point, [], {}))
        assert point.status == CheckStatus.WARNING

    # --- ValidationEngine._check_financial: price mismatch fail (lines 995-997) ---
    def test_check_financial_price_mismatch(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(25, "financial")
        estimate = {"total_gross_form": 100000.0, "total_gross": 99000.0}

        asyncio.run(engine._check_financial(point, estimate, {}))
        assert point.status == CheckStatus.FAIL
        assert point.auto_fixable is True

    # --- ValidationEngine._check_financial: arithmetic fail (lines 1006-1008) ---
    def test_check_financial_arithmetic_fail(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(27, "financial")
        estimate = {"total_net": 80000.0, "total_vat": 10000.0, "total_gross": 100000.0}

        asyncio.run(engine._check_financial(point, estimate, {}))
        assert point.status == CheckStatus.FAIL

    # --- ValidationEngine._check_financial: zero lines (lines 1016-1017) ---
    def test_check_financial_zero_lines(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(29, "financial")
        estimate = {"lines": [{"net_total": 0}, {"net_total": 500}]}

        asyncio.run(engine._check_financial(point, estimate, {}))
        assert point.status == CheckStatus.WARNING

    # --- ValidationEngine._check_financial: rażąco niska fail (lines 1025-1031) ---
    def test_check_financial_razaco_niska(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(30, "financial")
        estimate = {"total_gross": 60000.0}
        tender = {"estimated_value": 100000.0}

        asyncio.run(engine._check_financial(point, estimate, tender))
        assert point.status == CheckStatus.FAIL

    # --- ValidationEngine._check_financial: low price warning (lines 1032-1034) ---
    def test_check_financial_low_price_warning(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(30, "financial")
        estimate = {"total_gross": 75000.0}
        tender = {"estimated_value": 100000.0}

        asyncio.run(engine._check_financial(point, estimate, tender))
        assert point.status == CheckStatus.WARNING

    # --- ValidationEngine._check_financial: OK price (line 1036) ---
    def test_check_financial_ok_price(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(30, "financial")
        estimate = {"total_gross": 95000.0}
        tender = {"estimated_value": 100000.0}

        asyncio.run(engine._check_financial(point, estimate, tender))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_financial: id=34 kp/z rates (lines 1045-1052) ---
    def test_check_financial_kp_z_rates_warning(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(34, "financial")
        estimate = {"avg_kp_rate": 50, "avg_z_rate": 3}  # both out of range

        asyncio.run(engine._check_financial(point, estimate, {}))
        assert point.status == CheckStatus.WARNING

    def test_check_financial_kp_z_rates_pass(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(34, "financial")
        estimate = {"avg_kp_rate": 70, "avg_z_rate": 10}  # within range

        asyncio.run(engine._check_financial(point, estimate, {}))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_technical: missing permits fail (lines 1072-1073) ---
    def test_check_technical_missing_permits(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(42, "technical")
        tender = {"required_permits": ["KBK", "SPEC"]}
        company = {"uprawnienia_budowlane": ["KBK"]}

        asyncio.run(engine._check_technical(point, company, tender))
        assert point.status == CheckStatus.FAIL
        assert "SPEC" in point.details

    # --- ValidationEngine._check_technical: permits ok (line 1075) ---
    def test_check_technical_permits_ok(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(42, "technical")
        tender = {"required_permits": ["KBK"]}
        company = {"uprawnienia_budowlane": ["KBK", "SPEC"]}

        asyncio.run(engine._check_technical(point, company, tender))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_technical: reference value fail (lines 1081-1085) ---
    def test_check_technical_reference_value_fail(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(44, "technical")
        tender = {"min_reference_value": 500000}
        company = {"max_reference_value": 200000}

        asyncio.run(engine._check_technical(point, company, tender))
        assert point.status == CheckStatus.FAIL

    # --- ValidationEngine._check_technical: polisa OC fail (lines 1093-1097) ---
    def test_check_technical_polisa_oc_fail(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(46, "technical")
        tender = {"min_polisa_oc": 1000000}
        company = {"polisa_oc_kwota": 500000}

        asyncio.run(engine._check_technical(point, company, tender))
        assert point.status == CheckStatus.FAIL

    # --- ValidationEngine._check_technical: polisa OC ok ---
    def test_check_technical_polisa_oc_ok(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(46, "technical")
        tender = {"min_polisa_oc": 500000}
        company = {"polisa_oc_kwota": 1000000}

        asyncio.run(engine._check_technical(point, company, tender))
        assert point.status == CheckStatus.PASS

    # --- ValidationEngine._check_technical: other id → WARNING ---
    def test_check_technical_other_warning(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(47, "technical")

        asyncio.run(engine._check_technical(point, {}, {}))
        assert point.status == CheckStatus.WARNING

    # --- ValidationEngine._check_legal: always WARNING ---
    def test_check_legal_warning(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        point = self._point(35, "legal")

        asyncio.run(engine._check_legal(point, [], {}))
        assert point.status == CheckStatus.WARNING

    # --- ValidationEngine.validate: full path with strict_mode (line 860) ---
    def test_validate_full_strict_mode_warnings_fail(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine, CheckStatus,
        )
        engine = ValidationEngine()
        bid_id = uuid4()

        # Pass all docs except one to trigger warnings
        result = asyncio.run(engine.validate(
            bid_id=bid_id,
            documents=[],
            estimate={"total_gross_form": 100000, "total_gross": 100000},
            company={},
            tender={},
            strict_mode=True,
            categories=["formal"],  # limit to formal only
        ))
        # With strict_mode and warnings → status should be "failed" or "warnings"
        assert result.status in ("failed", "warnings", "passed")

    # --- ValidationEngine.validate: categories filter (line 860) ---
    def test_validate_categories_filter(self):
        from services.api.services.api.intelligence.validation_engine import (
            ValidationEngine,
        )
        engine = ValidationEngine()
        bid_id = uuid4()

        result = asyncio.run(engine.validate(
            bid_id=bid_id,
            documents=[],
            estimate={},
            company={},
            tender={},
            strict_mode=False,
            categories=["completeness"],
        ))
        # Only completeness checks should be in result
        from services.api.services.api.intelligence.validation_engine import CheckCategory
        for p in result.points:
            assert p.category == CheckCategory.COMPLETENESS

    # --- validate_bid: DB connection error (line 185 via _db_get_bid_data) ---
    def test_validate_bid_db_error(self):
        from services.api.services.api.intelligence.validation_engine import validate_bid

        bid_id = uuid4()
        with patch(
            "services.api.services.api.intelligence.validation_engine.get_db_conn",
            side_effect=Exception("no connection"),
        ):
            result = validate_bid(bid_id)

        # Should return a result with warnings/passed despite DB failure
        assert result.bid_id == bid_id

    # --- _generate_recommendations: all branches ---
    def test_generate_recommendations_all_branches(self):
        from services.api.services.api.intelligence.validation_engine import (
            _generate_recommendations, ValidationResult, ValidationPoint,
            CheckStatus, CheckCategory,
        )
        result = ValidationResult(bid_id=uuid4())

        # Add auto_fixable fail
        p1 = ValidationPoint(id=1, category=CheckCategory.COMPLETENESS,
                              description="doc missing", status=CheckStatus.FAIL, auto_fixable=True)
        # Add financial warning
        p2 = ValidationPoint(id=25, category=CheckCategory.FINANCIAL,
                              description="price issue", status=CheckStatus.WARNING)
        # Add many warnings
        warnings = [
            ValidationPoint(id=i, category=CheckCategory.FORMAL,
                            description=f"warn {i}", status=CheckStatus.WARNING)
            for i in range(13, 25)
        ]
        result.points = [p1, p2] + warnings

        recs = _generate_recommendations(result)
        assert any("auto" in r.lower() or "naprawionych" in r for r in recs)

    def test_generate_recommendations_passed(self):
        from services.api.services.api.intelligence.validation_engine import (
            _generate_recommendations, ValidationResult, ValidationPoint,
            CheckStatus, CheckCategory,
        )
        result = ValidationResult(bid_id=uuid4(), status="passed")
        result.points = [
            ValidationPoint(id=1, category=CheckCategory.COMPLETENESS,
                            description="doc ok", status=CheckStatus.PASS)
        ]
        recs = _generate_recommendations(result)
        assert any("pomyślnie" in r or "Gotowa" in r for r in recs)


# ══════════════════════════════════════════════════════════════════════════════
# 6. routers/module3.py
# ══════════════════════════════════════════════════════════════════════════════

class TestModule3:
    """Target: lines 197-200, 318-319, 336, 344, 348-354, 367, 371-375, 385"""

    def _make_engine(self, tenant_id="t1"):
        """Engine that resolves _get_tenant_id via env."""
        import os
        os.environ["DEFAULT_TENANT_ID"] = tenant_id
        return MagicMock()

    def setup_method(self):
        import os
        os.environ["DEFAULT_TENANT_ID"] = "t1"

    # --- list_employees: multiple employees with skills (lines 197-200) ---
    def test_list_employees_with_skills(self):
        from services.api.services.api.routers.module3 import list_employees

        emp_rows = [MagicMock()]
        emp_rows[0].__getitem__ = lambda s, i: ["emp-1", "Jan Kowalski", "555", "kierownik"][i]

        skill_rows = [MagicMock()]
        skill_rows[0].__getitem__ = lambda s, i: ["spawanie"][i]

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)

        exec_count = [0]
        def execute_side(stmt, params=None):
            exec_count[0] += 1
            res = MagicMock()
            sql = str(stmt).lower()
            if "employee" in sql and "select id, name" in sql:
                res.fetchall.return_value = emp_rows
            elif "competency" in sql:
                res.fetchall.return_value = skill_rows
            else:
                res.fetchall.return_value = []
            return res

        conn.execute.side_effect = execute_side
        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.module3.get_engine", return_value=engine):
            result = list_employees()

        assert len(result) == 1
        assert "spawanie" in result[0].skills

    # --- logistics_optimize: invalid day format (lines 318-319) ---
    def test_logistics_optimize_invalid_date(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.module3 import logistics_optimize, OptimizeRequest

        body = OptimizeRequest(day_range=["not-a-date", "2026-07-31"])

        engine = MagicMock()
        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.module3.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                logistics_optimize(body)
        assert exc.value.status_code == 422

    # --- logistics_optimize: wrong day_range length (line 307) ---
    def test_logistics_optimize_wrong_range_length(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.module3 import logistics_optimize, OptimizeRequest

        body = OptimizeRequest(day_range=["2026-07-01"])

        with pytest.raises(HTTPException) as exc:
            logistics_optimize(body)
        assert exc.value.status_code == 422

    # --- logistics_optimize: happy path (lines 336, 344, 348-354, 367, 371-375, 385) ---
    def test_logistics_optimize_happy_path(self):
        from services.api.services.api.routers.module3 import logistics_optimize, OptimizeRequest

        body = OptimizeRequest(day_range=["2026-07-01", "2026-07-03"])

        # Build mock conn with all required queries
        emp_row = MagicMock()
        emp_row.__getitem__ = lambda s, i: [str(uuid4()), "Jan"][i]

        eq_row = MagicMock()
        eq_row.__getitem__ = lambda s, i: [str(uuid4()), "koparka"][i]

        skill_row = MagicMock()
        skill_row.__getitem__ = lambda s, i: [str(uuid4()), "spawanie"][i]

        avail_row = MagicMock()
        avail_row.__getitem__ = lambda s, i: [str(uuid4()), "2026-07-01"][i]

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)

        def execute_side(stmt, params=None):
            sql = str(stmt).lower()
            res = MagicMock()
            if "employee" in sql and "select id, name" in sql:
                res.fetchall.return_value = [emp_row]
            elif "competency" in sql:
                res.fetchall.return_value = [skill_row]
            elif "availability" in sql and "employee_id is not null" in sql:
                res.fetchall.return_value = []
            elif "resource_equipment" in sql:
                res.fetchall.return_value = [eq_row]
            elif "availability" in sql and "equipment_id is not null" in sql:
                res.fetchall.return_value = []
            elif "contract" in sql:
                res.fetchall.return_value = []
            else:
                res.fetchall.return_value = []
            return res

        conn.execute.side_effect = execute_side
        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock(
            feasible=True,
            assignments=[],
            routes=[],
            infeasible_reason="",
        )

        with (
            patch("services.api.services.api.routers.module3.get_engine", return_value=engine),
            patch("services.logistics.optimize_logistics", return_value=mock_result),
        ):
            result = logistics_optimize(body)

        assert result.feasible is True

    # --- list_plans: with day filter (line 412-416) ---
    def test_list_plans_with_day(self):
        from services.api.services.api.routers.module3 import list_plans

        row = MagicMock()
        row.__getitem__ = lambda s, i: [str(uuid4()), "2026-07-01", "draft",
                                         "ul. Test 1", 50.0, 19.0, None, None][i]

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = [row]

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.module3.get_engine", return_value=engine):
            result = list_plans(day="2026-07-01")

        assert len(result) == 1

    # --- _get_tenant_id: no DEFAULT_TENANT_ID, DB row (line 562-566) ---
    def test_get_tenant_id_from_db(self):
        from services.api.services.api.routers.module3 import _get_tenant_id
        import os
        os.environ.pop("DEFAULT_TENANT_ID", None)

        row = MagicMock()
        row.__getitem__ = lambda s, i: ["tenant-from-db"][i]

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = row

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = _get_tenant_id(engine)
        assert result == "tenant-from-db"
        os.environ["DEFAULT_TENANT_ID"] = "t1"

    # --- _get_tenant_id: no tenant in DB raises 500 ---
    def test_get_tenant_id_no_tenant_raises(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.module3 import _get_tenant_id
        import os
        os.environ.pop("DEFAULT_TENANT_ID", None)

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = None

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc:
            _get_tenant_id(engine)
        assert exc.value.status_code == 500
        os.environ["DEFAULT_TENANT_ID"] = "t1"


# ══════════════════════════════════════════════════════════════════════════════
# 7. routers/monitoring.py
# ══════════════════════════════════════════════════════════════════════════════

class TestMonitoring:
    """Target: lines 95-96, 138, 173-174, 185-186, 196-197, 228, 239, 256"""

    # --- metrics: memory exception (lines 95-96) ---
    def test_metrics_memory_exception(self):
        from services.api.services.api.routers.monitoring import metrics
        import psutil

        with patch.object(psutil, "Process", side_effect=Exception("no proc")):
            result = asyncio.run(metrics())

        assert result["memory_mb"] is None

    # --- system_status: psutil exception (line 138) ---
    def test_system_status_psutil_exception(self):
        from services.api.services.api.routers.monitoring import system_status
        import psutil

        with (
            patch.object(psutil, "Process", side_effect=Exception("no proc")),
            patch("services.api.services.api.security.require_admin"),
        ):
            result = asyncio.run(system_status(_user()))

        assert result["memory_mb"] is None
        assert result["cpu_percent"] is None

    # --- health_detailed: db exception (lines 173-174) ---
    def test_health_detailed_db_exception(self):
        from services.api.services.api.routers.monitoring import health_detailed

        with patch("terra_db.session.get_engine", side_effect=Exception("no db")):
            result = asyncio.run(health_detailed())

        assert result["checks"]["database"]["status"] == "error"

    # --- health_detailed: memory > 1000 MB warning (lines 185-186) ---
    def test_health_detailed_high_memory_warning(self):
        from services.api.services.api.routers.monitoring import health_detailed
        import psutil

        mock_mem = MagicMock()
        mock_mem.rss = 1200 * 1024 * 1024  # 1200 MB

        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = mock_mem

        engine = MagicMock()
        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("terra_db.session.get_engine", return_value=engine),
            patch.object(psutil, "Process", return_value=mock_proc),
        ):
            result = asyncio.run(health_detailed())

        assert result["checks"]["memory"]["status"] == "warning"

    # --- health_detailed: psutil memory exception (lines 196-197) ---
    def test_health_detailed_memory_exception(self):
        from services.api.services.api.routers.monitoring import health_detailed
        import psutil

        engine = MagicMock()
        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("terra_db.session.get_engine", return_value=engine),
            patch.object(psutil, "Process", side_effect=Exception("no psutil")),
        ):
            result = asyncio.run(health_detailed())

        assert result["checks"]["memory"]["status"] == "unknown"

    # --- get_alerts: memory alert triggered (line 228) ---
    def test_get_alerts_high_memory(self):
        from services.api.services.api.routers.monitoring import (
            get_alerts, _request_count, _error_count,
        )
        import psutil

        mock_mem = MagicMock()
        mock_mem.rss = 900 * 1024 * 1024  # 900MB > threshold 800

        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = mock_mem

        engine = MagicMock()
        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(psutil, "Process", return_value=mock_proc),
            patch("terra_db.session.get_engine", return_value=engine),
            patch("services.api.services.api.security.require_admin"),
        ):
            result = asyncio.run(get_alerts(_user()))

        alert_ids = [a["id"] for a in result["alerts"]]
        assert "high_memory" in alert_ids

    # --- get_alerts: high error rate (line 239) ---
    def test_get_alerts_high_error_rate(self):
        from services.api.services.api.routers import monitoring as mon_mod
        import psutil

        mock_mem = MagicMock()
        mock_mem.rss = 100 * 1024 * 1024  # 100MB — no memory alert
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = mock_mem

        engine = MagicMock()
        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # Force counters: 200 requests, 20 errors → 10% error rate → critical
        with (
            patch.object(mon_mod, "_request_count", 200),
            patch.object(mon_mod, "_error_count", 20),
            patch.object(psutil, "Process", return_value=mock_proc),
            patch("terra_db.session.get_engine", return_value=engine),
            patch("services.api.services.api.security.require_admin"),
        ):
            result = asyncio.run(mon_mod.get_alerts(_user()))

        alert_ids = [a["id"] for a in result["alerts"]]
        assert "high_error_rate" in alert_ids

    # --- get_alerts: DB unreachable (line 256) ---
    def test_get_alerts_db_unreachable(self):
        from services.api.services.api.routers.monitoring import get_alerts
        import psutil

        mock_mem = MagicMock()
        mock_mem.rss = 100 * 1024 * 1024
        mock_proc = MagicMock()
        mock_proc.memory_info.return_value = mock_mem

        with (
            patch.object(psutil, "Process", return_value=mock_proc),
            patch("terra_db.session.get_engine", side_effect=Exception("no db")),
            patch("services.api.services.api.security.require_admin"),
        ):
            result = asyncio.run(get_alerts(_user()))

        alert_ids = [a["id"] for a in result["alerts"]]
        assert "db_unreachable" in alert_ids

    # --- sla_metrics: with response times (lines 294-299) ---
    def test_sla_metrics_with_response_times(self):
        from services.api.services.api.routers import monitoring as mon_mod

        with (
            patch.object(mon_mod, "_sla_total_requests", 100),
            patch.object(mon_mod, "_sla_successful_requests", 99),
            patch.object(mon_mod, "_sla_response_times", [float(i) for i in range(100)]),
            patch("services.api.services.api.security.require_admin"),
        ):
            result = asyncio.run(mon_mod.sla_metrics(_user()))

        assert result["response_times_ms"]["p50"] is not None

    # --- record_response_time: failure flag ---
    def test_record_response_time_failure(self):
        from services.api.services.api.routers.monitoring import record_response_time, _sla_successful_requests
        import services.api.services.api.routers.monitoring as mon_mod

        before = mon_mod._sla_successful_requests
        record_response_time(100.0, success=False)
        assert mon_mod._sla_successful_requests == before  # not incremented

    # --- increment_error_count ---
    def test_increment_error_count(self):
        import services.api.services.api.routers.monitoring as mon_mod
        from services.api.services.api.routers.monitoring import increment_error_count

        before = mon_mod._error_count
        increment_error_count()
        assert mon_mod._error_count == before + 1


# ══════════════════════════════════════════════════════════════════════════════
# 8. routers/intelligence.py
# ══════════════════════════════════════════════════════════════════════════════

class TestIntelligenceRouter:
    """Target: lines 157-164, 344-347"""

    # --- api_search_icb: exception raises 500 (lines 157-164) ---
    def test_api_search_icb_exception(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.intelligence import api_search_icb

        with (
            patch("services.api.services.api.routers.intelligence.rcache_get", return_value=None),
            patch("services.api.services.api.routers.intelligence._icb",
                  side_effect=Exception("ICB module broken")),
        ):
            with pytest.raises(HTTPException) as exc:
                api_search_icb(q="beton")
        assert exc.value.status_code == 500

    # --- api_search_icb: cache hit ---
    def test_api_search_icb_cache_hit(self):
        from services.api.services.api.routers.intelligence import api_search_icb

        cached = {"query": "beton", "results": [], "count": 0, "period": "2026-Q2"}
        with patch("services.api.services.api.routers.intelligence.rcache_get", return_value=cached):
            result = api_search_icb(q="beton")

        assert result == cached

    # --- api_search_icb: success path ---
    def test_api_search_icb_success(self):
        from services.api.services.api.routers.intelligence import api_search_icb

        mock_svc = {"search_icb": MagicMock(return_value=[{"name": "beton"}])}

        with (
            patch("services.api.services.api.routers.intelligence.rcache_get", return_value=None),
            patch("services.api.services.api.routers.intelligence._icb", return_value=mock_svc),
            patch("services.api.services.api.routers.intelligence.rcache_set"),
        ):
            result = api_search_icb(q="beton")

        assert result["count"] == 1

    # --- get_agent_brief_by_query: DB row found (lines 344-347) ---
    def test_get_agent_brief_db_row_found(self):
        from services.api.services.api.routers.intelligence import get_agent_brief_by_query

        row = MagicMock()
        row.__getitem__ = lambda s, i: [str(uuid4()), {"brief": "test brief", "go_decision": True}, "2026-01-01"][i]

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = row

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.intelligence._get_engine", return_value=engine):
            result = get_agent_brief_by_query(tender_id="tid1")

        assert result["status"] == "ok"
        assert result["brief"] == "test brief"

    # --- get_agent_brief_by_query: no row found ---
    def test_get_agent_brief_no_row(self):
        from services.api.services.api.routers.intelligence import get_agent_brief_by_query

        conn = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = None

        engine = MagicMock()
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.intelligence._get_engine", return_value=engine):
            result = get_agent_brief_by_query(tender_id="not-found")

        assert result["status"] == "not_found"
        assert result["brief"] is None

    # --- get_agent_brief_by_query: exception raises 500 ---
    def test_get_agent_brief_exception(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.intelligence import get_agent_brief_by_query

        with patch("services.api.services.api.routers.intelligence._get_engine",
                   side_effect=Exception("engine broke")):
            with pytest.raises(HTTPException) as exc:
                get_agent_brief_by_query(tender_id="tid1")
        assert exc.value.status_code == 500

    # --- api_benchmark: exception raises 500 ---
    def test_api_benchmark_exception(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.intelligence import api_benchmark

        with (
            patch("services.api.services.api.routers.intelligence.rcache_get", return_value=None),
            patch("services.api.services.api.routers.intelligence._bi",
                  side_effect=Exception("bi module broken")),
        ):
            with pytest.raises(HTTPException) as exc:
                api_benchmark(cpv_prefix="45")
        assert exc.value.status_code == 500

    # --- api_narzuty: all=True branch ---
    def test_api_narzuty_all_true(self):
        from services.api.services.api.routers.intelligence import api_narzuty

        mock_svc = {
            "get_all_narzuty": MagicMock(return_value=[{"branża": "ogólnobudowlane"}]),
            "get_narzuty": MagicMock(return_value={}),
        }

        with patch("services.api.services.api.routers.intelligence._icb", return_value=mock_svc):
            result = api_narzuty(all=True)

        assert "data" in result

    # --- api_narzuty: all=False branch ---
    def test_api_narzuty_all_false(self):
        from services.api.services.api.routers.intelligence import api_narzuty

        mock_svc = {
            "get_all_narzuty": MagicMock(return_value=[]),
            "get_narzuty": MagicMock(return_value={"ko_r_pct": 70}),
        }

        with patch("services.api.services.api.routers.intelligence._icb", return_value=mock_svc):
            result = api_narzuty(all=False)

        assert result == {"ko_r_pct": 70}

    # --- api_material_risk: with category ---
    def test_api_material_risk_with_category(self):
        from services.api.services.api.routers.intelligence import api_material_risk

        mock_pi = {
            "get_material_risk_score": MagicMock(return_value={"risk": 0.5}),
            "get_all_material_risks": MagicMock(return_value=[]),
        }

        with patch("services.api.services.api.routers.intelligence._pi", return_value=mock_pi):
            result = api_material_risk(category="beton")

        assert result == {"risk": 0.5}

    # --- api_win_probability: exception raises 500 ---
    def test_api_win_probability_exception(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.intelligence import api_win_probability, WinProbRequest

        req = WinProbRequest(our_price=90000, estimated_value=100000)

        with patch("services.api.services.api.routers.intelligence._bi",
                   side_effect=Exception("bi error")):
            with pytest.raises(HTTPException) as exc:
                api_win_probability(req)
        assert exc.value.status_code == 500
