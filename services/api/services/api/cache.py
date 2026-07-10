"""Shared in-process TTL cache for API layer.

Thread-safe, no external deps. Used by analytics, stats, dashboard endpoints
to avoid repeated heavy SQL queries.

Usage:
    from services.api.cache import api_cache

    @api_cache(ttl=60, key_fn=lambda user, **_: f"dashboard:{user.org_id}")
    def my_handler(user: AuthUser) -> dict:
        ...  # only runs on cache miss
"""
from __future__ import annotations

import functools
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STORE: dict[str, tuple[float, Any]] = {}  # key → (expires_at, value)


def get(key: str) -> Any:
    """Return cached value or None if missing/expired."""
    with _LOCK:
        entry = _STORE.get(key)
        if entry and time.monotonic() < entry[0]:
            return entry[1]
    return None


def set(key: str, value: Any, ttl: int = 60) -> None:
    """Store value with TTL seconds."""
    with _LOCK:
        _STORE[key] = (time.monotonic() + ttl, value)


def invalidate(prefix: str | None = None) -> int:
    """Invalidate all keys (or keys starting with prefix). Returns count removed."""
    with _LOCK:
        if prefix:
            keys = [k for k in _STORE if k.startswith(prefix)]
        else:
            keys = list(_STORE.keys())
        for k in keys:
            del _STORE[k]
    logger.debug("API cache invalidated: %d entries (prefix=%s)", len(keys), prefix)
    return len(keys)


def api_cache(ttl: int = 60, key_fn: Callable[..., str] | None = None):
    """Decorator: cache function result by key derived from args.

    Args:
        ttl:    Cache TTL in seconds (default 60).
        key_fn: Callable(*args, **kwargs) → str. Default: f"{func.__name__}:{str(args)}"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cached = get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s", cache_key)
                return cached
            result = func(*args, **kwargs)
            set(cache_key, result, ttl=ttl)
            logger.debug("Cache SET: %s (ttl=%ds)", cache_key, ttl)
            return result
        return wrapper
    return decorator
