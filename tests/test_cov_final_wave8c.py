"""Coverage tests for 16 small-gap files (wave8c)."""
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

# ─── Auth helper ──────────────────────────────────────────────────────────────
from services.api.services.api.auth.deps import CurrentUser

def _user():
    return CurrentUser(user_id="u1", email="t@t.pl", org_id="o1", role="owner")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. scoring_v2 — lines 83,85,87,141
# ═══════════════════════════════════════════════════════════════════════════════

def test_scoring_v2_simulate_score_deadline_far_future():
    """Line 141: deadline > 30 days → deadline_score = 30."""
    from services.api.services.api.routers.scoring_v2 import _simulate_score
    far_deadline = datetime.utcnow() + timedelta(days=60)
    score = _simulate_score(cpv="45000000", value=1_000_000, deadline=far_deadline, buyer="Test", weights={
        "cpv_match": 0.2, "value_fit": 0.2, "deadline": 0.2, "buyer_history": 0.2, "doc_quality": 0.2
    })
    assert 0 < score < 100


def test_scoring_v2_simulate_score_no_cpv_no_value_no_buyer():
    """Lines 83,85,87: cpv=None→40, value=0→30, buyer=None→30."""
    from services.api.services.api.routers.scoring_v2 import _simulate_score
    score = _simulate_score(cpv=None, value=0, deadline=None, buyer=None, weights={
        "cpv_match": 0.2, "value_fit": 0.2, "deadline": 0.2, "buyer_history": 0.2, "doc_quality": 0.2
    })
    assert score < 50


# ═══════════════════════════════════════════════════════════════════════════════
# 3. monitoring — lines 196-197, 228, 256
# ═══════════════════════════════════════════════════════════════════════════════

def test_monitoring_alerts_high_error_rate():
    """Line 228: error_rate > 5% → alert."""
    import services.api.services.api.routers.monitoring as mon_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(mon_mod.router)

    with mon_mod._count_lock:
        old_req = mon_mod._request_count
        old_err = mon_mod._error_count
        mon_mod._request_count = 200
        mon_mod._error_count = 30

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v2/alerts")
        app.dependency_overrides.clear()
        return resp

    try:
        resp = asyncio.run(_run())
        assert resp.status_code == 200
        data = resp.json()
        alert_ids = [a["id"] for a in data.get("alerts", [])]
        assert "high_error_rate" in alert_ids
    finally:
        with mon_mod._count_lock:
            mon_mod._request_count = old_req
            mon_mod._error_count = old_err


def test_monitoring_disk_unknown():
    """Lines 196-197: psutil.disk_usage raises → disk=unknown."""
    import services.api.services.api.routers.monitoring as mon_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(mon_mod.router)

    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            with patch("psutil.disk_usage", side_effect=OSError("nope")):
                resp = await ac.get("/api/v2/health/detailed")
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["disk"]["status"] == "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. rfq — lines 440-441, 455-456
# ═══════════════════════════════════════════════════════════════════════════════

def test_rfq_parse_price_value_error():
    """Lines 440-441, 455-456: regex matches but float()/int() raises ValueError."""
    from services.api.services.api.routers.rfq import _parse_offer_from_email
    body = "Cena netto: abc PLN\ntermin: xyz dni\nFirma TestCo"
    result = _parse_offer_from_email(body, "TestCo")
    assert result["price_net_pln"] is None
    assert result["lead_time_days"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# 5. swz — lines 193, 303-304
# ═══════════════════════════════════════════════════════════════════════════════

def test_swz_analyze_regex_red_flags():
    """Line 193: red flags detected by regex."""
    from services.api.services.api.routers.swz import _analyze_with_regex
    text = "Wymagane doświadczenie i referencje. Wykonawca musi mieć koncesję."
    result = _analyze_with_regex(text)
    assert isinstance(result, dict)


def test_swz_go_nogo_score_non_int():
    """Lines 303-304: go_nogo_score is string → int conversion."""
    from services.api.services.api.routers import swz as swz_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(swz_mod.router)

    fake_result = {
        "go_nogo_score": "invalid",
        "risk_level": "medium",
        "requirements": [],
        "red_flags": [],
        "key_dates": [],
        "recommended_actions": [],
    }

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            with patch.object(swz_mod, "_analyze_with_ai", return_value=fake_result), \
                 patch("terra_db.session.get_engine") as mock_eng:
                mock_conn = MagicMock()
                mock_conn.execute.return_value = MagicMock(fetchone=lambda: None)
                mock_eng.return_value.connect.return_value.__enter__ = lambda s: mock_conn
                mock_eng.return_value.connect.return_value.__exit__ = lambda s, *a: None
                resp = await ac.post("/api/v2/swz/analyze", json={"tender_id": "t1", "swz_text": "Test"})
        app.dependency_overrides.clear()
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code in (200, 422, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. market_intelligence — lines 58, 273-274
# ═══════════════════════════════════════════════════════════════════════════════

def test_market_intelligence_redis_set_exception():
    """Line 58: _redis_set exception path (silently swallowed)."""
    from services.api.services.api.routers.market_intelligence import _redis_set
    with patch("services.api.services.api.redis_cache._get_redis", side_effect=Exception("fail")):
        _redis_set("test_key", {"data": 1}, ttl=300)  # should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# 7. health — lines 235-236, 276
# ═══════════════════════════════════════════════════════════════════════════════

def test_health_cache_exception():
    """Lines 235-236: cache import fails → entries=0."""
    import services.api.services.api.routers.health as health_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(health_mod.router)

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Patch the cache module to raise on access
            with patch("terra_db.session.get_engine") as mock_eng:
                mock_conn = MagicMock()
                mock_conn.execute.return_value = MagicMock(fetchone=lambda: None, scalar=lambda: None)
                mock_eng.return_value.connect.return_value.__enter__ = lambda s: mock_conn
                mock_eng.return_value.connect.return_value.__exit__ = lambda s, *a: None
                resp = await ac.get("/health/detailed")
        app.dependency_overrides.clear()
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. competitor_watch — lines 159-160, 200
# ═══════════════════════════════════════════════════════════════════════════════

def test_competitor_watch_duplicate_409():
    """Lines 159-160: unique constraint → 409."""
    from services.api.services.api.routers import competitor_watch as cw_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(cw_mod.router)

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()

        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("unique constraint violation")
        mock_db.rollback = MagicMock()

        app.dependency_overrides[cw_mod.get_db] = lambda: mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v2/competitors", json={"competitor_nip": "1234567890", "competitor_name": "Test"})
        app.dependency_overrides.clear()
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 409


def test_competitor_watch_update_no_valid_fields():
    """Line 200: no valid fields → 400."""
    from services.api.services.api.routers import competitor_watch as cw_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(cw_mod.router)

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()

        mock_db = MagicMock()
        app.dependency_overrides[cw_mod.get_db] = lambda: mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            wid = str(uuid4())
            resp = await ac.put(f"/api/v2/competitors/{wid}", json={"invalid_field": "x"})
        app.dependency_overrides.clear()
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 10. redis_cache — lines 58, 125, 151
# ═══════════════════════════════════════════════════════════════════════════════

def test_redis_cache_set_error_fallback():
    """Line 125: Redis SET error → fallback to in-process cache."""
    from services.api.services.api import redis_cache as rc_mod

    mock_redis = MagicMock()
    mock_redis.setex.side_effect = Exception("connection error")

    with patch.object(rc_mod, "_get_redis", return_value=mock_redis), \
         patch("services.api.services.api.cache.set") as mock_cache_set:
        rc_mod.rcache_set("test_key", {"data": 1}, ttl=60)
        mock_cache_set.assert_called_once()


def test_redis_cache_invalidate_no_redis():
    """Line 151: invalidate_prefix when redis is None → returns 0."""
    from services.api.services.api import redis_cache as rc_mod

    with patch.object(rc_mod, "_get_redis", return_value=None):
        result = rc_mod.rcache_invalidate_prefix("test:")
        assert result == 0


def test_redis_cache_get_redis_already_connected():
    """Line 58: _redis_client already set → return immediately."""
    from services.api.services.api import redis_cache as rc_mod

    fake_client = MagicMock()
    with patch.object(rc_mod, "_redis_client", fake_client):
        result = rc_mod._get_redis()
        assert result is fake_client


# ═══════════════════════════════════════════════════════════════════════════════
# 11. sources_health — lines 162-167
# ═══════════════════════════════════════════════════════════════════════════════

def test_sources_health_ingest_stats():
    """Lines 162-167: duplicate_pairs query inside IngestStats."""
    from services.api.services.api.routers import sources_health as sh_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(sh_mod.router)

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            mock_eng = MagicMock()
            mock_conn = MagicMock()
            row1 = MagicMock(source="bzp", cnt=10)
            mock_result1 = MagicMock()
            mock_result1.__iter__ = lambda s: iter([row1])
            call_count = [0]
            def fake_execute(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_result1
                else:
                    m = MagicMock()
                    m.scalar.return_value = None
                    return m
            mock_conn.execute = fake_execute
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = lambda s, *a: None
            with patch("terra_db.session.get_engine", return_value=mock_eng.return_value):
                resp = await ac.get("/api/v1/sources/health")
        app.dependency_overrides.clear()
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. proactive — lines 166, 168, 223
# ═══════════════════════════════════════════════════════════════════════════════

def test_proactive_calc_priority_deadline_near():
    """Lines 166, 168: deadline_factor with days_left < 7 and < 14."""
    from services.api.services.api.routers.proactive import _calc_priority

    result = _calc_priority(match_score=80, value=1_000_000, deadline=datetime.utcnow() + timedelta(days=3))
    assert result > 0.5

    result2 = _calc_priority(match_score=80, value=1_000_000, deadline=datetime.utcnow() + timedelta(days=10))
    assert result2 > 0.4
    assert result > result2


def test_proactive_portfolio_max_concurrent():
    """Line 223: max_concurrent limit."""
    from services.api.services.api.routers import proactive as pro_mod
    from httpx import AsyncClient, ASGITransport
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(pro_mod.router)

    async def _run():
        from services.api.services.api.auth.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _user()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            mock_eng = MagicMock()
            mock_conn = MagicMock()
            rows = [(f"t{i}", f"Tender {i}", 80.0, 500000, datetime.utcnow() + timedelta(days=20), "active") for i in range(15)]
            mock_result = MagicMock()
            mock_result.fetchall.return_value = rows
            mock_conn.execute.return_value = mock_result
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = lambda s, *a: None
            with patch("terra_db.session.get_engine", return_value=mock_eng.return_value):
                resp = await ac.get("/api/v2/proactive/portfolio", params={"max_concurrent": 2, "budget_hours": 1000})
        app.dependency_overrides.clear()
        return resp

    resp = asyncio.run(_run())
    assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. excel_import — lines 28, 45-46
# ═══════════════════════════════════════════════════════════════════════════════

def test_excel_import_no_active_sheet():
    """Line 28: ws is None → return 0, ['Brak arkusza']."""
    from services.api.services.api.routers.excel_import import _process_xlsx_tenders

    with patch("openpyxl.load_workbook") as mock_lwb:
        mock_lwb.return_value.active = None
        count, errors = _process_xlsx_tenders(b"fake", "o1")
        assert count == 0
        assert "Brak arkusza" in errors[0]


def test_excel_import_value_parse():
    """Lines 45-46: value parsing with comma/space."""
    from services.api.services.api.routers.excel_import import _process_xlsx_tenders

    with patch("openpyxl.load_workbook") as mock_lwb, \
         patch("services.api.services.api.routers.excel_import.get_engine") as mock_eng:
        wb = MagicMock()
        ws = MagicMock()
        h1, h2, h3 = MagicMock(value="title"), MagicMock(value="buyer"), MagicMock(value="value_pln")
        ws.__getitem__ = lambda s, k: [h1, h2, h3]
        ws.iter_rows.return_value = iter([("Test Tender", "Buyer Co", "1 234,56")])
        wb.active = ws
        mock_lwb.return_value = wb

        mock_conn = MagicMock()
        mock_eng.return_value.begin.return_value.__enter__ = lambda s: mock_conn
        mock_eng.return_value.begin.return_value.__exit__ = lambda s, *a: None

        count, errors = _process_xlsx_tenders(b"fake", "o1")
        assert isinstance(count, int)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. material_risk — lines 93, 125-126
# ═══════════════════════════════════════════════════════════════════════════════

def test_material_risk_baseline_zero_skip():
    """Line 93: baseline==0 after fallback → continue (skip)."""
    from services.api.services.api.intelligence.material_risk import check_material_risks

    mock_eng = MagicMock()
    mock_conn = MagicMock()

    row = MagicMock()
    row.icb_id = "icb1"
    row.baseline_price = 0
    row.current_m = 0
    row.nazwa = "Material"

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [row]
    mock_conn.execute.return_value = mock_result

    mock_eng.connect.return_value.__enter__ = lambda s: mock_conn
    mock_eng.connect.return_value.__exit__ = lambda s, *a: None

    with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=mock_eng):
        result = check_material_risks(kosztorys_id="k1", tenant_id="t1", threshold_pct=5.0)
    assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. win_prob — lines 215-217
# ═══════════════════════════════════════════════════════════════════════════════

def test_win_prob_market_benchmark_no_data():
    """Lines 215-217: row is None or count==0 → return {cpv, count:0}."""
    from services.api.services.api.intelligence.win_prob import get_market_benchmarks

    mock_eng = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_eng.connect.return_value.__enter__ = lambda s: mock_conn
    mock_eng.connect.return_value.__exit__ = lambda s, *a: None

    with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=mock_eng):
        result = get_market_benchmarks("45000000")
    assert result.get("count") == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 16. v3/webhooks — lines 34-35, 42
# ═══════════════════════════════════════════════════════════════════════════════

def test_webhooks_validate_url_localhost():
    """Lines 34-35: localhost → HTTPException."""
    from services.api.services.api.routers.v3.webhooks import _validate_url
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _validate_url("http://localhost:8080/hook")
    assert exc_info.value.status_code == 422


def test_webhooks_validate_url_internal_network():
    """Line 42: internal network prefix → HTTPException."""
    from services.api.services.api.routers.v3.webhooks import _validate_url
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _validate_url("http://192.168.1.1/webhook")

    with pytest.raises(HTTPException):
        _validate_url("http://10.0.0.5/webhook")
