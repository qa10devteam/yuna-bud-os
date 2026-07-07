"""Faza 3 — Buyer CRM API.

Endpoints:
  GET    /api/v2/buyer-crm/search         — szukaj zamawiającego (atlas_buyers, 23k)
  GET    /api/v2/buyer-crm/followups      — follow-upy na dziś i ten tydzień
  GET    /api/v2/buyer-crm                — lista zamawiających w CRM (paginacja + filtry)
  POST   /api/v2/buyer-crm                — dodaj zamawiającego do CRM
  GET    /api/v2/buyer-crm/{id}           — profil + enrichment atlas_buyers
  PUT    /api/v2/buyer-crm/{id}           — aktualizuj CRM stage/kontakt/notatki
  DELETE /api/v2/buyer-crm/{id}           — usuń z CRM
  GET    /api/v2/buyer-crm/{id}/tenders   — historia przetargów + spend z MV

Tabela: buyer_crm (UNIQUE per tenant+buyer_nip)
Stage flow: prospect → contacted → demo → active → churned
"""
from __future__ import annotations

import logging
import re as _re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.deps import AuthUser
from terra_db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/buyer-crm", tags=["buyer-crm"])

VALID_STAGES = ("prospect", "contacted", "demo", "active", "churned")
_NIP_RE = _re.compile(r'^[0-9]{8,12}$')


def get_db():
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(get_db)]


def _require_org(user: Any) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="Użytkownik nie należy do żadnej organizacji")
    return user.org_id


# ─── Schematy ─────────────────────────────────────────────────────────────────

class BuyerCRMCreate(BaseModel):
    buyer_nip: str = Field(..., min_length=1, max_length=12)  # length validated in endpoint
    crm_stage: str = "prospect"
    priority: int = Field(3, ge=1, le=5)
    contact_name: str | None = Field(None, max_length=300)
    contact_email: str | None = Field(None, max_length=300)
    contact_phone: str | None = Field(None, max_length=50)
    annual_budget_est: float | None = Field(None, ge=0)
    preferred_cpv: list[str] = Field(default_factory=list)
    territory: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=5000)
    last_contact: str | None = None
    next_followup: str | None = None
    # NOTE: buyer_nip and crm_stage validated in endpoint (returns 400 not 422)


class BuyerCRMUpdate(BaseModel):
    crm_stage: str | None = None
    priority: int | None = Field(None, ge=1, le=5)
    contact_name: str | None = Field(None, max_length=300)
    contact_email: str | None = Field(None, max_length=300)
    contact_phone: str | None = Field(None, max_length=50)
    annual_budget_est: float | None = Field(None, ge=0)
    preferred_cpv: list[str] | None = None
    territory: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=5000)
    last_contact: str | None = None
    next_followup: str | None = None
    # NOTE: crm_stage validated in endpoint (returns 400 not 422)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/search", summary="Szukaj zamawiającego w atlas_buyers (23k)")
def search_buyers(
    user: AuthUser,
    db: DB,
    q: str = Query(..., min_length=2, description="Nazwa lub NIP zamawiającego"),
    limit: int = Query(20, le=50),
):
    _require_org(user)
    rows = db.execute(text("""
        SELECT nip, name, city, province,
               total_tenders, total_value, top_cpv
        FROM atlas_buyers
        WHERE name ILIKE :q OR nip LIKE :nip_q
        ORDER BY total_tenders DESC NULLS LAST
        LIMIT :limit
    """), {"q": f"%{q}%", "nip_q": f"{q}%", "limit": limit}).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@router.get("/followups", summary="Follow-upy na dziś i ten tydzień")
def followups(
    user: AuthUser,
    db: DB,
    days: int = Query(7, ge=1, le=30, description="Okno czasowe w dniach"),
):
    org_id = _require_org(user)
    rows = db.execute(text("""
        SELECT crm.id, crm.buyer_nip, crm.crm_stage, crm.priority,
               crm.contact_name, crm.contact_phone, crm.contact_email,
               crm.next_followup, crm.notes,
               ab.name AS buyer_name, ab.city, ab.province
        FROM buyer_crm crm
        LEFT JOIN atlas_buyers ab ON ab.nip = crm.buyer_nip
        WHERE crm.tenant_id = :org_id
          AND crm.next_followup <= CURRENT_DATE + (:days * INTERVAL '1 day')
          AND crm.next_followup IS NOT NULL
          AND crm.crm_stage NOT IN ('churned')
        ORDER BY crm.next_followup ASC, crm.priority ASC
    """), {"org_id": org_id, "days": days}).mappings().all()

    overdue = [r for r in rows if r["next_followup"] and str(r["next_followup"]) < str(__import__("datetime").date.today())]

    return {
        "followups": [dict(r) for r in rows],
        "total": len(rows),
        "overdue": len(overdue),
    }


@router.get("", summary="Lista zamawiających w CRM")
def list_crm(
    user: AuthUser,
    db: DB,
    stage: str | None = Query(None, description="Filtr stage CRM"),
    priority: int | None = Query(None, ge=1, le=5),
    territory: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    org_id = _require_org(user)

    if stage and stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowy stage: {stage}")

    conditions = ["crm.tenant_id = :org_id"]
    params: dict = {"org_id": org_id, "limit": limit, "offset": offset}

    if stage:
        conditions.append("crm.crm_stage = :stage")
        params["stage"] = stage
    if priority:
        conditions.append("crm.priority = :priority")
        params["priority"] = priority
    if territory:
        conditions.append("crm.territory ILIKE :territory")
        params["territory"] = f"%{territory}%"

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT crm.id, crm.buyer_nip, crm.crm_stage, crm.priority,
               crm.contact_name, crm.contact_email, crm.contact_phone,
               crm.annual_budget_est, crm.territory, crm.notes,
               crm.last_contact, crm.next_followup, crm.created_at, crm.updated_at,
               ab.name AS buyer_name, ab.city, ab.province,
               ab.total_tenders, ab.total_value
        FROM buyer_crm crm
        LEFT JOIN atlas_buyers ab ON ab.nip = crm.buyer_nip
        WHERE {where}
        ORDER BY crm.priority ASC, crm.next_followup ASC NULLS LAST, crm.created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(
        f"SELECT count(*) FROM buyer_crm crm WHERE {where}"
    ), params).scalar()

    return {"items": [dict(r) for r in rows], "total": total, "offset": offset, "limit": limit}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Dodaj zamawiającego do CRM")
def create_crm(body: BuyerCRMCreate, user: AuthUser, db: DB):
    org_id = _require_org(user)

    # Manual stage validation → 400 (nie 422 z Pydantic — dla spójności API)
    if body.crm_stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"crm_stage musi być jednym z: {VALID_STAGES}")

    # Manual NIP validation → 422 (format error)
    if not _NIP_RE.match(body.buyer_nip):
        raise HTTPException(status_code=422, detail="buyer_nip musi zawierać 8-12 cyfr")

    try:
        row = db.execute(text("""
            INSERT INTO buyer_crm (
                tenant_id, buyer_nip, crm_stage, priority,
                contact_name, contact_email, contact_phone,
                annual_budget_est, preferred_cpv, territory,
                notes, last_contact, next_followup
            ) VALUES (
                :org_id, :buyer_nip, :crm_stage, :priority,
                :contact_name, :contact_email, :contact_phone,
                :annual_budget_est, :preferred_cpv, :territory,
                :notes, :last_contact, :next_followup
            )
            RETURNING id, buyer_nip, crm_stage, priority, created_at
        """), {"org_id": org_id, **body.model_dump()}).mappings().one()
        db.commit()
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Zamawiający już w CRM")
        logger.error("create_crm error: %s", e)
        raise HTTPException(status_code=500, detail="Błąd zapisu")

    return dict(row)


@router.get("/{crm_id}", summary="Profil zamawiającego z enrichmentem atlas_buyers")
def get_crm(crm_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    row = db.execute(text("""
        SELECT crm.id, crm.buyer_nip, crm.crm_stage, crm.priority,
               crm.contact_name, crm.contact_email, crm.contact_phone,
               crm.annual_budget_est, crm.preferred_cpv, crm.territory,
               crm.notes, crm.last_contact, crm.next_followup,
               crm.created_at, crm.updated_at,
               ab.name AS buyer_name, ab.city, ab.province,
               ab.total_tenders, ab.total_value, ab.top_cpv
        FROM buyer_crm crm
        LEFT JOIN atlas_buyers ab ON ab.nip = crm.buyer_nip
        WHERE crm.id = :id AND crm.tenant_id = :org_id
    """), {"id": str(crm_id), "org_id": org_id}).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Wpis CRM nie istnieje")
    return dict(row)


@router.put("/{crm_id}", summary="Aktualizuj CRM — stage / kontakt / notatki")
def update_crm(crm_id: UUID, body: BuyerCRMUpdate, user: AuthUser, db: DB):
    org_id = _require_org(user)

    # Manual stage validation → 400
    if body.crm_stage is not None and body.crm_stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"crm_stage musi być jednym z: {VALID_STAGES}")

    existing = db.execute(text(
        "SELECT id FROM buyer_crm WHERE id = :id AND tenant_id = :org_id"
    ), {"id": str(crm_id), "org_id": org_id}).one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Wpis CRM nie istnieje")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Brak pól do aktualizacji")

    set_parts = ", ".join([f"{k} = :{k}" for k in updates])
    updates["id"] = str(crm_id)
    db.execute(text(
        f"UPDATE buyer_crm SET {set_parts} WHERE id = :id"
    ), updates)
    db.commit()
    return {"status": "ok", "id": str(crm_id), "updated_fields": list(updates.keys())}


@router.delete("/{crm_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń z CRM")
def delete_crm(crm_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    result = db.execute(text(
        "DELETE FROM buyer_crm WHERE id = :id AND tenant_id = :org_id"
    ), {"id": str(crm_id), "org_id": org_id})
    db.commit()
    if getattr(result, "rowcount", 1) == 0:
        raise HTTPException(status_code=404, detail="Wpis CRM nie istnieje")


@router.get("/{crm_id}/tenders", summary="Historia przetargów zamawiającego + spend z MV")
def buyer_tenders(
    crm_id: UUID,
    user: AuthUser,
    db: DB,
    limit: int = Query(50, le=200),
    cpv_prefix: str | None = Query(None, description="Filtr CPV prefix np. '4523'"),
    year: int | None = Query(None, description="Rok np. 2024"),
):
    org_id = _require_org(user)
    crm = db.execute(text(
        "SELECT buyer_nip FROM buyer_crm WHERE id = :id AND tenant_id = :org_id"
    ), {"id": str(crm_id), "org_id": org_id}).one_or_none()
    if not crm:
        raise HTTPException(status_code=404, detail="Wpis CRM nie istnieje")

    nip = crm[0]
    conditions = ["buyer_nip = :nip"]
    params: dict = {"nip": nip, "limit": limit}

    if cpv_prefix:
        conditions.append("cpv_code LIKE :cpv_q")
        params["cpv_q"] = f"{cpv_prefix}%"
    if year:
        conditions.append("EXTRACT(YEAR FROM date::date) = :year")
        params["year"] = year

    where = " AND ".join(conditions)
    tenders = db.execute(text(f"""
        SELECT id, title, cpv_code, province, estimated_value,
               offers_count, procedure_result, date, notice_type,
               contractor_name, contractor_national_id AS contractor_nip
        FROM historical_tenders
        WHERE {where}
        ORDER BY date DESC
        LIMIT :limit
    """), params).mappings().all()

    # Spend history z MV
    spend = db.execute(text("""
        SELECT cpv5, quarter, n_tenders, n_completed,
               avg_value, total_value, avg_competition
        FROM mv_buyer_quarterly_spend
        WHERE buyer_nip = :nip
        ORDER BY quarter DESC
        LIMIT 16
    """), {"nip": nip}).mappings().all()

    # Summary stats
    total_tenders = db.execute(text(
        "SELECT count(*) FROM historical_tenders WHERE buyer_nip = :nip"
    ), {"nip": nip}).scalar()

    return {
        "buyer_nip": nip,
        "total_tenders_all_time": total_tenders,
        "tenders": [dict(r) for r in tenders],
        "spend_history": [dict(r) for r in spend],
    }
