"""Coverage wave 4 — targeted tests for:
1) middleware/ids.py       lines 99-106  (IDS threshold trigger + Redis write error)
2) auth/encryption.py      lines 40-44  (decrypt with live Fernet + InvalidToken)
3) middleware/csrf.py       line  60     (CSRF token mismatch → 403)
4) middleware/tenant.py     lines 67-71  (_on_checkout with active tenant_id)
5) middleware/validation.py lines 23-24  (non-numeric content-length ValueError)
6) middleware/error_boundary.py ~1 stmt  (HTTPException path + audit_service import)
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_scope(method="GET", path="/test", client_ip="1.2.3.4", headers=None, cookies=None):
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode(), v.encode()))
    if cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        raw_headers.append((b"cookie", cookie_str.encode()))
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_ip, 12345) if client_ip else None,
    }


def _req(method="GET", path="/test", client_ip="1.2.3.4", headers=None, cookies=None):
    return Request(_make_scope(method, path, client_ip, headers, cookies))


async def _call_next_200(request):
    return JSONResponse({"ok": True}, status_code=200)


async def _call_next_401(request):
    return JSONResponse({"detail": "Unauthorized"}, status_code=401)


async def _call_next_403(request):
    return JSONResponse({"detail": "Forbidden"}, status_code=403)


def _body(response) -> dict:
    """Decode a Starlette/FastAPI JSONResponse body to a Python dict."""
    raw = response.body
    if isinstance(raw, (bytes, bytearray, memoryview)):
        raw = bytes(raw)
    return json.loads(raw)


# ══════════════════════════════════════════════════════════════════════════════
# 1. middleware/ids.py — lines 99-106
# ══════════════════════════════════════════════════════════════════════════════

class TestIDSMiddlewareThreshold:
    """Cover lines 99-106: IP block on threshold breach + Redis write failure."""

    def setup_method(self, method):
        """Enable IDS for threshold tests."""
        from services.api.services.api.middleware import ids as ids_mod
        ids_mod.IDS_ENABLED = True

    def teardown_method(self, method):
        """Restore IDS to disabled after threshold tests (avoid polluting other tests)."""
        from services.api.services.api.middleware import ids as ids_mod
        ids_mod.IDS_ENABLED = False

    def _get_middleware(self):
        from services.api.services.api.middleware.ids import IDSMiddleware
        mw = IDSMiddleware(app=MagicMock())
        return mw

    def test_threshold_reached_blocks_ip(self):
        """Lines 99-104: when incr >= IDS_THRESHOLD, setex block key + delete counter."""
        from services.api.services.api.middleware import ids as ids_mod

        mw = self._get_middleware()
        mock_redis = MagicMock()
        mock_redis.exists.return_value = False                    # not already blocked
        mock_redis.incr.return_value = ids_mod.IDS_THRESHOLD      # exactly at threshold
        mw._redis = mock_redis

        request = _req(method="POST", path="/api/tenders", client_ip="5.5.5.5")
        result = asyncio.run(mw.dispatch(request, _call_next_401))

        # Response from call_next should still pass through
        assert result.status_code == 401
        # setex called with block key
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert "ids:blocked:5.5.5.5" in call_args[0]
        # counter deleted
        mock_redis.delete.assert_called_once()

    def test_threshold_exceeded_blocks_ip_on_403(self):
        """Lines 99-104: 403 response also triggers IDS tracking + block."""
        from services.api.services.api.middleware import ids as ids_mod

        mw = self._get_middleware()
        mock_redis = MagicMock()
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = ids_mod.IDS_THRESHOLD + 5   # over threshold
        mw._redis = mock_redis

        request = _req(method="GET", path="/api/data", client_ip="6.6.6.6")
        result = asyncio.run(mw.dispatch(request, _call_next_403))

        assert result.status_code == 403
        mock_redis.setex.assert_called_once()
        mock_redis.delete.assert_called_once()

    def test_redis_write_failure_logged_not_raised(self):
        """Line 106: exception in tracking block is caught (not raised)."""
        mw = self._get_middleware()
        mock_redis = MagicMock()
        mock_redis.exists.return_value = False
        mock_redis.incr.side_effect = ConnectionError("Redis down")
        mw._redis = mock_redis

        request = _req(method="POST", path="/api/tenders", client_ip="7.7.7.7")
        # Must NOT raise — exception is swallowed
        result = asyncio.run(mw.dispatch(request, _call_next_401))
        assert result.status_code == 401   # response still returned

    def test_below_threshold_no_block(self):
        """Count below threshold: no setex/delete calls."""
        from services.api.services.api.middleware import ids as ids_mod

        mw = self._get_middleware()
        mock_redis = MagicMock()
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = ids_mod.IDS_THRESHOLD - 1
        mw._redis = mock_redis

        request = _req(method="POST", path="/api/tenders", client_ip="8.8.8.8")
        result = asyncio.run(mw.dispatch(request, _call_next_401))

        assert result.status_code == 401
        mock_redis.setex.assert_not_called()
        mock_redis.delete.assert_not_called()

    def test_ids_block_ttl_used_in_setex(self):
        """Line 99: IDS_BLOCK_TTL is passed as TTL to setex."""
        from services.api.services.api.middleware import ids as ids_mod

        mw = self._get_middleware()
        mock_redis = MagicMock()
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = ids_mod.IDS_THRESHOLD
        mw._redis = mock_redis

        request = _req(method="POST", path="/api/v1/resource", client_ip="9.9.9.9")
        asyncio.run(mw.dispatch(request, _call_next_401))

        call_args = mock_redis.setex.call_args[0]
        assert call_args[1] == ids_mod.IDS_BLOCK_TTL
        assert call_args[2] == "1"


# ══════════════════════════════════════════════════════════════════════════════
# 2. auth/encryption.py — lines 40-44
# ══════════════════════════════════════════════════════════════════════════════

class TestEncryptionDecrypt:
    """Cover lines 40-44: decrypt_field with an active Fernet key."""

    def _reload_with_key(self):
        """Return the encryption module reloaded with a fresh valid key."""
        from cryptography.fernet import Fernet
        valid_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"FIELD_ENCRYPTION_KEY": valid_key}):
            import services.api.services.api.auth.encryption as enc_mod
            importlib.reload(enc_mod)
        # enc_mod._fernet now uses the key baked in at reload time
        return enc_mod

    def test_decrypt_valid_ciphertext(self):
        """Line 41: _fernet.decrypt(...).decode() returns plaintext."""
        enc_mod = self._reload_with_key()
        plaintext = "super-secret-value"
        ciphertext = enc_mod._fernet.encrypt(plaintext.encode()).decode()
        result = enc_mod.decrypt_field(ciphertext)
        assert result == plaintext

    def test_decrypt_invalid_token_returns_none(self):
        """Lines 42-44: InvalidToken → log warning, return None."""
        enc_mod = self._reload_with_key()
        # Garbage that fails Fernet decryption
        result = enc_mod.decrypt_field("gAAAAAnot-valid-fernet-token-at-all====")
        assert result is None

    def test_decrypt_none_returns_none(self):
        """Lines 36-37: None input → None output."""
        enc_mod = self._reload_with_key()
        assert enc_mod.decrypt_field(None) is None

    def test_encrypt_then_decrypt_roundtrip(self):
        """Full roundtrip via encrypt_field + decrypt_field."""
        enc_mod = self._reload_with_key()
        original = "hello world 123 ąęó"
        cipher = enc_mod.encrypt_field(original)
        assert cipher != original
        recovered = enc_mod.decrypt_field(cipher)
        assert recovered == original

    def test_decrypt_no_key_returns_value_unchanged(self):
        """Lines 38-39: when _fernet is None, value returned as-is."""
        with patch.dict(os.environ, {"FIELD_ENCRYPTION_KEY": ""}):
            import services.api.services.api.auth.encryption as enc_mod
            importlib.reload(enc_mod)
        result = enc_mod.decrypt_field("some-plain-value")
        assert result == "some-plain-value"

    def teardown_method(self, method):
        """Reset module to no-key state after each test."""
        with patch.dict(os.environ, {"FIELD_ENCRYPTION_KEY": ""}):
            import services.api.services.api.auth.encryption as enc_mod
            importlib.reload(enc_mod)


# ══════════════════════════════════════════════════════════════════════════════
# 3. middleware/csrf.py — line 60 (CSRF mismatch → 403)
# ══════════════════════════════════════════════════════════════════════════════

class TestCSRFMiddlewareMismatch:
    """Cover line 60: csrf_cookie present but header absent/mismatched → 403."""

    def _get_middleware(self):
        from services.api.services.api.middleware.csrf import CSRFMiddleware
        return CSRFMiddleware(app=MagicMock())

    def test_csrf_cookie_present_header_missing_returns_403(self):
        """Line 60: cookie set, X-CSRF-Token absent → CSRF_INVALID 403."""
        mw = self._get_middleware()
        request = _req(
            method="POST",
            path="/api/tenders",
            cookies={"csrf_token": "abc123"},
        )
        result = asyncio.run(mw.dispatch(request, _call_next_200))
        assert result.status_code == 403
        body = _body(result)
        assert body["error"]["code"] == "CSRF_INVALID"

    def test_csrf_cookie_present_header_mismatched_returns_403(self):
        """Line 60: cookie set, header has different value → CSRF_INVALID 403."""
        mw = self._get_middleware()
        request = _req(
            method="POST",
            path="/api/orders",
            headers={"X-CSRF-Token": "wrong-token"},
            cookies={"csrf_token": "correct-token"},
        )
        result = asyncio.run(mw.dispatch(request, _call_next_200))
        assert result.status_code == 403
        body = _body(result)
        assert "CSRF" in body["error"]["code"]

    def test_csrf_cookie_and_header_match_allowed(self):
        """Lines 49-51: matching tokens → request passes through."""
        mw = self._get_middleware()
        request = _req(
            method="POST",
            path="/api/tenders",
            headers={"X-CSRF-Token": "matching-token"},
            cookies={"csrf_token": "matching-token"},
        )
        result = asyncio.run(mw.dispatch(request, _call_next_200))
        assert result.status_code == 200

    def test_no_cookie_no_bearer_allowed(self):
        """Lines 56-58: no csrf_cookie at all → allowed."""
        mw = self._get_middleware()
        request = _req(method="POST", path="/api/tenders")
        result = asyncio.run(mw.dispatch(request, _call_next_200))
        assert result.status_code == 200

    def test_bearer_token_exempts_csrf(self):
        """Lines 42-43: Bearer auth → no CSRF check needed."""
        mw = self._get_middleware()
        request = _req(
            method="DELETE",
            path="/api/tenders/1",
            headers={"Authorization": "Bearer some.jwt.token"},
            cookies={"csrf_token": "abc"},
        )
        result = asyncio.run(mw.dispatch(request, _call_next_200))
        assert result.status_code == 200

    def test_csrf_message_in_403_body(self):
        """Verify the 403 body contains the expected CSRF mismatch message."""
        mw = self._get_middleware()
        request = _req(
            method="PUT",
            path="/api/data",
            cookies={"csrf_token": "token-a"},
            headers={"X-CSRF-Token": "token-b"},
        )
        result = asyncio.run(mw.dispatch(request, _call_next_200))
        assert result.status_code == 403
        body = _body(result)
        assert "mismatch" in body["error"]["message"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# 4. middleware/tenant.py — lines 67-71 (_on_checkout with active tenant_id)
# ══════════════════════════════════════════════════════════════════════════════

class TestTenantRLSCheckout:
    """Cover lines 67-71: checkout listener executes cursor when tenant is set."""

    def _capture_checkout_listener(self, install_fn):
        """
        Call install_fn with a mock engine and capture the registered
        checkout listener by intercepting event.listens_for.
        """
        captured = {}

        original_listens_for = __import__("sqlalchemy").event.listens_for

        def _fake_listens_for(target, event_name, **kw):
            def decorator(fn):
                captured[event_name] = fn
                # Also register on the real engine so other tests work
                return fn
            return decorator

        import sqlalchemy
        with patch.object(sqlalchemy.event, "listens_for", side_effect=_fake_listens_for):
            install_fn(MagicMock())

        return captured

    def test_checkout_listener_executes_when_tid_set(self):
        """Lines 67-71: cursor.execute called with tenant_id."""
        from services.api.services.api.middleware.tenant import (
            _install_rls_listener,
            _current_tenant_id,
        )

        captured = self._capture_checkout_listener(_install_rls_listener)
        assert "checkout" in captured, "checkout listener not registered"

        checkout_fn = captured["checkout"]

        mock_dbapi_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_dbapi_conn.cursor.return_value = mock_cursor

        token = _current_tenant_id.set("test-tenant-uuid-1234")
        try:
            checkout_fn(mock_dbapi_conn, MagicMock(), MagicMock())

            mock_dbapi_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once()
            # Verify set_config SQL and the tenant id appear in the call
            execute_args = mock_cursor.execute.call_args
            sql_str = execute_args[0][0]
            assert "set_config" in sql_str
            tid_arg = execute_args[0][1]
            assert "test-tenant-uuid-1234" in str(tid_arg)
            mock_cursor.close.assert_called_once()
        finally:
            _current_tenant_id.reset(token)

    def test_checkout_listener_skips_when_no_tenant(self):
        """Lines 65-66: when tid is None, cursor is never opened."""
        from services.api.services.api.middleware.tenant import (
            _install_rls_listener,
            _current_tenant_id,
        )

        captured = self._capture_checkout_listener(_install_rls_listener)
        checkout_fn = captured["checkout"]

        mock_dbapi_conn = MagicMock()

        token = _current_tenant_id.set(None)
        try:
            checkout_fn(mock_dbapi_conn, MagicMock(), MagicMock())
            mock_dbapi_conn.cursor.assert_not_called()
        finally:
            _current_tenant_id.reset(token)

    def test_tenant_middleware_dispatch_sets_contextvar(self):
        """TenantMiddleware.dispatch sets _current_tenant_id for the duration."""
        from services.api.services.api.middleware.tenant import (
            TenantMiddleware,
            _current_tenant_id,
        )

        mw = TenantMiddleware(app=MagicMock())
        captured_tid: list = []

        async def _capturing_call_next(request):
            captured_tid.append(_current_tenant_id.get())
            return JSONResponse({"ok": True})

        request = _req(method="GET", path="/api/test")
        request.state.tenant_id = "tenant-xyz-999"

        asyncio.run(mw.dispatch(request, _capturing_call_next))

        assert captured_tid == ["tenant-xyz-999"]
        # After request, ContextVar must be reset to None
        assert _current_tenant_id.get() is None

    def test_make_get_db_with_tenant_sets_sql(self):
        """make_get_db_with_tenant yields db and calls set_tenant_id when tid set."""
        from services.api.services.api.middleware.tenant import (
            make_get_db_with_tenant,
            _current_tenant_id,
        )

        mock_session = MagicMock()
        mock_session_local = MagicMock(return_value=mock_session)

        get_db = make_get_db_with_tenant(mock_session_local)

        token = _current_tenant_id.set("tenant-for-db")
        try:
            gen = get_db()
            db = next(gen)
            assert db is mock_session
            mock_session.execute.assert_called_once()
            try:
                next(gen)
            except StopIteration:
                pass
            mock_session.close.assert_called_once()
        finally:
            _current_tenant_id.reset(token)


# ══════════════════════════════════════════════════════════════════════════════
# 5. middleware/validation.py — lines 23-24 (ValueError on non-numeric content-length)
# ══════════════════════════════════════════════════════════════════════════════

class TestValidationMiddlewareValueError:
    """Cover lines 23-24: ValueError when content-length header is non-numeric."""

    def test_non_numeric_content_length_defaults_to_zero(self):
        """Lines 23-24: 'abc' content-length → ValueError → defaults 0 → passes."""
        from services.api.services.api.middleware.validation import validate_request

        request = _req(
            method="POST",
            path="/api/tenders",
            headers={"content-length": "not-a-number"},
        )
        result = asyncio.run(validate_request(request, _call_next_200))
        # Falls back to content_length=0 → no 413
        assert result.status_code == 200

    def test_non_numeric_content_length_on_put(self):
        """Lines 23-24: PUT with malformed content-length is allowed through."""
        from services.api.services.api.middleware.validation import validate_request

        request = _req(
            method="PUT",
            path="/api/offers/1",
            headers={"content-length": "xyz-garbage"},
        )
        result = asyncio.run(validate_request(request, _call_next_200))
        assert result.status_code == 200

    def test_non_numeric_content_length_on_patch(self):
        """Lines 23-24: PATCH with malformed content-length (empty string) → allowed."""
        from services.api.services.api.middleware.validation import validate_request

        request = _req(
            method="PATCH",
            path="/api/tenders/1",
            headers={"content-length": ""},
        )
        result = asyncio.run(validate_request(request, _call_next_200))
        assert result.status_code == 200

    def test_oversized_body_returns_413(self):
        """Confirm valid oversized content-length still returns 413."""
        from services.api.services.api.middleware.validation import validate_request

        request = _req(
            method="POST",
            path="/api/upload",
            headers={"content-length": str(20 * 1024 * 1024)},  # 20 MB
        )
        result = asyncio.run(validate_request(request, _call_next_200))
        assert result.status_code == 413

    def test_strip_html_helper(self):
        """Sanity-check strip_html utility."""
        from services.api.services.api.middleware.validation import strip_html

        assert strip_html("<b>hello</b>") == "hello"
        assert strip_html("no tags") == "no tags"
        assert strip_html("  <p>text</p>  ") == "text"


# ══════════════════════════════════════════════════════════════════════════════
# 6. middleware/error_boundary.py — ~1 stmt
# ══════════════════════════════════════════════════════════════════════════════

class TestErrorBoundaryHandler:
    """Cover remaining stmts in error_boundary.py."""

    def test_http_exception_returns_correct_status(self):
        """Lines 15-19: HTTPException → JSONResponse with exc.status_code."""
        from fastapi import HTTPException
        from services.api.services.api.middleware.error_boundary import error_boundary_handler

        exc = HTTPException(status_code=404, detail="Not found")
        request = _req(method="GET", path="/api/missing")

        result = asyncio.run(error_boundary_handler(request, exc))
        assert result.status_code == 404
        body = _body(result)
        assert body["detail"] == "Not found"

    def test_http_exception_401(self):
        """HTTPException 401 branch."""
        from fastapi import HTTPException
        from services.api.services.api.middleware.error_boundary import error_boundary_handler

        exc = HTTPException(status_code=401, detail="Unauthorized")
        request = _req(method="POST", path="/api/secret")

        result = asyncio.run(error_boundary_handler(request, exc))
        assert result.status_code == 401

    def test_generic_exception_returns_500(self):
        """Lines 21-36: unhandled Exception → 500 JSON."""
        from services.api.services.api.middleware.error_boundary import error_boundary_handler

        exc = RuntimeError("Something exploded")
        request = _req(method="POST", path="/api/tenders")

        result = asyncio.run(error_boundary_handler(request, exc))
        assert result.status_code == 500
        body = _body(result)
        assert body["detail"]  # non-empty error message

    def test_audit_service_import_success_path(self):
        """Cover line 30 (pass after successful audit_service import attempt).

        We patch the relative import so it succeeds, exercising the
        try-import-pass branch.
        """
        # Build a fake audit_service module
        fake_audit = types.ModuleType("fake_audit_service")
        setattr(fake_audit, "log_audit", MagicMock())

        # The error_boundary handler does:
        #   from ..services.audit_service import log_audit
        # which resolves to the key below in sys.modules
        module_key = "services.api.services.api.services.audit_service"

        with patch.dict(sys.modules, {module_key: fake_audit}):
            import services.api.services.api.middleware.error_boundary as eb_mod
            importlib.reload(eb_mod)

            exc = ValueError("trigger non-HTTP path")
            request = _req(method="GET", path="/api/test")

            result = asyncio.run(eb_mod.error_boundary_handler(request, exc))
            assert result.status_code == 500

        # Restore original module state
        importlib.reload(eb_mod)

    def test_audit_service_import_failure_graceful(self):
        """Lines 31-32: failed audit_service import is silently swallowed."""
        from services.api.services.api.middleware.error_boundary import error_boundary_handler

        exc = KeyError("missing key")
        request = _req(method="DELETE", path="/api/resource/1")

        result = asyncio.run(error_boundary_handler(request, exc))
        assert result.status_code == 500
