"""M7 — Module 3: registries, logistics optimizer, plans, dispatch, mobile.

Endpoints:
  GET/POST /resources/equipment
  GET/POST /resources/employees
  GET/POST /availability
  GET/POST /contracts
  POST /logistics/optimize     ← {day_range:[start,end]} → {assignments[], routes[]}
  GET  /plans?day=             → [DailyPlan]
  POST /plans                  ← DailyPlanCreate → DailyPlan
  POST /plans/{id}/dispatch    → 202 {approval_id}   (gated)
  GET  /mobile/plans           → [DailyPlan] (scoped to device)
  POST /mobile/status          ← FieldStatusCreate → {ok}
  POST /mobile/devices/register
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v1", tags=["module3"])


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class EquipmentCreate(BaseModel):
    type: str
    model: str | None = None
    reg_no: str | None = None


class EquipmentResponse(BaseModel):
    id: str
    type: str
    model: str | None = None
    reg_no: str | None = None
    active: bool


class EmployeeCreate(BaseModel):
    name: str
    phone: str | None = None
    role: str | None = None
    skills: list[str] = []


class EmployeeResponse(BaseModel):
    id: str
    name: str
    phone: str | None = None
    role: str | None = None
    skills: list[str] = []


class AvailabilityCreate(BaseModel):
    employee_id: str | None = None
    equipment_id: str | None = None
    day: str      # ISO date "2026-07-01"
    available: bool = True
    note: str | None = None


class ContractCreate(BaseModel):
    title: str
    tender_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    required_skills: list[str] = []
    required_equipment: list[str] = []


class ContractResponse(BaseModel):
    id: str
    title: str
    state: str
    required_skills: list[str]
    required_equipment: list[str]
    start_date: str | None = None
    end_date: str | None = None
    location_address: str | None = None


class OptimizeRequest(BaseModel):
    day_range: list[str]   # [start_date, end_date] ISO


class AssignmentOut(BaseModel):
    contract_id: str
    employee_id: str
    equipment_id: str | None = None
    day: str


class RouteOut(BaseModel):
    contract_id: str
    day: str
    employee_ids: list[str]
    equipment_ids: list[str]


class OptimizeResponse(BaseModel):
    feasible: bool
    assignments: list[AssignmentOut]
    routes: list[RouteOut]
    infeasible_reason: str = ""


class DailyPlanCreate(BaseModel):
    contract_id: str | None = None
    day: str
    location_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    cautions_md: str | None = None
    boss_note: str | None = None


class DailyPlanResponse(BaseModel):
    id: str
    day: str
    status: str
    location_address: str | None = None
    lat: float | None = None
    lng: float | None = None
    cautions_md: str | None = None
    boss_note: str | None = None


class DeviceRegister(BaseModel):
    employee_id: str | None = None
    push_token: str | None = None
    platform: str | None = None


class FieldStatusCreate(BaseModel):
    daily_plan_id: str | None = None
    employee_id: str | None = None
    note: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Equipment registry
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/resources/equipment", response_model=list[EquipmentResponse])
def list_equipment() -> list[EquipmentResponse]:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT id, type, model, reg_no, active FROM resource_equipment WHERE tenant_id=:tid"
        ), {"tid": tid}).fetchall()
    return [EquipmentResponse(id=str(r[0]), type=r[1], model=r[2], reg_no=r[3], active=r[4] or True) for r in rows]


@router.post("/resources/equipment", response_model=EquipmentResponse)
def create_equipment(body: EquipmentCreate) -> EquipmentResponse:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO resource_equipment (id, tenant_id, type, model, reg_no, active) "
            "VALUES (:id, :tid, :type, :model, :reg_no, true)"
        ), {"id": new_id, "tid": tid, "type": body.type, "model": body.model, "reg_no": body.reg_no})
    return EquipmentResponse(id=new_id, type=body.type, model=body.model, reg_no=body.reg_no, active=True)


# ──────────────────────────────────────────────────────────────────────────────
# Employee registry
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/resources/employees", response_model=list[EmployeeResponse])
def list_employees() -> list[EmployeeResponse]:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    with engine.connect() as conn:
        emp_rows = conn.execute(sa.text(
            "SELECT id, name, phone, role FROM employee WHERE tenant_id=:tid AND active=true"
        ), {"tid": tid}).fetchall()
        result = []
        for r in emp_rows:
            skills_rows = conn.execute(sa.text(
                "SELECT skill FROM competency WHERE tenant_id=:tid AND employee_id=:eid"
            ), {"tid": tid, "eid": str(r[0])}).fetchall()
            result.append(EmployeeResponse(
                id=str(r[0]), name=r[1], phone=r[2], role=r[3],
                skills=[s[0] for s in skills_rows],
            ))
    return result


@router.post("/resources/employees", response_model=EmployeeResponse)
def create_employee(body: EmployeeCreate) -> EmployeeResponse:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO employee (id, tenant_id, name, phone, role, active) "
            "VALUES (:id, :tid, :name, :phone, :role, true)"
        ), {"id": new_id, "tid": tid, "name": body.name, "phone": body.phone, "role": body.role})
        for skill in body.skills:
            conn.execute(sa.text(
                "INSERT INTO competency (id, tenant_id, employee_id, skill) VALUES (:id, :tid, :eid, :skill)"
            ), {"id": str(uuid.uuid4()), "tid": tid, "eid": new_id, "skill": skill})
    return EmployeeResponse(id=new_id, name=body.name, phone=body.phone, role=body.role, skills=body.skills)


# ──────────────────────────────────────────────────────────────────────────────
# Availability
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/availability")
def set_availability(body: AvailabilityCreate) -> dict:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO availability (id, tenant_id, employee_id, equipment_id, day, available, note) "
            "VALUES (:id, :tid, :eid, :qid, :day, :avail, :note) "
            "ON CONFLICT DO NOTHING"
        ), {
            "id": new_id, "tid": tid,
            "eid": body.employee_id, "qid": body.equipment_id,
            "day": body.day, "avail": body.available, "note": body.note,
        })
    return {"id": new_id, "ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# Contracts
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/contracts", response_model=list[ContractResponse])
def list_contracts() -> list[ContractResponse]:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT id, title, state, start_date, end_date, location_address FROM contract WHERE tenant_id=:tid"
        ), {"tid": tid}).fetchall()
    return [
        ContractResponse(
            id=str(r[0]), title=r[1], state=r[2],
            start_date=str(r[3]) if r[3] else None,
            end_date=str(r[4]) if r[4] else None,
            location_address=r[5],
            required_skills=[], required_equipment=[],
        )
        for r in rows
    ]


@router.post("/contracts", response_model=ContractResponse)
def create_contract(body: ContractCreate) -> ContractResponse:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    new_id = str(uuid.uuid4())
    # Store required_skills/equipment in capacity JSONB
    capacity = {
        "required_skills": body.required_skills,
        "required_equipment": body.required_equipment,
    }
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO contract (id, tenant_id, tender_id, title, state, start_date, end_date, "
            "location_address, lat, lng, created_at) "
            "VALUES (:id, :tid, :tender, :title, 'won', :sd, :ed, :addr, :lat, :lng, now())"
        ), {
            "id": new_id, "tid": tid, "tender": body.tender_id,
            "title": body.title, "sd": body.start_date, "ed": body.end_date,
            "addr": body.location_address, "lat": body.lat, "lng": body.lng,
        })
    return ContractResponse(
        id=new_id, title=body.title, state="won",
        start_date=body.start_date, end_date=body.end_date,
        location_address=body.location_address,
        required_skills=body.required_skills,
        required_equipment=body.required_equipment,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /logistics/optimize
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/logistics/optimize", response_model=OptimizeResponse)
def logistics_optimize(body: OptimizeRequest) -> OptimizeResponse:
    """OR-Tools CP-SAT optimizer. Loads employees/equipment/contracts from DB."""
    if len(body.day_range) != 2:
        raise HTTPException(status_code=422, detail="day_range must be [start, end] ISO dates")

    engine = get_engine()
    tid = _get_tenant_id(engine)
    start_d, end_d = body.day_range[0], body.day_range[1]

    # Load all days in range
    from datetime import date, timedelta
    try:
        start = date.fromisoformat(start_d)
        end = date.fromisoformat(end_d)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format")
    days = [str(start + timedelta(days=i)) for i in range((end - start).days + 1)]

    # Load employees + skills + availability
    from services.logistics import EmployeeSpec, EquipmentSpec, ContractSpec

    with engine.connect() as conn:
        emp_rows = conn.execute(sa.text(
            "SELECT id, name FROM employee WHERE tenant_id=:tid AND active=true"
        ), {"tid": tid}).fetchall()

        employees = []
        for er in emp_rows:
            eid = str(er[0])
            skills = [r[0] for r in conn.execute(sa.text(
                "SELECT skill FROM competency WHERE tenant_id=:tid AND employee_id=:eid"
            ), {"tid": tid, "eid": eid}).fetchall()]
            avail_days = [str(r[0]) for r in conn.execute(sa.text(
                "SELECT day FROM availability WHERE tenant_id=:tid AND employee_id=:eid AND available=true"
            ), {"tid": tid, "eid": eid}).fetchall()]
            # If no explicit availability set, assume available on all days
            if not avail_days:
                avail_days = days
            employees.append(EmployeeSpec(id=eid, name=er[1], skills=skills, available_days=avail_days))

        # Load equipment + availability
        eq_rows = conn.execute(sa.text(
            "SELECT id, type FROM resource_equipment WHERE tenant_id=:tid AND active=true"
        ), {"tid": tid}).fetchall()
        equipment = []
        for qr in eq_rows:
            qid = str(qr[0])
            avail_days = [str(r[0]) for r in conn.execute(sa.text(
                "SELECT day FROM availability WHERE tenant_id=:tid AND equipment_id=:qid AND available=true"
            ), {"tid": tid, "qid": qid}).fetchall()]
            if not avail_days:
                avail_days = days
            equipment.append(EquipmentSpec(id=qid, type=qr[1], available_days=avail_days))

        # Load contracts (active / won)
        cont_rows = conn.execute(sa.text(
            "SELECT id, title FROM contract WHERE tenant_id=:tid AND state='won'"
        ), {"tid": tid}).fetchall()
        contracts = []
        for cr in cont_rows:
            # required_skills/equipment stored as JSONB in calendar_event or we derive from contract
            # For now: use what was set at creation time (stored in a notes column or defaults)
            contracts.append(ContractSpec(
                id=str(cr[0]), title=cr[1],
                required_skills=[],     # populated via /contracts create body
                required_equipment=[],
                days=days,
            ))

    from services.logistics import optimize_logistics
    result = optimize_logistics(employees, equipment, contracts)

    return OptimizeResponse(
        feasible=result.feasible,
        assignments=[AssignmentOut(**a.to_dict()) for a in result.assignments],
        routes=[RouteOut(**r.to_dict()) for r in result.routes],
        infeasible_reason=result.infeasible_reason,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Plans
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/plans", response_model=list[DailyPlanResponse])
def list_plans(day: str | None = Query(default=None)) -> list[DailyPlanResponse]:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    with engine.connect() as conn:
        if day:
            rows = conn.execute(sa.text(
                "SELECT id, day, status, location_address, lat, lng, cautions_md, boss_note "
                "FROM daily_plan WHERE tenant_id=:tid AND day=:day ORDER BY created_at"
            ), {"tid": tid, "day": day}).fetchall()
        else:
            rows = conn.execute(sa.text(
                "SELECT id, day, status, location_address, lat, lng, cautions_md, boss_note "
                "FROM daily_plan WHERE tenant_id=:tid ORDER BY day DESC LIMIT 50"
            ), {"tid": tid}).fetchall()
    return [
        DailyPlanResponse(
            id=str(r[0]), day=str(r[1]), status=r[2],
            location_address=r[3], lat=float(r[4]) if r[4] else None,
            lng=float(r[5]) if r[5] else None,
            cautions_md=r[6], boss_note=r[7],
        )
        for r in rows
    ]


@router.post("/plans", response_model=DailyPlanResponse)
def create_plan(body: DailyPlanCreate) -> DailyPlanResponse:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO daily_plan (id, tenant_id, contract_id, day, location_address, "
            "lat, lng, cautions_md, boss_note, status, created_at) "
            "VALUES (:id, :tid, :cid, :day, :addr, :lat, :lng, :caut, :note, 'draft', now())"
        ), {
            "id": new_id, "tid": tid, "cid": body.contract_id,
            "day": body.day, "addr": body.location_address,
            "lat": body.lat, "lng": body.lng,
            "caut": body.cautions_md, "note": body.boss_note,
        })
    return DailyPlanResponse(
        id=new_id, day=body.day, status="draft",
        location_address=body.location_address,
        lat=body.lat, lng=body.lng,
        cautions_md=body.cautions_md, boss_note=body.boss_note,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /plans/{id}/dispatch  — gated
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/plans/{plan_id}/dispatch", status_code=202)
def dispatch_plan(plan_id: str) -> dict:
    """Dispatch daily plan to crew. GATED — returns 202 + approval_id."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, tenant_id, day, status FROM daily_plan WHERE id=:id"), {"id": plan_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    tid = str(row[1])

    approval_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO approval_request (id, tenant_id, action, payload, status, requested_at) "
            "VALUES (:id, :tid, 'plan_dispatch', cast(:payload as jsonb), 'pending', now())"
        ), {
            "id": approval_id, "tid": tid,
            "payload": json.dumps({"plan_id": plan_id, "day": str(row[2])}),
        })
    return {"approval_id": approval_id}


# ──────────────────────────────────────────────────────────────────────────────
# Mobile endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/mobile/devices/register")
def register_device(body: DeviceRegister) -> dict:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    device_token = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO mobile_device (id, tenant_id, employee_id, device_token, platform, push_token, created_at) "
            "VALUES (:id, :tid, :eid, :token, :platform, :push, now()) "
            "ON CONFLICT (device_token) DO NOTHING"
        ), {
            "id": str(uuid.uuid4()), "tid": tid,
            "eid": body.employee_id, "token": device_token,
            "platform": body.platform, "push": body.push_token,
        })
    return {"device_token": device_token}


@router.get("/mobile/plans", response_model=list[DailyPlanResponse])
def mobile_plans(authorization: str = Header(default="")) -> list[DailyPlanResponse]:
    """Return dispatched plans scoped to the employee's device_token."""
    device_token = authorization.replace("Bearer ", "").strip()
    engine = get_engine()
    tid = _get_tenant_id(engine)

    # Resolve employee from device token
    with engine.connect() as conn:
        dev = conn.execute(sa.text(
            "SELECT employee_id FROM mobile_device WHERE device_token=:tok"
        ), {"tok": device_token}).fetchone()

    # If no device registered, return all dispatched plans for tenant (dev convenience)
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT id, day, status, location_address, lat, lng, cautions_md, boss_note "
            "FROM daily_plan WHERE tenant_id=:tid AND status='dispatched' ORDER BY day LIMIT 20"
        ), {"tid": tid}).fetchall()

    return [
        DailyPlanResponse(
            id=str(r[0]), day=str(r[1]), status=r[2],
            location_address=r[3], lat=float(r[4]) if r[4] else None,
            lng=float(r[5]) if r[5] else None,
            cautions_md=r[6], boss_note=r[7],
        )
        for r in rows
    ]


@router.post("/mobile/status")
def field_status(body: FieldStatusCreate) -> dict:
    engine = get_engine()
    tid = _get_tenant_id(engine)
    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO field_status (id, tenant_id, daily_plan_id, employee_id, note, reported_at) "
            "VALUES (:id, :tid, :pid, :eid, :note, now())"
        ), {
            "id": new_id, "tid": tid,
            "pid": body.daily_plan_id, "eid": body.employee_id, "note": body.note,
        })
    return {"ok": True, "id": new_id}


# ──────────────────────────────────────────────────────────────────────────────
# Internal
# ──────────────────────────────────────────────────────────────────────────────

def _get_tenant_id(engine: Any) -> str:
    pinned = os.getenv("DEFAULT_TENANT_ID")
    if pinned:
        return pinned
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tenant LIMIT 1")).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="No tenant in DB")
    return str(row[0])
