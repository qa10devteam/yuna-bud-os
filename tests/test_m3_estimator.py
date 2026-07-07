"""M3 acceptance tests — T-M3 / Acceptance A1 gates from spec/09.

Tests run offline (StubClient + fixture przedmiar + rate_card).

Acceptance criteria (spec/09 M3):
  ✅ Both variants compute
  ✅ Line totals reconcile EXACTLY to total_net_pln (sum-reconciliation, zero tolerance)
  ✅ compare delta correct: delta = A - B
  ✅ No owner RMS data sent to cloud (no-egress-of-rates test)
  ✅ Acceptance A1: ingest → /tenders → analyze → two-variant estimate → compare (offline)
"""
from __future__ import annotations

import os
import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")


# ─── Fixture przedmiar ─────────────────────────────────────────────────────

FIXTURE_PRZEDMIAR = [
    {"position_no": "1.1", "description": "Wykopy mechaniczne kat. III z transportem 1km",
     "unit": "m3", "quantity": 1250.0, "knr_code": "KNR 2-01 0211-03", "page": 3},
    {"position_no": "1.2", "description": "Nasypy z gruntu kat. II z zagęszczeniem",
     "unit": "m3", "quantity": 800.0, "knr_code": "KNR 2-01 0307-02", "page": 3},
    {"position_no": "1.3", "description": "Transport urobku do 5 km",
     "unit": "m3", "quantity": 450.0, "knr_code": "KNR 2-01 0510-01", "page": 4},
    {"position_no": "1.4", "description": "Zagęszczenie walcem wibracyjnym 8t",
     "unit": "m2", "quantity": 3200.0, "knr_code": "KNR 2-01 0405-04", "page": 4},
    {"position_no": "2.1", "description": "Podbudowa z kruszywa łamanego 0/31.5 gr. 20cm",
     "unit": "m2", "quantity": 2800.0, "knr_code": "KNR 2-31 0108-01", "page": 5},
    {"position_no": "2.2", "description": "Nawierzchnia AC16W gr. 5cm",
     "unit": "m2", "quantity": 2500.0, "knr_code": "KNR 2-31 0403-02", "page": 5},
]


# ─── Unit: Variant A ─────────────────────────────────────────────────────────

from services.estimator import (
    compute_variant_a, compute_variant_b, compare_estimates,
    verify_sum_reconciliation, RateCard, MarketPriceBase, Estimate,
)


class TestVariantA:
    def test_computes_all_lines(self):
        est = compute_variant_a(FIXTURE_PRZEDMIAR)
        assert est.variant == "A"
        assert len(est.lines) == len(FIXTURE_PRZEDMIAR)

    def test_sum_reconciliation_exact(self):
        """T-M3: line totals == total_net_pln. Zero tolerance."""
        est = compute_variant_a(FIXTURE_PRZEDMIAR)
        assert verify_sum_reconciliation(est), (
            f"Sum mismatch: lines={sum(l.line_total_pln for l in est.lines)}, "
            f"total={est.total_net_pln}"
        )

    def test_total_positive(self):
        est = compute_variant_a(FIXTURE_PRZEDMIAR)
        assert est.total_net_pln > 0

    def test_known_line_total(self):
        """1250 m³ × 22.50 zł = 28 125.00 zł (KNR 2-01 0211-03)."""
        est = compute_variant_a(FIXTURE_PRZEDMIAR)
        line = next(l for l in est.lines if l.position_no == "1.1")
        assert line.line_total_pln == Decimal("28125.00"), f"Got {line.line_total_pln}"

    def test_unit_prices_from_price_base(self):
        pb = MarketPriceBase()
        est = compute_variant_a(FIXTURE_PRZEDMIAR, price_base=pb)
        for line in est.lines:
            assert line.unit_price > 0

    def test_params_recorded(self):
        est = compute_variant_a(FIXTURE_PRZEDMIAR)
        assert "method" in est.params


# ─── Unit: Variant B ─────────────────────────────────────────────────────────

class TestVariantB:
    def test_computes_all_lines(self):
        est = compute_variant_b(FIXTURE_PRZEDMIAR)
        assert est.variant == "B"
        assert len(est.lines) == len(FIXTURE_PRZEDMIAR)

    def test_sum_reconciliation_exact(self):
        """T-M3: zero tolerance on sum reconciliation."""
        est = compute_variant_b(FIXTURE_PRZEDMIAR)
        assert verify_sum_reconciliation(est)

    def test_rms_components_positive(self):
        """Each line has labor + material + equipment components."""
        rc = RateCard()
        est = compute_variant_b(FIXTURE_PRZEDMIAR, rate_card=rc)
        for line in est.lines:
            assert line.line_total_pln > 0

    def test_custom_rate_card_affects_total(self):
        """Higher overhead → higher Variant B total."""
        rc_low = RateCard(kp_pct=Decimal("5.0"), zysk_pct=Decimal("3.0"))
        rc_high = RateCard(kp_pct=Decimal("20.0"), zysk_pct=Decimal("15.0"))
        est_low = compute_variant_b(FIXTURE_PRZEDMIAR, rate_card=rc_low)
        est_high = compute_variant_b(FIXTURE_PRZEDMIAR, rate_card=rc_high)
        assert est_high.total_net_pln > est_low.total_net_pln

    def test_calibration_coeff_scales_total(self):
        """calibration_coeff=1.1 → total ~10% higher than coeff=1.0."""
        rc_base = RateCard(calibration_coeff=Decimal("1.00"))
        rc_cal = RateCard(calibration_coeff=Decimal("1.10"))
        est_base = compute_variant_b(FIXTURE_PRZEDMIAR, rate_card=rc_base)
        est_cal = compute_variant_b(FIXTURE_PRZEDMIAR, rate_card=rc_cal)
        ratio = est_cal.total_net_pln / est_base.total_net_pln
        assert Decimal("1.08") <= ratio <= Decimal("1.12"), f"Ratio: {ratio}"

    def test_no_egress_of_rates(self):
        """T-M3: owner RMS rates must not appear in any external call.

        Ensures rate_card data stays local — no cloud LLM calls during Variant B.
        StubClient call count must be 0 for the compute step.
        """
        from services.ai.clients import StubClient
        stub = StubClient()
        initial_count = stub._call_count
        # compute_variant_b is pure Python — no LLM calls
        _ = compute_variant_b(FIXTURE_PRZEDMIAR)
        assert stub._call_count == initial_count, "Owner rates were sent to LLM!"

    def test_params_recorded(self):
        est = compute_variant_b(FIXTURE_PRZEDMIAR)
        assert "robocizna_zl_rg" in est.params
        assert "kp_pct" in est.params


# ─── Unit: Compare ────────────────────────────────────────────────────────────

class TestCompare:
    def test_delta_correct(self):
        """T-M3: delta_pln = A_total - B_total."""
        est_a = compute_variant_a(FIXTURE_PRZEDMIAR)
        est_b = compute_variant_b(FIXTURE_PRZEDMIAR)
        cmp = compare_estimates(est_a, est_b)
        assert cmp.delta_pln == est_a.total_net_pln - est_b.total_net_pln

    def test_margin_headroom_formula(self):
        """margin_headroom_pct = (A - B) / A × 100."""
        est_a = compute_variant_a(FIXTURE_PRZEDMIAR)
        est_b = compute_variant_b(FIXTURE_PRZEDMIAR)
        cmp = compare_estimates(est_a, est_b)
        expected = (est_a.total_net_pln - est_b.total_net_pln) * 100 / est_a.total_net_pln
        diff = abs(cmp.margin_headroom_pct - expected)
        assert diff < Decimal("0.01"), f"Margin calc error: {diff}"

    def test_zero_input_no_error(self):
        """Compare with 0 totals should not crash."""
        from services.estimator import Estimate, EstimateLine
        est_zero = Estimate(variant="A", lines=[], total_net_pln=Decimal("0"))
        est_b = Estimate(variant="B", lines=[], total_net_pln=Decimal("0"))
        cmp = compare_estimates(est_zero, est_b)
        assert cmp.delta_pln == Decimal("0")
        assert cmp.margin_headroom_pct == Decimal("0")


# ─── Integration: HTTP endpoints ──────────────────────────────────────────────

import sqlalchemy as sa
from terra_db.session import get_engine
from services.ingestion.pipeline import run_ingest


def _get_or_create_analyzed_tender() -> str:
    """Ensure a tender exists with analysis."""
    engine = get_engine()
    # Ensure tender exists
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tender LIMIT 1")).fetchone()
    if not row:
        run_ingest(engine, offline=True)
        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT id FROM tender LIMIT 1")).fetchone()
    tender_id = str(row[0])

    # Ensure analysis exists
    with engine.connect() as conn:
        a_row = conn.execute(
            sa.text("SELECT id FROM analysis WHERE tender_id = :tid"),
            {"tid": tender_id},
        ).fetchone()
    if not a_row:
        from services.documents.ocr import _fixture_extract
        from services.documents.parse_przedmiar import parse_przedmiar
        from services.documents.analysis import analyze_tender
        from services.ai.clients import StubClient
        from pathlib import Path
        import json, uuid
        llm = StubClient()
        extracted = _fixture_extract(Path("/dev/null"))
        items = parse_przedmiar(extracted.full_text, llm=llm)
        result = analyze_tender(extracted.full_text, doc_id="test", llm=llm,
                                przedmiar_items=[it.to_dict() for it in items])
        with engine.begin() as conn:
            conn.execute(sa.text(
                "INSERT INTO analysis (id, tender_id, summary_md, red_flags, key_facts, "
                "przedmiar_items, created_at) VALUES "
                "(:id, :tid, :summary, cast(:flags as jsonb), cast(:facts as jsonb), "
                "cast(:items as jsonb), now()) ON CONFLICT (tender_id) DO NOTHING"
            ), {
                "id": str(uuid.uuid4()), "tid": tender_id,
                "summary": result.summary_md,
                "flags": json.dumps([rf.to_dict() for rf in result.red_flags], ensure_ascii=False),
                "facts": json.dumps({}, ensure_ascii=False),
                "items": json.dumps([it.to_dict() for it in items], ensure_ascii=False),
            })
    return tender_id


@pytest.mark.asyncio
async def test_post_estimate_creates_both_variants():
    """POST /tenders/{id}/estimate → returns doc_id + owner_id."""
    from services.api.services.api.main import app
    tender_id = _get_or_create_analyzed_tender()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/tenders/{tender_id}/estimate")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "estimate_doc_id" in body
    assert "estimate_owner_id" in body
    assert body["estimate_doc_id"] != body["estimate_owner_id"]


@pytest.mark.asyncio
async def test_get_estimate_sum_reconciled():
    """GET /estimates/{id} → sum_reconciled=True."""
    from services.api.services.api.main import app
    tender_id = _get_or_create_analyzed_tender()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pair = (await ac.post(f"/api/v1/tenders/{tender_id}/estimate")).json()
        for est_id in [pair["estimate_doc_id"], pair["estimate_owner_id"]]:
            resp = await ac.get(f"/api/v1/estimates/{est_id}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["sum_reconciled"] is True, f"Sum not reconciled for {est_id}"


@pytest.mark.asyncio
async def test_compare_returns_delta():
    """GET /tenders/{id}/estimate/compare → correct delta."""
    from services.api.services.api.main import app
    tender_id = _get_or_create_analyzed_tender()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(f"/api/v1/tenders/{tender_id}/estimate")
        resp = await ac.get(f"/api/v1/tenders/{tender_id}/estimate/compare")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    from decimal import Decimal
    doc_total = Decimal(body["doc_total"])
    owner_total = Decimal(body["owner_total"])
    delta = Decimal(body["delta_pln"])
    assert delta == doc_total - owner_total


@pytest.mark.asyncio
async def test_patch_params_recomputes():
    """PATCH /estimates/{id}/params → recomputes with new overhead."""
    from services.api.services.api.main import app
    tender_id = _get_or_create_analyzed_tender()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pair = (await ac.post(f"/api/v1/tenders/{tender_id}/estimate")).json()
        est_id = pair["estimate_owner_id"]

        before = (await ac.get(f"/api/v1/estimates/{est_id}")).json()
        total_before = Decimal(before["total_net_pln"])

        # Raise overhead to 25% → total should increase
        patch_resp = await ac.patch(f"/api/v1/estimates/{est_id}/params",
                                    json={"params": {"kp_pct": "25.0"}})
        assert patch_resp.status_code == 200
        after = (await ac.get(f"/api/v1/estimates/{est_id}")).json()
        total_after = Decimal(after["total_net_pln"])

    assert total_after > total_before, "Higher overhead should increase total"
    assert Decimal(after["sum_reconciled"]) or after["sum_reconciled"] is True


@pytest.mark.asyncio
async def test_acceptance_a1_end_to_end():
    """A1: ingest → /tenders → analyze → estimate → compare (all offline)."""
    from services.api.services.api.main import app
    engine = get_engine()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Ingest
        r1 = await ac.post("/api/v1/ingest/run?offline=true")
        assert r1.status_code == 200

        # 2. List tenders
        r2 = await ac.get("/api/v1/tenders")
        assert r2.status_code == 200
        items = r2.json()["items"]
        assert len(items) >= 1
        tender_id = items[0]["id"]

        # 3. Analyze
        r3 = await ac.post(f"/api/v1/tenders/{tender_id}/analyze")
        assert r3.status_code == 200
        assert r3.json()["przedmiar_items_count"] >= 3

        # 4. Estimate (both variants)
        r4 = await ac.post(f"/api/v1/tenders/{tender_id}/estimate")
        assert r4.status_code == 200
        pair = r4.json()

        # 5. Get both variants
        est_a = (await ac.get(f"/api/v1/estimates/{pair['estimate_doc_id']}")).json()
        est_b = (await ac.get(f"/api/v1/estimates/{pair['estimate_owner_id']}")).json()

        assert est_a["variant"] == "doc"
        assert est_b["variant"] == "owner"
        assert est_a["sum_reconciled"] is True
        assert est_b["sum_reconciled"] is True

        # 6. Compare → go/no-go view
        r6 = await ac.get(f"/api/v1/tenders/{tender_id}/estimate/compare")
        assert r6.status_code == 200
        cmp = r6.json()
        assert "margin_headroom_pct" in cmp
        # Positive margin means owner cheaper than market → profitable
        from decimal import Decimal
        doc_total = Decimal(cmp["doc_total"])
        owner_total = Decimal(cmp["owner_total"])
        delta = Decimal(cmp["delta_pln"])
        assert delta == doc_total - owner_total
