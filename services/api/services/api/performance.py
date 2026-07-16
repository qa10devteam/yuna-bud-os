"""Faza 86-90 — Performance utilities.

- Response time tracking middleware
- Cache helper (in-memory LRU for dev, Redis-compatible interface)
- DB query optimization helpers
"""
from __future__ import annotations

import sys
sys.path.insert(0, '/home/ubuntu/terra-os/packages/vendor')

import time
import threading
from collections import OrderedDict
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# ─── In-memory LRU Cache ──────────────────────────────────────────────────────

class LRUCache:
    """Simple in-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 256, ttl_seconds: float = 300.0):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            value, ts = self._cache[key]
            if time.time() - ts > self._ttl:
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)  # evict LRU

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# ─── Global cache instance ────────────────────────────────────────────────────

# Plans cache (rarely changes)
plans_cache = LRUCache(max_size=10, ttl_seconds=3600)

# Metrics cache (short-lived)
metrics_cache = LRUCache(max_size=50, ttl_seconds=30)

# Tender list cache per org
tender_cache = LRUCache(max_size=200, ttl_seconds=60)


# ─── DB Query Optimization Hints ──────────────────────────────────────────────

OPTIMIZED_QUERIES = {
    "tenders_by_org": """
        SELECT t.id, t.name, t.status, t.deadline, t.created_at
        FROM tenders t
        WHERE t.org_id = :org_id
          AND t.is_deleted = false
        ORDER BY t.created_at DESC
        LIMIT :limit OFFSET :offset
        -- INDEX: idx_tenders_org_id_created_at
    """,

    "decisions_by_tender": """
        SELECT d.id, d.decision, d.confidence, d.created_at
        FROM decisions d
        WHERE d.tender_id = :tender_id
        ORDER BY d.created_at DESC
        -- INDEX: idx_decisions_tender_id
    """,

    "audit_log_by_actor": """
        SELECT id, action, entity_type, entity_id, created_at
        FROM audit_log
        WHERE actor_id = :actor_id
        ORDER BY created_at DESC
        LIMIT :limit
        -- INDEX: idx_audit_log_actor_id_created_at
    """,
}

# Recommended DB indexes
RECOMMENDED_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tenders_org_id_created_at ON tenders(org_id, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status) WHERE is_deleted = false;",
    "CREATE INDEX IF NOT EXISTS idx_decisions_tender_id ON decisions(tender_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_actor_id ON audit_log(actor_id, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id) WHERE revoked = false;",
    "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);",
    # Perf audit additions — high seq_scan tables
    "CREATE INDEX IF NOT EXISTS idx_agent_run_tenant_started ON agent_run(tenant_id, started_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_agent_run_status ON agent_run(tenant_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_agent_run_input_tender_id ON agent_run((input->>'tender_id')) WHERE input->>'tender_id' IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_chat_session_tender_id ON chat_session(tender_id) WHERE tender_id IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_competency_tenant_id ON competency(tenant_id);",
    "CREATE INDEX IF NOT EXISTS idx_availability_tenant_id ON availability(tenant_id);",
    "CREATE INDEX IF NOT EXISTS idx_risk_run_tenant_id ON risk_run(tenant_id, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_contract_tenant_id ON contract(tenant_id, created_at DESC NULLS LAST);",
    "CREATE INDEX IF NOT EXISTS idx_rfq_tenant_id ON rfq(tenant_id, created_at DESC NULLS LAST);",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_action_created ON audit_log(tenant_id, action, created_at DESC) WHERE action IS NOT NULL;",
]


def apply_recommended_indexes() -> list[str]:
    """Apply recommended DB indexes. Returns list of applied indexes."""
    applied = []
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            for idx_sql in RECOMMENDED_INDEXES:
                try:
                    conn.execute(text(idx_sql))
                    conn.commit()
                    applied.append(idx_sql.split("INDEX IF NOT EXISTS ")[1].split(" ON")[0])
                except Exception:
                    pass
    except Exception:
        pass
    return applied
