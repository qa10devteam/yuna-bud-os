"""Rate limiting via slowapi with Redis backend.

Rules:
  - 60 req/min per IP  (general)
  - 5 req/min per IP   for /api/v2/auth/* (brute-force protection)
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

from slowapi import Limiter
from slowapi.util import get_remote_address

import os

# Global limiter instance — imported in main.py
# In TESTING mode: use in-memory storage with high limits so tests don't hit 429
_storage = "memory://" if os.environ.get("TESTING") == "1" else "redis://localhost:6379/1"
_default_limits = ["99999/minute"] if os.environ.get("TESTING") == "1" else ["60/minute"]

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=_default_limits,
    storage_uri=_storage,
)
