"""Prometheus custom metrics for YU-NA API (Tasks 112-115)."""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

ENGINE_RUNS = Counter(
    'terra_engine_runs_total',
    'Engine L2 Monte Carlo runs',
    ['tenant_id', 'status']
)
ENGINE_LATENCY = Histogram(
    'terra_engine_latency_seconds',
    'Engine run latency in seconds',
    ['tenant_id']
)
ACTIVE_TENANTS = Gauge(
    'terra_active_tenants',
    'Number of active tenants'
)
RFQ_SENT = Counter(
    'terra_rfq_sent_total',
    'Total RFQs sent',
    ['tenant_id']
)
DB_POOL_SIZE = Gauge(
    'terra_db_pool_size',
    'DB connection pool size'
)
