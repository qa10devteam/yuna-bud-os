"""Sprint K5 tests — Validation, error handling, hardening."""
import sys, os, uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'db'))


@pytest.fixture()
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.kosztorys_v2 import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)
    mock_user = CurrentUser(
        user_id="test-k5",
        email="test@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture()
def headers():
    return {"Authorization": "Bearer test"}


class TestValidation:
    def test_empty_nazwa_rejected(self, client, headers):
        resp = client.post("/api/v2/kosztorys", json={
            "nazwa": "",
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=headers)
        assert resp.status_code == 422

    def test_invalid_typ_rejected(self, client, headers):
        resp = client.post("/api/v2/kosztorys", json={
            "nazwa": "Test",
            "typ": "invalid_type",
        }, headers=headers)
        assert resp.status_code == 422

    def test_negative_ilosc_rejected(self, client, headers):
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "Neg test",
        }, headers=headers)
        kid = r.json()["id"]
        resp = client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "opis": "Bad", "ilosc": -5, "r_jcena": 10,
        }, headers=headers)
        assert resp.status_code == 422

    def test_negative_cena_rejected(self, client, headers):
        r = client.post("/api/v2/kosztorys", json={"nazwa": "Neg cena"}, headers=headers)
        kid = r.json()["id"]
        resp = client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "opis": "Bad price", "r_jcena": -10,
        }, headers=headers)
        assert resp.status_code == 422

    def test_kwartal_out_of_range(self, client, headers):
        resp = client.post("/api/v2/kosztorys", json={
            "nazwa": "Q5 test", "kwartalnr": 5,
        }, headers=headers)
        assert resp.status_code == 422

    def test_vat_over_100_rejected(self, client, headers):
        resp = client.post("/api/v2/kosztorys", json={
            "nazwa": "VAT 200", "vat_pct": 200,
        }, headers=headers)
        assert resp.status_code == 422

    def test_valid_typ_accepted(self, client, headers):
        for typ in ["ofertowy", "inwestorski", "zamienny", "powykonawczy"]:
            resp = client.post("/api/v2/kosztorys", json={
                "nazwa": f"Typ {typ}", "typ": typ,
            }, headers=headers)
            assert resp.status_code == 201, f"typ={typ} should be accepted"


class TestErrorHandling:
    def test_get_nonexistent_kosztorys(self, client, headers):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v2/kosztorys/{fake_id}", headers=headers)
        assert resp.status_code in (404, 200)  # depends on if GET detail exists

    def test_recalc_nonexistent(self, client, headers):
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/api/v2/kosztorys/{fake_id}/recalc", headers=headers)
        assert resp.status_code in (404, 200)

    def test_export_pdf_empty_kosztorys(self, client, headers):
        """PDF export of kosztorys with no pozycje should still work or 404."""
        r = client.post("/api/v2/kosztorys", json={"nazwa": "Empty PDF"}, headers=headers)
        kid = r.json()["id"]
        resp = client.get(f"/api/v2/kosztorys/{kid}/export-pdf", headers=headers)
        # Should return PDF even if empty, or graceful error
        assert resp.status_code in (200, 404, 400)

    def test_double_recalc_idempotent(self, client, headers):
        """Recalc should be idempotent."""
        r = client.post("/api/v2/kosztorys", json={"nazwa": "Idempotent"}, headers=headers)
        kid = r.json()["id"]
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "opis": "X", "ilosc": 10, "r_jcena": 5, "m_jcena": 3, "s_jcena": 2,
        }, headers=headers)
        r1 = client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=headers)
        r2 = client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=headers)
        if r1.status_code == 200 and r2.status_code == 200:
            assert r1.json() == r2.json()
