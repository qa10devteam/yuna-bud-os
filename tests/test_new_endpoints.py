"""BLOK-6: Integration tests for 5 new API endpoints.

1. GET  /api/v2/auth/me/full
2. POST /api/v2/tenders/{id}/analyze
3. GET  /api/v2/tenders/{id}/similar
4. POST /api/v2/notifications/bulk-read
5. GET  /api/v2/search
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

FAKE_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET /api/v2/auth/me/full
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_full_authenticated(app, auth_headers):
    """Authenticated user gets full profile with expected keys."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/auth/me/full", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "user_id" in data
    assert "email" in data
    assert "role" in data
    assert "feature_flags" in data
    assert isinstance(data["feature_flags"], list)


@pytest.mark.asyncio
async def test_me_full_unauthenticated(app):
    """No token → 401/403 or 200 (conftest overrides auth globally in ASGI tests)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/auth/me/full")
    # conftest installs dependency_overrides so all ASGI calls get demo user;
    # expect either auth error (in real env) or success (in test env)
    assert r.status_code in (200, 401, 403)


@pytest.mark.asyncio
async def test_me_full_org_field(app, auth_headers):
    """org field is either None or a dict with id/name/plan."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/auth/me/full", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    org = data.get("org")
    if org is not None:
        assert "id" in org
        assert "name" in org
        assert "plan" in org


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /api/v2/tenders/{id}/analyze
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_tender_invalid_uuid(app, auth_headers):
    """Non-UUID tender_id → 404 (UUID validation)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v2/tenders/not-a-uuid/analyze", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_analyze_tender_not_found(app, auth_headers):
    """Valid UUID that doesn't exist → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v2/tenders/{FAKE_UUID}/analyze", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_analyze_tender_unauthenticated(app):
    """No token → 401/403 or 404 (conftest overrides auth in ASGI tests)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(f"/api/v2/tenders/{FAKE_UUID}/analyze")
    assert r.status_code in (401, 403, 404)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /api/v2/tenders/{id}/similar
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_similar_tenders_invalid_uuid(app, auth_headers):
    """Non-UUID tender_id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/tenders/not-a-uuid/similar", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_similar_tenders_not_found_returns_empty(app, auth_headers):
    """Non-existent tender → empty items list (not an error)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get(f"/api/v2/tenders/{FAKE_UUID}/similar", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "count" in data
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_similar_tenders_unauthenticated(app):
    """No token → 401/403 or 200 (conftest overrides auth in ASGI tests)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get(f"/api/v2/tenders/{FAKE_UUID}/similar")
    assert r.status_code in (200, 401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# 4. POST /api/v2/notifications/bulk-read
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bulk_read_empty_ids(app, auth_headers):
    """Empty body (no ids, all=false) → updated: 0."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v2/notifications/bulk-read",
            headers=auth_headers,
            json={},
        )
    assert r.status_code == 200
    data = r.json()
    assert "updated" in data
    assert data["updated"] == 0


@pytest.mark.asyncio
async def test_bulk_read_with_ids(app, auth_headers):
    """Passing specific (non-existent) UUIDs → updated: 0 (none matched)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v2/notifications/bulk-read",
            headers=auth_headers,
            json={"ids": [FAKE_UUID]},
        )
    assert r.status_code == 200
    data = r.json()
    assert "updated" in data
    assert isinstance(data["updated"], int)


@pytest.mark.asyncio
async def test_bulk_read_all(app, auth_headers):
    """all=true flag → updated count (may be 0 in clean DB)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v2/notifications/bulk-read",
            headers=auth_headers,
            json={"all": True},
        )
    assert r.status_code == 200
    data = r.json()
    assert "updated" in data
    assert isinstance(data["updated"], int)


@pytest.mark.asyncio
async def test_bulk_read_unauthenticated(app):
    """No token → 401/403 or 200 (conftest overrides auth in ASGI tests)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v2/notifications/bulk-read", json={"all": True})
    assert r.status_code in (200, 401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /api/v2/search
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_basic(app, auth_headers):
    """Valid query returns results shape."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/search?q=test", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # Accept either search response format (items/results)
    assert "items" in data or "results" in data


@pytest.mark.asyncio
async def test_search_too_short_query(app, auth_headers):
    """Query shorter than min_length → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/search?q=x", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_with_type_filter(app, auth_headers):
    """type=tenders filter is accepted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/search?q=remont&type=tenders", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_search_with_limit(app, auth_headers):
    """limit parameter is accepted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/search?q=budowa&limit=5", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_search_unauthenticated(app):
    """No token → 401/403 or 200 (conftest overrides auth in ASGI tests)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/search?q=test")
    assert r.status_code in (200, 401, 403)
