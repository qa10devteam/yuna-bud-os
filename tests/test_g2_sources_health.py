"""Tests for sources_health.py — /api/v1/sources/health endpoints."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


@pytest.fixture(scope="module")
def auth_headers():
    from services.api.services.api.auth.utils import create_access_token
    token = create_access_token(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_sources_health_v1_200(app, auth_headers):
    """GET /api/v1/sources/health → 200 with status field."""
    with patch("httpx.head") as mock_head, patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        mock_get.return_value = mock_resp
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/sources/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_sources_health_v1_has_sources(app, auth_headers):
    """GET /api/v1/sources/health → response includes sources list."""
    with patch("httpx.head") as mock_head, patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        mock_get.return_value = mock_resp
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/sources/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_sources_health_v1_has_ingest(app, auth_headers):
    """GET /api/v1/sources/health → response includes ingest stats."""
    with patch("httpx.head") as mock_head, patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        mock_get.return_value = mock_resp
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/sources/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "ingest" in data


@pytest.mark.asyncio
async def test_sources_health_v2_200(app, auth_headers):
    """GET /api/v2/sources/health → 200."""
    with patch("httpx.head") as mock_head, patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        mock_get.return_value = mock_resp
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v2/sources/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sources_health_v1_probe_error(app, auth_headers):
    """GET /api/v1/sources/health when external calls fail → still returns 200."""
    import httpx as _httpx
    with patch("httpx.head", side_effect=_httpx.ConnectError("timeout")), \
         patch("httpx.get", side_effect=_httpx.ConnectError("timeout")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/sources/health")
    assert resp.status_code == 200
    data = resp.json()
    # Should still return a degraded/error status
    assert "status" in data


@pytest.mark.asyncio
async def test_sources_health_v1_checked_at(app, auth_headers):
    """GET /api/v1/sources/health → includes checked_at timestamp."""
    with patch("httpx.head") as mock_head, patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        mock_get.return_value = mock_resp
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/sources/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "checked_at" in data
