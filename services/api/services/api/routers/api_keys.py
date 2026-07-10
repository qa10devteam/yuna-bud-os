"""Faza 73 — API Key management endpoints.

Endpoints:
  POST   /api/v2/api-keys        — create new API key (plain text shown ONCE)
  GET    /api/v2/api-keys        — list keys (prefix + name + scopes, no plaintext)
  DELETE /api/v2/api-keys/{id}   — revoke / delete key
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/api-keys", tags=["api-keys"])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]

_KEY_PREFIX = "terra_"
_KEY_BYTES = 32  # 256-bit entropy


# ─── Schemas ───────────────────────────────────────────────────────────────────

class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: str | None = None  # ISO datetime string


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    plain_key: str  # shown ONCE — not stored
    created_at: str


class ApiKeyInfo(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: str | None
    expires_at: str | None
    created_at: str


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _generate_key() -> tuple[str, str, str]:
    """Returns (plain_key, key_hash, prefix)."""
    raw = _KEY_PREFIX + secrets.token_urlsafe(_KEY_BYTES)
    prefix = raw[:8]  # e.g. 'terra_aB'
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash, prefix


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=ApiKeyCreated, status_code=201)
def create_api_key(body: CreateApiKeyRequest, current_user: AuthUser, db: DB) -> ApiKeyCreated:
    """Generate a new API key. The plain-text key is returned ONLY in this response."""
    plain_key, key_hash, prefix = _generate_key()
    key_id = str(uuid.uuid4())

    db.execute(
        text(
            """
            INSERT INTO api_keys (id, user_id, org_id, name, key_hash, prefix, scopes, expires_at)
            VALUES (:id, :uid, :org_id, :name, :key_hash, :prefix, :scopes, :expires_at)
            """
        ),
        {
            "id": key_id,
            "uid": current_user.user_id,
            "org_id": current_user.org_id,
            "name": body.name,
            "key_hash": key_hash,
            "prefix": prefix,
            "scopes": body.scopes,
            "expires_at": body.expires_at,
        },
    )
    db.commit()

    row = db.execute(
        text("SELECT id, name, prefix, scopes, created_at FROM api_keys WHERE id = :id"),
        {"id": key_id},
    ).fetchone()

    return ApiKeyCreated(
        id=str(row.id),
        name=row.name,
        prefix=row.prefix,
        scopes=list(row.scopes or []),
        plain_key=plain_key,
        created_at=str(row.created_at),
    )


@router.get("", response_model=list[ApiKeyInfo])
def list_api_keys(current_user: AuthUser, db: DB) -> list[ApiKeyInfo]:
    """List API keys for the current user (no plain text, only metadata)."""
    rows = db.execute(
        text(
            """
            SELECT id, name, prefix, scopes, last_used_at, expires_at, created_at
            FROM api_keys
            WHERE user_id = :uid
            ORDER BY created_at DESC
            """
        ),
        {"uid": current_user.user_id},
    ).fetchall()

    return [
        ApiKeyInfo(
            id=str(r.id),
            name=r.name,
            prefix=r.prefix,
            scopes=list(r.scopes or []),
            last_used_at=str(r.last_used_at) if r.last_used_at else None,
            expires_at=str(r.expires_at) if r.expires_at else None,
            created_at=str(r.created_at),
        )
        for r in rows
    ]


@router.delete("/{key_id}", status_code=204)
def delete_api_key(key_id: str, current_user: AuthUser, db: DB) -> None:
    """Revoke and delete an API key. Only the owner can delete their own keys."""
    row = db.execute(
        text("SELECT user_id FROM api_keys WHERE id = :id"),
        {"id": key_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Klucz API nie znaleziony")

    if str(row.user_id) != current_user.user_id and current_user.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Brak dostępu do tego klucza")

    db.execute(text("DELETE FROM api_keys WHERE id = :id"), {"id": key_id})
    db.commit()


# S111 — Rate limit check per API key
@router.get("/rate-limit-check")
def check_rate_limit(current_user: AuthUser, db: DB) -> dict:
    """S111 — Sprawdź zużycie rate limit per klucz API (placeholder + counter)."""
    rows = db.execute(
        text("SELECT id, name, prefix FROM api_keys WHERE org_id = :oid"),
        {"oid": current_user.org_id},
    ).fetchall()
    result = []
    for r in rows:
        # Rate limiting info - could be expanded with Redis counters
        result.append({
            "key_id": str(r.id),
            "name": r.name,
            "prefix": r.prefix,
            "rate_limit_per_hour": 1000,
            "used_this_hour": 0,  # Real impl: check Redis counter
            "status": "ok",
        })
    return {"api_keys": result, "global_rate_limit_per_hour": 10000}
