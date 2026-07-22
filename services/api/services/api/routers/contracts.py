"""Contracts router — GET /api/v2/contracts.

Returns contracts for the authenticated user's tenant.
"""
from __future__ import annotations

from fastapi import APIRouter
import sqlalchemy as sa

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/contracts", tags=["contracts"])


@router.get("")
def list_contracts(user: AuthUser, limit: int = 50, offset: int = 0) -> dict:
    """List contracts for the current tenant."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, tenant_id, tender_id, title, state,
                       start_date, end_date, location_address, lat, lng, created_at
                FROM contract
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT :lim OFFSET :off
            """),
            {"tid": tenant_id, "lim": limit, "off": offset},
        ).fetchall()

        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM contract WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).scalar()

    items = [
        {
            "id": str(r.id),
            "tender_id": str(r.tender_id) if r.tender_id else None,
            "title": r.title,
            "state": r.state,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "location_address": r.location_address,
            "lat": float(r.lat) if r.lat else None,
            "lng": float(r.lng) if r.lng else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}
