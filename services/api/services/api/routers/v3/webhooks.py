"""S109 — API v3 Webhooks: GET/POST/DELETE /api/v3/webhooks"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ...auth.deps import AuthUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v3/webhooks", tags=["webhooks-v3"])


class WebhookCreate(BaseModel):
    url: str
    events: list[str] = ["tender.matched"]


class WebhookOut(BaseModel):
    id: str
    url: str
    events: list[str]
    enabled: bool


def _validate_url(url: str) -> None:
    """SSRF protection: reject local/internal URLs."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid URL")
    hostname = parsed.hostname or ""
    bad = ["127.0.0.1", "localhost", "0.0.0.0", "::1"]
    if hostname in bad:
        raise HTTPException(status_code=422, detail="Internal URLs not allowed")
    for prefix in ["10.", "192.168.", "172."]:
        if hostname.startswith(prefix):
            raise HTTPException(status_code=422, detail="Internal network URLs not allowed")


def _resolve_tenant_org(engine: sa.Engine, user: AuthUser) -> tuple[str, str]:
    org_id = user.org_id
    if not org_id:
        raise HTTPException(status_code=403, detail="no_org")
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT tenant_id FROM organizations WHERE id = :oid LIMIT 1"),
            {"oid": org_id},
        ).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="tenant not found")
    return org_id, str(row[0])


@router.get("", response_model=list[WebhookOut])
def list_webhooks(user: AuthUser) -> list[WebhookOut]:
    """S109 — lista webhooków dla tenant."""
    engine = get_engine()
    org_id, tenant_id = _resolve_tenant_org(engine, user)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id::text, url, events, enabled FROM webhooks WHERE org_id = :oid ORDER BY created_at DESC"),
            {"oid": org_id},
        ).fetchall()
    return [WebhookOut(id=r[0], url=r[1], events=list(r[2] or []), enabled=bool(r[3])) for r in rows]


@router.post("", response_model=WebhookOut, status_code=201)
def create_webhook(body: WebhookCreate, user: AuthUser) -> WebhookOut:
    """S109 — tworzenie webhooka."""
    _validate_url(body.url)
    engine = get_engine()
    org_id, _tenant_id = _resolve_tenant_org(engine, user)
    with engine.begin() as conn:
        row = conn.execute(
            sa.text(
                "INSERT INTO webhooks(org_id, name, url, events) "
                "VALUES (:oid, :name, :url, :events) RETURNING id::text, url, events, enabled"
            ),
            {"oid": org_id, "name": body.url[:50], "url": body.url, "events": body.events},
        ).fetchone()
    return WebhookOut(id=row[0], url=row[1], events=list(row[2] or []), enabled=bool(row[3]))


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: str, user: AuthUser) -> None:
    """S109 — usunięcie webhooka."""
    engine = get_engine()
    org_id, _tenant_id = _resolve_tenant_org(engine, user)
    with engine.begin() as conn:
        result = conn.execute(
            sa.text("DELETE FROM webhooks WHERE id = :wid AND org_id = :oid"),
            {"wid": webhook_id, "oid": org_id},
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
