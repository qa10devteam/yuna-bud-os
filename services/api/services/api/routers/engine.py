"""M4/M5 — /tenders/{id}/engine/run, /tenders/{id}/engine, /tenders/{id}/rules/check,
           /tenders/{id}/risk (L2 Monte Carlo)."""
from __future__ import annotations

import json
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from services.engine.l1_symbolic import run_l1, Violation
from services.engine.l2_stochastic import run_l2, RiskInput, DEFAULT_RISK_FACTORS

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


class WinProbSchema(BaseModel):
    price_pln: float
    win_prob: float
    margin_p50: float


class DriverSchema(BaseModel):
    factor: str
    S1: float
    ST: float


class RiskSchema(BaseModel):
    margin_p10: float
    margin_p50: float
    margin_p90: float
    win_prob_at_price: list[WinProbSchema]
    drivers: list[DriverSchema]
    n_samples_used: int
    n_rejected: int


class EngineResultSchema(BaseModel):
    feasible: bool
    violations: list[ViolationSchema]
    risk: RiskSchema | None = None
    explanation_md: str


class RuleCheckResponse(BaseModel):
    violations: list[ViolationSchema]


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/engine/run  (L1 + L2)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/engine/run", response_model=EngineResultSchema)
def run_engine(tender_id: str, seed: int = 42, n_samples: int = 2000) -> EngineResultSchema:
    """Run L1 symbolic + L2 stochastic engine for a tender.

    Loads tender, analysis (key_facts + przedmiar_items) and latest estimate.
    Stores violations in discrepancy table; stores risk in risk_run table.
    """
    engine = get_engine()

    tender_dict, przedmiar_items, key_facts, estimate_dict = _load_tender_data(engine, tender_id)

    # --- L1 ---
    l1_result = run_l1(
        tender=tender_dict,
        przedmiar_items=przedmiar_items,
        estimate=estimate_dict,
        analysis={"key_facts": key_facts},
    )
    _store_discrepancies(engine, tender_id, l1_result.violations)

    # --- L2 ---
    risk_result = None
    risk_schema = None
    owner_cost = float(estimate_dict.get("total_net_pln") or 0) if estimate_dict else 0
    market_price = float(tender_dict.get("value_pln") or 0)

    if owner_cost > 0:
        ri = RiskInput(
            owner_cost=owner_cost,
            market_price=market_price or owner_cost * 1.2,
            risk_factors=DEFAULT_RISK_FACTORS,
            seed=seed,
            n_samples=n_samples,
        )
        risk_result = run_l2(ri)
        _store_risk_run(engine, tender_id, estimate_dict, risk_result)

        risk_schema = RiskSchema(
            margin_p10=risk_result.margin_p10,
            margin_p50=risk_result.margin_p50,
            margin_p90=risk_result.margin_p90,
            win_prob_at_price=[
                WinProbSchema(**p.to_dict()) for p in risk_result.win_prob_at_price
            ],
            drivers=[DriverSchema(**d.to_dict()) for d in risk_result.drivers],
            n_samples_used=risk_result.n_samples_used,
            n_rejected=risk_result.n_rejected,
        )

    return EngineResultSchema(
        feasible=l1_result.feasible,
        violations=[
            ViolationSchema(
                axiom_code=v.axiom_code,
                axiom_id=v.axiom_id,
                severity=v.severity,
                message=v.message,
                provenance=v.provenance,
            )
            for v in l1_result.violations
        ],
        risk=risk_schema,
        explanation_md=l1_result.explanation_md,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /tenders/{id}/engine
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/tenders/{tender_id}/engine", response_model=EngineResultSchema)
def get_engine_result(tender_id: str) -> EngineResultSchema:
    """Return stored engine result (discrepancies + latest risk_run)."""
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")

        disc_rows = conn.execute(
            sa.text(
                "SELECT kind, severity, message, provenance, axiom_id "
                "FROM discrepancy WHERE tender_id = :tid ORDER BY created_at DESC LIMIT 50"
            ),
            {"tid": tender_id},
        ).fetchall()

        # Latest risk_run
        rr = conn.execute(
            sa.text(
                "SELECT margin_p10, margin_p50, margin_p90, win_prob_at_price, drivers, samples "
                "FROM risk_run WHERE tender_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()

    violations = [
        ViolationSchema(
            axiom_code=r[0], axiom_id=str(r[4]) if r[4] else None,
            severity=r[1], message=r[2], provenance=r[3] or {},
        )
        for r in disc_rows
    ]
    block_count = sum(1 for v in violations if v.severity == "block")

    risk_schema = None
    if rr:
        risk_schema = RiskSchema(
            margin_p10=float(rr[0] or 0),
            margin_p50=float(rr[1] or 0),
            margin_p90=float(rr[2] or 0),
            win_prob_at_price=[WinProbSchema(**p) for p in (rr[3] or [])],
            drivers=[DriverSchema(**d) for d in (rr[4] or [])],
            n_samples_used=int(rr[5] or 0),
            n_rejected=0,
        )

    return EngineResultSchema(
        feasible=block_count == 0,
        violations=violations,
        risk=risk_schema,
        explanation_md="",
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/risk  (L2 only, parametric)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/risk", response_model=RiskSchema)
def run_risk(tender_id: str, seed: int = 42, n_samples: int = 2000) -> RiskSchema:
    """Run L2 stochastic risk analysis standalone (does not re-run L1)."""
    engine = get_engine()
    tender_dict, _, _, estimate_dict = _load_tender_data(engine, tender_id)

    owner_cost = float(estimate_dict.get("total_net_pln") or 0) if estimate_dict else 0
    market_price = float(tender_dict.get("value_pln") or 0)
    if owner_cost <= 0:
        raise HTTPException(status_code=422, detail="No estimate found — run POST /estimate first")

    ri = RiskInput(
        owner_cost=owner_cost,
        market_price=market_price or owner_cost * 1.2,
        risk_factors=DEFAULT_RISK_FACTORS,
        seed=seed,
        n_samples=n_samples,
    )
    result = run_l2(ri)
    _store_risk_run(engine, tender_id, estimate_dict, result)

    return RiskSchema(
        margin_p10=result.margin_p10,
        margin_p50=result.margin_p50,
        margin_p90=result.margin_p90,
        win_prob_at_price=[WinProbSchema(**p.to_dict()) for p in result.win_prob_at_price],
        drivers=[DriverSchema(**d.to_dict()) for d in result.drivers],
        n_samples_used=result.n_samples_used,
        n_rejected=result.n_rejected,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/rules/check
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/rules/check", response_model=RuleCheckResponse)
def rules_check(tender_id: str) -> RuleCheckResponse:
    """Run documentary/regulatory axiom check — live, not persisted."""
    engine = get_engine()
    tender_dict, przedmiar_items, key_facts, estimate_dict = _load_tender_data(engine, tender_id)

    result = run_l1(
        tender=tender_dict,
        przedmiar_items=przedmiar_items,
        estimate=estimate_dict,
        analysis={"key_facts": key_facts},
        axiom_codes=["A004", "A005", "A006"],
    )
    return RuleCheckResponse(
        violations=[
            ViolationSchema(
                axiom_code=v.axiom_code, axiom_id=v.axiom_id,
                severity=v.severity, message=v.message, provenance=v.provenance,
            )
            for v in result.violations
        ]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_tender_data(
    engine: Any, tender_id: str
) -> tuple[dict, list[dict], dict, dict | None]:
    """Load tender, analysis, estimate from DB. Raises 404 if tender missing."""
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, value_pln FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")
        tender_dict: dict[str, Any] = {"value_pln": float(row[1] or 0) if row[1] else 0}

        arow = conn.execute(
            sa.text(
                "SELECT przedmiar_items, key_facts FROM analysis "
                "WHERE tender_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()
        przedmiar_items: list[dict] = arow[0] if arow else []
        key_facts: dict = arow[1] if arow else {}

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
            estimate_dict = {"total_net_pln": float(erow[1]), "lines": erow[2] or []}

    return tender_dict, przedmiar_items, key_facts, estimate_dict


def _store_discrepancies(engine: Any, tender_id: str, violations: list[Violation]) -> None:
    """Persist violations to discrepancy table (replaces existing)."""
    with engine.begin() as conn:
        row = conn.execute(
            sa.text("SELECT tenant_id FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone()
        if not row:
            return
        tenant_id = str(row[0])
        conn.execute(sa.text("DELETE FROM discrepancy WHERE tender_id = :tid"), {"tid": tender_id})
        for v in violations:
            conn.execute(
                sa.text(
                    "INSERT INTO discrepancy "
                    "(id, tenant_id, tender_id, kind, severity, message, provenance, axiom_id, created_at) "
                    "VALUES (:id, :tid, :tender, :kind, cast(:sev as flag_severity), "
                    ":msg, cast(:prov as jsonb), :axiom_id, now())"
                ),
                {
                    "id": str(uuid.uuid4()), "tid": tenant_id, "tender": tender_id,
                    "kind": v.axiom_code, "sev": v.severity, "msg": v.message,
                    "prov": json.dumps(v.provenance, ensure_ascii=False),
                    "axiom_id": v.axiom_id,
                },
            )


def _store_risk_run(
    engine: Any, tender_id: str, estimate_dict: dict | None, result: Any
) -> None:
    """Persist risk_run to DB."""
    from services.engine.l2_stochastic import RiskResult
    if not isinstance(result, RiskResult):
        return
    with engine.begin() as conn:
        row = conn.execute(
            sa.text("SELECT tenant_id FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone()
        if not row:
            return
        tenant_id = str(row[0])

        # Get estimate_id if available
        est_id = None
        if estimate_dict:
            erow = conn.execute(
                sa.text("SELECT id FROM estimate WHERE tender_id = :tid AND variant = 'doc' LIMIT 1"),
                {"tid": tender_id},
            ).fetchone()
            if erow:
                est_id = str(erow[0])

        conn.execute(
            sa.text(
                "INSERT INTO risk_run "
                "(id, tenant_id, tender_id, estimate_id, samples, "
                " margin_p10, margin_p50, margin_p90, win_prob_at_price, drivers, created_at) "
                "VALUES (:id, :tid, :tender, :est_id, :samples, "
                " :p10, :p50, :p90, cast(:wpp as jsonb), cast(:drivers as jsonb), now())"
            ),
            {
                "id": str(uuid.uuid4()), "tid": tenant_id, "tender": tender_id,
                "est_id": est_id, "samples": result.n_samples_used,
                "p10": result.margin_p10, "p50": result.margin_p50, "p90": result.margin_p90,
                "wpp": json.dumps([p.to_dict() for p in result.win_prob_at_price]),
                "drivers": json.dumps([d.to_dict() for d in result.drivers]),
            },
        )
