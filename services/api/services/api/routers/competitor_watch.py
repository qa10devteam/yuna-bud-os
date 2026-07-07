"""Faza 3 — Competitor Watch API.

Endpoints:
  GET    /api/v2/competitors/search        — szukaj firm po nazwie/NIP (atlas_contractors)
  GET    /api/v2/competitors               — lista obserwowanych konkurentów
  POST   /api/v2/competitors               — dodaj firmę do watchlisty
  GET    /api/v2/competitors/{id}          — profil + enrichment atlas_contractors
  PUT    /api/v2/competitors/{id}          — aktualizuj notes/tags/notify
  DELETE /api/v2/competitors/{id}          — usuń z watchlisty
  GET    /api/v2/competitors/{id}/wins     — ostatnie wygrane (mv_competitor_recent_wins)
  GET    /api/v2/competitors/intel/{nip}   — pełny profil rynkowy firmy (nie w watchliście)

Tabela: competitor_watch (UNIQUE per tenant+nip)
Źródła: atlas_contractors (81k firm), mv_competitor_recent_wins (91k wygranych)
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

router = APIRouter(prefix="/api/v2/competitors", tags=["competitor-watch"])

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

class CompetitorCreate(BaseModel):
    competitor_nip: str = Field(..., min_length=8, max_length=12)
    competitor_name: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    notify_on_win: bool = True

    @field_validator("competitor_nip")
    @classmethod
    def validate_nip(cls, v: str) -> str:
        if not _NIP_RE.match(v):
            raise ValueError("competitor_nip musi zawierać 8-12 cyfr")
        return v


class CompetitorUpdate(BaseModel):
    competitor_name: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=5000)
    tags: list[str] | None = None
    notify_on_win: bool | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/search", summary="Szukaj firm w bazie atlas_contractors (81k)")
def search_contractors(
    user: AuthUser,
    db: DB,
    q: str = Query(..., min_length=2, description="Nazwa lub NIP firmy"),
    limit: int = Query(20, le=50),
):
    _require_org(user)
    rows = db.execute(text("""
        SELECT nip, name, city, province,
               total_wins, total_value, win_rate, top_cpv
        FROM atlas_contractors
        WHERE name ILIKE :q OR nip LIKE :nip_q
        ORDER BY total_wins DESC NULLS LAST
        LIMIT :limit
    """), {"q": f"%{q}%", "nip_q": f"{q}%", "limit": limit}).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@router.get("", summary="Lista obserwowanych konkurentów z enrichmentem")
def list_watched(
    user: AuthUser,
    db: DB,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    org_id = _require_org(user)
    rows = db.execute(text("""
        SELECT cw.id, cw.competitor_nip, cw.competitor_name,
               cw.notes, cw.tags, cw.notify_on_win, cw.created_at, cw.updated_at,
               ac.city, ac.province, ac.total_wins, ac.total_value,
               ac.win_rate, ac.top_cpv
        FROM competitor_watch cw
        LEFT JOIN atlas_contractors ac ON ac.nip = cw.competitor_nip
        WHERE cw.tenant_id = :org_id
        ORDER BY cw.created_at DESC
        LIMIT :limit OFFSET :offset
    """), {"org_id": org_id, "limit": limit, "offset": offset}).mappings().all()

    total = db.execute(text(
        "SELECT count(*) FROM competitor_watch WHERE tenant_id = :org_id"
    ), {"org_id": org_id}).scalar()

    return {"items": [dict(r) for r in rows], "total": total, "offset": offset, "limit": limit}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Dodaj firmę do watchlisty")
def add_competitor(body: CompetitorCreate, user: AuthUser, db: DB):
    org_id = _require_org(user)

    # Auto-enrich nazwą z atlas_contractors jeśli nie podano
    name = body.competitor_name
    if not name:
        ac = db.execute(text(
            "SELECT name FROM atlas_contractors WHERE nip = :nip"
        ), {"nip": body.competitor_nip}).one_or_none()
        if ac:
            name = ac[0]

    try:
        row = db.execute(text("""
            INSERT INTO competitor_watch (
                tenant_id, competitor_nip, competitor_name, notes, tags, notify_on_win
            ) VALUES (
                :org_id, :nip, :name, :notes, :tags, :notify
            )
            RETURNING id, competitor_nip, competitor_name, notify_on_win, created_at
        """), {
            "org_id": org_id,
            "nip": body.competitor_nip,
            "name": name,
            "notes": body.notes,
            "tags": body.tags,
            "notify": body.notify_on_win,
        }).mappings().one()
        db.commit()
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Firma już na watchliście")
        logger.error("add_competitor error: %s", e)
        raise HTTPException(status_code=500, detail="Błąd zapisu")
    return dict(row)


@router.get("/{watch_id}", summary="Profil obserwowanego konkurenta z enrichmentem")
def get_competitor(watch_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    row = db.execute(text("""
        SELECT cw.id, cw.competitor_nip, cw.competitor_name,
               cw.notes, cw.tags, cw.notify_on_win, cw.created_at, cw.updated_at,
               ac.city, ac.province, ac.total_wins, ac.total_value,
               ac.win_rate, ac.top_cpv
        FROM competitor_watch cw
        LEFT JOIN atlas_contractors ac ON ac.nip = cw.competitor_nip
        WHERE cw.id = :id AND cw.tenant_id = :org_id
    """), {"id": str(watch_id), "org_id": org_id}).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Konkurent nie znaleziony")
    return dict(row)


@router.put("/{watch_id}", summary="Aktualizuj notatki / tagi / notify")
def update_competitor(watch_id: UUID, body: CompetitorUpdate, user: AuthUser, db: DB):
    org_id = _require_org(user)
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Brak pól do aktualizacji")

    # Sprawdź czy rekord istnieje
    existing = db.execute(text(
        "SELECT id FROM competitor_watch WHERE id = :id AND tenant_id = :org_id"
    ), {"id": str(watch_id), "org_id": org_id}).one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Konkurent nie znaleziony")

    set_parts = ", ".join([f"{k} = :{k}" for k in updates])
    updates["id"] = str(watch_id)
    db.execute(text(
        f"UPDATE competitor_watch SET {set_parts} WHERE id = :id"
    ), updates)
    db.commit()
    return {"status": "ok", "id": str(watch_id)}


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń z watchlisty")
def remove_competitor(watch_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    result = db.execute(text(
        "DELETE FROM competitor_watch WHERE id = :id AND tenant_id = :org_id"
    ), {"id": str(watch_id), "org_id": org_id})
    db.commit()
    if getattr(result, "rowcount", 1) == 0:
        raise HTTPException(status_code=404, detail="Konkurent nie znaleziony")


@router.get("/{watch_id}/wins", summary="Ostatnie wygrane z mv_competitor_recent_wins")
def competitor_wins(
    watch_id: UUID,
    user: AuthUser,
    db: DB,
    limit: int = Query(50, le=200),
    cpv_prefix: str | None = Query(None, description="Filtr CPV prefix np. '4523'"),
    province: str | None = Query(None),
):
    org_id = _require_org(user)
    cw = db.execute(text("""
        SELECT competitor_nip FROM competitor_watch WHERE id = :id AND tenant_id = :org_id
    """), {"id": str(watch_id), "org_id": org_id}).one_or_none()
    if not cw:
        raise HTTPException(status_code=404, detail="Konkurent nie znaleziony")

    nip = cw[0]
    conditions = ["contractor_nip = :nip"]
    params: dict = {"nip": nip, "limit": limit}

    if cpv_prefix:
        conditions.append("cpv5 LIKE :cpv_q")
        params["cpv_q"] = f"{cpv_prefix}%"
    if province:
        conditions.append("tender_province = :province")
        params["province"] = province

    where = " AND ".join(conditions)
    rows = db.execute(text(f"""
        SELECT contractor_nip, contractor_name, cpv5, tender_province,
               win_date, value, buyer_name, buyer_nip, title, ht_id
        FROM mv_competitor_recent_wins
        WHERE {where}
        ORDER BY win_date DESC
        LIMIT :limit
    """), params).mappings().all()

    # Stats
    total_value = sum(float(r["value"]) for r in rows if r.get("value") is not None)

    return {
        "nip": nip,
        "wins": [dict(r) for r in rows],
        "total": len(rows),
        "total_value": round(total_value) if total_value else None,
    }


@router.get("/intel/{nip}", summary="Pełny profil rynkowy firmy po NIP")
def competitor_intel(
    nip: str,
    user: AuthUser,
    db: DB,
):
    """Deep intel: atlas_contractors + wygrane per CPV5/region (2 lata)."""
    _require_org(user)

    if not _NIP_RE.match(nip):
        raise HTTPException(status_code=400, detail="Nieprawidłowy format NIP (8-12 cyfr)")

    profile = db.execute(text("""
        SELECT nip, name, city, province, total_wins, total_value,
               win_rate, top_cpv
        FROM atlas_contractors WHERE nip = :nip
    """), {"nip": nip}).mappings().one_or_none()

    cpv_breakdown = db.execute(text("""
        SELECT left(cpv_code, 5) AS cpv5, count(*) AS wins,
               round(avg(estimated_value)::numeric) AS avg_value,
               round(sum(estimated_value)::numeric) AS total_value
        FROM historical_tenders
        WHERE contractor_national_id = :nip
          AND procedure_result = 'zawarcieUmowy'
          AND date >= (SELECT max(date) FROM historical_tenders) - INTERVAL '2 years'
        GROUP BY 1 ORDER BY wins DESC LIMIT 10
    """), {"nip": nip}).mappings().all()

    region_breakdown = db.execute(text("""
        SELECT province, count(*) AS wins,
               round(avg(estimated_value)::numeric) AS avg_value,
               round(sum(estimated_value)::numeric) AS total_value
        FROM historical_tenders
        WHERE contractor_national_id = :nip
          AND procedure_result = 'zawarcieUmowy'
          AND date >= (SELECT max(date) FROM historical_tenders) - INTERVAL '2 years'
        GROUP BY 1 ORDER BY wins DESC LIMIT 10
    """), {"nip": nip}).mappings().all()

    recent_wins = db.execute(text("""
        SELECT cpv5, tender_province, win_date, value,
               buyer_name, title, ht_id
        FROM mv_competitor_recent_wins
        WHERE contractor_nip = :nip
        ORDER BY win_date DESC
        LIMIT 10
    """), {"nip": nip}).mappings().all()

    return {
        "nip": nip,
        "profile": dict(profile) if profile else None,
        "cpv_breakdown": [dict(r) for r in cpv_breakdown],
        "region_breakdown": [dict(r) for r in region_breakdown],
        "recent_wins": [dict(r) for r in recent_wins],
    }
