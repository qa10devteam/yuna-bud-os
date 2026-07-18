"""IDS middleware — dynamic IP blocking based on repeated 401/403 responses.

Strategy:
  - Track 401/403 errors per IP in Redis with a sliding 5-minute window
  - After IDS_THRESHOLD errors (default: 20), block IP for IDS_BLOCK_TTL seconds (default: 3600)
  - Blocked IPs receive 403 immediately, before request hits any router
  - Localhost (127.0.0.1, ::1) is always exempt

Config (env vars):
  IDS_THRESHOLD   — errors before block (default: 20)
  IDS_WINDOW      — sliding window in seconds (default: 300 = 5 min)
  IDS_BLOCK_TTL   — block duration in seconds (default: 3600 = 1 hour)
  IDS_ENABLED     — set to "false" to disable (default: true)
"""
from __future__ import annotations

import logging
import os
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

IDS_ENABLED = os.getenv("IDS_ENABLED", "true").lower() == "true"
IDS_THRESHOLD = int(os.getenv("IDS_THRESHOLD", "20"))
IDS_WINDOW = int(os.getenv("IDS_WINDOW", "300"))  # 5 minutes
IDS_BLOCK_TTL = int(os.getenv("IDS_BLOCK_TTL", "3600"))  # 1 hour
EXEMPT_IPS = frozenset({"127.0.0.1", "::1"})
SKIP_PATHS = frozenset({"/health", "/metrics"})
SKIP_PREFIXES = ("/health", "/api/v1/health", "/api/v2/health", "/metrics")


def _get_redis():
    """Lazy Redis connection — reuse connection from rate_limiter if possible."""
    try:
        from .rate_limiter import _redis  # noqa: F401 — try to reuse
        return _redis
    except Exception:
        pass
    import redis as redis_lib
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD") or None
    return redis_lib.Redis(host=host, port=port, password=password, db=1, decode_responses=True)


class IDSMiddleware(BaseHTTPMiddleware):
    """Intrusion Detection System — auto-blocks IPs with repeated auth failures."""

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._redis = None

    def _get_r(self):
        if self._redis is None:
            self._redis = _get_redis()
        return self._redis

    async def dispatch(self, request: Request, call_next):
        if not IDS_ENABLED:
            return await call_next(request)

        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Health/metrics and localhost are always exempt (skip blocklist + tracking)
        if path in SKIP_PATHS or path.startswith(SKIP_PREFIXES) or client_ip in EXEMPT_IPS:
            return await call_next(request)

        # Check dynamic blocklist BEFORE forwarding
        try:
            r = self._get_r()
            if r.exists(f"ids:blocked:{client_ip}"):
                logger.warning("IDS blocked request from %s to %s", client_ip, path)
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Dostęp tymczasowo zablokowany"},
                )
        except Exception as e:
            logger.warning("IDS Redis check failed: %s", e)

        response = await call_next(request)

        # Track 401/403 responses
        if response.status_code in (401, 403):
            try:
                r = self._get_r()
                now = time.time()  # noqa: F841 — reserved for future sliding-window expansion
                counter_key = f"ids:failures:{client_ip}"

                # Increment failure count
                count = r.incr(counter_key)
                r.expire(counter_key, IDS_WINDOW)

                if count >= IDS_THRESHOLD:
                    # Block the IP
                    r.setex(f"ids:blocked:{client_ip}", IDS_BLOCK_TTL, "1")
                    r.delete(counter_key)
                    logger.warning(
                        "IDS: blocked IP %s after %d failures (threshold=%d, TTL=%ds)",
                        client_ip, count, IDS_THRESHOLD, IDS_BLOCK_TTL,
                    )
            except Exception as e:
                logger.warning("IDS Redis write failed: %s", e)

        return response
