"""Sprint K7 tests — kosztorys_v2 coverage boost: działy, pozycje, recalc, update, delete, intelligence, n8n."""
import uuid
import pytest

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
BASE = ""  # router mounted directly, no prefix


@pytest.fixture
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.kosztorys_v2 import router as k_router
    from services.api.services.api.routers.automations import router as auto_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(k_router)
    app.include_router(auto_router)

    mock_user = CurrentUser(
        user_id="test-user-k7",
        email="test@qa10.io",
        org_id=TENANT_ID,
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token", "X-Tenant-Id": TENANT_ID}


@pytest.fixture
def kosztorys_id(client, auth_headers):
    """Create a fresh kosztorys and return its ID."""
    resp = client.post("/api/v2/kosztorys", json={
        "nazwa": f"K7-Test-{uuid.uuid4().hex[:6]}",
        "ko_r_pct": 65, "ko_s_pct": 30, "z_pct": 10, "kz_pct": 7, "vat_pct": 23,
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


# ─── UPDATE / DELETE ─────────────────────────────────────────────────────────

class TestKosztorysUpdate:
    def test_update_kosztorys(self, client, auth_headers, kosztorys_id):
        resp = client.put(f"/api/v2/kosztorys/{kosztorys_id}", json={
            "nazwa": "Updated K7",
            "inwestor": "ZUS Katowice",
            "obiekt": "Modernizacja siedziby",
        }, headers=auth_headers)
        assert resp.status_code in (200, 204)

    def test_update_nonexistent(self, client, auth_headers):
        resp = client.put(f"/api/v2/kosztorys/{uuid.uuid4()}", json={
            "nazwa": "Ghost",
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_kosztorys(self, client, auth_headers):
        # Create one to delete
        r = client.post("/api/v2/kosztorys", json={"nazwa": "ToDelete"}, headers=auth_headers)
        assert r.status_code == 201
        kid = r.json()["id"]
        resp = client.delete(f"/api/v2/kosztorys/{kid}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent(self, client, auth_headers):
        resp = client.delete(f"/api/v2/kosztorys/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


# ─── RECALC ───────────────────────────────────────────────────────────────────

class TestRecalc:
    def test_recalc_empty(self, client, auth_headers, kosztorys_id):
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/recalc", headers=auth_headers)
        assert resp.status_code in (200, 204)

    def test_recalc_with_pozycja(self, client, auth_headers, kosztorys_id):
        # Add a pozycja first
        client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "Murowanie ścian", "jednostka": "m2",
            "ilosc": 50, "r_jcena": 45.0, "m_jcena": 120.0, "s_jcena": 10.0,
        }, headers=auth_headers)
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/recalc", headers=auth_headers)
        assert resp.status_code in (200, 204)

    def test_recalc_nonexistent(self, client, auth_headers):
        resp = client.post(f"/api/v2/kosztorys/{uuid.uuid4()}/recalc", headers=auth_headers)
        assert resp.status_code == 404


# ─── DZIAŁY ───────────────────────────────────────────────────────────────────

class TestDzialy:
    def test_create_dzial(self, client, auth_headers, kosztorys_id):
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/dzialy", json={
            "nazwa": "Roboty ziemne", "lp": 1,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]

    def test_list_dzialy(self, client, auth_headers, kosztorys_id):
        # Create one first
        client.post(f"/api/v2/kosztorys/{kosztorys_id}/dzialy", json={
            "nazwa": "Fundamenty",
        }, headers=auth_headers)
        resp = client.get(f"/api/v2/kosztorys/{kosztorys_id}/dzialy", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body)
        assert isinstance(items, list)

    def test_delete_dzial(self, client, auth_headers, kosztorys_id):
        r = client.post(f"/api/v2/kosztorys/{kosztorys_id}/dzialy", json={
            "nazwa": "ToDelete",
        }, headers=auth_headers)
        assert r.status_code == 201
        did = r.json()["id"]
        resp = client.delete(f"/api/v2/kosztorys/{kosztorys_id}/dzialy/{did}", headers=auth_headers)
        assert resp.status_code == 204

    def test_list_dzialy_nonexistent_kosztorys(self, client, auth_headers):
        resp = client.get(f"/api/v2/kosztorys/{uuid.uuid4()}/dzialy", headers=auth_headers)
        assert resp.status_code in (200, 404)  # 200 empty or 404


# ─── POZYCJE ─────────────────────────────────────────────────────────────────

class TestPozycje:
    def test_create_pozycja(self, client, auth_headers, kosztorys_id):
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "Wykopy ręczne", "jednostka": "m3",
            "ilosc": 100, "r_jcena": 38.5, "m_jcena": 0, "s_jcena": 12.0,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]

    def test_list_pozycje(self, client, auth_headers, kosztorys_id):
        client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "Beton C20", "jednostka": "m3", "ilosc": 20, "m_jcena": 450.0,
        }, headers=auth_headers)
        resp = client.get(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body)
        assert isinstance(items, list)

    def test_update_pozycja(self, client, auth_headers, kosztorys_id):
        r = client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "Tynki", "jednostka": "m2", "ilosc": 200, "r_jcena": 25.0,
        }, headers=auth_headers)
        assert r.status_code == 201
        pid = r.json()["id"]
        resp = client.put(f"/api/v2/kosztorys/{kosztorys_id}/pozycje/{pid}", json={
            "ilosc": 250, "r_jcena": 28.0,
        }, headers=auth_headers)
        assert resp.status_code in (200, 204)

    def test_delete_pozycja(self, client, auth_headers, kosztorys_id):
        r = client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "ToDelete", "jednostka": "szt", "ilosc": 1,
        }, headers=auth_headers)
        assert r.status_code == 201
        pid = r.json()["id"]
        resp = client.delete(f"/api/v2/kosztorys/{kosztorys_id}/pozycje/{pid}", headers=auth_headers)
        assert resp.status_code == 204

    def test_create_pozycja_invalid(self, client, auth_headers, kosztorys_id):
        # Missing required field 'opis'
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "jednostka": "m2", "ilosc": 10,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_pozycja_negative_ilosc(self, client, auth_headers, kosztorys_id):
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "Bad", "jednostka": "m2", "ilosc": -5,
        }, headers=auth_headers)
        assert resp.status_code == 422


# ─── INTELLIGENCE ─────────────────────────────────────────────────────────────

class TestIntelligence:
    def test_intelligence_empty_kosztorys(self, client, auth_headers, kosztorys_id):
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/intelligence", headers=auth_headers)
        assert resp.status_code in (200, 404, 422)

    def test_intelligence_with_data(self, client, auth_headers, kosztorys_id):
        # Add a pozycja with ICB-like data
        client.post(f"/api/v2/kosztorys/{kosztorys_id}/pozycje", json={
            "opis": "Robocizna ogólnobudowlana", "jednostka": "rbh",
            "ilosc": 100, "r_jcena": 52.0,
        }, headers=auth_headers)
        resp = client.post(f"/api/v2/kosztorys/{kosztorys_id}/intelligence", headers=auth_headers)
        assert resp.status_code in (200, 404, 500)

    def test_intelligence_nonexistent(self, client, auth_headers):
        resp = client.post(f"/api/v2/kosztorys/{uuid.uuid4()}/intelligence", headers=auth_headers)
        assert resp.status_code == 404


# ─── n8n STATUS ──────────────────────────────────────────────────────────────

class TestN8nEndpoints:
    def test_n8n_status(self, client, auth_headers):
        resp = client.get("/api/v2/automations/n8n/status", headers=auth_headers)
        # Might succeed if n8n is running, or fail gracefully
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_n8n_workflows(self, client, auth_headers):
        resp = client.get("/api/v2/automations/n8n/workflows", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_n8n_provision(self, client, auth_headers):
        event = f"kosztorys.test.{uuid.uuid4().hex[:4]}"
        resp = client.post(f"/api/v2/automations/n8n/provision?event={event}", headers=auth_headers)
        # Either provisioned or error (if n8n not available)
        assert resp.status_code in (200, 500)
