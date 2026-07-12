"""Faza 70 — OWASP Top 10 security audit file.

This file serves two purposes:
1. Documents the security posture of YU-NA against OWASP Top 10 2021
2. Provides runtime validators for string inputs

See also: security.py for RLS helpers and sanitization utilities.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# OWASP TOP 10 — 2021 SECURITY AUDIT CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
#
# A01:2021 – Broken Access Control                                    STATUS: ✓
#   ✓ require_org_access() in security.py enforced per-resource
#   ✓ require_user_access() for user-owned resources
#   ✓ All DB queries filtered by org_id or user_id (parameterized)
#   ✓ Admin-only endpoints check role (require_admin)
#   ✗ TODO: unit tests covering 403 on cross-org access
#
# A02:2021 – Cryptographic Failures                                   STATUS: ✓
#   ✓ Passwords hashed with bcrypt (work factor ≥ 12) in auth/utils.py
#   ✓ JWTs signed HS256 with SECRET_KEY from env (not hardcoded)
#   ✓ HTTPS enforced by Caddy (HSTS header added by SecurityHeadersMiddleware)
#   ✓ No sensitive data in logs or URLs
#   ✗ TODO: rotate JWT secret periodically
#
# A03:2021 – Injection (SQLi / command injection)                     STATUS: ✓
#   ✓ All DB queries: SQLAlchemy text() with :named_params — never f-strings
#   ✓ Input validated via Pydantic models before reaching DB layer
#   ✓ No dynamic SQL construction from user inputs
#   ✓ No shell commands executed with user-supplied data (subprocess uses lists)
#
# A04:2021 – Insecure Design                                          STATUS: ✓
#   ✓ Rate limiting on auth endpoints (10 req/min) via slowapi
#   ✓ Refresh token rotation (old token revoked on refresh)
#   ✓ GDPR account deletion available (Faza 69)
#   ✗ TODO: password reset flow with expiring tokens
#
# A05:2021 – Security Misconfiguration                                STATUS: ✓
#   ✓ Security headers middleware: X-Frame-Options DENY, nosniff, HSTS, etc.
#   ✓ /docs endpoint disabled in production (ENVIRONMENT=prod)
#   ✓ CORS: allow_origins=['*'] acceptable for internal API; restrict in prod
#   ✓ No debug mode in production
#   ✗ TODO: restrict CORS origins to known frontend domains
#
# A06:2021 – Vulnerable and Outdated Components                       STATUS: ⚠
#   ✓ Dependencies pinned in pyproject.toml
#   ✗ TODO: add pip-audit / safety to CI pipeline
#   ✗ TODO: Dependabot / Renovate for automated dependency updates
#
# A07:2021 – Identification and Authentication Failures               STATUS: ✓
#   ✓ JWT in Authorization: Bearer header (never in URL query params)
#   ✓ Token expiry enforced server-side
#   ✓ Brute-force protection: 10 req/min on /auth/* endpoints
#   ✓ is_active check on every login
#   ✗ TODO: MFA support
#
# A08:2021 – Software and Data Integrity Failures                     STATUS: ✓
#   ✓ All input deserialized through Pydantic schemas (no pickle/eval)
#   ✓ API accepts only JSON body (Content-Type validated by validation middleware)
#
# A09:2021 – Security Logging and Monitoring Failures                 STATUS: ⚠
#   ✓ Audit log table (audit_log) with actor, action, entity tracking
#   ✓ Request counter in monitoring middleware
#   ✗ TODO: structured JSON logs to file / syslog
#   ✗ TODO: alerting on repeated 401/403 errors
#
# A10:2021 – Server-Side Request Forgery (SSRF)                       STATUS: ✓
#   ✓ No user-controlled URLs used in server-side HTTP calls currently
#   ✓ External HTTP calls (BZP scraper) use hardcoded base URLs
#   ✗ TODO: URL allowlist when adding webhook / integration features
#
# ═══════════════════════════════════════════════════════════════════════════════
# STRING INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

import re

_MAX_STRING_LENGTH = 10_000
_HTML_RE = re.compile(r"<[^>]+>")
_JS_PROTO_RE = re.compile(r"javascript:", re.IGNORECASE)
_NULL_BYTE_RE = re.compile(r"\x00")
_PATH_TRAVERSAL_RE = re.compile(r"\.\./|\.\.\\")


def validate_string_input(value: str, field_name: str = "field", max_length: int = _MAX_STRING_LENGTH) -> str:
    """Validate and sanitize a user-supplied string.

    Raises ValueError if input is invalid.
    Returns sanitized string.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name}: expected string")

    if len(value) > max_length:
        raise ValueError(f"{field_name}: przekracza maksymalną długość {max_length} znaków")

    # Remove null bytes (can bypass filters)
    value = _NULL_BYTE_RE.sub("", value)

    # Block path traversal
    if _PATH_TRAVERSAL_RE.search(value):
        raise ValueError(f"{field_name}: niedozwolone sekwencje ścieżki")

    # Strip HTML tags and JS protocol
    value = _HTML_RE.sub("", value)
    value = _JS_PROTO_RE.sub("", value)

    return value.strip()


SECURITY_AUDIT_VERSION = "1.0"
LAST_REVIEWED = "2026-06-30"
