"""Tests for analytics_v2.py — /api/v2/analytics endpoints."""
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
async def test_analytics_dashboard_200(app, auth_headers):
    """GET /api/v2/analytics/dashboard → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_pipeline_funnel_200(app, auth_headers):
    """GET /api/v2/analytics/pipeline-funnel → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/analytics/pipeline-funnel", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_optimal_markup_200(app, auth_headers):
    """POST /api/v2/analytics/optimal-markup → 200."""
    payload = {
        "cost_estimate": 500000.0,
        "n_competitors": 5,
        "cpv": "45",
        "region": "mazowieckie",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/analytics/optimal-markup", json=payload, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_ahp_score_200(app, auth_headers):
    """POST /api/v2/analytics/ahp-score → 200."""
    payload = {
        "scores": {
            "cpv_match": 0.8,
            "value_range": 0.7,
            "deadline_pressure": 0.5,
            "buyer_history": 0.6,
            "document_quality": 0.9,
        }
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/analytics/ahp-score", json=payload, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_ahp_criteria_200(app, auth_headers):
    """GET /api/v2/analytics/ahp-criteria → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/analytics/ahp-criteria", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_win_probability_200(app, auth_headers):
    """GET /api/v2/analytics/win-probability → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(
            "/api/v2/analytics/win-probability?markup=15&n_competitors=5&cpv=45",
            headers=auth_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_cost_estimate_200(app, auth_headers):
    """POST /api/v2/analytics/cost-estimate → 200."""
    payload = {
        "cpv": "45",
        "region": "dolnośląskie",
        "area_m2": 1000.0,
        "value_estimated": 2000000.0,
        "description": "budowa drogi",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/analytics/cost-estimate", json=payload, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_recommendation_200(app, auth_headers):
    """POST /api/v2/analytics/recommendation → 200."""
    payload = {
        "cost_estimate": 750000.0,
        "n_competitors": 3,
        "cpv": "45",
        "region": "mazowieckie",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/analytics/recommendation", json=payload, headers=auth_headers)
    assert resp.status_code == 200
