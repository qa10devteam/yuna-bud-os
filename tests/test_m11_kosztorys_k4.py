"""Sprint K4 tests — Summary endpoint, from-tender, ATH export, ZWIAD integration."""
import sys, os, uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'db'))


@pytest.fixture()
def client():
    """TestClient with auth mocked."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.kosztorys_v2 import router as k_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(k_router)

    mock_user = CurrentUser(
        user_id="test-k4-user",
        email="test@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture()
def auth_headers():
    return {"Authorization": "Bearer test-token"}


class TestSummaryEndpoint:
    def test_summary_existing_kosztorys(self, client, auth_headers):
        """Create kosztorys, add pozycja, recalc, then get summary."""
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "Summary Test K4",
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]

        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "KNR", "opis": "Beton C25",
            "jednostka": "m3", "ilosc": 50,
            "r_jcena": 25.0, "m_jcena": 180.0, "s_jcena": 12.0,
        }, headers=auth_headers)
        client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == kid
        assert data["nazwa"] == "Summary Test K4"
        assert data["pozycje_count"] >= 1
        assert data["suma_netto"] > 0
        assert "narzuty" in data
        assert data["narzuty"]["ko_r_pct"] == 70.0

    def test_summary_nonexistent(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v2/kosztorys/{fake_id}/summary", headers=auth_headers)
        assert resp.status_code == 404


class TestAthExportFixed:
    def test_ath_export_returns_xml(self, client, auth_headers):
        """ATH export should now work with the @router.get decorator fix."""
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "ATH Export K4",
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]

        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "KNR 2-02",
            "opis": "Wykopy", "jednostka": "m3",
            "ilosc": 30, "r_jcena": 18.0, "m_jcena": 0.5, "s_jcena": 22.0,
        }, headers=auth_headers)
        client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/export-ath", headers=auth_headers)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "<?xml" in content or "<Kosztorys" in content


class TestFromTenderEndpoint:
    def test_from_tender_not_found(self, client, auth_headers):
        """Non-existent tender should 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/api/v2/kosztorys/from-tender/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_from_tender_creates(self, client, auth_headers):
        """If tender exists, creates kosztorys linked to it."""
        import sqlalchemy as sa
        from services.api.services.api.routers.kosztorys_v2 import get_engine

        # Check if we have any tenders
        with get_engine().connect() as conn:
            row = conn.execute(sa.text(
                "SELECT id FROM tender WHERE tenant_id = :tid LIMIT 1"
            ), {"tid": "ec3d1e16-2139-48c2-93b5-ffe0defd606d"}).first()

        if row is None:
            pytest.skip("No tenders in test DB")

        resp = client.post(f"/api/v2/kosztorys/from-tender/{row[0]}", headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tender_id"] == str(row[0])
        assert data["id"]


class TestPdfExportK4:
    def test_pdf_content_headers(self, client, auth_headers):
        """PDF export returns correct content-disposition."""
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "PDF K4",
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]

        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "", "opis": "Test",
            "jednostka": "szt", "ilosc": 1,
            "r_jcena": 10, "m_jcena": 5, "s_jcena": 2,
        }, headers=auth_headers)
        client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/export-pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert resp.content[:4] == b"%PDF"
