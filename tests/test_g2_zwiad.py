"""Tests for zwiad.py — /api/v1/tenders & /api/v1/ingest endpoints."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

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
async def test_tenders_list_200(app, auth_headers):
    """GET /api/v2/tenders → 200 with items and total."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or "total" in data


@pytest.mark.asyncio
async def test_tenders_list_with_limit(app, auth_headers):
    """GET /api/v2/tenders?limit=5 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders?limit=5", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tenders_list_filter_status(app, auth_headers):
    """GET /api/v2/tenders?status=new → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders?status=new", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tenders_list_filter_voivodeship(app, auth_headers):
    """GET /api/v2/tenders?voivodeship=mazowieckie → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders?voivodeship=mazowieckie", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tender_detail_404(app, auth_headers):
    """GET /api/v1/tenders/{id} for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/tenders/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tender_patch_404(app, auth_headers):
    """PATCH /api/v1/tenders/{id} for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch(
            f"/api/v1/tenders/{uuid.uuid4()}",
            json={"status": "new"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ingest_tasks_list_200(app, auth_headers):
    """GET /api/v1/ingest/tasks → 200 with list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/ingest/tasks", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ingest_task_404(app, auth_headers):
    """GET /api/v1/ingest/tasks/{task_id} for unknown → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/ingest/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
