"""Coverage push for:
  - services/api/services/api/routers/m7_phase2.py  (73%, lines 194-220,226-246,362-386,392-400)
  - services/api/services/api/routers/buyer_crm.py  (79%, lines 151-157,176-186,253-260,268-272,
    277-283,289-292,299-302,307-310,316-318,323-326,331-335,340-343,348-351,360-380)

Strategy: call route functions directly with mock DB/user to avoid routing conflicts and to
precisely target each uncovered branch.  No real DB or network needed.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch, call

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_conn(one_or_none=None, fetchall=None, scalar=0, rowcount=1):
    """Build a flexible MagicMock DB connection.

    All execute() chains (.one_or_none(), .fetchall(), .mappings().all(), .scalar())
    are pre-wired from the same result object so tests don't need per-call setup.
    """
    result = MagicMock()
    result.one_or_none.return_value = one_or_none
    result.fetchone.return_value = one_or_none
    result.scalar.return_value = scalar
    result.rowcount = rowcount
    # Direct .fetchall() used by m7_phase2 routes
    result.fetchall.return_value = fetchall or []

    # .mappings().all() and .mappings().one_or_none() chains (buyer_crm routes)
    mappings_mock = MagicMock()
    mappings_mock.all.return_value = fetchall or []
    mappings_mock.one_or_none.return_value = one_or_none
    mappings_mock.one.return_value = one_or_none
    result.mappings.return_value = mappings_mock

    conn = MagicMock()
    conn.execute.return_value = result
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    return conn


def _mock_engine_ctx(conn):
    """Wrap conn in an engine mock that works as a context manager for both
    engine.connect() and engine.begin()."""
    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value.__enter__ = lambda s: conn
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine


def _demo_user(org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d"):
    from services.api.services.api.auth.deps import CurrentUser
    return CurrentUser(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id=org_id,
        role="owner",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# m7_phase2.py — list_competitors  (lines 194-220)
# ═══════════════════════════════════════════════════════════════════════════════

def test_m7p2_competitors_success_with_rows():
    """list_competitors: atlas_contractors query succeeds → returns rows (lines 194-218)."""
    from services.api.services.api.routers.m7_phase2 import list_competitors

    competitor_row = ("Firma ABC Sp. z o.o.", "Warszawa", "1234567890", 20, 40, 0.5, 3_000_000.0)
    conn = _make_conn(fetchall=[competitor_row])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_competitors(limit=30)

    assert result["count"] == 1
    comp = result["competitors"][0]
    assert comp["name"] == "Firma ABC Sp. z o.o."
    assert comp["win_count"] == 20
    assert comp["win_rate"] == 0.5


def test_m7p2_competitors_empty_list():
    """list_competitors: atlas_contractors returns empty list → count 0 (lines 194-218)."""
    from services.api.services.api.routers.m7_phase2 import list_competitors

    conn = _make_conn(fetchall=[])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_competitors(limit=5)

    assert result["count"] == 0
    assert result["competitors"] == []


def test_m7p2_competitors_db_exception():
    """list_competitors: atlas_contractors query raises → fallback response (line 220)."""
    from services.api.services.api.routers.m7_phase2 import list_competitors

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.side_effect = Exception("relation atlas_contractors does not exist")
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_competitors(limit=30)

    assert result["count"] == 0
    assert result["competitors"] == []
    assert "note" in result


def test_m7p2_competitors_null_values():
    """list_competitors: rows with None values for win_rate, total_won_value → 0.0 fallback."""
    from services.api.services.api.routers.m7_phase2 import list_competitors

    competitor_row = ("Firma XYZ", None, "9876543210", 5, 10, None, None)
    conn = _make_conn(fetchall=[competitor_row])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_competitors(limit=10)

    assert result["count"] == 1
    comp = result["competitors"][0]
    assert comp["win_rate"] == 0
    assert comp["total_won_value"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# m7_phase2.py — competitor_heatmap  (lines 226-246)
# ═══════════════════════════════════════════════════════════════════════════════

def test_m7p2_heatmap_success_with_rows():
    """competitor_heatmap: JOIN query succeeds → heatmap data (lines 226-244)."""
    from services.api.services.api.routers.m7_phase2 import competitor_heatmap

    heatmap_row = ("Firma X", "45261910-6", 7, 2_500_000.0)
    conn = _make_conn(fetchall=[heatmap_row])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = competitor_heatmap()

    assert "heatmap" in result
    assert len(result["heatmap"]) == 1
    entry = result["heatmap"][0]
    assert entry["competitor"] == "Firma X"
    assert entry["wins"] == 7


def test_m7p2_heatmap_null_total_value():
    """competitor_heatmap: row with None total_value → 0.0 (lines 239-244)."""
    from services.api.services.api.routers.m7_phase2 import competitor_heatmap

    heatmap_row = ("Firma Y", "45262100-0", 3, None)
    conn = _make_conn(fetchall=[heatmap_row])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = competitor_heatmap()

    assert result["heatmap"][0]["total_value"] == 0


def test_m7p2_heatmap_db_exception():
    """competitor_heatmap: JOIN query raises → error response (lines 245-246)."""
    from services.api.services.api.routers.m7_phase2 import competitor_heatmap

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.side_effect = Exception("relation atlas_contractors does not exist")
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = competitor_heatmap()

    assert "heatmap" in result
    assert result["heatmap"] == []
    assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════════
# m7_phase2.py — list_notifications  (lines 362-386)
# ═══════════════════════════════════════════════════════════════════════════════

def test_m7p2_notifications_success_with_rows():
    """list_notifications: notifications table returns rows → dict with data (lines 362-385)."""
    from services.api.services.api.routers.m7_phase2 import list_notifications

    notif_id = str(uuid.uuid4())
    notif_row = (notif_id, "alert", "Nowy przetarg", "Szczegóły przetargu", False, "2024-06-01T12:00:00", None)
    conn = _make_conn(fetchall=[notif_row])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_notifications(limit=10, unread_only=False)

    assert result["count"] == 1
    n = result["notifications"][0]
    assert n["id"] == notif_id
    assert n["type"] == "alert"
    assert n["is_read"] is False


def test_m7p2_notifications_unread_only_filter():
    """list_notifications: unread_only=True → filter_clause applied (line 363 branch)."""
    from services.api.services.api.routers.m7_phase2 import list_notifications

    notif_row = (str(uuid.uuid4()), "tender", "Title", "Body", False, "2024-01-01T00:00:00", {"key": "val"})
    conn = _make_conn(fetchall=[notif_row])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_notifications(limit=20, unread_only=True)

    # Verify it executed (called the engine)
    assert result["count"] == 1
    assert result["notifications"][0]["metadata"] == {"key": "val"}


def test_m7p2_notifications_empty_list():
    """list_notifications: table exists but empty → count 0."""
    from services.api.services.api.routers.m7_phase2 import list_notifications

    conn = _make_conn(fetchall=[])
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_notifications(limit=30, unread_only=False)

    assert result["count"] == 0
    assert result["notifications"] == []


def test_m7p2_notifications_db_exception():
    """list_notifications: notifications table missing → fallback response (line 386)."""
    from services.api.services.api.routers.m7_phase2 import list_notifications

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.side_effect = Exception("relation notifications does not exist")
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = list_notifications(limit=30)

    assert result["count"] == 0
    assert result["notifications"] == []
    assert "note" in result


# ═══════════════════════════════════════════════════════════════════════════════
# m7_phase2.py — unread_count  (lines 392-400)
# ═══════════════════════════════════════════════════════════════════════════════

def test_m7p2_unread_count_success():
    """unread_count: table exists → {unread: N} (lines 392-399)."""
    from services.api.services.api.routers.m7_phase2 import unread_count

    conn = _make_conn(scalar=5)
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = unread_count()

    assert result == {"unread": 5}


def test_m7p2_unread_count_zero():
    """unread_count: table exists, count 0 → {unread: 0} (lines 392-399)."""
    from services.api.services.api.routers.m7_phase2 import unread_count

    conn = _make_conn(scalar=0)
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = unread_count()

    assert result["unread"] == 0


def test_m7p2_unread_count_exception():
    """unread_count: notifications table missing → fallback {unread: 0} (line 400)."""
    from services.api.services.api.routers.m7_phase2 import unread_count

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.side_effect = Exception("relation notifications does not exist")
    engine = _mock_engine_ctx(conn)

    with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
        result = unread_count()

    assert result == {"unread": 0}


# ═══════════════════════════════════════════════════════════════════════════════
# buyer_crm.py — list_crm  (lines 151-157, 176-186)
# ═══════════════════════════════════════════════════════════════════════════════

def test_buyer_crm_list_invalid_stage_400():
    """list_crm: invalid stage → HTTPException 400 (line 151)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import list_crm

    user = _demo_user()
    conn = _make_conn(fetchall=[], scalar=0)

    with pytest.raises(HTTPException) as exc_info:
        list_crm(user=user, db=conn, stage="nonexistent_stage")
    assert exc_info.value.status_code == 400
    assert "stage" in exc_info.value.detail.lower() or "Nieprawidłowy" in exc_info.value.detail


def test_buyer_crm_list_with_valid_stage_filter():
    """list_crm: valid stage filter appended to query (lines 156-157)."""
    from services.api.services.api.routers.buyer_crm import list_crm

    user = _demo_user()
    row = {"id": str(uuid.uuid4()), "buyer_nip": "1234567890", "crm_stage": "prospect",
           "priority": 3, "contact_name": None, "contact_email": None, "contact_phone": None,
           "annual_budget_est": None, "territory": None, "notes": None,
           "last_contact": None, "next_followup": None, "created_at": "2024-01-01", "updated_at": "2024-01-01",
           "buyer_name": "Urząd Gminy Test", "city": "Kraków", "province": "małopolskie",
           "total_tenders": 10, "total_value": 1_000_000}
    conn = _make_conn(fetchall=[row], scalar=1)

    result = list_crm(user=user, db=conn, stage="prospect", limit=50, offset=0)

    assert result["total"] == 1
    assert result["items"][0]["crm_stage"] == "prospect"


def test_buyer_crm_list_with_priority_filter():
    """list_crm: priority filter appended (lines 159-161)."""
    from services.api.services.api.routers.buyer_crm import list_crm

    user = _demo_user()
    conn = _make_conn(fetchall=[], scalar=0)

    # Must pass stage=None explicitly — default Query(None) object is truthy when called directly
    result = list_crm(user=user, db=conn, stage=None, priority=1, territory=None, limit=20, offset=0)

    assert result["total"] == 0
    assert result["items"] == []


def test_buyer_crm_list_with_territory_filter():
    """list_crm: territory ILIKE filter appended (lines 162-164)."""
    from services.api.services.api.routers.buyer_crm import list_crm

    user = _demo_user()
    conn = _make_conn(fetchall=[], scalar=0)

    result = list_crm(user=user, db=conn, stage=None, priority=None, territory="mazowieckie", limit=20, offset=0)

    assert result["total"] == 0
    assert result["limit"] == 20
    assert result["offset"] == 0


def test_buyer_crm_list_no_filters_returns_data():
    """list_crm: no filters, returns items and total (lines 176-186)."""
    from services.api.services.api.routers.buyer_crm import list_crm

    user = _demo_user()
    rows = [
        {"id": str(uuid.uuid4()), "buyer_nip": f"000000000{i}", "crm_stage": "active",
         "priority": 2, "contact_name": f"Osoba {i}", "contact_email": None, "contact_phone": None,
         "annual_budget_est": 500_000.0, "territory": "mazowieckie", "notes": None,
         "last_contact": None, "next_followup": None, "created_at": "2024-01-01", "updated_at": "2024-01-01",
         "buyer_name": f"Urząd {i}", "city": "Warszawa", "province": "mazowieckie",
         "total_tenders": 5, "total_value": 500_000.0}
        for i in range(3)
    ]
    conn = _make_conn(fetchall=rows, scalar=3)

    result = list_crm(user=user, db=conn, stage=None, priority=None, territory=None, limit=50, offset=0)

    assert result["total"] == 3
    assert len(result["items"]) == 3
    assert result["offset"] == 0
    assert result["limit"] == 50


def test_buyer_crm_list_user_no_org_400():
    """list_crm: user without org_id → HTTPException 400 (_require_org)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import list_crm

    user = _demo_user(org_id=None)
    conn = _make_conn()

    with pytest.raises(HTTPException) as exc_info:
        list_crm(user=user, db=conn)
    assert exc_info.value.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# buyer_crm.py — update_crm  (lines 253-260, 268-272, 277-283)
# ═══════════════════════════════════════════════════════════════════════════════

def test_buyer_crm_update_invalid_stage_400():
    """update_crm: invalid crm_stage → HTTPException 400 (line 252)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import update_crm, BuyerCRMUpdate

    crm_id = uuid.uuid4()
    user = _demo_user()
    conn = _make_conn()
    body = BuyerCRMUpdate(crm_stage="not_a_real_stage")

    with pytest.raises(HTTPException) as exc_info:
        update_crm(crm_id=crm_id, body=body, user=user, db=conn)
    assert exc_info.value.status_code == 400


def test_buyer_crm_update_not_found_404():
    """update_crm: existing record not found → HTTPException 404 (lines 253-258)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import update_crm, BuyerCRMUpdate

    crm_id = uuid.uuid4()
    user = _demo_user()
    conn = _make_conn(one_or_none=None)  # existing → None
    body = BuyerCRMUpdate(crm_stage="active")

    with pytest.raises(HTTPException) as exc_info:
        update_crm(crm_id=crm_id, body=body, user=user, db=conn)
    assert exc_info.value.status_code == 404


def test_buyer_crm_update_empty_body_400():
    """update_crm: all fields None → empty updates dict → HTTPException 400 (lines 259-262)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import update_crm, BuyerCRMUpdate

    crm_id = uuid.uuid4()
    user = _demo_user()
    # Return existing record on first execute
    existing_record = (str(crm_id),)
    conn = _make_conn(one_or_none=existing_record)
    body = BuyerCRMUpdate()  # all fields None → model_dump(exclude_none=True) == {}

    with pytest.raises(HTTPException) as exc_info:
        update_crm(crm_id=crm_id, body=body, user=user, db=conn)
    assert exc_info.value.status_code == 400
    assert "aktualizacji" in exc_info.value.detail or "fields" in exc_info.value.detail.lower()


def test_buyer_crm_update_success():
    """update_crm: valid update → {status: ok} (lines 268-283)."""
    from services.api.services.api.routers.buyer_crm import update_crm, BuyerCRMUpdate

    crm_id = uuid.uuid4()
    user = _demo_user()
    existing_record = (str(crm_id),)
    conn = _make_conn(one_or_none=existing_record)
    body = BuyerCRMUpdate(crm_stage="active", notes="Spotkanie umówione")

    result = update_crm(crm_id=crm_id, body=body, user=user, db=conn)

    assert result["status"] == "ok"
    assert str(crm_id) in result["id"]
    assert "crm_stage" in result["updated_fields"] or "notes" in result["updated_fields"]
    conn.commit.assert_called_once()


def test_buyer_crm_update_single_field():
    """update_crm: single field update (lines 268-278 set_parts generation)."""
    from services.api.services.api.routers.buyer_crm import update_crm, BuyerCRMUpdate

    crm_id = uuid.uuid4()
    user = _demo_user()
    existing_record = (str(crm_id),)
    conn = _make_conn(one_or_none=existing_record)
    body = BuyerCRMUpdate(priority=5)

    result = update_crm(crm_id=crm_id, body=body, user=user, db=conn)

    assert result["status"] == "ok"
    assert "priority" in result["updated_fields"]


def test_buyer_crm_update_contact_fields():
    """update_crm: contact fields (contact_name, contact_email, contact_phone) (lines 264-278)."""
    from services.api.services.api.routers.buyer_crm import update_crm, BuyerCRMUpdate

    crm_id = uuid.uuid4()
    user = _demo_user()
    existing_record = (str(crm_id),)
    conn = _make_conn(one_or_none=existing_record)
    body = BuyerCRMUpdate(
        contact_name="Jan Kowalski",
        contact_email="jan@example.com",
        contact_phone="+48123456789",
        territory="mazowieckie",
    )

    result = update_crm(crm_id=crm_id, body=body, user=user, db=conn)

    assert result["status"] == "ok"
    assert "contact_name" in result["updated_fields"]


# ═══════════════════════════════════════════════════════════════════════════════
# buyer_crm.py — delete_crm  (lines 289-292)
# ═══════════════════════════════════════════════════════════════════════════════

def test_buyer_crm_delete_rowcount_zero_raises_404():
    """delete_crm: rowcount=0 → HTTPException 404 (lines 288-289)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import delete_crm

    crm_id = uuid.uuid4()
    user = _demo_user()
    conn = _make_conn(rowcount=0)  # DELETE affected 0 rows

    with pytest.raises(HTTPException) as exc_info:
        delete_crm(crm_id=crm_id, user=user, db=conn)
    assert exc_info.value.status_code == 404


def test_buyer_crm_delete_success():
    """delete_crm: rowcount>=1 → no exception (lines 282-287)."""
    from services.api.services.api.routers.buyer_crm import delete_crm

    crm_id = uuid.uuid4()
    user = _demo_user()
    conn = _make_conn(rowcount=1)

    # Should not raise
    delete_crm(crm_id=crm_id, user=user, db=conn)
    conn.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# buyer_crm.py — buyer_tenders  (lines 299-351, 360-380)
# ═══════════════════════════════════════════════════════════════════════════════

def test_buyer_crm_tenders_not_found_404():
    """buyer_tenders: CRM record not found → HTTPException 404 (lines 299-306)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    user = _demo_user()
    conn = _make_conn(one_or_none=None)

    with pytest.raises(HTTPException) as exc_info:
        buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=50, cpv_prefix=None, year=None)
    assert exc_info.value.status_code == 404


def test_buyer_crm_tenders_success_no_filters():
    """buyer_tenders: CRM found, no filters → full response (lines 308-350)."""
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    nip = "1234567890"
    user = _demo_user()

    # Set up sequential execute results using side_effect
    crm_result = MagicMock()
    crm_result.one_or_none.return_value = (nip,)  # crm[0] = nip

    tenders_result = MagicMock()
    tenders_result.mappings.return_value.all.return_value = []

    spend_result = MagicMock()
    spend_result.mappings.return_value.all.return_value = []

    count_result = MagicMock()
    count_result.scalar.return_value = 42

    conn = MagicMock()
    conn.execute.side_effect = [crm_result, tenders_result, spend_result, count_result]
    conn.commit = MagicMock()

    result = buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=50, cpv_prefix=None, year=None)

    assert result["buyer_nip"] == nip
    assert result["total_tenders_all_time"] == 42
    assert result["tenders"] == []
    assert result["spend_history"] == []


def test_buyer_crm_tenders_with_cpv_prefix():
    """buyer_tenders: cpv_prefix filter adds condition (lines 312-314)."""
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    nip = "9876543210"
    user = _demo_user()

    crm_result = MagicMock()
    crm_result.one_or_none.return_value = (nip,)

    tenders_row = {"id": str(uuid.uuid4()), "title": "Remont drogi", "cpv_code": "45233140",
                   "province": "mazowieckie", "estimated_value": 500_000.0,
                   "offers_count": 3, "procedure_result": "awarded",
                   "date": "2024-03-15", "notice_type": "CN",
                   "contractor_name": "Firma Drogowa", "contractor_nip": "1111111111"}
    tenders_result = MagicMock()
    tenders_result.mappings.return_value.all.return_value = [tenders_row]

    spend_result = MagicMock()
    spend_result.mappings.return_value.all.return_value = []

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    conn = MagicMock()
    conn.execute.side_effect = [crm_result, tenders_result, spend_result, count_result]

    result = buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=50, cpv_prefix="4523", year=None)

    assert result["buyer_nip"] == nip
    assert len(result["tenders"]) == 1
    assert result["tenders"][0]["title"] == "Remont drogi"


def test_buyer_crm_tenders_with_year_filter():
    """buyer_tenders: year filter adds EXTRACT condition (lines 315-317)."""
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    nip = "5555555555"
    user = _demo_user()

    crm_result = MagicMock()
    crm_result.one_or_none.return_value = (nip,)

    tenders_result = MagicMock()
    tenders_result.mappings.return_value.all.return_value = []

    spend_result = MagicMock()
    spend_result.mappings.return_value.all.return_value = []

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    conn = MagicMock()
    conn.execute.side_effect = [crm_result, tenders_result, spend_result, count_result]

    result = buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=50, cpv_prefix=None, year=2024)

    assert result["buyer_nip"] == nip
    assert result["total_tenders_all_time"] == 0


def test_buyer_crm_tenders_with_both_filters():
    """buyer_tenders: both cpv_prefix AND year filters (lines 312-317)."""
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    nip = "3333333333"
    user = _demo_user()

    crm_result = MagicMock()
    crm_result.one_or_none.return_value = (nip,)

    tenders_result = MagicMock()
    tenders_result.mappings.return_value.all.return_value = []

    spend_result = MagicMock()
    spend_result.mappings.return_value.all.return_value = []

    count_result = MagicMock()
    count_result.scalar.return_value = 3

    conn = MagicMock()
    conn.execute.side_effect = [crm_result, tenders_result, spend_result, count_result]

    result = buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=10, cpv_prefix="45", year=2023)

    assert result["buyer_nip"] == nip
    assert result["total_tenders_all_time"] == 3


def test_buyer_crm_tenders_with_spend_data():
    """buyer_tenders: spend_history populated from mv_buyer_quarterly_spend (lines 331-338)."""
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    nip = "7777777777"
    user = _demo_user()

    crm_result = MagicMock()
    crm_result.one_or_none.return_value = (nip,)

    tenders_result = MagicMock()
    tenders_result.mappings.return_value.all.return_value = []

    spend_row = {"cpv5": "45233", "quarter": "2024-Q1", "n_tenders": 2,
                 "n_completed": 2, "avg_value": 300_000.0, "total_value": 600_000.0,
                 "avg_competition": 4.5}
    spend_result = MagicMock()
    spend_result.mappings.return_value.all.return_value = [spend_row]

    count_result = MagicMock()
    count_result.scalar.return_value = 10

    conn = MagicMock()
    conn.execute.side_effect = [crm_result, tenders_result, spend_result, count_result]

    result = buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=50, cpv_prefix=None, year=None)

    assert len(result["spend_history"]) == 1
    assert result["spend_history"][0]["cpv5"] == "45233"
    assert result["total_tenders_all_time"] == 10


def test_buyer_crm_tenders_no_org_400():
    """buyer_tenders: user without org_id → HTTPException 400."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import buyer_tenders

    crm_id = uuid.uuid4()
    user = _demo_user(org_id=None)
    conn = _make_conn()

    with pytest.raises(HTTPException) as exc_info:
        buyer_tenders(crm_id=crm_id, user=user, db=conn, limit=50, cpv_prefix=None, year=None)
    assert exc_info.value.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# buyer_crm.py — additional branches for create_crm success/error paths
# ═══════════════════════════════════════════════════════════════════════════════

def test_buyer_crm_create_invalid_stage():
    """create_crm: invalid crm_stage → HTTPException 400 (line 194)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import create_crm, BuyerCRMCreate

    user = _demo_user()
    conn = _make_conn()
    body = BuyerCRMCreate(buyer_nip="1234567890", crm_stage="bogus_stage")

    with pytest.raises(HTTPException) as exc_info:
        create_crm(body=body, user=user, db=conn)
    assert exc_info.value.status_code == 400


def test_buyer_crm_create_invalid_nip():
    """create_crm: NIP with letters → HTTPException 422 (line 198)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import create_crm, BuyerCRMCreate

    user = _demo_user()
    conn = _make_conn()
    body = BuyerCRMCreate(buyer_nip="ABC123", crm_stage="prospect")

    with pytest.raises(HTTPException) as exc_info:
        create_crm(body=body, user=user, db=conn)
    assert exc_info.value.status_code == 422


def test_buyer_crm_create_duplicate_raises_409():
    """create_crm: unique constraint violation → HTTPException 409 (lines 216-219)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import create_crm, BuyerCRMCreate

    user = _demo_user()
    conn = MagicMock()
    conn.execute.side_effect = Exception("duplicate key value violates unique constraint")
    conn.rollback = MagicMock()
    body = BuyerCRMCreate(buyer_nip="1234567890", crm_stage="prospect")

    with pytest.raises(HTTPException) as exc_info:
        create_crm(body=body, user=user, db=conn)
    assert exc_info.value.status_code == 409


def test_buyer_crm_create_generic_error_raises_500():
    """create_crm: non-unique DB error → HTTPException 500 (lines 220-221)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import create_crm, BuyerCRMCreate

    user = _demo_user()
    conn = MagicMock()
    conn.execute.side_effect = Exception("connection timeout")
    conn.rollback = MagicMock()
    body = BuyerCRMCreate(buyer_nip="1234567890", crm_stage="prospect")

    with pytest.raises(HTTPException) as exc_info:
        create_crm(body=body, user=user, db=conn)
    assert exc_info.value.status_code == 500


def test_buyer_crm_create_success():
    """create_crm: happy path → dict with id and crm_stage (lines 200-223)."""
    from services.api.services.api.routers.buyer_crm import create_crm, BuyerCRMCreate

    crm_id = uuid.uuid4()
    user = _demo_user()

    returned_row = {
        "id": str(crm_id),
        "buyer_nip": "1234567890",
        "crm_stage": "prospect",
        "priority": 3,
        "created_at": "2024-06-01T10:00:00",
    }
    conn = _make_conn(one_or_none=returned_row)
    # .mappings().one() returns the row
    conn.execute.return_value.mappings.return_value.one.return_value = returned_row
    conn.commit = MagicMock()

    body = BuyerCRMCreate(buyer_nip="1234567890", crm_stage="prospect", priority=3)
    result = create_crm(body=body, user=user, db=conn)

    assert result["buyer_nip"] == "1234567890"
    assert result["crm_stage"] == "prospect"


# ═══════════════════════════════════════════════════════════════════════════════
# buyer_crm.py — get_crm  (lines 226-243)
# ═══════════════════════════════════════════════════════════════════════════════

def test_buyer_crm_get_not_found_404():
    """get_crm: record not found → HTTPException 404 (lines 241-242)."""
    from fastapi import HTTPException
    from services.api.services.api.routers.buyer_crm import get_crm

    crm_id = uuid.uuid4()
    user = _demo_user()
    conn = _make_conn(one_or_none=None)

    with pytest.raises(HTTPException) as exc_info:
        get_crm(crm_id=crm_id, user=user, db=conn)
    assert exc_info.value.status_code == 404


def test_buyer_crm_get_success():
    """get_crm: record found → dict (lines 229-243)."""
    from services.api.services.api.routers.buyer_crm import get_crm

    crm_id = uuid.uuid4()
    user = _demo_user()
    row = {
        "id": str(crm_id), "buyer_nip": "1234567890", "crm_stage": "active",
        "priority": 2, "contact_name": "Test User", "contact_email": "t@t.pl",
        "contact_phone": "+48100000000", "annual_budget_est": 1_000_000.0,
        "preferred_cpv": ["45"], "territory": "mazowieckie", "notes": "note",
        "last_contact": "2024-01-01", "next_followup": "2024-07-01",
        "created_at": "2024-01-01", "updated_at": "2024-06-01",
        "buyer_name": "Urząd Testowy", "city": "Warszawa", "province": "mazowieckie",
        "total_tenders": 20, "total_value": 5_000_000.0, "top_cpv": ["45"],
    }
    conn = _make_conn(one_or_none=row)

    result = get_crm(crm_id=crm_id, user=user, db=conn)

    assert result["buyer_nip"] == "1234567890"
    assert result["crm_stage"] == "active"
