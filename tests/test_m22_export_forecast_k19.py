"""Sprint K19 — testy: prognoza ICB, export, kosztorys v1 deprecation."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

TENANT = str(uuid.uuid4())
TENDER_ID = str(uuid.uuid4())
KID = str(uuid.uuid4())


# ─── helpers ──────────────────────────────────────────────────────────────────

def _row(**kw):
    r = MagicMock()
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def _engine(rows_map: dict | None = None):
    engine = MagicMock()
    conn = MagicMock()

    def _execute(stmt, params=None):
        text = str(stmt).lower()
        result = MagicMock()
        rows = []
        if rows_map:
            for fragment, r in rows_map.items():
                if fragment.lower() in text:
                    rows = r
                    break
        result.fetchall.return_value = rows
        result.fetchone.return_value = rows[0] if rows else None
        result.rowcount = len(rows)
        return result

    conn.execute = _execute
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    begin_ctx = MagicMock()
    begin_ctx.__enter__ = lambda s: conn
    begin_ctx.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = conn
    engine.begin.return_value = begin_ctx
    return engine


# ══════════════════════════════════════════════════════════════════════════════
# 1. intelligence/price_intelligence.py — forecast_price
# ══════════════════════════════════════════════════════════════════════════════

class TestForecastPriceFunction:
    def test_import_ok(self):
        """forecast_price funkcja jest eksportowana."""
        from services.api.services.api.intelligence import price_intelligence as pi
        assert hasattr(pi, "forecast_price") or callable(getattr(pi, "forecast_price", None))

    def test_get_price_index_returns_list(self):
        """get_price_index zwraca listę kwartałów."""
        from services.api.services.api.intelligence.price_intelligence import get_price_index
        rows = [
            _row(kwartalrok=2024, kwartalnr=1, avg_r=50.0, avg_m=600.0, avg_s=80.0, n=100),
            _row(kwartalrok=2024, kwartalnr=2, avg_r=51.0, avg_m=620.0, avg_s=82.0, n=100),
        ]
        engine = _engine({"icb_ceny_srednie": rows})
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine", return_value=engine):
            result = get_price_index(quarters=4)
        assert isinstance(result, list)

    def test_forecast_linear_trend(self):
        """forecast_price zwraca dict z 'quarters' lub 'history'."""
        from services.api.services.api.intelligence.price_intelligence import forecast_price
        rows = [
            _row(kwartalrok=2024, kwartalnr=q, avg_price=500.0 + q * 10, n=50)
            for q in range(1, 5)
        ]
        engine = _engine({"icb_ceny_srednie": rows})
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine", return_value=engine):
            result = forecast_price(category="murarstwo", typ_rms="M", horizon_quarters=4)
        assert isinstance(result, dict)
        # forecast_price zwraca dict z kluczem 'forecasts', 'forecast', 'quarters' lub 'history'
        assert any(k in result for k in ("forecasts", "forecast", "quarters", "history", "p50"))

    def test_forecast_empty_history(self):
        """forecast_price na pustej historii — zwraca puste quarters lub graceful."""
        from services.api.services.api.intelligence.price_intelligence import forecast_price
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine", return_value=engine):
            result = forecast_price(category="beton_cement", typ_rms="M", horizon_quarters=2)
        assert isinstance(result, dict)

    def test_forecast_by_symbol(self):
        """forecast_price obsługuje parametr symbol."""
        from services.api.services.api.intelligence.price_intelligence import forecast_price
        rows = [_row(kwartalrok=2025, kwartalnr=1, avg_price=650.0, n=3)]
        engine = _engine({"icb_ceny_srednie": rows})
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine", return_value=engine):
            result = forecast_price(symbol="CEM-01", typ_rms="M", horizon_quarters=2)
        assert isinstance(result, dict)


# ══════════════════════════════════════════════════════════════════════════════
# 2. routers/intelligence.py — GET /prices/forecast endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestForecastEndpointRouter:
    def test_forecast_route_registered(self):
        """Route /prices/forecast jest zarejestrowany."""
        from services.api.services.api.routers.intelligence import router
        routes = [r.path for r in router.routes]
        assert any("forecast" in p for p in routes)

    def test_forecast_route_method_get(self):
        """Route forecast używa metody GET."""
        from services.api.services.api.routers.intelligence import router
        for r in router.routes:
            if hasattr(r, "path") and "forecast" in r.path:
                assert "GET" in r.methods
                break


# ══════════════════════════════════════════════════════════════════════════════
# 3. KosztorysPage — Prognoza tab state logic (unit tests komponentu)
# ══════════════════════════════════════════════════════════════════════════════

class TestForecastTabSourceCode:
    def test_runForecast_defined(self):
        """KosztorysPage zawiera funkcję runForecast."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "runForecast" in src

    def test_forecast_category_state(self):
        """KosztorysPage ma state forecastCategory."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "forecastCategory" in src
        assert "setForecastCategory" in src

    def test_forecast_horizon_state(self):
        """KosztorysPage ma state forecastHorizon."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "forecastHorizon" in src
        assert "setForecastHorizon" in src

    def test_forecast_data_state(self):
        """KosztorysPage ma state forecastData."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "forecastData" in src
        assert "setForecastData" in src

    def test_forecast_calls_intelligence_api(self):
        """runForecast wywołuje /api/v1/intelligence/prices/forecast."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "/api/v1/intelligence/prices/forecast" in src

    def test_forecast_chart_rendered(self):
        """Prognoza tab renderuje LineChart."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "LineChart" in src
        assert 'dataKey="avg_price"' in src

    def test_forecast_error_state(self):
        """Prognoza tab obsługuje błędy."""
        import pathlib
        src = pathlib.Path("/home/ubuntu/terra-os/apps/ui/src/components/pages/KosztorysPage.tsx").read_text()
        assert "forecastError" in src


# ══════════════════════════════════════════════════════════════════════════════
# 4. routers/kosztorys.py v1 — deprecation
# ══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV1Deprecation:
    def test_deprecation_notice_constant(self):
        """DEPRECATION_NOTICE jest zdefiniowane."""
        from services.api.services.api.routers.kosztorys import DEPRECATION_NOTICE
        assert "deprecated" in DEPRECATION_NOTICE.lower() or "Deprecated" in DEPRECATION_NOTICE

    def test_deprecation_headers_helper(self):
        """_deprecation_headers zwraca poprawne nagłówki RFC 8594."""
        from services.api.services.api.routers.kosztorys import _deprecation_headers
        h = _deprecation_headers()
        assert h["Deprecation"] == "true"
        assert "2026" in h["Sunset"]
        assert "successor-version" in h["Link"]

    def test_tag_is_deprecated(self):
        """Router v1 ma tag wskazujący deprecację."""
        from services.api.services.api.routers.kosztorys import router
        assert any("deprecated" in str(t).lower() for t in router.tags)

    def test_list_items_returns_jsonresponse(self):
        """list_kosztorys_items zwraca JSONResponse z nagłówkiem Deprecation."""
        from fastapi.responses import JSONResponse
        from services.api.services.api.routers.kosztorys import list_kosztorys_items
        row = _row(
            id=uuid.uuid4(), lp=1, kst_code="45.01",
            description="Roboty murowe", unit="m2",
            quantity=100.0, unit_price=50.0, category="murarstwo",
        )
        engine = _engine({"kosztorys_items": [row]})
        user = MagicMock()
        user.org_id = TENANT

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            resp = list_kosztorys_items(TENDER_ID, user)

        assert isinstance(resp, JSONResponse)
        assert resp.headers.get("deprecation") == "true" or resp.headers.get("Deprecation") == "true"

    def test_deprecated_field_in_body(self):
        """Response body zawiera pole _deprecated."""
        from fastapi.responses import JSONResponse
        import json
        from services.api.services.api.routers.kosztorys import list_kosztorys_items
        row = _row(
            id=uuid.uuid4(), lp=1, kst_code=None,
            description="Test", unit="szt",
            quantity=1.0, unit_price=100.0, category="inne",
        )
        engine = _engine({"kosztorys_items": [row]})
        user = MagicMock()
        user.org_id = TENANT

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            resp = list_kosztorys_items(TENDER_ID, user)

        body = json.loads(resp.body)
        assert "_deprecated" in body

    def test_v1_docstring_mentions_v2(self):
        """Docstring v1 routera wspomina o v2."""
        import inspect
        from services.api.services.api.routers import kosztorys
        doc = kosztorys.__doc__
        assert "v2" in doc.lower() or "/api/v2/kosztorys" in doc


class TestKosztorysV1ParseAth:
    def test_parse_ath_xml_valid(self):
        """_parse_ath_xml parsuje prosty ATH XML."""
        from services.api.services.api.routers.kosztorys import _parse_ath_xml
        xml = b"""<Kosztorys>
            <Pozycja kod="45.01">
                <Nazwa>Murowanie cegla</Nazwa>
                <Jm>m2</Jm>
                <Ilosc>100</Ilosc>
                <CenaJm>35.50</CenaJm>
            </Pozycja>
        </Kosztorys>"""
        items = _parse_ath_xml(xml)
        assert len(items) == 1
        assert items[0]["description"] == "Murowanie cegla"
        assert items[0]["quantity"] == pytest.approx(100.0)
        assert items[0]["unit_price"] == pytest.approx(35.50)

    def test_parse_ath_xml_empty(self):
        """_parse_ath_xml na pustym XML zwraca []."""
        from services.api.services.api.routers.kosztorys import _parse_ath_xml
        items = _parse_ath_xml(b"<Kosztorys/>")
        assert items == []

    def test_parse_ath_xml_invalid(self):
        """_parse_ath_xml na niepoprawnym XML zwraca []."""
        from services.api.services.api.routers.kosztorys import _parse_ath_xml
        items = _parse_ath_xml(b"not xml at all !!!")
        assert items == []

    def test_generate_ath_xml(self):
        """_generate_ath_xml generuje poprawny XML z pozycjami."""
        from services.api.services.api.routers.kosztorys import _generate_ath_xml
        items = [
            {"kst_code": "45.01", "description": "Beton B25", "unit": "m3",
             "quantity": 50.0, "unit_price": 450.0},
        ]
        xml_bytes = _generate_ath_xml(items)
        assert b"Beton B25" in xml_bytes
        assert b"Kosztorys" in xml_bytes


class TestKosztorysV1CrudLogic:
    """Testy logiki CRUD v1 przez mock DB."""

    def test_list_returns_correct_total(self):
        """list_kosztorys_items liczy sumę poprawnie."""
        from fastapi.responses import JSONResponse
        import json
        from services.api.services.api.routers.kosztorys import list_kosztorys_items
        rows = [
            _row(id=uuid.uuid4(), lp=1, kst_code=None, description="A",
                 unit="m2", quantity=10.0, unit_price=100.0, category="inne"),
            _row(id=uuid.uuid4(), lp=2, kst_code=None, description="B",
                 unit="m2", quantity=5.0, unit_price=200.0, category="inne"),
        ]
        engine = _engine({"kosztorys_items": rows})
        user = MagicMock(); user.org_id = TENANT

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            resp = list_kosztorys_items(TENDER_ID, user)

        body = json.loads(resp.body)
        assert body["count"] == 2
        assert body["total"] == pytest.approx(2000.0)  # 10*100 + 5*200

    def test_list_empty_tender(self):
        """list_kosztorys_items dla pustego przetargu zwraca count=0, total=0."""
        from fastapi.responses import JSONResponse
        import json
        from services.api.services.api.routers.kosztorys import list_kosztorys_items
        engine = _engine({"kosztorys_items": []})
        user = MagicMock(); user.org_id = TENANT

        with patch("services.api.services.api.routers.kosztorys.get_engine", return_value=engine):
            resp = list_kosztorys_items(TENDER_ID, user)

        body = json.loads(resp.body)
        assert body["count"] == 0
        assert body["total"] == 0.0
