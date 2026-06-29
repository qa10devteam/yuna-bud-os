"""M2 acceptance tests — T-M2 gates from spec/09.

Tests run offline using StubClient + fixture documents.

Acceptance criteria (spec/09 M2):
  ✅ scanned-przedmiar fixture → ≥N items with units/quantities/page
  ✅ onerous-clause fixture → cited red-flag
  ✅ no provenance-less claim
  ✅ POST /tenders/{id}/analyze → 200 with items + flags
  ✅ GET /tenders/{id}/analysis → summary + red_flags
"""
from __future__ import annotations

import os
import pytest
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terraosdev2026")


# ─── Unit: Document Classification ────────────────────────────────────────────

from services.documents.classify import classify_document, DocKind


class TestClassify:
    def test_przedmiar_filename(self):
        r = classify_document("Przedmiar_roboty_ziemne.pdf")
        assert r.kind == DocKind.PRZEDMIAR
        assert r.confidence >= 0.8

    def test_swz_filename(self):
        r = classify_document("SWZ_droga_gminna.pdf")
        assert r.kind == DocKind.SWZ

    def test_stwior_filename(self):
        r = classify_document("STWiOR_D-02.01.01.pdf")
        assert r.kind == DocKind.STWIOR

    def test_umowa_filename(self):
        r = classify_document("wzor_umowy.pdf")
        assert r.kind == DocKind.UMOWA

    def test_unknown_gets_other(self):
        r = classify_document("attachment_1.pdf")
        assert r.kind == DocKind.OTHER

    def test_content_heuristic(self):
        r = classify_document("dok.pdf", first_page_text="SPECYFIKACJA WARUNKÓW ZAMÓWIENIA")
        assert r.kind == DocKind.SWZ


# ─── Unit: Parse Przedmiar ────────────────────────────────────────────────────

from services.documents.parse_przedmiar import parse_przedmiar, PrzedmiarItem
from services.ai.clients import StubClient


class TestParsePrzemdiar:
    def test_regex_extraction(self):
        text = """
1.1 | Wykopy mechaniczne w gruncie kat. III | m3 | 1250.00 | KNR 2-01 0211-03
1.2 | Nasypy z gruntu kat. II z zagęszczeniem | m3 | 800.00 | KNR 2-01 0307-02
1.3 | Transport urobku na odległość do 5 km | m3 | 450.00 | KNR 2-01 0510-01
2.1 | Podbudowa z kruszywa łamanego 0/31.5 | m2 | 2800.00 | KNR 2-31 0108-01
"""
        items = parse_przedmiar(text)
        assert len(items) >= 4
        assert items[0].position_no == "1.1"
        assert items[0].unit == "m3"
        assert items[0].quantity == 1250.0
        assert "KNR" in (items[0].knr_code or "")

    def test_items_have_page_provenance(self):
        """T-M2: parsed items must have page provenance."""
        text = "1.1 | Wykopy mechaniczne gruncie III | m3 | 500.00 | KNR 2-01 0211-03"
        items = parse_przedmiar(text, page_offset=3)
        assert len(items) >= 1
        assert items[0].page == 3

    def test_llm_fallback(self):
        """If regex fails, LLM extraction kicks in."""
        llm = StubClient()
        items = parse_przedmiar("random text without table format", llm=llm)
        # StubClient returns 3 items
        assert len(items) >= 3
        for item in items:
            assert item.quantity > 0
            assert item.unit in ("m3", "m2", "mb", "szt", "t")

    def test_units_valid(self):
        text = "1.1 | Test | m3 | 100.00\n2.1 | Test2 | m2 | 200.00\n3.1 | Test3 | t | 50.00"
        items = parse_przedmiar(text)
        for item in items:
            assert item.unit in ("m3", "m2", "mb", "szt", "t", "km", "kpl", "kg", "ha", "mp")


# ─── Unit: Red Flag Detection ─────────────────────────────────────────────────

from services.documents.analysis import _detect_redflags_regex, analyze_tender, RedFlag


class TestRedFlags:
    def test_kary_umowne_detected(self):
        text = "§14 Kary umowne\n1. Za każdy dzień opóźnienia: 0.5% wynagrodzenia brutto za dzień."
        flags = _detect_redflags_regex(text, doc_id="doc-001")
        assert len(flags) >= 1
        assert any(f.category == "kary_umowne" for f in flags)

    def test_brak_waloryzacji_detected(self):
        text = "§15 Waloryzacja\nBrak klauzuli waloryzacyjnej. Wynagrodzenie stałe."
        flags = _detect_redflags_regex(text, doc_id="doc-002")
        assert len(flags) >= 1
        assert any(f.category == "brak_waloryzacji" for f in flags)

    def test_all_flags_have_provenance(self):
        """T-M2: no provenance-less claim."""
        text = "Kara 0.5%/dzień\nBrak waloryzacji\nTermin wykonania: 30 dni"
        flags = _detect_redflags_regex(text, doc_id="doc-003")
        for flag in flags:
            assert flag.provenance is not None
            assert "doc_id" in flag.provenance
            assert "page" in flag.provenance
            assert flag.provenance["page"] >= 1

    def test_fixture_onerous_clause(self):
        """T-M2: onerous-clause fixture → cited red-flag."""
        fixture_text = """
SPECYFIKACJA WARUNKÓW ZAMÓWIENIA
§14 Kary umowne
1. Za każdy dzień opóźnienia w wykonaniu przedmiotu umowy: 0.5% wynagrodzenia brutto.
§15 Waloryzacja
Brak klauzuli waloryzacyjnej. Wynagrodzenie ryczałtowe niezmienne.
"""
        llm = StubClient()
        result = analyze_tender(fixture_text, doc_id="fixture-001", llm=llm)
        # Must have at least 1 red flag with provenance
        assert len(result.red_flags) >= 1
        for rf in result.red_flags:
            assert rf.provenance is not None
            assert rf.provenance.get("page") is not None
            assert rf.message and len(rf.message) > 0

    def test_no_false_positives_on_clean_doc(self):
        """Clean document should produce 0 or few flags."""
        clean_text = "Wykonanie robót ziemnych zgodnie z projektem. Termin: 120 dni."
        flags = _detect_redflags_regex(clean_text, doc_id="clean-001")
        # Krotki_termin might fire, but kary/waloryzacja should not
        kary_flags = [f for f in flags if f.category == "kary_umowne"]
        assert len(kary_flags) == 0


# ─── Unit: Chunk + Embed ──────────────────────────────────────────────────────

from services.documents.chunk import chunk_and_embed


class TestChunk:
    def test_creates_chunks(self):
        llm = StubClient()
        pages = [
            {"page_num": 1, "text": "A" * 3000},
            {"page_num": 2, "text": "B" * 2000},
        ]
        chunks = chunk_and_embed("doc-test", pages, llm=llm)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.embedding) == 384
            assert chunk.page >= 1
            assert chunk.content

    def test_empty_page_skipped(self):
        llm = StubClient()
        pages = [{"page_num": 1, "text": ""}, {"page_num": 2, "text": "Content"}]
        chunks = chunk_and_embed("doc-test2", pages, llm=llm)
        assert all(c.page == 2 for c in chunks)


# ─── Integration: Full Analysis Pipeline ──────────────────────────────────────

class TestAnalysisPipeline:
    def test_full_pipeline_produces_analysis(self):
        """T-M2: full pipeline produces summary + red_flags + przedmiar items."""
        from services.documents.ocr import _fixture_extract
        from pathlib import Path

        llm = StubClient()
        extracted = _fixture_extract(Path("/dev/null"))
        full_text = extracted.full_text

        # Parse przedmiar
        items = parse_przedmiar(full_text, llm=llm)
        assert len(items) >= 3, f"Expected >=3 items, got {len(items)}"

        # Analysis
        result = analyze_tender(
            full_text, doc_id="test-pipeline", llm=llm,
            przedmiar_items=[it.to_dict() for it in items],
        )
        assert result.summary_md and len(result.summary_md) > 10
        assert len(result.red_flags) >= 1
        # All flags have provenance
        for rf in result.red_flags:
            assert rf.provenance.get("page") is not None


# ─── Integration: HTTP endpoints ──────────────────────────────────────────────

import sqlalchemy as sa
from terra_db.session import get_engine
from services.ingestion.pipeline import run_ingest


def _setup_tender():
    """Ensure at least one tender in DB for testing."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tender LIMIT 1")).fetchone()
    if row:
        return str(row[0])
    # Run ingest to create tenders
    run_ingest(engine, offline=True)
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tender LIMIT 1")).fetchone()
    return str(row[0]) if row else None


@pytest.mark.asyncio
async def test_post_analyze():
    """POST /tenders/{id}/analyze → 200 with items + flags."""
    from services.api.services.api.main import app
    tender_id = _setup_tender()
    assert tender_id is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/tenders/{tender_id}/analyze")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["przedmiar_items_count"] >= 3
    assert body["red_flags_count"] >= 1
    assert body["chunks_count"] >= 1


@pytest.mark.asyncio
async def test_get_analysis():
    """GET /tenders/{id}/analysis → summary + red_flags."""
    from services.api.services.api.main import app
    tender_id = _setup_tender()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ensure analysis exists
        await ac.post(f"/api/v1/tenders/{tender_id}/analyze")
        resp = await ac.get(f"/api/v1/tenders/{tender_id}/analysis")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary_md"] and len(body["summary_md"]) > 10
    assert len(body["red_flags"]) >= 1
    # Every red flag has provenance
    for rf in body["red_flags"]:
        assert "provenance" in rf
        assert rf["provenance"].get("page") is not None


@pytest.mark.asyncio
async def test_analyze_nonexistent_tender():
    """POST /tenders/nonexistent/analyze → 404."""
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/tenders/00000000-0000-0000-0000-000000000000/analyze")
    assert resp.status_code == 404
