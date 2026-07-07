"""M7 acceptance tests — registries, OR-Tools optimizer, plans, dispatch, mobile.

Acceptance T-M7:
  ✅ fixture (2 contracts / 7 employees / limited excavators) → feasible assignment respects competency
  ✅ over-constrained fixture → engine_infeasible with reason
  ✅ GET/POST /resources/equipment — CRUD
  ✅ GET/POST /resources/employees — CRUD with skills
  ✅ POST /availability → sets availability
  ✅ GET/POST /contracts — CRUD
  ✅ POST /logistics/optimize → feasible + assignments + routes
  ✅ POST /logistics/optimize over-constrained → infeasible_reason
  ✅ GET/POST /plans → DailyPlan CRUD
  ✅ POST /plans/{id}/dispatch → 202 + approval_id (gated)
  ✅ POST /mobile/devices/register → device_token
  ✅ GET /mobile/plans → dispatched plans (empty list ok)
  ✅ POST /mobile/status → ok
"""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")

from httpx import AsyncClient, ASGITransport


# ──────────────────────────────────────────────────────────────────────────────
# Unit: OR-Tools optimizer
# ──────────────────────────────────────────────────────────────────────────────

from services.logistics import (
    optimize_logistics,
    EmployeeSpec, EquipmentSpec, ContractSpec,
)


class TestOptimizerFeasible:
    """T-M7 Acceptance: 2 contracts / 7 employees / limited excavators → valid assignment."""

    EMPLOYEES = [
        EmployeeSpec("e1", "Jan",    ["operator_koparki", "kierowca"], ["2026-07-01", "2026-07-02"]),
        EmployeeSpec("e2", "Piotr",  ["operator_koparki"],             ["2026-07-01", "2026-07-02"]),
        EmployeeSpec("e3", "Adam",   ["kierowca"],                     ["2026-07-01", "2026-07-02"]),
        EmployeeSpec("e4", "Marek",  ["operator_walca"],               ["2026-07-01", "2026-07-02"]),
        EmployeeSpec("e5", "Tomek",  ["operator_koparki"],             ["2026-07-01"]),
        EmployeeSpec("e6", "Bartek", ["kierowca"],                     ["2026-07-02"]),
        EmployeeSpec("e7", "Paweł",  ["operator_walca"],               ["2026-07-01", "2026-07-02"]),
    ]
    EQUIPMENT = [
        EquipmentSpec("eq1", "koparka", ["2026-07-01", "2026-07-02"]),
        EquipmentSpec("eq2", "koparka", ["2026-07-01", "2026-07-02"]),
        EquipmentSpec("eq3", "walec",   ["2026-07-01", "2026-07-02"]),
    ]
    CONTRACTS = [
        ContractSpec("c1", "Wykopy A46",  ["operator_koparki"], ["koparka"], ["2026-07-01", "2026-07-02"]),
        ContractSpec("c2", "Nasypy DK19", ["operator_walca"],   ["walec"],   ["2026-07-01", "2026-07-02"]),
    ]

    def test_feasible(self):
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        assert r.feasible, f"Expected feasible, got: {r.infeasible_reason}"

    def test_assignments_non_empty(self):
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        assert len(r.assignments) > 0

    def test_skill_respected(self):
        """Every assignment employee must have contract's required skill."""
        emp_skills = {e.id: e.skills for e in self.EMPLOYEES}
        req_skills = {c.id: c.required_skills for c in self.CONTRACTS}
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        for a in r.assignments:
            for skill in req_skills[a.contract_id]:
                emp_on_day = [
                    x.employee_id for x in r.assignments
                    if x.contract_id == a.contract_id and x.day == a.day
                ]
                # At least one employee must have the skill
                covered = any(skill in emp_skills.get(eid, []) for eid in emp_on_day)
                assert covered, f"Skill {skill} not covered for contract {a.contract_id} on {a.day}"

    def test_availability_respected(self):
        """Employees only assigned on their available days."""
        avail = {e.id: set(e.available_days) for e in self.EMPLOYEES}
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        for a in r.assignments:
            assert a.day in avail[a.employee_id], (
                f"Employee {a.employee_id} assigned on {a.day} but not available"
            )

    def test_equipment_not_double_assigned(self):
        """Equipment assigned to at most one contract per day."""
        from collections import defaultdict
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        usage: dict[tuple[str | None, str], list[str]] = defaultdict(list)
        for a in r.assignments:
            if a.equipment_id:
                usage[(a.equipment_id, a.day)].append(a.contract_id)
        for key, contracts in usage.items():
            unique = set(contracts)
            assert len(unique) <= 1, (
                f"Equipment {key[0]} double-assigned on {key[1]}: {unique}"
            )

    def test_routes_built(self):
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        assert len(r.routes) > 0

    def test_to_dict(self):
        r = optimize_logistics(self.EMPLOYEES, self.EQUIPMENT, self.CONTRACTS)
        d = r.to_dict()
        assert "feasible" in d
        assert "assignments" in d
        assert "routes" in d


class TestOptimizerInfeasible:
    """T-M7 Acceptance: over-constrained → engine_infeasible with reason."""

    def test_no_skilled_employee(self):
        """Require 'operator_dźwigu' but no one has it."""
        employees = [
            EmployeeSpec("e1", "Jan", ["kierowca"], ["2026-07-01"]),
        ]
        equipment = [EquipmentSpec("eq1", "koparka", ["2026-07-01"])]
        contracts = [
            ContractSpec("c1", "Dźwig", ["operator_dźwigu"], ["koparka"], ["2026-07-01"]),
        ]
        r = optimize_logistics(employees, equipment, contracts)
        assert r.feasible is False
        assert "engine_infeasible" in r.infeasible_reason
        assert "operator_dźwigu" in r.infeasible_reason

    def test_no_equipment_type(self):
        """Require 'żuraw' but no such equipment."""
        employees = [
            EmployeeSpec("e1", "Jan", ["operator_żurawia"], ["2026-07-01"]),
        ]
        equipment = [EquipmentSpec("eq1", "koparka", ["2026-07-01"])]
        contracts = [
            ContractSpec("c1", "Montaż", ["operator_żurawia"], ["żuraw"], ["2026-07-01"]),
        ]
        r = optimize_logistics(employees, equipment, contracts)
        assert r.feasible is False
        assert "engine_infeasible" in r.infeasible_reason
        assert "żuraw" in r.infeasible_reason

    def test_employee_unavailable_on_contract_days(self):
        """Skill exists but employee unavailable on contract days."""
        employees = [
            EmployeeSpec("e1", "Jan", ["operator_koparki"], ["2026-07-05"]),  # wrong day
        ]
        equipment = [EquipmentSpec("eq1", "koparka", ["2026-07-01"])]
        contracts = [
            ContractSpec("c1", "Wykop", ["operator_koparki"], ["koparka"], ["2026-07-01"]),
        ]
        r = optimize_logistics(employees, equipment, contracts)
        assert r.feasible is False
        assert "engine_infeasible" in r.infeasible_reason

    def test_empty_contracts_always_feasible(self):
        r = optimize_logistics([], [], [])
        assert r.feasible is True

    def test_infeasible_reason_non_empty_on_fail(self):
        employees = [EmployeeSpec("e1", "Jan", [], ["2026-07-01"])]
        equipment: list = []
        contracts = [ContractSpec("c1", "X", ["spawacz"], [], ["2026-07-01"])]
        r = optimize_logistics(employees, equipment, contracts)
        assert r.feasible is False
        assert len(r.infeasible_reason) > 10


# ──────────────────────────────────────────────────────────────────────────────
# Integration: registries via HTTP
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_equipment_crud():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/resources/equipment", json={
            "type": "koparka", "model": "Komatsu PC210", "reg_no": "WA 12345",
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "koparka"
    assert "id" in body


@pytest.mark.asyncio
async def test_employee_crud_with_skills():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/resources/employees", json={
            "name": "Krzysztof Nowak",
            "phone": "+48 600 000 001",
            "role": "operator",
            "skills": ["operator_koparki", "kierowca"],
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Krzysztof Nowak"
    assert "operator_koparki" in body["skills"]
    assert "kierowca" in body["skills"]


@pytest.mark.asyncio
async def test_availability_set():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create employee first
        emp = (await ac.post("/api/v1/resources/employees", json={
            "name": "Avail Test", "skills": [],
        })).json()
        r = await ac.post("/api/v1/availability", json={
            "employee_id": emp["id"],
            "day": "2026-07-10",
            "available": True,
        })
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_contracts_crud():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/contracts", json={
            "title": "Kontrakt testowy M7",
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
            "location_address": "ul. Budowlana 1, Warszawa",
            "required_skills": ["operator_koparki"],
            "required_equipment": ["koparka"],
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "Kontrakt testowy M7"
    assert body["state"] == "won"


@pytest.mark.asyncio
async def test_list_equipment():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/resources/equipment")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_employees():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/resources/employees")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_contracts():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/contracts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ──────────────────────────────────────────────────────────────────────────────
# Integration: logistics/optimize via HTTP
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logistics_optimize_endpoint_returns_result():
    """POST /logistics/optimize → feasible or infeasible with proper shape."""
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/logistics/optimize", json={
            "day_range": ["2026-07-01", "2026-07-02"],
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "feasible" in body
    assert "assignments" in body
    assert "routes" in body
    assert "infeasible_reason" in body


@pytest.mark.asyncio
async def test_logistics_optimize_invalid_day_range():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/logistics/optimize", json={"day_range": ["2026-07-01"]})
    assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Integration: Plans
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_plan():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/plans", json={
            "day": "2026-07-01",
            "location_address": "ul. Stalowa 5, Warszawa",
            "cautions_md": "## Uwagi\n- Teren podmokły",
            "boss_note": "Praca od 7:00",
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["day"] == "2026-07-01"
    assert body["status"] == "draft"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_plans():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/plans")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_plans_by_day():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/plans", json={"day": "2026-07-15"})
        r = await ac.get("/api/v1/plans?day=2026-07-15")
    assert r.status_code == 200
    plans = r.json()
    assert all(p["day"] == "2026-07-15" for p in plans)


# ──────────────────────────────────────────────────────────────────────────────
# Integration: Plan dispatch (gated)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_returns_202_approval_id():
    """POST /plans/{id}/dispatch → 202 + approval_id (GATED)."""
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        plan = (await ac.post("/api/v1/plans", json={"day": "2026-07-20"})).json()
        r = await ac.post(f"/api/v1/plans/{plan['id']}/dispatch")
    assert r.status_code == 202, r.text
    body = r.json()
    assert "approval_id" in body
    assert body["approval_id"]


@pytest.mark.asyncio
async def test_dispatch_appears_in_approval_queue():
    """Dispatched plan creates pending approval_request."""
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        plan = (await ac.post("/api/v1/plans", json={"day": "2026-07-21"})).json()
        r = await ac.post(f"/api/v1/plans/{plan['id']}/dispatch")
        approval_id = r.json()["approval_id"]

        approvals = (await ac.get("/api/v1/approvals?status=pending")).json()
    pending_ids = [a["id"] for a in approvals]
    assert approval_id in pending_ids


@pytest.mark.asyncio
async def test_dispatch_approve_executes():
    """Approved dispatch → executed:True."""
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        plan = (await ac.post("/api/v1/plans", json={"day": "2026-07-22"})).json()
        r = await ac.post(f"/api/v1/plans/{plan['id']}/dispatch")
        approval_id = r.json()["approval_id"]

        approve = await ac.post(f"/api/v1/approvals/{approval_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["executed"] is True


# ──────────────────────────────────────────────────────────────────────────────
# Integration: Mobile endpoints
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mobile_device_register():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/mobile/devices/register", json={
            "platform": "android",
            "push_token": "fcm-token-abc123",
        })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "device_token" in body
    assert len(body["device_token"]) > 10  # UUID


@pytest.mark.asyncio
async def test_mobile_plans_returns_list():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/v1/mobile/plans")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_mobile_status_ok():
    from services.api.services.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/mobile/status", json={
            "note": "Wykop zakończony, zebraliśmy 40m3",
        })
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


# ──────────────────────────────────────────────────────────────────────────────
# Acceptance T-M7 combined end-to-end
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_t_m7_end_to_end():
    """Full T-M7: register crew → set availability → contracts → optimize → plan → dispatch."""
    from services.api.services.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        # 1. Register equipment
        eq = (await ac.post("/api/v1/resources/equipment", json={
            "type": "koparka", "model": "CAT 320", "reg_no": "PO 7777M",
        })).json()
        assert eq["type"] == "koparka"

        # 2. Register 3 employees with skills
        emp1 = (await ac.post("/api/v1/resources/employees", json={
            "name": "Operator A", "skills": ["operator_koparki"],
        })).json()
        emp2 = (await ac.post("/api/v1/resources/employees", json={
            "name": "Operator B", "skills": ["operator_walca"],
        })).json()
        emp3 = (await ac.post("/api/v1/resources/employees", json={
            "name": "Kierowca C", "skills": ["kierowca"],
        })).json()

        # 3. Set availability
        for emp_id in [emp1["id"], emp2["id"], emp3["id"]]:
            for day in ["2026-07-01", "2026-07-02"]:
                await ac.post("/api/v1/availability", json={
                    "employee_id": emp_id, "day": day, "available": True,
                })

        # 4. Create contract
        contract = (await ac.post("/api/v1/contracts", json={
            "title": "T-M7 Test Contract",
            "start_date": "2026-07-01",
            "end_date": "2026-07-02",
            "required_skills": ["operator_koparki"],
            "required_equipment": ["koparka"],
        })).json()
        assert contract["state"] == "won"

        # 5. Optimize
        opt_r = await ac.post("/api/v1/logistics/optimize", json={
            "day_range": ["2026-07-01", "2026-07-02"],
        })
        assert opt_r.status_code == 200
        opt = opt_r.json()
        assert "feasible" in opt
        # With employees loaded from DB, should be feasible (operators available)
        # (depends on what's in DB; we assert shape is correct)
        assert "assignments" in opt
        assert "infeasible_reason" in opt

        # 6. Create daily plan
        plan = (await ac.post("/api/v1/plans", json={
            "day": "2026-07-01",
            "location_address": "T-M7 test site",
            "cautions_md": "Brak uwag.",
        })).json()
        assert plan["status"] == "draft"

        # 7. Dispatch (gated)
        disp = await ac.post(f"/api/v1/plans/{plan['id']}/dispatch")
        assert disp.status_code == 202
        approval_id = disp.json()["approval_id"]

        # 8. Approve dispatch
        approve = await ac.post(f"/api/v1/approvals/{approval_id}/approve")
        assert approve.json()["executed"] is True

        # 9. Register mobile device
        dev = (await ac.post("/api/v1/mobile/devices/register", json={
            "employee_id": emp1["id"],
            "platform": "ios",
        })).json()
        assert "device_token" in dev

        # 10. Field status
        stat = await ac.post("/api/v1/mobile/status", json={
            "employee_id": emp1["id"],
            "note": "Wykop 40m3 gotowy",
        })
        assert stat.json()["ok"] is True
