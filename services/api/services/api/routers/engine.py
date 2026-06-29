"""M4 — /tenders/{id}/engine/run, /tenders/{id}/engine, /tenders/{id}/rules/check."""
from __future__ import annotations

import json
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from services.engine.l1_symbolic import run_l1, EngineResult, Violation

router = APIRouter(prefix="/api/v1", tags=["engine"])


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ViolationSchema(BaseModel):
    axiom_code: str
    axiom_id: str | None = None
    severity: str
    message: str
    provenance: dict


class EngineResultSchema(BaseModel):
    feasible: bool
    violations: list[ViolationSchema]
    explanation_md: str


class RuleCheckResponse(BaseModel):
    violations: list[ViolationSchema]


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/engine/run
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/engine/run", response_model=EngineResultSchema)
def run_engine(tender_id: str) -> EngineResultSchema:
    """Run L1 symbolic engine for a tender.

    Loads tender, analysis (key_facts + przedmiar_items) and latest estimate
    from DB, then runs the engine. Stores violations in discrepancy table.
    """
    engine = get_engine()

    # --- Load tender ---
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, value_pln FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tender not found")

    tender_dict: dict[str, Any] = {
        "value_pln": float(row[1] or 0) if row[1] else 0,
    }

    # --- Load analysis ---
    with engine.connect() as conn:
        arow = conn.execute(
            sa.text(
                "SELECT przedmiar_items, key_facts FROM analysis "
                "WHERE tender_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()

    przedmiar_items: list[dict] = []
    key_facts: dict = {}
    if arow:
        przedmiar_items = arow[0] or []
        key_facts = arow[1] or {}

    # --- Load latest doc-variant estimate ---
    with engine.connect() as conn:
        erow = conn.execute(
            sa.text(
                "SELECT e.id, e.total_net_pln, "
                "  (SELECT json_agg(json_build_object("
                "      'line_total_pln', el.line_total_pln, "
                "      'unit_price', el.unit_price, "
                "      'description', el.description, "
                "      'unit', el.unit, "
                "      'quantity', el.quantity"
                "  )) FROM estimate_line el WHERE el.estimate_id = e.id) as lines "
                "FROM estimate e "
                "WHERE e.tender_id = :tid AND e.variant = 'doc' "
                "ORDER BY e.created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()

    estimate_dict: dict[str, Any] | None = None
    if erow and erow[1]:
        estimate_dict = {
            "total_net_pln": float(erow[1]),
            "lines": erow[2] or [],
        }

    # --- Run engine ---
    result = run_l1(
        tender=tender_dict,
        przedmiar_items=przedmiar_items,
        estimate=estimate_dict,
        analysis={"key_facts": key_facts},
    )

    # --- Persist discrepancies ---
    _store_discrepancies(engine, tender_id, result.violations)

    return EngineResultSchema(
        feasible=result.feasible,
        violations=[
            ViolationSchema(
                axiom_code=v.axiom_code,
                axiom_id=v.axiom_id,
                severity=v.severity,
                message=v.message,
                provenance=v.provenance,
            )
            for v in result.violations
        ],
        explanation_md=result.explanation_md,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /tenders/{id}/engine
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/tenders/{tender_id}/engine", response_model=EngineResultSchema)
def get_engine_result(tender_id: str) -> EngineResultSchema:
    """Return stored engine result (latest discrepancies) for a tender."""
    engine = get_engine()

    with engine.connect() as conn:
        # Verify tender exists
        row = conn.execute(
            sa.text("SELECT id FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")

        rows = conn.execute(
            sa.text(
                "SELECT kind, severity, message, provenance, axiom_id "
                "FROM discrepancy WHERE tender_id = :tid "
                "ORDER BY created_at DESC LIMIT 50"
            ),
            {"tid": tender_id},
        ).fetchall()

    if not rows:
        # No violations stored yet — return empty feasible result
        return EngineResultSchema(feasible=True, violations=[], explanation_md="")

    violations = [
        ViolationSchema(
            axiom_code=r[0],
            axiom_id=str(r[4]) if r[4] else None,
            severity=r[1],
            message=r[2],
            provenance=r[3] or {},
        )
        for r in rows
    ]
    block_count = sum(1 for v in violations if v.severity == "block")
    return EngineResultSchema(
        feasible=block_count == 0,
        violations=violations,
        explanation_md="",
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/rules/check
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/rules/check", response_model=RuleCheckResponse)
def rules_check(tender_id: str) -> RuleCheckResponse:
    """Run documentary/regulatory axiom check against current tender state.

    Returns violations without persisting (live check).
    """
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, value_pln FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tender not found")

    tender_dict = {"value_pln": float(row[1] or 0) if row[1] else 0}

    with engine.connect() as conn:
        arow = conn.execute(
            sa.text(
                "SELECT przedmiar_items, key_facts FROM analysis "
                "WHERE tender_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()

    przedmiar_items = arow[0] if arow else []
    key_facts = arow[1] if arow else {}

    # Load latest estimate for sum-reconciliation check
    with engine.connect() as conn:
        erow = conn.execute(
            sa.text(
                "SELECT e.total_net_pln, "
                "  (SELECT json_agg(json_build_object('line_total_pln', el.line_total_pln)) "
                "   FROM estimate_line el WHERE el.estimate_id = e.id) as lines "
                "FROM estimate e WHERE e.tender_id = :tid "
                "ORDER BY e.created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()

    estimate_dict = None
    if erow and erow[0]:
        estimate_dict = {"total_net_pln": float(erow[0]), "lines": erow[1] or []}

    result = run_l1(
        tender=tender_dict,
        przedmiar_items=przedmiar_items,
        estimate=estimate_dict,
        analysis={"key_facts": key_facts},
        axiom_codes=["A004", "A005", "A006"],  # documentary/regulatory subset
    )

    return RuleCheckResponse(
        violations=[
            ViolationSchema(
                axiom_code=v.axiom_code,
                axiom_id=v.axiom_id,
                severity=v.severity,
                message=v.message,
                provenance=v.provenance,
            )
            for v in result.violations
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _store_discrepancies(engine: Any, tender_id: str, violations: list[Violation]) -> None:
    """Persist violations to discrepancy table.

    Replaces all existing discrepancies for this tender (re-run scenario).
    tenant_id resolved from tender row.
    """
    with engine.begin() as conn:
        # Get tenant_id from tender
        row = conn.execute(
            sa.text("SELECT tenant_id FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()
        if not row:
            return
        tenant_id = str(row[0])

        # Delete old discrepancies for this tender
        conn.execute(
            sa.text("DELETE FROM discrepancy WHERE tender_id = :tid"),
            {"tid": tender_id},
        )

        # Insert new
        for v in violations:
            conn.execute(
                sa.text(
                    "INSERT INTO discrepancy "
                    "(id, tenant_id, tender_id, kind, severity, message, provenance, axiom_id, created_at) "
                    "VALUES (:id, :tid, :tender, :kind, cast(:sev as flag_severity), "
                    ":msg, cast(:prov as jsonb), :axiom_id, now())"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tid": tenant_id,
                    "tender": tender_id,
                    "kind": v.axiom_code,
                    "sev": v.severity,
                    "msg": v.message,
                    "prov": json.dumps(v.provenance, ensure_ascii=False),
                    "axiom_id": v.axiom_id,
                },
            )
