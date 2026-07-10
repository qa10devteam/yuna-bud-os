"""S34 — In-memory per-user/IP rate limiter middleware (100 req/min).

Complements the global slowapi limiter with a per-org_id sliding window.
Falls back to client IP when no authenticated user is present.
"""
from __future__ import annotations

from collections import defaultdict, deque

import time

from fastapi import Request
from fastapi.responses import JSONResponse

_buckets: dict = defaultdict(lambda: deque(maxlen=120))


async def rate_limit_middleware(request: Request, call_next):
    """Sliding-window 100 req/min per org_id (or IP for anonymous)."""
    uid = (
        getattr(getattr(request.state, "user", None), "org_id", None)
        or (request.client.host if request.client else None)
        or "anon"
    )
    now = time.time()
    bucket = _buckets[str(uid)]
    bucket.append(now)
    window_count = sum(1 for t in bucket if now - t < 60)
    if window_count > 100:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit 100 req/min exceeded"},
        )
    return await call_next(request)
