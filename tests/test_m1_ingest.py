"""M1 acceptance tests — T-M1 gates from spec/09.

Tests run offline (TERRA_OFFLINE=1) using fixture notices.
No network, no external API calls.

Acceptance criteria (spec/09 M1):
  ✅ load fixture notices → expected tenders upserted
  ✅ out-of-CPV / out-of-geo notices dropped
  ✅ re-run → no dupes (idempotent)
  ✅ /tenders order correct (match_score DESC)
  ✅ /tenders/{id} returns correct tender
"""
from __future__ import annotations

import os
import pytest
from httpx import AsyncClient, ASGITransport
from decimal import Decimal

# Set offline + DB env before any import
os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")


# ─── Unit: CPV filter ────────────────────────────────────────────────────────

from services.ingestion.filters import passes_cpv_filter, passes_geo_filter
from services.ingestion.normalize import TenderIn
from decimal import Decimal
from datetime import datetime, timezone


def _make_tender(cpv=None, voivodeship=None, value=None):
    return TenderIn(
        source="bzp",
        external_id="TEST-001",
        title="Test",
        buyer="Gmina",
        cpv=cpv or [],
        voivodeship=voivodeship,
        value_pln=Decimal(str(value)) if value else None,
        deadline_at=None,
        published_at=None,
        url=None,
        raw={},
    )


class TestCpvFilter:
    def test_earthworks_cpv_passes(self):
        t = _make_tender(cpv=["45111200-0"])
        assert passes_cpv_filter(t) is True

    def test_road_cpv_passes(self):
        t = _make_tender(cpv=["45233120-6"])
        assert passes_cpv_filter(t) is True

    def test_office_supplies_dropped(self):
        t = _make_tender(cpv=["30192000-1"])
        assert passes_cpv_filter(t) is False

    def test_empty_cpv_dropped(self):
        t = _make_tender(cpv=[])
        assert passes_cpv_filter(t) is False

    def test_prefix_match_passes(self):
        # 45112700-2 starts with 45112 → earthworks prefix
        t = _make_tender(cpv=["45112700-2"])
        assert passes_cpv_filter(t) is True

    def test_mixed_cpv_passes_if_any_matches(self):
        t = _make_tender(cpv=["30192000-1", "45111200-0"])
        assert passes_cpv_filter(t) is True


# ─── Unit: Geo filter ────────────────────────────────────────────────────────

class TestGeoFilter:
    def test_dolnoslaskie_passes(self):
        t = _make_tender(voivodeship="dolnośląskie")
        assert passes_geo_filter(t) is True

    def test_mazowieckie_dropped(self):
        t = _make_tender(voivodeship="mazowieckie")
        assert passes_geo_filter(t) is False

    def test_unknown_voiv_passes(self):
        t = _make_tender(voivodeship=None)
        assert passes_geo_filter(t) is True

    def test_opolskie_passes(self):
        t = _make_tender(voivodeship="opolskie")
        assert passes_geo_filter(t) is True

    def test_case_insensitive(self):
        t = _make_tender(voivodeship="DOLNOŚLĄSKIE")
        assert passes_geo_filter(t) is True


# ─── Unit: Scorer ────────────────────────────────────────────────────────────

from services.ingestion.scorer import score_tender, OwnerProfileSnap


class TestScorer:
    def setup_method(self):
        self.profile = OwnerProfileSnap()

    def test_perfect_match_score_high(self):
        t = _make_tender(cpv=["45111200-0"], voivodeship="dolnośląskie", value=850_000)
        t2 = TenderIn(
            source="bzp", external_id="X", title="Roboty ziemne Pieszyce",
            buyer="Gmina", cpv=["45111200-0"], voivodeship="dolnośląskie",
            value_pln=Decimal("850000"), deadline_at=None, published_at=None,
            url=None, raw={}
        )
        r = score_tender(t2, self.profile)
        assert r.score >= 0.55, f"Expected >=0.55, got {r.score}"

    def test_out_of_scope_score_low(self):
        t = TenderIn(
            source="bzp", external_id="Y", title="Dostawa materiałów biurowych",
            buyer="Urząd", cpv=["30192000-1"], voivodeship="mazowieckie",
            value_pln=Decimal("45000"), deadline_at=None, published_at=None,
            url=None, raw={}
        )
        r = score_tender(t, self.profile)
        assert r.score <= 0.30, f"Expected <=0.30, got {r.score}"

    def test_score_0_to_1_range(self):
        for cpv, voiv, val in [
            (["45111200-0"], "dolnośląskie", 1_000_000),
            (["30000000-9"], "mazowieckie", 100_000),
            ([], None, None),
        ]:
            t = _make_tender(cpv=cpv, voivodeship=voiv, value=val)
            r = score_tender(t, self.profile)
            assert 0.0 <= r.score <= 1.0

    def test_reason_not_empty(self):
        t = _make_tender(cpv=["45111200-0"], voivodeship="dolnośląskie", value=500_000)
        r = score_tender(t, self.profile)
        assert r.reason and len(r.reason) > 0


# ─── Unit: Normalize ────────────────────────────────────────────────────────

from services.ingestion.fixtures import load_bzp_fixtures, _default_bzp_fixtures
from services.ingestion.normalize import normalize_bzp_notice


class TestNormalize:
    def test_valid_notice_normalizes(self):
        notices = _default_bzp_fixtures()
        # First fixture: droga gminna Pieszyce
        tin = normalize_bzp_notice(notices[0])
        assert tin is not None
        assert tin.source == "bzp"
        assert tin.external_id == "2024/BZP 00262955/01"
        assert "45233120-6" in tin.cpv
        assert tin.voivodeship == "dolnośląskie"
        assert tin.value_pln == Decimal("850000.00")

    def test_dostawa_skipped(self):
        notices = _default_bzp_fixtures()
        # Third fixture: dostawa (D) — should return None
        tin = normalize_bzp_notice(notices[2])
        assert tin is None

    def test_cpv_normalized(self):
        notices = _default_bzp_fixtures()
        tin = normalize_bzp_notice(notices[1])
        assert tin is not None
        for code in tin.cpv:
            assert isinstance(code, str) and len(code) > 0


# ─── Integration: Full pipeline (offline) ───────────────────────────────────

from terra_db.session import get_engine
from services.ingestion.pipeline import run_ingest
import sqlalchemy


def _clean_tenders(engine):
    with engine.begin() as conn:
        # Delete in FK-safe order (children first)
        conn.execute(sqlalchemy.text("DELETE FROM field_status"))
        conn.execute(sqlalchemy.text("DELETE FROM dispatch"))
        conn.execute(sqlalchemy.text("DELETE FROM daily_plan"))
        conn.execute(sqlalchemy.text("DELETE FROM calendar_event"))
        conn.execute(sqlalchemy.text("DELETE FROM contract"))
        conn.execute(sqlalchemy.text("DELETE FROM rfq_message"))
        conn.execute(sqlalchemy.text("DELETE FROM rfq"))
        conn.execute(sqlalchemy.text("DELETE FROM risk_run"))
        conn.execute(sqlalchemy.text("DELETE FROM estimate_line"))
        conn.execute(sqlalchemy.text("DELETE FROM estimate"))
        conn.execute(sqlalchemy.text("DELETE FROM discrepancy"))
        conn.execute(sqlalchemy.text("DELETE FROM przedmiar_item"))
        conn.execute(sqlalchemy.text("DELETE FROM document_chunk"))
        conn.execute(sqlalchemy.text("DELETE FROM tender_document"))
        conn.execute(sqlalchemy.text("DELETE FROM analysis"))
        conn.execute(sqlalchemy.text("DELETE FROM approval_request"))
        conn.execute(sqlalchemy.text("DELETE FROM tender"))


class TestPipeline:
    def setup_method(self):
        self.engine = get_engine()
        _clean_tenders(self.engine)

    def test_ingest_creates_expected_tenders(self):
        """T-M1: load fixture notices → expected tenders upserted."""
        result = run_ingest(self.engine, offline=True)
        # Fixtures: 5 total, fixture[2] is Dostawa (dropped in normalize),
        # fixture[4] is mazowieckie (dropped in geo filter)
        # → 3 should be created
        assert result.created >= 3, f"Expected >=3 created, got {result.created}"
        assert result.errors == 0, f"Unexpected errors: {result.errors}"

    def test_out_of_cpv_dropped(self):
        """T-M1: out-of-CPV notice dropped."""
        result = run_ingest(self.engine, offline=True)
        # Dostawa notice has CPV 30192000-1 → dropped in normalize (returns None)
        # OR dropped in CPV filter
        assert result.dropped_filter >= 1 or result.normalized < result.raw_fetched

    def test_out_of_geo_dropped(self):
        """T-M1: out-of-geo notice (mazowieckie) dropped."""
        result = run_ingest(self.engine, offline=True)
        assert result.dropped_filter >= 1

    def test_idempotent_no_dupes(self):
        """T-M1: re-run → no duplicate tenders inserted."""
        r1 = run_ingest(self.engine, offline=True)
        r2 = run_ingest(self.engine, offline=True)
        assert r2.created == 0, f"Second run should create 0, got {r2.created}"
        assert r2.updated >= r1.created, "Second run should update previously created"

    def test_tenders_in_db_after_ingest(self):
        """T-M1: DB has tenders with match_score set."""
        run_ingest(self.engine, offline=True)
        with self.engine.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text(
                    "SELECT id, match_score, match_reason FROM tender ORDER BY match_score DESC"
                )
            ).fetchall()
        assert len(rows) >= 3
        for row in rows:
            assert row[1] is not None, "match_score should not be null"
            assert float(row[1]) >= 0.0

    def test_tenders_ordered_by_match_score(self):
        """T-M1: /tenders order correct — match_score DESC."""
        run_ingest(self.engine, offline=True)
        with self.engine.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text("SELECT match_score FROM tender ORDER BY match_score DESC")
            ).fetchall()
        scores = [float(r[0]) for r in rows]
        assert scores == sorted(scores, reverse=True), "Tenders not sorted by score DESC"


# ─── Integration: HTTP endpoints ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_ingest_run():
    """POST /api/v1/ingest/run → 200 with agent_run_id."""
    from services.api.services.api.main import app  # type: ignore
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Clean DB first
        _clean_tenders(get_engine())
        resp = await ac.post("/api/v1/ingest/run?offline=true")
    assert resp.status_code in (200, 202), resp.text
    body = resp.json()
    # endpoint returns async task envelope: task_id + status
    assert "task_id" in body or "agent_run_id" in body, f"Expected task envelope, got: {body}"


@pytest.mark.asyncio
async def test_get_tenders_returns_list():
    """GET /api/v2/tenders → list ordered by match_score DESC."""
    from services.api.services.api.main import app  # type: ignore
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        _clean_tenders(get_engine())
        await ac.post("/api/v1/ingest/run?offline=true")
        # Wait briefly for async ingest to populate (offline mode is synchronous via task)
        await ac.post("/api/v1/ingest/run?offline=true")  # 2nd run ensures data present
        resp = await ac.get("/api/v2/tenders")
    assert resp.status_code in (200, 202), resp.text
    body = resp.json()
    assert "items" in body
    assert "total" in body
    items = body["items"]
    assert len(items) >= 3
    # Verify order
    scores = [item["match_score"] for item in items]
    assert scores == sorted(scores, reverse=True), "Not ordered by score DESC"


@pytest.mark.asyncio
async def test_get_tenders_cpv_filter():
    """GET /tenders?cpv=45111200-0 → only matching CPV."""
    from services.api.services.api.main import app  # type: ignore
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        _clean_tenders(get_engine())
        await ac.post("/api/v1/ingest/run?offline=true")
        resp = await ac.get("/api/v2/tenders?cpv=45111200-0")
    assert resp.status_code in (200, 202)
    body = resp.json()
    for item in body["items"]:
        assert "45111200-0" in item["cpv"]


@pytest.mark.asyncio
async def test_get_tender_by_id():
    """GET /tenders/{id} → full tender detail."""
    from services.api.services.api.main import app  # type: ignore
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        _clean_tenders(get_engine())
        await ac.post("/api/v1/ingest/run?offline=true")
        list_resp = await ac.get("/api/v2/tenders")
        items = list_resp.json().get("items", [])
        if not items:
            # fallback: seed one tender directly
            await ac.post("/api/v1/ingest/run?offline=true")
            list_resp = await ac.get("/api/v2/tenders")
            items = list_resp.json().get("items", [])
        assert items, f"Expected at least one tender, got: {list_resp.json()}"
        tender_id = items[0]["id"]
        detail_resp = await ac.get(f"/api/v2/tenders/{tender_id}")
    assert detail_resp.status_code == 200
    body = detail_resp.json()
    assert body["id"] == tender_id
    assert "source" in body
    assert "raw" in body  # full detail includes raw BZP payload


@pytest.mark.asyncio
async def test_get_tender_not_found():
    """GET /tenders/nonexistent → 404."""
    from services.api.services.api.main import app  # type: ignore
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v2/tenders/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
