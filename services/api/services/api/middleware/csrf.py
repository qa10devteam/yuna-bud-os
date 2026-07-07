"""CSRF double-submit cookie protection middleware — Task 119.

Strategy:
  - Safe methods (GET, HEAD, OPTIONS) are always allowed.
  - Requests using Bearer token (Authorization: Bearer …) are exempted —
    they are not vulnerable to CSRF because browsers don't auto-attach
    Authorization headers.
  - Cookie-based sessions must send matching X-CSRF-Token header.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection."""

    SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})
    # Paths exempted from CSRF (e.g. machine-to-machine webhook receivers)
    EXEMPT_PATH_PREFIXES: tuple[str, ...] = ("/health",)

    async def dispatch(self, request: Request, call_next):
        # Safe HTTP methods → no check needed
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # Exempt specific prefixes
        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PATH_PREFIXES):
            return await call_next(request)

        # Bearer-token based requests are NOT susceptible to CSRF
        # (browser never auto-sends Authorization header)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Cookie-based auth: validate double-submit token
        csrf_cookie = request.cookies.get("csrf_token", "")
        csrf_header = request.headers.get("X-CSRF-Token", "")

        if csrf_cookie and csrf_cookie == csrf_header:
            # Tokens match → legitimate same-origin request
            return await call_next(request)

        # If there is no csrf_cookie at all it might be a pure API call
        # (no session cookie set).  Only block when cookie IS present but
        # header is missing / mismatched.
        if not csrf_cookie:
            # No session cookie — allow (Bearer-less API clients, curl, etc.)
            return await call_next(request)

        return JSONResponse(
            status_code=403,
            content={"error": {"code": "CSRF_INVALID", "message": "CSRF token mismatch"}},
        )
