"""
S93 — Workflow Definitions CRUD.
GET /api/v2/workflows
POST /api/v2/workflows
PUT /api/v2/workflows/{id}
DELETE /api/v2/workflows/{id}
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user, CurrentUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/workflows", tags=["workflows"])


# ─── Models ────────────────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    definition: dict = Field(default_factory=dict, description="BPMN-like JSON definition")
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    name: str | None = None
    definition: dict | None = None
    is_active: bool | None = None


# ─── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_table() -> None:
    """Create workflow_definition table if not exists (idempotent)."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS workflow_definition (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                name TEXT NOT NULL,
                definition JSONB NOT NULL DEFAULT '{}',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        conn.commit()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
def list_workflows(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """GET /api/v2/workflows — list all workflows for tenant."""
    try:
        _ensure_table()
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT id, tenant_id, name, definition, is_active, created_at, updated_at
                FROM workflow_definition
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """), {"tid": str(user.org_id)}).fetchall()
        return [
            {
                "id": str(r[0]),
                "tenant_id": str(r[1]),
                "name": r[2],
                "definition": r[3],
                "is_active": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
                "updated_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.exception("list_workflows: %s", e)
        return []


@router.post("", status_code=201)
def create_workflow(
    body: WorkflowCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """POST /api/v2/workflows."""
    _ensure_table()
    wf_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("""
            INSERT INTO workflow_definition (id, tenant_id, name, definition, is_active, created_at, updated_at)
            VALUES (:id, :tid, :name, :def::jsonb, :active, :now, :now)
        """), {
            "id": wf_id,
            "tid": str(user.org_id),
            "name": body.name,
            "def": sa.func.cast(body.definition, sa.JSON).__str__() if False else __import__("json").dumps(body.definition),
            "active": body.is_active,
            "now": now,
        })
        conn.commit()
    return {"id": wf_id, "name": body.name, "is_active": body.is_active, "created_at": now.isoformat()}


@router.put("/{wf_id}")
def update_workflow(
    wf_id: str,
    body: WorkflowUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """PUT /api/v2/workflows/{id}."""
    _ensure_table()
    updates: list[str] = []
    params: dict[str, Any] = {"id": wf_id, "tid": str(user.org_id), "now": datetime.now(timezone.utc)}
    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.definition is not None:
        updates.append("definition = :def::jsonb")
        params["def"] = __import__("json").dumps(body.definition)
    if body.is_active is not None:
        updates.append("is_active = :active")
        params["active"] = body.is_active
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates.append("updated_at = :now")
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(sa.text(f"""
            UPDATE workflow_definition SET {', '.join(updates)}
            WHERE id = :id AND tenant_id = :tid
        """), params)
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(404, "Workflow not found")
    return {"id": wf_id, "updated": True}


@router.delete("/{wf_id}", status_code=204)
def delete_workflow(
    wf_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """DELETE /api/v2/workflows/{id}."""
    _ensure_table()
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(sa.text("""
            DELETE FROM workflow_definition WHERE id = :id AND tenant_id = :tid
        """), {"id": wf_id, "tid": str(user.org_id)})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(404, "Workflow not found")
