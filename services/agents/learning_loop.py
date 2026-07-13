"""M9 — Learning loop: calibration_coeff update on contract close.

When a contract closes with actual_cost_pln known, we compute:
  new_coeff = actual_cost / estimated_cost   (clipped to [0.5, 2.0])

and upsert calibration_coeff for that tenant+key.

On next estimate, compute_variant_b() will pick up the new coeff.
"""
from __future__ import annotations

import logging
import threading
from decimal import Decimal

import sqlalchemy as sa

logger = logging.getLogger(__name__)


def _ml_retrain_async(engine: object, tenant_id: str) -> None:
    """Launch MLScorer.retrain_from_db() in a daemon background thread."""
    def _run() -> None:
        try:
            from services.ingestion.scorer_ml import get_ml_scorer
            logger.info("source=learning_loop ml_retrain triggered tenant=%s", tenant_id)
            result = get_ml_scorer().retrain_from_db(engine)
            logger.info("source=learning_loop ml_retrain done: %s", result)
        except Exception as exc:  # pragma: no cover
            logger.warning("source=learning_loop ml_retrain error: %s", exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

_COEFF_MIN = Decimal("0.50")
_COEFF_MAX = Decimal("2.00")
_KEY = "estimate_calibration"


def close_contract(
    engine: object,
    contract_id: str,
    actual_cost_pln: Decimal | float,
    tenant_id: str,
) -> dict:
    """Close a contract, compute calibration delta, update calibration_coeff.

    Returns:
        {new_coeff, previous_coeff, delta_pct, contract_id}
    """
    actual = Decimal(str(actual_cost_pln))

    # Fetch estimated cost from estimate (owner variant) for this contract's tender
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT e.total_net_pln FROM estimate e "
            "JOIN contract c ON c.tender_id = e.tender_id "
            "WHERE c.id = :cid AND e.variant = 'owner' LIMIT 1"
        ), {"cid": contract_id}).fetchone()

    estimated = Decimal(str(row[0])) if row and row[0] else None

    # Compute new coeff
    if estimated and estimated > 0:
        raw_coeff = actual / estimated
        new_coeff = max(_COEFF_MIN, min(_COEFF_MAX, raw_coeff))
    else:
        new_coeff = Decimal("1.00")

    # Load previous coeff
    with engine.connect() as conn:
        prev_row = conn.execute(sa.text(
            "SELECT coeff FROM calibration_coeff WHERE tenant_id=:tid AND key=:key ORDER BY version DESC LIMIT 1"
        ), {"tid": tenant_id, "key": _KEY}).fetchone()
    prev_coeff = Decimal(str(prev_row[0])) if prev_row else Decimal("1.00")

    # Upsert: new version
    with engine.begin() as conn:
        # Get current max version
        ver_row = conn.execute(sa.text(
            "SELECT COALESCE(MAX(version), 0) FROM calibration_coeff WHERE tenant_id=:tid AND key=:key"
        ), {"tid": tenant_id, "key": _KEY}).fetchone()
        next_ver = (ver_row[0] or 0) + 1

        conn.execute(sa.text(
            "INSERT INTO calibration_coeff (id, tenant_id, key, coeff, version, updated_at) "
            "VALUES (gen_random_uuid(), :tid, :key, :coeff, :ver, now())"
        ), {"tid": tenant_id, "key": _KEY, "coeff": str(new_coeff), "ver": next_ver})

        # Mark contract closed
        conn.execute(sa.text(
            "UPDATE contract SET state='closed' WHERE id=:cid"
        ), {"cid": contract_id})

        # Audit
        import json
        conn.execute(sa.text(
            "INSERT INTO audit_log (tenant_id, at, actor, action, entity, entity_id, detail) "
            "VALUES (:tid, now(), 'learning_loop', 'contract_close_calibration', "
            "'contract', cast(:eid as uuid), cast(:d as jsonb))"
        ), {
            "tid": tenant_id, "eid": contract_id,
            "d": json.dumps({
                "actual_cost_pln": str(actual),
                "estimated_cost_pln": str(estimated),
                "new_coeff": str(new_coeff),
                "prev_coeff": str(prev_coeff),
                "version": next_ver,
            }),
        })

    delta_pct = float((new_coeff - prev_coeff) / prev_coeff * 100) if prev_coeff else 0.0
    logger.info(
        "calibration updated: contract=%s coeff %s→%s (Δ%.1f%%)",
        contract_id, prev_coeff, new_coeff, delta_pct,
    )

    # Trigger ML retrain in background after calibration update
    _ml_retrain_async(engine, tenant_id)

    return {
        "contract_id": contract_id,
        "previous_coeff": str(prev_coeff),
        "new_coeff": str(new_coeff),
        "delta_pct": round(delta_pct, 2),
        "version": next_ver,
    }
