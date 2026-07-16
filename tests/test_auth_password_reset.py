"""P3-1: Tests for password reset endpoints backed by DB table.

Tests:
  - test_forgot_password_returns_200: always 200 even for unknown email
  - test_reset_password_invalid_token_returns_400: bad token → 400
  - test_reset_password_expired_token_returns_400: expired token → 400
"""
from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone, timedelta

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")

from httpx import AsyncClient, ASGITransport
import sqlalchemy as sa
from sqlalchemy import text
from terra_db.session import get_engine


def _get_conn():
    """Return a raw SQLAlchemy connection (caller must use as context manager or close it)."""
    engine = get_engine()
    return engine.connect()


def _get_any_user_id() -> str | None:
    """Return the id of any existing user, or None if table is empty."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
        return str(row.id) if row else None


def _insert_reset_token(user_id: str, token: str, expires_at: datetime) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) "
                "VALUES (:uid, :token, :exp)"
            ),
            {"uid": user_id, "token": token, "exp": expires_at},
        )


def _cleanup_token(token: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM password_reset_tokens WHERE token = :token"),
            {"token": token},
        )


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_returns_200(app):
    """POST /forgot-password always returns 200 regardless of whether email exists."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Known non-existent email
        resp = await ac.post(
            "/api/v2/auth/forgot-password",
            json={"email": "no-such-user-xyz@example.invalid"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body


@pytest.mark.asyncio
async def test_forgot_password_returns_200_existing_email(app):
    """POST /forgot-password with a real user email also returns 200."""
    # Try with the demo user email; if not present just use an unknown one
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v2/auth/forgot-password",
            json={"email": "demo@terra-os.pl"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body


@pytest.mark.asyncio
async def test_reset_password_invalid_token_returns_400(app):
    """POST /reset-password with a bogus token → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v2/auth/reset-password",
            json={"token": "totally-invalid-token-that-does-not-exist", "new_password": "NewPass99!Secure"},
        )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert detail  # some error message present


@pytest.mark.asyncio
async def test_reset_password_expired_token_returns_400(app):
    """POST /reset-password with an expired token → 400."""
    user_id = _get_any_user_id()
    if user_id is None:
        pytest.skip("No users in DB — skipping expired token test")

    expired_token = "test-expired-token-p3-1-unique-xyz"
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)  # already expired

    _insert_reset_token(user_id, expired_token, past_time)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v2/auth/reset-password",
                json={"token": expired_token, "new_password": "NewPass99!Secure"},
            )
        assert resp.status_code == 400
        detail = resp.json().get("detail", "")
        assert detail
    finally:
        _cleanup_token(expired_token)
