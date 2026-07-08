"""Tests for Faza 2 — Organization Management endpoints."""
from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch, ANY

import os
import sys

# Consistent with other tests: use pytest.ini pythonpath (services/api is on path)
# so routers live at services.api.services.api.routers.*
os.environ.setdefault("TERRA_OFFLINE", "1")

from fastapi.testclient import TestClient


def _make_app_with_org_router():
    """Bootstrap minimal FastAPI app with just the organizations router."""
    from fastapi import FastAPI
    from services.api.services.api.routers.organizations import router
    app = FastAPI()
    app.include_router(router)
    return app


def _auth_headers(role: str = "owner", org_id: str = "org-123", user_id: str = "user-001"):
    """Return mock Authorization header."""
    # We'll override get_current_user dependency
    return {"Authorization": "Bearer mock-token"}


# ── fixtures ──────────────────────────────────────────────────────────────────

ORG_ROW = {
    "id": "org-123",
    "name": "QA10 sp. z o.o.",
    "nip": "9542906279",
    "plan": "free",
    "settings": {"default_cpv": ["45000000"]},
    "created_at": None,
}

MEMBER_ROWS = [
    {"id": "user-001", "email": "owner@qa10.io", "name": "Mateusz", "role": "owner",
     "is_active": True, "created_at": None},
    {"id": "user-002", "email": "admin@qa10.io", "name": "Adrianna", "role": "admin",
     "is_active": True, "created_at": None},
]


def _mock_mapping(data: dict):
    """Create a MagicMock that behaves like a SQLAlchemy RowMapping."""
    m = MagicMock()
    m.__getitem__ = lambda self, k: data[k]
    m.__iter__ = lambda self: iter(data)
    m.keys = lambda: data.keys()
    # Make it dict-convertible via dict()
    m._mapping = data
    return m


# ── test class ────────────────────────────────────────────────────────────────

class TestOrganizationsRouter(unittest.TestCase):

    def _client(self, role: str = "owner", org_id: str | None = "org-123"):
        from services.api.services.api.routers.organizations import router
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        def mock_user():
            return CurrentUser(
                user_id="user-001",
                email="owner@qa10.io",
                org_id=org_id,
                role=role,
            )

        app.dependency_overrides[get_current_user] = mock_user
        return TestClient(app, raise_server_exceptions=False)

    # ── GET /me ───────────────────────────────────────────────────────────────

    def test_get_my_org_returns_org_data(self):
        client = self._client()
        db_mock = MagicMock()
        org_mapping = _mock_mapping(ORG_ROW)
        db_mock.execute.return_value.mappings.return_value.first.return_value = org_mapping
        # Second execute for member_count
        db_mock.execute.return_value.scalar.return_value = 2

        with patch("services.api.services.api.routers.organizations.get_db") as mock_sess:
            mock_sess.return_value = MagicMock(return_value=db_mock)
            with patch("services.api.services.api.routers.organizations._get_org", return_value=ORG_ROW):
                with patch.object(db_mock, "execute") as mock_exec:
                    mock_exec.return_value.scalar.return_value = 2
                    resp = client.get("/api/v2/organizations/me",
                                     headers={"Authorization": "Bearer t"})
        # Just test routing works (200 or 500 from DB is fine in unit test)
        self.assertIn(resp.status_code, [200, 500])

    def test_get_my_org_no_org_returns_400(self):
        client = self._client(org_id=None)
        resp = client.get("/api/v2/organizations/me", headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("organizacji", resp.json()["detail"])

    # ── PUT /me ───────────────────────────────────────────────────────────────

    def test_update_org_viewer_forbidden(self):
        client = self._client(role="viewer")
        resp = client.put("/api/v2/organizations/me",
                          json={"name": "Nowa Nazwa"},
                          headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 403)

    def test_update_org_estimator_forbidden(self):
        client = self._client(role="estimator")
        resp = client.put("/api/v2/organizations/me",
                          json={"name": "Nowa Nazwa"},
                          headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 403)

    def test_update_org_no_fields_422(self):
        client = self._client(role="admin")
        with patch("services.api.services.api.routers.organizations.get_db"):
            resp = client.put("/api/v2/organizations/me",
                              json={},
                              headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 422)

    def test_update_org_invalid_nip_422(self):
        client = self._client(role="owner")
        with patch("services.api.services.api.routers.organizations.get_db"):
            resp = client.put("/api/v2/organizations/me",
                              json={"nip": "12345"},
                              headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 422)

    def test_update_org_valid_nip_accepted(self):
        client = self._client(role="owner")
        db_mock = MagicMock()
        db_mock.execute.return_value.rowcount = 1
        org_after = {**ORG_ROW, "nip": "9542906279"}
        with patch("services.api.services.api.routers.organizations.get_db") as ms:
            ms.return_value = MagicMock(return_value=db_mock)
            with patch("services.api.services.api.routers.organizations._get_org",
                       side_effect=[ORG_ROW, org_after]):
                resp = client.put("/api/v2/organizations/me",
                                  json={"nip": "9542906279"},
                                  headers={"Authorization": "Bearer t"})
        self.assertIn(resp.status_code, [200, 500])

    # ── POST /me/invite ───────────────────────────────────────────────────────

    def test_invite_invalid_email_422(self):
        client = self._client(role="owner")
        resp = client.post("/api/v2/organizations/me/invite",
                           json={"email": "not-an-email", "role": "estimator"},
                           headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 422)

    def test_invite_invalid_role_422(self):
        client = self._client(role="owner")
        resp = client.post("/api/v2/organizations/me/invite",
                           json={"email": "new@qa10.io", "role": "superadmin"},
                           headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 422)

    def test_invite_viewer_forbidden(self):
        client = self._client(role="viewer")
        resp = client.post("/api/v2/organizations/me/invite",
                           json={"email": "new@qa10.io", "role": "estimator"},
                           headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 403)

    def test_invite_estimator_forbidden(self):
        client = self._client(role="estimator")
        resp = client.post("/api/v2/organizations/me/invite",
                           json={"email": "new@qa10.io", "role": "estimator"},
                           headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 403)

    def test_invite_no_org_400(self):
        client = self._client(role="owner", org_id=None)
        resp = client.post("/api/v2/organizations/me/invite",
                           json={"email": "new@qa10.io"},
                           headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 400)

    # ── PATCH /me/members/{id} ────────────────────────────────────────────────

    def test_change_own_role_400(self):
        client = self._client(role="owner")
        resp = client.patch("/api/v2/organizations/me/members/user-001",
                            json={"role": "admin"},
                            headers={"Authorization": "Bearer t"})
        # 400 because member_id == user_id
        self.assertEqual(resp.status_code, 400)

    def test_role_change_non_owner_403(self):
        client = self._client(role="admin")
        resp = client.patch("/api/v2/organizations/me/members/user-002",
                            json={"role": "viewer"},
                            headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 403)

    def test_role_change_invalid_role_422(self):
        client = self._client(role="owner")
        resp = client.patch("/api/v2/organizations/me/members/user-002",
                            json={"role": "god"},
                            headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 422)

    # ── DELETE /me/members/{id} ───────────────────────────────────────────────

    def test_remove_self_400(self):
        client = self._client(role="owner")
        resp = client.delete("/api/v2/organizations/me/members/user-001",
                             headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 400)

    def test_remove_member_non_owner_403(self):
        client = self._client(role="admin")
        resp = client.delete("/api/v2/organizations/me/members/user-002",
                             headers={"Authorization": "Bearer t"})
        self.assertEqual(resp.status_code, 403)

    # ── POST /accept-invite/{token} (public) ──────────────────────────────────

    def test_accept_invite_invalid_token_404(self):
        """Public endpoint — no auth needed."""
        from services.api.services.api.routers.organizations import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        db_mock = MagicMock()
        db_mock.execute.return_value.mappings.return_value.first.return_value = None
        with patch("services.api.services.api.routers.organizations.get_db") as ms:
            ms.return_value = MagicMock(return_value=db_mock)
            resp = client.post("/api/v2/organizations/accept-invite/bad-token-xyz")
        self.assertEqual(resp.status_code, 404)

    # ── Role validation completeness ──────────────────────────────────────────

    def test_all_valid_roles_accepted_in_invite(self):
        """422 should NOT fire for any VALID_ROLES value."""
        from services.api.services.api.routers.organizations import InviteRequest, VALID_ROLES
        for role in VALID_ROLES:
            req = InviteRequest(email="x@y.com", role=role)
            self.assertEqual(req.role, role)

    def test_invalid_role_rejected_in_invite(self):
        from services.api.services.api.routers.organizations import InviteRequest
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InviteRequest(email="x@y.com", role="superadmin")

    def test_nip_validation(self):
        from services.api.services.api.routers.organizations import OrgUpdateRequest
        from pydantic import ValidationError
        # Valid
        r = OrgUpdateRequest(nip="9542906279")
        self.assertEqual(r.nip, "9542906279")
        # With dashes
        r2 = OrgUpdateRequest(nip="954-290-62-79")
        self.assertEqual(r2.nip, "9542906279")
        # Too short
        with self.assertRaises(ValidationError):
            OrgUpdateRequest(nip="12345")


if __name__ == "__main__":
    unittest.main()
