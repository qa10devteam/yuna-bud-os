"""S13 — Alert Config UI: GET/PUT /api/v2/alerts/smtp-config reads/writes email_configs table."""
from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/alerts", tags=["alert-config"])


class SmtpConfig(BaseModel):
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    from_email: str | None = None
    from_name: str = "YU-NA"
    enabled: bool = True


@router.get("/smtp-config", response_model=SmtpConfig)
def get_smtp_config(user: AuthUser) -> Any:
    """GET current SMTP configuration from email_configs table."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT smtp_host, smtp_port, smtp_user, smtp_pass, from_email, from_name, enabled"
                    " FROM email_configs WHERE org_id = :org_id"),
            {"org_id": user.org_id},
        ).fetchone()
    if not row:
        # Return defaults if no config yet
        return SmtpConfig()
    return SmtpConfig(
        smtp_host=row.smtp_host or "localhost",
        smtp_port=row.smtp_port or 587,
        smtp_user=row.smtp_user,
        smtp_pass="***" if row.smtp_pass else None,  # mask password
        from_email=row.from_email,
        from_name=row.from_name or "YU-NA",
        enabled=row.enabled if row.enabled is not None else True,
    )


@router.put("/smtp-config", response_model=SmtpConfig)
def put_smtp_config(body: SmtpConfig, user: AuthUser) -> Any:
    """PUT (upsert) SMTP configuration into email_configs table."""
    engine = get_engine()
    # Don't overwrite password if masked value was sent
    smtp_pass_val = body.smtp_pass if (body.smtp_pass and body.smtp_pass != "***") else None

    with engine.begin() as conn:
        existing = conn.execute(
            sa.text("SELECT id, smtp_pass FROM email_configs WHERE org_id = :org_id"),
            {"org_id": user.org_id},
        ).fetchone()

        if existing:
            # Preserve existing password if not updated
            new_pass = smtp_pass_val if smtp_pass_val else existing.smtp_pass
            conn.execute(
                sa.text("""
                    UPDATE email_configs
                    SET smtp_host=:h, smtp_port=:p, smtp_user=:u, smtp_pass=:pw,
                        from_email=:fe, from_name=:fn, enabled=:en
                    WHERE org_id=:org_id
                """),
                {
                    "h": body.smtp_host, "p": body.smtp_port, "u": body.smtp_user,
                    "pw": new_pass, "fe": body.from_email, "fn": body.from_name,
                    "en": body.enabled, "org_id": user.org_id,
                },
            )
        else:
            conn.execute(
                sa.text("""
                    INSERT INTO email_configs (org_id, smtp_host, smtp_port, smtp_user, smtp_pass, from_email, from_name, enabled)
                    VALUES (:org_id, :h, :p, :u, :pw, :fe, :fn, :en)
                """),
                {
                    "org_id": user.org_id, "h": body.smtp_host, "p": body.smtp_port,
                    "u": body.smtp_user, "pw": smtp_pass_val, "fe": body.from_email,
                    "fn": body.from_name, "en": body.enabled,
                },
            )
    return get_smtp_config(user)
