"""Tests covering uncovered lines in estimator.py, bid_writing.py, document_generator.py, tasks.py."""
from __future__ import annotations

import json
import subprocess
import uuid
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ===========================================================================
# document_generator.py — direct unit tests (no HTTP needed)
# ===========================================================================

class TestDocumentGeneratorFormatPln:
    """Cover lines 123-124 (_format_pln with bad input)."""

    def test_format_pln_valid(self):
        from services.api.services.api.intelligence.document_generator import _format_pln
        result = _format_pln(927149.00)
        assert "927" in result
        assert "149" in result

    def test_format_pln_invalid_type(self):
        from services.api.services.api.intelligence.document_generator import _format_pln
        # Triggers except (TypeError, ValueError): return str(value)
        result = _format_pln("not-a-number")
        assert result == "not-a-number"

    def test_format_pln_none(self):
        from services.api.services.api.intelligence.document_generator import _format_pln
        result = _format_pln(None)
        assert result == "None"


class TestDocumentGeneratorTrzyCyfry:
    """Cover lines 141, 145 (_trzy_cyfry with nastki range)."""

    def test_trzy_cyfry_zero(self):
        from services.api.services.api.intelligence.document_generator import _trzy_cyfry
        assert _trzy_cyfry(0) == ""

    def test_trzy_cyfry_nastki(self):
        """11-19 range → line 145."""
        from services.api.services.api.intelligence.document_generator import _trzy_cyfry
        result = _trzy_cyfry(12)
        assert "dwanaście" in result

    def test_trzy_cyfry_hundreds_with_nastki(self):
        from services.api.services.api.intelligence.document_generator import _trzy_cyfry
        result = _trzy_cyfry(115)
        assert "sto" in result
        assert "piętnaście" in result

    def test_trzy_cyfry_dziesiatki_jednosci(self):
        from services.api.services.api.intelligence.document_generator import _trzy_cyfry
        result = _trzy_cyfry(23)
        assert "dwadzieścia" in result
        assert "trzy" in result


class TestDocumentGeneratorKwotaSlownie:
    """Cover lines 160-161, 175, 177, 181."""

    def test_kwota_slownie_invalid(self):
        """Triggers except (TypeError, ValueError): return str(value) — lines 160-161."""
        from services.api.services.api.intelligence.document_generator import _kwota_slownie
        result = _kwota_slownie("invalid")
        assert result == "invalid"

    def test_kwota_slownie_none(self):
        from services.api.services.api.intelligence.document_generator import _kwota_slownie
        result = _kwota_slownie(None)
        assert result == "None"

    def test_kwota_slownie_miliardy(self):
        """Covers line 175 (mld branch)."""
        from services.api.services.api.intelligence.document_generator import _kwota_slownie
        result = _kwota_slownie(2_000_000_000.50)
        assert "miliardów" in result
        assert "złotych" in result

    def test_kwota_slownie_miliony(self):
        """Covers line 177 (mln branch)."""
        from services.api.services.api.intelligence.document_generator import _kwota_slownie
        result = _kwota_slownie(3_500_000.00)
        assert "milionów" in result
        assert "tysięcy" in result

    def test_kwota_slownie_tysiace(self):
        """Covers line 179 (tys branch)."""
        from services.api.services.api.intelligence.document_generator import _kwota_slownie
        result = _kwota_slownie(5_200.00)
        assert "tysięcy" in result

    def test_kwota_slownie_jednosci(self):
        """Covers line 181 (jed branch)."""
        from services.api.services.api.intelligence.document_generator import _kwota_slownie
        result = _kwota_slownie(7.50)
        assert "złotych" in result
        assert "50/100" in result


class TestSelectBestReferences:
    """Cover lines 221-253 (_select_best_references)."""

    def test_empty_referencje(self):
        from services.api.services.api.intelligence.document_generator import _select_best_references
        result = _select_best_references([], ["45000000-7"], Decimal("1000000"))
        assert result == []

    def test_with_cpv_match(self):
        from services.api.services.api.intelligence.document_generator import _select_best_references
        refs = [
            {"cpv_kody": ["45000000-7"], "wartosc_brutto": 800000, "data_zakonczenia": "2024-01-01"},
            {"cpv_kody": ["71000000-8"], "wartosc_brutto": 500000, "data_zakonczenia": "2022-01-01"},
        ]
        result = _select_best_references(refs, ["45000000-7"], Decimal("1000000"), required_count=2)
        assert len(result) == 2
        # First should be the CPV-matching one
        assert result[0]["cpv_kody"] == ["45000000-7"]

    def test_no_cpv_in_ref(self):
        """Covers line 231 — no CPV gets partial bonus."""
        from services.api.services.api.intelligence.document_generator import _select_best_references
        refs = [
            {"wartosc_brutto": 600000, "data_zakonczenia": "2023-06-01"},
        ]
        result = _select_best_references(refs, ["45000000-7"], Decimal("1000000"))
        assert len(result) == 1

    def test_value_ratio_below_50_above_25(self):
        """Covers line 239 (ratio >= 0.25 branch)."""
        from services.api.services.api.intelligence.document_generator import _select_best_references
        refs = [
            {"cpv_kody": ["45000000-7"], "wartosc_brutto": 300000, "data_zakonczenia": "2024-01-01"},
        ]
        result = _select_best_references(refs, ["45000000-7"], Decimal("1000000"))
        assert len(result) == 1

    def test_invalid_date(self):
        """Covers lines 247-248 (except ValueError/TypeError)."""
        from services.api.services.api.intelligence.document_generator import _select_best_references
        refs = [
            {"cpv_kody": ["45000000-7"], "wartosc_brutto": 800000, "data_zakonczenia": "invalid"},
        ]
        result = _select_best_references(refs, ["45000000-7"], Decimal("1000000"))
        assert len(result) == 1

    def test_no_tender_wartosc(self):
        """No tender value — skips value scoring."""
        from services.api.services.api.intelligence.document_generator import _select_best_references
        refs = [
            {"cpv_kody": ["45000000-7"], "wartosc_brutto": 800000, "data_zakonczenia": "2024-01-01"},
        ]
        result = _select_best_references(refs, ["45000000-7"], None)
        assert len(result) == 1


class TestDocumentValidation:
    """Cover lines 386-387, 409, 414, 418, 420, 424, 428, 460."""

    def test_validation_error_class(self):
        from services.api.services.api.intelligence.document_generator import DocumentValidationError
        err = DocumentValidationError(["err1", "err2"])
        assert err.errors == ["err1", "err2"]
        assert "err1" in str(err)

    def test_validate_inputs_missing_company_fields(self):
        """Covers line 409."""
        from services.api.services.api.intelligence.document_generator import (
            _validate_inputs, TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="", nip="", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("100"), total_brutto=Decimal("123"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("23"),
        )
        bid = BidStrategy(termin_realizacji_dni=90)
        errors = _validate_inputs(tender, company, kosztorys, bid)
        assert any("[FIRMA] Brakuje: Nazwa firmy" in e for e in errors)
        assert any("[FIRMA] Brakuje: NIP" in e for e in errors)
        assert any("[FIRMA] Brakuje: Miasto" in e for e in errors)

    def test_validate_inputs_bad_nip(self):
        """Covers line 414."""
        from services.api.services.api.intelligence.document_generator import (
            _validate_inputs, TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="Firma", nip="123", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="Warszawa",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("100"), total_brutto=Decimal("123"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("23"),
        )
        bid = BidStrategy(termin_realizacji_dni=90)
        errors = _validate_inputs(tender, company, kosztorys, bid)
        assert any("NIP nieprawidłowy" in e for e in errors)

    def test_validate_inputs_brutto_zero(self):
        """Covers line 418."""
        from services.api.services.api.intelligence.document_generator import (
            _validate_inputs, TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="Firma", nip="1234567890", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="Warszawa",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("0"), total_brutto=Decimal("0"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("0"),
        )
        bid = BidStrategy(termin_realizacji_dni=90)
        errors = _validate_inputs(tender, company, kosztorys, bid)
        assert any("brutto musi być > 0" in e for e in errors)

    def test_validate_inputs_netto_gt_brutto(self):
        """Covers line 420."""
        from services.api.services.api.intelligence.document_generator import (
            _validate_inputs, TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="Firma", nip="1234567890", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="Warszawa",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("200"), total_brutto=Decimal("100"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("23"),
        )
        bid = BidStrategy(termin_realizacji_dni=90)
        errors = _validate_inputs(tender, company, kosztorys, bid)
        assert any("netto > brutto" in e for e in errors)

    def test_validate_inputs_bad_termin(self):
        """Covers line 424."""
        from services.api.services.api.intelligence.document_generator import (
            _validate_inputs, TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="Firma", nip="1234567890", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="Warszawa",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("100"), total_brutto=Decimal("123"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("23"),
        )
        bid = BidStrategy(termin_realizacji_dni=0)
        errors = _validate_inputs(tender, company, kosztorys, bid)
        assert any("Termin realizacji" in e for e in errors)

    def test_validate_inputs_bad_gwarancja(self):
        """Covers line 428."""
        from services.api.services.api.intelligence.document_generator import (
            _validate_inputs, TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="Firma", nip="1234567890", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="Warszawa",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("100"), total_brutto=Decimal("123"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("23"),
        )
        bid = BidStrategy(termin_realizacji_dni=90, gwarancja_miesiecy=6)
        errors = _validate_inputs(tender, company, kosztorys, bid)
        assert any("Gwarancja" in e for e in errors)

    def test_validation_error_raised_in_generate(self):
        """Covers line 460 (raise DocumentValidationError)."""
        from services.api.services.api.intelligence.document_generator import (
            DocumentOrchestrator, DocumentValidationError,
            TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="", nip="", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("0"), total_brutto=Decimal("0"),
            vat_stawka=Decimal("23"), vat_kwota=Decimal("0"),
        )
        bid = BidStrategy(termin_realizacji_dni=0, gwarancja_miesiecy=6)
        orch = DocumentOrchestrator()
        with pytest.raises(DocumentValidationError) as exc_info:
            orch.generate_package(tender, company, kosztorys, bid)
        assert len(exc_info.value.errors) > 0


class TestKosztorysToDocx:
    """Cover lines 353-365 (kosztorys pozycje rendering)."""

    def test_kosztorys_to_docx_with_pozycje(self):
        from services.api.services.api.intelligence.document_generator import (
            _kosztorys_to_docx, KosztorysContext, TenderContext, CompanyContext,
        )
        tender = TenderContext(nr_sprawy="ZP/1/2026", tytul="Test", zamawiajacy_nazwa="Urząd")
        company = CompanyContext(
            nazwa_pelna="Firma", nip="1234567890", adres_ulica="ul. X", adres_nr_budynku="1",
            adres_kod_pocztowy="00-001", adres_miasto="Warszawa",
        )
        kosztorys = KosztorysContext(
            total_netto=Decimal("10000"),
            total_brutto=Decimal("12300"),
            vat_stawka=Decimal("23"),
            vat_kwota=Decimal("2300"),
            pozycje=[
                {
                    "lp": 1,
                    "opis_roboty": "Roboty ziemne",
                    "knr_katalog": "KNR 2-01",
                    "knr_tablica": "0101-01",
                    "jednostka": "m3",
                    "ilosc": 100,
                    "cena_jm_netto": 50,
                    "wartosc_netto": 5000,
                },
                {
                    "lp": 2,
                    "opis_roboty": "Beton C25/30",
                    "knr_katalog": "KNR 2-02",
                    "knr_tablica": "0201-01",
                    "jednostka": "m3",
                    "ilosc": 50,
                    "cena_jm_netto": 100,
                    "wartosc_netto": 5000,
                },
            ],
        )
        result = _kosztorys_to_docx(kosztorys, tender, company)
        assert isinstance(result, bytes)
        assert len(result) > 100


# ===========================================================================
# estimator.py — unit tests with mocked DB
# ===========================================================================

class TestEstimatorCreateEstimate:
    """Cover lines 78-101 (create_estimate success path)."""

    @patch("services.api.services.api.routers.estimator.get_engine")
    @patch("services.api.services.api.routers.estimator._load_rate_card")
    @patch("services.api.services.api.routers.estimator.compute_variant_a")
    @patch("services.api.services.api.routers.estimator.compute_variant_b")
    @patch("services.api.services.api.routers.estimator.verify_sum_reconciliation")
    @patch("services.api.services.api.routers.estimator._store_estimate")
    def test_create_estimate_success(
        self, mock_store, mock_verify, mock_b, mock_a, mock_rc, mock_engine
    ):
        from services.api.services.api.routers.estimator import create_estimate

        # Mock DB returns items
        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, i: [{"position_no": "1", "description": "test", "unit": "m3", "quantity": "10"}][i] if i == 0 else None
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_rc.return_value = None

        # Mock estimates
        est_a = MagicMock()
        est_a.variant = "A"
        est_b = MagicMock()
        est_b.variant = "B"
        mock_a.return_value = est_a
        mock_b.return_value = est_b
        mock_verify.return_value = True
        mock_store.side_effect = ["id-a", "id-b"]

        result = create_estimate("tender-1")
        assert result.estimate_doc_id == "id-a"
        assert result.estimate_owner_id == "id-b"

    @patch("services.api.services.api.routers.estimator.get_engine")
    def test_create_estimate_empty_items(self, mock_engine):
        """Cover line 80 — empty items raises 422."""
        from services.api.services.api.routers.estimator import create_estimate
        from fastapi import HTTPException

        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, i: [] if i == 0 else None
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            create_estimate("tender-1")
        assert exc_info.value.status_code == 422


class TestEstimatorUpdateParams:
    """Cover lines 184-214 (update_estimate_params)."""

    @patch("services.api.services.api.routers.estimator.get_engine")
    @patch("services.api.services.api.routers.estimator.compute_variant_a")
    @patch("services.api.services.api.routers.estimator.verify_sum_reconciliation")
    @patch("services.api.services.api.routers.estimator._update_estimate")
    @patch("services.api.services.api.routers.estimator.get_estimate")
    def test_update_params_variant_a(
        self, mock_get_est, mock_update, mock_verify, mock_compute_a, mock_engine
    ):
        from services.api.services.api.routers.estimator import update_estimate_params, ParamsUpdate

        # First query: get estimate row (tender_id, variant, params)
        mock_conn = MagicMock()
        est_row = MagicMock()
        est_row.__getitem__ = lambda self, i: ["tender-1", "A", {}][i]
        # Second query: get analysis row
        analysis_row = MagicMock()
        analysis_row.__getitem__ = lambda self, i: [[{"position_no": "1"}]][i]

        call_count = [0]
        def side_effect_fetchone():
            call_count[0] += 1
            if call_count[0] == 1:
                return est_row
            return analysis_row

        mock_conn.execute.return_value.fetchone = side_effect_fetchone
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        est = MagicMock()
        mock_compute_a.return_value = est
        mock_verify.return_value = True
        mock_get_est.return_value = MagicMock()

        body = ParamsUpdate(params={"kp_pct": "10.0"})
        result = update_estimate_params("est-1", body)
        mock_compute_a.assert_called_once()

    @patch("services.api.services.api.routers.estimator.get_engine")
    @patch("services.api.services.api.routers.estimator.compute_variant_b")
    @patch("services.api.services.api.routers.estimator.verify_sum_reconciliation")
    @patch("services.api.services.api.routers.estimator._update_estimate")
    @patch("services.api.services.api.routers.estimator.get_estimate")
    def test_update_params_variant_b(
        self, mock_get_est, mock_update, mock_verify, mock_compute_b, mock_engine
    ):
        from services.api.services.api.routers.estimator import update_estimate_params, ParamsUpdate

        mock_conn = MagicMock()
        est_row = MagicMock()
        est_row.__getitem__ = lambda self, i: ["tender-1", "B", {"kp_pct": "12.0"}][i]
        analysis_row = MagicMock()
        analysis_row.__getitem__ = lambda self, i: [[{"position_no": "1"}]][i]

        call_count = [0]
        def side_effect_fetchone():
            call_count[0] += 1
            if call_count[0] == 1:
                return est_row
            return analysis_row

        mock_conn.execute.return_value.fetchone = side_effect_fetchone
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        est = MagicMock()
        mock_compute_b.return_value = est
        mock_verify.return_value = True
        mock_get_est.return_value = MagicMock()

        body = ParamsUpdate(params={"zysk_pct": "10.0"})
        result = update_estimate_params("est-1", body)
        mock_compute_b.assert_called_once()


class TestEstimatorCompare:
    """Cover lines 234-261 (compare_estimate_endpoint)."""

    @patch("services.api.services.api.routers.estimator.get_engine")
    @patch("services.api.services.api.routers.estimator.compare_estimates")
    def test_compare_success(self, mock_compare, mock_engine):
        from services.api.services.api.routers.estimator import compare_estimate_endpoint

        mock_conn = MagicMock()
        row_doc = MagicMock()
        row_doc.__getitem__ = lambda self, i: [
            "doc", Decimal("10000"), [{"position_no": "1", "description": "x", "unit": "m3", "quantity": "10", "line_total_pln": "5000"}], {}
        ][i]
        row_owner = MagicMock()
        row_owner.__getitem__ = lambda self, i: [
            "owner", Decimal("12000"), [{"position_no": "1", "description": "x", "unit": "m3", "quantity": "10", "line_total_pln": "6000"}], {}
        ][i]
        mock_conn.execute.return_value.fetchall.return_value = [row_doc, row_owner]
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        cmp_result = MagicMock()
        cmp_result.to_dict.return_value = {
            "doc_total": "10000", "owner_total": "12000",
            "delta_pln": "2000", "margin_headroom_pct": "16.67",
        }
        mock_compare.return_value = cmp_result

        result = compare_estimate_endpoint("tender-1")
        assert result.doc_total == "10000"
        assert result.delta_pln == "2000"

    @patch("services.api.services.api.routers.estimator.get_engine")
    def test_compare_missing_variant(self, mock_engine):
        """Covers line 258 — both variants required."""
        from services.api.services.api.routers.estimator import compare_estimate_endpoint
        from fastapi import HTTPException

        mock_conn = MagicMock()
        row_doc = MagicMock()
        row_doc.__getitem__ = lambda self, i: [
            "doc", Decimal("10000"), [{"position_no": "1", "quantity": "10", "line_total_pln": "5000"}], {}
        ][i]
        mock_conn.execute.return_value.fetchall.return_value = [row_doc]
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            compare_estimate_endpoint("tender-1")
        assert exc_info.value.status_code == 404


class TestEstimatorHelpers:
    """Cover lines 272, 276-303, 307-308."""

    @patch("services.api.services.api.routers.estimator.get_engine")
    def test_get_tenant_id(self, mock_engine):
        """Covers line 272."""
        from services.api.services.api.routers.estimator import _get_tenant_id

        mock_conn = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, i: "tenant-uuid"
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_engine.return_value = MagicMock()
        engine = mock_engine.return_value
        engine.connect.return_value.__enter__ = lambda s: mock_conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = _get_tenant_id(engine)
        assert result == "tenant-uuid"

    @patch("services.api.services.api.routers.estimator._get_tenant_id")
    def test_store_estimate_insert(self, mock_tenant):
        """Covers lines 276-303 — insert path."""
        from services.api.services.api.routers.estimator import _store_estimate

        mock_tenant.return_value = "tenant-1"

        mock_conn = MagicMock()
        # First query: SELECT id WHERE ... → no existing row
        mock_conn.execute.return_value.fetchone.return_value = None

        engine = MagicMock()
        engine.begin.return_value.__enter__ = lambda s: mock_conn
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        estimate = MagicMock()
        estimate.variant = "doc"
        estimate.total_net_pln = Decimal("10000")
        estimate.lines = []
        estimate.params = {}

        result = _store_estimate(engine, "tender-1", estimate)
        assert result is not None  # UUID string

    @patch("services.api.services.api.routers.estimator._get_tenant_id")
    def test_store_estimate_update(self, mock_tenant):
        """Covers lines 276-303 — update path."""
        from services.api.services.api.routers.estimator import _store_estimate

        mock_tenant.return_value = "tenant-1"

        mock_conn = MagicMock()
        existing_row = MagicMock()
        existing_row.__getitem__ = lambda self, i: "existing-id"
        mock_conn.execute.return_value.fetchone.return_value = existing_row

        engine = MagicMock()
        engine.begin.return_value.__enter__ = lambda s: mock_conn
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        estimate = MagicMock()
        estimate.variant = "doc"
        estimate.total_net_pln = Decimal("10000")
        estimate.lines = []
        estimate.params = {}

        result = _store_estimate(engine, "tender-1", estimate)
        assert result == "existing-id"

    def test_update_estimate(self):
        """Covers lines 307-308."""
        from services.api.services.api.routers.estimator import _update_estimate

        mock_conn = MagicMock()
        engine = MagicMock()
        engine.begin.return_value.__enter__ = lambda s: mock_conn
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        estimate = MagicMock()
        estimate.total_net_pln = Decimal("15000")
        estimate.lines = []

        _update_estimate(engine, "est-1", estimate, {"kp_pct": "10"})
        mock_conn.execute.assert_called_once()


class TestListEstimatesNormalized:
    """Cover line 122 (normalized_lines.append inside list_estimates_for_tender)."""

    @patch("services.api.services.api.routers.estimator.get_engine")
    def test_list_estimates_normalizes_lines(self, mock_engine):
        from services.api.services.api.routers.estimator import list_estimates_for_tender

        mock_conn = MagicMock()
        row = MagicMock()
        row.__getitem__ = lambda self, i: [
            "est-id-1", "doc", Decimal("5000"),
            [{"description": "Roboty", "unit": "m3", "quantity": 10, "unit_price": 50, "total": 500}],
            {"kp_pct": "12"},
        ][i]
        mock_conn.execute.return_value.fetchall.return_value = [row]
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = list_estimates_for_tender("tender-1")
        assert len(result) == 1
        assert result[0]["lines"][0]["description"] == "Roboty"


# ===========================================================================
# bid_writing.py — unit tests
# ===========================================================================

class TestBidWritingHelpers:
    """Cover lines 210-212, 236-244, 247-248, 250-251, 270-278."""

    @patch("services.api.services.api.routers.bid_writing.get_engine")
    def test_fetch_historical_context_exception(self, mock_engine):
        """Covers lines 210-212 (exception in _fetch_historical_context)."""
        from services.api.services.api.routers.bid_writing import _fetch_historical_context

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB error")
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        result = _fetch_historical_context("45000000")
        assert "błąd" in result.lower() or "brak" in result.lower()

    @patch("services.api.services.api.routers.bid_writing.get_engine")
    def test_fetch_historical_context_empty_cpv(self, mock_engine):
        """Empty CPV prefix returns default message."""
        from services.api.services.api.routers.bid_writing import _fetch_historical_context
        result = _fetch_historical_context("")
        assert "Brak danych" in result

    @patch("services.api.services.api.routers.bid_writing.boto3")
    def test_call_bedrock_success(self, mock_boto3):
        """Covers lines 236-244 (successful bedrock call with JSON extraction)."""
        from services.api.services.api.routers.bid_writing import _call_bedrock

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        response_body = MagicMock()
        response_body.read.return_value = json.dumps({
            "content": [{"text": '{"opis_podejscia": "test", "metodologia": "test2"}'}]
        }).encode()
        mock_client.invoke_model.return_value = {"body": response_body}

        result = _call_bedrock("test prompt")
        assert result is not None
        assert result["opis_podejscia"] == "test"

    @patch("services.api.services.api.routers.bid_writing.boto3")
    def test_call_bedrock_non_json_response(self, mock_boto3):
        """Covers line 243-244 (non-JSON text → returns None)."""
        from services.api.services.api.routers.bid_writing import _call_bedrock

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        response_body = MagicMock()
        response_body.read.return_value = json.dumps({
            "content": [{"text": "This is plain text without JSON"}]
        }).encode()
        mock_client.invoke_model.return_value = {"body": response_body}

        result = _call_bedrock("test prompt")
        assert result is None

    @patch("services.api.services.api.routers.bid_writing.boto3")
    def test_call_bedrock_client_error(self, mock_boto3):
        """Covers lines 247-248 (BotoCoreError/ClientError)."""
        from services.api.services.api.routers.bid_writing import _call_bedrock
        from botocore.exceptions import ClientError

        mock_boto3.client.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "invoke_model"
        )

        result = _call_bedrock("test prompt")
        assert result is None

    @patch("services.api.services.api.routers.bid_writing.boto3")
    def test_call_bedrock_json_decode_error(self, mock_boto3):
        """Covers lines 250-251 (JSONDecodeError)."""
        from services.api.services.api.routers.bid_writing import _call_bedrock

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        response_body = MagicMock()
        response_body.read.return_value = b"not json at all {"
        mock_client.invoke_model.return_value = {"body": response_body}

        result = _call_bedrock("test prompt")
        assert result is None

    @patch("services.api.services.api.routers.bid_writing.boto3")
    def test_call_bedrock_unexpected_error(self, mock_boto3):
        """Covers lines 252-254 (unexpected Exception)."""
        from services.api.services.api.routers.bid_writing import _call_bedrock

        mock_boto3.client.side_effect = RuntimeError("unexpected")

        result = _call_bedrock("test prompt")
        assert result is None

    def test_build_fallback_sections(self):
        """Covers lines 270-278."""
        from services.api.services.api.routers.bid_writing import _build_fallback_sections

        result = _build_fallback_sections(
            tender_title="Budowa drogi",
            buyer="Urząd Gminy",
            cpv_main="45000000-7",
            company_name="BudFirma",
            company_description="Duża firma budowlana",
            key_projects=["Projekt A", "Projekt B"],
            certifications=["ISO 9001", "ISO 14001"],
        )
        assert "opis_podejscia" in result
        assert "metodologia" in result
        assert "BudFirma" in result["opis_podejscia"]

    def test_build_fallback_sections_empty_projects(self):
        """Covers lines 271 (empty key_projects fallback)."""
        from services.api.services.api.routers.bid_writing import _build_fallback_sections

        result = _build_fallback_sections(
            tender_title="Test",
            buyer="Urząd",
            cpv_main="45000000-7",
            company_name="Firma",
            company_description="",
            key_projects=[],
            certifications=[],
        )
        assert "liczne realizacje" in result["doswiadczenie"]
        assert "odpowiednie uprawnienia" in result["doswiadczenie"]


class TestBidWritingGenerateEndpoint:
    """Cover lines 347-451 (generate_bid_writing endpoint)."""

    @patch("services.api.services.api.routers.bid_writing._try_log_bid_writing")
    @patch("services.api.services.api.routers.bid_writing._call_bedrock")
    @patch("services.api.services.api.routers.bid_writing._fetch_historical_context")
    @patch("services.api.services.api.routers.bid_writing._fetch_swz_chunks")
    @patch("services.api.services.api.routers.bid_writing._fetch_tender_data")
    def test_generate_bid_writing_fallback(
        self, mock_fetch_tender, mock_swz, mock_hist, mock_bedrock, mock_log
    ):
        """Covers lines 347-451 — bedrock returns None → fallback template."""
        from services.api.services.api.routers.bid_writing import (
            generate_bid_writing, BidWritingRequest,
        )
        from services.api.services.api.auth.deps import CurrentUser
        import asyncio

        mock_fetch_tender.return_value = {
            "id": "tid-1", "title": "Budowa mostu", "buyer": "GDDKiA",
            "cpv_main": "45000000-7", "estimated_value": 5000000, "description": "Opis zamówienia",
        }
        mock_swz.return_value = "Fragment SWZ ..."
        mock_hist.return_value = "Brak danych historycznych."
        mock_bedrock.return_value = None  # fallback

        user = MagicMock()
        user.tenant_id = "tenant-1"

        req = BidWritingRequest(
            tender_id="tid-1",
            company_name="BudFirma",
            company_nip="1234567890",
            company_description="Doświadczona firma",
            key_projects=["Most A"],
            certifications=["ISO 9001"],
        )

        result = asyncio.run(generate_bid_writing(req, user, None))
        assert result.source == "template"
        assert result.tender_title == "Budowa mostu"
        assert result.word_count > 0

    @patch("services.api.services.api.routers.bid_writing._try_log_bid_writing")
    @patch("services.api.services.api.routers.bid_writing._call_bedrock")
    @patch("services.api.services.api.routers.bid_writing._fetch_historical_context")
    @patch("services.api.services.api.routers.bid_writing._fetch_swz_chunks")
    @patch("services.api.services.api.routers.bid_writing._fetch_tender_data")
    def test_generate_bid_writing_ai_success(
        self, mock_fetch_tender, mock_swz, mock_hist, mock_bedrock, mock_log
    ):
        """AI returns valid sections."""
        from services.api.services.api.routers.bid_writing import generate_bid_writing, BidWritingRequest
        import asyncio

        mock_fetch_tender.return_value = {
            "id": "tid-1", "title": "Remont szkoły", "buyer": "Gmina X",
            "cpv_main": "45000000-7", "estimated_value": 1000000, "description": "Opis",
        }
        mock_swz.return_value = ""
        mock_hist.return_value = "Brak danych."
        mock_bedrock.return_value = {
            "opis_podejscia": "AI opis",
            "metodologia": "AI metodologia",
            "doswiadczenie": "AI doswiadczenie",
            "propozycja_wartosci": "AI propozycja",
            "podsumowanie": "AI podsumowanie",
        }

        user = MagicMock()
        user.tenant_id = "tenant-1"

        req = BidWritingRequest(
            tender_id="tid-1", company_name="Firma", company_nip="1234567890",
        )

        result = asyncio.run(generate_bid_writing(req, user, None))
        assert result.source == "ai"
        assert "AI opis" in result.sections.opis_podejscia

    @patch("services.api.services.api.routers.bid_writing._fetch_tender_data")
    def test_generate_bid_writing_tender_not_found(self, mock_fetch_tender):
        """Covers line 349 — tender not found."""
        from services.api.services.api.routers.bid_writing import generate_bid_writing, BidWritingRequest
        from fastapi import HTTPException
        import asyncio

        mock_fetch_tender.return_value = None

        user = MagicMock()
        user.tenant_id = "tenant-1"

        req = BidWritingRequest(
            tender_id="nonexistent", company_name="Firma", company_nip="1234567890",
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(generate_bid_writing(req, user, None))
        assert exc_info.value.status_code == 404


# ===========================================================================
# tasks.py — unit tests with mocked dependencies
# ===========================================================================

class TestSyncBzpTask:
    """Cover lines 27-54 (sync_bzp_task)."""

    def test_sync_bzp_task_success(self):
        """Covers success path lines 27-51."""
        mock_result = MagicMock()
        mock_result.raw_fetched = 10
        mock_result.created = 5
        mock_result.updated = 3

        mock_ingest_mod = MagicMock()
        mock_ingest_mod.run_ingest = MagicMock(return_value=mock_result)

        with patch("terra_db.session.get_engine") as mock_engine, \
             patch.dict("sys.modules", {
                 "services.ingestion.pipeline": mock_ingest_mod,
                 "services.api.services.api.cache": MagicMock(),
             }):
            from services.api.services.api.tasks import sync_bzp_task
            # __wrapped__ on a celery bound task drops self — signature is (days_back, offline)
            result = sync_bzp_task.__wrapped__(days_back=7, offline=True)
            assert result["status"] == "ok"
            assert result["fetched"] == 10
            assert result["created"] == 5

    def test_sync_bzp_task_failure(self):
        """Covers lines 52-54 (exception → retry)."""
        from services.api.services.api.tasks import sync_bzp_task

        with patch("terra_db.session.get_engine", side_effect=Exception("DB down")):
            # For bound tasks, we need to mock self.retry 
            # Use apply() which runs the task in-process
            with pytest.raises(Exception):
                sync_bzp_task.__wrapped__(days_back=7, offline=True)


class TestSyncUzpTask:
    """Cover lines 173-178 (sync_uzp_task)."""

    @patch("subprocess.run")
    def test_sync_uzp_task(self, mock_run):
        from services.api.services.api.tasks import sync_uzp_task
        mock_run.return_value = MagicMock(stdout="OK output", returncode=0)
        result = sync_uzp_task()
        assert result["returncode"] == 0
        assert "OK output" in result["stdout"]


class TestSyncTedTask:
    """Cover lines 184-190 (sync_ted_task)."""

    @patch("subprocess.run")
    def test_sync_ted_task(self, mock_run):
        from services.api.services.api.tasks import sync_ted_task
        mock_run.return_value = MagicMock(stdout="TED imported", returncode=0)
        result = sync_ted_task()
        assert result["returncode"] == 0


class TestSyncPretenderTask:
    """Cover lines 196-202 (sync_pretender_task)."""

    @patch("subprocess.run")
    def test_sync_pretender_task(self, mock_run):
        from services.api.services.api.tasks import sync_pretender_task
        mock_run.return_value = MagicMock(stdout="Pretender done", returncode=0)
        result = sync_pretender_task()
        assert result["returncode"] == 0
        assert "Pretender done" in result["stdout"]
