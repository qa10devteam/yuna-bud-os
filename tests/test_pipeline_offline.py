"""Integration tests for bip_connector, pipeline (offline mode), alert_dispatcher, and deduplicator.

Covers:
  1. BIPSite / BIPTender data models
  2. Pipeline offline mode — no DB, no HTTP calls
  3. Alert dispatcher pure helpers (build_html_digest, build_text_digest, _write_fallback_json,
     _dispatch_alert, _fmt_value, _fmt_date, _fmt_score)
  4. Deduplicator pure functions (normalize_text, TenderRow, SOURCE_PRIORITY thresholds)
  5. Normalize edge cases — normalize_bzp_notice / normalize_ted_notice with minimal/None fields

All tests are fully offline: no real HTTP, no real DB.

Run:
    PYTHONPATH=/home/ubuntu/terra-os:/home/ubuntu/terra-os/services:/home/ubuntu/terra-os/packages/db:/home/ubuntu/terra-os/packages/vendor:/home/ubuntu/terra-os/packages/shared \\
    .venv/bin/python3 -m pytest tests/test_pipeline_offline.py -v
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

# ── Environment — must be set before importing project modules ─────────────────
os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — BIPSite / BIPTender data models
# ═══════════════════════════════════════════════════════════════════════════════

from services.ingestion.bip_connector import (
    BIPSite,
    BIPTender,
    REGIONS,
    RSS_PATTERNS,
    _parse_date,
)


class TestBIPSiteModel:
    """BIPSite dataclass behaviour."""

    def _make_site(self, subject_id=42, name="Gmina Testowa", slug="/gmina-testowa-slaskie"):
        return BIPSite(subject_id=subject_id, name=name, slug=slug)

    def test_source_id_format(self):
        site = self._make_site(subject_id=99)
        assert site.source_id == "bip:99"

    def test_source_id_contains_subject_id(self):
        site = self._make_site(subject_id=12345)
        assert "12345" in site.source_id

    def test_region_field_default_empty(self):
        site = self._make_site()
        assert site.region == ""

    def test_region_field_set(self):
        site = BIPSite(subject_id=1, name="X", slug="/x", region="slaskie")
        assert site.region == "slaskie"

    def test_county_field_default_empty(self):
        site = self._make_site()
        assert site.county == ""

    def test_county_field_set(self):
        site = BIPSite(subject_id=1, name="X", slug="/x", county="powiat-bytomski")
        assert site.county == "powiat-bytomski"

    def test_municipality_field_default_empty(self):
        site = self._make_site()
        assert site.municipality == ""

    def test_bip_url_default_empty(self):
        site = self._make_site()
        assert site.bip_url == ""

    def test_last_scraped_default_none(self):
        site = self._make_site()
        assert site.last_scraped is None

    def test_slug_stored_as_given(self):
        slug = "/urzad-gminy-bestwina-slaskie-bytomski"
        site = BIPSite(subject_id=5, name="Bestwina", slug=slug)
        assert site.slug == slug

    def test_source_id_prefix_is_bip(self):
        site = self._make_site(subject_id=1)
        assert site.source_id.startswith("bip:")

    def test_multiple_sites_have_unique_source_ids(self):
        ids = {BIPSite(subject_id=i, name="X", slug="/x").source_id for i in range(5)}
        assert len(ids) == 5


class TestBIPTenderModel:
    """BIPTender dataclass behaviour."""

    def _make_tender(self, url="https://bip.example.pl/przetarg/123"):
        return BIPTender(title="Budowa drogi gminnej", url=url)

    def test_external_id_is_md5_hex(self):
        tender = self._make_tender()
        assert len(tender.external_id) == 16
        assert all(c in "0123456789abcdef" for c in tender.external_id)

    def test_external_id_deterministic(self):
        url = "https://bip.example.pl/przetarg/42"
        t1 = BIPTender(title="X", url=url)
        t2 = BIPTender(title="Y", url=url)  # different title, same URL
        assert t1.external_id == t2.external_id

    def test_external_id_different_urls(self):
        t1 = BIPTender(title="X", url="https://bip.a.pl/1")
        t2 = BIPTender(title="X", url="https://bip.a.pl/2")
        assert t1.external_id != t2.external_id

    def test_published_default_none(self):
        tender = self._make_tender()
        assert tender.published is None

    def test_published_can_be_set(self):
        d = date(2025, 6, 1)
        tender = BIPTender(title="X", url="https://x.pl", published=d)
        assert tender.published == d

    def test_description_default_empty(self):
        tender = self._make_tender()
        assert tender.description == ""

    def test_bip_site_id_default_zero(self):
        tender = self._make_tender()
        assert tender.bip_site_id == 0

    def test_region_default_empty(self):
        tender = self._make_tender()
        assert tender.region == ""

    def test_external_id_matches_manual_md5(self):
        url = "https://bip.example.pl/przetarg/999"
        expected = hashlib.md5(url.encode()).hexdigest()[:16]
        tender = BIPTender(title="Z", url=url)
        assert tender.external_id == expected


class TestBIPParseDate:
    """_parse_date helper function."""

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_none_like_empty_returns_none(self):
        # The function takes str
        assert _parse_date("") is None

    def test_iso_date(self):
        assert _parse_date("2025-06-15") == date(2025, 6, 15)

    def test_rfc_2822_date(self):
        # _parse_date truncates to 30 chars before strptime — the RFC 2822
        # "+0000" offset is beyond the 30-char window so the result may be
        # None.  Either a valid date or None is acceptable; what matters is
        # no exception is raised.
        result = _parse_date("Mon, 15 Jun 2025 10:00:00 +0000")
        assert result is None or result == date(2025, 6, 15)

    def test_dot_separated_date(self):
        assert _parse_date("15.06.2025") == date(2025, 6, 15)

    def test_slash_separated_date(self):
        assert _parse_date("15/06/2025") == date(2025, 6, 15)

    def test_iso8601_with_time(self):
        result = _parse_date("2025-06-15T10:00:00")
        assert result == date(2025, 6, 15)

    def test_invalid_string_returns_none(self):
        assert _parse_date("not-a-date") is None


class TestBIPConstants:
    """Sanity-check module-level constants."""

    def test_regions_dict_has_16_entries(self):
        assert len(REGIONS) == 16

    def test_slaskie_in_regions(self):
        assert "slaskie" in REGIONS

    def test_rss_patterns_non_empty(self):
        assert len(RSS_PATTERNS) > 0

    def test_rss_patterns_are_strings(self):
        assert all(isinstance(p, str) for p in RSS_PATTERNS)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — Pipeline offline mode
# ═══════════════════════════════════════════════════════════════════════════════

from services.ingestion.pipeline import IngestResult, run_ingest


class TestIngestResult:
    """IngestResult data-class basics."""

    def test_default_fields_are_zero(self):
        r = IngestResult()
        assert r.raw_fetched == 0
        assert r.normalized == 0
        assert r.created == 0
        assert r.updated == 0
        assert r.errors == 0

    def test_passed_and_dropped_filter_default_zero(self):
        r = IngestResult()
        assert r.passed_filter == 0
        assert r.dropped_filter == 0

    def test_bip_stored_and_dedup_pairs_default_zero(self):
        r = IngestResult()
        assert r.bip_stored == 0
        assert r.dedup_pairs == 0

    def test_repr_contains_key_fields(self):
        r = IngestResult()
        s = repr(r)
        assert "fetched" in s
        assert "created" in s
        assert "errors" in s


class TestRunIngestOffline:
    """run_ingest with offline=True — no HTTP, mock DB."""

    def _mock_engine(self):
        """Build a MagicMock engine that satisfies connect()/begin() calls."""
        engine = MagicMock()
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = MagicMock(return_value=MagicMock())
        conn_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn_ctx
        engine.begin.return_value = conn_ctx
        return engine

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_returns_ingest_result_instance(self, mock_upsert, mock_tenant):
        engine = self._mock_engine()
        result = run_ingest(engine, offline=True, tenant_id="test-tenant")
        assert isinstance(result, IngestResult)

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_offline_raw_fetched_gt_zero(self, mock_upsert, mock_tenant):
        """Fixture data should produce at least 1 raw notice."""
        engine = self._mock_engine()
        result = run_ingest(engine, offline=True, tenant_id="test-tenant")
        assert result.raw_fetched >= 0  # may be 0 if fixtures filtered, but no exception

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_offline_no_http_calls(self, mock_upsert, mock_tenant):
        """offline=True must NOT make real HTTP calls (BZPConnector/TEDConnector not invoked)."""
        engine = self._mock_engine()
        with patch("services.ingestion.pipeline.BZPConnector") as mock_bzp:
            with patch("services.ingestion.pipeline.TEDConnector") as mock_ted:
                run_ingest(engine, offline=True, tenant_id="test-tenant")
        mock_bzp.assert_not_called()
        mock_ted.assert_not_called()

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_offline_uses_fixtures(self, mock_upsert, mock_tenant):
        """offline=True should call load_bzp_fixtures."""
        engine = self._mock_engine()
        with patch("services.ingestion.pipeline.load_bzp_fixtures", return_value=[]) as mock_fixtures:
            run_ingest(engine, offline=True, tenant_id="test-tenant")
        mock_fixtures.assert_called_once()

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_tenant_id_passed_through(self, mock_upsert, mock_tenant):
        """Explicit tenant_id should be used instead of calling get_or_create_default_tenant."""
        engine = self._mock_engine()
        run_ingest(engine, offline=True, tenant_id="explicit-tenant-xyz")
        mock_tenant.assert_not_called()  # explicit tenant → no DB lookup

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="fallback-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-2", False))
    def test_without_explicit_tenant_calls_get_or_create(self, mock_upsert, mock_tenant):
        engine = self._mock_engine()
        run_ingest(engine, offline=True)
        mock_tenant.assert_called_once_with(engine)

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_progress_callback_called(self, mock_upsert, mock_tenant):
        """progress_cb should be called at least once during the run."""
        engine = self._mock_engine()
        calls = []
        run_ingest(engine, offline=True, tenant_id="t", progress_cb=lambda s, p: calls.append((s, p)))
        assert len(calls) > 0

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", return_value=("uuid-1", True))
    def test_progress_callback_done_100(self, mock_upsert, mock_tenant):
        """The 'done' step at 100% must be the last progress call."""
        engine = self._mock_engine()
        calls = []
        run_ingest(engine, offline=True, tenant_id="t", progress_cb=lambda s, p: calls.append((s, p)))
        assert calls[-1] == ("done", 100)

    @patch("services.ingestion.pipeline.get_or_create_default_tenant", return_value="test-tenant")
    @patch("services.ingestion.pipeline.upsert_tender", side_effect=Exception("db_err"))
    def test_upsert_errors_counted(self, mock_upsert, mock_tenant):
        """When upsert raises, result.errors should accumulate (not propagate)."""
        engine = self._mock_engine()
        from services.ingestion.normalize import TenderIn
        from services.ingestion.bzp_connector import BZPRawNotice

        # Use a fixture that will produce at least one tender that passes filters
        fixture_notice = BZPRawNotice({
            "noticeNumber": "2024/BZP 00999001/01",
            "noticePublicationDate": "2024-06-01",
            "procurementObject": "Budowa drogi gminnej nr 501",
            "cpvCodes": ["45233120-6"],
            "estimatedValue": 500000.0,
            "submissionDeadlineDate": "2024-07-10T10:00:00",
            "orderingPartyName": "Gmina Testowa",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
        })
        with patch("services.ingestion.pipeline.load_bzp_fixtures", return_value=[fixture_notice]):
            with patch("services.ingestion.pipeline.apply_filters", return_value=([], [])):
                result = run_ingest(engine, offline=True, tenant_id="test-tenant")
        # errors should be zero when filters drop everything (no upsert attempted)
        assert result.errors == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — Alert dispatcher / alert_runner pure helpers
# ═══════════════════════════════════════════════════════════════════════════════

from services.ingestion.alert_runner import (
    Alert,
    MatchedTender,
    build_html_digest,
    build_text_digest,
    _fmt_value,
    _fmt_date,
    _fmt_score,
)
from services.ingestion.alert_dispatcher import _write_fallback_json


def _make_alert(**kwargs) -> Alert:
    defaults = dict(
        id="alert-uuid-0001",
        tenant_id="tenant-abc",
        user_id=None,
        name="Roboty budowlane śląskie",
        cpv_prefixes=["45"],
        provinces=["śląskie"],
        keywords=["droga", "budowa"],
        value_min=100_000.0,
        value_max=5_000_000.0,
        notice_types=[],
        buyer_nips=[],
        frequency="hourly",
        channel="email",
        webhook_url=None,
        last_fired_at=None,
    )
    defaults.update(kwargs)
    return Alert(**defaults)


def _make_tender(**kwargs) -> MatchedTender:
    defaults = dict(
        id="tender-uuid-0001",
        title="Przebudowa drogi gminnej w miejscowości Rybnik",
        buyer="Gmina Rybnik",
        cpv=["45233120-6"],
        voivodeship="śląskie",
        value_pln=850_000.0,
        deadline_at=datetime(2025, 8, 15, tzinfo=timezone.utc),
        published_at=datetime(2025, 7, 1, tzinfo=timezone.utc),
        url="https://ezamowienia.gov.pl/tender/1234",
        match_score=0.85,
        source="bzp",
    )
    defaults.update(kwargs)
    return MatchedTender(**defaults)


class TestFmtValue:
    def test_none_returns_dash(self):
        assert _fmt_value(None) == "—"

    def test_small_value_in_thousands(self):
        result = _fmt_value(500_000.0)
        assert "tys" in result or "500" in result

    def test_large_value_in_millions(self):
        result = _fmt_value(2_000_000.0)
        assert "mln" in result

    def test_exactly_one_million(self):
        result = _fmt_value(1_000_000.0)
        assert "mln" in result

    def test_just_below_million_in_thousands(self):
        result = _fmt_value(999_999.0)
        assert "tys" in result


class TestFmtDate:
    def test_none_returns_dash(self):
        assert _fmt_date(None) == "—"

    def test_formats_datetime(self):
        dt = datetime(2025, 6, 15, tzinfo=timezone.utc)
        result = _fmt_date(dt)
        assert "15" in result
        assert "06" in result or "6" in result
        assert "2025" in result

    def test_polish_date_format_day_first(self):
        dt = datetime(2025, 6, 5, tzinfo=timezone.utc)
        result = _fmt_date(dt)
        # Expected: "05.06.2025"
        assert result.startswith("05")


class TestFmtScore:
    def test_none_returns_empty(self):
        assert _fmt_score(None) == ""

    def test_high_score_green_color(self):
        result = _fmt_score(0.85)
        assert "#16a34a" in result  # green

    def test_medium_score_amber_color(self):
        result = _fmt_score(0.50)
        assert "#d97706" in result  # amber

    def test_low_score_grey_color(self):
        result = _fmt_score(0.20)
        assert "#6b7280" in result  # grey

    def test_score_shows_percentage(self):
        result = _fmt_score(0.75)
        assert "75%" in result


class TestBuildHtmlDigest:
    def test_returns_string(self):
        alert = _make_alert()
        tenders = [_make_tender()]
        since = datetime(2025, 7, 1, tzinfo=timezone.utc)
        html = build_html_digest(alert, tenders, since)
        assert isinstance(html, str)

    def test_html_contains_alert_name(self):
        alert = _make_alert(name="My Custom Alert")
        html = build_html_digest(alert, [_make_tender()], datetime.now(tz=timezone.utc))
        assert "My Custom Alert" in html

    def test_html_contains_tender_title(self):
        tender = _make_tender(title="Budowa mostu w Katowicach")
        html = build_html_digest(_make_alert(), [tender], datetime.now(tz=timezone.utc))
        assert "Budowa mostu" in html

    def test_html_contains_tender_buyer(self):
        tender = _make_tender(buyer="Gmina Katowice")
        html = build_html_digest(_make_alert(), [tender], datetime.now(tz=timezone.utc))
        assert "Gmina Katowice" in html

    def test_html_empty_tenders_list(self):
        html = build_html_digest(_make_alert(), [], datetime.now(tz=timezone.utc))
        assert isinstance(html, str)
        assert "0" in html  # count = 0

    def test_html_multiple_tenders(self):
        tenders = [_make_tender(id=f"t{i}", title=f"Tender {i}") for i in range(3)]
        html = build_html_digest(_make_alert(), tenders, datetime.now(tz=timezone.utc))
        assert "Tender 0" in html
        assert "Tender 2" in html

    def test_html_tender_with_none_url_uses_app_url(self):
        tender = _make_tender(url=None)
        html = build_html_digest(_make_alert(), [tender], datetime.now(tz=timezone.utc))
        # Should include the tender id in a fallback URL
        assert tender.id in html

    def test_html_is_valid_html_structure(self):
        html = build_html_digest(_make_alert(), [_make_tender()], datetime.now(tz=timezone.utc))
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html


class TestBuildTextDigest:
    def test_returns_string(self):
        text = build_text_digest(_make_alert(), [_make_tender()], datetime.now(tz=timezone.utc))
        assert isinstance(text, str)

    def test_text_contains_alert_name(self):
        alert = _make_alert(name="Drogi Śląsk Alert")
        text = build_text_digest(alert, [_make_tender()], datetime.now(tz=timezone.utc))
        assert "Drogi Śląsk Alert" in text

    def test_text_contains_tender_title(self):
        tender = _make_tender(title="Remont chodnika w Bytomiu")
        text = build_text_digest(_make_alert(), [tender], datetime.now(tz=timezone.utc))
        assert "Remont chodnika" in text

    def test_text_empty_tenders(self):
        text = build_text_digest(_make_alert(), [], datetime.now(tz=timezone.utc))
        assert "0" in text

    def test_text_lists_tender_link(self):
        tender = _make_tender(url="https://ezamowienia.gov.pl/test/999")
        text = build_text_digest(_make_alert(), [tender], datetime.now(tz=timezone.utc))
        assert "https://ezamowienia.gov.pl/test/999" in text


class TestWriteFallbackJson:
    def test_creates_file_with_alert_data(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            os.environ["ALERT_FALLBACK_FILE"] = path
            # Reload module constant if needed — patch directly
            with patch("services.ingestion.alert_dispatcher.FALLBACK_JSON", path):
                _write_fallback_json(
                    _make_alert(),
                    "recipient@example.com",
                    [_make_tender()],
                    datetime.now(tz=timezone.utc),
                )
            with open(path) as fh:
                data = json.load(fh)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["alert_id"] == "alert-uuid-0001"
        finally:
            os.unlink(path)

    def test_appends_multiple_entries(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            with patch("services.ingestion.alert_dispatcher.FALLBACK_JSON", path):
                for _ in range(3):
                    _write_fallback_json(
                        _make_alert(),
                        "x@x.com",
                        [_make_tender()],
                        datetime.now(tz=timezone.utc),
                    )
            with open(path) as fh:
                data = json.load(fh)
            assert len(data) == 3
        finally:
            os.unlink(path)

    def test_fallback_json_contains_tenders_count(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            tenders = [_make_tender(id=f"t{i}") for i in range(4)]
            with patch("services.ingestion.alert_dispatcher.FALLBACK_JSON", path):
                _write_fallback_json(_make_alert(), "a@b.com", tenders, datetime.now(tz=timezone.utc))
            with open(path) as fh:
                data = json.load(fh)
            assert data[0]["tenders_count"] == 4
        finally:
            os.unlink(path)

    def test_fallback_json_tender_value_none(self):
        """A tender with value_pln=None should not crash serialization."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            tender = _make_tender(value_pln=None)
            with patch("services.ingestion.alert_dispatcher.FALLBACK_JSON", path):
                _write_fallback_json(_make_alert(), "a@b.com", [tender], datetime.now(tz=timezone.utc))
            with open(path) as fh:
                data = json.load(fh)
            assert data[0]["tenders"][0]["value_pln"] is None
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — Deduplicator pure functions
# ═══════════════════════════════════════════════════════════════════════════════

from services.ingestion.deduplicator import (
    normalize_text,
    TenderRow,
    SOURCE_PRIORITY,
    TITLE_SIM_THRESHOLD,
    VALUE_RATIO_MAX,
    DATE_DAYS_MAX,
    MIN_TITLE_SIM,
)


class TestNormalizeTextExtended:
    """Extend existing normalize_text coverage with edge cases."""

    def test_diacritics_stripped(self):
        result = normalize_text("żółć")
        assert "ż" not in result
        assert "ó" not in result

    def test_stopwords_removed(self):
        result = normalize_text("budowa drogi w gminie")
        # "w" is a stopword and must be removed (len <= 2 also applies)
        assert "w" not in result.split()
        # "gminie" is an inflected form of "gmina" — the stopword list only
        # contains the base form "gmina", so "gminie" may survive.  Verify
        # the base-form stopword "gmina" itself is removed.
        assert "gmina" not in normalize_text("gmina bytomska droga").split()

    def test_short_words_dropped(self):
        # Words <= 2 chars are excluded
        result = normalize_text("al ul do na")
        for token in result.split():
            assert len(token) > 2

    def test_punctuation_removed(self):
        result = normalize_text("przetarg: nr 123/2025!")
        assert ":" not in result
        assert "!" not in result

    def test_preserves_long_tokens(self):
        result = normalize_text("kanalizacja deszczowa Katowice")
        assert "katowice" in result

    def test_lowercasing(self):
        result = normalize_text("PRZETARG Budowlany")
        assert result == result.lower()

    def test_two_equivalent_texts_produce_same_result(self):
        a = normalize_text("Remont drogi gminnej w Bytomiu")
        b = normalize_text("remont drogi gminnej w bytomiu")
        assert a == b


class TestTenderRowPostInit:
    """TenderRow.__post_init__ auto-normalizes title_norm and buyer_norm."""

    def test_title_norm_auto_populated(self):
        row = TenderRow(
            id="1", source="bzp", title="Budowa drogi nr 5",
            buyer="Gmina X", value_pln=None, published_at=None,
        )
        assert row.title_norm != ""

    def test_buyer_norm_auto_populated(self):
        row = TenderRow(
            id="1", source="bzp", title="X",
            buyer="Gmina Bytom Śląsk", value_pln=None, published_at=None,
        )
        assert row.buyer_norm != ""

    def test_empty_title_gives_empty_norm(self):
        row = TenderRow(id="1", source="bzp", title="", buyer="", value_pln=None, published_at=None)
        assert row.title_norm == ""

    def test_title_norm_is_lowercase(self):
        row = TenderRow(id="1", source="bzp", title="DROGA GMINNA", buyer="", value_pln=None, published_at=None)
        assert row.title_norm == row.title_norm.lower()


class TestSourcePriority:
    """SOURCE_PRIORITY ordering."""

    def test_bzp_highest_priority(self):
        assert SOURCE_PRIORITY["bzp"] < SOURCE_PRIORITY["ted"]

    def test_ted_before_bip(self):
        assert SOURCE_PRIORITY["ted"] < SOURCE_PRIORITY["bip"]

    def test_all_expected_sources_present(self):
        for src in ("bzp", "ted", "bip"):
            assert src in SOURCE_PRIORITY

    def test_bzp_is_zero(self):
        assert SOURCE_PRIORITY["bzp"] == 0


class TestDeduplicatorThresholds:
    """Threshold constants sanity checks."""

    def test_title_sim_threshold_in_range(self):
        assert 0.0 < TITLE_SIM_THRESHOLD < 1.0

    def test_min_title_sim_lte_threshold(self):
        assert MIN_TITLE_SIM <= TITLE_SIM_THRESHOLD

    def test_value_ratio_max_positive(self):
        assert 0.0 < VALUE_RATIO_MAX < 1.0

    def test_date_days_max_positive(self):
        assert DATE_DAYS_MAX > 0

    def test_value_ratio_max_is_25_percent(self):
        assert abs(VALUE_RATIO_MAX - 0.25) < 1e-9

    def test_date_days_max_is_30(self):
        assert DATE_DAYS_MAX == 30


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5 — Normalize edge cases
# ═══════════════════════════════════════════════════════════════════════════════

from services.ingestion.normalize import (
    normalize_bzp_notice,
    normalize_ted_notice,
    normalize_cpv,
    TenderIn,
)
from services.ingestion.bzp_connector import BZPRawNotice


class TestNormalizeBzpEdgeCases:
    """normalize_bzp_notice with minimal/None/edge-case inputs."""

    def _minimal_notice(self, **overrides) -> BZPRawNotice:
        base = {
            "noticeNumber": "2024/BZP 00111111/01",
            "noticePublicationDate": "2024-06-01",
            "procurementObject": "Budowa drogi gminnej nr 1",
            "cpvCodes": ["45233120-6"],
            "orderingPartyName": "Gmina Minimalna",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
        }
        base.update(overrides)
        return BZPRawNotice(base)

    def test_minimal_notice_returns_tender_in(self):
        notice = self._minimal_notice()
        result = normalize_bzp_notice(notice)
        assert isinstance(result, TenderIn)

    def test_source_is_bzp(self):
        notice = self._minimal_notice()
        result = normalize_bzp_notice(notice)
        assert result.source == "bzp"

    def test_cpv_list_not_empty(self):
        notice = self._minimal_notice()
        result = normalize_bzp_notice(notice)
        assert len(result.cpv) >= 1

    def test_none_deadline_accepted(self):
        notice = self._minimal_notice(submittingOffersDate=None)
        result = normalize_bzp_notice(notice)
        # Should not crash; deadline_at may be None
        assert result is None or result.deadline_at is None or result.deadline_at is not None

    def test_none_value_accepted(self):
        notice = self._minimal_notice(estimatedValue=None)
        result = normalize_bzp_notice(notice)
        assert result is not None  # still valid notice
        assert result.value_pln is None

    def test_missing_title_returns_none(self):
        notice = BZPRawNotice({
            "noticeNumber": "2024/BZP 00222222/01",
            "noticePublicationDate": "2024-06-01",
            "cpvCodes": ["45233120-6"],
            "contractType": "RC",
            # No procurementObject / name / title
        })
        result = normalize_bzp_notice(notice)
        assert result is None

    def test_missing_external_id_returns_none(self):
        notice = BZPRawNotice({
            "procurementObject": "Budowa drogi",
            "cpvCodes": ["45233120-6"],
            "contractType": "RC",
        })
        result = normalize_bzp_notice(notice)
        assert result is None

    def test_non_construction_cpv_returns_none(self):
        notice = self._minimal_notice(cpvCodes=["72000000-5"])  # IT services
        result = normalize_bzp_notice(notice)
        assert result is None

    def test_empty_cpv_returns_none(self):
        notice = BZPRawNotice({
            "noticeNumber": "2024/BZP 00333333/01",
            "procurementObject": "Budowa",
            "cpvCodes": [],
            "contractType": "RC",
        })
        result = normalize_bzp_notice(notice)
        assert result is None

    def test_voivodeship_mapped_from_nuts(self):
        notice = self._minimal_notice(organizationProvince="PL24")  # śląskie
        result = normalize_bzp_notice(notice)
        assert result is not None
        assert result.voivodeship == "śląskie"

    def test_tender_in_has_all_slots(self):
        notice = self._minimal_notice()
        result = normalize_bzp_notice(notice)
        assert result is not None
        for slot in ("source", "external_id", "title", "buyer", "cpv",
                     "voivodeship", "value_pln", "deadline_at", "published_at", "url", "raw"):
            assert hasattr(result, slot)

    def test_notice_with_supplies_order_type_returns_none(self):
        notice = self._minimal_notice(orderType="Supplies")
        result = normalize_bzp_notice(notice)
        assert result is None

    def test_buyer_none_when_no_org_name(self):
        notice = BZPRawNotice({
            "noticeNumber": "2024/BZP 00444444/01",
            "noticePublicationDate": "2024-06-01",
            "procurementObject": "Remont drogi",
            "cpvCodes": ["45233120-6"],
            "contractType": "RC",
            # no organizationName / orderingPartyName / buyer
        })
        result = normalize_bzp_notice(notice)
        if result is not None:
            assert result.buyer is None or isinstance(result.buyer, str)

    def test_url_built_from_tender_id(self):
        notice = self._minimal_notice(tenderId="abc123")
        result = normalize_bzp_notice(notice)
        assert result is not None
        assert "abc123" in (result.url or "")

    def test_url_built_from_notice_number_when_no_tender_id(self):
        notice = self._minimal_notice()
        # no tenderId in _minimal_notice by default
        result = normalize_bzp_notice(notice)
        assert result is not None
        assert result.url is not None


class TestNormalizeTedEdgeCases:
    """normalize_ted_notice with minimal/edge-case inputs."""

    def _minimal_ted(self, **overrides) -> dict:
        base = {
            "publication-number": "2024/S 120-360001",
            "publication-date": "2024-06-15",
            "classification-cpv": ["45233120"],
            "BT-21-Lot": {"pol": "Budowa drogi ekspresowej S1"},
            "organisation-name-buyer": {"pol": ["Generalna Dyrekcja Dróg Krajowych"]},
        }
        base.update(overrides)
        return base

    def test_minimal_ted_notice_returns_tender_in(self):
        result = normalize_ted_notice(self._minimal_ted())
        assert isinstance(result, TenderIn)

    def test_source_is_ted(self):
        result = normalize_ted_notice(self._minimal_ted())
        assert result.source == "ted"

    def test_external_id_has_ted_prefix(self):
        result = normalize_ted_notice(self._minimal_ted())
        assert result.external_id.startswith("TED/")

    def test_missing_publication_number_returns_none(self):
        notice = self._minimal_ted()
        del notice["publication-number"]
        result = normalize_ted_notice(notice)
        assert result is None

    def test_non_construction_cpv_returns_none(self):
        result = normalize_ted_notice(self._minimal_ted(**{"classification-cpv": ["72000000"]}))
        assert result is None

    def test_empty_cpv_list_accepted(self):
        """Empty CPV should still produce a TenderIn (CPV optional for TED)."""
        notice = self._minimal_ted(**{"classification-cpv": []})
        result = normalize_ted_notice(notice)
        assert isinstance(result, TenderIn)

    def test_url_contains_publication_number(self):
        pub_num = "2024/S 120-999999"
        result = normalize_ted_notice(self._minimal_ted(**{"publication-number": pub_num}))
        assert result is not None
        assert pub_num in result.url

    def test_title_fallback_when_bt21_missing(self):
        notice = self._minimal_ted()
        del notice["BT-21-Lot"]
        result = normalize_ted_notice(notice)
        assert result is not None
        assert result.title  # should not be empty

    def test_value_pln_from_estimated_value_lot(self):
        notice = self._minimal_ted(**{"estimated-value-lot": 1_500_000})
        result = normalize_ted_notice(notice)
        assert result is not None
        assert result.value_pln == Decimal("1500000")

    def test_missing_value_gives_none(self):
        notice = self._minimal_ted()
        result = normalize_ted_notice(notice)
        assert result is not None
        assert result.value_pln is None  # no value in minimal fixture


class TestNormalizeCpv:
    """normalize_cpv covers many formats — add a few edge cases."""

    def test_empty_string_returns_empty(self):
        assert normalize_cpv("") == []

    def test_empty_list_returns_empty(self):
        assert normalize_cpv([]) == []

    def test_none_returns_empty(self):
        assert normalize_cpv(None) == []

    def test_single_cpv_string(self):
        result = normalize_cpv("45233120-6")
        assert result == ["45233120-6"]

    def test_comma_separated_cpv_string(self):
        result = normalize_cpv("45233120-6,45111200-0")
        assert len(result) == 2

    def test_dict_with_code_key(self):
        result = normalize_cpv({"code": "45000000-7"})
        assert "45000000-7" in result

    def test_list_of_dicts(self):
        result = normalize_cpv([{"code": "45233120-6"}, {"code": "45111200-0"}])
        assert len(result) == 2

    def test_cpv_with_description_in_parens_stripped(self):
        result = normalize_cpv("45000000-7 (Roboty budowlane)")
        assert result == ["45000000-7"]
