"""Faza 3 — Tender Alerts API.

Endpoints:
  GET    /api/v2/alerts              — lista alertów org (items/total)
  POST   /api/v2/alerts              — utwórz alert
  GET    /api/v2/alerts/{id}         — szczegóły alertu
  PUT    /api/v2/alerts/{id}         — aktualizuj alert (partial)
  DELETE /api/v2/alerts/{id}         — usuń alert
  PATCH  /api/v2/alerts/{id}/toggle  — włącz/wyłącz alert
  POST   /api/v2/alerts/{id}/test    — testuj alert (matching przetargi + stats)
  GET    /api/v2/alerts/{id}/matches — ostatnie dopasowania (z paginacją)

Tabela: tender_alert (RLS via tenant_id = org_id)
Security: wszystkie filtry parametryzowane, whitelist dla enum pól.
"""
from __future__ import annotations

import logging
import re as _re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.deps import AuthUser
from terra_db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/alerts", tags=["tender-alerts"])


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


# ─── Whitelist validators ─────────────────────────────────────────────────────

_CPV_RE  = _re.compile(r'^[0-9]{1,9}$')
_PROV_RE = _re.compile(r'^PL[0-9A-Z]{2,3}$')
_NIP_RE  = _re.compile(r'^[0-9]{8,12}$')
_NT_ALLOWED = frozenset([
    "ogloszenieOZamowieniu", "ogloszenieOWyniku", "ogloszenieOUdzieleniu",
    "zapytanieOCene", "zamowienieZWolnejReki", "inne",
])
_FREQ_ALLOWED = frozenset(["instant", "daily", "weekly"])
_CHANNEL_ALLOWED = frozenset(["email", "push", "webhook"])


# ─── Schematy Pydantic ────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    cpv_prefixes: list[str] = Field(default_factory=list)
    provinces: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    value_min: float | None = Field(None, ge=0)
    value_max: float | None = Field(None, ge=0)
    notice_types: list[str] = Field(default_factory=list)
    buyer_nips: list[str] = Field(default_factory=list)
    is_active: bool = True
    frequency: str = "daily"
    channel: str = "email"
    webhook_url: str | None = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v not in _FREQ_ALLOWED:
            raise ValueError(f"frequency musi być jednym z: {sorted(_FREQ_ALLOWED)}")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if v not in _CHANNEL_ALLOWED:
            raise ValueError(f"channel musi być jednym z: {sorted(_CHANNEL_ALLOWED)}")
        return v

    @model_validator(mode="after")
    def validate_webhook(self) -> "AlertCreate":
        if self.channel == "webhook" and not self.webhook_url:
            raise ValueError("webhook_url wymagany gdy channel='webhook'")
        if self.value_max and self.value_min and self.value_max < self.value_min:
            raise ValueError("value_max musi być >= value_min")
        return self


class AlertUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    cpv_prefixes: list[str] | None = None
    provinces: list[str] | None = None
    keywords: list[str] | None = None
    value_min: float | None = Field(None, ge=0)
    value_max: float | None = Field(None, ge=0)
    notice_types: list[str] | None = None
    buyer_nips: list[str] | None = None
    is_active: bool | None = None
    frequency: str | None = None
    channel: str | None = None
    webhook_url: str | None = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str | None) -> str | None:
        if v is not None and v not in _FREQ_ALLOWED:
            raise ValueError(f"frequency musi być jednym z: {sorted(_FREQ_ALLOWED)}")
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str | None) -> str | None:
        if v is not None and v not in _CHANNEL_ALLOWED:
            raise ValueError(f"channel musi być jednym z: {sorted(_CHANNEL_ALLOWED)}")
        return v


# ─── Helper: generuje sparametryzowane SQL ────────────────────────────────────

def _alert_matches_sql(alert: dict, limit: int = 20) -> tuple[str, dict]:
    """Generuje sparametryzowane SQL + params dla przetargów pasujących do alertu.

    NIGDY nie wstrzykuje danych użytkownika jako SQL literals.
    Whitelist regex blokuje injection dla CPV/NIP/prowincji.
    Keywords idą przez ILIKE z parametrami (nie format string).
    """
    conditions: list[str] = [
        "ht.date >= (SELECT max(date) - INTERVAL '365 days' FROM historical_tenders)"
    ]
    params: dict = {}

    # CPV prefixes — tylko cyfry
    if alert.get("cpv_prefixes"):
        safe_pfx = [p for p in alert["cpv_prefixes"][:10] if _CPV_RE.match(str(p))]
        if safe_pfx:
            parts = []
            for i, p in enumerate(safe_pfx):
                k = f"cpv_{i}"
                params[k] = f"{p}%"
                parts.append(f"ht.cpv_code LIKE :{k}")
            conditions.append(f"({' OR '.join(parts)})")

    # Provinces — format PLxx
    if alert.get("provinces"):
        safe = [p for p in alert["provinces"][:20] if _PROV_RE.match(str(p))]
        if safe:
            for i, p in enumerate(safe):
                params[f"prov_{i}"] = p
            ph = ",".join([f":prov_{i}" for i in range(len(safe))])
            conditions.append(f"ht.province IN ({ph})")

    # Values — float, safe
    if alert.get("value_min") is not None:
        params["value_min"] = float(alert["value_min"])
        conditions.append("ht.estimated_value >= :value_min")
    if alert.get("value_max") is not None:
        params["value_max"] = float(alert["value_max"])
        conditions.append("ht.estimated_value <= :value_max")

    # Notice types — whitelist
    if alert.get("notice_types"):
        safe = [t for t in alert["notice_types"][:10] if t in _NT_ALLOWED]
        if safe:
            for i, t in enumerate(safe):
                params[f"nt_{i}"] = t
            ph = ",".join([f":nt_{i}" for i in range(len(safe))])
            conditions.append(f"ht.notice_type IN ({ph})")

    # Buyer NIPs
    if alert.get("buyer_nips"):
        safe = [n for n in alert["buyer_nips"][:20] if _NIP_RE.match(str(n))]
        if safe:
            for i, n in enumerate(safe):
                params[f"bnip_{i}"] = n
            ph = ",".join([f":bnip_{i}" for i in range(len(safe))])
            conditions.append(f"ht.buyer_nip IN ({ph})")

    # Keywords — ILIKE parametryzowane (nie format string)
    if alert.get("keywords"):
        parts = []
        for i, kw in enumerate(alert["keywords"][:10]):
            k = f"kw_{i}"
            safe_kw = str(kw).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params[k] = f"%{safe_kw}%"
            parts.append(f"ht.title ILIKE :{k}")
        if parts:
            conditions.append(f"({' OR '.join(parts)})")

    params["_limit"] = limit
    where = " AND ".join(conditions)
    sql = f"""
        SELECT ht.id, ht.title, ht.buyer, ht.buyer_nip, ht.province, ht.cpv_code,
               ht.estimated_value, ht.date, ht.notice_type, ht.offers_count,
               ht.procedure_result
        FROM historical_tenders ht
        WHERE {where}
        ORDER BY ht.date DESC
        LIMIT :_limit
    """
    return sql, params


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", summary="Lista alertów organizacji")
def list_alerts(
    user: AuthUser,
    db: DB,
    active_only: bool = Query(False, description="Tylko aktywne"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    org_id = _require_org(user)
    params: dict = {"org_id": org_id, "limit": limit, "offset": offset}
    extra = " AND is_active = true" if active_only else ""

    rows = db.execute(text(f"""
        SELECT id, name, cpv_prefixes, provinces, keywords,
               value_min, value_max, notice_types, buyer_nips,
               is_active, frequency, channel, webhook_url,
               last_fired_at, total_fired, created_at, updated_at
        FROM tender_alert
        WHERE tenant_id = :org_id{extra}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(
        f"SELECT count(*) FROM tender_alert WHERE tenant_id = :org_id{extra}"
    ), {"org_id": org_id}).scalar()

    return {"items": [dict(r) for r in rows], "total": total, "offset": offset, "limit": limit}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Utwórz alert")
def create_alert(body: AlertCreate, user: AuthUser, db: DB):
    org_id = _require_org(user)

    # Duplicate name check (UNIQUE idx_alert_tenant_name_unique)
    dup = db.execute(text(
        "SELECT id FROM tender_alert WHERE tenant_id = :org_id AND name = :name"
    ), {"org_id": org_id, "name": body.name}).one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail="Alert o tej nazwie już istnieje")

    row = db.execute(text("""
        INSERT INTO tender_alert (
            tenant_id, user_id, name, cpv_prefixes, provinces, keywords,
            value_min, value_max, notice_types, buyer_nips,
            is_active, frequency, channel, webhook_url
        ) VALUES (
            :org_id, :user_id, :name, :cpv_prefixes, :provinces, :keywords,
            :value_min, :value_max, :notice_types, :buyer_nips,
            :is_active, :frequency, :channel, :webhook_url
        )
        RETURNING id, name, is_active, frequency, channel,
                  total_fired, last_fired_at, created_at
    """), {
        "org_id": org_id,
        "user_id": user.user_id,
        "name": body.name,
        "cpv_prefixes": body.cpv_prefixes,
        "provinces": body.provinces,
        "keywords": body.keywords,
        "value_min": body.value_min,
        "value_max": body.value_max,
        "notice_types": body.notice_types,
        "buyer_nips": body.buyer_nips,
        "is_active": body.is_active,
        "frequency": body.frequency,
        "channel": body.channel,
        "webhook_url": body.webhook_url,
    }).mappings().one()
    db.commit()
    return dict(row)


@router.get("/{alert_id}", summary="Szczegóły alertu")
def get_alert(alert_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    row = db.execute(text("""
        SELECT * FROM tender_alert
        WHERE id = :id AND tenant_id = :org_id
    """), {"id": str(alert_id), "org_id": org_id}).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert nie istnieje")
    return dict(row)


@router.put("/{alert_id}", summary="Aktualizuj alert")
def update_alert(alert_id: UUID, body: AlertUpdate, user: AuthUser, db: DB):
    org_id = _require_org(user)

    existing = db.execute(text(
        "SELECT id FROM tender_alert WHERE id = :id AND tenant_id = :org_id"
    ), {"id": str(alert_id), "org_id": org_id}).one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Alert nie istnieje")

    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Brak pól do aktualizacji")

    # Sprawdź unikalność nazwy jeśli zmieniana
    if "name" in updates:
        dup = db.execute(text(
            "SELECT id FROM tender_alert WHERE tenant_id = :org_id AND name = :name AND id != :id"
        ), {"org_id": org_id, "name": updates["name"], "id": str(alert_id)}).one_or_none()
        if dup:
            raise HTTPException(status_code=409, detail="Alert o tej nazwie już istnieje")

    set_parts = ", ".join([f"{k} = :{k}" for k in updates])
    updates["id"] = str(alert_id)
    db.execute(text(f"UPDATE tender_alert SET {set_parts} WHERE id = :id"), updates)
    db.commit()
    return {"status": "ok", "id": str(alert_id), "updated_fields": list(updates.keys())}


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń alert")
def delete_alert(alert_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    result = db.execute(text("""
        DELETE FROM tender_alert WHERE id = :id AND tenant_id = :org_id
    """), {"id": str(alert_id), "org_id": org_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert nie istnieje")


@router.patch("/{alert_id}/toggle", summary="Włącz / wyłącz alert")
def toggle_alert(alert_id: UUID, user: AuthUser, db: DB):
    org_id = _require_org(user)
    row = db.execute(text("""
        UPDATE tender_alert
        SET is_active = NOT is_active
        WHERE id = :id AND tenant_id = :org_id
        RETURNING id, is_active
    """), {"id": str(alert_id), "org_id": org_id}).mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert nie istnieje")
    db.commit()
    return {"id": str(alert_id), "is_active": row["is_active"]}


@router.post("/{alert_id}/test", summary="Testuj alert — zwróć matching przetargi + statystyki")
def test_alert(
    alert_id: UUID,
    user: AuthUser,
    db: DB,
    limit: int = Query(20, le=100),
):
    org_id = _require_org(user)
    alert = db.execute(text("""
        SELECT * FROM tender_alert WHERE id = :id AND tenant_id = :org_id
    """), {"id": str(alert_id), "org_id": org_id}).mappings().one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert nie istnieje")

    alert_dict = dict(alert)
    sql, params = _alert_matches_sql(alert_dict, limit=limit)
    try:
        rows = db.execute(text(sql), params).mappings().all()
        matches = [dict(r) for r in rows]

        # Statystyki dopasowania
        total_value = sum(
            float(m["estimated_value"]) for m in matches
            if m.get("estimated_value") is not None
        )
        avg_value = round(total_value / len(matches)) if matches else None

        return {
            "alert_id": str(alert_id),
            "alert_name": alert_dict["name"],
            "matches": matches,
            "total": len(matches),
            "stats": {
                "avg_estimated_value": avg_value,
                "total_value": round(total_value) if total_value else None,
            },
        }
    except Exception as e:
        logger.error("Alert test error alert_id=%s: %s", alert_id, e)
        raise HTTPException(status_code=500, detail=f"Błąd wykonania zapytania: {e}")


@router.get("/{alert_id}/matches", summary="Ostatnie dopasowania alertu (historia)")
def alert_matches(
    alert_id: UUID,
    user: AuthUser,
    db: DB,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """Zwraca aktualne dopasowania alertu z paginacją."""
    org_id = _require_org(user)
    alert = db.execute(text("""
        SELECT * FROM tender_alert WHERE id = :id AND tenant_id = :org_id
    """), {"id": str(alert_id), "org_id": org_id}).mappings().one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert nie istnieje")

    alert_dict = dict(alert)
    sql, params = _alert_matches_sql(alert_dict, limit=limit)
    # Dodaj OFFSET do wygenerowanego zapytania
    sql_with_offset = sql.rstrip().rstrip(";") + f" OFFSET :_offset"
    params["_offset"] = offset
    params["_limit"] = limit

    try:
        rows = db.execute(text(sql_with_offset), params).mappings().all()
        return {
            "alert_id": str(alert_id),
            "alert_name": alert_dict["name"],
            "items": [dict(r) for r in rows],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        logger.error("Alert matches error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
