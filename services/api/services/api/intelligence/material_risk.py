"""
Material Price Risk Monitor — monitors price changes for ICB materials linked to kosztorysy.
Compares baseline prices (at kosztorys creation) vs. current ICB market prices.
Inserts alerts into material_alert table when threshold exceeded.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

from terra_db.session import get_engine

logger = logging.getLogger(__name__)

# Severity thresholds (absolute % change)
_SEV_LOW = 5.0
_SEV_MEDIUM = 10.0
_SEV_HIGH = 20.0


def _get_severity(change_pct: float) -> str:
    abs_change = abs(change_pct)
    if abs_change < _SEV_LOW:
        return "low"
    elif abs_change < _SEV_MEDIUM:
        return "medium"
    elif abs_change < _SEV_HIGH:
        return "high"
    return "critical"


def check_material_risks(
    kosztorys_id: str,
    tenant_id: str,
    threshold_pct: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Compare baseline ICB prices vs current prices for all pozycje in kosztorys.
    Inserts alerts for items exceeding threshold_pct.

    Returns list of {'icb_id', 'symbol', 'nazwa', 'baseline_price', 'current_price',
                      'change_pct', 'severity', 'alert_created': bool}.
    """
    results: list[dict[str, Any]] = []
    try:
        engine = get_engine()
        with engine.begin() as conn:
            # Get pozycje with ICB material linkage (icb_id_m) and stored baseline price
            rows = conn.execute(sa.text("""
                SELECT p.id::text AS poz_id,
                       p.icb_id_m::text AS icb_id,
                       p.opis AS nazwa,
                       p.m_baseline_price::float AS baseline_price,
                       p.m_jcena::float AS current_m
                FROM kosztorys_pozycja p
                WHERE p.kosztorys_id = :kid
                  AND p.tenant_id = :tid
                  AND p.icb_id_m IS NOT NULL
            """), {"kid": kosztorys_id, "tid": tenant_id}).fetchall()

            if not rows:
                return []

            for row in rows:
                icb_id = row.icb_id
                baseline = row.baseline_price

                # Fetch latest ICB price for this material (typ_rms = 'M')
                latest = conn.execute(sa.text("""
                    SELECT c.cena_netto::float AS price, c.symbol, c.kwartalnr, c.kwartalrok
                    FROM icb_ceny_srednie c
                    WHERE c.id_ceny = :icb_id AND c.typ_rms = 'M'
                    ORDER BY c.kwartalrok DESC, c.kwartalnr DESC
                    LIMIT 1
                """), {"icb_id": icb_id}).fetchone()

                if not latest:
                    continue

                current_price = latest.price
                symbol = latest.symbol or row.nazwa or icb_id

                # If no baseline stored, use current m_jcena as baseline
                if not baseline or baseline == 0:
                    baseline = row.current_m or current_price

                if not baseline or baseline == 0:
                    continue

                change_pct = (current_price - baseline) / baseline * 100.0
                severity = _get_severity(change_pct)
                alert_created = False

                if abs(change_pct) >= threshold_pct:
                    # Insert alert
                    alert_id = str(uuid.uuid4())
                    try:
                        conn.execute(sa.text("""
                            INSERT INTO material_alert
                                (id, tenant_id, kosztorys_id, icb_id, symbol,
                                 baseline_price, current_price, change_pct,
                                 severity, created_at)
                            VALUES
                                (:id, :tenant_id, :kid, :icb_id, :symbol,
                                 :baseline, :current, :change_pct,
                                 :severity, NOW())
                            ON CONFLICT DO NOTHING
                        """), {
                            "id": alert_id,
                            "tenant_id": tenant_id,
                            "kid": kosztorys_id,
                            "icb_id": icb_id,
                            "symbol": symbol,
                            "baseline": baseline,
                            "current": current_price,
                            "change_pct": change_pct,
                            "severity": severity,
                        })
                        alert_created = True
                    except SQLAlchemyError as e:
                        logger.warning("Failed to insert material_alert for icb_id=%s: %s", icb_id, e)

                results.append({
                    "icb_id": icb_id,
                    "symbol": symbol,
                    "nazwa": row.nazwa,
                    "baseline_price": round(baseline, 4),
                    "current_price": round(current_price, 4),
                    "change_pct": round(change_pct, 2),
                    "severity": severity,
                    "alert_created": alert_created,
                })

    except SQLAlchemyError as e:
        logger.error("check_material_risks failed for kosztorys_id=%s: %s", kosztorys_id, e)

    return results


def get_active_alerts(org_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    Fetch unacknowledged material price alerts for an org (tenant).
    Returns list of alert dicts ordered by severity then created_at DESC.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT id::text, tenant_id::text AS org_id, kosztorys_id::text, icb_id, symbol,
                       baseline_price::float, current_price::float, change_pct::float,
                       severity, created_at
                FROM material_alert
                WHERE tenant_id = :org_id
                  AND acknowledged_at IS NULL
                ORDER BY
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'high'     THEN 2
                        WHEN 'medium'   THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT :lim
            """), {"org_id": org_id, "lim": limit}).fetchall()

        return [
            {
                "id": r.id,
                "kosztorys_id": r.kosztorys_id,
                "icb_id": r.icb_id,
                "symbol": r.symbol,
                "baseline_price": r.baseline_price,
                "current_price": r.current_price,
                "change_pct": r.change_pct,
                "severity": r.severity,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except SQLAlchemyError as e:
        logger.error("get_active_alerts failed for org_id=%s: %s", org_id, e)
        return []


def acknowledge_alert(alert_id: str, org_id: str) -> bool:
    """
    Mark a material_alert as acknowledged.
    Returns True if the alert was found and updated, False otherwise.
    """
    try:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(sa.text("""
                UPDATE material_alert
                SET acknowledged_at = NOW()
                WHERE id = :alert_id
                  AND tenant_id = :org_id
                  AND acknowledged_at IS NULL
            """), {"alert_id": alert_id, "org_id": org_id})
            return (result.rowcount or 0) > 0
    except SQLAlchemyError as e:
        logger.error("acknowledge_alert failed for alert_id=%s: %s", alert_id, e)
        return False
