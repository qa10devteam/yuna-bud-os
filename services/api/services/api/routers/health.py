"""Health check router — M0 acceptance gate + live/ready/detailed endpoints."""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter(tags=["health"])

# Track startup time for uptime calculation
_START_TIME: float = time.monotonic()

# Schemas

class HealthResponse(BaseModel):
    status: str
    db: str
    version: str = "0.1.0"


class LiveResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str
    db: str
    redis: str


class DetailedResponse(BaseModel):
    version: str
    uptime_s: float
    db_status: str
    db_tables_count: int
    redis_status: str
    env: str


class SystemHealthResponse(BaseModel):
    status: str
    uptime_s: float
    version: str
    subsystems: dict


# Helper: check Redis

def _check_redis() -> str:
    try:
        import redis as redis_lib
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        r = redis_lib.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


# Legacy endpoint (M0 acceptance)

@router.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """M0 acceptance: returns {status: ok, db: ok}."""
    db_status = "ok"
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
    )


@router.get("/api/v2/health", response_model=HealthResponse)
async def health_v2() -> dict:
    """V2 health check: returns {status: ok, version: 2.0, db: ok}."""
    db_status = "ok"
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "2.0",
        "db": db_status,
    }


# Liveness

@router.get("/health/live", response_model=LiveResponse)
async def health_live() -> LiveResponse:
    """Liveness probe — always 200 if the process is alive."""
    return LiveResponse(status="ok")


# Readiness

@router.get("/health/ready", response_model=ReadyResponse)
async def health_ready(response: Response) -> ReadyResponse:
    """Readiness probe — 200 if DB and Redis reachable, 503 otherwise."""
    db_status = "ok"
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"
    redis_status = _check_redis()
    if db_status != "ok" or redis_status != "ok":
        response.status_code = 503
    return ReadyResponse(
        status="ready" if (db_status == "ok" and redis_status == "ok") else "not_ready",
        db=db_status,
        redis=redis_status,
    )


# Detailed

@router.get("/health/detailed", response_model=DetailedResponse)
async def health_detailed() -> DetailedResponse:
    """Detailed health: version, uptime, DB tables count, Redis ping, env."""
    uptime_s = round(time.monotonic() - _START_TIME, 2)
    version = "0.1.0"
    env = os.getenv("ENVIRONMENT", "dev")
    db_status = "ok"
    db_tables_count = 0
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"))
            row = result.fetchone()
            db_tables_count = int(row[0]) if row else 0
    except Exception as exc:
        db_status = f"error: {exc}"
    redis_status = _check_redis()
    return DetailedResponse(
        version=version,
        uptime_s=uptime_s,
        db_status=db_status,
        db_tables_count=db_tables_count,
        redis_status=redis_status,
        env=env,
    )


# ─── BPMN Sprint 6 — System health ─────────────────────────────────────────

@router.get("/health/system", response_model=SystemHealthResponse)
async def health_system() -> dict:
    """BPMN Faza 1 Sprint 6 — Full system health: DB, cache, ingest, alerts.

    Returns per-subsystem status + recent ingest task stats.
    HTTP 200 = all OK | 206 = degraded | 503 = critical failure.
    """
    from fastapi import Response
    result: dict = {
        "status": "ok",
        "uptime_s": round(time.monotonic() - _START_TIME, 2),
        "version": "0.1.0",
        "subsystems": {},
    }

    # 1. DB
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )).fetchone()
            tables = int(row[0]) if row else 0
        result["subsystems"]["db"] = {"status": "ok", "tables": tables}
    except Exception as exc:
        result["subsystems"]["db"] = {"status": "error", "detail": str(exc)}
        result["status"] = "critical"

    # 2. Ingest tasks (last 10 min)
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'done')   AS done,
                    COUNT(*) FILTER (WHERE status = 'running') AS running,
                    COUNT(*) FILTER (WHERE status = 'failed')  AS failed,
                    MAX(finished_at) AS last_finished
                FROM ingest_task
                WHERE created_at > NOW() - INTERVAL '10 minutes'
            """)).fetchone()
        result["subsystems"]["ingest"] = {
            "status": "ok",
            "last_10min": {
                "done": int(row[0]) if row else 0,
                "running": int(row[1]) if row else 0,
                "failed": int(row[2]) if row else 0,
            },
            "last_finished": row[3].isoformat() if row and row[3] else None,
        }
        if row and row[2] > 0:
            result["subsystems"]["ingest"]["status"] = "degraded"
            if result["status"] == "ok":
                result["status"] = "degraded"
    except Exception as exc:
        result["subsystems"]["ingest"] = {"status": "unavailable", "detail": str(exc)}

    # 3. In-process cache
    try:
        from ..cache import _STORE, _LOCK
        with _LOCK:
            cache_size = len(_STORE)
        result["subsystems"]["cache"] = {"status": "ok", "entries": cache_size}
    except Exception:
        result["subsystems"]["cache"] = {"status": "ok", "entries": 0}

    # 4. Alert dispatcher (systemd)
    try:
        import subprocess
        proc = subprocess.run(
            ["systemctl", "is-active", "terra-alert-dispatcher"],
            capture_output=True, text=True, timeout=2,
        )
        svc_status = proc.stdout.strip()
        result["subsystems"]["alert_dispatcher"] = {
            "status": "ok" if svc_status == "active" else "degraded",
            "systemd_state": svc_status,
        }
        if svc_status != "active" and result["status"] == "ok":
            result["status"] = "degraded"
    except Exception as exc:
        result["subsystems"]["alert_dispatcher"] = {"status": "unknown", "detail": str(exc)}

    # 5. S127-S129 — ingest_lag check (>6h → notification)
    try:
        from terra_db.session import get_engine as _get_engine_lag
        from sqlalchemy import text as _text_lag
        _engine_lag = _get_engine_lag()
        with _engine_lag.connect() as _conn_lag:
            _last = _conn_lag.execute(
                _text_lag("SELECT max(updated_at) FROM ingest_task WHERE status='done'")
            ).scalar()
            if _last is None or (_last and (
                __import__('datetime').datetime.now(__import__('datetime').timezone.utc) - _last
            ).total_seconds() > 6 * 3600):
                try:
                    _conn_lag.execute(
                        _text_lag(
                            "INSERT INTO notifications(id, type, message, created_at) "
                            "VALUES(gen_random_uuid(), 'ingest_lag', 'No ingest done in 6h', now()) "
                            "ON CONFLICT DO NOTHING"
                        )
                    )
                    _conn_lag.commit()
                except Exception:
                    pass
            result["subsystems"]["ingest_lag"] = {
                "status": "ok" if _last else "warning",
                "last_done": _last.isoformat() if _last else None,
            }
    except Exception as _exc_lag:
        result["subsystems"]["ingest_lag"] = {"status": "unavailable", "detail": str(_exc_lag)}

    return result


# ─── F3: Production /health — DB + Redis + vLLM checks ──────────────────────

class ServicesHealth(BaseModel):
    db: bool
    redis: bool
    vllm: bool


class ProductionHealthResponse(BaseModel):
    status: str  # "ok" | "degraded" | "down"
    services: ServicesHealth


@router.get("/health", response_model=ProductionHealthResponse, include_in_schema=True)
async def health_production() -> ProductionHealthResponse:
    """Production health check: DB (SELECT 1), Redis (PING), vLLM (/health).

    Returns:
        status: "ok" — all services up
                "degraded" — some services down
                "down" — all services down
        services: per-service boolean
    """
    services: dict[str, bool] = {"db": False, "redis": False, "vllm": False}

    # 1. PostgreSQL — SELECT 1
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        _engine = get_engine()
        with _engine.connect() as _conn:
            _conn.execute(text("SELECT 1"))
        services["db"] = True
    except Exception:
        services["db"] = False

    # 2. Redis — PING on port 6379
    try:
        import socket as _socket
        _sock = _socket.create_connection(("127.0.0.1", 6379), timeout=1)
        _sock.sendall(b"PING\r\n")
        _resp = _sock.recv(16)
        _sock.close()
        services["redis"] = _resp.startswith(b"+PONG")
    except Exception:
        services["redis"] = False

    # 3. vLLM — GET http://localhost:8001/health
    try:
        import urllib.request as _urllib_req
        _req = _urllib_req.urlopen("http://localhost:8001/health", timeout=2)
        services["vllm"] = _req.status == 200
    except Exception:
        services["vllm"] = False

    up_count = sum(services.values())
    if up_count == 3:
        overall = "ok"
    elif up_count == 0:
        overall = "down"
    else:
        overall = "degraded"

    return ProductionHealthResponse(
        status=overall,
        services=ServicesHealth(**services),
    )
