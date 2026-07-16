"""P3-6 — Tests for forgot-password and reset-password endpoints.

The router uses:
  - A SQLAlchemy Session (via `get_db` dependency) to SELECT the user
  - A raw engine (`get_engine()`) to INSERT/SELECT password_reset_tokens
  - `send_password_reset_email` for email delivery

Covers:
  - POST /api/v2/auth/forgot-password with a known email → 200 + email sent
  - POST /api/v2/auth/forgot-password with unknown email → 200, no email (anti-enumeration)
  - POST /api/v2/auth/forgot-password: both paths return the same message
  - POST /api/v2/auth/reset-password with invalid/unknown token → 400
  - POST /api/v2/auth/reset-password with expired token → 400
  - POST /api/v2/auth/reset-password with already-used token → 400
  - POST /api/v2/auth/reset-password with valid token → 200, password updated
  - POST /api/v2/auth/reset-password weak password → 422
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_app():
    from fastapi import FastAPI
    from services.api.services.api.auth.router import router
    app = FastAPI()
    app.include_router(router)
    return app


def _make_db_session(user_row=None):
    """Return a mock SQLAlchemy session for the `get_db` dependency."""
    session = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt)
        res = MagicMock()
        res.fetchone.return_value = user_row
        return res

    session.execute = MagicMock(side_effect=_execute)
    session.commit = MagicMock()
    session.close = MagicMock()
    return session


def _make_engine_conn(row=None):
    """Return a mock engine + conn for raw engine.begin() calls."""
    conn = MagicMock()
    res = MagicMock()
    res.fetchone.return_value = row
    conn.execute.return_value = res
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.begin.return_value = conn
    engine.connect.return_value = conn
    return engine, conn


def _client(db_session, engine=None):
    """Build TestClient with mocked DB + engine."""
    from services.api.services.api.auth.router import get_db
    app = _make_app()
    app.dependency_overrides[get_db] = lambda: db_session
    if engine is None:
        engine, _ = _make_engine_conn()
    return TestClient(app, raise_server_exceptions=False), engine


# ── forgot-password ────────────────────────────────────────────────────────────

class TestForgotPassword:
    def test_known_email_returns_200_and_sends_email(self):
        """Valid registered email → 200 with generic success message, email sent."""
        user_row = MagicMock()
        user_row.id = str(uuid.uuid4())
        user_row.email = "alice@example.com"

        db = _make_db_session(user_row=user_row)
        engine, _conn = _make_engine_conn()

        with patch("services.api.services.api.auth.router.send_password_reset_email") as mock_email:
            with patch("services.api.services.api.auth.router.get_engine", return_value=engine):
                app = _make_app()
                from services.api.services.api.auth.router import get_db
                app.dependency_overrides[get_db] = lambda: db
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post(
                    "/api/v2/auth/forgot-password",
                    json={"email": "alice@example.com"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body
        mock_email.assert_called_once()

    def test_unknown_email_also_returns_200_no_email(self):
        """Anti-enumeration: unknown email still returns 200, email NOT sent."""
        db = _make_db_session(user_row=None)
        engine, _ = _make_engine_conn()

        with patch("services.api.services.api.auth.router.send_password_reset_email") as mock_email:
            with patch("services.api.services.api.auth.router.get_engine", return_value=engine):
                app = _make_app()
                from services.api.services.api.auth.router import get_db
                app.dependency_overrides[get_db] = lambda: db
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post(
                    "/api/v2/auth/forgot-password",
                    json={"email": "nobody@example.com"},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body
        mock_email.assert_not_called()

    def test_same_message_for_known_and_unknown(self):
        """Known and unknown addresses return the same message body (no leaking)."""
        user_row = MagicMock()
        user_row.id = str(uuid.uuid4())
        user_row.email = "k@x.com"

        engine_k, _ = _make_engine_conn()
        engine_u, _ = _make_engine_conn()

        with patch("services.api.services.api.auth.router.send_password_reset_email"):
            with patch("services.api.services.api.auth.router.get_engine", return_value=engine_k):
                app_k = _make_app()
                from services.api.services.api.auth.router import get_db
                app_k.dependency_overrides[get_db] = lambda: _make_db_session(user_row)
                r_known = TestClient(app_k, raise_server_exceptions=False).post(
                    "/api/v2/auth/forgot-password", json={"email": "k@x.com"}
                )

        with patch("services.api.services.api.auth.router.send_password_reset_email"):
            with patch("services.api.services.api.auth.router.get_engine", return_value=engine_u):
                app_u = _make_app()
                app_u.dependency_overrides[get_db] = lambda: _make_db_session(None)
                r_unknown = TestClient(app_u, raise_server_exceptions=False).post(
                    "/api/v2/auth/forgot-password", json={"email": "nobody@x.com"}
                )

        assert r_known.json()["message"] == r_unknown.json()["message"]


# ── reset-password ─────────────────────────────────────────────────────────────

class TestResetPassword:
    def _reset_client(self, token_row=None, update_row=None):
        """Build a client where engine.begin() returns mocked token + user rows."""
        db = _make_db_session()

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        call_count = [0]

        def _execute(stmt, params=None):
            sql = str(stmt)
            res = MagicMock()
            if "SELECT id, user_id, expires_at, used_at" in sql:
                res.fetchone.return_value = token_row
            elif "UPDATE users SET password_hash" in sql:
                res.fetchone.return_value = update_row
            else:
                res.fetchone.return_value = None
            return res

        conn.execute = MagicMock(side_effect=_execute)
        engine = MagicMock()
        engine.begin.return_value = conn

        with patch("services.api.services.api.auth.router.get_engine", return_value=engine):
            app = _make_app()
            from services.api.services.api.auth.router import get_db
            app.dependency_overrides[get_db] = lambda: db
            client = TestClient(app, raise_server_exceptions=False)
        return client, engine

    def test_invalid_token_returns_400(self):
        """Bogus / non-existent token → 400."""
        client, engine = self._reset_client(token_row=None)
        with patch("services.api.services.api.auth.router.get_engine", return_value=engine):
            app = _make_app()
            from services.api.services.api.auth.router import get_db
            db = _make_db_session()
            app.dependency_overrides[get_db] = lambda: db
            resp = TestClient(app, raise_server_exceptions=False).post(
                "/api/v2/auth/reset-password",
                json={"token": "not-a-real-token", "new_password": "NewPassword123!"},
            )
        assert resp.status_code == 400
        assert "detail" in resp.json()

    def test_expired_token_returns_400(self):
        """Expired token (expires_at in the past) → 400."""
        token_row = MagicMock()
        token_row.id = str(uuid.uuid4())
        token_row.user_id = str(uuid.uuid4())
        token_row.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
        token_row.used_at = None

        with patch("services.api.services.api.auth.router.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)

            def _execute(stmt, params=None):
                res = MagicMock()
                res.fetchone.return_value = token_row
                return res

            conn.execute = MagicMock(side_effect=_execute)
            engine = MagicMock()
            engine.begin.return_value = conn
            mock_ge.return_value = engine

            app = _make_app()
            from services.api.services.api.auth.router import get_db
            app.dependency_overrides[get_db] = lambda: _make_db_session()
            resp = TestClient(app, raise_server_exceptions=False).post(
                "/api/v2/auth/reset-password",
                json={"token": "expired-token", "new_password": "NewPassword123!"},
            )

        assert resp.status_code == 400

    def test_already_used_token_returns_400(self):
        """Token with used_at set → 400."""
        token_row = MagicMock()
        token_row.id = str(uuid.uuid4())
        token_row.user_id = str(uuid.uuid4())
        token_row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token_row.used_at = datetime.now(timezone.utc) - timedelta(minutes=5)

        with patch("services.api.services.api.auth.router.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)
            res = MagicMock()
            res.fetchone.return_value = token_row
            conn.execute.return_value = res
            engine = MagicMock()
            engine.begin.return_value = conn
            mock_ge.return_value = engine

            app = _make_app()
            from services.api.services.api.auth.router import get_db
            app.dependency_overrides[get_db] = lambda: _make_db_session()
            resp = TestClient(app, raise_server_exceptions=False).post(
                "/api/v2/auth/reset-password",
                json={"token": "used-token", "new_password": "NewPassword123!"},
            )

        assert resp.status_code == 400

    def test_valid_token_returns_200(self):
        """Valid, unused, unexpired token → 200, password updated."""
        token_row = MagicMock()
        token_row.id = str(uuid.uuid4())
        token_row.user_id = str(uuid.uuid4())
        token_row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token_row.used_at = None

        update_row = MagicMock()
        update_row.id = str(uuid.uuid4())

        with patch("services.api.services.api.auth.router.get_engine") as mock_ge:
            conn = MagicMock()
            conn.__enter__ = MagicMock(return_value=conn)
            conn.__exit__ = MagicMock(return_value=False)

            call_results = [token_row, None, update_row]  # SELECT, UPDATE tokens, UPDATE users
            call_idx = [0]

            def _execute(stmt, params=None):
                sql = str(stmt)
                res = MagicMock()
                if "SELECT id, user_id, expires_at, used_at" in sql:
                    res.fetchone.return_value = token_row
                elif "UPDATE users SET password_hash" in sql:
                    res.fetchone.return_value = update_row
                else:
                    res.fetchone.return_value = None
                return res

            conn.execute = MagicMock(side_effect=_execute)
            engine = MagicMock()
            engine.begin.return_value = conn
            mock_ge.return_value = engine

            app = _make_app()
            from services.api.services.api.auth.router import get_db
            app.dependency_overrides[get_db] = lambda: _make_db_session()
            resp = TestClient(app, raise_server_exceptions=False).post(
                "/api/v2/auth/reset-password",
                json={"token": "valid-token", "new_password": "MyNewPassword123!"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body

    def test_weak_password_returns_422(self):
        """Password < 8 chars → 422 validation error before hitting DB."""
        with patch("services.api.services.api.auth.router.get_engine") as mock_ge:
            engine, _ = _make_engine_conn()
            mock_ge.return_value = engine

            app = _make_app()
            from services.api.services.api.auth.router import get_db
            app.dependency_overrides[get_db] = lambda: _make_db_session()
            resp = TestClient(app, raise_server_exceptions=False).post(
                "/api/v2/auth/reset-password",
                json={"token": "any-token", "new_password": "short"},
            )

        assert resp.status_code == 422
