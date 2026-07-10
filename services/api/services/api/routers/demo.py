"""Faza 78 — Demo mode router.

Provides seed demo data endpoints for showcasing Terra.OS without real data.
"""
from __future__ import annotations


import os
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

router = APIRouter(prefix="/api/v2/demo", tags=["demo"])

DEMO_ENABLED = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def _check_demo_enabled():
    if not DEMO_ENABLED:
        raise HTTPException(status_code=404, detail="Demo mode disabled")


DEMO_TENDERS = [
    {
        "id": "demo-tender-001",
        "name": "Budowa drogi gminnej w miejscowości Kowale",
        "buyer": "Gmina Kowale",
        "status": "analysis",
        "deadline": "2026-08-15",
        "value_pln": 2_450_000,
        "cpv": ["45233120-6"],
        "risk_score": 0.32,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
    },
    {
        "id": "demo-tender-002",
        "name": "Remont nawierzchni ul. Lipowej w Strzelinie",
        "buyer": "Powiat Strzeliński",
        "status": "estimation",
        "deadline": "2026-07-30",
        "value_pln": 890_000,
        "cpv": ["45233220-7"],
        "risk_score": 0.18,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
    },
    {
        "id": "demo-tender-003",
        "name": "Budowa zbiornika retencyjnego",
        "buyer": "Gmina Piława Górna",
        "status": "decision",
        "deadline": "2026-07-10",
        "value_pln": 3_200_000,
        "cpv": ["45247270-3"],
        "risk_score": 0.61,
        "ai_recommendation": "no_go",
        "region": "dolnośląskie",
    },
    {
        "id": "demo-tender-004",
        "name": "Termomodernizacja budynku szkoły podstawowej",
        "buyer": "Gmina Dzierżoniów",
        "status": "won",
        "deadline": "2026-06-01",
        "value_pln": 1_750_000,
        "cpv": ["45321000-3"],
        "risk_score": 0.24,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
        "won": True,
    },
    {
        "id": "demo-tender-005",
        "name": "Budowa chodnika wzdłuż DW385",
        "buyer": "Zarząd Dróg Województwa Dolnośląskiego",
        "status": "lost",
        "deadline": "2026-05-15",
        "value_pln": 420_000,
        "cpv": ["45233162-2"],
        "risk_score": 0.42,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
        "won": False,
    },
]

DEMO_METRICS = {
    "tenders_total": 47,
    "tenders_won": 19,
    "win_rate_pct": 40.4,
    "avg_value_pln": 1_250_000,
    "total_value_won_pln": 23_750_000,
    "pending_decisions": 3,
    "active_analyses": 5,
}


@router.get("/tenders")
def demo_tenders() -> list[dict[str, Any]]:
    """Return demo tender list."""
    _check_demo_enabled()
    return DEMO_TENDERS


@router.get("/metrics")
def demo_metrics() -> dict[str, Any]:
    """Return demo dashboard metrics."""
    _check_demo_enabled()
    return DEMO_METRICS


@router.get("/status")
def demo_status() -> dict[str, Any]:
    """Return demo mode status."""
    return {
        "demo_mode": DEMO_ENABLED,
        "message": "Demo mode aktywny — dane przykładowe" if DEMO_ENABLED else "Demo wyłączone",
    }


# ── S3-05: Demo tenant auto-reset ──────────────────────────────────────────────

DEMO_ORG_ID: str = os.getenv("DEMO_ORG_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")
DEMO_RESET_SECRET: str = os.getenv("DEMO_RESET_SECRET", "demo-reset-secret-change-in-prod")

_SEED_TENDERS = [
    {"title": "Budowa drogi gminnej w miejscowości Kowale", "buyer": "Gmina Kowale",
     "value_pln": 2_450_000, "cpv": "45233120-6"},
    {"title": "Remont nawierzchni ul. Lipowej w Strzelinie", "buyer": "Powiat Strzeliński",
     "value_pln": 890_000, "cpv": "45233220-7"},
    {"title": "Budowa zbiornika retencyjnego", "buyer": "Gmina Piława Górna",
     "value_pln": 3_200_000, "cpv": "45247270-3"},
    {"title": "Termomodernizacja budynku szkoły podstawowej", "buyer": "Gmina Dzierżoniów",
     "value_pln": 1_750_000, "cpv": "45321000-3"},
    {"title": "Budowa chodnika wzdłuż DW385", "buyer": "ZDW Dolnośląskiego",
     "value_pln": 420_000, "cpv": "45233162-2"},
]


@router.post("/reset")
def demo_reset(secret: str = "") -> dict[str, Any]:
    """S3-05 — Reset demo org: wipe non-permanent data, re-seed demo tenders.

    Requires ?secret=DEMO_RESET_SECRET (or env DEMO_RESET_SECRET).
    Called by Hermes cron every 24h.
    """
    _check_demo_enabled()
    if secret != DEMO_RESET_SECRET:
        raise HTTPException(status_code=403, detail="Invalid reset secret")

    import uuid as _uuid
    from datetime import datetime, timezone, timedelta
    from terra_db.session import get_engine
    from sqlalchemy.orm import Session

    engine = get_engine()
    now = datetime.now(timezone.utc)

    with Session(engine) as db:
        # 1. Usuń tendery demo — wyłącz FK triggers żeby nie szukać wszystkich zależności
        db.execute(text("SET session_replication_role = replica"))
        db.execute(text("DELETE FROM tender WHERE tenant_id = :oid"), {"oid": DEMO_ORG_ID})
        db.execute(text("SET session_replication_role = DEFAULT"))

        # 2. Re-seed demo tenders
        for i, td in enumerate(_SEED_TENDERS):
            ext_id = f"DEMO-RESET-{_uuid.uuid4().hex[:8].upper()}"
            db.execute(text(
                "INSERT INTO tender "
                "(id, title, buyer, source, external_id, published_at, deadline_at, value_pln, "
                " status, match_score, tenant_id) "
                "VALUES (:id, :title, :buyer, 'bzp', :ext, :pub, :dl, :val, 'new', :ms, :oid)"
            ), {
                "id": str(_uuid.uuid4()),
                "title": td["title"],
                "buyer": td["buyer"],
                "ext": ext_id,
                "pub": now - timedelta(days=i),
                "dl": now + timedelta(days=30 - i * 4),
                "val": td["value_pln"],
                "ms": round(0.85 - i * 0.06, 2),
                "oid": DEMO_ORG_ID,
            })

        # 3. Ensure subscription exists (no tender_limit column)
        db.execute(text(
            "INSERT INTO subscription (org_id, plan, status) "
            "VALUES (:oid, 'pro', 'active') "
            "ON CONFLICT (org_id) DO UPDATE SET plan='pro', status='active'"
        ), {"oid": DEMO_ORG_ID})

        db.commit()

    return {
        "ok": True,
        "reset_at": now.isoformat(),
        "org_id": DEMO_ORG_ID,
        "seeded_tenders": len(_SEED_TENDERS),
    }
