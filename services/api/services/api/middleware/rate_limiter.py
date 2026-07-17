"""Redis-based per-IP rate limiter middleware (100 req/min general, 5 req/min auth).

Uses Redis sliding window counters. No localhost whitelist (reverse proxy scenario).
Adds X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers.
"""
from __future__ import annotations

import os
import time

from fastapi import Request
from fastapi.responses import JSONResponse

import redis

_redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    db=1,
    decode_responses=True,
)

# Limits
_AUTH_LIMIT = 5
_GENERAL_LIMIT = 100
_WINDOW = 60  # seconds


def _is_auth_endpoint(path: str) -> bool:
    """Check if the path is an auth endpoint that needs stricter limiting."""
    return path.startswith("/api/v2/auth/login") or path.startswith("/api/v2/auth/register")


async def rate_limit_middleware(request: Request, call_next):
    """Redis sliding-window rate limiter. No whitelist."""
    if os.environ.get("TESTING") == "1":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    is_auth = _is_auth_endpoint(path)
    limit = _AUTH_LIMIT if is_auth else _GENERAL_LIMIT

    # Redis key with endpoint category
    category = "auth" if is_auth else "general"
    key = f"rate:{client_ip}:{category}"

    now = time.time()
    window_start = now - _WINDOW

    pipe = _redis.pipeline()
    # Remove old entries outside window
    pipe.zremrangebyscore(key, 0, window_start)
    # Count current entries
    pipe.zcard(key)
    # Add current request
    pipe.zadd(key, {f"{now}:{id(request)}": now})
    # Set TTL
    pipe.expire(key, _WINDOW + 1)
    results = pipe.execute()

    current_count = results[1]
    remaining = max(0, limit - current_count - 1)
    reset_at = int(now) + _WINDOW

    if current_count >= limit:
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit exceeded: {limit} req/min"},
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
                "Retry-After": str(_WINDOW),
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_at)
    return response
