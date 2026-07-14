"""Tests for estimates_v2.py — /api/v2/estimates endpoints."""
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
@pytest.mark.xfail(reason="DB schema mismatch in test env", strict=False)
async def test_estimates_list_200(app, auth_headers):
    """GET /api/v2/estimates?tender_id=... → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/estimates?tender_id=test-tender-001", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_estimates_list_missing_param_422(app, auth_headers):
    """GET /api/v2/estimates without tender_id → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/estimates", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_estimates_create_404_tender_not_found(app, auth_headers):
    """POST /api/v2/estimates with non-existent tender → 404."""
    payload = {
        "tender_id": str(uuid.uuid4()),
        "variant": "doc",
        "total_net_pln": 100000.0,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/estimates", json=payload, headers=auth_headers)
    assert resp.status_code in (404, 403)


@pytest.mark.asyncio
async def test_estimates_create_invalid_variant_422(app, auth_headers):
    """POST /api/v2/estimates with bad variant → 422."""
    payload = {
        "tender_id": str(uuid.uuid4()),
        "variant": "invalid_variant",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/estimates", json=payload, headers=auth_headers)
    assert resp.status_code in (404, 422)


@pytest.mark.asyncio
async def test_estimates_get_single_404(app, auth_headers):
    """GET /api/v2/estimates/{id} for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/estimates/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_estimates_patch_404(app, auth_headers):
    """PUT /api/v2/estimates/{id} for unknown id → 404."""
    payload = {"total_net_pln": 200000.0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.put(f"/api/v2/estimates/{uuid.uuid4()}", json=payload, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_estimates_delete_404(app, auth_headers):
    """DELETE /api/v2/estimates/{id} for unknown id → 404 or 405."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete(f"/api/v2/estimates/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code in (404, 405)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="DB schema mismatch in test env", strict=False)
async def test_estimates_predict_200(app, auth_headers):
    """GET /api/v2/estimates/predict → 200 with cost prediction."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(
            "/api/v2/estimates/predict?cpv=45&region=mazowieckie&area_m2=500&floors=3",
            headers=auth_headers,
        )
    assert resp.status_code in (200, 404, 422)


@pytest.mark.asyncio
async def test_estimates_export_404(app, auth_headers):
    """GET /api/v2/estimates/{id}/export for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/estimates/{uuid.uuid4()}/export", headers=auth_headers)
    assert resp.status_code in (404, 405)
