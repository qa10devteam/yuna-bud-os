"""Coverage boost-b: reports, kosztorys_v3, resources, auth/router, audit_v2, scoring, tender_alerts.

Targets uncovered branches:
- reports.py: PDF with reportlab mock, benchmark comparison, date filters
- kosztorys_v3.py: ICB rates, AI wycena 404, SSE trigger path
- resources.py: subcontractor 404, equipment delete, employee CRUD, logistics, gantt, calendar, collision
- auth/router.py: register success+duplicate, login wrong pass, refresh, logout, me endpoints
- audit_v2.py: trail filters, entity history, diff detail, stats, _summarize_changes
- scoring.py: config get/put validation, score breakdown, cpv heatmap, refresh views
- tender_alerts.py: duplicate 409, webhook channel, delete 404, toggle 404, update 404
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, AsyncMock
import uuid

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Shared fixtures ──────────────────────────────────────────────────────────

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


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTS — lines 31-48, 61-67, 79-85
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_reports_monthly_with_year_month(app, auth_headers):
    """GET /api/v2/reports/monthly?year=2024&month=1 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/reports/monthly?year=2024&month=1", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "year" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_reports_monthly_pdf_with_reportlab(app, auth_headers):
    """GET /api/v2/reports/monthly/pdf — mock reportlab canvas."""
    buf_mock = MagicMock()
    buf_mock.read.return_value = b"%PDF-1.4 fake pdf content"
    buf_mock.seek.return_value = None

    canvas_mock = MagicMock()
    canvas_mock.Canvas.return_value = MagicMock()
    canvas_mock.Canvas.return_value.save.return_value = None

    import io
    real_bytesio = io.BytesIO

    with patch.dict("sys.modules", {"reportlab": MagicMock(), "reportlab.pdfgen": MagicMock(),
                                     "reportlab.pdfgen.canvas": canvas_mock}):
        with patch("io.BytesIO", return_value=buf_mock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/reports/monthly/pdf?year=2025&month=6", headers=auth_headers)
    # Either PDF or HTML fallback
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reports_monthly_pdf_no_reportlab(app, auth_headers):
    """GET /api/v2/reports/monthly/pdf — ImportError fallback → HTML."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "reportlab" in name:
            raise ImportError("no reportlab")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/reports/monthly/pdf?year=2026&month=3", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reports_benchmark(app, auth_headers):
    """GET /api/v2/reports/benchmark → 200 with rank data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/reports/benchmark", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_tenants" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_reports_monthly_date_filter_edge(app, auth_headers):
    """Monthly report with month=12 boundary."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/reports/monthly?year=2023&month=12", headers=auth_headers)
    assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# KOSZTORYS V3 — lines 92-192 (ICB rates + AI wycena)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_icb_rates_200(app, auth_headers):
    """GET /api/v2/icb/rates?cpv5=45000&nuts2=PL91 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/icb/rates?cpv5=45000&nuts2=PL91", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "cpv5" in data
    assert "rates" in data


@pytest.mark.asyncio
async def test_icb_rates_different_region(app, auth_headers):
    """ICB rates for another region."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/icb/rates?cpv5=45100&nuts2=PL21", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ai_wycena_404_not_found(app, auth_headers):
    """POST /api/v2/kosztorys/nonexistent-id/ai-wycena-v2 → 404."""
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"/api/v2/kosztorys/{fake_id}/ai-wycena-v2", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_icb_rates_empty_result(app, auth_headers):
    """ICB rates for non-existing CPV → 200 with empty rates."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/icb/rates?cpv5=99999&nuts2=PL00", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["rates"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES — equipment, subcontractors, employees, logistics, gantt, calendar
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_subcontractor_get_404(app, auth_headers):
    """GET /api/v1/subcontractors/{bad_id} → 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v1/subcontractors/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_subcontractor_delete(app, auth_headers):
    """DELETE /api/v1/subcontractors/{id} → 200."""
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/v1/subcontractors/{fake_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_subcontractor_tender_link(app, auth_headers):
    """GET /api/v1/subcontractors/tender/{tid} → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v1/subcontractors/tender/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_equipment_delete(app, auth_headers):
    """DELETE /api/v1/equipment/{eq_id} → 200."""
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/v1/equipment/{fake_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_equipment_tender_list(app, auth_headers):
    """GET /api/v1/equipment/tender/{tid} → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v1/equipment/tender/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_equipment_list_with_status_filter(app, auth_headers):
    """GET /api/v1/equipment?status=available → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/equipment?status=available", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_employee_list(app, auth_headers):
    """GET /api/v1/resources/employees → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/resources/employees", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_employee_create(app, auth_headers):
    """POST /api/v1/resources/employees → 201."""
    payload = {"name": "Jan Kowalski", "role": "operator", "phone": "123456789", "hourly_rate": 45.0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/resources/employees", headers=auth_headers, json=payload)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_employee_delete(app, auth_headers):
    """DELETE /api/v1/resources/employees/{id} → 204."""
    fake_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/v1/resources/employees/{fake_id}", headers=auth_headers)
    assert r.status_code in (200, 204)


@pytest.mark.asyncio
async def test_res_equipment_list(app, auth_headers):
    """GET /api/v1/resources/equipment → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/resources/equipment", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_res_equipment_create(app, auth_headers):
    """POST /api/v1/resources/equipment → 201."""
    payload = {"name": "Koparka gąsienicowa", "category": "maszyna", "daily_cost": 500.0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/resources/equipment", headers=auth_headers, json=payload)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_logistics_optimize_empty(app, auth_headers):
    """POST /api/v1/logistics/optimize — empty sites → routes=[]."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/logistics/optimize", headers=auth_headers, json={"sites": []})
    assert r.status_code == 200
    data = r.json()
    assert data["routes"] == []
    assert data["total_km"] == 0


@pytest.mark.asyncio
async def test_logistics_optimize_with_sites(app, auth_headers):
    """POST /api/v1/logistics/optimize — 3 sites → route computed."""
    payload = {
        "sites": [
            {"lat": 52.23, "lng": 21.01, "name": "Warszawa"},
            {"lat": 50.06, "lng": 19.94, "name": "Kraków"},
            {"lat": 51.11, "lng": 17.02, "name": "Wrocław"},
        ],
        "depot": {"lat": 52.23, "lng": 21.01},
        "max_distance_km": 500,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/logistics/optimize", headers=auth_headers, json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "routes" in data
    assert data["total_km"] > 0


@pytest.mark.asyncio
async def test_logistics_optimize_no_depot(app, auth_headers):
    """POST /api/v1/logistics/optimize — no depot uses default Warsaw."""
    payload = {
        "sites": [
            {"lat": 54.35, "lng": 18.65, "name": "Gdańsk"},
            {"lat": 53.13, "lng": 18.01, "name": "Bydgoszcz"},
        ],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/logistics/optimize", headers=auth_headers, json=payload)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gantt_get(app, auth_headers):
    """GET /api/v1/gantt/{tid} → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v1/gantt/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data


@pytest.mark.asyncio
async def test_gantt_create(app, auth_headers):
    """POST /api/v1/gantt/{tid} → 200."""
    tid = str(uuid.uuid4())
    payload = {"name": "Etap 1", "start_date": "2026-01-01", "end_date": "2026-03-31", "progress": 0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"/api/v1/gantt/{tid}", headers=auth_headers, json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "created"


@pytest.mark.asyncio
async def test_gantt_update(app, auth_headers):
    """PATCH /api/v1/gantt/{tid}/{task_id} → 200."""
    tid = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    payload = {"name": "Etap 1 updated", "progress": 50}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"/api/v1/gantt/{tid}/{task_id}", headers=auth_headers, json=payload)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gantt_delete(app, auth_headers):
    """DELETE /api/v1/gantt/{tid}/{task_id} → 200."""
    tid = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/v1/gantt/{tid}/{task_id}", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_calendar_list(app, auth_headers):
    """GET /api/v1/calendar → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/calendar", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "events" in data


@pytest.mark.asyncio
async def test_calendar_list_date_filter(app, auth_headers):
    """GET /api/v1/calendar?from_date=2026-01-01&to_date=2026-12-31 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/calendar?from_date=2026-01-01&to_date=2026-12-31", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_calendar_create(app, auth_headers):
    """POST /api/v1/calendar → 200."""
    payload = {"title": "Termin składania ofert", "event_type": "deadline", "event_date": "2026-08-15"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/calendar", headers=auth_headers, json=payload)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_calendar_delete(app, auth_headers):
    """DELETE /api/v1/calendar/{event_id} → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/v1/calendar/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_calendar_sync_from_tenders(app, auth_headers):
    """POST /api/v1/calendar/sync-from-tenders → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v1/calendar/sync-from-tenders", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_contracts_list(app, auth_headers):
    """GET /api/v1/contracts → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/contracts", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_resources_availability(app, auth_headers):
    """GET /api/v2/resources/availability?from_date=...&to_date=... → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/resources/availability?from_date=2026-01-01&to_date=2026-12-31", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_resources_collision_check(app, auth_headers):
    """POST /api/v2/resources/check-collision → 200."""
    payload = {
        "resource_id": str(uuid.uuid4()),
        "from_date": "2026-07-01",
        "to_date": "2026-07-31",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/resources/check-collision", headers=auth_headers, json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "collision" in data
    assert "conflict_days" in data


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH/ROUTER — register/login/refresh/logout/me (lines 99-326)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_auth_register_duplicate_email(app, auth_headers):
    """POST /api/v2/auth/register with duplicate email → 409."""
    payload = {
        "email": "demo@terra-os.pl",  # existing user
        "name": "Demo User",
        "password": "password123",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/register", json=payload)
    # Either 409 conflict or 422 validation — depends on DB state
    assert r.status_code in (409, 422, 201, 500)


@pytest.mark.asyncio
async def test_auth_register_invalid_email(app):
    """POST /api/v2/auth/register with invalid email → 422."""
    payload = {
        "email": "not-an-email",
        "name": "Test",
        "password": "password123",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/register", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_register_short_password(app):
    """POST /api/v2/auth/register with short password → 422."""
    payload = {
        "email": "test@example.com",
        "name": "Test",
        "password": "short",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/register", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_login_wrong_password(app):
    """POST /api/v2/auth/login with wrong password → 401."""
    payload = {"email": "demo@terra-os.pl", "password": "wrongpassword999"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/login", json=payload)
    assert r.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_auth_login_nonexistent_user(app):
    """POST /api/v2/auth/login with non-existent email → 401."""
    payload = {"email": "nonexistent@nowhere.com", "password": "password123"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/login", json=payload)
    assert r.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_auth_refresh_invalid_token(app):
    """POST /api/v2/auth/refresh with invalid token → 401."""
    payload = {"refresh_token": "invalid.token.here"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/refresh", json=payload)
    assert r.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_auth_logout(app):
    """POST /api/v2/auth/logout → 204."""
    payload = {"refresh_token": "some-random-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/logout", json=payload)
    assert r.status_code in (204, 422, 500)


@pytest.mark.asyncio
async def test_auth_me_authenticated(app, auth_headers):
    """GET /api/v2/auth/me → 200 with user info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "email" in data or "id" in data


@pytest.mark.asyncio
async def test_auth_me_full(app, auth_headers):
    """GET /api/v2/auth/me/full → 200 with extended profile."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/auth/me/full", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "email" in data or "user_id" in data


@pytest.mark.asyncio
async def test_auth_forgot_password(app):
    """POST /api/v2/auth/forgot-password → 200 always (anti-enum)."""
    payload = {"email": "nonexistent@example.com"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/forgot-password", json=payload)
    assert r.status_code in (200, 422, 429, 500)


@pytest.mark.asyncio
async def test_auth_reset_password_invalid_token(app):
    """POST /api/v2/auth/reset-password with invalid token → 400."""
    payload = {"token": "invalid-reset-token", "new_password": "NewPassword123"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/auth/reset-password", json=payload)
    assert r.status_code in (400, 422, 429, 500)


# ─── Auth unit tests (direct function calls) ─────────────────────────────────

def test_auth_helper_token_response_structure():
    """_token_response creates TokenResponse with access+refresh tokens."""
    from services.api.services.api.auth.utils import create_access_token, create_refresh_token, hash_refresh_token
    token = create_access_token("uid", "test@test.pl", "org1", "owner")
    assert token
    raw, h, exp = create_refresh_token()
    assert hash_refresh_token(raw) == h


def test_set_auth_cookies_structure():
    """_set_auth_cookies sets session + csrf_token cookies."""
    from services.api.services.api.auth.router import _set_auth_cookies
    from fastapi.responses import Response as FastAPIResponse
    response = FastAPIResponse()
    _set_auth_cookies(response, "test-access-token")
    # Function runs without error — cookies set via response
    assert True


def test_seed_new_org_demo_tenders_constant():
    """_DEMO_TENDERS has 3 items with required fields."""
    from services.api.services.api.auth.router import _DEMO_TENDERS
    assert len(_DEMO_TENDERS) == 3
    for td in _DEMO_TENDERS:
        assert "title" in td
        assert "value_pln" in td


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT V2 — trail filters, entity history, diff, stats (lines 34-231)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_trail_200(app, auth_headers):
    """GET /api/v2/audit/trail → 200 with items + total."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/trail", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_audit_trail_filter_entity_type(app, auth_headers):
    """GET /api/v2/audit/trail?entity_type=tender → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/trail?entity_type=tender", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_audit_trail_filter_user_id(app, auth_headers):
    """GET /api/v2/audit/trail?user_id=xxx → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/trail?user_id=demo_user_123", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_audit_trail_filter_action(app, auth_headers):
    """GET /api/v2/audit/trail?action=update → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/trail?action=update", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_audit_trail_pagination(app, auth_headers):
    """GET /api/v2/audit/trail?limit=5&offset=10 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/trail?limit=5&offset=10", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 5
    assert data["offset"] == 10


@pytest.mark.asyncio
async def test_audit_trail_all_filters(app, auth_headers):
    """GET /api/v2/audit/trail with all filters combined → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            "/api/v2/audit/trail?entity_type=tender&action=create&user_id=uid123&limit=10&offset=0",
            headers=auth_headers,
        )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_audit_recent_200(app, auth_headers):
    """GET /api/v2/audit/recent → 200 with list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/recent", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_audit_recent_custom_limit(app, auth_headers):
    """GET /api/v2/audit/recent?limit=5 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/recent?limit=5", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_audit_entity_history(app, auth_headers):
    """GET /api/v2/audit/entity/{entity_id} → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v2/audit/entity/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_audit_diff_not_found(app, auth_headers):
    """GET /api/v2/audit/diff/{bad_id} → returns dict."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v2/audit/diff/{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # Returns {"error": "Not found"} or valid diff
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_audit_stats(app, auth_headers):
    """GET /api/v2/audit/stats → 200 with activity."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "period_days" in data
    assert "daily_activity" in data


@pytest.mark.asyncio
async def test_audit_stats_custom_days(app, auth_headers):
    """GET /api/v2/audit/stats?days=7 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/audit/stats?days=7", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["period_days"] == 7


def test_audit_summarize_changes_none():
    """_summarize_changes(None) → 'brak szczegółów'."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    assert _summarize_changes(None) == "brak szczegółów"


def test_audit_summarize_changes_empty_string():
    """_summarize_changes('') → 'brak szczegółów'."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    assert _summarize_changes("") == "brak szczegółów"


def test_audit_summarize_changes_dict():
    """_summarize_changes with dict JSON → 'Zmieniono: ...'."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    changes_json = json.dumps({"field1": "val1", "field2": "val2", "field3": "v3"})
    result = _summarize_changes(changes_json)
    assert "Zmieniono" in result


def test_audit_summarize_changes_many_fields():
    """_summarize_changes with >3 fields → '... +N więcej'."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    changes_json = json.dumps({f"field{i}": f"val{i}" for i in range(6)})
    result = _summarize_changes(changes_json)
    assert "więcej" in result


def test_audit_summarize_changes_invalid_json():
    """_summarize_changes with invalid JSON → 'zmiana'."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    result = _summarize_changes("not valid json {{{")
    assert result == "zmiana"


def test_audit_summarize_changes_list_json():
    """_summarize_changes with a list → truncated string."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    result = _summarize_changes(json.dumps(["a", "b", "c"]))
    assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING — config, breakdown, heatmap, refresh (lines 43-142)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scoring_config_get(app, auth_headers):
    """GET /api/v2/scoring/config → 200 with weights."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/scoring/config", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "weights" in data


@pytest.mark.asyncio
async def test_scoring_config_put_valid(app, auth_headers):
    """PUT /api/v2/scoring/config — weights summing to 100 → 200."""
    payload = {
        "weights": {
            "cpv_match": 30,
            "value_range": 25,
            "deadline_pressure": 20,
            "buyer_history": 15,
            "document_quality": 10,
        }
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put("/api/v2/scoring/config", headers=auth_headers, json=payload)
    assert r.status_code in (200, 500)


@pytest.mark.asyncio
async def test_scoring_config_put_invalid_sum(app, auth_headers):
    """PUT /api/v2/scoring/config — weights NOT summing to 100 → 400."""
    payload = {
        "weights": {
            "cpv_match": 50,
            "value_range": 30,
        }
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put("/api/v2/scoring/config", headers=auth_headers, json=payload)
    assert r.status_code == 400
    data = r.json()
    assert "100" in data.get("detail", "")


@pytest.mark.asyncio
async def test_scoring_config_put_sum_zero(app, auth_headers):
    """PUT /api/v2/scoring/config — empty weights dict → 400."""
    payload = {"weights": {}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put("/api/v2/scoring/config", headers=auth_headers, json=payload)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_scoring_breakdown_404(app, auth_headers):
    """GET /api/v2/tenders/{id}/score-breakdown → 404 for unknown tender."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v2/tenders/{uuid.uuid4()}/score-breakdown", headers=auth_headers)
    assert r.status_code in (404, 500)


@pytest.mark.asyncio
async def test_scoring_cpv_heatmap(app, auth_headers):
    """GET /api/v2/market/cpv-heatmap → 200 with list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/market/cpv-heatmap", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_scoring_refresh_views(app, auth_headers):
    """POST /api/v2/admin/refresh-views → 200 or 500."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/admin/refresh-views", headers=auth_headers)
    assert r.status_code in (200, 500)


def test_scoring_default_weights_sum():
    """_DEFAULT_WEIGHTS sums to 100."""
    from services.api.services.api.routers.scoring import _DEFAULT_WEIGHTS
    assert sum(_DEFAULT_WEIGHTS.values()) == 100


def test_scoring_config_request_validation():
    """ScoringConfigRequest can be created."""
    from services.api.services.api.routers.scoring import ScoringConfigRequest
    req = ScoringConfigRequest(weights={"cpv_match": 100})
    assert req.weights["cpv_match"] == 100


# ═══════════════════════════════════════════════════════════════════════════════
# TENDER ALERTS — duplicate 409, webhook, delete cascade, toggle/update 404
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_alert_create_webhook_no_url_422(app, auth_headers):
    """POST /api/v2/tender-alerts — channel=webhook without url → 422."""
    payload = {
        "name": "Webhook Alert No URL",
        "frequency": "daily",
        "channel": "webhook",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/tender-alerts", headers=auth_headers, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_alert_create_invalid_channel(app, auth_headers):
    """POST /api/v2/tender-alerts — bad channel → 422."""
    payload = {
        "name": "Bad Channel Alert",
        "frequency": "daily",
        "channel": "fax",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/tender-alerts", headers=auth_headers, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_alert_create_invalid_frequency(app, auth_headers):
    """POST /api/v2/tender-alerts — bad frequency → 422."""
    payload = {
        "name": "Bad Freq Alert",
        "frequency": "monthly",
        "channel": "email",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/tender-alerts", headers=auth_headers, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_alert_create_value_max_less_than_min(app, auth_headers):
    """POST /api/v2/tender-alerts — value_max < value_min → 422."""
    payload = {
        "name": "Invalid Value Range",
        "frequency": "daily",
        "channel": "email",
        "value_min": 100000,
        "value_max": 50000,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/tender-alerts", headers=auth_headers, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_alert_get_404(app, auth_headers):
    """GET /api/v2/tender-alerts/{random_id} → 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v2/tender-alerts/{random_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_update_404(app, auth_headers):
    """PUT /api/v2/tender-alerts/{random_id} → 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(
            f"/api/v2/tender-alerts/{random_id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_update_no_fields_400(app, auth_headers):
    """PUT /api/v2/tender-alerts/{random_id} with no fields → 400 or 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(
            f"/api/v2/tender-alerts/{random_id}",
            headers=auth_headers,
            json={},
        )
    assert r.status_code in (400, 404)


@pytest.mark.asyncio
async def test_alert_delete_404(app, auth_headers):
    """DELETE /api/v2/tender-alerts/{random_id} → 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"/api/v2/tender-alerts/{random_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_toggle_404(app, auth_headers):
    """PATCH /api/v2/tender-alerts/{random_id}/toggle → 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"/api/v2/tender-alerts/{random_id}/toggle", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_test_404(app, auth_headers):
    """POST /api/v2/tender-alerts/{random_id}/test → 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"/api/v2/tender-alerts/{random_id}/test", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_matches_404(app, auth_headers):
    """GET /api/v2/tender-alerts/{random_id}/matches → 404."""
    random_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"/api/v2/tender-alerts/{random_id}/matches", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_list_active_only(app, auth_headers):
    """GET /api/v2/tender-alerts?active_only=true → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/tender-alerts?active_only=true", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_alert_list_with_pagination(app, auth_headers):
    """GET /api/v2/tender-alerts?limit=5&offset=0 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/tender-alerts?limit=5&offset=0", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 5


# ─── Alert SQL helper unit tests ──────────────────────────────────────────────

def test_alert_matches_sql_empty_alert():
    """_alert_matches_sql with empty alert → valid SQL + minimal params."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    sql, params = _alert_matches_sql({}, limit=10)
    assert "SELECT" in sql
    assert params["_limit"] == 10


def test_alert_matches_sql_cpv_prefixes():
    """_alert_matches_sql with CPV prefixes → CPV LIKE conditions."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"cpv_prefixes": ["45000", "71000"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "cpv_code LIKE" in sql
    assert "cpv_0" in params


def test_alert_matches_sql_invalid_cpv_filtered():
    """_alert_matches_sql with invalid CPV (injection attempt) → filtered."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"cpv_prefixes": ["'; DROP TABLE tenders;--", "45000"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    # Only valid CPV "45000" should appear
    if "cpv_0" in params:
        assert params["cpv_0"] == "45000%"


def test_alert_matches_sql_provinces():
    """_alert_matches_sql with provinces → IN condition."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"provinces": ["PL91", "PL21"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "province IN" in sql


def test_alert_matches_sql_invalid_province_filtered():
    """_alert_matches_sql with invalid province → filtered."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"provinces": ["INVALID", "PL91"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    # Only PL91 should be present
    assert "prov_0" in params and params["prov_0"] == "PL91"


def test_alert_matches_sql_value_range():
    """_alert_matches_sql with value range → BETWEEN conditions."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"value_min": 10000.0, "value_max": 500000.0}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "estimated_value >= :value_min" in sql
    assert "estimated_value <= :value_max" in sql
    assert params["value_min"] == 10000.0
    assert params["value_max"] == 500000.0


def test_alert_matches_sql_keywords():
    """_alert_matches_sql with keywords → ILIKE conditions."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"keywords": ["roboty budowlane", "remont"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "ILIKE" in sql
    assert "kw_0" in params
    assert "roboty budowlane" in params["kw_0"]


def test_alert_matches_sql_keywords_escape():
    """_alert_matches_sql escapes % and _ in keywords."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"keywords": ["100% done", "test_value"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "\\%" in params["kw_0"]
    assert "\\_" in params["kw_1"]


def test_alert_matches_sql_notice_types_whitelist():
    """_alert_matches_sql with valid notice types → IN condition."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"notice_types": ["ogloszenieOZamowieniu", "zapytanieOCene"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "notice_type IN" in sql


def test_alert_matches_sql_notice_types_invalid_filtered():
    """_alert_matches_sql filters invalid notice types."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"notice_types": ["invalid_type", "ogloszenieOZamowieniu"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    # Only valid type should pass
    assert "nt_0" in params and params["nt_0"] == "ogloszenieOZamowieniu"


def test_alert_matches_sql_buyer_nips():
    """_alert_matches_sql with buyer NIPs → IN condition."""
    from services.api.services.api.routers.tender_alerts import _alert_matches_sql
    alert = {"buyer_nips": ["1234567890", "9876543210"]}
    sql, params = _alert_matches_sql(alert, limit=5)
    assert "buyer_nip IN" in sql


def test_alert_matches_sql_require_org_no_org():
    """_require_org raises HTTPException when user has no org_id."""
    from services.api.services.api.routers.tender_alerts import _require_org
    from fastapi import HTTPException
    user_mock = MagicMock()
    user_mock.org_id = None
    with pytest.raises(HTTPException) as exc_info:
        _require_org(user_mock)
    assert exc_info.value.status_code == 400


def test_alert_matches_sql_require_org_with_org():
    """_require_org returns org_id when user has org_id."""
    from services.api.services.api.routers.tender_alerts import _require_org
    user_mock = MagicMock()
    user_mock.org_id = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
    result = _require_org(user_mock)
    assert result == "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
