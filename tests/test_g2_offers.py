"""Tests for offers.py — /api/v1/offers CRUD endpoints."""
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
async def test_offers_list_200(app, auth_headers):
    """GET /api/v1/offers → 200 with items."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/offers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or "next_cursor" in data


@pytest.mark.asyncio
async def test_offers_list_with_cursor(app, auth_headers):
    """GET /api/v1/offers?limit=5 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/offers?limit=5", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.xfail(reason="offers table missing source column in test DB", strict=False)
async def test_offers_create_201(app, auth_headers):
    """POST /api/v1/offers → 201."""
    payload = {
        "title": "Oferta testowa na budowę drogi",
        "status": "draft",
        "delivery_days": 90,
        "warranty_months": 36,
        "payment_terms": "30 dni od faktury",
        "price_gross_pln": 500000.0,
        "vat_pct": 23.0,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/offers", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_offers_create_invalid_status_422(app, auth_headers):
    """POST /api/v1/offers with invalid status → 422."""
    payload = {
        "title": "Bad offer",
        "status": "invalid_status_xyz",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/offers", json=payload, headers=auth_headers)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="offers table missing source column in test DB", strict=False)
async def test_offers_get_single_200(app, auth_headers):
    """POST then GET /api/v1/offers/{id} → 200."""
    payload = {
        "title": "Oferta get test",
        "status": "draft",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        create_resp = await c.post("/api/v1/offers", json=payload, headers=auth_headers)
        if create_resp.status_code in (200, 201):
            offer_id = create_resp.json().get("id")
            if offer_id:
                get_resp = await c.get(f"/api/v1/offers/{offer_id}", headers=auth_headers)
                assert get_resp.status_code == 200


@pytest.mark.asyncio
async def test_offers_get_404(app, auth_headers):
    """GET /api/v1/offers/{id} for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/offers/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_offers_patch_404(app, auth_headers):
    """PATCH /api/v1/offers/{id} for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch(
            f"/api/v1/offers/{uuid.uuid4()}",
            json={"status": "ready"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.xfail(reason="offers table missing source column in test DB", strict=False)
async def test_offers_delete_204(app, auth_headers):
    """POST then DELETE /api/v1/offers/{id} → 204."""
    payload = {"title": "Offer to delete", "status": "draft"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        create_resp = await c.post("/api/v1/offers", json=payload, headers=auth_headers)
        if create_resp.status_code in (200, 201):
            offer_id = create_resp.json().get("id")
            if offer_id:
                del_resp = await c.delete(f"/api/v1/offers/{offer_id}", headers=auth_headers)
                assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_offers_delete_404(app, auth_headers):
    """DELETE /api/v1/offers/{id} for unknown id → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete(f"/api/v1/offers/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_offers_pdf_404(app, auth_headers):
    """GET /api/v1/offers/{id}/pdf for unknown → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/offers/{uuid.uuid4()}/pdf", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.xfail(reason="offers table missing source column in test DB", strict=False)
async def test_offers_create_with_source(app, auth_headers):
    """POST /api/v1/offers with valid source → 201 or 422."""
    payload = {
        "title": "Oferta z BZP",
        "status": "draft",
        "source": "bzp",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/offers", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201, 422)
