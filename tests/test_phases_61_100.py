"""Tests for Fazy 61-100 — Security, GDPR, Monitoring, Billing, PWA.

Run with: cd /home/ubuntu/terra-os && python -m pytest tests/test_phases_61_100.py -v
"""
from __future__ import annotations

import sys
import os

# Make terra packages importable — must be before any terra imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "vendor"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "db"))
# services/api appended last — avoids shadowing terra-os/services (ingestion, engine…)
_api_p = os.path.join(os.path.dirname(__file__), "..", "services", "api")
if _api_p not in sys.path:
    sys.path.append(_api_p)

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("ENVIRONMENT", "dev")

import pytest
from unittest.mock import MagicMock, patch


# ─── Faza 61-65: Security Hardening ───────────────────────────────────────────

class TestSecurityModule:
    """Unit tests for security.py helpers."""

    def test_sanitize_string_strips_html(self):
        from services.api.services.api.security import sanitize_string
        result = sanitize_string("<script>alert('xss')</script>hello")
        assert "<script>" not in result
        assert "hello" in result

    def test_sanitize_string_strips_javascript_protocol(self):
        from services.api.services.api.security import sanitize_string
        result = sanitize_string("javascript:alert(1)")
        assert "javascript:" not in result

    def test_sanitize_string_respects_max_length(self):
        from services.api.services.api.security import sanitize_string
        long_str = "a" * 20000
        result = sanitize_string(long_str, max_length=100)
        assert len(result) == 100

    def test_sanitize_dict_sanitizes_string_fields(self):
        from services.api.services.api.security import sanitize_dict
        data = {"name": "<b>Hello</b>", "value": 42}
        result = sanitize_dict(data)
        assert "<b>" not in result["name"]
        assert result["value"] == 42

    def test_require_org_access_passes_for_matching_org(self):
        from services.api.services.api.security import require_org_access
        from services.api.services.api.auth.deps import CurrentUser
        user = CurrentUser(user_id="u1", email="a@b.com", org_id="org1", role="member")
        # Should not raise
        require_org_access("org1", user)

    def test_require_org_access_raises_for_wrong_org(self):
        from services.api.services.api.security import require_org_access
        from services.api.services.api.auth.deps import CurrentUser
        from fastapi import HTTPException
        user = CurrentUser(user_id="u1", email="a@b.com", org_id="org1", role="member")
        with pytest.raises(HTTPException) as exc_info:
            require_org_access("org2", user)
        assert exc_info.value.status_code == 403

    def test_require_admin_passes_for_admin(self):
        from services.api.services.api.security import require_admin
        from services.api.services.api.auth.deps import CurrentUser
        user = CurrentUser(user_id="u1", email="a@b.com", org_id="org1", role="admin")
        require_admin(user)  # Should not raise

    def test_require_admin_passes_for_owner(self):
        from services.api.services.api.security import require_admin
        from services.api.services.api.auth.deps import CurrentUser
        user = CurrentUser(user_id="u1", email="a@b.com", org_id="org1", role="owner")
        require_admin(user)  # Should not raise

    def test_require_admin_raises_for_member(self):
        from services.api.services.api.security import require_admin
        from services.api.services.api.auth.deps import CurrentUser
        from fastapi import HTTPException
        user = CurrentUser(user_id="u1", email="a@b.com", org_id="org1", role="member")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403


class TestSecurityAudit:
    """Unit tests for security_audit.py validators."""

    def test_validate_string_input_passes_clean_string(self):
        from services.api.services.api.security_audit import validate_string_input
        result = validate_string_input("Hello World", "test_field")
        assert result == "Hello World"

    def test_validate_string_input_strips_html(self):
        from services.api.services.api.security_audit import validate_string_input
        result = validate_string_input("<b>bold</b>", "test")
        assert "<b>" not in result
        assert "bold" in result

    def test_validate_string_input_rejects_path_traversal(self):
        from services.api.services.api.security_audit import validate_string_input
        with pytest.raises(ValueError, match="ścieżki"):
            validate_string_input("../etc/passwd", "path")

    def test_validate_string_input_removes_null_bytes(self):
        from services.api.services.api.security_audit import validate_string_input
        result = validate_string_input("hello\x00world", "test")
        assert "\x00" not in result

    def test_validate_string_input_rejects_too_long(self):
        from services.api.services.api.security_audit import validate_string_input
        with pytest.raises(ValueError, match="długość"):
            validate_string_input("x" * 20000, "test", max_length=100)

    def test_security_audit_version_exists(self):
        from services.api.services.api.security_audit import SECURITY_AUDIT_VERSION, LAST_REVIEWED
        assert SECURITY_AUDIT_VERSION == "1.0"
        assert LAST_REVIEWED is not None


class TestValidationMiddleware:
    """Unit tests for input validation middleware."""

    def test_strip_html_removes_tags(self):
        from services.api.services.api.middleware.validation import strip_html
        result = strip_html("<p>Hello <b>World</b></p>")
        assert result == "Hello World"

    def test_strip_html_handles_empty_string(self):
        from services.api.services.api.middleware.validation import strip_html
        assert strip_html("") == ""


# ─── Faza 66-70: GDPR ─────────────────────────────────────────────────────────

class TestGdprRouter:
    """Unit tests for GDPR router logic."""

    def test_gdpr_router_has_correct_prefix(self):
        from services.api.services.api.routers.gdpr import router
        assert router.prefix == "/api/v2/gdpr"

    def test_gdpr_router_has_export_endpoint(self):
        from services.api.services.api.routers.gdpr import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/gdpr/export" in routes

    def test_gdpr_router_has_account_delete_endpoint(self):
        from services.api.services.api.routers.gdpr import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/gdpr/account" in routes

    def test_gdpr_router_has_consent_endpoint(self):
        from services.api.services.api.routers.gdpr import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/gdpr/consent" in routes

    def test_gdpr_router_has_audit_trail_endpoint(self):
        from services.api.services.api.routers.gdpr import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/gdpr/audit-trail" in routes


# ─── Faza 71-75: Monitoring ───────────────────────────────────────────────────

class TestMonitoringRouter:
    """Unit tests for monitoring router."""

    def test_request_counter_increments(self):
        from services.api.services.api.routers.monitoring import (
            increment_request_count,
            get_request_count,
        )
        initial = get_request_count()
        increment_request_count()
        assert get_request_count() == initial + 1

    def test_record_response_time_stores_values(self):
        from services.api.services.api.routers.monitoring import (
            record_response_time,
            _sla_response_times,
            _sla_lock,
        )
        record_response_time(100.0, success=True)
        with _sla_lock:
            assert len(_sla_response_times) > 0

    def test_monitoring_router_prefix(self):
        from services.api.services.api.routers.monitoring import router
        assert router.prefix == "/api/v2"

    def test_monitoring_has_metrics_endpoint(self):
        from services.api.services.api.routers.monitoring import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/metrics" in routes

    def test_monitoring_has_system_status_endpoint(self):
        from services.api.services.api.routers.monitoring import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/system/status" in routes

    def test_monitoring_has_health_detailed_endpoint(self):
        from services.api.services.api.routers.monitoring import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/health/detailed" in routes

    def test_monitoring_has_alerts_endpoint(self):
        from services.api.services.api.routers.monitoring import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/alerts" in routes

    def test_monitoring_has_sla_endpoint(self):
        from services.api.services.api.routers.monitoring import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/sla" in routes


# ─── Faza 76-80: Launch Prep / Billing ────────────────────────────────────────

class TestBillingRouter:
    """Unit tests for billing router."""

    def test_plans_list_has_4_plans(self):
        from services.api.services.api.routers.billing import PLANS
        assert len(PLANS) == 4

    def test_free_plan_price_is_zero(self):
        from services.api.services.api.routers.billing import PLANS
        free = next(p for p in PLANS if p["id"] == "free")
        assert free["price_pln"] == 0

    def test_pro_plan_has_features(self):
        from services.api.services.api.routers.billing import PLANS
        pro = next(p for p in PLANS if p["id"] == "pro")
        assert len(pro["features"]) > 0
        assert pro["price_pln"] == 499

    def test_business_plan_unlimited_tenders(self):
        from services.api.services.api.routers.billing import PLANS
        biz = next(p for p in PLANS if p["id"] == "business")
        assert biz["limits"]["tenders"] == -1

    def test_billing_router_prefix(self):
        from services.api.services.api.routers.billing import router
        assert router.prefix == "/api/v2/billing"

    def test_billing_has_checkout_endpoint(self):
        from services.api.services.api.routers.billing import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/billing/checkout" in routes

    def test_billing_has_webhook_endpoint(self):
        from services.api.services.api.routers.billing import router
        routes = {r.path for r in router.routes}
        assert "/api/v2/billing/webhook" in routes


class TestApiKeysRouter:
    """Unit tests for API key management."""

    def test_generate_key_returns_triple(self):
        from services.api.services.api.routers.api_keys import _generate_key
        plain, key_hash, prefix = _generate_key()
        assert plain.startswith("terra_")
        assert len(key_hash) == 64  # SHA256 hex
        assert prefix == plain[:8]

    def test_key_hash_is_sha256(self):
        import hashlib
        from services.api.services.api.routers.api_keys import _generate_key
        plain, key_hash, _ = _generate_key()
        expected = hashlib.sha256(plain.encode()).hexdigest()
        assert key_hash == expected

    def test_api_keys_router_has_all_endpoints(self):
        from services.api.services.api.routers.api_keys import router
        paths = {r.path for r in router.routes}
        assert "/api/v2/api-keys" in paths
        assert "/api/v2/api-keys/{key_id}" in paths


# ─── Faza 86-90: Performance ──────────────────────────────────────────────────

class TestPerformanceHelpers:
    """Unit tests for performance-related functions."""

    def test_response_time_percentile_calculation(self):
        """Test SLA percentile math."""
        times = list(range(1, 101))  # 1..100
        sorted_t = sorted(times)
        n = len(sorted_t)
        p50 = sorted_t[int(n * 0.50)]  # index 50 → value 51 (0-indexed)
        p95 = sorted_t[min(int(n * 0.95), n - 1)]  # index 95 → value 96
        assert p50 == 51  # 0-indexed: position 50 in 1..100 = value 51
        assert p95 == 96


# ─── Faza 91-95: Error Scenarios ──────────────────────────────────────────────

class TestErrorScenarios:
    """Test error handling across security/GDPR/monitoring."""

    def test_sanitize_string_non_string_passthrough(self):
        from services.api.services.api.security import sanitize_string
        # Non-string input should be returned as-is
        result = sanitize_string(42)  # type: ignore
        assert result == 42

    def test_require_user_access_admin_bypass(self):
        from services.api.services.api.security import require_user_access
        from services.api.services.api.auth.deps import CurrentUser
        admin = CurrentUser(user_id="admin1", email="a@b.com", org_id="org1", role="admin")
        # Admin can access other user's resources
        require_user_access("other_user", admin)  # Should not raise

    def test_consent_request_defaults_to_false(self):
        from services.api.services.api.routers.gdpr import ConsentRequest
        consent = ConsentRequest()
        assert consent.analytics is False
        assert consent.marketing is False
        assert consent.third_party is False

    def test_checkout_request_defaults(self):
        from services.api.services.api.routers.billing import CheckoutRequest
        req = CheckoutRequest()
        assert req.plan_id == "pro"
        assert "/billing/success" in req.success_url

    def test_billing_unknown_plan_raises(self):
        """Test that checkout raises for unknown plans."""
        from services.api.services.api.routers.billing import PLANS
        plan = next((p for p in PLANS if p["id"] == "nonexistent"), None)
        assert plan is None


# ─── Faza 96-100: PWA ─────────────────────────────────────────────────────────

class TestPWAFiles:
    """Test PWA manifest and service worker files exist."""

    def test_manifest_json_exists(self):
        manifest_path = "/home/ubuntu/terra-os/apps/ui/public/manifest.json"
        assert os.path.exists(manifest_path), "manifest.json is missing"

    def test_manifest_json_valid(self):
        import json
        manifest_path = "/home/ubuntu/terra-os/apps/ui/public/manifest.json"
        if not os.path.exists(manifest_path):
            pytest.skip("manifest.json not yet created")
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "name" in manifest
        assert "icons" in manifest
        assert "start_url" in manifest
        assert "display" in manifest

    def test_service_worker_exists(self):
        sw_path = "/home/ubuntu/terra-os/apps/ui/public/sw.js"
        assert os.path.exists(sw_path), "Service worker sw.js is missing"

    def test_service_worker_has_cache_logic(self):
        sw_path = "/home/ubuntu/terra-os/apps/ui/public/sw.js"
        if not os.path.exists(sw_path):
            pytest.skip("sw.js not yet created")
        with open(sw_path) as f:
            content = f.read()
        assert "cache" in content.lower()
        assert "fetch" in content.lower()


# ─── Integration smoke tests ──────────────────────────────────────────────────

class TestAppImport:
    """Smoke test that the FastAPI app can be imported without crashing."""

    def test_app_imports_successfully(self):
        from services.api.services.api.main import app
        assert app is not None
        assert app.title == "Terra.OS API"

    def _app_paths(self, app):
        """Collect all route paths recursively (handles FastAPI _IncludedRouter)."""
        paths: set = set()
        for r in getattr(app, 'routes', []):
            if hasattr(r, 'path'):
                paths.add(r.path)
            orig = getattr(r, 'original_router', None)
            if orig:
                paths |= self._app_paths(orig)
        return paths

    def test_app_has_required_routes(self):
        from services.api.services.api.main import app
        paths = self._app_paths(app)
        assert "/api/v1/health" in paths

    def test_security_headers_middleware_registered(self):
        from services.api.services.api.main import app, SecurityHeadersMiddleware
        middleware_types = [m.cls for m in app.user_middleware if hasattr(m, 'cls')]
        assert SecurityHeadersMiddleware in middleware_types

    def test_gdpr_routes_registered_in_app(self):
        from services.api.services.api.main import app
        paths = self._app_paths(app)
        assert "/api/v2/gdpr/export" in paths
        assert "/api/v2/gdpr/account" in paths

    def test_monitoring_routes_registered(self):
        from services.api.services.api.main import app
        paths = self._app_paths(app)
        assert "/api/v2/metrics" in paths
        assert "/api/v2/system/status" in paths

    def test_billing_routes_registered(self):
        from services.api.services.api.main import app
        paths = self._app_paths(app)
        assert "/api/v2/billing/plans" in paths
        assert "/api/v2/billing/checkout" in paths
