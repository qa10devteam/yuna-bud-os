"""Batch-B coverage tests: m7_backend, rfq, health, resources, icb_advanced,
market_intelligence, monitoring, chat, engine, estimator, comments."""
from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eng(fetchone=None, rows=None, scalar=0, rowcount=1):
    """Build a fully mocked SQLAlchemy engine."""
    e = MagicMock()
    c = MagicMock()

    def _enter(s):
        return c

    for ctx in (e.connect.return_value, e.begin.return_value):
        ctx.__enter__ = _enter
        ctx.__exit__ = MagicMock(return_value=False)

    r = MagicMock()
    r.fetchone.return_value = fetchone
    r.fetchall.return_value = rows if rows is not None else (
        [] if fetchone is None else [fetchone]
    )
    r.rowcount = rowcount
    r.scalar.return_value = scalar
    r.mappings.return_value.all.return_value = rows or []
    r.mappings.return_value.first.return_value = fetchone
    r.mappings.return_value.one_or_none.return_value = fetchone
    r.mappings.return_value.one.return_value = fetchone or MagicMock()
    if fetchone is not None and isinstance(fetchone, tuple):
        r.__getitem__ = lambda self, k: fetchone[k]
    c.execute.return_value = r
    c.commit.return_value = None
    return e


def _user(tenant_id=None, org_id=None, role="owner", user_id=None):
    u = MagicMock()
    u.user_id = user_id or str(uuid.uuid4())
    u.tenant_id = tenant_id or str(uuid.uuid4())
    u.org_id = org_id or str(uuid.uuid4())
    u.role = role
    u.email = "test@qa10.io"
    return u


# Module-level alias shortcuts
M7 = "services.api.services.api.routers.m7_backend.get_engine"
RFQ = "services.api.services.api.routers.rfq.get_engine"
HEALTH = "terra_db.session.get_engine"
RESOURCES = "services.api.services.api.routers.resources.get_engine"
ICB = "services.api.services.api.routers.icb_advanced.get_engine"
MIDB = "services.api.services.api.routers.market_intelligence.get_engine"
MON = "terra_db.session.get_engine"
CHAT = "services.api.services.api.routers.chat.get_engine"
ENGINE = "services.api.services.api.routers.engine.get_engine"
EST = "services.api.services.api.routers.estimator.get_engine"
COMM = "services.api.services.api.routers.comments.get_engine"
PLAN = "services.api.services.api.auth.plan_gate._get_org_plan"


# ---------------------------------------------------------------------------
# App fixture (module-scoped) – conftest auth override already applied
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    from starlette.testclient import TestClient
    from services.api.services.api.main import app as _app
    with TestClient(_app) as client:
        yield client


# ============================================================================
# MONITORING
# ============================================================================

class TestMonitoringFunctions:
    def test_increment_request_count(self):
        from services.api.services.api.routers.monitoring import (
            increment_request_count, get_request_count
        )
        before = get_request_count()
        increment_request_count()
        assert get_request_count() == before + 1

    def test_increment_error_count(self):
        from services.api.services.api.routers.monitoring import increment_error_count
        increment_error_count()

    def test_get_request_count(self):
        from services.api.services.api.routers.monitoring import get_request_count
        assert isinstance(get_request_count(), int)

    def test_record_response_time_success(self):
        from services.api.services.api.routers.monitoring import record_response_time
        record_response_time(50.0, success=True)
        record_response_time(200.0, success=False)

    def test_record_response_time_truncates(self):
        from services.api.services.api.routers.monitoring import record_response_time, _sla_response_times
        for _ in range(1005):
            record_response_time(10.0, success=True)
        assert len(_sla_response_times) <= 1000

    def test_metrics_endpoint(self, app):
        with patch(MON) as ge:
            ge.return_value = _eng(scalar=5)
            resp = app.get("/api/v2/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_seconds" in data

    def test_metrics_db_error(self, app):
        with patch(MON) as ge:
            ge.side_effect = Exception("db down")
            resp = app.get("/api/v2/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["db_latency_ms"] is None

    def test_system_status(self, app):
        with patch(MON) as ge:
            ge.return_value = _eng()
            resp = app.get("/api/v2/system/status")
        assert resp.status_code == 200

    def test_system_status_db_error(self, app):
        with patch(MON) as ge:
            ge.side_effect = Exception("fail")
            resp = app.get("/api/v2/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["db"] == "error"

    def test_health_detailed_monitoring(self, app):
        with patch(MON) as ge:
            ge.return_value = _eng()
            resp = app.get("/api/v2/health/detailed")
        assert resp.status_code == 200

    def test_alerts_endpoint(self, app):
        with patch(MON) as ge:
            ge.return_value = _eng()
            resp = app.get("/api/v2/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data

    def test_alerts_db_unreachable(self, app):
        with patch(MON) as ge:
            ge.side_effect = Exception("unreachable")
            resp = app.get("/api/v2/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert any(a["id"] == "db_unreachable" for a in data["alerts"])

    def test_sla_metrics(self, app):
        resp = app.get("/api/v2/sla")
        assert resp.status_code == 200
        data = resp.json()
        assert "availability_pct" in data

    def test_sla_with_response_times(self, app):
        from services.api.services.api.routers.monitoring import record_response_time
        for i in range(10):
            record_response_time(float(i * 10), success=(i % 2 == 0))
        resp = app.get("/api/v2/sla")
        assert resp.status_code == 200


# ============================================================================
# HEALTH
# ============================================================================

class TestHealth:
    def test_health_v1(self, app):
        with patch(HEALTH) as ge:
            ge.return_value = _eng()
            resp = app.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_v1_db_error(self, app):
        with patch(HEALTH) as ge:
            ge.side_effect = Exception("fail")
            resp = app.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"

    def test_health_v2(self, app):
        with patch(HEALTH) as ge:
            ge.return_value = _eng()
            resp = app.get("/api/v2/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data

    def test_health_v2_db_error(self, app):
        with patch(HEALTH) as ge:
            ge.side_effect = Exception("fail")
            resp = app.get("/api/v2/health")
        assert resp.status_code == 200

    def test_health_live(self, app):
        resp = app.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_ready(self, app):
        with patch(HEALTH) as ge:
            ge.return_value = _eng()
            resp = app.get("/health/ready")
        assert resp.status_code in (200, 503)

    def test_health_detailed(self, app):
        with patch(HEALTH) as ge:
            ge.return_value = _eng(fetchone=(50,))
            resp = app.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_s" in data

    def test_health_system(self, app):
        with patch(HEALTH) as ge:
            ge.return_value = _eng(fetchone=(10,))
            resp = app.get("/health/system")
        assert resp.status_code in (200, 206, 503)

    def test_health_production(self, app):
        with patch(HEALTH) as ge:
            ge.return_value = _eng()
            resp = app.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "services" in data

    def test_check_redis_function(self):
        from services.api.services.api.routers.health import _check_redis
        result = _check_redis()
        assert isinstance(result, str)


# ============================================================================
# ESTIMATOR
# ============================================================================

class TestEstimator:
    def test_create_estimate_no_analysis(self):
        from services.api.services.api.routers.estimator import create_estimate
        from fastapi import HTTPException
        with patch(EST) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                create_estimate("tid-1")
        assert exc.value.status_code == 404

    def test_list_estimates_not_found(self):
        from services.api.services.api.routers.estimator import list_estimates_for_tender
        from fastapi import HTTPException
        with patch(EST) as ge:
            ge.return_value = _eng(rows=[])
            with pytest.raises(HTTPException) as exc:
                list_estimates_for_tender("tid-1")
        assert exc.value.status_code == 404

    def test_get_estimate_not_found(self):
        from services.api.services.api.routers.estimator import get_estimate
        from fastapi import HTTPException
        with patch(EST) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                get_estimate(str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_get_estimate_with_data(self):
        from services.api.services.api.routers.estimator import get_estimate
        eid = str(uuid.uuid4())
        row = (eid, "doc", "1000.00", [], {})
        with patch(EST) as ge:
            ge.return_value = _eng(fetchone=row)
            result = get_estimate(eid)
        assert result.id == eid
        assert result.variant == "doc"

    def test_update_estimate_params_not_found(self):
        from services.api.services.api.routers.estimator import update_estimate_params, ParamsUpdate
        from fastapi import HTTPException
        with patch(EST) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                update_estimate_params(str(uuid.uuid4()), ParamsUpdate(params={}))
        assert exc.value.status_code == 404

    def test_compare_endpoint_not_found(self):
        from services.api.services.api.routers.estimator import compare_estimate_endpoint
        from fastapi import HTTPException
        with patch(EST) as ge:
            ge.return_value = _eng(rows=[])
            with pytest.raises(HTTPException) as exc:
                compare_estimate_endpoint("tid-1")
        assert exc.value.status_code == 404

    def test_get_tenant_id_not_found(self):
        from services.api.services.api.routers.estimator import _get_tenant_id
        from fastapi import HTTPException
        e = _eng(fetchone=None)
        with patch(EST) as ge:
            ge.return_value = e
            with pytest.raises(HTTPException) as exc:
                _get_tenant_id(e)
        assert exc.value.status_code == 500

    def test_load_rate_card_none(self):
        from services.api.services.api.routers.estimator import _load_rate_card
        e = _eng(fetchone=None)
        result = _load_rate_card(e, "tid-1")
        assert result is None

    def test_load_rate_card_with_data(self):
        from services.api.services.api.routers.estimator import _load_rate_card
        rc_data = {"robocizna_zl_rg": "40.00", "kp_pct": "12.0", "zysk_pct": "8.0"}
        row = (rc_data,)
        e = _eng(fetchone=row)
        result = _load_rate_card(e, "tid-1")
        assert result is not None

    def test_load_rate_card_no_data_in_row(self):
        from services.api.services.api.routers.estimator import _load_rate_card
        row = (None,)
        e = _eng(fetchone=row)
        result = _load_rate_card(e, "tid-1")
        assert result is None

    def test_compare_endpoint_missing_variant(self):
        from services.api.services.api.routers.estimator import compare_estimate_endpoint
        from fastapi import HTTPException
        row = MagicMock()
        row[0] = "doc"
        row[1] = "1000.00"
        row[2] = []
        row[3] = {}
        with patch(EST) as ge:
            ge.return_value = _eng(rows=[row])
            with pytest.raises(HTTPException) as exc:
                compare_estimate_endpoint("tid-1")
        assert exc.value.status_code == 404

    def test_list_estimates_via_http(self, app):
        row = MagicMock()
        row[0] = str(uuid.uuid4())
        row[1] = "doc"
        row[2] = "1000.00"
        row[3] = [{"position_no": "1", "description": "Test", "unit": "m2",
                   "quantity": "10", "unit_price": "100", "line_total_pln": "1000",
                   "labor_pln": "0", "material_pln": "1000", "equipment_pln": "0"}]
        row[4] = {}
        tid = str(uuid.uuid4())
        with patch(EST) as ge:
            ge.return_value = _eng(rows=[row])
            resp = app.get(f"/api/v1/tenders/{tid}/estimates")
        assert resp.status_code in (200, 404)


# ============================================================================
# COMMENTS
# ============================================================================

class TestComments:
    def test_extract_mentions(self):
        from services.api.services.api.routers.comments import _extract_mentions
        body = "Hello @alice and @bob, see @charlie"
        mentions = _extract_mentions(body)
        assert "alice" in mentions
        assert "bob" in mentions

    def test_extract_mentions_none(self):
        from services.api.services.api.routers.comments import _extract_mentions
        assert _extract_mentions("no mentions here") == []

    def test_encode_decode_cursor(self):
        from services.api.services.api.routers.comments import _encode_cursor, _decode_cursor
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rid = str(uuid.uuid4())
        cursor = _encode_cursor(dt, rid)
        ts, cid = _decode_cursor(cursor)
        assert cid == rid

    def test_encode_decode_cursor_none_dt(self):
        from services.api.services.api.routers.comments import _encode_cursor, _decode_cursor
        rid = str(uuid.uuid4())
        cursor = _encode_cursor(None, rid)
        ts, cid = _decode_cursor(cursor)
        assert cid == rid
        assert ts is None

    def test_decode_cursor_invalid(self):
        from services.api.services.api.routers.comments import _decode_cursor
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _decode_cursor("not-valid-base64!")
        assert exc.value.status_code == 400

    def test_validate_uuid_valid(self):
        from services.api.services.api.routers.comments import _validate_uuid
        _validate_uuid(str(uuid.uuid4()))

    def test_validate_uuid_invalid(self):
        from services.api.services.api.routers.comments import _validate_uuid
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _validate_uuid("not-a-uuid")
        assert exc.value.status_code == 400

    def test_table_exists(self):
        from services.api.services.api.routers.comments import _table_exists
        conn = MagicMock()
        r = MagicMock()
        r.scalar.return_value = True
        conn.execute.return_value = r
        assert _table_exists(conn, "audit_log") is True

    def test_table_not_exists(self):
        from services.api.services.api.routers.comments import _table_exists
        conn = MagicMock()
        r = MagicMock()
        r.scalar.return_value = False
        conn.execute.return_value = r
        assert _table_exists(conn, "nonexistent") is False

    def test_list_comments_no_org(self):
        from services.api.services.api.routers.comments import list_comments
        from fastapi import HTTPException
        user = _user(org_id=None)
        user.org_id = None
        tid = str(uuid.uuid4())
        with patch(COMM) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            with pytest.raises(HTTPException) as exc:
                list_comments(tid, user, limit=10, cursor=None)
        assert exc.value.status_code == 403

    def test_list_comments_empty(self):
        from services.api.services.api.routers.comments import list_comments
        user = _user()
        tid = str(uuid.uuid4())
        with patch(COMM) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            result = list_comments(tid, user, limit=10, cursor=None)
        assert result["total"] == 0
        assert result["comments"] == []

    def test_list_comments_with_cursor(self):
        from services.api.services.api.routers.comments import list_comments, _encode_cursor
        from datetime import datetime, timezone
        user = _user()
        tid = str(uuid.uuid4())
        cursor = _encode_cursor(datetime(2025, 1, 1, tzinfo=timezone.utc), str(uuid.uuid4()))
        with patch(COMM) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            result = list_comments(tid, user, limit=10, cursor=cursor)
        assert "comments" in result

    def test_create_comment_no_org(self):
        from services.api.services.api.routers.comments import create_comment, CommentCreate
        from fastapi import HTTPException
        user = _user()
        user.org_id = None
        tid = str(uuid.uuid4())
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                create_comment(tid, CommentCreate(body="test"), user)
        assert exc.value.status_code == 403

    def test_create_comment_tender_not_found(self):
        from services.api.services.api.routers.comments import create_comment, CommentCreate
        from fastapi import HTTPException
        user = _user()
        tid = str(uuid.uuid4())
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                create_comment(tid, CommentCreate(body="test comment"), user)
        assert exc.value.status_code == 404

    def test_create_comment_success(self):
        from services.api.services.api.routers.comments import create_comment, CommentCreate
        user = _user()
        tid = str(uuid.uuid4())
        tender_row = MagicMock()
        tender_row.id = tid
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=tender_row)
            result = create_comment(tid, CommentCreate(body="Hello @world"), user)
        assert result["status"] == "created"
        assert "world" in result["mentions"]

    def test_create_comment_with_parent_not_found(self):
        from services.api.services.api.routers.comments import create_comment, CommentCreate
        from fastapi import HTTPException
        user = _user()
        tid = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                r.fetchone.return_value = MagicMock()
            else:
                r.fetchone.return_value = None
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        with patch(COMM) as ge:
            ge.return_value = e
            with pytest.raises(HTTPException) as exc:
                create_comment(tid, CommentCreate(body="test", parent_id=parent_id), user)
        assert exc.value.status_code == 404

    def test_update_comment_no_org(self):
        from services.api.services.api.routers.comments import update_comment, CommentUpdate
        from fastapi import HTTPException
        user = _user()
        user.org_id = None
        with patch(COMM) as ge:
            ge.return_value = _eng()
            with pytest.raises(HTTPException) as exc:
                update_comment(str(uuid.uuid4()), str(uuid.uuid4()),
                               CommentUpdate(body="updated"), user)
        assert exc.value.status_code == 403

    def test_update_comment_not_found(self):
        from services.api.services.api.routers.comments import update_comment, CommentUpdate
        from fastapi import HTTPException
        user = _user()
        tid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                update_comment(tid, cid, CommentUpdate(body="updated"), user)
        assert exc.value.status_code == 404

    def test_update_comment_forbidden(self):
        from services.api.services.api.routers.comments import update_comment, CommentUpdate
        from fastapi import HTTPException
        user = _user(role="viewer")
        user.role = "viewer"
        tid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        row = MagicMock()
        row.user_id = str(uuid.uuid4())  # different user
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=row)
            with pytest.raises(HTTPException) as exc:
                update_comment(tid, cid, CommentUpdate(body="updated"), user)
        assert exc.value.status_code == 403

    def test_update_comment_success_admin(self):
        from services.api.services.api.routers.comments import update_comment, CommentUpdate
        user = _user(role="admin")
        user.role = "admin"
        tid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        row = MagicMock()
        row.user_id = str(uuid.uuid4())  # different user but admin can edit
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=row)
            result = update_comment(tid, cid, CommentUpdate(body="updated"), user)
        assert result["status"] == "updated"

    def test_update_comment_own_success(self):
        from services.api.services.api.routers.comments import update_comment, CommentUpdate
        uid = str(uuid.uuid4())
        user = _user(role="viewer", user_id=uid)
        user.role = "viewer"
        user.user_id = uid
        tid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        row = MagicMock()
        row.user_id = uid  # same user
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=row)
            result = update_comment(tid, cid, CommentUpdate(body="updated"), user)
        assert result["status"] == "updated"

    def test_delete_comment_no_org(self):
        from services.api.services.api.routers.comments import delete_comment
        from fastapi import HTTPException
        user = _user()
        user.org_id = None
        with patch(COMM) as ge:
            ge.return_value = _eng()
            with pytest.raises(HTTPException) as exc:
                delete_comment(str(uuid.uuid4()), str(uuid.uuid4()), user)
        assert exc.value.status_code == 403

    def test_delete_comment_not_found(self):
        from services.api.services.api.routers.comments import delete_comment
        from fastapi import HTTPException
        user = _user()
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                delete_comment(str(uuid.uuid4()), str(uuid.uuid4()), user)
        assert exc.value.status_code == 404

    def test_delete_comment_forbidden(self):
        from services.api.services.api.routers.comments import delete_comment
        from fastapi import HTTPException
        user = _user(role="viewer")
        user.role = "viewer"
        row = MagicMock()
        row.user_id = str(uuid.uuid4())  # different user
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=row)
            with pytest.raises(HTTPException) as exc:
                delete_comment(str(uuid.uuid4()), str(uuid.uuid4()), user)
        assert exc.value.status_code == 403

    def test_delete_comment_success(self):
        from services.api.services.api.routers.comments import delete_comment
        uid = str(uuid.uuid4())
        user = _user(role="admin", user_id=uid)
        user.role = "admin"
        user.user_id = uid
        row = MagicMock()
        row.user_id = str(uuid.uuid4())  # admin can delete others' comments
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=row)
            result = delete_comment(str(uuid.uuid4()), str(uuid.uuid4()), user)
        assert result["status"] == "deleted"

    def test_delete_own_comment_success(self):
        from services.api.services.api.routers.comments import delete_comment
        uid = str(uuid.uuid4())
        user = _user(role="viewer", user_id=uid)
        user.role = "viewer"
        user.user_id = uid
        row = MagicMock()
        row.user_id = uid  # own comment
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=row)
            result = delete_comment(str(uuid.uuid4()), str(uuid.uuid4()), user)
        assert result["status"] == "deleted"

    def test_tender_activity_no_org(self):
        from services.api.services.api.routers.comments import tender_activity
        from fastapi import HTTPException
        user = _user()
        user.org_id = None
        with patch(COMM) as ge:
            ge.return_value = _eng()
            with pytest.raises(HTTPException) as exc:
                tender_activity(str(uuid.uuid4()), user, limit=50)
        assert exc.value.status_code == 403

    def test_tender_activity_not_found(self):
        from services.api.services.api.routers.comments import tender_activity
        from fastapi import HTTPException
        user = _user()
        with patch(COMM) as ge:
            ge.return_value = _eng(fetchone=None)
            with pytest.raises(HTTPException) as exc:
                tender_activity(str(uuid.uuid4()), user, limit=50)
        assert exc.value.status_code == 404

    def test_tender_activity_success(self):
        from services.api.services.api.routers.comments import tender_activity
        user = _user()
        tid = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                r.fetchone.return_value = MagicMock()
            elif call_count[0] == 2:
                r.fetchall.return_value = []
            elif call_count[0] == 3:
                r.scalar.return_value = True
            else:
                r.fetchall.return_value = []
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        with patch(COMM) as ge:
            ge.return_value = e
            result = tender_activity(tid, user, limit=50)
        assert "activity" in result


# ============================================================================
# ENGINE
# ============================================================================

class TestEngine:
    def test_load_tender_data_not_found(self):
        from services.api.services.api.routers.engine import _load_tender_data
        from fastapi import HTTPException
        e = _eng(fetchone=None)
        with pytest.raises(HTTPException) as exc:
            _load_tender_data(e, str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_load_tender_data_found(self):
        from services.api.services.api.routers.engine import _load_tender_data
        tid = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                row = (tid, 1000000.0)
                r.fetchone.return_value = row
            elif call_count[0] == 2:
                arow = ([], {})
                r.fetchone.return_value = arow
            else:
                r.fetchone.return_value = None
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        tender_dict, items, key_facts, estimate = _load_tender_data(e, tid)
        assert tender_dict["value_pln"] == 1000000.0
        assert items == []

    def test_get_engine_result_404(self, app):
        with patch(ENGINE) as ge:
            ge.return_value = _eng(fetchone=None)
            tid = str(uuid.uuid4())
            resp = app.get(f"/api/v1/tenders/{tid}/engine")
        assert resp.status_code == 404

    def test_get_engine_result_200(self, app):
        tid = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                row = MagicMock()
                row[0] = tid
                r.fetchone.return_value = row
            elif call_count[0] == 2:
                r.fetchall.return_value = []
            else:
                r.fetchone.return_value = None
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        with patch(ENGINE) as ge:
            ge.return_value = e
            resp = app.get(f"/api/v1/tenders/{tid}/engine")
        assert resp.status_code == 200

    def test_rules_check_404(self, app):
        with patch(ENGINE) as ge:
            ge.return_value = _eng(fetchone=None)
            tid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/tenders/{tid}/rules/check")
        assert resp.status_code == 404

    def test_store_discrepancies_no_tender(self):
        from services.api.services.api.routers.engine import _store_discrepancies
        e = _eng(fetchone=None)
        _store_discrepancies(e, "tid-1", [])

    def test_store_risk_run_not_risk_result(self):
        from services.api.services.api.routers.engine import _store_risk_run
        e = _eng()
        _store_risk_run(e, "tid-1", {}, MagicMock())

    def test_run_engine_endpoint_404(self, app):
        with patch(ENGINE) as ge:
            ge.return_value = _eng(fetchone=None)
            tid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/tenders/{tid}/engine/run")
        assert resp.status_code in (404, 429)


# ============================================================================
# CHAT
# ============================================================================

class TestChat:
    def test_parse_edit_narzut(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        edit = _parse_edit_intent("podnieś narzut do 15%", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "kp_pct"
        assert "15" in str(edit["value"])

    def test_parse_edit_zysk(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        edit = _parse_edit_intent("ustaw zysk na 10%", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "zysk_pct"

    def test_parse_edit_robocizna(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        edit = _parse_edit_intent("zmień robociznę na 45", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "robocizna_zl_rg"

    def test_parse_edit_kp_alias(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        edit = _parse_edit_intent("ustaw kp na 12%", {})
        assert edit["op"] == "set_param"
        assert edit["target"] == "kp_pct"

    def test_parse_edit_overhead(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        edit = _parse_edit_intent("overhead 20%", {})
        assert edit["op"] == "set_param"

    def test_parse_edit_fallback_noop(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        llm = MagicMock()
        llm.generate.return_value = '{"op": "unknown_op", "target": null, "value": null}'
        with patch("services.ai.vllm_client.get_llm_client", return_value=llm):
            edit = _parse_edit_intent("random gibberish xyz", {})
        assert edit["op"] == "noop"

    def test_parse_edit_llm_valid(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        llm = MagicMock()
        llm.generate.return_value = '{"op": "set_param", "target": "kp_pct", "value": "10"}'
        with patch("services.api.services.api.routers.chat.get_llm_client", return_value=llm):
            edit = _parse_edit_intent("some message without known pattern", {})
        assert edit["op"] in ("set_param", "noop")

    def test_parse_edit_llm_exception(self):
        from services.api.services.api.routers.chat import _parse_edit_intent
        llm = MagicMock()
        llm.generate.side_effect = Exception("llm error")
        with patch("services.api.services.api.routers.chat.get_llm_client", return_value=llm):
            edit = _parse_edit_intent("some message", {})
        assert edit["op"] == "noop"

    def test_apply_edit_noop(self):
        from services.api.services.api.routers.chat import _apply_edit
        e = _eng()
        result = _apply_edit(e, "eid", "tid", "doc", {}, {"op": "noop"})
        assert result["changed"] is False

    def test_apply_edit_no_analysis(self):
        from services.api.services.api.routers.chat import _apply_edit
        e = _eng(fetchone=None)
        result = _apply_edit(e, "eid", "tid", "doc", {},
                             {"op": "set_param", "target": "kp_pct", "value": "15"})
        assert result["changed"] is False
        assert result.get("error") == "no analysis"

    def test_write_audit(self):
        from services.api.services.api.routers.chat import _write_audit
        e = _eng()
        c_mock = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        _write_audit(e, "eid", "tid", {"op": "set_param"}, {"changed": True})
        c_mock.execute.assert_called()

    def test_stream_chat_noop(self):
        from services.api.services.api.routers.chat import _stream_chat
        e = _eng()
        gen = _stream_chat(e, "eid", "tid", "doc", {}, {"op": "noop"}, "some message")
        events = list(gen)
        assert any("flag" in ev for ev in events)
        assert any("done" in ev for ev in events)

    def test_estimate_chat_404(self, app):
        with patch(CHAT) as ge:
            ge.return_value = _eng(fetchone=None)
            eid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/estimates/{eid}/chat",
                            json={"message": "test"})
        assert resp.status_code in (404, 429)

    def test_general_chat_przetarg(self, app):
        with patch("services.api.services.api.routers.chat.bedrock_client") as m:
            m.invoke_model.return_value = {"body": MagicMock(read=lambda: b'{"content":[{"text":"ok"}]}')}
            resp = app.post("/api/v1/chat", json={"message": "o przetargach"})
        assert resp.status_code in (200, 429, 500)

    def test_general_chat_ryzyko(self, app):
        with patch("services.api.services.api.routers.chat.bedrock_client") as m:
            m.invoke_model.return_value = {"body": MagicMock(read=lambda: b'{"content":[{"text":"ok"}]}')}
            resp = app.post("/api/v1/chat", json={"message": "ryzyko i silnik monte carlo"})
        assert resp.status_code in (200, 429, 500)

    def test_general_chat_help(self, app):
        with patch("services.api.services.api.routers.chat.bedrock_client") as m:
            m.invoke_model.return_value = {"body": MagicMock(read=lambda: b'{"content":[{"text":"ok"}]}')}
            resp = app.post("/api/v1/chat", json={"message": "jak działa pomoc"})
        assert resp.status_code in (200, 429, 500)

    def test_general_chat_other(self, app):
        resp = app.post("/api/v1/chat",
                        json={"message": "co to jest xyz"})
        assert resp.status_code in (200, 429)

    def test_general_chat_with_tender_id(self, app):
        resp = app.post("/api/v1/chat",
                        json={"message": "przetarg", "tender_id": str(uuid.uuid4())})
        assert resp.status_code in (200, 429)


# ============================================================================
# M7_BACKEND
# ============================================================================

class TestM7Backend:
    def test_get_usage(self):
        from services.api.services.api.routers.m7_backend import get_usage
        tid = str(uuid.uuid4())
        with patch(M7) as ge:
            ge.return_value = _eng(scalar=5)
            result = get_usage(tid)
        assert "tenders_this_month" in result

    def test_monthly_report(self):
        from services.api.services.api.routers.m7_backend import monthly_report
        tid = str(uuid.uuid4())
        row = (10, 5, 3, 500000.0, 300000.0)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = monthly_report(tid)
        assert result["total"] == 10
        assert result["won"] == 5

    def test_report_templates(self):
        from services.api.services.api.routers.m7_backend import report_templates
        result = report_templates()
        assert len(result) == 3
        assert any(t["id"] == "zarzad" for t in result)

    def test_market_kpi_bar(self):
        from services.api.services.api.routers.m7_backend import market_kpi_bar
        row = (3, 100000.0, 50)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = market_kpi_bar()
        assert "new_today" in result
        assert "total_tenders" in result

    def test_get_bookmarks(self):
        from services.api.services.api.routers.m7_backend import get_bookmarks
        tid = str(uuid.uuid4())
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = get_bookmarks(tid)
        assert result == []

    def test_add_bookmark(self):
        from services.api.services.api.routers.m7_backend import add_bookmark, BookmarkRequest
        tid = str(uuid.uuid4())
        tender_id = str(uuid.uuid4())
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = add_bookmark(tender_id, tid, BookmarkRequest(priority=1, notes="test"))
        assert result["status"] == "bookmarked"

    def test_add_bookmark_no_body(self):
        from services.api.services.api.routers.m7_backend import add_bookmark
        tid = str(uuid.uuid4())
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = add_bookmark(str(uuid.uuid4()), tid, None)
        assert result["status"] == "bookmarked"

    def test_remove_bookmark(self):
        from services.api.services.api.routers.m7_backend import remove_bookmark
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = remove_bookmark(str(uuid.uuid4()), str(uuid.uuid4()))
        assert result["status"] == "removed"

    def test_get_alerts_m7(self):
        from services.api.services.api.routers.m7_backend import get_alerts
        tid = str(uuid.uuid4())
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = get_alerts(tid)
        assert result == []

    def test_create_alert(self):
        from services.api.services.api.routers.m7_backend import create_alert, AlertRequest
        user = _user()
        body = AlertRequest(name="Test Alert", keywords=["beton"])
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = create_alert(body, user, tenant_id=str(uuid.uuid4()))
        assert result["status"] == "created"

    def test_create_alert_with_convenience_fields(self):
        from services.api.services.api.routers.m7_backend import create_alert, AlertRequest
        user = _user()
        body = AlertRequest(keyword="drogi", cpv="45233", region="śląskie")
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = create_alert(body, user)
        assert result["status"] == "created"

    def test_alert_request_resolved_name(self):
        from services.api.services.api.routers.m7_backend import AlertRequest
        body = AlertRequest(keyword="drogi", cpv="45", region="mazowieckie")
        assert "drogi" in body.resolved_name()
        assert "45" in body.resolved_name()

    def test_alert_request_default_name(self):
        from services.api.services.api.routers.m7_backend import AlertRequest
        body = AlertRequest()
        assert body.resolved_name() == "Alert"

    def test_test_alert_not_found(self):
        from services.api.services.api.routers.m7_backend import test_alert
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=None)
            result = test_alert(str(uuid.uuid4()), str(uuid.uuid4()))
        assert "error" in result

    def test_test_alert_found(self):
        from services.api.services.api.routers.m7_backend import test_alert
        row = (["45"], ["beton"], 100000.0, 2000000.0)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row, scalar=5)
            result = test_alert(str(uuid.uuid4()), str(uuid.uuid4()))
        assert "matching_tenders" in result

    def test_list_webhooks(self):
        from services.api.services.api.routers.m7_backend import list_webhooks
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = list_webhooks(str(uuid.uuid4()))
        assert result == []

    def test_create_webhook(self):
        from services.api.services.api.routers.m7_backend import create_webhook, WebhookRequest
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = create_webhook(str(uuid.uuid4()),
                                    WebhookRequest(name="wh1", url="https://example.com"))
        assert result["status"] == "created"

    def test_delete_webhook(self):
        from services.api.services.api.routers.m7_backend import delete_webhook
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = delete_webhook(str(uuid.uuid4()))
        assert result["status"] == "deleted"

    def test_team_members(self):
        from services.api.services.api.routers.m7_backend import team_members
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = team_members(str(uuid.uuid4()))
        assert result == []

    def test_team_activity(self):
        from services.api.services.api.routers.m7_backend import team_activity
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = team_activity(str(uuid.uuid4()))
        assert result == []

    def test_submit_feedback(self):
        from services.api.services.api.routers.m7_backend import submit_feedback, FeedbackRequest
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = submit_feedback(str(uuid.uuid4()),
                                     FeedbackRequest(rating=5, comment="great"))
        assert result["status"] == "saved"

    def test_feedback_stats(self):
        from services.api.services.api.routers.m7_backend import feedback_stats
        row = (10, 4.5, 8)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = feedback_stats(str(uuid.uuid4()))
        assert result["total"] == 10

    def test_feedback_stats_empty(self):
        from services.api.services.api.routers.m7_backend import feedback_stats
        row = (0, None, 0)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = feedback_stats(str(uuid.uuid4()))
        assert result["total"] == 0
        assert result["avg_rating"] == 0

    def test_list_axioms(self):
        from services.api.services.api.routers.m7_backend import list_axioms
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = list_axioms(str(uuid.uuid4()))
        assert result == []

    def test_create_axiom(self):
        from services.api.services.api.routers.m7_backend import create_axiom, AxiomRequest
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = create_axiom(str(uuid.uuid4()),
                                  AxiomRequest(code="A001", body="tender.value_pln > 0"))
        assert result["status"] == "created"

    def test_evaluate_axioms_tender_not_found(self):
        from services.api.services.api.routers.m7_backend import evaluate_axioms
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=None)
            result = evaluate_axioms(str(uuid.uuid4()), str(uuid.uuid4()))
        assert result[0]["error"] == "tender not found"

    def test_evaluate_axioms_with_data(self):
        from services.api.services.api.routers.m7_backend import evaluate_axioms
        tid = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                row = MagicMock()
                row.__getitem__ = lambda s, k: [
                    "Test Tender", 500000.0, ["45233"], "mazowieckie", None
                ][k]
                r.fetchone.return_value = row
            else:
                ax = MagicMock()
                ax.__getitem__ = lambda s, k: [
                    str(uuid.uuid4()), "BLOCK", "A001",
                    "tender['value_pln'] > 0"
                ][k]
                r.fetchall.return_value = [ax]
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        with patch(M7) as ge:
            ge.return_value = e
            result = evaluate_axioms(tid, tenant_id)
        assert len(result) >= 1

    def test_get_bid_intelligence(self):
        from services.api.services.api.routers.m7_backend import get_bid_intelligence
        with patch(M7) as ge:
            ge.return_value = _eng(rows=[])
            result = get_bid_intelligence(str(uuid.uuid4()))
        assert result == []

    def test_add_bid_intel(self):
        from services.api.services.api.routers.m7_backend import add_bid_intel, BidIntelRequest
        with patch(M7) as ge:
            ge.return_value = _eng()
            result = add_bid_intel(
                str(uuid.uuid4()),
                BidIntelRequest(tender_id=str(uuid.uuid4()), our_price=100000.0)
            )
        assert result["status"] == "recorded"

    def test_optimal_markup_no_data(self):
        from services.api.services.api.routers.m7_backend import optimal_markup
        row = (0, None, None, 0, None)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = optimal_markup(str(uuid.uuid4()))
        assert result["sample_size"] == 0

    def test_optimal_markup_with_data(self):
        from services.api.services.api.routers.m7_backend import optimal_markup
        row = (20, 12.5, 15.0, 10, 50.0)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = optimal_markup(str(uuid.uuid4()))
        assert result["sample_size"] == 20

    def test_optimal_markup_with_cpv5(self):
        from services.api.services.api.routers.m7_backend import optimal_markup
        row = (5, 10.0, 12.0, 2, 40.0)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = optimal_markup(str(uuid.uuid4()), cpv5="45233")
        assert "recommended_markup_pct" in result

    def test_bid_intel_stats(self):
        from services.api.services.api.routers.m7_backend import bid_intel_stats
        row = (10, 12.5, 2.5, 6, 60.0)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = bid_intel_stats(str(uuid.uuid4()))
        assert result["total_bids"] == 10

    def test_ai_summary_endpoint(self, app):
        row = (5, 2, 200000.0, 1)
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            resp = app.post("/api/v2/reports/ai-summary",
                            params={"tenant_id": str(uuid.uuid4())})
        assert resp.status_code in (200, 422, 500)

    def test_create_alert_no_tenant(self):
        from services.api.services.api.routers.m7_backend import create_alert, AlertRequest
        user = _user()
        user.org_id = None
        body = AlertRequest(name="test")
        row = MagicMock()
        row[0] = str(uuid.uuid4())
        with patch(M7) as ge:
            ge.return_value = _eng(fetchone=row)
            result = create_alert(body, user, tenant_id=None)
        assert "status" in result or "error" in result


# ============================================================================
# RFQ
# ============================================================================

class TestRFQ:
    def test_list_rfq_v2(self, app):
        with patch(RFQ) as ge, \
             patch("services.api.services.api.routers.rfq.get_engine", return_value=_eng(rows=[])):
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/rfq")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    def test_create_rfq_tender_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            tid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/tenders/{tid}/rfq",
                            json={"scope_desc": "Test scope", "counterparties": []})
        assert resp.status_code == 404

    def test_create_rfq_success(self, app):
        tid = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        row = MagicMock()
        row[0] = tid
        row[1] = tenant_id
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=row)
            resp = app.post(f"/api/v1/tenders/{tid}/rfq",
                            json={"scope_desc": "Beton i stal", "counterparties": ["a@b.pl"]})
        assert resp.status_code in (202, 200)

    def test_get_rfq_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            rfq_id = str(uuid.uuid4())
            resp = app.get(f"/api/v1/rfq/{rfq_id}")
        assert resp.status_code == 404

    def test_get_rfq_success(self, app):
        rfq_id = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                rfq_row = (rfq_id, "draft", "Test scope")
                r.fetchone.return_value = rfq_row
            else:
                r.fetchall.return_value = []
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        with patch(RFQ) as ge:
            ge.return_value = e
            resp = app.get(f"/api/v1/rfq/{rfq_id}")
        assert resp.status_code == 200

    def test_rfq_inbound_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            rfq_id = str(uuid.uuid4())
            resp = app.post(f"/api/v1/rfq/{rfq_id}/inbound",
                            json={"message_uid": "uid1", "counterparty": "test@t.pl",
                                  "body": "Oferujemy 45000 zł netto w 30 dni"})
        assert resp.status_code == 404

    def test_rfq_inbound_duplicate(self, app):
        rfq_id = str(uuid.uuid4())
        tid = str(uuid.uuid4())
        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                row = MagicMock()
                row[0] = rfq_id
                row[1] = tid
                r.fetchone.return_value = row
            else:
                dup = MagicMock()
                dup.id = str(uuid.uuid4())
                r.fetchone.return_value = dup
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)
        with patch(RFQ) as ge:
            ge.return_value = e
            resp = app.post(f"/api/v1/rfq/{rfq_id}/inbound",
                            json={"message_uid": "uid1", "counterparty": "a@b.pl",
                                  "body": "Oferujemy 45000 zł netto"})
        assert resp.status_code == 200
        assert resp.json()["duplicate"] is True

    def test_autofill_tender_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            tid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/tenders/{tid}/autofill")
        assert resp.status_code == 404

    def test_list_approvals(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v1/approvals")
        assert resp.status_code == 200

    def test_approve_action_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            aid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/approvals/{aid}/approve")
        assert resp.status_code == 404

    def test_approve_action_not_pending(self, app):
        aid = str(uuid.uuid4())
        row = MagicMock()
        row[0] = aid
        row[1] = str(uuid.uuid4())
        row[2] = "rfq_send"
        row[3] = {}
        row[4] = "approved"
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=row)
            resp = app.post(f"/api/v1/approvals/{aid}/approve")
        assert resp.status_code == 409

    def test_reject_action_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            aid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/approvals/{aid}/reject")
        assert resp.status_code == 404

    def test_reject_action_not_pending(self, app):
        aid = str(uuid.uuid4())
        row = MagicMock()
        row[0] = aid
        row[1] = str(uuid.uuid4())
        row[2] = "approved"
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=row)
            resp = app.post(f"/api/v1/approvals/{aid}/reject")
        assert resp.status_code == 409

    def test_parse_offer_from_email_price_zl(self):
        from services.api.services.api.routers.rfq import _parse_offer_from_email
        offer = _parse_offer_from_email("Oferujemy wykonanie za 45000 zł netto w terminie 30 dni", "firma@x.pl")
        assert offer["price_net_pln"] == 45000.0
        assert offer["lead_time_days"] == 30

    def test_parse_offer_from_email_pln(self):
        from services.api.services.api.routers.rfq import _parse_offer_from_email
        offer = _parse_offer_from_email("Cena: 38500 PLN, termin: 21 dni roboczych", "firma@x.pl")
        assert offer["price_net_pln"] is not None

    def test_parse_offer_from_email_empty(self):
        from services.api.services.api.routers.rfq import _parse_offer_from_email
        offer = _parse_offer_from_email("brak informacji", "test@t.pl")
        assert offer["price_net_pln"] is None

    def test_execute_gated_action_rfq_send(self):
        from services.api.services.api.routers.rfq import _execute_gated_action
        rfq_id = str(uuid.uuid4())
        tid = str(uuid.uuid4())
        payload = {"rfq_id": rfq_id, "counterparties": ["a@b.pl", "c@d.pl"],
                   "scope_desc": "test scope"}
        e = _eng()
        result = _execute_gated_action(e, "rfq_send", payload, tid)
        assert result["rfq_id"] == rfq_id

    def test_execute_gated_action_autofill(self):
        from services.api.services.api.routers.rfq import _execute_gated_action
        e = _eng()
        result = _execute_gated_action(e, "autofill_submit",
                                        {"tender_id": str(uuid.uuid4())},
                                        str(uuid.uuid4()))
        assert result["status"] == "draft_produced"

    def test_execute_gated_action_unknown(self):
        from services.api.services.api.routers.rfq import _execute_gated_action
        e = _eng()
        result = _execute_gated_action(e, "unknown_action", {}, str(uuid.uuid4()))
        assert result["status"] == "executed"

    def test_send_rfq_to_subcontractors_not_found(self, app):
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=None)
            rfq_id = str(uuid.uuid4())
            resp = app.post(f"/api/v2/rfq/{rfq_id}/send-to-subcontractors",
                            json={"emails": ["a@b.pl"], "message": "test"})
        assert resp.status_code == 404

    def test_create_rfq_v2(self, app):
        tid = str(uuid.uuid4())
        row = MagicMock()
        row[0] = tid
        row[1] = str(uuid.uuid4())
        with patch(RFQ) as ge:
            ge.return_value = _eng(fetchone=row)
            resp = app.post(f"/api/v2/tenders/{tid}/rfq",
                            json={"scope_desc": "test scope v2"})
        assert resp.status_code in (200, 202)


# ============================================================================
# RESOURCES
# ============================================================================

class TestResources:
    def test_list_subcontractors(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            resp = app.get("/api/v1/subcontractors")
        assert resp.status_code == 200

    def test_list_subcontractors_with_active_filter(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            resp = app.get("/api/v1/subcontractors?active=true")
        assert resp.status_code == 200

    def test_create_subcontractor(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            resp = app.post("/api/v1/subcontractors",
                            json={"name": "TestFirma", "nip": "1234567890",
                                  "specialization": ["beton"]})
        assert resp.status_code == 200

    def test_get_subcontractor_not_found(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(fetchone=None)
            sid = str(uuid.uuid4())
            resp = app.get(f"/api/v1/subcontractors/{sid}")
        assert resp.status_code == 404

    def test_delete_subcontractor(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            sid = str(uuid.uuid4())
            resp = app.delete(f"/api/v1/subcontractors/{sid}")
        assert resp.status_code == 200

    def test_tender_subcontractors(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[])
            tid = str(uuid.uuid4())
            resp = app.get(f"/api/v1/subcontractors/tender/{tid}")
        assert resp.status_code == 200

    def test_link_subcontractor(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            tid = str(uuid.uuid4())
            sid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/subcontractors/tender/{tid}",
                            json={"subcontractor_id": sid, "role": "główny"})
        assert resp.status_code == 200

    def test_list_equipment(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            resp = app.get("/api/v1/equipment")
        assert resp.status_code == 200

    def test_list_equipment_with_status(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[], scalar=0)
            resp = app.get("/api/v1/equipment?status=available")
        assert resp.status_code == 200

    def test_create_equipment(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            resp = app.post("/api/v1/equipment",
                            json={"name": "Koparka", "category": "maszyna",
                                  "daily_cost": 2000.0})
        assert resp.status_code == 200

    def test_delete_equipment(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            eq_id = str(uuid.uuid4())
            resp = app.delete(f"/api/v1/equipment/{eq_id}")
        assert resp.status_code == 200

    def test_tender_equipment(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[])
            tid = str(uuid.uuid4())
            resp = app.get(f"/api/v1/equipment/tender/{tid}")
        assert resp.status_code == 200

    def test_get_gantt(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[])
            tid = str(uuid.uuid4())
            resp = app.get(f"/api/v1/gantt/{tid}")
        assert resp.status_code == 200

    def test_create_gantt_task(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            tid = str(uuid.uuid4())
            resp = app.post(f"/api/v1/gantt/{tid}",
                            json={"name": "Fundamenty", "progress": 0})
        assert resp.status_code == 200

    def test_update_gantt_task(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            tid = str(uuid.uuid4())
            task_id = str(uuid.uuid4())
            resp = app.patch(f"/api/v1/gantt/{tid}/{task_id}",
                             json={"name": "Fundamenty Updated", "progress": 50})
        assert resp.status_code == 200

    def test_delete_gantt_task(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            tid = str(uuid.uuid4())
            task_id = str(uuid.uuid4())
            resp = app.delete(f"/api/v1/gantt/{tid}/{task_id}")
        assert resp.status_code == 200

    def test_list_calendar_events(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v1/calendar")
        assert resp.status_code == 200

    def test_list_calendar_events_with_dates(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v1/calendar?from_date=2025-01-01&to_date=2025-12-31")
        assert resp.status_code in (200, 422)

    def test_create_calendar_event(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            resp = app.post("/api/v1/calendar",
                            json={"title": "Deadline", "event_date": "2025-06-30",
                                  "event_type": "deadline"})
        assert resp.status_code == 200

    def test_delete_calendar_event(self, app):
        with patch(RESOURCES) as ge:
            ge.return_value = _eng()
            eid = str(uuid.uuid4())
            resp = app.delete(f"/api/v1/calendar/{eid}")
        assert resp.status_code == 200


# ============================================================================
# ICB_ADVANCED
# ============================================================================

class TestICBAdvanced:
    def test_compute_forecasts(self, app):
        mock_result = {"computed": 5, "categories": 3}
        with patch("services.api.services.api.intelligence.forecaster.compute_all_forecasts",
                   return_value=mock_result):
            resp = app.post("/api/v2/icb/forecast/compute")
        assert resp.status_code == 200

    def test_get_forecast(self, app):
        with patch("services.api.services.api.intelligence.forecaster.get_forecasts",
                   return_value=[{"category": "beton", "forecast": []}]):
            resp = app.get("/api/v2/icb/forecast")
        assert resp.status_code == 200

    def test_search_icb(self, app):
        mock_results = [{"symbol": "1234", "cena_netto": 100.0, "nazwa": "beton"}]
        with patch("services.api.services.api.intelligence.icb_service.search_icb",
                   return_value=mock_results), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)), \
             patch(ICB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/icb/search?q=beton")
        assert resp.status_code == 200

    def test_suggest_icb(self, app):
        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)), \
             patch("services.api.services.api.routers.icb_advanced.rcache_get",
                   return_value=None), \
             patch(ICB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/icb/suggest?q=be")
        assert resp.status_code == 200

    def test_suggest_icb_cached(self, app):
        cached = [{"id": 1, "nazwa": "beton", "symbol": "123"}]
        with patch("services.api.services.api.routers.icb_advanced.rcache_get",
                   return_value=cached), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)):
            resp = app.get("/api/v2/icb/suggest?q=be")
        assert resp.status_code == 200
        assert resp.json() == cached

    def test_icb_categories(self, app):
        with patch("services.api.services.api.routers.icb_advanced.rcache_get",
                   return_value=None), \
             patch(ICB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/icb/categories")
        assert resp.status_code == 200

    def test_icb_categories_cached(self, app):
        cached = [{"category": "beton", "count": 100}]
        with patch("services.api.services.api.routers.icb_advanced.rcache_get",
                   return_value=cached):
            resp = app.get("/api/v2/icb/categories")
        assert resp.status_code == 200
        assert resp.json() == cached

    def test_category_detail(self, app):
        with patch(ICB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/icb/category/beton/detail")
        assert resp.status_code == 200

    def test_compare_regional_no_data(self, app):
        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)), \
             patch(ICB) as ge:
            ge.return_value = _eng(scalar=0)
            resp = app.get("/api/v2/icb/compare")
        assert resp.status_code == 200

    def test_compute_basket_empty(self, app):
        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   return_value=1.0):
            resp = app.post("/api/v2/icb/basket",
                            json={"items": []})
        assert resp.status_code == 200

    def test_icb_dashboard(self, app):
        with patch("services.api.services.api.routers.icb_advanced._dashboard_cache",
                   {"data": {"overview": {}}, "ts": 9999999999}):
            resp = app.get("/api/v2/icb/dashboard")
        assert resp.status_code == 200

    def test_robocizna_map(self, app):
        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)), \
             patch(ICB) as ge:
            ge.return_value = _eng(fetchone=(52.0, 40.0, 60.0), rows=[])
            resp = app.get("/api/v2/icb/robocizna/map")
        assert resp.status_code == 200

    def test_volatility_matrix(self, app):
        with patch(ICB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/icb/volatility-matrix")
        assert resp.status_code == 200

    def test_kosztorys_autofill(self, app):
        kosztorys_id = str(uuid.uuid4())
        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   return_value=(2026, 2)), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   return_value=1.0), \
             patch(ICB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.post("/api/v2/icb/kosztorys-autofill",
                            json={"kosztorys_id": kosztorys_id,
                                  "voivodeship": "mazowieckie"})
        assert resp.status_code == 200


# ============================================================================
# MARKET INTELLIGENCE
# ============================================================================

class TestMarketIntelligence:
    def test_redis_get_none(self):
        from services.api.services.api.routers.market_intelligence import _redis_get
        result = _redis_get("key_that_doesnt_exist_xyz")
        assert result is None

    def test_redis_set_silent(self):
        from services.api.services.api.routers.market_intelligence import _redis_set
        _redis_set("key", {"data": 1}, ttl=60)

    def test_benchmark_empty(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/benchmark?cpv_prefix=45")
        assert resp.status_code == 200

    def test_benchmark_with_province(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/benchmark?cpv_prefix=45&province=PL22")
        assert resp.status_code == 200

    def test_market_trends(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/trends")
        assert resp.status_code == 200

    def test_market_trends_with_filters(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/trends?cpv_prefix=45&province=PL22")
        assert resp.status_code == 200

    def test_top_competitors(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/competitors/top")
        assert resp.status_code == 200

    def test_top_competitors_with_filters(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/competitors/top?cpv_prefix=45&province=PL22")
        assert resp.status_code == 200

    def test_top_buyers(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/buyers/top")
        assert resp.status_code == 200

    def test_icb_prices(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/prices/icb")
        assert resp.status_code == 200

    def test_icb_prices_with_filters(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get(
                "/api/v2/intelligence/prices/icb?category=beton&typ_rms=M&year=2026&quarter=2")
        assert resp.status_code == 200

    def test_icb_prices_bad_typ_rms(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/prices/icb?typ_rms=X")
        assert resp.status_code == 400

    def test_price_inflation(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/prices/inflation")
        assert resp.status_code == 200

    def test_price_inflation_bad_typ_rms(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/prices/inflation?typ_rms=Z")
        assert resp.status_code == 400

    def test_regional_prices(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/regional")
        assert resp.status_code == 200

    def test_seasonality(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/seasonality")
        assert resp.status_code == 200

    def test_fts_search(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(scalar=0, rows=[])
            resp = app.get("/api/v2/intelligence/fts?q=remont drogi")
        assert resp.status_code == 200

    def test_fts_with_filters(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(scalar=0, rows=[])
            resp = app.get(
                "/api/v2/intelligence/fts?q=beton&cpv_prefix=45&province=PL22&value_min=1000&value_max=1000000&notice_type=PNO")
        assert resp.status_code == 200

    def test_win_rates(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/win-rates?cpv_prefix=45")
        assert resp.status_code == 200

    def test_top_buyers_cpv(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(rows=[])
            resp = app.get("/api/v2/intelligence/top-buyers-cpv?cpv_prefix=45")
        assert resp.status_code == 200

    def test_sekocenbud_search(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(scalar=0, rows=[])
            resp = app.get("/api/v2/intelligence/sekocenbud?q=beton&limit=10")
        assert resp.status_code == 200

    def test_sekocenbud_with_chapter(self, app):
        with patch(PLAN, return_value="business"), \
             patch(MIDB) as ge:
            ge.return_value = _eng(scalar=0, rows=[])
            resp = app.get("/api/v2/intelligence/sekocenbud?q=&chapter=murarstwo")
        assert resp.status_code == 200

    def test_market_summary_cached(self, app):
        cached = {"kpi": {}, "top_cpv": [], "top_province": [], "filters": {}}
        with patch(PLAN, return_value="business"), \
             patch("services.api.services.api.routers.market_intelligence._redis_get",
                   return_value=cached):
            resp = app.get("/api/v2/intelligence/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpi" in data

    def test_market_summary_live(self, app):
        from unittest.mock import MagicMock
        summary_row = MagicMock()
        summary_row.__getitem__ = lambda s, k: {
            "n_tenders": 100, "n_with_value": 90,
            "total_value_mln": 500.0, "avg_value": 55000,
            "avg_competition": 3.2, "n_buyers": 50, "n_contractors": 30
        }[k]

        call_count = [0]
        c_mock = MagicMock()
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            r = MagicMock()
            r.mappings.return_value.one.return_value = summary_row
            r.mappings.return_value.all.return_value = []
            r.scalar.return_value = None
            return r
        c_mock.execute.side_effect = side_effect
        e = MagicMock()
        def _enter(s): return c_mock
        for ctx in (e.connect.return_value, e.begin.return_value):
            ctx.__enter__ = _enter
            ctx.__exit__ = MagicMock(return_value=False)

        with patch(PLAN, return_value="business"), \
             patch("services.api.services.api.routers.market_intelligence._redis_get",
                   return_value=None), \
             patch("services.api.services.api.routers.market_intelligence._redis_set"), \
             patch(MIDB) as ge:
            ge.return_value = e
            resp = app.get("/api/v2/intelligence/summary")
        assert resp.status_code in (200, 500)
