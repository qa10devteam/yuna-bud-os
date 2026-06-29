"""M9 — Observability: agent_run tracking + /agents endpoints.

Endpoints:
  GET  /agents/{run_id}                    → AgentRun status + cost + tokens + error
  POST /agents/{run_id}/pause              → marks paused
  POST /agents/{run_id}/resume             → marks running
  POST /agents/{run_id}/cancel             → marks cancelled

Also: POST /api/v1/pipeline/run            → trigger full pipeline (queued)
      POST /api/v1/contracts/{id}/close    → learning loop close (actual_cost_pln)
      GET  /api/v1/system/backup/status    → backup status
      POST /api/v1/system/backup/run       → trigger pg_dump
      GET  /api/v1/audit                   → paginated audit_log
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v1", tags=["observability", "system"])


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class AgentRunResponse(BaseModel):
    id: str
    agent: str
    status: str
    tokens_in: int
    tokens_out: int
    cost_pln: float
    error: str | None


class ContractCloseRequest(BaseModel):
    actual_cost_pln: float


class BackupStatusResponse(BaseModel):
    last_backup_at: str | None
    last_backup_path: str | None
    status: str


class AuditEntry(BaseModel):
    id: int
    at: str
    actor: str
    action: str
    entity: str | None
    entity_id: str | None
    detail: dict | None


# ──────────────────────────────────────────────────────────────────────────────
# Agent run tracking
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/agents/{run_id}", response_model=AgentRunResponse)
def get_agent_run(run_id: str) -> AgentRunResponse:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id, agent, status, tokens_in, tokens_out, cost_pln, error "
            "FROM agent_run WHERE id=:id"
        ), {"id": run_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    return AgentRunResponse(
        id=str(row[0]), agent=row[1], status=row[2],
        tokens_in=row[3] or 0, tokens_out=row[4] or 0,
        cost_pln=float(row[5] or 0),
        error=row[6],
    )


def _transition_agent(run_id: str, new_status: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id, status FROM agent_run WHERE id=:id"
        ), {"id": run_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    with engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE agent_run SET status=:s WHERE id=:id"
        ), {"s": new_status, "id": run_id})
    return {"ok": True, "status": new_status}


@router.post("/agents/{run_id}/pause")
def pause_agent(run_id: str) -> dict:
    return _transition_agent(run_id, "paused")


@router.post("/agents/{run_id}/resume")
def resume_agent(run_id: str) -> dict:
    return _transition_agent(run_id, "running")


@router.post("/agents/{run_id}/cancel")
def cancel_agent(run_id: str) -> dict:
    return _transition_agent(run_id, "cancelled")


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline trigger
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/pipeline/run", status_code=202)
def trigger_pipeline() -> dict:
    """Enqueue a full pipeline run. Returns agent_run_id to poll."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tenant LIMIT 1")).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="No tenant")
    tenant_id = str(row[0])

    run_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO agent_run (id, tenant_id, agent, status, started_at) "
            "VALUES (:id, :tid, 'pipeline_supervisor', 'queued', now())"
        ), {"id": run_id, "tid": tenant_id})

    # Run synchronously (offline test mode)
    _run_pipeline_sync(run_id, tenant_id)

    return {"agent_run_id": run_id}


def _run_pipeline_sync(run_id: str, tenant_id: str) -> None:
    """Execute pipeline in-process (test/offline). Updates agent_run on finish."""
    from services.agents.pipeline import run_pipeline, PipelineState
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(
                "UPDATE agent_run SET status='running' WHERE id=:id"
            ), {"id": run_id})
        result = run_pipeline(PipelineState(steps=[]))
        final_status = "failed" if result.get("error") else "succeeded"
        with engine.begin() as conn:
            conn.execute(sa.text(
                "UPDATE agent_run SET status=:s, output=cast(:out as jsonb), finished_at=now() WHERE id=:id"
            ), {
                "s": final_status, "id": run_id,
                "out": json.dumps({k: v for k, v in result.items() if k != "error"}),
            })
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(sa.text(
                "UPDATE agent_run SET status='failed', error=:e, finished_at=now() WHERE id=:id"
            ), {"e": str(exc), "id": run_id})


# ──────────────────────────────────────────────────────────────────────────────
# Learning loop — contract close
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/contracts/{contract_id}/close")
def close_contract_endpoint(contract_id: str, body: ContractCloseRequest) -> dict:
    """Close contract + trigger calibration update (learning loop)."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id, tenant_id FROM contract WHERE id=:id"
        ), {"id": contract_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    tenant_id = str(row[1])

    from services.agents.learning_loop import close_contract
    from decimal import Decimal
    result = close_contract(engine, contract_id, Decimal(str(body.actual_cost_pln)), tenant_id)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Backup / DR
# ──────────────────────────────────────────────────────────────────────────────

_BACKUP_DIR = Path(os.environ.get("TERRA_BACKUP_DIR", "/tmp/terra_backups"))
_BACKUP_STATE_FILE = _BACKUP_DIR / "last_backup.json"


@router.get("/system/backup/status", response_model=BackupStatusResponse)
def backup_status() -> BackupStatusResponse:
    if _BACKUP_STATE_FILE.exists():
        data = json.loads(_BACKUP_STATE_FILE.read_text())
        return BackupStatusResponse(
            last_backup_at=data.get("at"),
            last_backup_path=data.get("path"),
            status=data.get("status", "unknown"),
        )
    return BackupStatusResponse(last_backup_at=None, last_backup_path=None, status="never_run")


@router.post("/system/backup/run")
def run_backup() -> dict:
    """Execute pg_dump. Non-blocking check of binary; runs synchronously in test mode."""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    import datetime
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = str(_BACKUP_DIR / f"terraos_{ts}.sql.gz")

    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "terraos")
    db_user = os.environ.get("DB_USER", "terraos")
    db_pass = os.environ.get("DB_PASSWORD", "")

    env = {**os.environ, "PGPASSWORD": db_pass}
    cmd = [
        "pg_dump",
        f"--host={db_host}", f"--port={db_port}",
        f"--username={db_user}", "--format=custom", "--compress=9",
        f"--file={out_path}", db_name,
    ]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=120)
        status = "ok" if result.returncode == 0 else "error"
        error_msg = result.stderr.decode()[:200] if result.returncode != 0 else ""
    except FileNotFoundError:
        # pg_dump not available in test env — record as skipped
        status = "skipped_no_pg_dump"
        error_msg = "pg_dump not found"

    import datetime as _dt
    state = {
        "at": _dt.datetime.utcnow().isoformat(),
        "path": out_path,
        "status": status,
        "error": error_msg,
    }
    _BACKUP_STATE_FILE.write_text(json.dumps(state))
    return state


# ──────────────────────────────────────────────────────────────────────────────
# Audit log read-only
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/audit", response_model=list[AuditEntry])
def read_audit(
    entity: str | None = Query(default=None),
    cursor: int | None = Query(default=None),
    limit: int = Query(default=20, le=100),
) -> list[AuditEntry]:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tenant LIMIT 1")).fetchone()
    if not row:
        return []
    tenant_id = str(row[0])

    filters = ["a.tenant_id=:tid"]
    params: dict = {"tid": tenant_id, "lim": limit}
    if entity:
        filters.append("a.entity=:entity")
        params["entity"] = entity
    if cursor:
        filters.append("a.id < :cursor")
        params["cursor"] = cursor

    where = " AND ".join(filters)
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            f"SELECT id, at, actor, action, entity, entity_id, detail "
            f"FROM audit_log a WHERE {where} ORDER BY id DESC LIMIT :lim"
        ), params).fetchall()

    return [
        AuditEntry(
            id=r[0], at=str(r[1]), actor=r[2], action=r[3],
            entity=r[4], entity_id=str(r[5]) if r[5] else None,
            detail=r[6] if isinstance(r[6], dict) else (json.loads(r[6]) if r[6] else None),
        )
        for r in rows
    ]
