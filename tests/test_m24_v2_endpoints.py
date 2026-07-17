"""K21 — kosztorys_v2 uncovered endpoints: list, get, update, delete, recalc,
export_pdf, export_ath, summary, from_tender, delete_estimate, user_rates."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
KID = str(uuid.uuid4())
TID = str(uuid.uuid4())


def _user(org_id: str = TENANT_ID):
    u = MagicMock()
    u.org_id = org_id
    return u


def _conn_factory(rows_map: dict):
    """rows_map: {query_substr: [row, ...]}"""
    conn = MagicMock()
    def execute_side_effect(stmt, params=None):
        sql = str(stmt) if hasattr(stmt, "__str__") else stmt
        for key, rows in rows_map.items():
            if key in sql:
                res = MagicMock()
                res.fetchall.return_value = rows
                res.fetchone.return_value = rows[0] if rows else None
                res.rowcount = len(rows)
                return res
        res = MagicMock()
        res.fetchall.return_value = []
        res.fetchone.return_value = None
        res.rowcount = 0
        return res
    conn.execute = MagicMock(side_effect=execute_side_effect)
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def _engine(rows_map: dict = None):
    if rows_map is None:
        rows_map = {}
    conn = _conn_factory(rows_map)
    engine = MagicMock()
    engine.connect.return_value = conn
    engine.begin.return_value = conn
    return engine


def _kosztorys_row():
    r = MagicMock()
    r.id = KID
    r.nazwa = "Test kosztorys"
    r.status = "draft"
    r.typ = "ofertowy"
    r.tender_id = None
    r.kwartalrok = 2026
    r.kwartalnr = 2
    r.suma_netto = 100000.0
    r.suma_brutto = 123000.0
    r.win_probability = 0.65
    r.anomaly_score = 0.1
    r.inwestor = "Inwestor SA"
    r.obiekt = "Budynek A"
    r.lokalizacja = "Katowice"
    r.ko_r_pct = 70.0
    r.ko_s_pct = 30.0
    r.z_pct = 12.5
    r.kz_pct = 7.1
    r.vat_pct = 23.0
    r.notes = None
    r.created_at = None
    r.updated_at = None
    r.tenant_id = TENANT_ID
    return r


# ─── LIST ─────────────────────────────────────────────────────────────────────

class TestListKosztorysy:
    def test_empty_list(self):
        from services.api.services.api.routers.kosztorys_v2 import list_kosztorysy
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_kosztorysy(_user())
        assert "items" in result
        assert result["items"] == []

    def test_with_rows(self):
        from services.api.services.api.routers.kosztorys_v2 import list_kosztorysy
        row = MagicMock()
        row.id = KID; row.nazwa = "Test"; row.status = "draft"; row.typ = "ofertowy"
        row.tender_id = None; row.kwartalrok = 2026; row.kwartalnr = 2
        row.suma_netto = 100000.0; row.suma_brutto = 123000.0
        row.win_probability = 0.65; row.anomaly_score = 0.1
        row.created_at = None; row.updated_at = None
        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        def exe(stmt, params=None):
            r = MagicMock()
            call_n[0] += 1
            if call_n[0] == 1:
                r.fetchall.return_value = [row]
            else:
                r.scalar.return_value = 1
            return r
        conn.execute = MagicMock(side_effect=exe)
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_kosztorysy(_user())
        assert result["total"] == 1
        assert result["items"][0]["id"] == KID


# ─── GET ──────────────────────────────────────────────────────────────────────

class TestGetKosztorys:
    def test_get_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import get_kosztorys
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                get_kosztorys(kid=KID, user=_user())
        assert exc.value.status_code == 404

    def test_get_found(self):
        from services.api.services.api.routers.kosztorys_v2 import get_kosztorys
        row = _kosztorys_row()
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        # _get_kosztorys_or_404 → SELECT FROM kosztorys
        # dzial_count → SELECT count(*) FROM kosztorys_dzial
        # pozycja_count → SELECT count(*) FROM kosztorys_pozycja
        call_count = [0]
        def exe(stmt, params=None):
            r = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                r.fetchone.return_value = row
            else:
                r.fetchone.return_value = (0,)
            return r
        conn.execute = MagicMock(side_effect=exe)
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = get_kosztorys(kid=KID, user=_user())
        assert result["id"] == KID


# ─── UPDATE ───────────────────────────────────────────────────────────────────

class TestUpdateKosztorys:
    def test_update_no_fields_raises_400(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import update_kosztorys, KosztorysUpdate
        body = KosztorysUpdate()
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                update_kosztorys(KID, body, _user())
        assert exc.value.status_code == 400

    def test_update_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import update_kosztorys, KosztorysUpdate
        body = KosztorysUpdate(nazwa="Nowy")
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 0
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                update_kosztorys(KID, body, _user())
        assert exc.value.status_code == 404

    def test_update_success(self):
        from services.api.services.api.routers.kosztorys_v2 import update_kosztorys, KosztorysUpdate
        body = KosztorysUpdate(nazwa="Zaktualizowany", z_pct=15.0)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 1
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = update_kosztorys(KID, body, _user())
        assert result["id"] == KID


# ─── DELETE ───────────────────────────────────────────────────────────────────

class TestDeleteKosztorys:
    def test_delete_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import delete_kosztorys
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 0
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_kosztorys(KID, _user())
        assert exc.value.status_code == 404

    def test_delete_success(self):
        from services.api.services.api.routers.kosztorys_v2 import delete_kosztorys
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 1
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = delete_kosztorys(KID, _user())
        assert result is None


# ─── RECALC ───────────────────────────────────────────────────────────────────

class TestRecalcKosztorys:
    def test_recalc_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import recalc
        engine = MagicMock()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with patch(
                "services.api.services.api.intelligence.kosztorys_engine.recalc_kosztorys_db",
                side_effect=ValueError("not found"),
            ):
                with pytest.raises(HTTPException) as exc:
                    recalc(KID, _user())
        assert exc.value.status_code == 404

    def test_recalc_success(self):
        from services.api.services.api.routers.kosztorys_v2 import recalc
        mock_obj = MagicMock()
        mock_obj.suma_r = 10000.0; mock_obj.suma_m = 5000.0; mock_obj.suma_s = 2000.0
        mock_obj.suma_ko = 8000.0; mock_obj.suma_z = 3000.0; mock_obj.suma_kz = 1000.0
        mock_obj.suma_netto = 29000.0; mock_obj.suma_vat = 6670.0; mock_obj.suma_brutto = 35670.0
        mock_obj.pozycje = [1, 2, 3]  # len() = 3
        engine = MagicMock()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with patch(
                "services.api.services.api.intelligence.kosztorys_engine.recalc_kosztorys_db",
                return_value=mock_obj,
            ):
                result = recalc(KID, _user())
        assert result["suma_netto"] == 29000.0
        assert result["n_pozycje"] == 3


# ─── EXPORT PDF ───────────────────────────────────────────────────────────────

class TestExportPdf:
    def test_export_pdf_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import export_pdf
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                export_pdf(KID, _user())
        assert exc.value.status_code == 404

    def test_export_pdf_success(self):
        from fastapi.responses import Response
        from services.api.services.api.routers.kosztorys_v2 import export_pdf
        hdr = _kosztorys_row()
        # add extra attrs used in export_pdf
        hdr.data_opracowania = None
        hdr.suma_r = 0; hdr.suma_m = 0; hdr.suma_s = 0
        hdr.suma_ko = 0; hdr.suma_kz = 0; hdr.suma_z = 0
        hdr.suma_vat = 0; hdr.benchmark_percentile = None
        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        def exe(stmt, params=None):
            r = MagicMock()
            call_n[0] += 1
            if call_n[0] == 1:
                r.fetchone.return_value = hdr
            else:
                r.fetchall.return_value = []
                r._mapping = {}
            return r
        conn.execute = MagicMock(side_effect=exe)
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with patch(
                "services.api.services.api.intelligence.pdf_generator.generate_pdf",
                return_value=b"%PDF-1.4 fake",
            ):
                result = export_pdf(KID, _user())
        assert isinstance(result, Response)
        assert result.media_type == "application/pdf"


# ─── SUMMARY ──────────────────────────────────────────────────────────────────

class TestGetSummary:
    def test_summary_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import get_kosztorys_summary
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        # .mappings().first() → None
        conn.execute.return_value.mappings.return_value.first.return_value = None
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                get_kosztorys_summary(KID, _user())
        assert exc.value.status_code == 404

    def test_summary_found(self):
        from services.api.services.api.routers.kosztorys_v2 import get_kosztorys_summary
        row = MagicMock()
        row.id = KID; row.nazwa = "Test"; row.inwestor = "Inv"; row.obiekt = "Obj"
        row.lokalizacja = "Katowice"; row.typ = "ofertowy"; row.kwartalnr = 2
        row.kwartalrok = 2026; row.tender_id = None; row.status = "draft"
        row.suma_netto = 100000.0; row.suma_brutto = 123000.0; row.suma_vat = 23000.0
        row.ko_r_pct = 70.0; row.ko_s_pct = 30.0; row.z_pct = 12.5
        row.kz_pct = 7.1; row.vat_pct = 23.0
        row.win_probability = 0.65; row.anomaly_score = 0.1
        row.poz_count = 5; row.created_at = None; row.updated_at = None
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.mappings.return_value.first.return_value = row
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = get_kosztorys_summary(KID, _user())
        assert result["id"] == KID
        assert result["pozycje_count"] == 5


# ─── FROM TENDER ──────────────────────────────────────────────────────────────

class TestCreateFromTender:
    def test_invalid_uuid(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import create_from_tender
        with pytest.raises(HTTPException) as exc:
            create_from_tender("not-a-uuid", _user())
        assert exc.value.status_code == 422

    def test_tender_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import create_from_tender
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.mappings.return_value.first.return_value = None
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                create_from_tender(TID, _user())
        assert exc.value.status_code == 404

    def test_from_tender_creates_kosztorys(self):
        from services.api.services.api.routers.kosztorys_v2 import create_from_tender
        tender_row = MagicMock()
        tender_row.title = "Przetarg testowy"
        tender_row.buyer = "Inwestor SA"
        tender_row.voivodeship = "śląskie"
        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.commit = MagicMock()
        def exe(stmt, params=None):
            r = MagicMock()
            call_n[0] += 1
            if call_n[0] == 1:
                r.mappings.return_value.first.return_value = tender_row
            else:
                r.mappings.return_value.first.return_value = None
            return r
        conn.execute = MagicMock(side_effect=exe)
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = create_from_tender(TID, _user())
        assert "id" in result
        assert result["status"] == "created"


# ─── DELETE ESTIMATE ──────────────────────────────────────────────────────────

class TestDeleteEstimate:
    def test_delete_estimate_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import delete_estimate
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 0
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_estimate(str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404

    def test_delete_estimate_success(self):
        from services.api.services.api.routers.kosztorys_v2 import delete_estimate
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 1
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = delete_estimate(str(uuid.uuid4()), _user())
        assert result is None


# ─── USER RATES ───────────────────────────────────────────────────────────────

class TestUserRates:
    def test_list_user_rates_empty(self):
        from services.api.services.api.routers.kosztorys_v2 import list_user_rates
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_user_rates(_user())
        assert result["items"] == []
        assert result["total"] == 0

    def test_list_user_rates_with_rows(self):
        from services.api.services.api.routers.kosztorys_v2 import list_user_rates
        import datetime
        rate_row = (str(uuid.uuid4()), "R001", "Roboty", "m2", "R", 150.0, datetime.datetime(2026, 1, 1))
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = [rate_row]
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = list_user_rates(_user())
        assert result["total"] == 1
        assert result["items"][0]["symbol"] == "R001"

    def test_create_user_rate(self):
        from services.api.services.api.routers.kosztorys_v2 import create_user_rate, UserRateCreate
        body = UserRateCreate(symbol="M001", jednostka="szt", typ_rms="M", cena_netto=50.0)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = create_user_rate(body, _user())
        assert result["symbol"] == "M001"
        assert result["typ_rms"] == "M"

    def test_delete_user_rate_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import delete_user_rate
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 0
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                delete_user_rate(str(uuid.uuid4()), _user())
        assert exc.value.status_code == 404

    def test_delete_user_rate_success(self):
        from services.api.services.api.routers.kosztorys_v2 import delete_user_rate
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.rowcount = 1
        engine = MagicMock()
        engine.begin.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = delete_user_rate(str(uuid.uuid4()), _user())
        assert result is None


# ─── EXPORT ATH ──────────────────────────────────────────────────────────────

class TestExportAth:
    def test_export_ath_not_found(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.kosztorys_v2 import export_ath
        engine = _engine()
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                export_ath(KID, _user())
        assert exc.value.status_code == 404

    def test_export_ath_success(self):
        from fastapi.responses import Response
        from services.api.services.api.routers.kosztorys_v2 import export_ath
        row = _kosztorys_row()
        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        def exe(stmt, params=None):
            r = MagicMock()
            call_n[0] += 1
            if call_n[0] == 1:
                r.fetchone.return_value = row
            else:
                r.fetchall.return_value = []
            return r
        conn.execute = MagicMock(side_effect=exe)
        engine = MagicMock()
        engine.connect.return_value = conn
        with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine):
            result = export_ath(KID, _user())
        assert isinstance(result, Response)
        assert "xml" in result.media_type or result.media_type == "application/octet-stream"
