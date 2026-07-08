"""Sprint K11 tests — benchmark, market_intelligence, market_data router coverage."""
import uuid
import pytest

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


@pytest.fixture
def benchmark_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.benchmark import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)
    mock_user = CurrentUser(user_id="k11", email="test@qa10.io", org_id=TENANT_ID, role="admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture
def intel_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.market_intelligence import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)
    mock_user = CurrentUser(user_id="k11", email="test@qa10.io", org_id=TENANT_ID, role="admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture
def market_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.market_data import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)
    mock_user = CurrentUser(user_id="k11", email="test@qa10.io", org_id=TENANT_ID, role="admin")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


auth = {"Authorization": "Bearer test"}


# ─── BENCHMARK ROUTER ─────────────────────────────────────────────────────────

class TestBenchmarkRouter:
    def test_benchmark_cpv(self, benchmark_client):
        resp = benchmark_client.get("/benchmark/45", headers=auth)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_benchmark_cpv_narrow(self, benchmark_client):
        resp = benchmark_client.get("/benchmark/45200000", headers=auth)
        assert resp.status_code in (200, 404)

    def test_competitors_profile_nonexistent(self, benchmark_client):
        resp = benchmark_client.get("/competitors/0000000000/profile", headers=auth)
        assert resp.status_code in (200, 404)

    def test_competitors_search_empty(self, benchmark_client):
        resp = benchmark_client.get("/competitors/search?q=nieistniejacy", headers=auth)
        assert resp.status_code in (200, 404)

    def test_competitors_search_real(self, benchmark_client):
        resp = benchmark_client.get("/competitors/search?q=budimex", headers=auth)
        assert resp.status_code in (200, 404)


# ─── MARKET INTELLIGENCE ROUTER ───────────────────────────────────────────────

class TestMarketIntelligenceRouter:
    def test_benchmark_no_params(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/benchmark", headers=auth)
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert isinstance(resp.json(), (dict, list))

    def test_benchmark_with_cpv(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/benchmark?cpv=45", headers=auth)
        assert resp.status_code in (200, 422)

    def test_trends(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/trends", headers=auth)
        assert resp.status_code in (200, 422)

    def test_trends_with_cpv(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/trends?cpv=45", headers=auth)
        assert resp.status_code in (200, 422)

    def test_competitors_top(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/competitors/top", headers=auth)
        assert resp.status_code in (200, 422)

    def test_buyers_top(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/buyers/top", headers=auth)
        assert resp.status_code in (200, 422)

    def test_prices_icb(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/prices/icb", headers=auth)
        assert resp.status_code in (200, 422)

    def test_prices_icb_with_category(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/prices/icb?category=Roboty+betonowe", headers=auth)
        assert resp.status_code in (200, 422)

    def test_prices_inflation(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/prices/inflation", headers=auth)
        assert resp.status_code in (200, 422)

    def test_regional(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/regional", headers=auth)
        assert resp.status_code in (200, 422)

    def test_seasonality(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/seasonality", headers=auth)
        assert resp.status_code in (200, 422)

    def test_fts_search(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/fts?q=droga+betonowa", headers=auth)
        assert resp.status_code in (200, 422)

    def test_summary(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/summary", headers=auth)
        assert resp.status_code in (200, 422)

    def test_win_rates(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/win-rates", headers=auth)
        assert resp.status_code in (200, 422)

    def test_top_buyers_cpv(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/top-buyers-cpv?cpv=45", headers=auth)
        assert resp.status_code in (200, 422)

    def test_sekocenbud_search(self, intel_client):
        resp = intel_client.get("/api/v2/intelligence/sekocenbud?q=beton", headers=auth)
        assert resp.status_code in (200, 422)


# ─── MARKET DATA ROUTER ───────────────────────────────────────────────────────

class TestMarketDataRouter:
    def test_list_or_first_endpoint(self, market_client):
        # Hit the first available route (browse routes to find something)
        from services.api.services.api.routers.market_data import router
        if not router.routes:
            pytest.skip("No routes in market_data router")
        first_route = router.routes[0]
        path = getattr(first_route, 'path', '/')
        resp = market_client.get(path, headers=auth)
        assert resp.status_code in (200, 404, 422, 405)
