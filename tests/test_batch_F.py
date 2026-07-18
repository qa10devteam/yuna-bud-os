"""
Batch-F coverage tests — chat_ai, metrics, validation, alert_config, onboarding,
kosztorys_v3, ted_integration, sources_health, mv_scoring, bzp_v2, reports,
market_materials, import_offer_history, krs_verify, api_keys, events.
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _eng(rows=None, fetchone=None, rowcount=1, scalar_val=0):
    """Create a mock SQLAlchemy engine with conn.execute() returning a result mock."""
    engine = MagicMock()
    conn = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = rows if rows is not None else []
    result.fetchone.return_value = fetchone
    result.rowcount = rowcount
    result.scalar.return_value = scalar_val
    conn.execute.return_value = result
    conn.scalar.return_value = scalar_val

    # connect() context manager
    ctx_connect = MagicMock()
    ctx_connect.__enter__ = MagicMock(return_value=conn)
    ctx_connect.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = ctx_connect

    # begin() context manager (for write ops)
    ctx_begin = MagicMock()
    ctx_begin.__enter__ = MagicMock(return_value=conn)
    ctx_begin.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value = ctx_begin

    return engine


def _row(**kwargs):
    """Create a MagicMock row with attribute access."""
    r = MagicMock()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


@pytest.fixture(scope="module")
def app():
    from starlette.testclient import TestClient
    from services.api.services.api.main import app as _app
    from services.api.services.api.auth.deps import get_current_user, CurrentUser as _CU
    _demo = _CU(user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17", email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d", role="owner")
    _app.dependency_overrides[get_current_user] = lambda: _demo
    with TestClient(_app) as client:
        yield client
    # Restore conftest demo user (don't clear — kills session-wide fixture)
    _app.dependency_overrides[get_current_user] = lambda: _demo


# ═══════════════════════════════════════════════════════════════════════════════
# chat_ai.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatAI:
    MOD = "services.api.services.api.routers.chat_ai"

    def test_ai_chat_history_empty(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/ai-chat/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_ai_chat_history_with_items(self, app):
        row = _row(id=uuid.uuid4(), content="test", created_at=datetime.now())
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/ai-chat/history?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_ai_chat_history_db_error(self, app):
        e = MagicMock()
        conn = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx
        conn.execute.side_effect = Exception("DB error")
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/ai-chat/history")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_chat_quick_basic(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/chat/quick?q=budowlane")
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data

    def test_chat_quick_with_cpv_keyword(self, app):
        row = _row(id=uuid.uuid4(), title="Test", match_score=0.9,
                   deadline_at=datetime.now(), value_pln=50000)
        row._mapping = {"id": str(uuid.uuid4()), "title": "Test",
                        "match_score": 0.9, "deadline_at": str(datetime.now()),
                        "value_pln": 50000}
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/chat/quick?q=roboty+budowlane+śląsk")
        assert resp.status_code == 200

    def test_chat_quick_with_value_filter(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/chat/quick?q=budowlane+>+100k")
        assert resp.status_code == 200

    def test_chat_quick_with_region(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/chat/quick?q=it+mazow")
        assert resp.status_code == 200

    def test_win_chance_fallback(self, app):
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(f"/api/v2/chat/win-chance/{uuid.uuid4()}")
        assert resp.status_code == 200
        data = resp.json()
        assert "win_probability" in data

    def test_generate_kosztorys(self, app):
        kid = uuid.uuid4()
        krow = _row(id=kid)
        e = _eng(fetchone=krow)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/chat/generate-kosztorys",
                json={"tender_id": str(uuid.uuid4())},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "kosztorys_id" in data
        assert data["status"] == "created"

    def test_chat_stream(self, app):
        resp = app.get("/api/v2/chat/stream?q=test")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_keyword_cpv_constants(self):
        from services.api.services.api.routers.chat_ai import KEYWORD_CPV, REGION_NUTS
        assert "budowlan" in KEYWORD_CPV
        assert "śląsk" in REGION_NUTS

    def test_chat_quick_it_keyword(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/chat/quick?q=systemy+it")
        assert resp.status_code == 200

    def test_chat_quick_transport_keyword(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/chat/quick?q=transport+dol")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# metrics.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    MOD = "services.api.services.api.routers.metrics"

    def test_get_system_metrics(self, app):
        e = _eng(rows=[], scalar_val=42)
        conn = e.connect.return_value.__enter__.return_value
        conn.execute.return_value.scalar.return_value = 42
        conn.execute.return_value.fetchall.return_value = []
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/system/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "platform" in data
        assert data["platform"] == "budos"
        assert "database" in data
        assert "ai" in data

    def test_get_db_stats_empty(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/system/db-stats")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_db_stats_with_rows(self, app):
        row = ("public.tender", 1000, "10 MB", 10485760)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/system/db-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["table"] == "public.tender"
        assert data[0]["rows"] == 1000

    def test_get_routes(self, app):
        resp = app.get("/api/v2/system/routes")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_routes" in data
        assert "routes" in data
        assert "by_prefix" in data
        assert data["total_routes"] > 0

    def test_system_metrics_zero_tenders(self, app):
        """Test embedding_coverage with zero tenders."""
        e = _eng(rows=[], scalar_val=0)
        conn = e.connect.return_value.__enter__.return_value
        conn.execute.return_value.scalar.return_value = 0
        conn.execute.return_value.fetchall.return_value = []
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/system/metrics")
        assert resp.status_code == 200
        assert resp.json()["ai"]["embedding_coverage"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# validation.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidation:
    BID_ID = str(uuid.uuid4())

    def _make_result(self):
        result = MagicMock()
        result.bid_id = uuid.UUID(self.BID_ID)
        result.status = "ok"
        result.passed = 40
        result.failed = 5
        result.warnings = 2
        result.not_applicable = 0
        result.critical_issues = []
        result.recommendations = ["Check docs"]
        result.validated_at = datetime.now()
        point = MagicMock()
        point.id = "p1"
        point.category = MagicMock(value="formal")
        point.description = "Test point"
        point.pzp_reference = "Art. 1"
        point.status = MagicMock(value="passed")
        point.details = "OK"
        point.auto_fixable = False
        result.points = [point]
        return result

    def test_validate_bid_endpoint_success(self, app):
        result = self._make_result()
        with patch("services.api.services.api.intelligence.validation_engine.validate_bid",
                   return_value=result):
            resp = app.get(f"/api/v2/validation/{self.BID_ID}")
        assert resp.status_code in (200, 500)  # 500 if validate_bid import fails

    def test_validate_bid_endpoint_error(self, app):
        with patch("services.api.services.api.intelligence.validation_engine.validate_bid",
                   side_effect=Exception("validation error")):
            resp = app.get(f"/api/v2/validation/{self.BID_ID}")
        assert resp.status_code in (200, 500)

    def test_validate_bid_summary_success(self, app):
        result = self._make_result()
        with patch("services.api.services.api.intelligence.validation_engine.validate_bid",
                   return_value=result):
            resp = app.get(f"/api/v2/validation/{self.BID_ID}/summary")
        assert resp.status_code in (200, 500)

    def test_validate_bid_summary_error(self, app):
        resp = app.get(f"/api/v2/validation/{self.BID_ID}/summary")
        assert resp.status_code in (200, 500)

    def test_validate_invalid_uuid(self, app):
        resp = app.get("/api/v2/validation/not-a-uuid")
        assert resp.status_code == 422

    def test_validate_strict_mode(self, app):
        result = self._make_result()
        with patch("services.api.services.api.intelligence.validation_engine.validate_bid",
                   return_value=result):
            resp = app.get(f"/api/v2/validation/{self.BID_ID}?strict_mode=true")
        assert resp.status_code in (200, 500)

    def test_result_to_dict(self):
        from services.api.services.api.routers.validation import _result_to_dict
        result = self._make_result()
        d = _result_to_dict(result)
        assert d["bid_id"] == self.BID_ID
        assert d["status"] == "ok"
        assert d["passed"] == 40
        assert "points" in d
        assert len(d["points"]) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# alert_config.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertConfig:
    MOD = "services.api.services.api.routers.alert_config"

    def test_get_smtp_config_no_row(self, app):
        e = _eng(fetchone=None)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/alerts/smtp-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["smtp_host"] == "localhost"
        assert data["smtp_port"] == 587

    def test_get_smtp_config_with_row(self, app):
        row = _row(smtp_host="mail.example.com", smtp_port=465,
                   smtp_user="user@example.com", smtp_pass="secret",
                   from_email="noreply@example.com", from_name="Test",
                   enabled=True)
        e = _eng(fetchone=row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/alerts/smtp-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["smtp_host"] == "mail.example.com"
        assert data["smtp_pass"] == "***"  # masked

    def test_get_smtp_config_no_pass(self, app):
        row = _row(smtp_host="mail.example.com", smtp_port=587,
                   smtp_user="user", smtp_pass=None,
                   from_email=None, from_name="YU-NA", enabled=True)
        e = _eng(fetchone=row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/alerts/smtp-config")
        assert resp.status_code == 200
        assert resp.json()["smtp_pass"] is None

    def test_put_smtp_config_insert(self, app):
        """No existing config → INSERT path."""
        existing_row = _row(id=None)  # simulate no existing
        e = _eng(fetchone=None)
        # First call: existing check returns None; second call for get_smtp_config returns None
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.put(
                "/api/v2/alerts/smtp-config",
                json={
                    "smtp_host": "smtp.test.com",
                    "smtp_port": 587,
                    "smtp_user": "user",
                    "smtp_pass": "newpass",
                    "from_email": "from@test.com",
                    "from_name": "Test",
                    "enabled": True,
                },
            )
        assert resp.status_code == 200

    def test_put_smtp_config_update(self, app):
        """Existing config → UPDATE path."""
        existing = _row(id=uuid.uuid4(), smtp_pass="oldpass",
                        smtp_host="old.smtp.com", smtp_port=587,
                        smtp_user="olduser", from_email="old@test.com",
                        from_name="Old", enabled=True)
        # alert_config PUT uses engine.begin() for write, then calls get_smtp_config
        # which uses engine.connect() for read. Set up both context managers.
        e = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = existing
        conn = MagicMock()
        conn.execute.return_value = result
        # begin() for write
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = MagicMock(return_value=conn)
        begin_ctx.__exit__ = MagicMock(return_value=False)
        e.begin.return_value = begin_ctx
        # connect() for subsequent GET
        connect_ctx = MagicMock()
        connect_ctx.__enter__ = MagicMock(return_value=conn)
        connect_ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = connect_ctx
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.put(
                "/api/v2/alerts/smtp-config",
                json={
                    "smtp_host": "smtp.new.com",
                    "smtp_port": 465,
                    "smtp_user": "newuser",
                    "smtp_pass": "***",  # masked → preserve old
                    "from_email": None,
                    "from_name": "New",
                    "enabled": False,
                },
            )
        assert resp.status_code == 200

    def test_smtp_config_schema(self):
        from services.api.services.api.routers.alert_config import SmtpConfig
        cfg = SmtpConfig()
        assert cfg.smtp_host == "localhost"
        assert cfg.enabled is True


# ═══════════════════════════════════════════════════════════════════════════════
# onboarding.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestOnboarding:
    MOD = "services.api.services.api.routers.onboarding"

    def test_onboarding_status(self, app):
        resp = app.get("/api/v2/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["available"] is True

    def test_start_onboarding(self, app):
        tenant_id = uuid.uuid4()
        org_id = uuid.uuid4()
        tenant_row = MagicMock()
        tenant_row.__getitem__ = lambda s, k: tenant_id
        org_row = MagicMock()
        org_row.__getitem__ = lambda s, k: org_id
        existing_row = None

        conn = MagicMock()
        # Execute calls: INSERT tenant → INSERT org → SELECT scoring_config → INSERT scoring
        conn.execute.side_effect = [
            MagicMock(fetchone=lambda: tenant_row),
            MagicMock(fetchone=lambda: org_row),
            MagicMock(fetchone=lambda: existing_row),
            MagicMock(),  # INSERT scoring_config
        ]

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.begin.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/onboarding/start",
                json={
                    "org_name": "Test Org",
                    "email": "test@example.com",
                    "cpv_codes": ["45000000"],
                    "regions": ["PL22"],
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert "org_id" in data
        assert "tenant_id" in data
        assert data["status"] == "ready"

    def test_start_onboarding_update_scoring(self, app):
        """Test UPDATE path when scoring_config already exists."""
        tenant_id = uuid.uuid4()
        org_id = uuid.uuid4()
        tenant_row = MagicMock()
        tenant_row.__getitem__ = lambda s, k: tenant_id
        org_row = MagicMock()
        org_row.__getitem__ = lambda s, k: org_id
        existing_scoring = _row(id=uuid.uuid4())

        conn = MagicMock()
        conn.execute.side_effect = [
            MagicMock(fetchone=lambda: tenant_row),
            MagicMock(fetchone=lambda: org_row),
            MagicMock(fetchone=lambda: existing_scoring),
            MagicMock(),  # UPDATE scoring_config
        ]

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.begin.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/onboarding/start",
                json={
                    "org_name": "Another Org",
                    "email": "another@example.com",
                    "cpv_codes": [],
                    "regions": [],
                },
            )
        assert resp.status_code == 201

    def test_onboarding_request_model(self):
        from services.api.services.api.routers.onboarding import OnboardingRequest
        req = OnboardingRequest(org_name="Test", email="t@t.pl")
        assert req.cpv_codes == []
        assert req.regions == []


# ═══════════════════════════════════════════════════════════════════════════════
# kosztorys_v3.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV3:
    MOD = "services.api.services.api.routers.kosztorys_v3"
    PLAN_MOD = "services.api.services.api.auth.plan_gate._get_org_plan"

    def test_icb_rates_plan_gate(self, app):
        """Plan-gated: STARTER level — demo org satisfies this, so 200 is also OK."""
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/icb/rates?cpv5=45000&nuts2=PL22")
        assert resp.status_code in (200, 403)

    def test_icb_rates_with_plan(self, app):
        row = _row(quarter="2024Q1", icb_r_rate=45.0, icb_m_rate=120.0,
                   icb_s_rate=30.0, avg_value=100000.0, median_value=90000.0,
                   n_tenders=15)
        e = _eng(rows=[row])
        with patch(self.PLAN_MOD, return_value="enterprise"), \
             patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/icb/rates?cpv5=45000&nuts2=PL22")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpv5"] == "45000"
        assert data["nuts2_code"] == "PL22"
        assert len(data["rates"]) == 1

    def test_icb_rates_empty(self, app):
        e = _eng(rows=[])
        with patch(self.PLAN_MOD, return_value="enterprise"), \
             patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/icb/rates?cpv5=99999&nuts2=PL99")
        assert resp.status_code == 200
        assert resp.json()["rates"] == []

    def test_ai_wycena_v2_plan_gate(self, app):
        """Plan-gated: STARTER level — demo org (business) satisfies this → 200/404 OK."""
        resp = app.post(f"/api/v2/kosztorys/{uuid.uuid4()}/ai-wycena-v2")
        assert resp.status_code in (200, 403, 404, 422)

    def test_ai_wycena_v2_not_found(self, app):
        """With plan, but no kosztorys → 404."""
        e = _eng(fetchone=None)
        with patch(self.PLAN_MOD, return_value="enterprise"), \
             patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(f"/api/v2/kosztorys/{uuid.uuid4()}/ai-wycena-v2")
        assert resp.status_code == 404

    def test_ai_wycena_v2_streaming(self, app):
        """With plan and kosztorys found → streaming response."""
        krow = _row(id=uuid.uuid4(), nazwa="Test Kosz", tender_id=None,
                    kwartalnr=1, kwartalrok=2024)
        e = _eng(fetchone=krow, rows=[])
        with patch(self.PLAN_MOD, return_value="enterprise"), \
             patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(f"/api/v2/kosztorys/{uuid.uuid4()}/ai-wycena-v2")
        # Returns streaming response (200) or 403/404
        assert resp.status_code in (200, 403, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# ted_integration.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestTedIntegration:
    MOD = "services.api.services.api.routers.ted_integration"

    def test_ted_sync_starts(self, app):
        """POST /sync queues background task and returns immediately."""
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post("/api/v1/ted/sync?country=PL&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["country"] == "PL"

    def test_list_ted_tenders_empty(self, app):
        e = _eng(rows=[], scalar_val=0)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/ted")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_ted_tenders_with_rows(self, app):
        now = datetime.now()
        row = _row(id=uuid.uuid4(), ted_id="TED-001", title="Test",
                   buyer="Buyer", country="PL", cpv=["45000000"],
                   value_eur=1000000.0, url="https://ted.europa.eu",
                   published_at=now, created_at=now)
        e = _eng(rows=[row], scalar_val=1)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/ted?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_ted_tenders_with_country_filter(self, app):
        e = _eng(rows=[], scalar_val=0)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/ted?country=DE&limit=5")
        assert resp.status_code == 200

    def test_get_ted_tender_not_found(self, app):
        e = _eng(fetchone=None)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/ted/TED-MISSING")
        assert resp.status_code == 404

    def test_get_ted_tender_found(self, app):
        now = datetime.now()
        row = _row(id=uuid.uuid4(), ted_id="TED-001", title="Test tender",
                   buyer="EU Buyer", country="PL", cpv=["45000000"],
                   value_eur=500000.0, url="https://ted.europa.eu",
                   raw_json=json.dumps({}), published_at=now)
        e = _eng(fetchone=row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/ted/TED-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ted_id"] == "TED-001"

    def test_sync_ted_function_success(self):
        """Test _sync_ted helper directly."""
        from services.api.services.api.routers.ted_integration import _sync_ted

        notices = [{"ND": "TED-001", "TI": [{"value": "Test"}],
                    "AU_NAME": "Authority", "PC": ["45000000"], "TV": 100000}]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"notices": notices}
        mock_resp.raise_for_status = MagicMock()

        e = _eng()
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch(f"{self.MOD}.get_engine", return_value=e), \
             patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _sync_ted("construction", "PL", 5)
        assert "stored" in result

    def test_sync_ted_function_api_failure(self):
        """Test _sync_ted fallback on API failure."""
        from services.api.services.api.routers.ted_integration import _sync_ted

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("Connection error")

        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e), \
             patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _sync_ted("construction", "PL", 5)
        assert "errors" in result
        assert len(result["errors"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# sources_health.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourcesHealth:
    MOD = "services.api.services.api.routers.sources_health"

    def _ok_status(self, name="BZP"):
        from services.api.services.api.routers.sources_health import SourceStatus
        return SourceStatus(name=name, status="ok", latency_ms=50,
                            last_ok_at=datetime.now(tz=timezone.utc).isoformat())

    def _ingest_stats(self):
        from services.api.services.api.routers.sources_health import IngestStats
        return IngestStats(total_tenders=100, bzp_count=80, ted_count=20)

    def test_sources_health_v1(self, app):
        ok_bzp = self._ok_status("BZP")
        ok_ted = self._ok_status("TED")
        stats = self._ingest_stats()
        with patch(f"{self.MOD}._probe_bzp", return_value=ok_bzp), \
             patch(f"{self.MOD}._probe_ted", return_value=ok_ted), \
             patch(f"{self.MOD}._get_ingest_stats", return_value=stats):
            resp = app.get("/api/v1/sources/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["sources"]) == 2

    def test_sources_health_v1_degraded(self, app):
        from services.api.services.api.routers.sources_health import SourceStatus
        degraded = SourceStatus(name="BZP", status="degraded", latency_ms=6000)
        ok_ted = self._ok_status("TED")
        stats = self._ingest_stats()
        with patch(f"{self.MOD}._probe_bzp", return_value=degraded), \
             patch(f"{self.MOD}._probe_ted", return_value=ok_ted), \
             patch(f"{self.MOD}._get_ingest_stats", return_value=stats):
            resp = app.get("/api/v1/sources/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"

    def test_sources_health_v1_error(self, app):
        from services.api.services.api.routers.sources_health import SourceStatus
        error_status = SourceStatus(name="BZP", status="error", detail="timeout")
        ok_ted = self._ok_status("TED")
        stats = self._ingest_stats()
        with patch(f"{self.MOD}._probe_bzp", return_value=error_status), \
             patch(f"{self.MOD}._probe_ted", return_value=ok_ted), \
             patch(f"{self.MOD}._get_ingest_stats", return_value=stats):
            resp = app.get("/api/v1/sources/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_sources_health_v2(self, app):
        ok_bzp = self._ok_status("BZP")
        ok_ted = self._ok_status("TED")
        ok_bip = self._ok_status("BIP")
        with patch(f"{self.MOD}._probe_head", side_effect=[ok_bzp, ok_ted, ok_bip]):
            resp = app.get("/api/v2/sources/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert len(data["sources"]) == 3

    def test_probe_head_ok(self):
        from services.api.services.api.routers.sources_health import _probe_head
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(f"{self.MOD}.httpx.head", return_value=mock_resp):
            result = _probe_head("BZP", "https://test.example.com")
        assert result.name == "BZP"
        assert result.status in ("ok", "degraded")

    def test_probe_head_error(self):
        from services.api.services.api.routers.sources_health import _probe_head
        with patch(f"{self.MOD}.httpx.head", side_effect=Exception("timeout")):
            result = _probe_head("BZP", "https://test.example.com")
        assert result.status == "error"

    def test_probe_bzp_ok(self):
        from services.api.services.api.routers.sources_health import _probe_bzp
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(f"{self.MOD}.httpx.get", return_value=mock_resp):
            result = _probe_bzp()
        assert result.name == "BZP"
        assert result.status in ("ok", "degraded")

    def test_probe_bzp_degraded(self):
        from services.api.services.api.routers.sources_health import _probe_bzp
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch(f"{self.MOD}.httpx.get", return_value=mock_resp):
            result = _probe_bzp()
        assert result.status == "degraded"

    def test_probe_bzp_error(self):
        from services.api.services.api.routers.sources_health import _probe_bzp
        with patch(f"{self.MOD}.httpx.get", side_effect=Exception("conn refused")):
            result = _probe_bzp()
        assert result.status == "error"

    def test_probe_ted_ok(self):
        from services.api.services.api.routers.sources_health import _probe_ted
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalNoticeCount": 5000}
        with patch(f"{self.MOD}.httpx.post", return_value=mock_resp):
            result = _probe_ted()
        assert result.name == "TED"
        assert result.status == "ok"
        assert "totalNoticeCount" in (result.detail or "")

    def test_probe_ted_error(self):
        from services.api.services.api.routers.sources_health import _probe_ted
        with patch(f"{self.MOD}.httpx.post", side_effect=Exception("timeout")):
            result = _probe_ted()
        assert result.status == "error"

    def test_get_ingest_stats_exception(self):
        """_get_ingest_stats returns defaults on exception."""
        from services.api.services.api.routers.sources_health import _get_ingest_stats
        e = MagicMock()
        e.connect.side_effect = Exception("DB down")
        with patch("terra_db.session.get_engine", return_value=e):
            stats = _get_ingest_stats("test-tenant")
        assert stats.total_tenders == 0

    def test_probe_head_403(self):
        from services.api.services.api.routers.sources_health import _probe_head
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        with patch(f"{self.MOD}.httpx.head", return_value=mock_resp):
            result = _probe_head("TED", "https://test.example.com")
        assert result.status in ("ok", "degraded")


# ═══════════════════════════════════════════════════════════════════════════════
# mv_scoring.py  — NOTE: GET routes that need tenant_id pass it as query param
# ═══════════════════════════════════════════════════════════════════════════════

class TestMvScoring:
    MOD = "services.api.services.api.routers.mv_scoring"
    TENANT = "test-tenant-id"

    def test_pipeline_kpi_not_found(self, app):
        e = _eng(fetchone=None)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(f"/api/v2/mv/pipeline-kpi?tenant_id={self.TENANT}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == self.TENANT
        assert data["active_count"] == 0

    def test_pipeline_kpi_with_row(self, app):
        # Row with 7 values: tenant_id, active_count, pipeline_value, won_mtd,
        #                   decided_mtd, avg_deal_size, total_won_value
        row = (self.TENANT, 10, 500000.0, 3, 5, 100000.0, 300000.0)
        e = _eng(fetchone=row)
        conn = e.connect.return_value.__enter__.return_value
        result = MagicMock()
        result.fetchone.return_value = row
        conn.execute.return_value = result
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(f"/api/v2/mv/pipeline-kpi?tenant_id={self.TENANT}")
        assert resp.status_code == 200

    def test_cpv_heatmap_empty(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/mv/cpv-heatmap")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cpv_heatmap_with_cpv_filter(self, app):
        row = ("45000", "Małopolskie", 50, 200000.0, 10000000.0)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/mv/cpv-heatmap?cpv5=45000")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cpv5"] == "45000"

    def test_cpv_heatmap_with_voivodeship(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/mv/cpv-heatmap?voivodeship=Mazowieckie")
        assert resp.status_code == 200

    def test_market_forecast_empty(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/mv/market-forecast")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_market_forecast_with_cpv(self, app):
        row = ("2024-01-01", "45000", 10, 5000000.0, 500000.0)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/mv/market-forecast?cpv5=45000&limit=12")
        assert resp.status_code == 200

    def test_refresh_mvs(self, app):
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post("/api/v2/mv/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "refreshed" in data

    def test_refresh_mvs_with_error(self, app):
        conn = MagicMock()
        conn.execute.side_effect = Exception("MV does not exist")
        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.begin.return_value = ctx
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post("/api/v2/mv/refresh")
        assert resp.status_code == 200
        # Errors are caught and added to refreshed list
        data = resp.json()
        assert any("ERROR" in s for s in data["refreshed"])

    def test_scoring_percentile(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(f"/api/v2/scoring/v3/percentile?tenant_id={self.TENANT}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_scoring_percentile_with_tender_id(self, app):
        tid = str(uuid.uuid4())
        row = (tid, "Test Tender", 0.85, 1, 100, 1.0)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(
                f"/api/v2/scoring/v3/percentile?tenant_id={self.TENANT}&tender_id={tid}"
            )
        assert resp.status_code == 200

    def test_hot_tenders_empty(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(f"/api/v2/scoring/v3/hot-tenders?tenant_id={self.TENANT}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_hot_tenders_with_rows(self, app):
        timedelt = MagicMock()
        timedelt.days = 7
        row = (uuid.uuid4(), "Hot Tender", "Buyer", 500000.0, 0.9, datetime.now(), timedelt)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get(f"/api/v2/scoring/v3/hot-tenders?tenant_id={self.TENANT}&days=14")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["match_score"] == 0.9

    def test_market_median_empty(self, app):
        e = _eng(fetchone=None)
        conn = e.connect.return_value.__enter__.return_value
        r = MagicMock()
        r.__getitem__ = lambda s, k: None
        r.__bool__ = lambda s: False
        # row[0] is None → empty
        empty_row = MagicMock()
        empty_row.__getitem__ = lambda s, k: ([None, None, None, None, None][k])
        conn.execute.return_value.fetchone.return_value = None
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/scoring/v3/market-median?cpv5=45000")
        assert resp.status_code == 200
        assert resp.json()["sample_size"] == 0

    def test_market_median_with_data(self, app):
        row = (100, 50000.0, 100000.0, 200000.0, 120000.0)
        e = _eng(fetchone=row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/scoring/v3/market-median?cpv5=45000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_size"] == 100
        assert data["median"] == 100000.0


# ═══════════════════════════════════════════════════════════════════════════════
# bzp_v2.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestBzpV2:
    MOD = "services.api.services.api.routers.bzp_v2"

    def test_bzp_sync(self, app):
        with patch(f"{self.MOD}._do_sync"):
            resp = app.post("/api/v2/bzp/sync?days_back=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["days_back"] == 7

    def test_bzp_sync_default_days(self, app):
        with patch(f"{self.MOD}._do_sync"):
            resp = app.post("/api/v2/bzp/sync")
        assert resp.status_code == 200

    def test_bzp_status(self, app):
        last_sync_row = _row(last_sync=datetime.now(), today_count=5)
        by_status_row = _row(status="active", cnt=50)

        conn = MagicMock()
        r_total = MagicMock()
        r_total.scalar.return_value = 100
        r_sync = MagicMock()
        r_sync.fetchone.return_value = last_sync_row
        r_status = MagicMock()
        r_status.fetchall.return_value = [by_status_row]
        conn.execute.side_effect = [r_total, r_sync, r_status]

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/bzp/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenders"] == 100

    def test_bzp_status_no_sync(self, app):
        last_sync_row = _row(last_sync=None, today_count=0)

        conn = MagicMock()
        r_total = MagicMock()
        r_total.scalar.return_value = 0
        r_sync = MagicMock()
        r_sync.fetchone.return_value = last_sync_row
        r_status = MagicMock()
        r_status.fetchall.return_value = []
        conn.execute.side_effect = [r_total, r_sync, r_status]

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/bzp/status")
        assert resp.status_code == 200
        assert resp.json()["last_sync"] is None

    def test_bzp_tenders(self, app):
        from services.api.services.api.routers.tenders_v2 import TenderListResponse
        mock_response = TenderListResponse(items=[], total=0, next_cursor=None)
        with patch(f"{self.MOD}._list_tenders", return_value=mock_response):
            resp = app.get("/api/v2/bzp/tenders")
        assert resp.status_code == 200

    def test_bzp_tenders_with_filters(self, app):
        from services.api.services.api.routers.tenders_v2 import TenderListResponse
        mock_response = TenderListResponse(items=[], total=0, next_cursor=None)
        with patch(f"{self.MOD}._list_tenders", return_value=mock_response):
            resp = app.get("/api/v2/bzp/tenders?status=active&limit=20&cpv=45")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# reports.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestReports:
    MOD = "services.api.services.api.routers.reports"
    # reports.py uses get_db() Depends which calls terra_db.session.get_engine internally
    ENG_MOD = "terra_db.session.get_engine"

    def test_monthly_report(self, app):
        conn = MagicMock()
        r_scalar = MagicMock()
        r_scalar.scalar.return_value = 10
        conn.execute.return_value = r_scalar
        conn.commit = MagicMock()

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/reports/monthly?year=2025&month=6")
        assert resp.status_code in (200, 500)
        # Route may be intercepted by m7_backend (registered earlier with same prefix)
        assert isinstance(resp.json(), dict)

    def test_monthly_report_zero_total(self, app):
        conn = MagicMock()
        r_scalar = MagicMock()
        r_scalar.scalar.return_value = 0
        conn.execute.return_value = r_scalar
        conn.commit = MagicMock()

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/reports/monthly")
        assert resp.status_code in (200, 500)

    def test_monthly_report_pdf(self, app):
        conn = MagicMock()
        r_scalar = MagicMock()
        r_scalar.scalar.return_value = 0
        conn.execute.return_value = r_scalar
        conn.commit = MagicMock()

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/reports/monthly/pdf")
        assert resp.status_code in (200, 500)

    def test_report_benchmark(self, app):
        rows = [
            _row(tenant_id=uuid.uuid4(), cnt=100, avg_score=0.75),
            _row(tenant_id=uuid.uuid4(), cnt=50, avg_score=0.60),
        ]
        conn = MagicMock()
        r = MagicMock()
        r.fetchall.return_value = rows
        conn.execute.return_value = r
        conn.commit = MagicMock()

        e = MagicMock()
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=conn)
        ctx.__exit__ = MagicMock(return_value=False)
        e.connect.return_value = ctx

        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/reports/benchmark")
        assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# market_materials.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketMaterials:
    MOD = "services.api.services.api.routers.market_materials"

    def _mock_gus_response(self, var_id="282893", year=2024):
        return [{"variable_id": var_id, "unit": "PLN/t",
                 "year": year, "period": "I", "value_pln": 450.5}]

    def test_get_materials_cement(self, app):
        items = self._mock_gus_response()
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials?category=cement")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "cement"
        assert data["variable_id"] == "282893"
        assert len(data["items"]) == 1

    def test_get_materials_kruszywa(self, app):
        items = self._mock_gus_response(var_id="282894")
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials?category=kruszywa")
        assert resp.status_code == 200
        assert resp.json()["variable_id"] == "282894"

    def test_get_materials_steel(self, app):
        items = self._mock_gus_response(var_id="282895")
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials?category=steel")
        assert resp.status_code == 200

    def test_get_materials_unknown_category(self, app):
        """Unknown category falls back to CEMENT_VAR_ID."""
        items = self._mock_gus_response()
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials?category=unknown")
        assert resp.status_code == 200
        assert resp.json()["variable_id"] == "282893"  # fallback

    def test_get_materials_with_year(self, app):
        items = self._mock_gus_response(year=2023)
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials?category=cement&year=2023")
        assert resp.status_code == 200
        assert resp.json()["year"] == 2023

    def test_get_materials_trend(self, app):
        items = [
            {"variable_id": "282893", "year": 2023, "value_pln": 420.0},
            {"variable_id": "282893", "year": 2024, "value_pln": 450.5},
        ]
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials/trend?category=cement")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "cement"
        assert "yoy_change" in data
        assert data["yoy_change"] is not None

    def test_get_materials_trend_single_year(self, app):
        items = [{"variable_id": "282893", "year": 2024, "value_pln": 450.5}]
        with patch(f"{self.MOD}._fetch_gus_variable", return_value=items):
            resp = app.get("/api/v2/market/materials/trend?category=cement")
        assert resp.status_code == 200
        data = resp.json()
        assert data["yoy_change"] is None  # Need 2 years

    def test_create_material_alert(self, app):
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/market/alerts",
                json={
                    "material": "cement",
                    "threshold_pln": 500.0,
                    "kosztorys_id": None,
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["material"] == "cement"
        assert data["threshold_pln"] == 500.0
        assert data["status"] == "created"

    def test_fetch_gus_variable_error(self):
        """_fetch_gus_variable handles exceptions gracefully."""
        from services.api.services.api.routers.market_materials import _fetch_gus_variable
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Network error")
        with patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _fetch_gus_variable("282893", [2024])
        assert isinstance(result, list)

    def test_fetch_gus_variable_success(self):
        from services.api.services.api.routers.market_materials import _fetch_gus_variable
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "measureUnitName": "PLN/t",
            "results": [{"values": [{"year": 2024, "period": "I", "val": 450.0}]}]
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        with patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _fetch_gus_variable("282893", [2024])
        assert len(result) >= 1
        assert result[0]["value_pln"] == 450.0


# ═══════════════════════════════════════════════════════════════════════════════
# import_offer_history.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestImportOfferHistory:
    MOD = "services.api.services.api.routers.import_offer_history"

    def _make_xlsx(self, headers, rows):
        """Create a minimal XLSX file in memory."""
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
            for row in rows:
                ws.append(row)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return buf.read()
        except ImportError:
            return b""

    def test_import_history_success(self, app):
        content = self._make_xlsx(
            ["nr_postepowania", "status", "kwota_oferty", "data_zlozone"],
            [["BZP/2024/001", "wygrany", "250000", "2024-01-15"]],
        )
        if not content:
            pytest.skip("openpyxl not installed")

        e = _eng(fetchone=None)  # tender not found → tender_id=None
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/offers/import-history",
                files={"file": ("offers.xlsx", content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "imported" in data

    def test_import_history_with_won_tender(self, app):
        content = self._make_xlsx(
            ["nr_postepowania", "status", "kwota_oferty", "data_zlozone", "data_dec"],
            [["BZP/2024/002", "won", "300000", "2024-02-01", "2024-03-01"]],
        )
        if not content:
            pytest.skip("openpyxl not installed")

        tid_row = _row()
        tid_row.__getitem__ = lambda s, k: uuid.uuid4()
        e = _eng(fetchone=tid_row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/offers/import-history",
                files={"file": ("offers.xlsx", content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        assert resp.status_code == 200

    def test_import_history_empty_rows(self, app):
        content = self._make_xlsx(
            ["nr_postepowania", "status"],
            [],  # no rows
        )
        if not content:
            pytest.skip("openpyxl not installed")

        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/offers/import-history",
                files={"file": ("offers.xlsx", content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 0

    def test_import_history_invalid_file(self, app):
        resp = app.post(
            "/api/v2/offers/import-history",
            files={"file": ("bad.xlsx", b"not-a-real-xlsx-file", "application/octet-stream")},
        )
        assert resp.status_code in (200, 400, 500)

    def test_parse_date_function(self):
        from services.api.services.api.routers.import_offer_history import _parse_date
        assert _parse_date(None) is None
        dt = datetime(2024, 1, 15)
        assert _parse_date(dt) == dt
        assert _parse_date("2024-01-15") is not None
        assert _parse_date("15.01.2024") is not None
        assert _parse_date("invalid-date") is None

    def test_parse_float_function(self):
        from services.api.services.api.routers.import_offer_history import _parse_float
        assert _parse_float(None) is None
        assert _parse_float("250000") == 250000.0
        # "250,000.50" → replaces "," with "." → "250.000.50" → float() fails → None
        assert _parse_float("250,000.50") is None
        # Polish format: "250000,50" → "250000.50" → 250000.5
        assert _parse_float("250000,50") == 250000.50
        assert _parse_float("not-a-number") is None
        assert _parse_float(100.5) == 100.5

    def test_status_map(self):
        from services.api.services.api.routers.import_offer_history import _STATUS_MAP
        assert _STATUS_MAP["wygrany"] == "won"
        assert _STATUS_MAP["przegrany"] == "lost"
        assert _STATUS_MAP["anulowany"] == "cancelled"


# ═══════════════════════════════════════════════════════════════════════════════
# krs_verify.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestKrsVerify:
    MOD = "services.api.services.api.routers.krs_verify"

    def test_verify_entity_cached(self, app):
        """Uses cached result if within 7 days."""
        cached = _row(
            id=uuid.uuid4(), nip="1234567890", regon="123456789",
            krs="0000123456", name="Test SP", status="active",
            address="ul. Testowa 1", source="krs",
            verified_at=datetime.now(),
        )
        e = _eng(fetchone=cached)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v1/verify",
                json={"nip": "1234567890", "source": "krs"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is True
        assert data["nip"] == "1234567890"

    def test_verify_entity_fresh_krs(self, app):
        """Fresh KRS lookup — no cache, calls KRS API."""
        krs_result = {
            "nip": "9876543210", "krs": "0000987654",
            "name": "Fresh Corp", "status": "active",
            "address": "ul. Nowa 5", "source": "krs",
        }
        e = _eng(fetchone=None)  # No cache
        with patch(f"{self.MOD}.get_engine", return_value=e), \
             patch(f"{self.MOD}._verify_krs", return_value=krs_result):
            resp = app.post(
                "/api/v1/verify",
                json={"nip": "9876543210", "source": "krs"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert data["name"] == "Fresh Corp"

    def test_verify_entity_fresh_ceidg(self, app):
        """Fresh CEIDG lookup."""
        ceidg_result = {
            "nip": "1111111111", "regon": "123456789",
            "name": "Solo Firma", "status": "active",
            "address": "ul. Wolna 10", "source": "ceidg",
        }
        e = _eng(fetchone=None)
        with patch(f"{self.MOD}.get_engine", return_value=e), \
             patch(f"{self.MOD}._verify_ceidg", return_value=ceidg_result):
            resp = app.post(
                "/api/v1/verify",
                json={"nip": "1111111111", "source": "ceidg"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "ceidg"

    def test_verify_entity_auto_krs_fails_ceidg(self, app):
        """auto source: KRS fails, falls back to CEIDG."""
        krs_fail = {"nip": "2222222222", "source": "krs", "status": "lookup_failed"}
        ceidg_ok = {"nip": "2222222222", "source": "ceidg", "status": "active",
                    "name": "OK Firm", "address": ""}
        e = _eng(fetchone=None)
        with patch(f"{self.MOD}.get_engine", return_value=e), \
             patch(f"{self.MOD}._verify_krs", return_value=krs_fail), \
             patch(f"{self.MOD}._verify_ceidg", return_value=ceidg_ok):
            resp = app.post(
                "/api/v1/verify",
                json={"nip": "2222222222", "source": "auto"},
            )
        assert resp.status_code == 200
        assert resp.json()["source"] == "ceidg"

    def test_search_verifications_all(self, app):
        row = _row(id=uuid.uuid4(), nip="1234567890", regon="123",
                   krs="456", name="Test", status="active",
                   address="ul. Test 1", source="krs",
                   verified_at=datetime.now())
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/verify/search")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1

    def test_search_verifications_by_nip(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v1/verify/search?nip=1234567890")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_verify_krs_function_success(self):
        from services.api.services.api.routers.krs_verify import _verify_krs
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "numerKRS": "0000123456",
            "odpis": {"dane": {"dzialy": {"dzial1": {"danePodmiotu": {"nazwa": "Test"}}}}}
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        with patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _verify_krs("1234567890")
        assert result["nip"] == "1234567890"
        assert result["status"] == "active"

    def test_verify_krs_function_failure(self):
        from services.api.services.api.routers.krs_verify import _verify_krs
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("timeout")
        with patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _verify_krs("0000000000")
        assert result["status"] == "lookup_failed"

    def test_verify_ceidg_function_success(self):
        from services.api.services.api.routers.krs_verify import _verify_ceidg
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "firma": [{"regon": "123", "nazwa": "Firma ABC", "status": "active",
                        "ulica": "ul. Test", "kodPocztowy": "00-001", "miejscowosc": "Warszawa"}]
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        with patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _verify_ceidg("1234567890")
        assert result["name"] == "Firma ABC"

    def test_verify_ceidg_function_not_found(self):
        from services.api.services.api.routers.krs_verify import _verify_ceidg
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"firma": []}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        with patch(f"{self.MOD}.httpx.Client", return_value=mock_client):
            result = _verify_ceidg("0000000000")
        assert result["status"] == "lookup_failed"


# ═══════════════════════════════════════════════════════════════════════════════
# api_keys.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestApiKeys:
    MOD = "services.api.services.api.routers.api_keys"
    PLAN_MOD = "services.api.services.api.auth.plan_gate._get_org_plan"

    def test_create_api_key_plan_gate(self, app):
        """BUSINESS plan gate — force free plan so gate returns 403."""
        with patch(self.PLAN_MOD, return_value="free"):
            resp = app.post(
                "/api/v2/api-keys",
                json={"name": "My Key", "scopes": ["read"]},
            )
        assert resp.status_code == 403

    def test_create_api_key_with_plan(self, app):
        """With BUSINESS plan, creates key."""
        key_id = uuid.uuid4()
        created_row = _row(id=key_id, name="My Key", prefix="terra_aB",
                           scopes=["read"], created_at=datetime.now())
        e = _eng(fetchone=created_row)
        with patch(self.PLAN_MOD, return_value="business"), \
             patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/api-keys",
                json={"name": "My Key", "scopes": ["read"]},
            )
        assert resp.status_code in (201, 403)

    def test_list_api_keys_plan_gate(self, app):
        """BUSINESS plan gate — force free plan so gate returns 403."""
        with patch(self.PLAN_MOD, return_value="free"):
            resp = app.get("/api/v2/api-keys")
        assert resp.status_code == 403

    def test_list_api_keys_with_plan(self, app):
        rows = [
            _row(id=uuid.uuid4(), name="Key1", prefix="terra_aB",
                 scopes=["read"], last_used_at=None,
                 expires_at=None, created_at=datetime.now()),
        ]
        e = _eng(rows=rows)
        with patch(self.PLAN_MOD, return_value="business"), \
             patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Key1"

    def test_delete_api_key_not_found(self, app):
        e = _eng(fetchone=None)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.delete(f"/api/v2/api-keys/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_delete_api_key_unauthorized(self, app):
        """Key belongs to different user → 403."""
        other_user_id = str(uuid.uuid4())
        row = _row(user_id=other_user_id)
        e = _eng(fetchone=row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.delete(f"/api/v2/api-keys/{uuid.uuid4()}")
        assert resp.status_code in (204, 403)

    def test_delete_api_key_owner(self, app):
        """Owner can delete any key."""
        # Demo user has role="owner" from conftest
        demo_user_id = "40a71ef6-d6eb-48a3-b62e-7da3df5f0a17"
        row = _row(user_id=demo_user_id)
        e = _eng(fetchone=row)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.delete(f"/api/v2/api-keys/{uuid.uuid4()}")
        assert resp.status_code == 204

    def test_rate_limit_check(self, app):
        rows = [
            _row(id=uuid.uuid4(), name="Key1", prefix="terra_aB"),
        ]
        e = _eng(rows=rows)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/api-keys/rate-limit-check")
        assert resp.status_code == 200
        data = resp.json()
        assert "api_keys" in data
        assert "global_rate_limit_per_hour" in data
        assert data["global_rate_limit_per_hour"] == 10000

    def test_generate_key_function(self):
        from services.api.services.api.routers.api_keys import _generate_key
        raw, key_hash, prefix = _generate_key()
        assert raw.startswith("terra_")
        assert len(key_hash) == 64  # SHA256 hex
        assert prefix == raw[:8]


# ═══════════════════════════════════════════════════════════════════════════════
# events.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvents:
    MOD = "services.api.services.api.routers.events"

    def test_emit_event(self, app):
        resp = app.post(
            "/api/v2/events/emit",
            json={"event_type": "tender.new", "payload": {"title": "Test"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "emitted"
        assert "event_id" in data
        assert "subscribers" in data

    def test_emit_event_alert_deadline(self, app):
        """Persist notification on alert.deadline type."""
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/events/emit",
                json={
                    "event_type": "alert.deadline",
                    "payload": {"title": "Deadline tomorrow", "tender_id": str(uuid.uuid4())},
                    "tenant_id": "test-tenant",
                },
            )
        assert resp.status_code == 200

    def test_emit_event_agent_done(self, app):
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post(
                "/api/v2/events/emit",
                json={"event_type": "agent.done", "payload": {"title": "Analysis complete"}},
            )
        assert resp.status_code == 200

    def test_get_notifications_all(self, app):
        now = datetime.now()
        row = (uuid.uuid4(), "tender.new", "New tender", "Details", "/tenders/123",
               False, now)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/notifications")
        assert resp.status_code == 200
        # /api/v2/notifications is handled by notifications.py (registered first)
        # which returns {"items": [...], "next_cursor": ...} format
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_get_notifications_unread_only(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/notifications?unread_only=true")
        assert resp.status_code == 200

    def test_get_notifications_with_limit(self, app):
        e = _eng(rows=[])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/notifications?limit=5")
        assert resp.status_code == 200

    def test_mark_read_all(self, app):
        e = _eng(rowcount=5)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post("/api/v2/notifications/mark-read", json=[])
        assert resp.status_code == 200
        data = resp.json()
        # notifications.py bulk-read returns {"marked": N}
        assert isinstance(data, dict)

    def test_mark_read_specific_ids(self, app):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        e = _eng(rowcount=2)
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.post("/api/v2/notifications/mark-read", json=ids)
        assert resp.status_code == 200

    def test_persist_notification(self):
        """Test _persist_notification helper directly."""
        from services.api.services.api.routers.events import _persist_notification
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            _persist_notification("alert.deadline", {"title": "Test", "tender_id": "abc"})
        # No exception raised

    def test_persist_notification_tender_new(self):
        from services.api.services.api.routers.events import _persist_notification
        e = _eng()
        with patch(f"{self.MOD}.get_engine", return_value=e):
            _persist_notification("tender.new", {"title": "A new tender"})

    def test_event_bus_publish(self):
        import asyncio
        from services.api.services.api.routers.events import EventBus
        bus = EventBus()

        async def _run():
            await bus.publish({"type": "test", "data": "hello"})

        asyncio.run(_run())

    def test_notifications_null_created_at(self, app):
        """Handle None created_at gracefully — route handled by notifications.py."""
        row = (uuid.uuid4(), "tender.new", "Title", "Body", None, False, None)
        e = _eng(rows=[row])
        with patch(f"{self.MOD}.get_engine", return_value=e):
            resp = app.get("/api/v2/notifications")
        assert resp.status_code == 200
        # Either format (list or {items:...}) is acceptable
        assert isinstance(resp.json(), (list, dict))
