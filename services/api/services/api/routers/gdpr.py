"""Faza 66-70 — GDPR compliance endpoints.

Endpoints:
  GET    /api/v2/gdpr/export           — export all user data as JSON (Art. 20)
  DELETE /api/v2/gdpr/account          — soft-delete + anonymise account (Art. 17)
  POST   /api/v2/gdpr/consent          — record user consent (Art. 7)
  GET    /api/v2/gdpr/consent          — get consent status
  GET    /api/v2/gdpr/audit-trail      — audit trail for user (Art. 15)
"""
from __future__ import annotations


from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/gdpr", tags=["gdpr"])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


# ─── Schemas ───────────────────────────────────────────────────────────────────

class ConsentRequest(BaseModel):
    analytics: bool = False
    marketing: bool = False
    third_party: bool = False


class SingleConsentRequest(BaseModel):
    consent_type: Literal['analytics', 'marketing', 'third_party']
    granted: bool


# ─── Faza 67: Data Export ──────────────────────────────────────────────────────

@router.get("/export")
def gdpr_export(current_user: AuthUser, db: DB) -> dict[str, Any]:
    """Export all personal data for the authenticated user as JSON (GDPR Art. 20)."""

    user_row = db.execute(
        text("SELECT id, email, name, org_id, role, is_active, created_at FROM users WHERE id = :uid"),
        {"uid": current_user.user_id},
    ).fetchone()

    if not user_row:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")

    user_data = {
        "id": str(user_row.id),
        "email": user_row.email,
        "name": user_row.name,
        "org_id": str(user_row.org_id) if user_row.org_id else None,
        "role": user_row.role,
        "is_active": user_row.is_active,
        "created_at": str(user_row.created_at),
    }

    # Tenders owned by user's org
    tenders: list[dict] = []
    if current_user.org_id:
        try:
            tender_rows = db.execute(
                text(
                    "SELECT id, name, status, created_at FROM tenders WHERE org_id = :org_id ORDER BY created_at DESC"
                ),
                {"org_id": current_user.org_id},
            ).fetchall()
            tenders = [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "status": r.status,
                    "created_at": str(r.created_at),
                }
                for r in tender_rows
            ]
        except Exception:
            tenders = []

    # Decisions made by user
    decisions: list[dict] = []
    try:
        decision_rows = db.execute(
            text(
                "SELECT id, tender_id, decision, created_at FROM decisions WHERE user_id = :uid ORDER BY created_at DESC"
            ),
            {"uid": current_user.user_id},
        ).fetchall()
        decisions = [
            {
                "id": str(r.id),
                "tender_id": str(r.tender_id),
                "decision": r.decision,
                "created_at": str(r.created_at),
            }
            for r in decision_rows
        ]
    except Exception:
        decisions = []

    # Audit log entries
    audit_entries: list[dict] = []
    try:
        audit_rows = db.execute(
            text(
                "SELECT id, action, entity_type, entity_id, created_at FROM audit_log WHERE actor_id = :uid ORDER BY created_at DESC LIMIT 100"
            ),
            {"uid": current_user.user_id},
        ).fetchall()
        audit_entries = [
            {
                "id": str(r.id),
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "created_at": str(r.created_at),
            }
            for r in audit_rows
        ]
    except Exception:
        audit_entries = []

    return {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": user_data,
        "tenders": tenders,
        "decisions": decisions,
        "audit_trail": audit_entries,
    }


# ─── Faza 68: Account Deletion ────────────────────────────────────────────────

@router.delete("/account", status_code=200)
def gdpr_delete_account(
    current_user: AuthUser,
    db: DB,
    x_confirm_delete: str | None = Header(default=None, alias="X-Confirm-Delete"),
) -> dict[str, str]:
    """Soft-delete user account: deactivate + anonymise email (GDPR Art. 17).

    Requires header: X-Confirm-Delete: yes
    """
    if x_confirm_delete != "yes":
        raise HTTPException(
            status_code=400,
            detail="Wymagany nagłówek X-Confirm-Delete: yes do potwierdzenia usunięcia konta",
        )

    anonymised_email = f"deleted_{current_user.user_id}@terra.deleted"

    db.execute(
        text(
            """
            UPDATE users
            SET is_active = false,
                email = :anon_email,
                name = 'Usunięty użytkownik'
            WHERE id = :uid
            """
        ),
        {"anon_email": anonymised_email, "uid": current_user.user_id},
    )

    # Revoke all refresh tokens
    try:
        db.execute(
            text("UPDATE refresh_tokens SET revoked = true WHERE user_id = :uid"),
            {"uid": current_user.user_id},
        )
    except Exception:
        pass

    db.commit()

    return {"status": "deleted", "message": "Konto zostało usunięte i zanonimizowane"}


# ─── Faza 69: Consent Management ──────────────────────────────────────────────

@router.post("/consent", status_code=200)
def record_consent(body: ConsentRequest, current_user: AuthUser, db: DB) -> dict[str, Any]:
    """Record user consent choices (GDPR Art. 7)."""
    try:
        db.execute(
            text("""
                INSERT INTO gdpr_consents (user_id, analytics, marketing, third_party, recorded_at)
                VALUES (:uid, :analytics, :marketing, :third_party, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    analytics = EXCLUDED.analytics,
                    marketing = EXCLUDED.marketing,
                    third_party = EXCLUDED.third_party,
                    recorded_at = NOW()
            """),
            {
                "uid": current_user.user_id,
                "analytics": body.analytics,
                "marketing": body.marketing,
                "third_party": body.third_party,
            },
        )
        db.commit()
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Failed to record GDPR consent for user %s: %s", current_user.user_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to record consent") from exc

    return {
        "status": "recorded",
        "consent": {
            "analytics": body.analytics,
            "marketing": body.marketing,
            "third_party": body.third_party,
        },
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.patch("/consent", status_code=200)
def update_single_consent(body: SingleConsentRequest, current_user: AuthUser, db: DB) -> dict[str, Any]:
    """Update a single consent field (GDPR Art. 7)."""
    allowed = {"analytics", "marketing", "third_party"}
    field = body.consent_type
    if field not in allowed:
        raise HTTPException(status_code=422, detail=f"consent_type must be one of {allowed}")

    try:
        db.execute(
            text(f"""
                INSERT INTO gdpr_consents (user_id, analytics, marketing, third_party, recorded_at)
                VALUES (:uid, False, False, False, NOW())
                ON CONFLICT (user_id) DO UPDATE SET {field} = :granted, recorded_at = NOW()
            """),
            {"uid": current_user.user_id, "granted": body.granted},
        )
        db.commit()
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Failed to update GDPR consent for user %s: %s", current_user.user_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update consent") from exc

    consent = {f: False for f in allowed}
    consent[field] = body.granted
    return {
        "status": "recorded",
        "consent": consent,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/consent")
def get_consent(current_user: AuthUser, db: DB) -> dict[str, Any]:
    try:
        row = db.execute(
            text("SELECT analytics, marketing, third_party, recorded_at FROM gdpr_consents WHERE user_id = :uid"),
            {"uid": current_user.user_id},
        ).fetchone()

        if row:
            return {
                "analytics": row.analytics,
                "marketing": row.marketing,
                "third_party": row.third_party,
                "recorded_at": str(row.recorded_at),
            }
    except Exception:
        pass

    return {
        "analytics": False,
        "marketing": False,
        "third_party": False,
        "recorded_at": None,
    }


# ─── Faza 70: Audit Trail ─────────────────────────────────────────────────────

@router.get("/audit-trail")
def audit_trail(current_user: AuthUser, db: DB, limit: int = 50) -> dict[str, Any]:
    """Return audit trail for current user (GDPR Art. 15 - right of access)."""
    entries: list[dict] = []
    try:
        rows = db.execute(
            text("""
                SELECT id, action, entity_type, entity_id, meta, created_at
                FROM audit_log
                WHERE actor_id = :uid
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"uid": current_user.user_id, "limit": min(limit, 200)},
        ).fetchall()
        entries = [
            {
                "id": str(r.id),
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "meta": r.meta,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    except Exception:
        entries = []

    return {
        "total": len(entries),
        "entries": entries,
        "user_id": current_user.user_id,
    }
