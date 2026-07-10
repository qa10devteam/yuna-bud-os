"""S5-3 — Smoke tests for P0 endpoints (10 tests).

Tests run against live API at localhost:8765.
Uses real HTTP via httpx — marks: integration (skipped in CI unless DB present).
All tests share a single auth token obtained in module setup.
"""
from __future__ import annotations

import os
import pytest
import httpx

API_BASE = os.getenv("TERRA_API_BASE", "http://127.0.0.1:8765")
TEST_EMAIL = os.getenv("TERRA_TEST_EMAIL", "rsk.centrala@gmail.com")
TEST_PASS = os.getenv("TERRA_TEST_PASS", "demo1234")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def token():
    resp = httpx.post(
        f"{API_BASE}/api/v2/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
        timeout=10,
    )
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── 1. Health ──────────────────────────────────────────────────────────────────

def test_health():
    """GET /api/v2/health → 200, status ok."""
    r = httpx.get(f"{API_BASE}/api/v2/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


# ── 2. Auth ────────────────────────────────────────────────────────────────────

def test_auth_login():
    """POST /api/v2/auth/login → 200, returns access_token."""
    r = httpx.post(
        f"{API_BASE}/api/v2/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
        timeout=5,
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert len(body["access_token"]) > 20


# ── 3. Tenders list ────────────────────────────────────────────────────────────

def test_tenders_list(auth):
    """GET /api/v2/tenders → 200, returns items list."""
    r = httpx.get(f"{API_BASE}/api/v2/tenders?limit=5", headers=auth, timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert "total" in body


# ── 4. Tender detail ───────────────────────────────────────────────────────────

def test_tender_detail(auth):
    """GET /api/v2/tenders/{id} → 200 for first tender in list."""
    tenders = httpx.get(f"{API_BASE}/api/v2/tenders?limit=1", headers=auth, timeout=5).json()
    if not tenders["items"]:
        pytest.skip("No tenders in DB")
    tid = tenders["items"][0]["id"]
    r = httpx.get(f"{API_BASE}/api/v2/tenders/{tid}", headers=auth, timeout=5)
    assert r.status_code == 200
    assert r.json()["id"] == tid


# ── 5. Dashboard stats ─────────────────────────────────────────────────────────

def test_dashboard_stats(auth):
    """GET /api/v2/dashboard/stats → 200, has total_tenders."""
    r = httpx.get(f"{API_BASE}/api/v2/dashboard/stats", headers=auth, timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "total_tenders" in body
    assert isinstance(body["total_tenders"], int)


# ── 6. Notifications ───────────────────────────────────────────────────────────

def test_notifications_list(auth):
    """GET /api/v2/notifications → 200, returns items."""
    r = httpx.get(f"{API_BASE}/api/v2/notifications", headers=auth, timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body


def test_notifications_count(auth):
    """GET /api/v2/notifications/count → 200, unread_count integer."""
    r = httpx.get(f"{API_BASE}/api/v2/notifications/count", headers=auth, timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert "unread_count" in body
    assert isinstance(body["unread_count"], int)


# ── 7. Feature flags ───────────────────────────────────────────────────────────

def test_feature_flags(auth):
    """GET /api/v2/feature-flags → 200, returns list."""
    r = httpx.get(f"{API_BASE}/api/v2/feature-flags", headers=auth, timeout=5, follow_redirects=True)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


# ── 8. Tender alerts ──────────────────────────────────────────────────────────

def test_tender_alerts(auth):
    """GET /api/v2/tender-alerts → 200."""
    r = httpx.get(f"{API_BASE}/api/v2/tender-alerts", headers=auth, timeout=5)
    assert r.status_code == 200


# ── 9. Unauthorized → 401 ─────────────────────────────────────────────────────

def test_tenders_unauthorized():
    """GET /api/v2/tenders without token → 401 or 403."""
    r = httpx.get(f"{API_BASE}/api/v2/tenders", timeout=5)
    assert r.status_code in (401, 403)


# ── 10. Cache: double dashboard hit is fast ────────────────────────────────────

def test_dashboard_cache_second_hit_faster(auth):
    """Second GET /api/v2/dashboard/stats should be served from cache (faster)."""
    import time
    # First hit — warms cache
    t0 = time.monotonic()
    r1 = httpx.get(f"{API_BASE}/api/v2/dashboard/stats", headers=auth, timeout=5)
    t1 = time.monotonic() - t0
    assert r1.status_code == 200

    # Second hit — from cache
    t0 = time.monotonic()
    r2 = httpx.get(f"{API_BASE}/api/v2/dashboard/stats", headers=auth, timeout=5)
    t2 = time.monotonic() - t0
    assert r2.status_code == 200

    # Cache hit should be < 50ms (DB hit can be 100+ms)
    assert t2 < 0.05, f"Cache miss? second hit took {t2*1000:.0f}ms"
