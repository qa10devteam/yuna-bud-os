"""Faza 56 — Subkontrahenci: zarządzanie bazą podwykonawców.
Faza 57 — Zasoby sprzętowe: maszyny i sprzęt budowlany.
Faza 58 — Harmonogram Gantt (stub): zadania z datami.
Faza 59 — Kalendarz terminów: events i deadline'y przetargów.
"""
from __future__ import annotations


import uuid
from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

sub_router = APIRouter(prefix="/api/v1/subcontractors", tags=["subcontractors"])
equip_router = APIRouter(prefix="/api/v1/equipment", tags=["equipment"])
gantt_router = APIRouter(prefix="/api/v1/gantt", tags=["gantt"])
calendar_router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])
employees_router = APIRouter(prefix="/api/v1/resources/employees", tags=["employees"])
res_equip_router = APIRouter(prefix="/api/v1/resources/equipment", tags=["resources-equipment"])
logistics_router = APIRouter(prefix="/api/v1/logistics", tags=["logistics"])
contracts_router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 56: Subkontrahenci
# ═══════════════════════════════════════════════════════════════════════════════

class SubcontractorCreate(BaseModel):
    name: str
    nip: str | None = None
    specialization: list[str] = []
    contact_email: str | None = None
    contact_phone: str | None = None
    rating: float | None = None
    notes: str | None = None


class TenderSubcontractorLink(BaseModel):
    subcontractor_id: str
    role: str | None = None
    value_pln: float | None = None


@sub_router.get("")
def list_subcontractors(
    user: AuthUser,
    active: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    engine = get_engine()
    filters = ["org_id = :org_id"]
    params: dict = {"limit": limit, "offset": offset, "org_id": user.org_id}
    if active is not None:
        filters.append("active = :active")
        params["active"] = active
    where = "WHERE " + " AND ".join(filters)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f"""
                SELECT id, name, nip, specialization, contact_email, contact_phone, rating, active, created_at
                FROM subcontractors {where}
                ORDER BY name LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()
        total = conn.execute(sa.text(f"SELECT COUNT(*) FROM subcontractors {where}"), params).scalar()
    return {
        "total": int(total or 0),
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "nip": r.nip,
                "specialization": list(r.specialization) if r.specialization else [],
                "contact_email": r.contact_email,
                "contact_phone": r.contact_phone,
                "rating": float(r.rating) if r.rating else None,
                "active": r.active,
            }
            for r in rows
        ],
    }


@sub_router.post("")
def create_subcontractor(sub: SubcontractorCreate, user: AuthUser) -> dict:
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO subcontractors (id, org_id, name, nip, specialization, contact_email, contact_phone, rating, notes)
                VALUES (:id, :org_id, :name, :nip, :spec, :email, :phone, :rating, :notes)
            """),
            {
                "id": rec_id,
                "org_id": user.org_id or None,
                "name": sub.name,
                "nip": sub.nip,
                "spec": sub.specialization,
                "email": sub.contact_email,
                "phone": sub.contact_phone,
                "rating": sub.rating,
                "notes": sub.notes,
            },
        )
        conn.commit()
    return {"id": rec_id, "status": "created"}


@sub_router.get("/{sub_id}")
def get_subcontractor(sub_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT * FROM subcontractors WHERE id = :id AND org_id = :org"), {"id": sub_id, "org": user.org_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Nie znaleziono lub brak dostępu")
    return {
        "id": str(row.id),
        "name": row.name,
        "nip": row.nip,
        "specialization": list(row.specialization) if row.specialization else [],
        "contact_email": row.contact_email,
        "contact_phone": row.contact_phone,
        "rating": float(row.rating) if row.rating else None,
        "active": row.active,
        "notes": row.notes,
    }


@sub_router.delete("/{sub_id}")
def delete_subcontractor(sub_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM subcontractors WHERE id = :id AND org_id = :org"), {"id": sub_id, "org": user.org_id})
        conn.commit()
    return {"status": "deleted"}


@sub_router.get("/tender/{tender_id}")
def tender_subcontractors(tender_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT ts.id, s.name, s.nip, s.contact_email, ts.role, ts.value_pln
                FROM tender_subcontractors ts
                JOIN subcontractors s ON s.id = ts.subcontractor_id
                WHERE ts.tender_id = :tid
            """),
            {"tid": tender_id},
        ).fetchall()
    return {
        "tender_id": tender_id,
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "nip": r.nip,
                "contact_email": r.contact_email,
                "role": r.role,
                "value_pln": float(r.value_pln) if r.value_pln else None,
            }
            for r in rows
        ],
    }


@sub_router.post("/tender/{tender_id}")
def link_subcontractor(tender_id: str, link: TenderSubcontractorLink, user: AuthUser) -> dict:
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO tender_subcontractors (id, tender_id, subcontractor_id, role, value_pln)
                VALUES (:id, :tender_id, :sub_id, :role, :value)
                ON CONFLICT (tender_id, subcontractor_id) DO UPDATE SET role=EXCLUDED.role, value_pln=EXCLUDED.value_pln
            """),
            {
                "id": rec_id,
                "tender_id": tender_id,
                "sub_id": link.subcontractor_id,
                "role": link.role,
                "value": link.value_pln,
            },
        )
        conn.commit()
    return {"status": "linked", "tender_id": tender_id}


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 57: Zasoby sprzętowe
# ═══════════════════════════════════════════════════════════════════════════════

class EquipmentCreate(BaseModel):
    name: str
    category: str = "maszyna"
    model: str | None = None
    serial_no: str | None = None
    owned: bool = True
    daily_cost: float | None = None
    status: str = "available"
    notes: str | None = None


@equip_router.get("")
def list_equipment(
    user: AuthUser,
    status: str | None = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
) -> dict:
    engine = get_engine()
    filters = []
    params: dict = {"limit": limit, "offset": offset}
    if status:
        filters.append("status = :status")
        params["status"] = status
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f"""
                SELECT id, name, category, model, serial_no, owned, daily_cost, status, created_at
                FROM equipment {where}
                ORDER BY name LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()
        total = conn.execute(sa.text(f"SELECT COUNT(*) FROM equipment {where}"), params).scalar()
    return {
        "total": int(total or 0),
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category,
                "model": r.model,
                "serial_no": r.serial_no,
                "owned": r.owned,
                "daily_cost": float(r.daily_cost) if r.daily_cost else None,
                "status": r.status,
            }
            for r in rows
        ],
    }


@equip_router.post("")
def create_equipment(eq: EquipmentCreate, user: AuthUser) -> dict:
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO equipment (id, org_id, name, category, model, serial_no, owned, daily_cost, status, notes)
                VALUES (:id, :org_id, :name, :cat, :model, :serial, :owned, :cost, :status, :notes)
            """),
            {
                "id": rec_id,
                "org_id": user.org_id or None,
                "name": eq.name,
                "cat": eq.category,
                "model": eq.model,
                "serial": eq.serial_no,
                "owned": eq.owned,
                "cost": eq.daily_cost,
                "status": eq.status,
                "notes": eq.notes,
            },
        )
        conn.commit()
    return {"id": rec_id, "status": "created"}


@equip_router.delete("/{eq_id}")
def delete_equipment(eq_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM equipment WHERE id = :id AND org_id = :org"), {"id": eq_id, "org": user.org_id})
        conn.commit()
    return {"status": "deleted"}


@equip_router.get("/tender/{tender_id}")
def tender_equipment(tender_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT te.id, e.name, e.category, e.daily_cost, te.start_date, te.end_date, te.days
                FROM tender_equipment te
                JOIN equipment e ON e.id = te.equipment_id
                WHERE te.tender_id = :tid
            """),
            {"tid": tender_id},
        ).fetchall()
    return {
        "tender_id": tender_id,
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category,
                "daily_cost": float(r.daily_cost) if r.daily_cost else None,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "days": r.days,
                "total_cost": float(r.daily_cost or 0) * (r.days or 0),
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 58: Harmonogram Gantt (stub)
# ═══════════════════════════════════════════════════════════════════════════════

class GanttTaskCreate(BaseModel):
    name: str
    start_date: date | None = None
    end_date: date | None = None
    progress: int = 0
    color: str = "#3b82f6"
    parent_id: str | None = None
    position: int = 0


@gantt_router.get("/{tender_id}")
def get_gantt(tender_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, parent_id, name, start_date, end_date, progress, color, position
                FROM gantt_tasks WHERE tender_id = :tid ORDER BY position ASC, created_at ASC
            """),
            {"tid": tender_id},
        ).fetchall()
    return {
        "tender_id": tender_id,
        "tasks": [
            {
                "id": str(r.id),
                "parent_id": str(r.parent_id) if r.parent_id else None,
                "name": r.name,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "progress": r.progress,
                "color": r.color,
                "position": r.position,
            }
            for r in rows
        ],
    }


@gantt_router.post("/{tender_id}")
def create_gantt_task(tender_id: str, task: GanttTaskCreate, user: AuthUser) -> dict:
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO gantt_tasks (id, tender_id, parent_id, name, start_date, end_date, progress, color, position)
                VALUES (:id, :tid, :parent, :name, :start, :end, :progress, :color, :pos)
            """),
            {
                "id": rec_id,
                "tid": tender_id,
                "parent": task.parent_id,
                "name": task.name,
                "start": task.start_date,
                "end": task.end_date,
                "progress": task.progress,
                "color": task.color,
                "pos": task.position,
            },
        )
        conn.commit()
    return {"id": rec_id, "status": "created"}


@gantt_router.patch("/{tender_id}/{task_id}")
def update_gantt_task(
    tender_id: str,
    task_id: str,
    task: GanttTaskCreate,
    user: AuthUser,
) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                UPDATE gantt_tasks SET name=:name, start_date=:start, end_date=:end,
                    progress=:progress, color=:color, position=:pos
                WHERE id=:id AND tender_id=:tid
            """),
            {
                "name": task.name,
                "start": task.start_date,
                "end": task.end_date,
                "progress": task.progress,
                "color": task.color,
                "pos": task.position,
                "id": task_id,
                "tid": tender_id,
            },
        )
        conn.commit()
    return {"id": task_id, "status": "updated"}


@gantt_router.delete("/{tender_id}/{task_id}")
def delete_gantt_task(tender_id: str, task_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM gantt_tasks WHERE id=:id AND tender_id=:tid"), {"id": task_id, "tid": tender_id})
        conn.commit()
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# Faza 59: Kalendarz terminów
# ═══════════════════════════════════════════════════════════════════════════════

class CalendarEventCreate(BaseModel):
    title: str
    event_type: str = "deadline"
    event_date: date
    tender_id: str | None = None
    notify_days_before: int = 3


@calendar_router.get("")
def list_calendar_events(
    user: AuthUser,
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    limit: int = Query(100),
) -> dict:
    engine = get_engine()
    filters = []
    params: dict = {"limit": limit}
    if from_date:
        filters.append("event_date >= :from_date::date")
        params["from_date"] = from_date
    if to_date:
        filters.append("event_date <= :to_date::date")
        params["to_date"] = to_date
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f"""
                SELECT ce.id, ce.title, ce.event_type, ce.event_date,
                       ce.tender_id, t.title AS tender_title, ce.notify_days_before, ce.notified
                FROM calendar_events ce
                LEFT JOIN tender t ON t.id = ce.tender_id
                {where}
                ORDER BY ce.event_date ASC
                LIMIT :limit
            """),
            params,
        ).fetchall()
    return {
        "events": [
            {
                "id": str(r.id),
                "title": r.title,
                "event_type": r.event_type,
                "event_date": r.event_date.isoformat() if r.event_date else None,
                "tender_id": str(r.tender_id) if r.tender_id else None,
                "tender_title": r.tender_title,
                "notify_days_before": r.notify_days_before,
                "notified": r.notified,
            }
            for r in rows
        ]
    }


@calendar_router.post("")
def create_calendar_event(event: CalendarEventCreate, user: AuthUser) -> dict:
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO calendar_events (id, org_id, tender_id, title, event_type, event_date, notify_days_before)
                VALUES (:id, :org_id, :tender_id, :title, :type, :date, :notify)
            """),
            {
                "id": rec_id,
                "org_id": user.org_id or None,
                "tender_id": event.tender_id,
                "title": event.title,
                "type": event.event_type,
                "date": event.event_date,
                "notify": event.notify_days_before,
            },
        )
        conn.commit()
    return {"id": rec_id, "status": "created"}


@calendar_router.delete("/{event_id}")
def delete_calendar_event(event_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM calendar_events WHERE id=:id AND org_id=:org"), {"id": event_id, "org": user.org_id})
        conn.commit()
    return {"status": "deleted"}


@calendar_router.post("/sync-from-tenders")
def sync_calendar_from_tenders(user: AuthUser) -> dict:
    """Synchronizuj deadline'y przetargów z kalendarzem."""
    engine = get_engine()
    added = 0
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT t.id, t.title, t.deadline_at
                FROM tender t
                WHERE t.deadline_at IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM calendar_events ce WHERE ce.tender_id = t.id AND ce.event_type = 'deadline'
                  )
                LIMIT 200
            """)
        ).fetchall()

        for row in rows:
            conn.execute(
                sa.text("""
                    INSERT INTO calendar_events (id, org_id, tender_id, title, event_type, event_date)
                    VALUES (:id, :org_id, :tid, :title, 'deadline', :date)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "org_id": user.org_id or None,
                    "tid": str(row.id),
                    "title": f"Termin składania: {row.title[:80]}",
                    "date": row.deadline_at.date() if row.deadline_at else None,
                },
            )
            added += 1
        conn.commit()

    return {"synced": added, "message": f"Dodano {added} terminów do kalendarza"}


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOYEES (Pracownicy)
# ═══════════════════════════════════════════════════════════════════════════════

class EmployeeCreate(BaseModel):
    name: str
    role: str = "pracownik"
    phone: str | None = None
    hourly_rate: float | None = None


@employees_router.get("")
def list_employees(user: AuthUser) -> dict:
    """Lista pracowników firmy."""
    org_id = user.org_id or "default"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT * FROM employees WHERE org_id = :org ORDER BY name"),
            {"org": org_id},
        ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@employees_router.post("", status_code=201)
def create_employee(body: EmployeeCreate, user: AuthUser) -> dict:
    """Dodaj pracownika."""
    org_id = user.org_id or "default"
    emp_id = str(uuid.uuid4())
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO employees (id, org_id, name, role, phone, hourly_rate)
                VALUES (:id, :org, :name, :role, :phone, :rate)
            """),
            {"id": emp_id, "org": org_id, "name": body.name,
             "role": body.role, "phone": body.phone, "rate": body.hourly_rate},
        )
    return {"id": emp_id, "name": body.name, "role": body.role}


@employees_router.delete("/{emp_id}", status_code=204)
def delete_employee(emp_id: str, user: AuthUser) -> None:
    """Usuń pracownika."""
    org_id = user.org_id or "default"
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text("DELETE FROM employees WHERE id = :id AND org_id = :org"),
            {"id": emp_id, "org": org_id},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES/EQUIPMENT (alias proxy to /api/v1/equipment logic)
# ═══════════════════════════════════════════════════════════════════════════════

@res_equip_router.get("")
def list_res_equipment(user: AuthUser, limit: int = Query(100)) -> dict:
    """Lista sprzętu (alias /api/v1/resources/equipment → equipment table)."""
    org_id = user.org_id or "default"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT * FROM equipment WHERE org_id = :org ORDER BY name LIMIT :lim"),
            {"org": org_id, "lim": limit},
        ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@res_equip_router.post("", status_code=201)
def create_res_equipment(body: EquipmentCreate, user: AuthUser) -> dict:
    """Dodaj sprzęt (via /api/v1/resources/equipment)."""
    org_id = user.org_id or "default"
    eq_id = str(uuid.uuid4())
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO equipment (id, org_id, name, category, status, daily_cost)
                VALUES (:id, :org, :name, :cat, :st, :cost)
            """),
            {"id": eq_id, "org": org_id, "name": body.name,
             "cat": body.category, "st": body.status or "available", "cost": body.daily_cost},
        )
    return {"id": eq_id, "name": body.name}


# ═══════════════════════════════════════════════════════════════════════════════
# LOGISTICS OPTIMIZE (Optymalizacja tras)
# ═══════════════════════════════════════════════════════════════════════════════

class OptimizeRequest(BaseModel):
    sites: list[dict] = []
    depot: dict | None = None
    max_distance_km: float = 200


@logistics_router.post("/optimize")
def optimize_routes(body: OptimizeRequest, user: AuthUser) -> dict:
    """Optymalizacja tras — prosty greedy nearest-neighbor."""
    if not body.sites:
        return {"routes": [], "total_km": 0, "message": "Brak lokalizacji do optymalizacji"}

    # Simple nearest-neighbor heuristic
    sites = body.sites[:]
    route = []
    current = body.depot or {"lat": 52.23, "lng": 21.01}  # Default: Warsaw
    total_km = 0.0

    while sites:
        # Find nearest
        nearest_idx = 0
        nearest_dist = float("inf")
        for i, s in enumerate(sites):
            dlat = abs(s.get("lat", 52) - current.get("lat", 52))
            dlng = abs(s.get("lng", 21) - current.get("lng", 21))
            dist = (dlat**2 + dlng**2) ** 0.5 * 111  # rough km
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = i
        site = sites.pop(nearest_idx)
        route.append({**site, "distance_km": round(nearest_dist, 1)})
        total_km += nearest_dist
        current = site

    return {
        "routes": [{"stops": route, "total_km": round(total_km, 1)}],
        "total_km": round(total_km, 1),
        "vehicles_needed": max(1, len(route) // 8),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACTS (Kontrakty/umowy)
# ═══════════════════════════════════════════════════════════════════════════════

@contracts_router.get("")
def list_contracts(user: AuthUser) -> dict:
    """Lista kontraktów z przetargów (status=won lub signed)."""
    org_id = user.org_id or "default"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT t.id, t.title, t.buyer, t.value_pln, t.status, t.updated_at
                FROM tender t
                WHERE t.org_id = :org AND t.status IN ('won', 'signed', 'contract', 'realized')
                ORDER BY t.updated_at DESC
                LIMIT 50
            """),
            {"org": org_id},
        ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


# ═══════════════════════════════════════════════════════════════════════════════
# S78/S79/S80 — Resources availability + collision check (v2)
# ═══════════════════════════════════════════════════════════════════════════════

res_v2_router = APIRouter(prefix="/api/v2/resources", tags=["resources-v2"])


class CollisionCheckRequest(BaseModel):
    resource_id: str
    from_date: str
    to_date: str


@res_v2_router.get("/availability")
def get_resource_availability(
    from_date: str = Query(..., description="Format: YYYY-MM-DD"),
    to_date: str = Query(..., description="Format: YYYY-MM-DD"),
    user: AuthUser = None,
) -> dict:
    """S78 — Dostępność zasobów w przedziale dat (tabela availability)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """SELECT id, employee_id, equipment_id, day, available, note
                   FROM availability
                   WHERE tenant_id = :tid
                     AND day >= :from_date::date
                     AND day <= :to_date::date
                   ORDER BY day"""
            ),
            {
                "tid": str(user.org_id) if user else "",
                "from_date": from_date,
                "to_date": to_date,
            },
        ).mappings().fetchall()
    return {
        "from_date": from_date,
        "to_date": to_date,
        "items": [dict(r) for r in rows],
        "total": len(rows),
    }


@res_v2_router.post("/check-collision")
def check_resource_collision(body: CollisionCheckRequest, user: AuthUser = None) -> dict:
    """S79/S80 — Sprawdź kolizję zasobu w przedziale dat."""
    engine = get_engine()
    with engine.connect() as conn:
        count = conn.execute(
            sa.text(
                """SELECT count(*) FROM availability
                   WHERE (employee_id = :rid OR equipment_id = :rid)
                     AND available = false
                     AND day >= :from_date::date
                     AND day <= :to_date::date"""
            ),
            {
                "rid": body.resource_id,
                "from_date": body.from_date,
                "to_date": body.to_date,
            },
        ).scalar() or 0
    return {
        "resource_id": body.resource_id,
        "from_date": body.from_date,
        "to_date": body.to_date,
        "collision": count > 0,
        "conflict_days": count,
    }
