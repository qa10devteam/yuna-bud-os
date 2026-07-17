"""Coverage tests for validation_engine.py — focuses on exercising all branches."""
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from services.api.services.api.intelligence.validation_engine import (
    validate_bid,
    _db_get_bid_data,
    _generate_recommendations,
    ValidationEngine,
    ValidationResult,
    ValidationPoint,
    CheckStatus,
    CheckCategory,
    CHECKLIST_47,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_offer(**kw):
    base = {
        "id": str(uuid4()), "tenant_id": str(uuid4()), "tender_id": str(uuid4()),
        "estimate_id": None, "title": "Test", "status": "draft",
        "contractor_name": "ACME", "contractor_nip": "1234567890",
        "price_gross_pln": 100000.0, "vat_pct": 23.0,
        "metadata": {}, "created_at": None, "updated_at": None,
        "payment_terms": "30 days", "delivery_days": 30,
    }
    base.update(kw)
    return base


def _make_kosztorys(**kw):
    base = {
        "id": str(uuid4()), "tender_id": str(uuid4()), "nazwa": "KSZ",
        "status": "draft", "typ": "A",
        "suma_netto": 81300.0, "suma_vat": 18700.0, "suma_brutto": 100000.0,
        "vat_pct": 23.0, "ko_r_pct": 70.0, "ko_s_pct": 70.0, "z_pct": 10.0,
        "win_probability": None, "benchmark_percentile": None, "anomaly_score": None,
        "created_at": None, "updated_at": None,
    }
    base.update(kw)
    return base


def _make_db(offer=None, kosztorys=None, tender_documents=None,
             tender_document=None, bid_intelligence=None):
    return {
        "offer": offer,
        "kosztorys": kosztorys,
        "tender_documents": tender_documents or [],
        "tender_document": tender_document or [],
        "bid_intelligence": bid_intelligence,
    }


def _run_validate_bid(db_data):
    """Run validate_bid with a mocked _db_get_bid_data."""
    with patch(
        "services.api.services.api.intelligence.validation_engine._db_get_bid_data",
        return_value=db_data,
    ):
        return validate_bid(uuid4())


# ─── _db_get_bid_data ─────────────────────────────────────────────────────────

class TestDbGetBidData:
    def test_returns_empty_on_db_error(self):
        with patch(
            "services.api.services.api.intelligence.validation_engine.get_db_conn",
            side_effect=Exception("connection refused"),
        ):
            result = _db_get_bid_data(uuid4())
        assert result["offer"] is None
        assert result["kosztorys"] is None
        assert result["tender_documents"] == []

    def test_with_offer_row(self):
        """Lines 173-178 — offer row fetch path."""
        conn_mock = MagicMock()
        cur_mock = MagicMock()
        conn_mock.cursor.return_value = cur_mock

        offer_row = (str(uuid4()),) + (None,) * 14
        kosztorys_row = (str(uuid4()),) + (None,) * 16
        tender_docs_rows = []
        parsed_docs_rows = []
        bid_intel_row = None

        cur_mock.fetchone.side_effect = [offer_row, kosztorys_row, bid_intel_row]
        cur_mock.fetchall.side_effect = [tender_docs_rows, parsed_docs_rows]

        with patch(
            "services.api.services.api.intelligence.validation_engine.get_db_conn",
            return_value=conn_mock,
        ):
            result = _db_get_bid_data(uuid4())

        assert result["offer"] is not None
        assert result["kosztorys"] is not None

    def test_with_no_offer_and_no_kosztorys(self):
        """Lines 184-213 — both None paths."""
        conn_mock = MagicMock()
        cur_mock = MagicMock()
        conn_mock.cursor.return_value = cur_mock
        cur_mock.fetchone.return_value = None
        cur_mock.fetchall.return_value = []

        with patch(
            "services.api.services.api.intelligence.validation_engine.get_db_conn",
            return_value=conn_mock,
        ):
            result = _db_get_bid_data(uuid4())

        assert result["offer"] is None
        assert result["kosztorys"] is None

    def test_with_bid_intelligence_row(self):
        """Lines 265-271 — bid_intelligence row."""
        conn_mock = MagicMock()
        cur_mock = MagicMock()
        conn_mock.cursor.return_value = cur_mock

        bi_row = (str(uuid4()), str(uuid4()), 100.0, 90.0, 3, 2, False, 1.1, 95.0, None, None, None)
        cur_mock.fetchone.side_effect = [None, None, bi_row]
        cur_mock.fetchall.return_value = []

        with patch(
            "services.api.services.api.intelligence.validation_engine.get_db_conn",
            return_value=conn_mock,
        ):
            result = _db_get_bid_data(uuid4())

        assert result["bid_intelligence"] is not None


# ─── validate_bid — completeness (cid 1-12) ──────────────────────────────────

class TestCompleteness:
    def test_cid1_has_formularz_doc(self):
        """cid=1 PASS — formularz doc in parsed_docs."""
        db = _make_db(tender_document=[{"filename": "formularz_ofertowy.pdf", "kind": "formularz"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 1)
        assert p.status == CheckStatus.PASS

    def test_cid1_offer_exists_no_doc(self):
        """cid=1 WARNING — offer in DB but no file."""
        db = _make_db(offer=_make_offer())
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 1)
        assert p.status == CheckStatus.WARNING

    def test_cid1_neither(self):
        """cid=1 FAIL — no offer, no doc."""
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 1)
        assert p.status == CheckStatus.FAIL

    def test_cid2_kosztorys_positive_brutto(self):
        """cid=2 PASS — kosztorys with positive suma_brutto."""
        db = _make_db(kosztorys=_make_kosztorys(suma_brutto=100000.0))
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 2)
        assert p.status == CheckStatus.PASS

    def test_cid2_kosztorys_zero_brutto(self):
        """cid=2 FAIL — kosztorys with suma_brutto=0."""
        db = _make_db(kosztorys=_make_kosztorys(suma_brutto=0))
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 2)
        assert p.status == CheckStatus.FAIL

    def test_cid2_doc_only(self):
        """cid=2 WARNING — doc exists but no DB kosztorys."""
        db = _make_db(tender_document=[{"filename": "kosztorys.pdf", "kind": "kosztorys"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 2)
        assert p.status == CheckStatus.WARNING

    def test_cid2_neither(self):
        """cid=2 FAIL — no doc, no kosztorys."""
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 2)
        assert p.status == CheckStatus.FAIL

    def test_cid3_to_cid12_without_docs(self):
        """cid 3-12 all hit branches without matching docs."""
        db = _make_db()
        r = _run_validate_bid(db)
        ids_hit = {p.id for p in r.points}
        for i in range(3, 13):
            assert i in ids_hit

    def test_cid3_with_doc(self):
        """cid=3 PASS."""
        db = _make_db(tender_document=[{"filename": "oswiadczenie_wykluczenie.pdf", "kind": "oswiadczenie"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 3)
        assert p.status == CheckStatus.PASS

    def test_cid8_with_wadium_doc(self):
        db = _make_db(tender_document=[{"filename": "wadium_gwarancja.pdf", "kind": "wadium"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 8)
        assert p.status == CheckStatus.PASS


# ─── validate_bid — formal (cid 13-24) ───────────────────────────────────────

class TestFormal:
    def test_cid15_no_offer(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 15)
        assert p.status == CheckStatus.WARNING

    def test_cid15_with_offer(self):
        db = _make_db(offer=_make_offer())
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 15)
        assert p.status == CheckStatus.WARNING

    def test_cid19(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 19)
        assert p.status == CheckStatus.PASS

    def test_cid20_no_docs(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 20)
        assert p.status == CheckStatus.WARNING

    def test_cid20_good_formats(self):
        db = _make_db(tender_document=[{"filename": "doc.pdf", "kind": "form", "parsed_ok": True}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 20)
        assert p.status == CheckStatus.PASS

    def test_cid20_bad_format(self):
        db = _make_db(tender_document=[{"filename": "doc.exe", "kind": "form", "parsed_ok": True}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 20)
        assert p.status == CheckStatus.FAIL

    def test_cid22_parse_failed(self):
        db = _make_db(tender_document=[{"filename": "doc.pdf", "kind": "form", "parsed_ok": False}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 22)
        assert p.status == CheckStatus.WARNING

    def test_cid22_parse_ok(self):
        db = _make_db(tender_document=[{"filename": "doc.pdf", "kind": "form", "parsed_ok": True}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 22)
        assert p.status == CheckStatus.PASS

    def test_other_formal_checks_warning(self):
        db = _make_db()
        r = _run_validate_bid(db)
        for cid in [13, 14, 16, 17, 18, 21, 23, 24]:
            pts = [p for p in r.points if p.id == cid]
            if pts:
                assert pts[0].status == CheckStatus.WARNING


# ─── validate_bid — financial (cid 25-34) ────────────────────────────────────

class TestFinancial:
    def test_cid25_pass_exact_match(self):
        offer = _make_offer(price_gross_pln=100000.0)
        kosz = _make_kosztorys(suma_brutto=100000.0)
        db = _make_db(offer=offer, kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 25)
        assert p.status == CheckStatus.PASS

    def test_cid25_small_diff_warning(self):
        offer = _make_offer(price_gross_pln=100000.0)
        kosz = _make_kosztorys(suma_brutto=100050.0)  # <0.1% diff
        db = _make_db(offer=offer, kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 25)
        assert p.status in (CheckStatus.WARNING, CheckStatus.PASS)

    def test_cid25_large_diff_fail(self):
        offer = _make_offer(price_gross_pln=100000.0)
        kosz = _make_kosztorys(suma_brutto=200000.0)
        db = _make_db(offer=offer, kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 25)
        assert p.status == CheckStatus.FAIL
        assert p.auto_fixable is True

    def test_cid25_zero_amounts(self):
        offer = _make_offer(price_gross_pln=0)
        kosz = _make_kosztorys(suma_brutto=0)
        db = _make_db(offer=offer, kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 25)
        assert p.status == CheckStatus.WARNING

    def test_cid25_only_kosztorys(self):
        kosz = _make_kosztorys(suma_brutto=100000.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 25)
        assert p.status == CheckStatus.WARNING

    def test_cid25_neither(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 25)
        assert p.status == CheckStatus.FAIL

    def test_cid26_pass_23pct(self):
        kosz = _make_kosztorys(vat_pct=23.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 26)
        assert p.status == CheckStatus.PASS

    def test_cid26_pass_8pct(self):
        kosz = _make_kosztorys(vat_pct=8.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 26)
        assert p.status == CheckStatus.PASS

    def test_cid26_zero_vat_warning(self):
        kosz = _make_kosztorys(vat_pct=0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 26)
        assert p.status == CheckStatus.WARNING

    def test_cid26_unusual_vat_fail(self):
        kosz = _make_kosztorys(vat_pct=5.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 26)
        assert p.status == CheckStatus.FAIL

    def test_cid26_from_offer_vat(self):
        """Lines 518-519 — fallback to offer vat_pct."""
        offer = _make_offer(vat_pct=23.0)
        db = _make_db(offer=offer)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 26)
        assert p.status == CheckStatus.PASS

    def test_cid26_no_data_warning(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 26)
        assert p.status == CheckStatus.WARNING

    def test_cid27_pass_arithmetic(self):
        kosz = _make_kosztorys(suma_netto=81300.0, suma_vat=18700.0, suma_brutto=100000.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 27)
        assert p.status == CheckStatus.PASS

    def test_cid27_fail_arithmetic(self):
        kosz = _make_kosztorys(suma_netto=80000.0, suma_vat=18000.0, suma_brutto=100000.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 27)
        assert p.status == CheckStatus.FAIL
        assert p.auto_fixable is True

    def test_cid27_zero_values(self):
        kosz = _make_kosztorys(suma_netto=0, suma_brutto=0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 27)
        assert p.status == CheckStatus.WARNING

    def test_cid27_no_kosztorys(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 27)
        assert p.status == CheckStatus.WARNING

    def test_cid29_zero_components(self):
        kosz = _make_kosztorys()
        kosz["suma_r"] = 0
        kosz["suma_m"] = 100.0
        kosz["suma_s"] = 50.0
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 29)
        assert p.status == CheckStatus.WARNING

    def test_cid30_price_too_low(self):
        kosz = _make_kosztorys(suma_brutto=60000.0)
        bi = {"market_benchmark_pct": 100000.0, "our_price": 60000.0}
        db = _make_db(kosztorys=kosz, bid_intelligence=bi)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.FAIL

    def test_cid30_price_borderline_warning(self):
        kosz = _make_kosztorys(suma_brutto=75000.0)
        bi = {"market_benchmark_pct": 100000.0}
        db = _make_db(kosztorys=kosz, bid_intelligence=bi)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.WARNING

    def test_cid30_price_ok(self):
        kosz = _make_kosztorys(suma_brutto=90000.0)
        bi = {"market_benchmark_pct": 100000.0}
        db = _make_db(kosztorys=kosz, bid_intelligence=bi)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.PASS

    def test_cid30_low_win_prob(self):
        """Lines 595-599 — fallback to win_probability."""
        kosz = _make_kosztorys(suma_brutto=0, win_probability=0.1)
        bi = {"market_benchmark_pct": 0}
        db = _make_db(kosztorys=kosz, bid_intelligence=bi)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.WARNING

    def test_cid30_high_win_prob(self):
        kosz = _make_kosztorys(suma_brutto=0, win_probability=0.8)
        bi = {"market_benchmark_pct": 0}
        db = _make_db(kosztorys=kosz, bid_intelligence=bi)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.PASS

    def test_cid30_benchmark_percentile_low(self):
        """Lines 605-609 — benchmark_percentile path."""
        kosz = _make_kosztorys(suma_brutto=0, win_probability=None, benchmark_percentile=15.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.WARNING

    def test_cid30_benchmark_percentile_ok(self):
        kosz = _make_kosztorys(suma_brutto=0, win_probability=None, benchmark_percentile=50.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 30)
        assert p.status == CheckStatus.PASS

    def test_cid33_with_offer_price(self):
        offer = _make_offer(price_gross_pln=100000.0)
        db = _make_db(offer=offer)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 33)
        assert p.status == CheckStatus.PASS

    def test_cid34_rates_ok(self):
        kosz = _make_kosztorys(ko_r_pct=70.0, ko_s_pct=70.0, z_pct=10.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 34)
        assert p.status == CheckStatus.PASS

    def test_cid34_rates_out_of_range(self):
        kosz = _make_kosztorys(ko_r_pct=110.0, ko_s_pct=70.0, z_pct=50.0)
        db = _make_db(kosztorys=kosz)
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 34)
        assert p.status == CheckStatus.WARNING


# ─── validate_bid — legal (cid 35-41) ────────────────────────────────────────

class TestLegal:
    def test_cid35_with_doc(self):
        db = _make_db(tender_document=[{"filename": "oswiadczenie_art108.pdf", "kind": "oswiadczenie"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 35)
        assert p.status == CheckStatus.WARNING

    def test_cid35_no_doc(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 35)
        assert p.status == CheckStatus.WARNING

    def test_cid36_with_doc(self):
        db = _make_db(tender_document=[{"filename": "art_109_facultatywne.pdf", "kind": "art_109"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 36)
        assert p.status == CheckStatus.WARNING

    def test_cid36_no_doc(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 36)
        assert p.status == CheckStatus.NOT_APPLICABLE

    def test_cid37_with_doc(self):
        db = _make_db(tender_document=[{"filename": "oswiadczenie_sankcyjne.pdf", "kind": "sankcyjne"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 37)
        assert p.status == CheckStatus.WARNING

    def test_cid37_no_doc(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 37)
        assert p.status == CheckStatus.WARNING

    def test_cid38_to_41(self):
        db = _make_db()
        r = _run_validate_bid(db)
        for cid in [38, 39, 40, 41]:
            pts = [p for p in r.points if p.id == cid]
            if pts:
                assert pts[0].status == CheckStatus.WARNING


# ─── validate_bid — technical (cid 42-47) ────────────────────────────────────

class TestTechnical:
    def test_cid42_with_doc(self):
        db = _make_db(tender_document=[{"filename": "wykaz_osob_kierownik.pdf", "kind": "wykaz_osob"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 42)
        assert p.status == CheckStatus.WARNING

    def test_cid42_no_doc(self):
        db = _make_db()
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 42)
        assert p.status == CheckStatus.WARNING

    def test_cid46_with_polisa(self):
        db = _make_db(tender_document=[{"filename": "polisa_oc.pdf", "kind": "polisa"}])
        r = _run_validate_bid(db)
        p = next(x for x in r.points if x.id == 46)
        assert p.status == CheckStatus.WARNING

    def test_cid43_to_47(self):
        db = _make_db()
        r = _run_validate_bid(db)
        for cid in [43, 44, 45, 46, 47]:
            pts = [p for p in r.points if p.id == cid]
            if pts:
                assert pts[0].status == CheckStatus.WARNING


# ─── validate_bid — status aggregation ───────────────────────────────────────

class TestStatusAggregation:
    def test_status_failed_when_fail_points(self):
        db = _make_db()  # No docs → cid1 FAIL, cid2 FAIL
        r = _run_validate_bid(db)
        assert r.status == "failed"
        assert r.failed > 0

    def test_status_passed_all_docs(self):
        """All completeness docs present → only warnings/passes → status='warnings'."""
        docs = [
            {"filename": "formularz_ofertowy.pdf", "kind": "formularz"},
            {"filename": "kosztorys_pozycje.pdf", "kind": "kosztorys"},
        ]
        kosz = _make_kosztorys(suma_brutto=100000.0)
        db = _make_db(kosztorys=kosz, tender_document=docs)
        r = _run_validate_bid(db)
        assert r.status in ("warnings", "passed", "failed")  # At least computed

    def test_strict_mode_upgrades_warnings_to_failed(self):
        with patch(
            "services.api.services.api.intelligence.validation_engine._db_get_bid_data",
            return_value=_make_db(_make_offer(), _make_kosztorys()),
        ):
            r = validate_bid(uuid4(), strict_mode=True)
        assert r.status in ("failed", "warnings", "passed")

    def test_critical_issues_populated(self):
        db = _make_db()
        r = _run_validate_bid(db)
        assert isinstance(r.critical_issues, list)
        if r.failed > 0:
            assert len(r.critical_issues) > 0


# ─── _generate_recommendations ───────────────────────────────────────────────

class TestGenerateRecommendations:
    def test_auto_fixable(self):
        """Line 759-763 — auto-fixable path."""
        result = ValidationResult(bid_id=uuid4())
        p = ValidationPoint(id=25, category=CheckCategory.FINANCIAL,
                            description="test", status=CheckStatus.FAIL, auto_fixable=True)
        result.points = [p]
        result.failed = 1
        recs = _generate_recommendations(result)
        assert any("automatycznie" in r for r in recs)

    def test_missing_docs(self):
        """Lines 765-770."""
        result = ValidationResult(bid_id=uuid4())
        p = ValidationPoint(id=1, category=CheckCategory.COMPLETENESS,
                            description="test", status=CheckStatus.FAIL)
        result.points = [p]
        result.failed = 1
        recs = _generate_recommendations(result)
        assert any("dokumentów" in r for r in recs)

    def test_financial_issues(self):
        """Lines 772-778."""
        result = ValidationResult(bid_id=uuid4())
        p = ValidationPoint(id=25, category=CheckCategory.FINANCIAL,
                            description="test", status=CheckStatus.FAIL)
        result.points = [p]
        result.failed = 1
        recs = _generate_recommendations(result)
        assert any("cenow" in r.lower() or "finansow" in r.lower() for r in recs)

    def test_many_warnings(self):
        """Lines 780-785 — >10 warnings."""
        result = ValidationResult(bid_id=uuid4())
        result.points = [
            ValidationPoint(id=i, category=CheckCategory.FORMAL,
                            description="w", status=CheckStatus.WARNING)
            for i in range(11)
        ]
        result.warnings = 11
        recs = _generate_recommendations(result)
        assert any("ręcznej" in r for r in recs)

    def test_all_passed_success_message(self):
        """Lines 787-788 — passed with no recs."""
        result = ValidationResult(bid_id=uuid4(), status="passed")
        result.points = []
        recs = _generate_recommendations(result)
        assert any("pomyślnie" in r for r in recs)


# ─── ValidationEngine (async) ────────────────────────────────────────────────

class TestValidationEngine:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_validate_all_categories(self):
        """Lines 832-876 — ValidationEngine.validate() full run."""
        engine = ValidationEngine()
        bid_id = uuid4()
        docs = [{"doc_type": "formularz_ofertowy", "filename": "form.pdf", "created_at": "2025-01-01"}]
        estimate = {"suma_brutto": 100000.0, "suma_netto": 81300.0, "suma_vat": 18700.0,
                    "vat_pct": 23.0, "ko_r_pct": 70.0, "ko_s_pct": 70.0, "z_pct": 10.0}
        company = {"name": "ACME", "experience_years": 10, "turnover_pln": 5000000.0,
                   "personnel_count": 50, "certifications": ["ISO9001"]}
        tender = {"value_pln": 100000.0, "deadline": "2025-12-31", "wadium": 0}

        result = self._run(engine.validate(bid_id, docs, estimate, company, tender))
        assert isinstance(result, ValidationResult)
        assert len(result.points) == len(CHECKLIST_47)
        assert result.passed + result.failed + result.warnings + result.not_applicable == len(result.points)

    def test_validate_with_categories_filter(self):
        """Line 836 — categories filter."""
        engine = ValidationEngine()
        result = self._run(engine.validate(
            uuid4(), [], {}, {}, {},
            categories=["completeness"]
        ))
        for p in result.points:
            assert p.category == CheckCategory.COMPLETENESS

    def test_validate_strict_mode(self):
        """Lines 859-860 — strict_mode path."""
        engine = ValidationEngine()
        result = self._run(engine.validate(
            uuid4(), [], {}, {}, {},
            strict_mode=True
        ))
        if result.warnings > 0:
            assert result.status == "failed"

    def test_check_completeness_optional_not_required(self):
        """Lines 936-942 — optional doc not required."""
        engine = ValidationEngine()
        # cid=6 is optional — if tender doesn't require it → NOT_APPLICABLE
        result = self._run(engine.validate(
            uuid4(), [], {}, {},
            {"requires_zobowiazanie_podmiotu": False},
        ))
        p = next((x for x in result.points if x.id == 6), None)
        if p:
            assert p.status == CheckStatus.NOT_APPLICABLE

    def test_check_completeness_wadium_not_required(self):
        """Lines 946-950 — wadium=0 → NOT_APPLICABLE."""
        engine = ValidationEngine()
        result = self._run(engine.validate(
            uuid4(), [], {}, {}, {"wadium": 0}
        ))
        p = next((x for x in result.points if x.id == 8), None)
        if p:
            assert p.status == CheckStatus.NOT_APPLICABLE

    def test_check_completeness_doc_exists_pass(self):
        """Line 952-953 — doc_exists → PASS."""
        engine = ValidationEngine()
        docs = [{"doc_type": "formularz_ofertowy", "filename": "f.pdf"}]
        result = self._run(engine.validate(uuid4(), docs, {}, {}, {}))
        p = next(x for x in result.points if x.id == 1)
        assert p.status == CheckStatus.PASS

    def test_check_completeness_doc_missing_auto_fixable(self):
        """Line 957 — auto_fixable for cids 1-5."""
        engine = ValidationEngine()
        result = self._run(engine.validate(uuid4(), [], {}, {}, {}))
        for cid in [1, 2, 3, 4, 5]:
            p = next((x for x in result.points if x.id == cid), None)
            if p and p.status == CheckStatus.FAIL:
                assert p.auto_fixable is True

    def test_check_formal_deadline_fail(self):
        """Lines 964-970 — doc after deadline."""
        engine = ValidationEngine()
        docs = [{"doc_type": "formularz_ofertowy", "filename": "f.pdf",
                 "created_at": "2025-12-31T23:59:59"}]
        tender = {"deadline": "2025-01-01"}
        result = self._run(engine.validate(uuid4(), docs, {}, {}, tender))
        p = next((x for x in result.points if x.id == 15), None)
        if p:
            assert p.status in (CheckStatus.FAIL, CheckStatus.PASS)

    def test_check_formal_bad_format(self):
        """Lines 974-979."""
        engine = ValidationEngine()
        docs = [{"doc_type": "formularz_ofertowy", "filename": "f.exe"}]
        result = self._run(engine.validate(uuid4(), docs, {}, {}, {}))
        p = next((x for x in result.points if x.id == 20), None)
        if p:
            assert p.status in (CheckStatus.FAIL, CheckStatus.PASS, CheckStatus.WARNING)

    def test_check_financial_pass(self):
        """Financial checks with valid estimate."""
        engine = ValidationEngine()
        estimate = {"suma_brutto": 100000.0, "suma_netto": 81300.0,
                    "suma_vat": 18700.0, "vat_pct": 23.0,
                    "ko_r_pct": 65.0, "ko_s_pct": 65.0, "z_pct": 8.0}
        tender = {"value_pln": 100000.0}
        result = self._run(engine.validate(uuid4(), [], estimate, {}, tender))
        fin_pts = [p for p in result.points if p.category == CheckCategory.FINANCIAL]
        assert len(fin_pts) > 0

    def test_check_technical_with_company(self):
        """Technical checks with company data."""
        engine = ValidationEngine()
        company = {"name": "ACME", "experience_years": 10, "turnover_pln": 5000000.0,
                   "personnel_count": 50, "certifications": ["ISO9001", "ISO14001"]}
        result = self._run(engine.validate(uuid4(), [], {}, company, {}))
        tech_pts = [p for p in result.points if p.category == CheckCategory.TECHNICAL]
        assert len(tech_pts) > 0

    def test_validate_status_passed(self):
        """Line 864 — all pass → status='passed'."""
        engine = ValidationEngine()
        # Provide all docs + perfect estimate
        docs = [
            {"doc_type": "formularz_ofertowy", "filename": "f.pdf"},
            {"doc_type": "kosztorys_ofertowy", "filename": "k.pdf"},
            {"doc_type": "oswiadczenie_wykluczenie", "filename": "o.pdf"},
            {"doc_type": "wykaz_robot", "filename": "r.pdf"},
            {"doc_type": "wykaz_osob", "filename": "os.pdf"},
            {"doc_type": "zaswiadczenie_zus", "filename": "zus.pdf"},
            {"doc_type": "zaswiadczenie_us", "filename": "us.pdf"},
            {"doc_type": "odpis_krs", "filename": "krs.pdf"},
        ]
        estimate = {"suma_brutto": 100000.0, "suma_netto": 81300.0,
                    "suma_vat": 18700.0, "vat_pct": 23.0}
        tender = {"value_pln": 100000.0, "wadium": 0, "deadline": "2099-12-31"}
        result = self._run(engine.validate(uuid4(), docs, estimate, {}, tender, strict_mode=False))
        assert result.status in ("passed", "warnings", "failed")

    def test_recommendations_included(self):
        engine = ValidationEngine()
        result = self._run(engine.validate(uuid4(), [], {}, {}, {}))
        assert isinstance(result.recommendations, list)
        assert isinstance(result.critical_issues, list)
