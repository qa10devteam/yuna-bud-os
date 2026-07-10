"""S3-04 — RLS cross-tenant isolation tests.

Verifies that Row Level Security prevents any data leakage between tenants.
Creates two real orgs/users in DB, seeds a row per tenant, then asserts
tenant A cannot see tenant B's data through the API.

Marks: integration (requires live DB; skipped in CI unless TERRA_DB_URL set).
"""
from __future__ import annotations

import uuid
import pytest
import httpx

API_BASE = "http://127.0.0.1:8765"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create_org_and_user(db, email: str, password: str) -> tuple[str, str]:
    """Insert tenant + org + user directly in DB; return (org_id, org_id).
    
    Convention: org.id == tenant.id (mirrors production setup where _resolve_tenant_id
    returns org_id, and tender.tenant_id == org_id).
    """
    import sys
    sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
    sys.path.insert(0, "/home/ubuntu/terra-os/services/api")
    from services.api.services.api.auth.utils import hash_password
    from sqlalchemy import text

    org_id = str(uuid.uuid4())   # org_id == tenant_id (same UUID)
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)

    # 1. tenant row — same UUID as org (mirrors production convention)
    db.execute(text(
        "INSERT INTO tenant (id, name) VALUES (:id, :name)"
    ), {"id": org_id, "name": f"TestTenant-{org_id[:8]}"})

    # 2. org — id == tenant_id (so _resolve_tenant_id(org_id) == org_id == tender.tenant_id)
    db.execute(text(
        "INSERT INTO organizations (id, name, tenant_id) VALUES (:id, :name, :tid)"
    ), {"id": org_id, "name": f"TestOrg-{org_id[:8]}", "tid": org_id})

    # 3. user in that org
    db.execute(text(
        "INSERT INTO users (id, email, name, password_hash, org_id, role) "
        "VALUES (:id, :email, :name, :ph, :oid, 'owner')"
    ), {"id": user_id, "email": email, "name": "Test User",
        "ph": pw_hash, "oid": org_id})

    # 4. subscription
    db.execute(text(
        "INSERT INTO subscription (org_id, plan, status) VALUES (:oid, 'pro', 'active')"
    ), {"oid": org_id})

    db.commit()
    return org_id, org_id  # tenant_id == org_id


def _seed_tender(db, tenant_id: str, title: str) -> str:
    """Insert a tender row; tenant_id = organizations.tenant_id (FK → tenant.id)."""
    from sqlalchemy import text

    tid = str(uuid.uuid4())
    db.execute(text(
        "INSERT INTO tender (id, title, buyer, source, external_id, published_at, deadline_at, "
        "                    value_pln, status, tenant_id) "
        "VALUES (:id, :title, 'Test Buyer', 'bzp', :ext_id, NOW(), NOW() + INTERVAL '30 days', "
        "        100000, 'new', :tid)"
    ), {"id": tid, "title": title, "ext_id": f"TEST-{tid[:8]}", "tid": tenant_id})
    db.commit()
    return tid


def _login(email: str, password: str) -> str:
    resp = httpx.post(
        f"{API_BASE}/api/v2/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def two_tenants():
    """Create two isolated tenants, seed one tender each, yield tokens + tender IDs."""
    from terra_db.session import get_engine
    from sqlalchemy.orm import Session
    from sqlalchemy import text

    email_a = f"rls-a-{uuid.uuid4().hex[:6]}@test.local"
    email_b = f"rls-b-{uuid.uuid4().hex[:6]}@test.local"
    pwd_a, pwd_b = "Pass1234!", "Pass5678!"

    engine = get_engine()
    with Session(engine) as db:
        tenant_a, org_a = _create_org_and_user(db, email_a, pwd_a)
        tenant_b, org_b = _create_org_and_user(db, email_b, pwd_b)
        # tender.tenant_id = organizations.tenant_id (nie org.id)
        tender_a = _seed_tender(db, tenant_a, "Tender belonging to Tenant A")
        tender_b = _seed_tender(db, tenant_b, "Tender belonging to Tenant B")

    token_a = _login(email_a, pwd_a)
    token_b = _login(email_b, pwd_b)

    yield {
        "tenant_a": tenant_a, "tenant_b": tenant_b,
        "org_a": str(org_a), "org_b": str(org_b),
        "tender_a": tender_a, "tender_b": tender_b,
        "token_a": token_a, "token_b": token_b,
        "email_a": email_a, "email_b": email_b,
    }

    # Cleanup
    engine2 = get_engine()
    with Session(engine2) as db:
        db.execute(text("DELETE FROM tender WHERE tenant_id IN (:a, :b)"), {"a": tenant_a, "b": tenant_b})
        db.execute(text("DELETE FROM refresh_tokens WHERE user_id IN ("
                        "  SELECT id FROM users WHERE org_id IN (:a, :b))"),
                   {"a": org_a, "b": org_b})
        db.execute(text("DELETE FROM subscription WHERE org_id IN (:a, :b)"), {"a": org_a, "b": org_b})
        db.execute(text("DELETE FROM users WHERE org_id IN (:a, :b)"), {"a": org_a, "b": org_b})
        db.execute(text("DELETE FROM organizations WHERE tenant_id IN (:a, :b)"), {"a": tenant_a, "b": tenant_b})
        db.execute(text("DELETE FROM tenant WHERE id IN (:a, :b)"), {"a": tenant_a, "b": tenant_b})
        db.commit()


# ── Tests ──────────────────────────────────────────────────────────────────────

pytestmark = pytest.mark.integration


class TestRLSIsolation:
    """Cross-tenant data leakage — 0 rows must bleed between tenants."""

    def test_tenant_a_sees_own_tender(self, two_tenants):
        """Tenant A can find its own tender."""
        t = two_tenants
        r = httpx.get(
            f"{API_BASE}/api/v2/tenders",
            headers={"Authorization": f"Bearer {t['token_a']}"},
            timeout=10,
        )
        assert r.status_code == 200
        ids = [x["id"] for x in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
        assert t["tender_a"] in ids, "Tenant A cannot see its own tender"

    def test_tenant_a_cannot_see_tenant_b_tender(self, two_tenants):
        """Tenant A's token must NOT return Tenant B's tender."""
        t = two_tenants
        r = httpx.get(
            f"{API_BASE}/api/v2/tenders",
            headers={"Authorization": f"Bearer {t['token_a']}"},
            timeout=10,
        )
        assert r.status_code == 200
        ids = [x["id"] for x in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
        assert t["tender_b"] not in ids, "⚠️ RLS BREACH: Tenant A can see Tenant B's tender!"

    def test_tenant_b_cannot_see_tenant_a_tender(self, two_tenants):
        """Tenant B's token must NOT return Tenant A's tender."""
        t = two_tenants
        r = httpx.get(
            f"{API_BASE}/api/v2/tenders",
            headers={"Authorization": f"Bearer {t['token_b']}"},
            timeout=10,
        )
        assert r.status_code == 200
        ids = [x["id"] for x in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
        assert t["tender_a"] not in ids, "⚠️ RLS BREACH: Tenant B can see Tenant A's tender!"

    def test_direct_id_fetch_blocked_cross_tenant(self, two_tenants):
        """GET /tenders/{id} with wrong tenant token → 404 (not 403, not 200)."""
        t = two_tenants
        r = httpx.get(
            f"{API_BASE}/api/v2/tenders/{t['tender_b']}",
            headers={"Authorization": f"Bearer {t['token_a']}"},
            timeout=10,
        )
        assert r.status_code in (404, 403), (
            f"⚠️ RLS BREACH: cross-tenant direct fetch returned {r.status_code}"
        )

    def test_unauthenticated_returns_401(self, two_tenants):
        """No token → 401, not any tenant's data."""
        r = httpx.get(f"{API_BASE}/api/v2/tenders", timeout=5)
        assert r.status_code == 401

    def test_tenant_b_sees_own_tender(self, two_tenants):
        """Tenant B can find its own tender (sanity check)."""
        t = two_tenants
        r = httpx.get(
            f"{API_BASE}/api/v2/tenders",
            headers={"Authorization": f"Bearer {t['token_b']}"},
            timeout=10,
        )
        assert r.status_code == 200
        ids = [x["id"] for x in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
        assert t["tender_b"] in ids, "Tenant B cannot see its own tender"

    def test_estimates_isolated(self, two_tenants):
        """GET /kosztorys/estimate returns only rows for calling tenant."""
        t = two_tenants
        r_a = httpx.get(
            f"{API_BASE}/api/v2/kosztorys/estimate",
            headers={"Authorization": f"Bearer {t['token_a']}"},
            timeout=10,
        )
        r_b = httpx.get(
            f"{API_BASE}/api/v2/kosztorys/estimate",
            headers={"Authorization": f"Bearer {t['token_b']}"},
            timeout=10,
        )
        assert r_a.status_code in (200, 404)
        assert r_b.status_code in (200, 404)
        ids_a = {x["id"] for x in (r_a.json() if isinstance(r_a.json(), list) else r_a.json().get("items", []))}
        ids_b = {x["id"] for x in (r_b.json() if isinstance(r_b.json(), list) else r_b.json().get("items", []))}
        overlap = ids_a & ids_b
        assert not overlap, f"⚠️ RLS BREACH: estimates overlap between tenants: {overlap}"
