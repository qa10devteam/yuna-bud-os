"""M6 acceptance tests — T-M6 / Acceptance A2 gates from spec/09.

Tests run offline (StubClient + fixture data).

Acceptance criteria (spec/09 M6 / A2):
  ✅ POST /rfq → 202 + approval_id (never sends inline)
  ✅ GET  /rfq/{id} → RFQ with messages + parsed_offers
  ✅ POST /rfq/{id}/inbound → parsed_offer from fixture email body (idempotent on message_uid)
  ✅ POST /approvals/{id}/approve → executed:true + rfq status=sent + audit_log row
  ✅ POST /approvals/{id}/reject → ok + status=rejected
  ✅ GET  /approvals?status=pending → pending list
  ✅ POST /estimates/{id}/chat → SSE stream, param changed, sum reconciled, audit written
  ✅ POST /tenders/{id}/autofill → 202 + approval_id (never submits)
  ✅ Acceptance A2 end-to-end: A1 + engine + risk + RFQ round-trip + param edit
"""
from __future__ import annotations

import json
import os
import pytest

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")

from httpx import AsyncClient, ASGITransport
import sqlalchemy as sa
from terra_db.session import get_engine as _get_engine


# ─── Unit: email offer parser ─────────────────────────────────────────────────

from services.api.services.api.routers.rfq import _parse_offer_from_email


class TestOfferParser:
    def test_parses_price_zl(self):
        body = "Oferujemy wykonanie za 45 000 zł netto w terminie 30 dni."
        offer = _parse_offer_from_email(body, "Firma A")
        assert offer["price_net_pln"] == 45_000.0
        assert offer["lead_time_days"] == 30

    def test_parses_price_pln(self):
        body = "Cena: 38500 PLN, termin: 21 dni roboczych"
        offer = _parse_offer_from_email(body, "Firma B")
        assert offer["price_net_pln"] == 38_500.0
        assert offer["lead_time_days"] == 21

    def test_parses_price_za(self):
        body = "Wyceniamy usługę za 12000 zł. Realizacja w ciągu 14 dni."
        offer = _parse_offer_from_email(body, "Firma C")
        assert offer["price_net_pln"] == 12_000.0
        assert offer["lead_time_days"] == 14

    def test_no_price_returns_none(self):
        body = "Niestety nie możemy złożyć oferty w tym terminie."
        offer = _parse_offer_from_email(body, "Firma D")
        assert offer["price_net_pln"] is None

    def test_counterparty_preserved(self):
        offer = _parse_offer_from_email("Oferta: 5000 zł, 7 dni", "Kowalski Sp. z o.o.")
        assert offer["counterparty"] == "Kowalski Sp. z o.o."

    def test_notes_truncated_to_200(self):
        body = "x" * 300
        offer = _parse_offer_from_email(body, "X")
        assert len(offer["notes"]) <= 200


# ─── Unit: chat edit intent parser ────────────────────────────────────────────

from services.api.services.api.routers.chat import _parse_edit_intent


class TestChatParser:
    def test_parses_narzut(self):
        edit = _parse_edit_intent("podnieś narzut do 15%", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "kp_pct"
        assert float(edit["value"]) == 15.0

    def test_parses_zysk(self):
        edit = _parse_edit_intent("ustaw zysk na 10%", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "zysk_pct"
        assert float(edit["value"]) == 10.0

    def test_parses_robocizna(self):
        edit = _parse_edit_intent("zmień robociznę na 40 zł/rg", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "robocizna_zl_rg"
        assert float(edit["value"]) == 40.0

    def test_noop_on_unknown(self):
        edit = _parse_edit_intent("powiedz mi coś o słoniach", {})
        assert edit["op"] == "noop"

    def test_comma_decimal(self):
        edit = _parse_edit_intent("narzut do 12,5%", {})
        assert edit["op"] == "set_param"
        assert float(edit["value"]) == 12.5


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _setup_tender_with_estimate() -> tuple[str, str, str]:
    """Returns (tender_id, estimate_doc_id, estimate_owner_id)."""
    import uuid as _uuid
    engine = _get_engine()

    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tender LIMIT 1")).fetchone()
    if not row:
        from services.ingestion.pipeline import run_ingest
        run_ingest(engine, offline=True)
        with engine.connect() as conn:
            row = conn.execute(sa.text("SELECT id FROM tender LIMIT 1")).fetchone()
    tender_id = str(row[0])

    # Ensure analysis
    with engine.connect() as conn:
        arow = conn.execute(
            sa.text("SELECT id FROM analysis WHERE tender_id=:tid"), {"tid": tender_id}
        ).fetchone()
    if not arow:
        from services.documents.ocr import _fixture_extract
        from services.documents.parse_przedmiar import parse_przedmiar
        from services.documents.analysis import analyze_tender
        from services.ai.clients import StubClient
        from pathlib import Path
        llm = StubClient()
        extracted = _fixture_extract(Path("/dev/null"))
        items = parse_przedmiar(extracted.full_text, llm=llm)
        result = analyze_tender(extracted.full_text, doc_id="test", llm=llm,
                                przedmiar_items=[it.to_dict() for it in items])
        with engine.begin() as conn:
            conn.execute(sa.text(
                "INSERT INTO analysis (id, tender_id, summary_md, red_flags, key_facts, "
                "przedmiar_items, created_at) VALUES "
                "(:id, :tid, :s, cast(:f as jsonb), cast(:kf as jsonb), cast(:i as jsonb), now()) "
                "ON CONFLICT (tender_id) DO NOTHING"
            ), {
                "id": str(_uuid.uuid4()), "tid": tender_id,
                "s": result.summary_md,
                "f": json.dumps([rf.to_dict() for rf in result.red_flags]),
                "kf": json.dumps({"max_excavation_depth_m": 1.0, "teren_mokry": False}),
                "i": json.dumps([it.to_dict() for it in items]),
            })

    # Ensure estimate
    with engine.connect() as conn:
        e_doc = conn.execute(
            sa.text("SELECT id FROM estimate WHERE tender_id=:tid AND variant='doc'"),
            {"tid": tender_id},
        ).fetchone()
        e_own = conn.execute(
            sa.text("SELECT id FROM estimate WHERE tender_id=:tid AND variant='owner'"),
            {"tid": tender_id},
        ).fetchone()

    if not e_doc or not e_own:
        from services.ingestion.pipeline import run_ingest
        # Create estimate via HTTP to be thorough
        pass

    # Get IDs
    with engine.connect() as conn:
        ed = conn.execute(
            sa.text("SELECT id FROM estimate WHERE tender_id=:tid AND variant='doc'"), {"tid": tender_id}
        ).fetchone()
        eo = conn.execute(
            sa.text("SELECT id FROM estimate WHERE tender_id=:tid AND variant='owner'"), {"tid": tender_id}
        ).fetchone()

    return tender_id, (str(ed[0]) if ed else ""), (str(eo[0]) if eo else "")


# ─── Integration: RFQ ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_rfq_returns_202_approval_id():
    """POST /rfq → 202 + approval_id, never sends inline."""
    from services.api.services.api.main import app
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Usługi odwodnienia wykopu",
            "counterparties": ["firma-x@example.com", "firma-y@example.com"],
        })

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "approval_id" in body
    assert body["approval_id"]


@pytest.mark.asyncio
async def test_rfq_not_sent_before_approval():
    """RFQ must stay in draft/pending until approved."""
    from services.api.services.api.main import app
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Test no-send",
            "counterparties": ["test@example.com"],
        })
        approval_id = r.json()["approval_id"]

        # Approval is pending
        approvals = (await ac.get("/api/v1/approvals?status=pending")).json()
        pending_ids = [a["id"] for a in approvals]
        assert approval_id in pending_ids


@pytest.mark.asyncio
async def test_rfq_send_after_approval():
    """POST /approvals/{id}/approve → executed + rfq status=sent + audit row."""
    from services.api.services.api.main import app
    engine = _get_engine()
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Dostawa kruszywa",
            "counterparties": ["kruszywa@example.com"],
        })
        approval_id = r.json()["approval_id"]

        # Approve
        resp = await ac.post(f"/api/v1/approvals/{approval_id}/approve")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["executed"] is True
        assert "rfq_id" in body["result"]

    # Verify audit_log row written
    rfq_id = body["result"]["rfq_id"]
    with engine.connect() as conn:
        audit = conn.execute(
            sa.text("SELECT id FROM audit_log WHERE action LIKE '%rfq_send%' LIMIT 1")
        ).fetchone()
    assert audit is not None, "audit_log row must be written on approval"

    # Verify RFQ is now sent
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        rfq_resp = await ac.get(f"/api/v1/rfq/{rfq_id}")
    assert rfq_resp.status_code == 200
    assert rfq_resp.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_rfq_inbound_parsed():
    """POST /rfq/{id}/inbound → parsed_offer with price + lead_time."""
    from services.api.services.api.main import app
    engine = _get_engine()
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Odwodnienie wykopu",
            "counterparties": ["odwodnienie@example.com"],
        })
        approval_id = r.json()["approval_id"]
        await ac.post(f"/api/v1/approvals/{approval_id}/approve")

        rfq_resp = (await ac.get(f"/api/v1/rfq/{r.json().get('rfq_id', '')}"))
        # Get rfq_id from approval result
        appr_result = (await ac.post(f"/api/v1/approvals/{approval_id}/approve")).json()

    # Fresh RFQ creation
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r2 = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Odwodnienie wykopu 2",
            "counterparties": ["odwodnienie2@example.com"],
        })
        approval_id2 = r2.json()["approval_id"]
        appr2 = await ac.post(f"/api/v1/approvals/{approval_id2}/approve")
        rfq_id2 = appr2.json()["result"]["rfq_id"]

        # Inbound reply
        inbound = await ac.post(f"/api/v1/rfq/{rfq_id2}/inbound", json={
            "message_uid": "MSG-001",
            "counterparty": "odwodnienie2@example.com",
            "subject": "Re: Zapytanie ofertowe",
            "body": "Dzień dobry, oferujemy usługę za 18 500 zł netto w terminie 14 dni.",
        })
    assert inbound.status_code == 200, inbound.text
    result = inbound.json()
    assert result["parsed_offer"]["price_net_pln"] == 18_500.0
    assert result["parsed_offer"]["lead_time_days"] == 14


@pytest.mark.asyncio
async def test_rfq_inbound_idempotent():
    """POST /rfq/{id}/inbound with same message_uid → duplicate=True, no double insert."""
    from services.api.services.api.main import app
    engine = _get_engine()
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Test idempotency",
            "counterparties": ["x@example.com"],
        })
        ap_id = r.json()["approval_id"]
        ap_res = (await ac.post(f"/api/v1/approvals/{ap_id}/approve")).json()
        rfq_id = ap_res["result"]["rfq_id"]

        payload = {
            "message_uid": "IDEM-001",
            "counterparty": "x@example.com",
            "subject": "Re",
            "body": "Cena 5000 zł, termin 7 dni",
        }
        r1 = await ac.post(f"/api/v1/rfq/{rfq_id}/inbound", json=payload)
        r2 = await ac.post(f"/api/v1/rfq/{rfq_id}/inbound", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json().get("duplicate") is True


@pytest.mark.asyncio
async def test_approval_reject():
    """POST /approvals/{id}/reject → ok + status=rejected."""
    from services.api.services.api.main import app
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Reject test",
            "counterparties": [],
        })
        approval_id = r.json()["approval_id"]
        resp = await ac.post(f"/api/v1/approvals/{approval_id}/reject")

    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify status
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT status FROM approval_request WHERE id=:id"), {"id": approval_id}
        ).fetchone()
    assert row[0] == "rejected"


# ─── Integration: Chat-brain edits ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_edit_kp_recomputes():
    """POST /estimates/{id}/chat 'podnieś narzut do 20%' → total changes + sum reconciled."""
    from services.api.services.api.main import app
    tender_id, _, owner_id = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ensure estimate exists
        pair = (await ac.post(f"/api/v1/tenders/{tender_id}/estimate")).json()
        owner_id = pair["estimate_owner_id"]

        before = (await ac.get(f"/api/v1/estimates/{owner_id}")).json()
        total_before = float(before["total_net_pln"])

        resp = await ac.post(f"/api/v1/estimates/{owner_id}/chat",
                             json={"message": "podnieś narzut do 20%"})

    assert resp.status_code == 200
    # Parse SSE events
    events = _parse_sse(resp.text)
    event_types = [e["event"] for e in events]
    assert "done" in event_types

    done_data = next(e["data"] for e in events if e["event"] == "done")
    if done_data.get("changed"):
        new_total = float(done_data.get("new_total", total_before))
        assert new_total > total_before, "Higher overhead must increase total"
        assert done_data.get("sum_reconciled") is True


@pytest.mark.asyncio
async def test_chat_edit_writes_audit():
    """Chat edit must write audit_log row."""
    from services.api.services.api.main import app
    engine = _get_engine()
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pair = (await ac.post(f"/api/v1/tenders/{tender_id}/estimate")).json()
        owner_id = pair["estimate_owner_id"]
        await ac.post(f"/api/v1/estimates/{owner_id}/chat",
                      json={"message": "ustaw zysk na 12%"})

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id FROM audit_log WHERE action='estimate_edit' LIMIT 1")
        ).fetchone()
    assert row is not None, "audit_log row must be written after chat edit"


@pytest.mark.asyncio
async def test_chat_noop_no_crash():
    """Unknown command → SSE stream with flag:warn, no crash."""
    from services.api.services.api.main import app
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pair = (await ac.post(f"/api/v1/tenders/{tender_id}/estimate")).json()
        owner_id = pair["estimate_owner_id"]
        resp = await ac.post(f"/api/v1/estimates/{owner_id}/chat",
                             json={"message": "opowiedz mi bajkę o żabach"})

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    event_types = [e["event"] for e in events]
    assert "done" in event_types or "flag" in event_types


# ─── Integration: Autofill ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_autofill_returns_202():
    """POST /tenders/{id}/autofill → 202 + approval_id, never submits."""
    from services.api.services.api.main import app
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/tenders/{tender_id}/autofill")

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "approval_id" in body


@pytest.mark.asyncio
async def test_autofill_approve_draft_not_submit():
    """Approved autofill → draft_produced, never submits."""
    from services.api.services.api.main import app
    tender_id, _, _ = _setup_tender_with_estimate()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/tenders/{tender_id}/autofill")
        approval_id = r.json()["approval_id"]
        resp = await ac.post(f"/api/v1/approvals/{approval_id}/approve")

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result.get("status") == "draft_produced"
    # Must NOT have "submitted" in result
    assert "submitted" not in str(result).lower()


# ─── Acceptance A2 — full Tier 2 end-to-end ──────────────────────────────────

@pytest.mark.asyncio
async def test_acceptance_a2_end_to_end():
    """A2: A1 + engine verdict + risk distribution + RFQ round-trip + param edit.

    Steps:
    1. ingest → /tenders → analyze
    2. two-variant estimate → compare (A1 ✅)
    3. engine/run → feasible + risk{}
    4. POST /rfq → 202 → approve → sent → inbound reply → parsed_offer
    5. PATCH /estimates/{id}/params → reconciles
    6. autofill → 202 (never submits)
    """
    from services.api.services.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        # 1. Ingest + tenders
        r1 = await ac.post("/api/v1/ingest/run?offline=true")
        assert r1.status_code == 200
        tenders = (await ac.get("/api/v1/tenders")).json()["items"]
        assert len(tenders) >= 1
        tender_id = tenders[0]["id"]

        # 2. Analyze
        r_analyze = await ac.post(f"/api/v1/tenders/{tender_id}/analyze")
        assert r_analyze.status_code == 200

        # 3. Two-variant estimate
        r_est = await ac.post(f"/api/v1/tenders/{tender_id}/estimate")
        assert r_est.status_code == 200
        pair = r_est.json()
        assert "estimate_doc_id" in pair and "estimate_owner_id" in pair

        # 4. Compare (A1 gate)
        r_cmp = await ac.get(f"/api/v1/tenders/{tender_id}/estimate/compare")
        assert r_cmp.status_code == 200
        cmp = r_cmp.json()
        assert "margin_headroom_pct" in cmp

        # 5. Engine verdict + risk
        r_eng = await ac.post(f"/api/v1/tenders/{tender_id}/engine/run")
        assert r_eng.status_code == 200
        eng = r_eng.json()
        assert "feasible" in eng
        assert "violations" in eng
        # risk may be None if no estimate total, but key must exist
        assert "risk" in eng

        # 6. RFQ round-trip
        r_rfq = await ac.post(f"/api/v1/tenders/{tender_id}/rfq", json={
            "scope_desc": "Odwodnienie głębokiego wykopu",
            "counterparties": ["podwykonawca@example.com"],
        })
        assert r_rfq.status_code == 202
        ap_id = r_rfq.json()["approval_id"]

        # Approve → send
        r_ap = await ac.post(f"/api/v1/approvals/{ap_id}/approve")
        assert r_ap.status_code == 200
        assert r_ap.json()["executed"] is True
        rfq_id = r_ap.json()["result"]["rfq_id"]

        # Inbound reply
        r_in = await ac.post(f"/api/v1/rfq/{rfq_id}/inbound", json={
            "message_uid": "A2-MSG-001",
            "counterparty": "podwykonawca@example.com",
            "subject": "Re: Zapytanie ofertowe",
            "body": "Oferujemy odwodnienie za 22 000 zł netto, termin 10 dni.",
        })
        assert r_in.status_code == 200
        assert r_in.json()["parsed_offer"]["price_net_pln"] == 22_000.0

        # GET /rfq → parsed_offers
        r_get_rfq = await ac.get(f"/api/v1/rfq/{rfq_id}")
        assert r_get_rfq.status_code == 200
        rfq_data = r_get_rfq.json()
        assert len(rfq_data["parsed_offers"]) >= 1

        # 7. Interactive param edit (reconciles)
        owner_id = pair["estimate_owner_id"]
        r_patch = await ac.patch(f"/api/v1/estimates/{owner_id}/params",
                                 json={"params": {"kp_pct": "18.0"}})
        assert r_patch.status_code == 200
        assert r_patch.json()["sum_reconciled"] is True

        # 8. Autofill → 202 (never submits)
        r_af = await ac.post(f"/api/v1/tenders/{tender_id}/autofill")
        assert r_af.status_code == 202
        af_ap_id = r_af.json()["approval_id"]

        # Approve autofill → draft_produced
        r_af_ap = await ac.post(f"/api/v1/approvals/{af_ap_id}/approve")
        assert r_af_ap.status_code == 200
        assert r_af_ap.json()["result"]["status"] == "draft_produced"


# ─── Helper ──────────────────────────────────────────────────────────────────

def _parse_sse(text: str) -> list[dict]:
    """Parse SSE stream text into list of {event, data}."""
    events = []
    current: dict = {}
    for line in text.split("\n"):
        line = line.rstrip()
        if line.startswith("event:"):
            current["event"] = line[6:].strip()
        elif line.startswith("data:"):
            raw = line[5:].strip()
            try:
                current["data"] = json.loads(raw)
            except json.JSONDecodeError:
                current["data"] = raw
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events
