"""Tests for gantt.py — /api/v2/gantt endpoints."""
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
async def test_gantt_list_projects_200(app, auth_headers):
    """GET /api/v2/gantt/list → 200 with list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/gantt/list", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_gantt_get_tender_200(app, auth_headers):
    """GET /api/v2/gantt/{tender_id} → 200 with list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/gantt/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="DB schema mismatch in test env", strict=False)
async def test_gantt_add_task_200(app, auth_headers):
    """POST /api/v2/gantt/{tender_id}/tasks → 200."""
    payload = {
        "name": "Faza projektowania",
        "start_date": "2026-08-01",
        "end_date": "2026-08-31",
        "progress": 0,
        "color": "#3b82f6",
        "position": 1,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(f"/api/v2/gantt/{uuid.uuid4()}/tasks", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json().get("status") == "created"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="DB schema mismatch in test env", strict=False)
async def test_gantt_add_task_minimal(app, auth_headers):
    """POST /api/v2/gantt/{tender_id}/tasks with minimal payload → 200."""
    payload = {"name": "Faza budowy"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(f"/api/v2/gantt/{uuid.uuid4()}/tasks", json=payload, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_gantt_auto_generate_200(app, auth_headers):
    """POST /api/v2/gantt/{tender_id}/auto-generate → 200 or 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(f"/api/v2/gantt/{uuid.uuid4()}/auto-generate", headers=auth_headers)
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_gantt_get_empty_tender(app, auth_headers):
    """GET /api/v2/gantt/{tender_id} for unknown tender → 200 empty list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/gantt/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_gantt_no_auth_401(app):
    """GET /api/v2/gantt/list without auth → 401 or 403."""
    from services.api.services.api.main import app as _app
    from services.api.services.api.auth.deps import get_current_user
    original = _app.dependency_overrides.get(get_current_user)
    if original:
        del _app.dependency_overrides[get_current_user]
    try:
        async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as c:
            resp = await c.get("/api/v2/gantt/list")
        assert resp.status_code in (401, 403, 422)
    finally:
        if original:
            _app.dependency_overrides[get_current_user] = original
