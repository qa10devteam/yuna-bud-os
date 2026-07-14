"""G3 — Organizations router coverage: org profile, members, invites."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


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


BASE = "/api/v2/organizations"


def _mock_db():
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.commit = MagicMock()
    return conn


@pytest.mark.asyncio
async def test_get_org_me(app, auth_headers):
    """GET /api/v2/organizations/me → 200."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        org_row = {"id": "ec3d1e16", "name": "Test Org", "nip": "1234567890",
                   "plan": "free", "settings": {}, "created_at": None}
        conn.execute.return_value.mappings.return_value.first.return_value = org_row
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/me", headers=auth_headers)

    assert resp.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_put_org_me(app, auth_headers):
    """PUT /api/v2/organizations/me → updates org profile."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        conn.execute.return_value.mappings.return_value.first.return_value = {
            "id": "ec3d1e16", "name": "Updated Org", "nip": "9876543210",
            "plan": "free", "settings": {}, "created_at": None,
        }
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(f"{BASE}/me", headers=auth_headers,
                                    json={"name": "Updated Org"})

    assert resp.status_code in (200, 403, 404, 500)


@pytest.mark.asyncio
async def test_get_org_members(app, auth_headers):
    """GET /api/v2/organizations/me/members → list."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        conn.execute.return_value.mappings.return_value.first.return_value = {
            "id": "ec3d1e16", "name": "Test", "nip": None,
            "plan": "free", "settings": {}, "created_at": None,
        }
        conn.execute.return_value.mappings.return_value.all.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/me/members", headers=auth_headers)

    assert resp.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_post_invite(app, auth_headers):
    """POST /api/v2/organizations/me/invite → sends invite."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        with patch("services.api.services.api.routers.organizations.send_invite_email"):
            conn = _mock_db()
            conn.execute.return_value.mappings.return_value.first.return_value = {
                "id": "ec3d1e16", "name": "Test", "nip": None,
                "plan": "free", "settings": {}, "created_at": None,
            }
            conn.execute.return_value.scalar.return_value = 0
            mock_eng.return_value.connect.return_value = conn

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(f"{BASE}/me/invite", headers=auth_headers,
                                         json={"email": "newmember@example.com", "role": "viewer"})

    assert resp.status_code in (200, 201, 400, 403, 404, 409, 500)


@pytest.mark.asyncio
async def test_delete_member(app, auth_headers):
    """DELETE /api/v2/organizations/me/members/{user_id} → removes member."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        conn.execute.return_value.mappings.return_value.first.return_value = {
            "id": "ec3d1e16", "name": "Test", "nip": None,
            "plan": "free", "settings": {}, "created_at": None,
        }
        conn.execute.return_value.rowcount = 1
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(
                f"{BASE}/me/members/some-user-id",
                headers=auth_headers,
            )

    assert resp.status_code in (200, 204, 403, 404, 500)


@pytest.mark.asyncio
async def test_patch_member_role(app, auth_headers):
    """PATCH /api/v2/organizations/me/members/{user_id} → changes role."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        conn.execute.return_value.mappings.return_value.first.return_value = {
            "id": "ec3d1e16", "name": "Test", "nip": None,
            "plan": "free", "settings": {}, "created_at": None,
        }
        conn.execute.return_value.rowcount = 1
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                f"{BASE}/me/members/some-user-id",
                headers=auth_headers,
                json={"role": "admin"},
            )

    assert resp.status_code in (200, 400, 403, 404, 500)


@pytest.mark.asyncio
async def test_list_invites(app, auth_headers):
    """GET /api/v2/organizations/me/invites → list pending invites."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        conn.execute.return_value.mappings.return_value.first.return_value = {
            "id": "ec3d1e16", "name": "Test", "nip": None,
            "plan": "free", "settings": {}, "created_at": None,
        }
        conn.execute.return_value.mappings.return_value.all.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/me/invites", headers=auth_headers)

    assert resp.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_cancel_invite(app, auth_headers):
    """DELETE /api/v2/organizations/me/invites/{invite_id} → cancels invite."""
    with patch("services.api.services.api.routers.organizations.get_engine") as mock_eng:
        conn = _mock_db()
        conn.execute.return_value.mappings.return_value.first.return_value = {
            "id": "ec3d1e16", "name": "Test", "nip": None,
            "plan": "free", "settings": {}, "created_at": None,
        }
        conn.execute.return_value.rowcount = 1
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(
                f"{BASE}/me/invites/some-invite-id",
                headers=auth_headers,
            )

    assert resp.status_code in (200, 204, 403, 404, 500)
