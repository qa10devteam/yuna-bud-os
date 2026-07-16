"""Faza 4 — API v2: Estimates router."""
from __future__ import annotations

import json
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/estimates", tags=["estimates-v2"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class EstimateCreate(BaseModel):
    tender_id: str
    variant: str = "doc"  # doc | owner
    total_net_pln: float | None = None
    overhead_pct: float | None = None
    profit_pct: float | None = None
    params: dict = {}


class EstimateUpdate(BaseModel):
    total_net_pln: float | None = None
    overhead_pct: float | None = None
    profit_pct: float | None = None
    params: dict | None = None


class EstimateLineUpdate(BaseModel):
    description: str | None = None
    unit: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    labor_pln: float | None = None
    material_pln: float | None = None
    equipment_pln: float | None = None


class PredictRequest(BaseModel):
    cpv: str = "45"
    region: str = "mazowieckie"
    area_m2: float = 1000.0
    floors: int = 1
    description: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: Any) -> dict:
    return {
        "id": str(row.id),
        "tender_id": str(row.tender_id),
        "variant": row.variant,
        "total_net_pln": float(row.total_net_pln) if row.total_net_pln else None,
        "overhead_pct": float(row.overhead_pct) if row.overhead_pct else None,
        "profit_pct": float(row.profit_pct) if row.profit_pct else None,
        "params": row.params if isinstance(row.params, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _require_org(user: AuthUser) -> str:
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail={"error": "no_org", "message": "Brak org_id"},
        )
    return str(tenant_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
def list_estimates(tender_id: str, user: AuthUser) -> dict:
    """Lista wycen dla przetargu."""
    tenant_id = _require_org(user)
    engine = get_engine()

    # Validate tender_id is a valid UUID to avoid DB cast errors
    try:
        uuid.UUID(tender_id)
    except (ValueError, AttributeError):
        return {"items": [], "total": 0}

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """SELECT id, tender_id, variant, total_net_pln, overhead_pct,
                          profit_pct, params, created_at
                   FROM estimate
                   WHERE tenant_id = :tenant_id AND tender_id = :tender_id
                   ORDER BY created_at DESC"""
            ),
            {"tenant_id": tenant_id, "tender_id": tender_id},
        ).fetchall()

    return {"items": [_row_to_dict(r) for r in rows], "total": len(rows)}


@router.post("")
def create_estimate(body: EstimateCreate, user: AuthUser) -> dict:
    """Utwórz wycenę."""
    tenant_id = _require_org(user)
    engine = get_engine()

    if body.variant not in ("doc", "owner"):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_variant", "message": "variant musi być 'doc' lub 'owner'"},
        )

    # Sprawdź czy przetarg należy do tenanta
    with engine.connect() as conn:
        tender = conn.execute(
            sa.text("SELECT id FROM tender WHERE id = :id AND tenant_id = :tid"),
            {"id": body.tender_id, "tid": tenant_id},
        ).fetchone()

    if not tender:
        raise HTTPException(
            status_code=404,
            detail={"error": "tender_not_found", "message": "Przetarg nie znaleziony"},
        )

    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """INSERT INTO estimate
                       (id, tenant_id, tender_id, variant, total_net_pln, overhead_pct, profit_pct, params, created_at)
                   VALUES
                       (:id, :tid, :tender_id, :variant, :total_net_pln, :overhead_pct, :profit_pct,
                        CAST(:params AS jsonb), NOW())
                   RETURNING id, tender_id, variant, total_net_pln, overhead_pct, profit_pct, params, created_at"""
            ),
            {
                "id": new_id,
                "tid": tenant_id,
                "tender_id": body.tender_id,
                "variant": body.variant,
                "total_net_pln": body.total_net_pln,
                "overhead_pct": body.overhead_pct,
                "profit_pct": body.profit_pct,
                "params": json.dumps(body.params),
            },
        ).fetchone()

    return _row_to_dict(result)


@router.get("/predict")
def predict_cost(
    user: AuthUser,  # required — no default so FastAPI always injects via Depends
    cpv: str = "45",
    region: str = "mazowieckie",
    area_m2: float = 1000.0,
    floors: int = 1,
    description: str = "",
) -> dict:
    """Szacuj koszty na podstawie modelu ML/benchmark."""
    from ..analytics.cost_estimation import get_estimator

    estimator = get_estimator()
    pred = estimator.predict({"cpv": cpv, "region": region, "area_m2": area_m2, "floors": floors})

    # pred = EstimateResult.to_dict() → keys: total_net_pln, confidence_low, confidence_high, method, variant, lines
    from ..analytics.cost_estimation import _resolve_cpv_benchmark
    total = pred.get("total_net_pln", 0)
    bm = _resolve_cpv_benchmark(cpv)
    return {
        "benchmark": round(bm["price_per_m2"] * area_m2, 2),
        "ai_estimate": total,
        "confidence_interval": {
            "low95": pred.get("confidence_low", round(total * 0.7, 2)),
            "high95": pred.get("confidence_high", round(total * 1.3, 2)),
        },
        "method": pred.get("method", "benchmark"),
        "variant": pred.get("variant", ""),
        "lines": pred.get("lines", []),
        "notes": pred.get("notes", ""),
        "similar_projects": [],
    }


@router.get("/{estimate_id}")
def get_estimate(estimate_id: str, user: AuthUser) -> dict:
    """Szczegóły wyceny z pozycjami kosztorysu."""
    tenant_id = _require_org(user)
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """SELECT id, tender_id, variant, total_net_pln, overhead_pct,
                          profit_pct, params, created_at
                   FROM estimate
                   WHERE id = :id AND tenant_id = :tenant_id"""
            ),
            {"id": estimate_id, "tenant_id": tenant_id},
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Wycena nie znaleziona"},
            )

        lines = conn.execute(
            sa.text(
                """SELECT id, description, unit, quantity, unit_price,
                          labor_pln, material_pln, equipment_pln, line_total_pln
                   FROM estimate_line
                   WHERE estimate_id = :eid AND tenant_id = :tid
                   ORDER BY created_at"""
            ),
            {"eid": estimate_id, "tid": tenant_id},
        ).fetchall()

    result = _row_to_dict(row)
    result["lines"] = [
        {
            "id": str(ln.id),
            "description": ln.description,
            "unit": ln.unit,
            "quantity": float(ln.quantity) if ln.quantity else None,
            "unit_price": float(ln.unit_price) if ln.unit_price else None,
            "labor_pln": float(ln.labor_pln) if ln.labor_pln else None,
            "material_pln": float(ln.material_pln) if ln.material_pln else None,
            "equipment_pln": float(ln.equipment_pln) if ln.equipment_pln else None,
            "line_total_pln": float(ln.line_total_pln) if ln.line_total_pln else None,
        }
        for ln in lines
    ]
    return result


@router.put("/{estimate_id}")
def update_estimate(estimate_id: str, body: EstimateUpdate, user: AuthUser) -> dict:
    """Aktualizuj wycenę."""
    tenant_id = _require_org(user)
    engine = get_engine()

    updates: list[str] = []
    params: dict[str, Any] = {"id": estimate_id, "tenant_id": tenant_id}

    if body.total_net_pln is not None:
        updates.append("total_net_pln = :total_net_pln")
        params["total_net_pln"] = body.total_net_pln
    if body.overhead_pct is not None:
        updates.append("overhead_pct = :overhead_pct")
        params["overhead_pct"] = body.overhead_pct
    if body.profit_pct is not None:
        updates.append("profit_pct = :profit_pct")
        params["profit_pct"] = body.profit_pct
    if body.params is not None:
        updates.append("params = CAST(:params AS jsonb)")
        params["params"] = json.dumps(body.params)

    if not updates:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_fields", "message": "Brak pól do aktualizacji"},
        )

    set_clause = ", ".join(updates)
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                f"""UPDATE estimate SET {set_clause}
                   WHERE id = :id AND tenant_id = :tenant_id
                   RETURNING id, tender_id, variant, total_net_pln, overhead_pct,
                             profit_pct, params, created_at"""
            ),
            params,
        ).fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Wycena nie znaleziona"},
        )

    return _row_to_dict(result)


@router.patch("/{estimate_id}/lines")
def patch_estimate_lines(
    estimate_id: str,
    lines: list[dict],
    user: AuthUser,
) -> dict:
    """
    Bulk-update or upsert line items for an estimate.

    Each item in ``lines`` must have an ``id`` key (existing line UUID) plus
    any subset of updatable fields.  Missing fields are left unchanged.
    Pass ``"_delete": true`` in a line object to remove that line.

    Returns the full refreshed list of lines.
    """
    tenant_id = _require_org(user)
    engine = get_engine()

    # Verify estimate belongs to tenant
    with engine.connect() as conn:
        est = conn.execute(
            sa.text("SELECT id FROM estimate WHERE id = :id AND tenant_id = :tid"),
            {"id": estimate_id, "tid": tenant_id},
        ).fetchone()
    if not est:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Wycena nie znaleziona"},
        )

    UPDATABLE = {
        "description", "unit", "quantity", "unit_price",
        "labor_pln", "material_pln", "equipment_pln",
    }

    with engine.begin() as conn:
        for line in lines:
            line_id = line.get("id")
            if not line_id:
                # New line — insert
                new_line_id = str(uuid.uuid4())
                conn.execute(
                    sa.text(
                        """INSERT INTO estimate_line
                               (id, estimate_id, tenant_id, description, unit,
                                quantity, unit_price, labor_pln, material_pln, equipment_pln, created_at)
                           VALUES
                               (:id, :eid, :tid, :description, :unit,
                                :quantity, :unit_price, :labor_pln, :material_pln, :equipment_pln, NOW())"""
                    ),
                    {
                        "id": new_line_id,
                        "eid": estimate_id,
                        "tid": tenant_id,
                        "description": line.get("description"),
                        "unit": line.get("unit"),
                        "quantity": line.get("quantity"),
                        "unit_price": line.get("unit_price"),
                        "labor_pln": line.get("labor_pln"),
                        "material_pln": line.get("material_pln"),
                        "equipment_pln": line.get("equipment_pln"),
                    },
                )
                continue

            if line.get("_delete"):
                conn.execute(
                    sa.text(
                        "DELETE FROM estimate_line WHERE id = :id AND estimate_id = :eid AND tenant_id = :tid"
                    ),
                    {"id": line_id, "eid": estimate_id, "tid": tenant_id},
                )
                continue

            field_updates = [f"{f} = :{f}" for f in UPDATABLE if f in line]
            if not field_updates:
                continue

            update_params: dict[str, Any] = {
                "id": line_id,
                "eid": estimate_id,
                "tid": tenant_id,
            }
            update_params.update({f: line[f] for f in UPDATABLE if f in line})

            conn.execute(
                sa.text(
                    f"UPDATE estimate_line SET {', '.join(field_updates)} "
                    "WHERE id = :id AND estimate_id = :eid AND tenant_id = :tid"
                ),
                update_params,
            )

    # Return refreshed lines
    with engine.connect() as conn:
        refreshed = conn.execute(
            sa.text(
                """SELECT id, description, unit, quantity, unit_price,
                          labor_pln, material_pln, equipment_pln, line_total_pln
                   FROM estimate_line
                   WHERE estimate_id = :eid AND tenant_id = :tid
                   ORDER BY created_at"""
            ),
            {"eid": estimate_id, "tid": tenant_id},
        ).fetchall()

    return {
        "estimate_id": estimate_id,
        "lines": [
            {
                "id": str(ln.id),
                "description": ln.description,
                "unit": ln.unit,
                "quantity": float(ln.quantity) if ln.quantity else None,
                "unit_price": float(ln.unit_price) if ln.unit_price else None,
                "labor_pln": float(ln.labor_pln) if ln.labor_pln else None,
                "material_pln": float(ln.material_pln) if ln.material_pln else None,
                "equipment_pln": float(ln.equipment_pln) if ln.equipment_pln else None,
                "line_total_pln": float(ln.line_total_pln) if ln.line_total_pln else None,
            }
            for ln in refreshed
        ],
    }
