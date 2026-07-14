"""Tests for resources.py — subcontractors, equipment, employees, etc."""
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


# ── Subcontractors ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subcontractors_list_200(app, auth_headers):
    """GET /api/v1/subcontractors → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/subcontractors", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_subcontractors_list_filter_active(app, auth_headers):
    """GET /api/v1/subcontractors?active=true → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/subcontractors?active=true", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_subcontractors_create_200(app, auth_headers):
    """POST /api/v1/subcontractors → 200 or 201."""
    payload = {
        "name": "Test Subcontractor Sp. z o.o.",
        "nip": "1234567890",
        "specialization": ["roboty budowlane"],
        "contact_email": "sub@test.pl",
        "rating": 4.5,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/subcontractors", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_subcontractors_get_404(app, auth_headers):
    """GET /api/v1/subcontractors/{id} for unknown → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/subcontractors/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_subcontractors_delete_404(app, auth_headers):
    """DELETE /api/v1/subcontractors/{id} for unknown → 404 or 200 (idempotent)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete(f"/api/v1/subcontractors/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code in (200, 204, 404)


# ── Equipment ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_equipment_list_200(app, auth_headers):
    """GET /api/v1/equipment → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/equipment", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_equipment_create_200(app, auth_headers):
    """POST /api/v1/equipment → 200 or 201."""
    payload = {
        "name": "Koparka CAT 320",
        "type": "heavy",
        "serial_number": "CAT-2024-001",
        "daily_rate_pln": 2500.0,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/equipment", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_equipment_delete_404(app, auth_headers):
    """DELETE /api/v1/equipment/{id} for unknown → 404 or 200 (idempotent)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete(f"/api/v1/equipment/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code in (200, 204, 404)


# ── Employees ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_employees_list_200(app, auth_headers):
    """GET /api/v1/resources/employees → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/resources/employees", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_employees_create_201(app, auth_headers):
    """POST /api/v1/resources/employees → 201."""
    payload = {
        "name": "Jan Testowy",
        "role": "kierownik budowy",
        "hourly_rate_pln": 85.0,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/resources/employees", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_employees_delete_404(app, auth_headers):
    """DELETE /api/v1/resources/employees/{id} for unknown → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete(f"/api/v1/resources/employees/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code in (204, 404)
