"""Faza 4 — API v2: Decisions router (GO/NO-GO).

Używa tabeli approval_request (id, tenant_id, action, payload, status, requested_at).
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/decisions", tags=["decisions-v2"])


class DecisionCreate(BaseModel):
    tender_id: str
    decision: str  # GO | NO-GO
    rationale: str = ""
    ahp_scores: dict | None = None
    value_pln: float | None = None  # S74: bid value for escalation


@router.get("")
def list_decisions(tender_id: str, user: AuthUser) -> dict:
    """Lista decyzji dla przetargu (filtr po payload.tender_id)."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """SELECT id, action, payload, status, requested_at, decided_at
                   FROM approval_request
                   WHERE tenant_id = :tenant_id
                     AND payload->>'tender_id' = :tender_id
                   ORDER BY requested_at DESC"""
            ),
            {"tenant_id": tenant_id, "tender_id": tender_id},
        ).fetchall()

    return {
        "items": [
            {
                "id": str(r.id),
                "tender_id": tender_id,
                "decision": r.payload.get("decision") if isinstance(r.payload, dict) else None,
                "status": r.status,
                "rationale": r.payload.get("rationale") if isinstance(r.payload, dict) else None,
                "created_at": r.requested_at.isoformat() if r.requested_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.post("")
def create_decision(body: DecisionCreate, user: AuthUser) -> dict:
    """Utwórz decyzję GO/NO-GO."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    decision_upper = body.decision.upper().strip()
    if decision_upper not in ("GO", "NO-GO", "NOGO", "NO_GO"):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_decision", "message": "decision musi być GO lub NO-GO"},
        )

    # Map do approval_status enum
    status_map = {"GO": "approved", "NO-GO": "rejected", "NOGO": "rejected", "NO_GO": "rejected"}
    db_status = status_map[decision_upper]

    # Sprawdź przetarg — używamy tenant z tabeli tenant, nie organizations
    # Szukamy po DEFAULT_TENANT_ID lub user.org_id
    # tender.tenant_id → tabela tenant
    with engine.connect() as conn:
        tender = conn.execute(
            sa.text("SELECT id, tenant_id FROM tender WHERE id = :id LIMIT 1"),
            {"id": body.tender_id},
        ).fetchone()

    if not tender:
        raise HTTPException(status_code=404, detail={"error": "tender_not_found", "message": "Przetarg nie znaleziony"})

    # Użyj tenant_id z przetargu (bo tabela approval_request FK → tenant.id)
    actual_tenant_id = str(tender.tenant_id)

    payload = {
        "tender_id": body.tender_id,
        "decision": decision_upper,
        "rationale": body.rationale,
        "org_id": tenant_id,
    }
    if body.ahp_scores:
        payload["ahp_scores"] = body.ahp_scores

    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """INSERT INTO approval_request
                       (id, tenant_id, action, payload, status, requested_at)
                   VALUES (:id, :tid, :action, CAST(:payload AS jsonb), :status, NOW())
                   RETURNING id, action, payload, status, requested_at"""
            ),
            {
                "id": new_id,
                "tid": actual_tenant_id,
                "action": "bid_decision",
                "payload": json.dumps(payload),
                "status": db_status,
            },
        ).fetchone()

        # Zaktualizuj status przetargu
        new_tender_status = "decided_go" if db_status == "approved" else "decided_nogo"
        conn.execute(
            sa.text("UPDATE tender SET status = :s WHERE id = :id"),
            {"s": new_tender_status, "id": body.tender_id},
        )

        # S74 — Escalation: bid > 1 000 000 PLN → dodaj eskalację pending
        escalation_created = False
        if decision_upper in ("GO",) and body.value_pln and body.value_pln > 1_000_000:
            esc_payload = json.dumps({
                "tender_id": body.tender_id,
                "decision": decision_upper,
                "value_pln": body.value_pln,
                "escalation": True,
            })
            conn.execute(
                sa.text(
                    """INSERT INTO approval_request
                           (id, tenant_id, action, payload, status, requested_at)
                       VALUES (gen_random_uuid(), :tid, :action, CAST(:payload AS jsonb), 'pending', NOW())"""
                ),
                {
                    "tid": actual_tenant_id,
                    "action": "bid_escalation",
                    "payload": esc_payload,
                },
            )
            escalation_created = True

    resp = {
        "id": str(result.id),
        "tender_id": body.tender_id,
        "decision": decision_upper,
        "status": result.status,
        "rationale": body.rationale,
        "created_at": result.requested_at.isoformat() if result.requested_at else None,
    }
    if escalation_created:
        resp["escalation"] = "pending"
    return resp


@router.get("/{decision_id}")
def get_decision(decision_id: str, user: AuthUser) -> dict:
    """Szczegóły decyzji."""
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """SELECT id, action, payload, status, requested_at, decided_at
                   FROM approval_request
                   WHERE id = :id"""
            ),
            {"id": decision_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Decyzja nie znaleziona"})

    payload = row.payload if isinstance(row.payload, dict) else {}
    return {
        "id": str(row.id),
        "tender_id": payload.get("tender_id"),
        "decision": payload.get("decision"),
        "status": row.status,
        "rationale": payload.get("rationale"),
        "created_at": row.requested_at.isoformat() if row.requested_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }


# ─────────────────── S73: Bulk decision update ───────────────────────────── #

class BulkDecisionCreate(BaseModel):
    tender_ids: list[str]
    decision: str  # GO | NO-GO | bid | pass
    rationale: str = ""


@router.post("/bulk", status_code=201)
def bulk_decision(body: BulkDecisionCreate, user: AuthUser) -> dict:
    """S73: Batch upsert decyzji dla listy przetargów."""
    engine = get_engine()
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(403, "Brak org_id")

    created = []
    with engine.connect() as conn:
        for tid in body.tender_ids:
            req_id = str(uuid.uuid4())
            conn.execute(sa.text("""
                INSERT INTO approval_request (id, tenant_id, action, payload, status)
                VALUES (:id, :tenant_id, 'decision', :payload::jsonb, 'pending')
            """), {
                "id": req_id,
                "tenant_id": tenant_id,
                "payload": json.dumps({
                    "tender_id": tid,
                    "decision": body.decision,
                    "rationale": body.rationale,
                }),
            })
            created.append(req_id)
        conn.commit()
    return {"created": len(created), "ids": created}


# ─────────────────── S75: Deadline reminders (post-hook) ─────────────────── #

def insert_deadline_reminders(engine: Any, tenant_id: str) -> int:
    """S75: Wstaw powiadomienia dla przetargów z deadline za 1/3/7 dni."""
    inserted = 0
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT t.id, t.title, t.deadline_at::date AS dl,
                       o.id AS org_id
                FROM tender t
                JOIN tenant ten ON ten.id = t.tenant_id
                JOIN organizations o ON o.id = ten.id
                WHERE t.tenant_id = :tid
                  AND t.deadline_at IS NOT NULL
                  AND t.deadline_at::date IN (
                      current_date + 7,
                      current_date + 3,
                      current_date + 1
                  )
            """), {"tid": tenant_id}).fetchall()
            for row in rows:
                days_left = (row.dl - __import__("datetime").date.today()).days
                conn.execute(sa.text("""
                    INSERT INTO notifications (id, org_id, type, title, body)
                    VALUES (gen_random_uuid(), :org_id, 'deadline_reminder',
                            :title, :body)
                    ON CONFLICT DO NOTHING
                """), {
                    "org_id": str(row.org_id),
                    "title": f"Deadline przetargu za {days_left} dni",
                    "body": f"Przetarg: {row.title} — termin: {row.dl}",
                })
                inserted += 1
            conn.commit()
    except Exception:
        pass
    return inserted
