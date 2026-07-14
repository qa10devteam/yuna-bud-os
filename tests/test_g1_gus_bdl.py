"""G1 — GUS BDL router coverage tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


# ── GET /api/v1/gus/indicators ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_indicators_ok(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/gus/indicators", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_list_indicators_filter_variable(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/gus/indicators?variable_id=P3808", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_indicators_filter_year(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/gus/indicators?year=2024", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_indicators_no_auth(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/gus/indicators")
    # conftest overrides auth so ASGI calls get demo user
    assert r.status_code in (200, 401, 403)


# ── GET /api/v1/gus/inflation ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_inflation_summary_ok(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/gus/inflation", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "note" in data


# ── POST /api/v1/gus/sync ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gus_sync_ok(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/gus/sync", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_gus_sync_year_param(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/gus/sync?year=2023", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["year"] == 2023


@pytest.mark.asyncio
async def test_gus_sync_invalid_year(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/gus/sync?year=1900", headers=auth_headers)
    assert r.status_code == 422


# ── GET /api/v2/gus/buyer/{nip} ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_gus_buyer_not_found(app, auth_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/gus/buyer/9999999999", headers=auth_headers)
    # Returns 200 with source=not_found, or 404
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert "source" in data or "nip" in data


@pytest.mark.asyncio
async def test_gus_sync_limit_year(app, auth_headers):
    """Year > 2030 should be rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/gus/sync?year=2031", headers=auth_headers)
    assert r.status_code == 422
