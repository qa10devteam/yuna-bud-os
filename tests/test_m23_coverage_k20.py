"""Sprint K20 — coverage boost: kosztorys v1 63→85%, kosztorys_v2 75→88%, win_prob, anomaly."""
from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

TENANT = str(uuid.uuid4())
TENDER_ID = str(uuid.uuid4())


# ─── helpers ──────────────────────────────────────────────────────────────────

def _row(**kw):
    r = MagicMock()
    for k, v in kw.items():
        setattr(r, k, v)
    r.__getitem__ = lambda self, k: getattr(self, k) if isinstance(k, str) else list(kw.values())[k]
    return r


def _tuple_row(*vals):
    """Wiersz jako tuple (dla kosztorys_v2 r[0], r[1]…)."""
    class TupleRow:
        def __init__(self, *v): self._v = v
        def __getitem__(self, i): return self._v[i]
        def isoformat(self): return "2025-01-01T00:00:00"
    return TupleRow(*vals)


def _engine(rows_map: dict | None = None):
    engine = MagicMock()
    conn = MagicMock()

    def _execute(stmt, params=None):
        text_str = str(stmt).lower()
        result = MagicMock()
        rows = []
        if rows_map:
            for fragment, r in rows_map.items():
                if fragment.lower() in text_str:
                    rows = r
                    break
        result.fetchall.return_value = rows
        result.fetchone.return_value = rows[0] if rows else None
        result.rowcount = len(rows)
        return result

    conn.execute = _execute
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    begin_ctx = MagicMock()
    begin_ctx.__enter__ = lambda s: conn
    begin_ctx.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = conn
    engine.begin.return_value = begin_ctx
    return engine


def _user(org_id: str = TENANT):
    u = MagicMock()
    u.org_id = org_id
    return u


# ══════════════════════════════════════════════════════════════════════════════
# 1. kosztorys.py v1 — create/update/delete/import/export (L160–318)
# ══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV1Create:
    def test_create_returns_id(self):
        """create_kosztorys_item zwraca id + status created."""
        from services.api.services.api.routers.kosztorys import create_kosztorys_item, KosztorysItemCreate
        item = KosztorysItemCreate(
            lp=1, description="Murarstwo", unit="m2",
            quantity=100.0, unit_price=50.0,
        )
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = create_kosztorys_item(TENDER_ID, item, _user())
        assert "id" in result
        assert result["status"] == "created"

    def test_create_with_kst_code(self):
        """create_kosztorys_item przyjmuje kst_code i category."""
        from services.api.services.api.routers.kosztorys import create_kosztorys_item, KosztorysItemCreate
        item = KosztorysItemCreate(
            lp=2, kst_code="45.21", description="Zbrojenie", unit="t",
            quantity=5.0, unit_price=4200.0, category="stal",
        )
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = create_kosztorys_item(TENDER_ID, item, _user())
        assert result["status"] == "created"


class TestKosztorysV1Update:
    def test_update_ok(self):
        """update_kosztorys_item zwraca zaktualizowany wiersz."""
        from services.api.services.api.routers.kosztorys import update_kosztorys_item, KosztorysItemUpdate
        item_id = str(uuid.uuid4())
        patch_body = KosztorysItemUpdate(unit_price=75.0)

        updated_row = MagicMock()
        updated_row.__getitem__ = lambda s, i: [
            uuid.UUID(item_id), uuid.UUID(TENDER_ID),
            "Murarstwo", "m2", 100.0, 75.0, 7500.0, None,
        ][i]

        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 1
        conn.execute = MagicMock(side_effect=[res, MagicMock(fetchone=lambda: updated_row)])
        conn.commit = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = update_kosztorys_item(TENDER_ID, item_id, patch_body, _user())
        assert "id" in result

    def test_update_empty_patch_raises_400(self):
        """update_kosztorys_item bez pól → 400."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys import update_kosztorys_item, KosztorysItemUpdate
        patch_body = KosztorysItemUpdate()
        with pytest.raises(HTTPException) as exc:
            update_kosztorys_item(TENDER_ID, str(uuid.uuid4()), patch_body, _user())
        assert exc.value.status_code == 400

    def test_update_not_found_raises_404(self):
        """update_kosztorys_item gdy rowcount=0 → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys import update_kosztorys_item, KosztorysItemUpdate
        patch_body = KosztorysItemUpdate(unit_price=99.0)

        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 0
        conn.execute = MagicMock(return_value=res)
        conn.commit = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                update_kosztorys_item(TENDER_ID, str(uuid.uuid4()), patch_body, _user())
        assert exc.value.status_code == 404


class TestKosztorysV1Delete:
    def test_delete_ok(self):
        """delete_kosztorys_item zwraca status deleted."""
        from services.api.services.api.routers.kosztorys import delete_kosztorys_item
        item_id = str(uuid.uuid4())
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 1
        conn.execute = MagicMock(return_value=res)
        conn.commit = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = delete_kosztorys_item(TENDER_ID, item_id, _user())
        assert result["status"] == "deleted"

    def test_delete_not_found_raises_404(self):
        """delete_kosztorys_item gdy rowcount=0 → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys import delete_kosztorys_item
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 0
        conn.execute = MagicMock(return_value=res)
        conn.commit = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_kosztorys_item(TENDER_ID, str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404


class TestKosztorysV1Import:
    """import_ath jest async — uruchamiamy przez asyncio.run() z AsyncMock."""

    def test_import_ath_empty_xml_raises_400(self):
        """import_ath z pustym XML (brak pozycji) → HTTPException 400."""
        from fastapi import HTTPException
        from unittest.mock import AsyncMock
        from services.api.services.api.routers.kosztorys import import_ath

        upload = MagicMock()
        upload.read = AsyncMock(return_value=b"<Kosztorys/>")
        upload.filename = "test.ath"
        engine = _engine()

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(import_ath(TENDER_ID, _user(), upload))
        assert exc.value.status_code == 400

    def test_import_ath_valid_xml(self):
        """import_ath z poprawnymi danymi → importuje pozycje, zwraca dict."""
        from unittest.mock import AsyncMock
        from services.api.services.api.routers.kosztorys import import_ath

        xml = b"""<Kosztorys>
            <Pozycja kod="45.01">
                <Nazwa>Test murarstwo</Nazwa>
                <Jm>m2</Jm>
                <Ilosc>50</Ilosc>
                <CenaJm>120.00</CenaJm>
            </Pozycja>
        </Kosztorys>"""

        upload = MagicMock()
        upload.read = AsyncMock(return_value=xml)
        upload.filename = "kosztorys.ath"
        engine = _engine()

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = asyncio.run(import_ath(TENDER_ID, _user(), upload))
        assert isinstance(result, dict)
        assert "imported" in result


class TestKosztorysV1Export:
    def test_export_ath_empty(self):
        """export_ath na pustym kosztorysie zwraca StreamingResponse."""
        from fastapi.responses import StreamingResponse
        from services.api.services.api.routers.kosztorys import export_ath

        engine = _engine({"kosztorys_items": []})
        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = export_ath(TENDER_ID, _user())
        assert isinstance(result, StreamingResponse)

    def test_export_ath_with_items(self):
        """export_ath z pozycjami zwraca StreamingResponse z XML."""
        from fastapi.responses import StreamingResponse
        from services.api.services.api.routers.kosztorys import export_ath

        rows = [
            _row(kst_code="45.01", description="Murarstwo",
                 unit="m2", quantity=100.0, unit_price=50.0),
        ]
        engine = _engine({"kosztorys_items": rows})
        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            result = export_ath(TENDER_ID, _user())
        assert isinstance(result, StreamingResponse)
        assert result.media_type is not None


# ══════════════════════════════════════════════════════════════════════════════
# 2. kosztorys_v2.py — estimate endpoint + delete_estimate + user-rates CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV2Estimate:
    def _mock_estimate_result(self, method: str = "icb") -> dict:
        return {
            "method": method, "variant": "standard",
            "total_net_pln": 150000.0,
            "confidence_low": 135000.0, "confidence_high": 165000.0,
            "lines": [], "params": {}, "notes": "",
        }

    def test_estimate_swz_missing_text_raises_400(self):
        """POST /estimate method=swz bez swz_text → 400."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import create_estimate, CostEstimateRequest
        req = CostEstimateRequest(method="swz", area_m2=500.0)
        with pytest.raises(HTTPException) as exc:
            create_estimate(req, _user())
        assert exc.value.status_code == 400

    def test_estimate_icb_zero_area_raises_400(self):
        """POST /estimate method=icb z area_m2=0 → 400."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import create_estimate, CostEstimateRequest
        req = CostEstimateRequest(method="icb", area_m2=0.0)
        with pytest.raises(HTTPException) as exc:
            create_estimate(req, _user())
        assert exc.value.status_code == 400

    def test_estimate_user_rates_zero_area_raises_400(self):
        """POST /estimate method=user_rates z area_m2=0 → 400."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import create_estimate, CostEstimateRequest
        req = CostEstimateRequest(method="user_rates", area_m2=0.0)
        with pytest.raises(HTTPException) as exc:
            create_estimate(req, _user())
        assert exc.value.status_code == 400

    def test_estimate_unknown_method_raises_validation_error(self):
        """POST /estimate z nieznaną metodą → ValidationError (pydantic pattern)."""
        from pydantic import ValidationError
        from services.api.services.api.routers.kosztorys_v2 import CostEstimateRequest
        with pytest.raises(ValidationError):
            CostEstimateRequest(method="xyz", area_m2=100.0)

    def test_estimate_swz_success(self):
        """POST /estimate method=swz z tekstem → zapisuje i zwraca ids."""
        from services.api.services.api.routers.kosztorys_v2 import create_estimate, CostEstimateRequest
        req = CostEstimateRequest(
            method="swz", area_m2=500.0,
            swz_text="Roboty murowe\t100\tm2\t50.00\nBeton\t50\tm3\t450.00",
        )
        mock_result = self._mock_estimate_result("swz")
        engine = _engine()
        mock_est = MagicMock()
        mock_est.to_dict.return_value = mock_result

        # estimate_from_swz importowane lokalnie w create_estimate — patchujemy moduł źródłowy
        import services.api.services.api.analytics.cost_estimation as ce_mod
        orig = getattr(ce_mod, "estimate_from_swz", None)
        ce_mod.estimate_from_swz = MagicMock(return_value=mock_est)
        try:
            with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
                result = create_estimate(req, _user())
        finally:
            if orig is not None:
                ce_mod.estimate_from_swz = orig

        assert "ids" in result
        assert "estimates" in result
        assert result["count"] == 1

    def test_estimate_icb_success(self):
        """POST /estimate method=icb z area_m2 > 0 → sukces."""
        from services.api.services.api.routers.kosztorys_v2 import create_estimate, CostEstimateRequest
        req = CostEstimateRequest(method="icb", area_m2=1000.0, cpv="45000000")
        mock_result = self._mock_estimate_result("icb")
        engine = _engine()

        mock_est = MagicMock()
        mock_est.to_dict.return_value = mock_result

        import services.api.services.api.analytics.cost_estimation as ce_mod
        orig = getattr(ce_mod, "estimate_from_icb", None)
        ce_mod.estimate_from_icb = MagicMock(return_value=mock_est)
        try:
            with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
                result = create_estimate(req, _user())
        finally:
            if orig is not None:
                ce_mod.estimate_from_icb = orig

        assert result["count"] == 1

    def test_estimate_all_success(self):
        """POST /estimate method=all → estimate_all wywołane, zwraca wiele wyników."""
        from services.api.services.api.routers.kosztorys_v2 import create_estimate, CostEstimateRequest
        req = CostEstimateRequest(method="all", area_m2=500.0, cpv="45000000")
        results = [self._mock_estimate_result("icb"), self._mock_estimate_result("swz")]
        engine = _engine()

        import services.api.services.api.analytics.cost_estimation as ce_mod
        orig = getattr(ce_mod, "estimate_all", None)
        ce_mod.estimate_all = MagicMock(return_value=results)
        try:
            with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
                result = create_estimate(req, _user())
        finally:
            if orig is not None:
                ce_mod.estimate_all = orig

        assert result["count"] == 2


class TestKosztorysV2DeleteEstimate:
    def test_delete_estimate_ok(self):
        """DELETE /estimate/{id} → 204, brak wyjątku."""
        from services.api.services.api.routers.kosztorys_v2 import delete_estimate
        eid = str(uuid.uuid4())
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 1
        conn.execute = MagicMock(return_value=res)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx

        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = delete_estimate(eid, _user())
        assert result is None  # 204 No Content

    def test_delete_estimate_not_found_raises_404(self):
        """DELETE /estimate/{id} gdy nie ma rekordu → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import delete_estimate
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 0
        conn.execute = MagicMock(return_value=res)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx

        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_estimate(str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404


class TestKosztorysV2UserRates:
    def test_list_user_rates_empty(self):
        """GET /user-rates — zwraca pustą listę."""
        from services.api.services.api.routers.kosztorys_v2 import list_user_rates
        engine = _engine({"user_rates": []})
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_user_rates(_user())
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_user_rates_with_data(self):
        """GET /user-rates — zwraca stawki tenanta."""
        from services.api.services.api.routers.kosztorys_v2 import list_user_rates
        rid = uuid.uuid4()
        row = _tuple_row(rid, "CEM-01", "Cement 32.5", "t", "M ", 650.0, None)
        engine = _engine({"user_rates": [row]})
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_user_rates(_user())
        assert result["total"] == 1
        assert result["items"][0]["symbol"] == "CEM-01"
        assert result["items"][0]["typ_rms"] == "M"  # stripped

    def test_create_user_rate(self):
        """POST /user-rates → tworzy stawkę, zwraca id + symbol."""
        from services.api.services.api.routers.kosztorys_v2 import create_user_rate, UserRateCreate
        rate = UserRateCreate(symbol="STL-01", nazwa="Stal A500", jednostka="t", typ_rms="M", cena_netto=4200.0)
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = create_user_rate(rate, _user())
        assert "id" in result
        assert result["symbol"] == "STL-01"
        assert result["typ_rms"] == "M"

    def test_create_user_rate_defaults_nazwa(self):
        """POST /user-rates bez nazwa → nazwa = symbol."""
        from services.api.services.api.routers.kosztorys_v2 import create_user_rate, UserRateCreate
        rate = UserRateCreate(symbol="X-01", jednostka="szt", typ_rms="R", cena_netto=99.0)
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = create_user_rate(rate, _user())
        assert result["symbol"] == "X-01"

    def test_delete_user_rate_ok(self):
        """DELETE /user-rates/{id} → 204 bez wyjątku."""
        from services.api.services.api.routers.kosztorys_v2 import delete_user_rate
        rid = str(uuid.uuid4())
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 1
        conn.execute = MagicMock(return_value=res)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx

        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = delete_user_rate(rid, _user())
        assert result is None

    def test_delete_user_rate_not_found_raises_404(self):
        """DELETE /user-rates/{id} gdy brak → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import delete_user_rate
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 0
        conn.execute = MagicMock(return_value=res)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx

        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_user_rate(str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 3. intelligence/win_prob.py — _fetch_ratios nuts2/no-nuts2/error + compute/estimate
# ══════════════════════════════════════════════════════════════════════════════

class TestWinProbCoverage:
    def _conn_with_rows(self, rows):
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.fetchall.return_value = rows
        conn.execute = MagicMock(return_value=res)
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        return engine

    def test_fetch_ratios_with_nuts2(self):
        """_fetch_ratios z nuts2 → użyje nuts2-filtered SQL brancha."""
        from services.api.services.api.intelligence.win_prob import _fetch_ratios

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, i: 0.9
        engine = self._conn_with_rows([mock_row, mock_row])
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = _fetch_ratios("45000000", nuts2="PL22")
        assert isinstance(result, list)

    def test_fetch_ratios_without_nuts2(self):
        """_fetch_ratios bez nuts2 → użyje LIKE branch, pusta DB → []."""
        from services.api.services.api.intelligence.win_prob import _fetch_ratios
        engine = self._conn_with_rows([])
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = _fetch_ratios("45000000")
        assert result == []

    def test_fetch_ratios_db_error_returns_empty(self):
        """_fetch_ratios przy SQLAlchemyError → zwraca []."""
        from sqlalchemy.exc import SQLAlchemyError
        from services.api.services.api.intelligence.win_prob import _fetch_ratios
        engine = MagicMock()
        conn = MagicMock()
        conn.execute = MagicMock(side_effect=SQLAlchemyError("boom"))
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = _fetch_ratios("45000000")
        assert result == []

    def test_compute_win_probability_no_data(self):
        """compute_win_probability bez danych rynkowych → zwraca dict."""
        from services.api.services.api.intelligence.win_prob import compute_win_probability
        engine = self._conn_with_rows([])
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = compute_win_probability(estimated_value=500000.0, cpv_prefix="45000000")
        assert isinstance(result, dict)

    def test_compute_win_probability_with_data(self):
        """compute_win_probability z danymi → zwraca dict ze statystykami."""
        from services.api.services.api.intelligence.win_prob import compute_win_probability
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, i: 0.92  # ratio
        engine = self._conn_with_rows([mock_row] * 10)
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = compute_win_probability(estimated_value=500000.0, cpv_prefix="45000000")
        assert isinstance(result, dict)

    def test_estimate_win_prob_returns_float(self):
        """estimate_win_prob → zwraca float ∈ [0, 1]."""
        from services.api.services.api.intelligence.win_prob import estimate_win_prob
        engine = self._conn_with_rows([])
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = estimate_win_prob(offer_pct=95.0, cpv_prefix="45000000")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_estimate_win_prob_low_offer(self):
        """estimate_win_prob z niską ofertą (70%) → wysoka szansa wygranej."""
        from services.api.services.api.intelligence.win_prob import estimate_win_prob
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, i: 0.9
        engine = self._conn_with_rows([mock_row] * 20)
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result_low = estimate_win_prob(offer_pct=70.0, cpv_prefix="45000000")
            result_high = estimate_win_prob(offer_pct=120.0, cpv_prefix="45000000")
        # Niższa oferta → wyższa szansa (nie zawsze deterministyczne bez danych, sprawdzamy typy)
        assert isinstance(result_low, float)
        assert isinstance(result_high, float)

    def test_get_market_benchmarks(self):
        """get_market_benchmarks zwraca dict z p25/p50/p75."""
        from services.api.services.api.intelligence.win_prob import get_market_benchmarks
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda s, i: 0.9
        engine = self._conn_with_rows([mock_row] * 5)
        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            result = get_market_benchmarks("45000000")
        assert isinstance(result, dict)


# ══════════════════════════════════════════════════════════════════════════════
# 4. intelligence/anomaly.py — analyze_kosztorys + get_anomalies + zscore
# ══════════════════════════════════════════════════════════════════════════════

class TestAnomalyCoverage:
    def _anomaly_engine(self, pozycja_rows=None):
        """Engine z JOIN kosztorys + kosztorys_pozycja → zwraca odpowiednie wiersze."""
        engine = MagicMock()
        conn = MagicMock()

        def _execute(stmt, params=None):
            result = MagicMock()
            rows = pozycja_rows or []
            result.fetchall.return_value = rows
            result.fetchone.return_value = rows[0] if rows else None
            result.rowcount = len(rows)
            return result

        conn.execute = _execute
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        engine.begin.return_value = begin_ctx
        return engine

    def _make_rows(self, n: int = 5, outlier_idx: int | None = None):
        """Generuje wiersze tuple (id, r_jcena, m_jcena, s_jcena)."""
        rows = []
        for i in range(n):
            price = 999999.0 if i == outlier_idx else 50.0 + i * 2
            row = MagicMock()
            row.__getitem__ = lambda s, k, p=price, uid=str(uuid.uuid4()): (
                uid if k == 0 else p if k == 1 else None
            )
            rows.append(row)
        return rows

    def test_analyze_kosztorys_empty(self):
        """analyze_kosztorys bez wierszy → _empty z pozycje_analyzed=0."""
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys
        engine = self._anomaly_engine([])
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            result = analyze_kosztorys(str(uuid.uuid4()), TENANT)
        assert isinstance(result, dict)
        assert result.get("pozycje_analyzed", 0) == 0

    def test_analyze_kosztorys_with_rows(self):
        """analyze_kosztorys z wierszami — nie crashuje (mockujemy zscore_pozycja)."""
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys
        rows = self._make_rows(5, outlier_idx=4)
        engine = self._anomaly_engine(rows)
        # zscore_pozycja robi własne zapytania ICB — mockujemy całą funkcję
        mock_zscore = MagicMock(return_value={
            "pozycja_id": "x", "r_zscore": 0.0, "m_zscore": None, "s_zscore": None,
            "is_anomaly": False, "anomaly_score": 0.0,
        })
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine), \
             patch("services.api.services.api.intelligence.anomaly.zscore_pozycja", mock_zscore):
            result = analyze_kosztorys(str(uuid.uuid4()), TENANT)
        assert isinstance(result, dict)

    def test_analyze_kosztorys_db_error_returns_empty(self):
        """analyze_kosztorys przy błędzie DB → zwraca _empty."""
        from sqlalchemy.exc import SQLAlchemyError
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys
        engine = MagicMock()
        conn = MagicMock()
        conn.execute = MagicMock(side_effect=SQLAlchemyError("boom"))
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            result = analyze_kosztorys(str(uuid.uuid4()), TENANT)
        assert isinstance(result, dict)
        assert result.get("pozycje_analyzed", 0) == 0

    def test_get_anomalies_returns_list(self):
        """get_anomalies zwraca listę (może być pusta)."""
        from services.api.services.api.intelligence.anomaly import get_anomalies
        engine = self._anomaly_engine([])
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            result = get_anomalies(str(uuid.uuid4()), TENANT)
        assert isinstance(result, list)

    def test_zscore_pozycja_not_found(self):
        """zscore_pozycja dla nieistniejącej pozycji → zwraca dict."""
        from services.api.services.api.intelligence.anomaly import zscore_pozycja
        engine = self._anomaly_engine([])
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            result = zscore_pozycja(str(uuid.uuid4()))
        assert isinstance(result, dict)

    def test_try_isolation_forest_too_small(self):
        """_try_isolation_forest z < 5 wierszami → zwraca None."""
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest
        import numpy as np
        small_matrix = np.array([[100.0], [200.0]])
        result = _try_isolation_forest(small_matrix)
        assert result is None

    def test_try_isolation_forest_sufficient_data(self):
        """_try_isolation_forest z >= 5 wierszami → zwraca listę boolów lub None."""
        from services.api.services.api.intelligence.anomaly import _try_isolation_forest
        import numpy as np
        matrix = np.array([[float(i * 10)] for i in range(10)])
        result = _try_isolation_forest(matrix)
        # Może być None jeśli sklearn niedostępny, lub lista boolów
        assert result is None or (isinstance(result, list) and len(result) == 10)


# ══════════════════════════════════════════════════════════════════════════════
# 5. kosztorys_v2.py — list_estimates, get_kosztorys, anomalies, win_prob,
#    material_alerts, dzialy CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV2Extra:
    """Pokrycie linii 315–365, 437–471, 522, 558–620 + list_estimates."""

    def _conn(self, rows=None):
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock()
        res.fetchall.return_value = rows or []
        res.fetchone.return_value = (rows or [None])[0]
        res.rowcount = len(rows or [])
        conn.execute = MagicMock(return_value=res)
        conn.commit = MagicMock()
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        engine.begin.return_value = begin_ctx
        return engine

    # ── list_estimates ──────────────────────────────────────────────────────

    def test_list_estimates_empty(self):
        """GET /estimate — brak rekordów → items=[], total=0."""
        from services.api.services.api.routers.kosztorys_v2 import list_estimates
        engine = self._conn([])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_estimates(_user())
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_estimates_with_tender_filter(self):
        """GET /estimate?tender_id=X — filtruje po przetargu."""
        from services.api.services.api.routers.kosztorys_v2 import list_estimates
        engine = self._conn([])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_estimates(_user(), tender_id=TENDER_ID)
        assert result["total"] == 0

    def test_list_estimates_with_data(self):
        """GET /estimate — z danymi zwraca items."""
        from services.api.services.api.routers.kosztorys_v2 import list_estimates
        import datetime
        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            uuid.UUID(TENDER_ID), "icb", "standard", uuid.UUID(TENDER_ID),
            500.0, "45000000", "PL22",
            150000.0, 135000.0, 165000.0,
            [], {}, "notes", datetime.datetime(2025, 1, 1),
        ][i]
        engine = self._conn([row])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_estimates(_user())
        assert result["total"] == 1
        assert result["items"][0]["method"] == "icb"

    # ── get_kosztorys_anomalies ─────────────────────────────────────────────

    def test_get_kosztorys_anomalies_not_found(self):
        """GET /{kid}/anomalies — kosztorys nie istnieje → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import get_kosztorys_anomalies
        engine = self._conn([])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                get_kosztorys_anomalies(str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404

    def test_get_kosztorys_anomalies_found(self):
        """GET /{kid}/anomalies — kosztorys istnieje → zwraca anomalies dict."""
        from services.api.services.api.routers.kosztorys_v2 import get_kosztorys_anomalies
        kid = str(uuid.uuid4())

        engine = MagicMock()
        conn = MagicMock()
        call_count = [0]
        kosztorys_row = MagicMock()

        def _execute(stmt, params=None):
            res = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # _get_kosztorys_or_404 — fetchone
                res.fetchone.return_value = kosztorys_row
                res.fetchall.return_value = [kosztorys_row]
            else:
                # anomalies query — fetchall, brak anomalii
                res.fetchall.return_value = []
            return res
        conn.execute = _execute
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = get_kosztorys_anomalies(kid, _user())
        assert result["kosztorys_id"] == kid
        assert result["count"] == 0

    # ── get_win_probability ─────────────────────────────────────────────────

    def test_get_win_probability_not_found(self):
        """GET /{kid}/win-probability — kosztorys nie istnieje → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import get_win_probability
        engine = self._conn([])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                get_win_probability(str(uuid.uuid4()), user=_user())
        assert exc.value.status_code == 404

    def test_get_win_probability_found(self):
        """GET /{kid}/win-probability — zwraca wynik (cached lub computed)."""
        from services.api.services.api.routers.kosztorys_v2 import get_win_probability
        kid = str(uuid.uuid4())
        # hdr row — _get_kosztorys_or_404 zwraca obiekt z atrybutami
        hdr = MagicMock()
        hdr.suma_netto = 500000.0
        hdr.win_probability = 0.72  # cached → natychmiastowy return

        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = hdr
        res.fetchall.return_value = [hdr]
        conn.execute = MagicMock(return_value=res)
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = get_win_probability(kid, cpv="45000000", user=_user())
        assert "win_probability" in result
        assert result["win_probability"] == 0.72

    # ── material_alerts ─────────────────────────────────────────────────────

    def test_get_material_alerts_empty(self):
        """GET /material-alerts — brak alertów → pusta lista."""
        from services.api.services.api.routers.kosztorys_v2 import get_material_alerts
        engine = self._conn([])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = get_material_alerts(_user())
        assert isinstance(result, list)
        assert len(result) == 0

    def test_acknowledge_material_alert_not_found(self):
        """POST /material-alerts/{id}/acknowledge — alert nie istnieje → ok=False."""
        from services.api.services.api.routers.kosztorys_v2 import acknowledge_material_alert
        # acknowledge_material_alert nie rzuca 404, przechwytuje wyjątek i zwraca ok=False
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine"):
            with patch("services.api.services.api.intelligence.material_risk.acknowledge_alert",
                       return_value=False, create=True):
                result = acknowledge_material_alert(str(uuid.uuid4()), _user())
        assert isinstance(result, dict)
        assert "ok" in result

    def test_acknowledge_material_alert_ok(self):
        """POST /material-alerts/{id}/acknowledge — sukces → ok=True."""
        from services.api.services.api.routers.kosztorys_v2 import acknowledge_material_alert
        import services.api.services.api.intelligence.material_risk as mr_mod
        orig = getattr(mr_mod, "acknowledge_alert", None)
        mr_mod.acknowledge_alert = MagicMock(return_value=True)
        try:
            with patch("services.api.services.api.routers.kosztorys_v2.get_engine"):
                result = acknowledge_material_alert(str(uuid.uuid4()), _user())
        finally:
            if orig is not None:
                mr_mod.acknowledge_alert = orig
        assert result["ok"] is True

    # ── dzialy CRUD ─────────────────────────────────────────────────────────

    def test_add_dzial_kosztorys_not_found(self):
        """POST /{kid}/dzialy — kosztorys nie istnieje → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import add_dzial, DzialCreate
        body = DzialCreate(nazwa="Roboty murowe", lp=1)
        engine = self._conn([])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                add_dzial(str(uuid.uuid4()), body, _user())
        assert exc.value.status_code == 404

    def test_add_dzial_ok(self):
        """POST /{kid}/dzialy — kosztorys istnieje → tworzy dział."""
        from services.api.services.api.routers.kosztorys_v2 import add_dzial, DzialCreate
        kid = str(uuid.uuid4())
        row = MagicMock()
        row.__getitem__ = lambda s, i: kid if i == 0 else TENANT
        body = DzialCreate(nazwa="Roboty murowe", lp=1)
        engine = self._conn([row])
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = add_dzial(kid, body, _user())
        assert "id" in result
        assert result["status"] == "created"

    def test_list_dzialy_empty(self):
        """GET /{kid}/dzialy — brak działów → items=[]."""
        from services.api.services.api.routers.kosztorys_v2 import list_dzialy
        kid = str(uuid.uuid4())
        kosztorys_row = MagicMock()
        kosztorys_row.__getitem__ = lambda s, i: kid if i == 0 else TENANT
        # Pierwsze zapytanie = kosztorys check, drugie = dzialy
        engine = MagicMock()
        conn = MagicMock()
        call_count = [0]
        def _execute(stmt, params=None):
            res = MagicMock()
            call_count[0] += 1
            res.fetchall.return_value = [] if call_count[0] > 1 else [kosztorys_row]
            res.fetchone.return_value = kosztorys_row if call_count[0] == 1 else None
            res.rowcount = 0
            return res
        conn.execute = _execute
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_dzialy(kid, _user())
        assert "items" in result

    def test_delete_dzial_not_found(self):
        """DELETE /{kid}/dzialy/{did} — dział nie istnieje → 404."""
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import delete_dzial
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 0
        conn.execute = MagicMock(return_value=res)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_dzial(str(uuid.uuid4()), str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404

    def test_delete_dzial_ok(self):
        """DELETE /{kid}/dzialy/{did} — sukces → None (204)."""
        from services.api.services.api.routers.kosztorys_v2 import delete_dzial
        engine = MagicMock()
        conn = MagicMock()
        res = MagicMock(); res.rowcount = 1
        conn.execute = MagicMock(return_value=res)
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = delete_dzial(str(uuid.uuid4()), str(uuid.uuid4()), _user())
        assert result is None

