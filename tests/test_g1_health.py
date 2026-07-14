"""G1 — Health router coverage tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


# ── GET /api/v1/health ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_v1_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "db" in data


# ── GET /api/v2/health ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_v2_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v2/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["version"] == "2.0"


# ── GET /health/live ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_live_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/live")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


# ── GET /health/ready ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_ready_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/ready")
    # 200 if DB + Redis ok; 503 if Redis not reachable
    assert r.status_code in (200, 503)
    data = r.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_health_ready_db_field(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/ready")
    data = r.json()
    # DB should be accessible in test env
    assert data["db"] == "ok"


# ── GET /health/detailed ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_detailed_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/detailed")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "uptime_s" in data
    assert "db_status" in data
    assert "db_tables_count" in data
    assert "redis_status" in data
    assert "env" in data


@pytest.mark.asyncio
async def test_health_detailed_uptime_positive(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/detailed")
    data = r.json()
    assert data["uptime_s"] >= 0


@pytest.mark.asyncio
async def test_health_detailed_tables_count(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/detailed")
    data = r.json()
    assert data["db_tables_count"] >= 0


# ── GET /health/system ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_system_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/system")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "subsystems" in data
    assert "uptime_s" in data


@pytest.mark.asyncio
async def test_health_system_subsystems(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health/system")
    data = r.json()
    subs = data["subsystems"]
    assert "db" in subs
    assert subs["db"]["status"] in ("ok", "error")


# ── Unit: _check_redis ────────────────────────────────────────────────────────

def test_check_redis_returns_string():
    from services.api.services.api.routers.health import _check_redis
    result = _check_redis()
    assert isinstance(result, str)
