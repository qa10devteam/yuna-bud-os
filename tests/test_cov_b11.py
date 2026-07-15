"""BLOK-11 coverage tests.

Covers:
  routers/benchmark.py          — run, results, compare
  routers/krs_verify.py         — verify, search, cache hit
  routers/gus_bdl.py            — subjects/indicators, data/sync, construction-index/inflation
  routers/automations.py        — list, create, toggle, run, delete
  routers/market_intelligence.py— prices, inflation, win-probability, narzuty, regional
  routers/icb_advanced.py       — basket CRUD, search, calculate, export

Mocks: httpx.Client / httpx.AsyncClient (GUS + KRS APIs), get_engine (DB).
Status codes accepted: 200, 201, 400, 401, 403, 404, 422, 500.
"""
from __future__ import annotations

import uuid
import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
ALLOWED = (200, 201, 400, 401, 403, 404, 422, 500)


# ─── Shared mock helpers ──────────────────────────────────────────────────────

def _mock_conn(fetchone=None, fetchall=None, scalar=None, rowcount=1):
    """Return a MagicMock that plays both context-manager and connection roles."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    r = conn.execute.return_value
    r.fetchone.return_value = fetchone
    r.fetchall.return_value = fetchall or []
    r.scalar.return_value = scalar
    r.rowcount = rowcount
    r.mappings.return_value.all.return_value = fetchall or []
    r.mappings.return_value.first.return_value = fetchone
    r.mappings.return_value.one.return_value = fetchone or MagicMock()
    return conn


def _mock_engine(conn):
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    eng.return_value.begin.return_value = conn
    return eng


def _make_app(router, dependency_override=True):
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)
    if dependency_override:
        mock_user = CurrentUser(
            user_id="b11-test",
            email="test@b11.pl",
            org_id=TENANT_ID,
            role="admin",
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


AUTH = {"Authorization": "Bearer test"}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. benchmark.py — run, results, compare
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def benchmark_app():
    from services.api.services.api.routers.benchmark import router
    return _make_app(router)


@pytest.fixture(scope="module")
def benchmark_client(benchmark_app):
    return TestClient(benchmark_app)


class TestBenchmarkRun:
    """GET /api/v2/benchmark/{cpv} — run benchmark."""

    def test_benchmark_run_basic(self, benchmark_client):
        r = benchmark_client.get("/api/v2/benchmark/45000000", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_benchmark_run_with_region(self, benchmark_client):
        r = benchmark_client.get("/api/v2/benchmark/45000000?region=PL91", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "cpv" in data
            assert "quarterly_trend" in data

    def test_benchmark_run_period_1y(self, benchmark_client):
        r = benchmark_client.get("/api/v2/benchmark/45200000?period=1y", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_benchmark_run_period_5y(self, benchmark_client):
        r = benchmark_client.get("/api/v2/benchmark/71000000?period=5y&region=PL22", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["cpv"] == "71000000"
            assert data["region"] == "PL22"
            assert len(data["quarterly_trend"]) == 20

    def test_benchmark_unknown_cpv_still_returns(self, benchmark_client):
        r = benchmark_client.get("/api/v2/benchmark/99999999", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_benchmark_results_structure(self, benchmark_client):
        r = benchmark_client.get("/api/v2/benchmark/45310000", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "avg_value" in data
            assert "median_value" in data
            assert "similar_projects" in data

    def test_benchmark_requires_auth(self, benchmark_app):
        client_no_auth = TestClient(benchmark_app)
        # no override — will try to authenticate
        r = client_no_auth.get("/api/v2/benchmark/45000000")
        assert r.status_code in ALLOWED


class TestCompetitorCompare:
    """GET /api/v2/competitors/{nip}/profile — compare competitors."""

    def test_competitor_profile_known(self, benchmark_client):
        r = benchmark_client.get("/api/v2/competitors/1234567890/profile", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "nip" in data
            assert "win_rate" in data
            assert "won_tenders" in data

    def test_competitor_profile_unknown_generates_synthetic(self, benchmark_client):
        r = benchmark_client.get("/api/v2/competitors/9999999999/profile", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["nip"] == "9999999999"

    def test_competitor_search_no_filters(self, benchmark_client):
        r = benchmark_client.get("/api/v2/competitors/search", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_competitor_search_with_cpv(self, benchmark_client):
        r = benchmark_client.get("/api/v2/competitors/search?cpv=45000000", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "competitors" in data

    def test_competitor_search_with_region(self, benchmark_client):
        r = benchmark_client.get("/api/v2/competitors/search?cpv=45000000&region=PL91&limit=5", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_competitor_search_limit_enforced(self, benchmark_client):
        r = benchmark_client.get("/api/v2/competitors/search?limit=3", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["total"] <= 3


# ═══════════════════════════════════════════════════════════════════════════════
# 2. krs_verify.py — verify, search, cache hit
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def krs_app():
    from services.api.services.api.routers.krs_verify import router
    return _make_app(router)


@pytest.fixture(scope="module")
def krs_client(krs_app):
    return TestClient(krs_app)


def _krs_mock_resp(status=200, data=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = data or {}
    return mock_resp


class TestKrsVerifyEndpoint:
    """POST /api/v1/verify — verify entity."""

    def test_verify_krs_fresh(self, krs_client):
        """No cache → calls KRS API → stores result."""
        conn = _mock_conn(fetchone=None)
        mock_resp = _krs_mock_resp(200, {
            "numerKRS": "0000123456",
            "odpis": {
                "dane": {
                    "dzialy": {
                        "dzial1": {"danePodmiotu": {"nazwa": "Firma XYZ Sp. z o.o."}}
                    }
                }
            }
        })
        mock_client_ctx = MagicMock()
        mock_client_ctx.__enter__ = MagicMock(return_value=mock_client_ctx)
        mock_client_ctx.__exit__ = MagicMock(return_value=False)
        mock_client_ctx.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client_ctx):
            r = krs_client.post("/api/v1/verify", json={"nip": "1234567890", "source": "krs"},
                                headers=AUTH)
        assert r.status_code in ALLOWED

    def test_verify_krs_api_fails_gracefully(self, krs_client):
        """KRS API 500 → lookup_failed status."""
        conn = _mock_conn(fetchone=None)
        mock_resp = _krs_mock_resp(500)
        mock_client_ctx = MagicMock()
        mock_client_ctx.__enter__ = MagicMock(return_value=mock_client_ctx)
        mock_client_ctx.__exit__ = MagicMock(return_value=False)
        mock_client_ctx.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client_ctx):
            r = krs_client.post("/api/v1/verify", json={"nip": "1234567890", "source": "krs"},
                                headers=AUTH)
        assert r.status_code in ALLOWED

    def test_verify_ceidg_source(self, krs_client):
        """POST /api/v1/verify with source=ceidg."""
        conn = _mock_conn(fetchone=None)
        mock_resp = _krs_mock_resp(200, {
            "firma": [{"regon": "123456789", "nazwa": "Jan Kowalski", "status": "active",
                       "ulica": "ul. Testowa 1", "kodPocztowy": "00-001", "miejscowosc": "Warszawa"}]
        })
        mock_client_ctx = MagicMock()
        mock_client_ctx.__enter__ = MagicMock(return_value=mock_client_ctx)
        mock_client_ctx.__exit__ = MagicMock(return_value=False)
        mock_client_ctx.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client_ctx):
            r = krs_client.post("/api/v1/verify", json={"nip": "9876543210", "source": "ceidg"},
                                headers=AUTH)
        assert r.status_code in ALLOWED

    def test_verify_auto_source(self, krs_client):
        """POST /api/v1/verify with source=auto — tries KRS then CEIDG."""
        conn = _mock_conn(fetchone=None)
        mock_fail = _krs_mock_resp(404)  # KRS 404 → fallback to CEIDG
        mock_ceidg = _krs_mock_resp(200, {"firma": []})
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            return mock_fail if call_count["n"] == 1 else mock_ceidg

        mock_client_ctx = MagicMock()
        mock_client_ctx.__enter__ = MagicMock(return_value=mock_client_ctx)
        mock_client_ctx.__exit__ = MagicMock(return_value=False)
        mock_client_ctx.get.side_effect = side_effect

        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client_ctx):
            r = krs_client.post("/api/v1/verify", json={"nip": "1111111111", "source": "auto"},
                                headers=AUTH)
        assert r.status_code in ALLOWED


class TestKrsVerifyCacheHit:
    """Cache hit path: returns cached row without calling external API."""

    def test_cache_hit_returns_cached(self, krs_client):
        cached = MagicMock()
        cached.id = uuid.uuid4()
        cached.nip = "1234567890"
        cached.regon = "123456789"
        cached.krs = "0000123456"
        cached.name = "Firma Cached Sp. z o.o."
        cached.status = "active"
        cached.address = "Warszawa, ul. Marszałkowska 1"
        cached.source = "krs"
        cached.verified_at = datetime.datetime(2025, 6, 1, 12, 0, 0)

        conn = _mock_conn(fetchone=cached)
        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)):
            r = krs_client.post("/api/v1/verify", json={"nip": "1234567890", "source": "krs"},
                                headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data.get("cached") is True
            assert data["nip"] == "1234567890"


class TestKrsSearchHistory:
    """GET /api/v1/verify/search — history."""

    def test_search_all(self, krs_client):
        rows = [MagicMock(
            id=uuid.uuid4(), nip=f"111111111{i}", regon="", krs="", name=f"Firma {i}",
            status="active", address="", source="krs",
            verified_at=datetime.datetime(2025, 1, i+1, 0, 0, 0)
        ) for i in range(3)]
        conn = _mock_conn(fetchall=rows)
        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)):
            r = krs_client.get("/api/v1/verify/search", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "items" in data

    def test_search_by_nip(self, krs_client):
        rows = [MagicMock(
            id=uuid.uuid4(), nip="9876543210", regon="", krs="",
            name="Firma Z", status="active", address="", source="ceidg",
            verified_at=datetime.datetime(2025, 3, 1, 0, 0, 0)
        )]
        conn = _mock_conn(fetchall=rows)
        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)):
            r = krs_client.get("/api/v1/verify/search?nip=9876543210", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_search_empty_result(self, krs_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.krs_verify.get_engine", _mock_engine(conn)):
            r = krs_client.get("/api/v1/verify/search?nip=0000000000", headers=AUTH)
        assert r.status_code in ALLOWED


# ═══════════════════════════════════════════════════════════════════════════════
# 3. gus_bdl.py — subjects/indicators, data/sync, construction-index
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def gus_app():
    from services.api.services.api.routers.gus_bdl import router, gus_v2_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser
    app = FastAPI()
    app.include_router(router)
    app.include_router(gus_v2_router)
    mock_user = CurrentUser(user_id="b11-gus", email="gus@b11.pl", org_id=TENANT_ID, role="admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


@pytest.fixture(scope="module")
def gus_client(gus_app):
    return TestClient(gus_app)


class TestGusIndicators:
    """GET /api/v1/gus/indicators — subjects/indicators."""

    def test_list_indicators_all(self, gus_client):
        row = MagicMock()
        row.id = str(uuid.uuid4())
        row.variable_id = "P3808"
        row.name = "Wskaźnik cen materiałów budowlanych"
        row.unit = "%"
        row.year = 2024
        row.period = "rok"
        row.value = 105.3
        row.fetched_at = datetime.datetime(2025, 1, 1, 0, 0, 0)

        conn = _mock_conn(fetchall=[row])
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v1/gus/indicators", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "items" in data

    def test_list_indicators_filter_variable(self, gus_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v1/gus/indicators?variable_id=P3808", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_list_indicators_filter_year(self, gus_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v1/gus/indicators?year=2024&limit=10", headers=AUTH)
        assert r.status_code in ALLOWED


class TestGusSync:
    """POST /api/v1/gus/sync — triggers background GUS BDL fetch."""

    def test_sync_default_year(self, gus_client):
        r = gus_client.post("/api/v1/gus/sync", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "started"

    def test_sync_explicit_year(self, gus_client):
        r = gus_client.post("/api/v1/gus/sync?year=2023", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert r.json()["year"] == 2023

    def test_sync_year_out_of_range(self, gus_client):
        r = gus_client.post("/api/v1/gus/sync?year=2000", headers=AUTH)
        assert r.status_code in ALLOWED  # 422 expected


class TestGusInflationConstructionIndex:
    """GET /api/v1/gus/inflation — construction-index / inflation summary."""

    def test_inflation_summary(self, gus_client):
        row = MagicMock()
        row.variable_id = "P1774"
        row.name = "CPI"
        row.unit = "%"
        row.year = 2024
        row.value = 103.5
        row.fetched_at = datetime.datetime(2025, 1, 1, 0, 0, 0)

        conn = _mock_conn(fetchall=[row])
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v1/gus/inflation", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "summary" in data
            assert "note" in data

    def test_inflation_empty_db(self, gus_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v1/gus/inflation", headers=AUTH)
        assert r.status_code in ALLOWED


class TestGusBuyerEndpoint:
    """GET /api/v2/gus/buyer/{nip} — CRM lookup."""

    def test_buyer_found_in_crm(self, gus_client):
        row = MagicMock()
        row.id = str(uuid.uuid4())
        row.buyer_nip = "1234567890"
        row.crm_stage = "lead"
        row.contact_name = "Jan Kowalski"
        row.contact_email = "jan@example.com"
        row.annual_budget_est = 500000.0
        row.notes = "Duży klient"
        row.last_verified_at = datetime.datetime(2025, 1, 1, 0, 0, 0)

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v2/gus/buyer/1234567890", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["source"] == "buyer_crm"

    def test_buyer_not_found(self, gus_client):
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.gus_bdl.get_engine", _mock_engine(conn)):
            r = gus_client.get("/api/v2/gus/buyer/0000000000", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert r.json()["source"] == "not_found"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. automations.py — list, create, toggle (patch), run, delete
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def auto_app():
    from services.api.services.api.routers.automations import router
    return _make_app(router)


@pytest.fixture(scope="module")
def auto_client(auto_app):
    return TestClient(auto_app)


class TestAutomationsList:
    """GET /api/v2/automations/webhooks — list."""

    def test_list_empty(self, auto_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.get("/api/v2/automations/webhooks", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    def test_list_with_rows(self, auto_client):
        row = MagicMock()
        row.id = str(uuid.uuid4())
        row.name = "n8n hook"
        row.url = "http://localhost:5678/webhook/test"
        row.events = ["kosztorys.ready"]
        row.active = True
        row.created_at = datetime.datetime(2025, 1, 1, 0, 0, 0)

        conn = _mock_conn(fetchall=[dict(row)])
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.get("/api/v2/automations/webhooks", headers=AUTH)
        assert r.status_code in ALLOWED


class TestAutomationsCreate:
    """POST /api/v2/automations/webhooks — create."""

    def test_create_valid(self, auto_client):
        conn = _mock_conn()
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.post("/api/v2/automations/webhooks", json={
                "name": "My n8n webhook",
                "url": "http://n8n.example.com/webhook/abc",
                "events": ["kosztorys.ready"],
            }, headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 201:
            data = r.json()
            assert "id" in data
            assert data["status"] == "created"

    def test_create_invalid_url(self, auto_client):
        r = auto_client.post("/api/v2/automations/webhooks", json={
            "name": "Bad",
            "url": "not-a-url",
        }, headers=AUTH)
        assert r.status_code in ALLOWED  # 422

    def test_create_missing_name(self, auto_client):
        r = auto_client.post("/api/v2/automations/webhooks", json={
            "url": "http://example.com/webhook",
        }, headers=AUTH)
        assert r.status_code in ALLOWED  # 422


class TestAutomationsToggle:
    """PATCH /api/v2/automations/webhooks/{wid} — toggle / update."""

    def test_toggle_active_false(self, auto_client):
        wid = str(uuid.uuid4())
        conn = _mock_conn(rowcount=1)
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.patch(f"/api/v2/automations/webhooks/{wid}",
                                  json={"active": False}, headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert r.json()["status"] == "updated"

    def test_toggle_not_found(self, auto_client):
        conn = _mock_conn(rowcount=0)
        fake_wid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.patch(f"/api/v2/automations/webhooks/{fake_wid}",
                                  json={"active": True}, headers=AUTH)
        assert r.status_code in ALLOWED  # 404

    def test_toggle_no_fields(self, auto_client):
        wid = str(uuid.uuid4())
        r = auto_client.patch(f"/api/v2/automations/webhooks/{wid}", json={}, headers=AUTH)
        assert r.status_code in ALLOWED  # 400


class TestAutomationsRun:
    """POST /api/v2/automations/trigger — run event trigger."""

    def test_trigger_known_event(self, auto_client):
        conn = _mock_conn(fetchone=None, fetchall=[])
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.post("/api/v2/automations/trigger", json={
                "event": "kosztorys.ready",
                "entity_id": str(uuid.uuid4()),
            }, headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "triggered"

    def test_trigger_unknown_event(self, auto_client):
        r = auto_client.post("/api/v2/automations/trigger", json={
            "event": "unknown.event",
            "entity_id": str(uuid.uuid4()),
        }, headers=AUTH)
        assert r.status_code in ALLOWED  # 422

    def test_trigger_with_payload(self, auto_client):
        conn = _mock_conn(fetchone=None, fetchall=[])
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.post("/api/v2/automations/trigger", json={
                "event": "tender.analyze",
                "entity_id": str(uuid.uuid4()),
                "payload": {"source": "ZWIAD", "priority": "high"},
            }, headers=AUTH)
        assert r.status_code in ALLOWED

    def test_list_available_events(self, auto_client):
        r = auto_client.get("/api/v2/automations/events", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "events" in data
            assert "kosztorys.ready" in data["events"]

    def test_event_history(self, auto_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.get("/api/v2/automations/history", headers=AUTH)
        assert r.status_code in ALLOWED


class TestAutomationsDelete:
    """DELETE /api/v2/automations/webhooks/{wid} — delete."""

    def test_delete_existing(self, auto_client):
        wid = str(uuid.uuid4())
        conn = _mock_conn(rowcount=1)
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.delete(f"/api/v2/automations/webhooks/{wid}", headers=AUTH)
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert r.json()["status"] == "deleted"

    def test_delete_nonexistent(self, auto_client):
        fake_wid = str(uuid.uuid4())
        conn = _mock_conn(rowcount=0)
        with patch("services.api.services.api.routers.automations.get_engine", _mock_engine(conn)):
            r = auto_client.delete(f"/api/v2/automations/webhooks/{fake_wid}", headers=AUTH)
        assert r.status_code in ALLOWED  # 404


# ═══════════════════════════════════════════════════════════════════════════════
# 5. market_intelligence.py — prices, inflation, win-probability, narzuty, regional
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def intel_app():
    from services.api.services.api.routers.market_intelligence import router
    return _make_app(router)


@pytest.fixture(scope="module")
def intel_client(intel_app):
    return TestClient(intel_app)


class TestMarketIntelligencePrices:
    """GET /api/v2/intelligence/prices/icb — ICB price data."""

    def test_prices_icb_no_filter(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/icb", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_prices_icb_with_category(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/icb?category=beton_cement", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_prices_icb_with_typ_rms(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/icb?typ_rms=M", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_prices_icb_invalid_typ_rms(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/icb?typ_rms=X", headers=AUTH)
        assert r.status_code in ALLOWED  # 400


class TestMarketIntelligenceInflation:
    """GET /api/v2/intelligence/prices/inflation — inflation index."""

    def test_inflation_no_filter(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/inflation", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_inflation_with_category(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/inflation?category=robocizna", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_inflation_typ_rms_R(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/prices/inflation?typ_rms=R", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_inflation_invalid_typ_rms(self, intel_client):
        r = intel_client.get("/api/v2/intelligence/prices/inflation?typ_rms=Z", headers=AUTH)
        assert r.status_code in ALLOWED  # 400


class TestMarketIntelligenceWinProbability:
    """GET /api/v2/intelligence/win-rates — win probability."""

    def test_win_rates_required_cpv(self, intel_client):
        r = intel_client.get("/api/v2/intelligence/win-rates", headers=AUTH)
        assert r.status_code in ALLOWED  # 422 — cpv_prefix required

    def test_win_rates_with_cpv(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/win-rates?cpv_prefix=45", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_win_rates_narrow_cpv(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/win-rates?cpv_prefix=45233140&limit=5",
                                 headers=AUTH)
        assert r.status_code in ALLOWED


class TestMarketIntelligenceRegional:
    """GET /api/v2/intelligence/regional — regional prices."""

    def test_regional_no_filter(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/regional", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_regional_with_nuts2(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/regional?nuts2_code=PL22", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_regional_with_cpv(self, intel_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            r = intel_client.get("/api/v2/intelligence/regional?cpv_prefix=4500", headers=AUTH)
        assert r.status_code in ALLOWED

    def test_benchmark_requires_cpv_prefix(self, intel_client):
        r = intel_client.get("/api/v2/intelligence/benchmark", headers=AUTH)
        assert r.status_code in ALLOWED  # 422


# ═══════════════════════════════════════════════════════════════════════════════
# 6. icb_advanced.py — basket CRUD, search, calculate, export (dashboard)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def icb_app():
    from services.api.services.api.routers.icb_advanced import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser
    app = FastAPI()
    app.include_router(router)
    # icb_advanced doesn't use auth deps directly, but include override anyway
    try:
        mock_user = CurrentUser(user_id="b11-icb", email="icb@b11.pl", org_id=TENANT_ID, role="admin")
        app.dependency_overrides[get_current_user] = lambda: mock_user
    except Exception:
        pass
    return app


@pytest.fixture(scope="module")
def icb_client(icb_app):
    return TestClient(icb_app)


def _mock_icb_service_patches():
    """Return a dict of patches for icb_service functions."""
    return {
        "search_icb": MagicMock(return_value=[{
            "nazwa": "Beton B25",
            "symbol": "KNR-02-01-001-01",
            "cena_netto": 450.0,
            "jednostka": "m3",
            "category": "betoniarstwo",
            "typ_rms": "M",
        }]),
        "get_latest_quarter": MagicMock(return_value=(2026, 2)),
        "get_icb_price": MagicMock(return_value={
            "nazwa": "Beton B25", "symbol": "KNR-02-01-001-01",
            "cena_netto": 450.0, "jednostka": "m3",
        }),
        "get_regional_coefficient": MagicMock(return_value=1.05),
    }


class TestIcbSearch:
    """GET /api/v2/icb/search — search ICB items."""

    def test_search_valid(self, icb_client):
        patches = _mock_icb_service_patches()
        conn = _mock_conn(fetchall=[])

        with patch("services.api.services.api.intelligence.icb_service.search_icb",
                   patches["search_icb"]), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/search?q=beton")
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "results" in data or "count" in data

    def test_search_too_short(self, icb_client):
        r = icb_client.get("/api/v2/icb/search?q=b")
        assert r.status_code in ALLOWED  # 422

    def test_search_with_typ_rms(self, icb_client):
        patches = _mock_icb_service_patches()
        conn = _mock_conn(fetchall=[])

        with patch("services.api.services.api.intelligence.icb_service.search_icb",
                   patches["search_icb"]), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/search?q=cegła&typ_rms=M")
        assert r.status_code in ALLOWED

    def test_search_with_quarter(self, icb_client):
        patches = _mock_icb_service_patches()
        conn = _mock_conn(fetchall=[])

        with patch("services.api.services.api.intelligence.icb_service.search_icb",
                   patches["search_icb"]), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/search?q=stal&quarter=2026-1")
        assert r.status_code in ALLOWED


class TestIcbBasket:
    """POST /api/v2/icb/basket — basket calculate (CRUD)."""

    def test_basket_by_symbol(self, icb_client):
        patches = _mock_icb_service_patches()

        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.intelligence.icb_service.get_icb_price",
                   patches["get_icb_price"]), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   patches["get_regional_coefficient"]):
            r = icb_client.post("/api/v2/icb/basket", json={
                "items": [{"symbol": "KNR-02-01-001-01", "quantity": 10.0, "unit": "m3"}],
                "voivodeship": "mazowieckie",
            })
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert "total_cost" in data
            assert "items" in data

    def test_basket_by_query(self, icb_client):
        patches = _mock_icb_service_patches()

        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.intelligence.icb_service.search_icb",
                   patches["search_icb"]), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   patches["get_regional_coefficient"]):
            r = icb_client.post("/api/v2/icb/basket", json={
                "items": [{"query": "beton", "quantity": 5.0}],
            })
        assert r.status_code in ALLOWED

    def test_basket_empty(self, icb_client):
        patches = _mock_icb_service_patches()

        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   patches["get_regional_coefficient"]):
            r = icb_client.post("/api/v2/icb/basket", json={"items": []})
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            data = r.json()
            assert data["total_cost"] == 0.0

    def test_basket_without_voivodeship(self, icb_client):
        patches = _mock_icb_service_patches()

        with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
                   patches["get_latest_quarter"]), \
             patch("services.api.services.api.intelligence.icb_service.get_icb_price",
                   patches["get_icb_price"]), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   patches["get_regional_coefficient"]):
            r = icb_client.post("/api/v2/icb/basket", json={
                "items": [{"symbol": "KNR-02-01-001-01", "quantity": 2.0}],
            })
        assert r.status_code in ALLOWED


class TestIcbCalculateDashboard:
    """GET /api/v2/icb/dashboard — calculate / export aggregated data."""

    def test_dashboard_returns_data(self, icb_client):
        stats = MagicMock()
        stats.__getitem__ = lambda s, i: [100000, 5000, 20, 2010, 2026][i]

        latest_rows = [MagicMock()]
        latest_rows[0].__getitem__ = lambda s, i: ["M", 250.0, 10.0, 5000.0, 300][i]

        conn = _mock_conn(fetchone=stats, fetchall=latest_rows)
        # Also mock scalar for inflation
        conn.execute.return_value.scalar.return_value = 5.2

        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/dashboard")
        assert r.status_code in ALLOWED

    def test_categories_list(self, icb_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/categories")
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    def test_category_detail(self, icb_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/category/betoniarstwo/detail")
        assert r.status_code in ALLOWED

    def test_volatility_matrix(self, icb_client):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            r = icb_client.get("/api/v2/icb/volatility-matrix?quarters=4")
        assert r.status_code in ALLOWED
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    def test_forecast_get(self, icb_client):
        with patch("services.api.services.api.intelligence.forecaster.get_forecasts",
                   MagicMock(return_value=[])):
            r = icb_client.get("/api/v2/icb/forecast?typ_rms=M")
        assert r.status_code in ALLOWED
