"""Coverage tests for:
  - services/api/services/api/routers/external_data.py
  - services/api/services/api/routers/export.py

All DB / AI / export-library calls are mocked — no real DB or files needed.
"""
from __future__ import annotations

import io
import json
import zipfile
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_row(**kwargs):
    """Fake SQLAlchemy Row with ._mapping dict and attribute access."""
    row = MagicMock()
    row._mapping = kwargs
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _mock_engine_multi(*execute_returns):
    """Return (engine, conn) whose conn.execute() cycles through *execute_returns*.

    Each item in execute_returns should be a dict with keys:
        scalar, fetchone, fetchall, rowcount
    """
    results = []
    for spec in execute_returns:
        r = MagicMock()
        r.scalar.return_value = spec.get("scalar", 0)
        r.fetchone.return_value = spec.get("fetchone")
        r.fetchall.return_value = spec.get("fetchall", [])
        r.rowcount = spec.get("rowcount", 1)
        results.append(r)

    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.commit = MagicMock()
    if results:
        conn.execute.side_effect = results
    else:
        conn.execute.return_value.fetchall.return_value = []
        conn.execute.return_value.scalar.return_value = 0

    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value.__enter__ = lambda s: conn
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine, conn


def _mock_engine_simple(scalar=0, fetchone=None, fetchall=None):
    return _mock_engine_multi(
        {"scalar": scalar, "fetchone": fetchone, "fetchall": fetchall or []}
    )


# ─── Fixtures ─────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
#  EXTERNAL DATA — /api/v2/external/*
# ─────────────────────────────────────────────────────────────────────────────

_EXT_MODULE = "services.api.services.api.routers.external_data"
_PLAN_MODULE = "services.api.services.api.auth.plan_gate"


# ── TED Notices ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ted_table_not_exists(app, auth_headers):
    """Lines 47: table doesn't exist → message returned."""
    engine, _ = _mock_engine_multi(
        {"scalar": False},   # EXISTS check → False
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/ted", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert "message" in data


@pytest.mark.asyncio
async def test_ted_with_data(app, auth_headers):
    """Lines 49-76: table exists, returns rows."""
    row = _make_row(
        ted_id="TED-001",
        title="Test tender",
        buyer="Urząd Gminy",
        cpv_codes=["45000000"],
        contract_value_eur=100000,
        contract_value_pln=450000,
        publication_date="2024-01-15",
        notice_type="CN",
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},       # EXISTS check
        {"fetchall": [row]},    # SELECT rows
        {"scalar": 1},          # COUNT(*)
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/ted?days_back=30&limit=10&offset=0",
                            headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] == 1
    assert data["days_back"] == 30


@pytest.mark.asyncio
async def test_ted_with_cpv_filter(app, auth_headers):
    """Lines 53-55: cpv_prefix filter applied."""
    row = _make_row(
        ted_id="TED-002", title="CPV filtered", buyer="B",
        cpv_codes=["45100000"], contract_value_eur=0, contract_value_pln=0,
        publication_date="2024-02-01", notice_type="CN",
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},
        {"fetchall": [row]},
        {"scalar": 1},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/ted?cpv_prefix=45", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cpv_prefix"] == "45"


@pytest.mark.asyncio
async def test_ted_exception_returns_error(app, auth_headers):
    """Lines 77-79: exception → error dict."""
    with patch(f"{_EXT_MODULE}.get_engine", side_effect=RuntimeError("db down")), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/ted", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert "error" in data


# ── GUS Indicators ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gus_table_not_exists(app, auth_headers):
    """Lines 97-98: gus_indicators table missing."""
    engine, _ = _mock_engine_multi({"scalar": False})
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/gus/indicators", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert "message" in data


@pytest.mark.asyncio
async def test_gus_with_data_no_year(app, auth_headers):
    """Lines 100-125: no year filter, rows grouped by variable_name."""
    row = _make_row(
        variable_id="P_001",
        variable_name="Produkcja budowlana",
        unit_name="mln PLN",
        year=2023,
        value=12345.67,
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},
        {"fetchall": [row]},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/gus/indicators", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "indicators" in data
    assert data["total_records"] == 1
    assert "Produkcja budowlana" in data["indicators"]


@pytest.mark.asyncio
async def test_gus_with_year_filter(app, auth_headers):
    """Lines 102-104: year param triggers WHERE clause."""
    row = _make_row(
        variable_id="P_001", variable_name="Produkcja", unit_name="szt", year=2024, value=100.0
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},
        {"fetchall": [row]},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/gus/indicators?year=2024", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "indicators" in data


@pytest.mark.asyncio
async def test_gus_variable_id_fallback(app, auth_headers):
    """Lines 116-117: variable_name is None → fall back to variable_id."""
    row = _make_row(
        variable_id="P_NO_NAME", variable_name=None, unit_name="szt", year=2023, value=None
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},
        {"fetchall": [row]},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/gus/indicators", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "P_NO_NAME" in data["indicators"]
    assert data["indicators"]["P_NO_NAME"][0]["value"] is None


@pytest.mark.asyncio
async def test_gus_exception_returns_error(app, auth_headers):
    """Lines 126-128: exception → error dict."""
    with patch(f"{_EXT_MODULE}.get_engine", side_effect=Exception("fail")), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/gus/indicators", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "error" in data


# ── Pre-tender Signals ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pretenders_table_not_exists(app, auth_headers):
    """Lines 149-150: pretender_signals table missing."""
    engine, _ = _mock_engine_multi({"scalar": False})
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/pretenders", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert "message" in data


@pytest.mark.asyncio
async def test_pretenders_with_data_no_filters(app, auth_headers):
    """Lines 152-181: no filters → plain WHERE clause."""
    row = _make_row(
        signal_id="SIG-001",
        source="bzp_pin",
        title="Budowa drogi",
        buyer="Gmina Testowa",
        estimated_value_pln=500000,
        cpv_codes=["45233120"],
        expected_date="2024-06-01",
        published_at="2024-01-10T12:00:00",
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},
        {"fetchall": [row]},
        {"scalar": 1},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/pretenders", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_pretenders_with_cpv_and_source_filter(app, auth_headers):
    """Lines 155-162: cpv_prefix + source conditions joined with AND."""
    row = _make_row(
        signal_id="SIG-002", source="bzp_pin", title="Roboty", buyer="ZUS",
        estimated_value_pln=0, cpv_codes=["45000000"],
        expected_date=None, published_at="2024-01-01T00:00:00",
    )
    engine, _ = _mock_engine_multi(
        {"scalar": True},
        {"fetchall": [row]},
        {"scalar": 1},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                "/api/v2/external/pretenders?cpv_prefix=45&source=bzp_pin",
                headers=auth_headers,
            )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_pretenders_exception_returns_error(app, auth_headers):
    """Lines 182-184: exception → error dict."""
    with patch(f"{_EXT_MODULE}.get_engine", side_effect=Exception("fail")), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/pretenders", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "error" in data


# ── Market Intelligence ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_market_intelligence_success(app, auth_headers):
    """Lines 196-250: all sub-queries succeed, _generate_market_summary called."""
    ted_row = MagicMock()
    ted_row.__getitem__ = lambda s, i: (5, 250000.0)[i]

    bzp_row = MagicMock()
    bzp_row.__getitem__ = lambda s, i: (3, 1000000.0)[i]

    pt_row = MagicMock()
    pt_row.__getitem__ = lambda s, i: (2, 500000.0)[i]

    gus_row = _make_row(unit_name="mln PLN", year=2023, value=12345.67)

    engine, _ = _mock_engine_multi(
        {"fetchone": ted_row},
        {"fetchone": bzp_row},
        {"fetchone": pt_row},
        {"fetchone": gus_row},
    )
    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"), \
         patch(f"{_EXT_MODULE}._generate_market_summary", return_value="AI summary text"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                "/api/v2/external/market-intelligence?cpv_prefix=45",
                headers=auth_headers,
            )
    assert r.status_code == 200
    data = r.json()
    assert data["summary"] == "AI summary text"
    assert "stats" in data


@pytest.mark.asyncio
async def test_market_intelligence_sub_queries_fail_gracefully(app, auth_headers):
    """Lines 209-231: inner try/except blocks catch query errors."""
    # Make all sub-queries raise exceptions → defaults applied
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.side_effect = Exception("table missing")

    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch(f"{_EXT_MODULE}.get_engine", return_value=engine), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"), \
         patch(f"{_EXT_MODULE}._generate_market_summary", return_value="fallback"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/market-intelligence", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert data["stats"]["ted_30d"]["count"] == 0
    assert data["stats"]["bzp_30d"]["count"] == 0


@pytest.mark.asyncio
async def test_market_intelligence_outer_exception(app, auth_headers):
    """Lines 248-250: outer exception → error summary."""
    with patch(f"{_EXT_MODULE}.get_engine", side_effect=Exception("total failure")), \
         patch(f"{_PLAN_MODULE}._get_org_plan", return_value="enterprise"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/external/market-intelligence", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "Błąd" in data["summary"]


# ── _generate_market_summary (unit-tested directly) ───────────────────────────

def test_generate_market_summary_with_llm():
    """Lines 253-272: LLM client available → calls generate()."""
    import types, sys
    from services.api.services.api.routers.external_data import _generate_market_summary
    mock_client = MagicMock()
    mock_client.generate.return_value = "LLM generated summary"
    # Create a fake services.ai.vllm_client module so the `from` import works
    fake_module = types.ModuleType("services.ai.vllm_client")
    # get_llm_client returns the mock which then raises on .generate()
    setattr(fake_module, "get_llm_client", lambda: mock_client)
    stats = {
        "ted_30d": {"count": 5, "total_eur": 100000},
        "bzp_30d": {"count": 3, "total_pln": 500000},
        "pretenders": {"count": 2, "total_est_pln": 200000},
        "gus_top": {"unit_name": "mln PLN", "year": 2023, "value": 12000},
    }
    with patch("services.ai.vllm_client.get_llm_client", return_value=mock_client):
        result = _generate_market_summary("45", stats)
    assert result == "LLM generated summary"
    mock_client.generate.assert_called_once()


def test_generate_market_summary_llm_import_error():
    """Lines 273-284: LLM import fails → static text fallback."""
    from services.api.services.api.routers.external_data import _generate_market_summary
    stats = {
        "ted_30d": {"count": 5, "total_eur": 100000},
        "bzp_30d": {"count": 3, "total_pln": 500000},
        "pretenders": {"count": 2, "total_est_pln": 200000},
    }
    with patch.dict("sys.modules", {"services.ai.vllm_client": None}):
        result = _generate_market_summary("45", stats)
    # Should return static fallback string
    assert "CPV 45" in result
    assert "AI niedostępne" in result


def test_generate_market_summary_llm_runtime_error():
    """Lines 273-284: LLM raises at runtime → static fallback."""
    import types, sys
    from services.api.services.api.routers.external_data import _generate_market_summary
    mock_client = MagicMock()
    mock_client.generate.side_effect = RuntimeError("GPU OOM")
    fake_module = types.ModuleType("services.ai.vllm_client")
    # get_llm_client returns the mock which then raises on .generate()
    setattr(fake_module, "get_llm_client", lambda: mock_client)
    stats = {
        "ted_30d": {"count": 0, "total_eur": 0},
        "bzp_30d": {"count": 0, "total_pln": 0},
        "pretenders": {"count": 0, "total_est_pln": 0},
    }
    with patch("services.ai.vllm_client.get_llm_client", return_value=mock_client):
        result = _generate_market_summary("45", stats)
    assert "AI niedostępne" in result


def test_generate_market_summary_empty_stats_fallback():
    """Lines 274-284: empty stats dict → fallback with zeros."""
    from services.api.services.api.routers.external_data import _generate_market_summary
    with patch.dict("sys.modules", {"services.ai.vllm_client": None}):
        result = _generate_market_summary("45100000", {})
    assert "CPV 45100000" in result or "45100000" in result
    assert "AI niedostępne" in result


# ─────────────────────────────────────────────────────────────────────────────
#  EXPORT — /api/v1/*
# ─────────────────────────────────────────────────────────────────────────────

_EXPORT_MODULE = "services.api.services.api.routers.export"

_SAMPLE_LINES = [
    {"description": "Roboty ziemne", "quantity": 10.0, "unit": "m3",
     "unit_price": 50.0, "line_total_pln": 500.0},
    {"description": "Beton fundamentowy", "quantity": 5.0, "unit": "m3",
     "unit_price": 200.0, "line_total_pln": 1000.0},
]


def _make_estimate_row(tender_id="tender-001", total_net_pln=1500.0, lines=None, variant="doc"):
    return _make_row(
        id="est-001",
        tender_id=tender_id,
        variant=variant,
        total_net_pln=total_net_pln,
        params={},
        lines=lines if lines is not None else _SAMPLE_LINES,
    )


def _make_tender_row(title="Test Przetarg"):
    return _make_row(
        id="tender-001",
        title=title,
        buyer="Gmina",
        cpv="45000000",
        external_id="BZP-1234",
    )


def _make_owner_row():
    return _make_row(company_name="Firma Budowlana Sp. z o.o.")


# ── Helper unit tests ─────────────────────────────────────────────────────────

def test_slug_basic():
    from services.api.services.api.routers.export import _slug
    assert _slug("Hello World!") == "Hello_World_"


def test_slug_none_like():
    from services.api.services.api.routers.export import _slug
    # Empty string → default 'kosztorys'
    assert _slug("") == "kosztorys"


def test_slug_long_string():
    from services.api.services.api.routers.export import _slug
    s = "A" * 100
    assert len(_slug(s)) <= 60


def test_validate_lines_empty_raises():
    from fastapi import HTTPException
    from services.api.services.api.routers.export import _validate_lines
    with pytest.raises(HTTPException) as exc_info:
        _validate_lines([])
    assert exc_info.value.status_code == 422


def test_validate_lines_missing_price_warning():
    from services.api.services.api.routers.export import _validate_lines
    lines = [{"description": "item", "quantity": 1.0, "unit": "szt",
              "unit_price": 0, "line_total_pln": 0}]
    warnings = _validate_lines(lines)
    assert any("ceny" in w for w in warnings)


def test_validate_lines_missing_unit_warning():
    from services.api.services.api.routers.export import _validate_lines
    lines = [{"description": "item", "quantity": 1.0, "unit": "",
              "unit_price": 100.0, "line_total_pln": 100.0}]
    warnings = _validate_lines(lines)
    assert any("jednostki" in w for w in warnings)
    # Unit should have been patched to 'kpl'
    assert lines[0]["unit"] == "kpl"


def test_check_sum_none_total_no_raise():
    from services.api.services.api.routers.export import _check_sum
    # No exception when total is None
    _check_sum(_SAMPLE_LINES, None)


def test_check_sum_ok():
    from services.api.services.api.routers.export import _check_sum
    lines = [{"line_total_pln": 100.0}, {"line_total_pln": 200.0}]
    _check_sum(lines, 300.0)  # exact match, no raise


def test_check_sum_deviation_raises():
    from fastapi import HTTPException
    from services.api.services.api.routers.export import _check_sum
    lines = [{"line_total_pln": 100.0}]
    with pytest.raises(HTTPException) as exc_info:
        _check_sum(lines, 200.0)  # 100 vs 200 → deviation > 0.10
    assert exc_info.value.status_code == 500


def test_export_request_defaults():
    """Lines 99-103: ExportRequest model defaults."""
    from services.api.services.api.routers.export import ExportRequest
    req = ExportRequest()
    assert req.template == "kosztorys_ofertowy"
    assert req.include_cover_page is True
    assert req.include_summary is True
    assert req.watermark is None
    assert req.hide_unit_prices is False
    assert req.kp_percent == 12.0
    assert req.zysk_percent == 8.0
    assert req.vat_percent == 23.0


def test_get_estimate_not_found():
    """_get_estimate raises 404 when row is None."""
    from fastapi import HTTPException
    from services.api.services.api.routers.export import _get_estimate
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        _get_estimate(conn, "nonexistent-id")
    assert exc_info.value.status_code == 404


def test_get_tender_missing():
    """_get_tender returns empty dict when row is None."""
    from services.api.services.api.routers.export import _get_tender
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    result = _get_tender(conn, "no-tender")
    assert result == {}


def test_get_owner_missing():
    """_get_owner returns empty dict when row is None."""
    from services.api.services.api.routers.export import _get_owner
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    result = _get_owner(conn)
    assert result == {}


# ── DOCX export endpoint ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_docx_success(app, auth_headers):
    """Lines 115-149: DOCX export returns streaming response."""
    est_row = _make_estimate_row()
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchone": est_row},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )

    fake_docx_bytes = b"PK\x03\x04fake-docx-content"

    mock_cfg_cls = MagicMock()
    mock_cfg_instance = MagicMock()
    mock_cfg_cls.return_value = mock_cfg_instance

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine), \
         patch("services.estimator.export_docx.DocxExportConfig", mock_cfg_cls, create=True), \
         patch("services.estimator.export_docx.export_estimate_docx",
               return_value=fake_docx_bytes, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/est-001/export/docx",
                headers=auth_headers,
                json={"template": "kosztorys_ofertowy"},
            )
    assert r.status_code == 200
    assert "docx" in r.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_docx_estimate_not_found(app, auth_headers):
    """Lines 122-126: estimate not found → 404."""
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.return_value.fetchone.return_value = None

    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/nonexistent/export/docx",
                headers=auth_headers,
            )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_docx_no_lines_422(app, auth_headers):
    """Lines 126: empty lines → 422."""
    est_row = _make_estimate_row(lines=[])
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchone": est_row},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )
    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/est-001/export/docx",
                headers=auth_headers,
            )
    assert r.status_code == 422


# ── XLSX export endpoint ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_xlsx_success(app, auth_headers):
    """Lines 155-184: XLSX export returns streaming response."""
    est_row = _make_estimate_row()
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchone": est_row},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )

    fake_xlsx_bytes = b"PK\x03\x04fake-xlsx-content"

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine), \
         patch("services.estimator.export_xlsx.XlsxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_xlsx.export_estimate_xlsx",
               return_value=fake_xlsx_bytes, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/est-001/export/xlsx",
                headers=auth_headers,
                json={},
            )
    assert r.status_code == 200
    assert "xlsx" in r.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_xlsx_estimate_not_found(app, auth_headers):
    """XLSX: estimate not found → 404."""
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.return_value.fetchone.return_value = None

    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/nonexistent/export/xlsx",
                headers=auth_headers,
            )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_xlsx_no_lines_422(app, auth_headers):
    """XLSX: empty lines → 422."""
    est_row = _make_estimate_row(lines=[])
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchone": est_row},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )
    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/est-001/export/xlsx",
                headers=auth_headers,
            )
    assert r.status_code == 422


# ── ZIP export endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_zip_success(app, auth_headers):
    """Lines 190-250: ZIP export packs DOCX + XLSX per estimate variant."""
    row1 = _make_row(
        id="est-001", variant="ofertowy", total_net_pln=1500.0,
        lines=_SAMPLE_LINES,
    )
    tender_row = _make_tender_row("My Project")
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchall": [row1]},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )

    fake_bytes = b"PK\x03\x04content"

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine), \
         patch("services.estimator.export_docx.DocxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_docx.export_estimate_docx",
               return_value=fake_bytes, create=True), \
         patch("services.estimator.export_xlsx.XlsxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_xlsx.export_estimate_xlsx",
               return_value=fake_bytes, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/tenders/tender-001/estimate/export/zip",
                headers=auth_headers,
                json={},
            )
    assert r.status_code == 200
    assert "zip" in r.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_zip_empty_lines_skipped(app, auth_headers):
    """Lines 219-220: estimates with empty lines are skipped inside the zip."""
    row_empty = _make_row(
        id="est-empty", variant="ofertowy", total_net_pln=0.0, lines=[],
    )
    row_valid = _make_row(
        id="est-valid", variant="szczegolowy", total_net_pln=1500.0, lines=_SAMPLE_LINES,
    )
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchall": [row_empty, row_valid]},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )

    fake_bytes = b"PK\x03\x04"

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine), \
         patch("services.estimator.export_docx.DocxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_docx.export_estimate_docx",
               return_value=fake_bytes, create=True), \
         patch("services.estimator.export_xlsx.XlsxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_xlsx.export_estimate_xlsx",
               return_value=fake_bytes, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/tenders/tender-001/estimate/export/zip",
                headers=auth_headers,
            )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_export_zip_no_estimates_404(app, auth_headers):
    """Lines 210-211: no estimates → 404."""
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchall": []},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )
    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/tenders/no-tender/estimate/export/zip",
                headers=auth_headers,
            )
    assert r.status_code == 404


# ── Preview endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_preview_success(app, auth_headers):
    """Lines 256-305: preview returns page/sheet metadata."""
    est_row = _make_estimate_row()
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchone": est_row},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )

    fake_bytes = b"x" * 4096  # 4 KB

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine), \
         patch("services.estimator.export_docx.DocxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_docx.export_estimate_docx",
               return_value=fake_bytes, create=True), \
         patch("services.estimator.export_xlsx.XlsxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_xlsx.export_estimate_xlsx",
               return_value=fake_bytes, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/est-001/export/preview",
                headers=auth_headers,
                json={"include_cover_page": True, "include_summary": True},
            )
    assert r.status_code == 200
    data = r.json()
    assert "pages" in data
    assert "sheets" in data
    assert "sections" in data
    assert "Strona tytułowa" in data["sections"]
    assert "Podsumowanie (netto/VAT/brutto)" in data["sections"]
    assert "estimated_docx_size_kb" in data
    assert "estimated_xlsx_size_kb" in data


@pytest.mark.asyncio
async def test_export_preview_no_cover_no_summary(app, auth_headers):
    """Lines 287-293: sections without cover/summary."""
    est_row = _make_estimate_row()
    tender_row = _make_tender_row()
    owner_row = _make_owner_row()

    engine, _ = _mock_engine_multi(
        {"fetchone": est_row},
        {"fetchone": tender_row},
        {"fetchone": owner_row},
    )

    fake_bytes = b"y" * 1024

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine), \
         patch("services.estimator.export_docx.DocxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_docx.export_estimate_docx",
               return_value=fake_bytes, create=True), \
         patch("services.estimator.export_xlsx.XlsxExportConfig", MagicMock(), create=True), \
         patch("services.estimator.export_xlsx.export_estimate_xlsx",
               return_value=fake_bytes, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/est-001/export/preview",
                headers=auth_headers,
                json={"include_cover_page": False, "include_summary": False},
            )
    assert r.status_code == 200
    data = r.json()
    assert "Strona tytułowa" not in data["sections"]
    assert "Podsumowanie" not in " ".join(data["sections"])


@pytest.mark.asyncio
async def test_export_preview_estimate_not_found(app, auth_headers):
    """Preview: estimate not found → 404."""
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute.return_value.fetchone.return_value = None

    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch(f"{_EXPORT_MODULE}.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/estimates/no-est/export/preview",
                headers=auth_headers,
            )
    assert r.status_code == 404


# ── Tender list exports: CSV + XLSX ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_tenders_csv(app, auth_headers):
    """Lines 323-356: /api/v1/tenders/csv → CSV with UTF-8-sig BOM.

    Uses a mini-app with only the export router to avoid the wildcard
    /tenders/{tender_id} route in zwiad.router swallowing the request.
    """
    from fastapi import FastAPI
    from services.api.services.api.routers.export import router as export_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    mini_app = FastAPI()
    mini_app.include_router(export_router)

    _demo = CurrentUser(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    mini_app.dependency_overrides[get_current_user] = lambda: _demo

    row = _make_row(
        id="t-001", title="Przetarg 1", source="bzp", value_pln=100000,
        match_score=0.9, deadline_at="2024-06-01", created_at="2024-01-01"
    )
    engine, _ = _mock_engine_multi({"fetchall": [row]})

    with patch("terra_db.session.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=mini_app), base_url="http://test") as c:
            r = await c.get("/api/v1/tenders/csv", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_export_tenders_xlsx_with_openpyxl(app, auth_headers):
    """Lines 359-395: /api/v1/tenders/xlsx → XLSX via openpyxl.

    Uses a mini-app to avoid route shadowing.
    """
    from fastapi import FastAPI
    from services.api.services.api.routers.export import router as export_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    mini_app = FastAPI()
    mini_app.include_router(export_router)

    _demo = CurrentUser(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    mini_app.dependency_overrides[get_current_user] = lambda: _demo

    row = _make_row(
        id="t-001", title="Przetarg XLSX", source="ted", value_pln=200000,
        match_score=0.85, deadline_at="2024-07-01",
    )
    # row iteration for ws.append (openpyxl iterates over the row object)
    row.__iter__ = lambda s: iter(["t-001", "Przetarg XLSX", "ted", 200000, 0.85, "2024-07-01"])

    engine, _ = _mock_engine_multi({"fetchall": [row]})

    with patch("terra_db.session.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=mini_app), base_url="http://test") as c:
            r = await c.get("/api/v1/tenders/xlsx", headers=auth_headers)
    # Accept 200 regardless of openpyxl presence
    assert r.status_code == 200
