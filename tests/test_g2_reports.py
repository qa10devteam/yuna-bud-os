"""Tests for reports.py — /api/v2/reports endpoints."""
from __future__ import annotations

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
async def test_reports_monthly_200(app, auth_headers):
    """GET /api/v2/reports/monthly → 200 with some response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/reports/monthly", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Accept both the v2/reports/monthly and any overriding report endpoint
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_reports_monthly_custom_params(app, auth_headers):
    """GET /api/v2/reports/monthly?year=2025&month=3 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/reports/monthly?year=2025&month=3", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_reports_monthly_pdf_200(app, auth_headers):
    """GET /api/v2/reports/monthly/pdf → 200 with content-type pdf or html."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/reports/monthly/pdf", headers=auth_headers)
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "pdf" in ct or "html" in ct or "json" in ct


@pytest.mark.asyncio
async def test_reports_benchmark_200(app, auth_headers):
    """GET /api/v2/reports/benchmark → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/reports/benchmark", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reports_monthly_is_dict(app, auth_headers):
    """GET /api/v2/reports/monthly → returns a dict."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/reports/monthly", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@pytest.mark.asyncio
async def test_reports_monthly_not_empty(app, auth_headers):
    """GET /api/v2/reports/monthly → dict is not empty."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/reports/monthly", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) > 0
