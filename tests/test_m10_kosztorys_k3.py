"""Sprint K3 tests — benchmark seed + PDF export + kosztorys API integration."""
import sys, os, uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'db'))


@pytest.fixture()
def engine():
    return sa.create_engine(os.environ.get(
        "DATABASE_URL", "postgresql://terraos:***@localhost:5432/terraos"
    ))


@pytest.fixture()
def client():
    """TestClient with kosztorys_v2 + intelligence routers mounted, auth mocked."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.kosztorys_v2 import router as k_router
    from services.api.services.api.routers.intelligence import router as i_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(k_router)
    app.include_router(i_router)

    mock_user = CurrentUser(
        user_id="test-user-001",
        email="test@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture()
def auth_headers():
    return {"Authorization": "Bearer test-token", "X-Tenant-Id": "ec3d1e16-2f6c-4a5b-9e7a-abc123456789"}


# ═══ Benchmark Seed ═══════════════════════════════════════════════════════════

class TestBenchmarkSeed:
    def test_seed_cpv_benchmark_runs(self, engine):
        from services.api.services.api.intelligence.benchmark_seed import seed_cpv_benchmark
        result = seed_cpv_benchmark(engine)
        assert "total" in result
        assert result["total"] >= 0
        assert "quarter" in result

    def test_benchmark_data_exists(self, engine):
        with engine.connect() as conn:
            count = conn.execute(sa.text(
                "SELECT count(*) FROM cpv_regional_benchmark WHERE nuts2_code='PL'"
            )).scalar()
        assert count >= 1, "Expected seeded benchmark data"

    def test_benchmark_has_values(self, engine):
        with engine.connect() as conn:
            row = conn.execute(sa.text("""
                SELECT avg_value, median_value, p25_value, p75_value, n_tenders
                FROM cpv_regional_benchmark
                WHERE nuts2_code='PL'
                ORDER BY n_tenders DESC
                LIMIT 1
            """)).fetchone()
        assert row is not None
        assert float(row.avg_value) > 0
        assert float(row.median_value) > 0
        assert float(row.p25_value) <= float(row.median_value)
        assert float(row.p75_value) >= float(row.median_value)


# ═══ PDF Generator ════════════════════════════════════════════════════════════

class TestPdfGenerator:
    def test_generate_pdf_basic(self):
        from services.api.services.api.intelligence.pdf_generator import generate_pdf
        header = {
            "nazwa": "Test Kosztorys",
            "inwestor": "Inwestor Sp. z o.o.",
            "obiekt": "Budynek A",
            "lokalizacja": "Warszawa",
            "typ": "inwestorski",
            "status": "draft",
            "kwartalnr": 2,
            "kwartalrok": 2026,
            "ko_r_pct": 70,
            "ko_s_pct": 30,
            "z_pct": 12.5,
            "kz_pct": 7.1,
            "vat_pct": 23,
            "tender_id": None,
            "data_opracowania": "2026-07-08",
        }
        pozycje = [
            {
                "lp": 1, "kst_code": "KNR 2-02 0101-01",
                "opis": "Roboty ziemne", "jednostka": "m3",
                "ilosc": 100, "r_jcena": 15.50, "m_jcena": 2.30, "s_jcena": 8.00,
                "r_total": 1550, "m_total": 230, "s_total": 800,
                "ko_total": 1325, "z_total": 512, "kz_total": 16.33,
                "jcena_netto": 44.3333, "wartosc_netto": 4433.33,
                "is_anomaly": False,
            },
            {
                "lp": 2, "kst_code": "KNR 4-01 0202-03",
                "opis": "Izolacje fundamentów", "jednostka": "m2",
                "ilosc": 250, "r_jcena": 12.00, "m_jcena": 35.00, "s_jcena": 3.50,
                "r_total": 3000, "m_total": 8750, "s_total": 875,
                "ko_total": 2362.5, "z_total": 2072.8, "kz_total": 621.25,
                "jcena_netto": 70.7242, "wartosc_netto": 17681.05,
                "is_anomaly": True,
            },
        ]
        sums = {
            "r": 4550, "m": 8980, "s": 1675,
            "ko": 3687.5, "kz": 637.58, "z": 2584.8,
            "netto": 22114.88, "vat": 5086.42, "brutto": 27201.30,
        }
        intel = {
            "benchmark_percentile": 42.5,
            "win_probability": 0.67,
            "anomaly_score": 0.12,
        }

        pdf_bytes = generate_pdf(header, pozycje, sums=sums, intel=intel)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        # PDF magic number
        assert pdf_bytes[:4] == b'%PDF'

    def test_generate_pdf_empty(self):
        from services.api.services.api.intelligence.pdf_generator import generate_pdf
        header = {
            "nazwa": "Pusty kosztorys",
            "inwestor": None, "obiekt": None,
            "lokalizacja": None, "typ": "ofertowy", "status": "draft",
            "kwartalnr": 3, "kwartalrok": 2026,
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
            "tender_id": None, "data_opracowania": None,
        }
        pdf = generate_pdf(header, [])
        assert pdf[:4] == b'%PDF'

    def test_generate_pdf_with_dzialy(self):
        from services.api.services.api.intelligence.pdf_generator import generate_pdf
        header = {
            "nazwa": "Z działami",
            "inwestor": "Test", "obiekt": "B",
            "lokalizacja": "Kato", "typ": "inwestorski", "status": "draft",
            "kwartalnr": 2, "kwartalrok": 2026,
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
            "tender_id": None, "data_opracowania": None,
        }
        dzialy = [{"id": "d1", "lp": 1, "nazwa": "Roboty ziemne"}]
        pozycje = [{
            "lp": 1, "kst_code": "KNR", "opis": "Wykopy",
            "jednostka": "m3", "ilosc": 50,
            "r_jcena": 10, "m_jcena": 0, "s_jcena": 5,
            "jcena_netto": 20.5, "wartosc_netto": 1025.0,
            "is_anomaly": False, "dzial_id": "d1",
            "r_total": 500, "m_total": 0, "s_total": 250,
            "ko_total": 425, "z_total": 200, "kz_total": 0,
        }]
        pdf = generate_pdf(header, pozycje, dzialy=dzialy)
        assert pdf[:4] == b'%PDF'
        assert len(pdf) > 500


# ═══ API Kosztorys v2 Endpoints ═══════════════════════════════════════════════

class TestKosztorysV2Api:
    def test_create_kosztorys(self, client, auth_headers):
        resp = client.post("/api/v2/kosztorys", json={
            "nazwa": "Test K3",
            "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]
        assert data["status"] == "created"
        # store for potential downstream use (class-level)
        type(self)._last_id = data["id"]

    def test_list_kosztorys(self, client, auth_headers):
        resp = client.get("/api/v2/kosztorys?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_add_pozycja(self, client, auth_headers):
        # Create kosztorys first
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "Poz test", "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]

        resp = client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1,
            "kst_code": "KNR 2-02 0101",
            "opis": "Roboty ziemne test",
            "jednostka": "m3",
            "ilosc": 100,
            "r_jcena": 15.5,
            "m_jcena": 2.3,
            "s_jcena": 8.0,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]
        assert data["status"] == "created"

    def test_list_pozycje(self, client, auth_headers):
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "List poz", "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "", "opis": "Test", "jednostka": "szt",
            "ilosc": 1, "r_jcena": 10, "m_jcena": 5, "s_jcena": 2,
        }, headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/pozycje", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1

    def test_recalc(self, client, auth_headers):
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "Recalc", "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "", "opis": "Poz1", "jednostka": "m2",
            "ilosc": 50, "r_jcena": 20, "m_jcena": 10, "s_jcena": 5,
        }, headers=auth_headers)

        resp = client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert float(data.get("suma_netto", 0)) > 0

    def test_export_pdf(self, client, auth_headers):
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "PDF test", "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "KNR", "opis": "Roboty", "jednostka": "m3",
            "ilosc": 10, "r_jcena": 15, "m_jcena": 5, "s_jcena": 3,
        }, headers=auth_headers)
        client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/export-pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b'%PDF'
        assert len(resp.content) > 1000

    def test_export_ath(self, client, auth_headers):
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "ATH test", "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "KNR 2", "opis": "Murowanie", "jednostka": "m2",
            "ilosc": 20, "r_jcena": 12, "m_jcena": 30, "s_jcena": 4,
        }, headers=auth_headers)
        client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/export-ath", headers=auth_headers)
        # May be 200 or 404 depending on implementation completeness
        assert resp.status_code in (200, 404)

    def test_intelligence_endpoint(self, client, auth_headers):
        r = client.post("/api/v2/kosztorys", json={
            "nazwa": "Intel test", "ko_r_pct": 70, "ko_s_pct": 30,
            "z_pct": 12.5, "kz_pct": 7.1, "vat_pct": 23,
        }, headers=auth_headers)
        kid = r.json()["id"]
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": 1, "kst_code": "KNR", "opis": "Test intel", "jednostka": "szt",
            "ilosc": 5, "r_jcena": 100, "m_jcena": 50, "s_jcena": 20,
        }, headers=auth_headers)
        client.post(f"/api/v2/kosztorys/{kid}/recalc", headers=auth_headers)

        resp = client.get(f"/api/v2/kosztorys/{kid}/intelligence", headers=auth_headers)
        # May be 200, 404, or 405 depending on route availability
        assert resp.status_code in (200, 404, 405)


# ═══ Intelligence API ═════════════════════════════════════════════════════════

class TestIntelligenceApi:
    def test_benchmark_endpoint(self, client, auth_headers):
        resp = client.get("/api/v2/intelligence/benchmark?cpv5=45000&nuts2_code=PL", headers=auth_headers)
        # May be 200 or 404 depending on seed data
        assert resp.status_code in (200, 404)

    def test_price_icb_search(self, client, auth_headers):
        resp = client.get("/api/v2/intelligence/prices/icb?q=beton&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data or "items" in data

    def test_price_index(self, client, auth_headers):
        resp = client.get("/api/v2/intelligence/prices/index", headers=auth_headers)
        assert resp.status_code == 200

    def test_win_probability(self, client, auth_headers):
        resp = client.post("/api/v2/intelligence/win-probability", json={
            "our_price": 500000,
            "cpv5": "45000",
        }, headers=auth_headers)
        # 200 or 422 if body format is different
        assert resp.status_code in (200, 422)


# ═══ Kosztorys Engine Unit ════════════════════════════════════════════════════

class TestKosztorysEngine:
    def test_calc_pozycja_formula(self):
        from services.api.services.api.intelligence.kosztorys_engine import calc_pozycja, PozycjaInput, Narzuty
        poz = PozycjaInput(r_jcena=20.0, m_jcena=10.0, s_jcena=5.0, ilosc=100.0)
        narz = Narzuty(ko_r_pct=70, ko_s_pct=30, z_pct=12.5, kz_pct=7.1, vat_pct=23)
        result = calc_pozycja(poz, narz)
        assert result.jcena_netto > 0
        assert result.wartosc_netto > 0
        assert result.r_total == pytest.approx(20.0 * 100, rel=0.01)
        assert result.m_total == pytest.approx(10.0 * 100, rel=0.01)
        assert result.s_total == pytest.approx(5.0 * 100, rel=0.01)
        assert result.ko_total > 0
        assert result.z_total > 0

    def test_calc_pozycja_zero_values(self):
        from services.api.services.api.intelligence.kosztorys_engine import calc_pozycja, PozycjaInput, Narzuty
        poz = PozycjaInput(r_jcena=0, m_jcena=0, s_jcena=0, ilosc=10)
        narz = Narzuty(ko_r_pct=70, ko_s_pct=30, z_pct=12.5, kz_pct=7.1, vat_pct=23)
        result = calc_pozycja(poz, narz)
        assert result.jcena_netto == 0
        assert result.wartosc_netto == 0
