"""M6 — RFQ agent + Approval gate.

Endpoints:
  POST /tenders/{id}/rfq                  ← {scope_desc, counterparties[]} → 202 {approval_id}
  GET  /rfq/{id}                          → RFQ{status, messages[], parsed_offers[]}
  POST /rfq/{id}/inbound                  ← {message_uid, counterparty, body} → parsed_offer (fixture)
  POST /tenders/{id}/autofill             → 202 {approval_id}  (gated draft)
  GET  /approvals?status=pending          → [ApprovalRequest]
  POST /approvals/{id}/approve            → {executed:true, result:{...}}
  POST /approvals/{id}/reject             → {ok:true}

All external sends are GATED — POST /rfq returns 202+approval_id, never sends directly.
The actual send is triggered only by POST /approvals/{id}/approve.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser, TenantDep, get_current_user

router = APIRouter(prefix="/api/v1", tags=["rfq", "approvals"])

# ──────────────────────────────────────────────────────────────────────────────
# v2 router alias — provides GET /api/v2/rfq
# ──────────────────────────────────────────────────────────────────────────────
router_v2 = APIRouter(prefix="/api/v2", tags=["rfq"])


@router_v2.get("/rfq")
def list_rfq_v2(user: AuthUser) -> dict:
    """GET /api/v2/rfq — list RFQ records for current tenant."""
    from terra_db.session import get_engine
    import sqlalchemy as sa
    engine = get_engine()
    tid = str(user.org_id)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT id, tender_id, status, scope_desc, created_at "
                "FROM rfq WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 50"
            ),
            {"tid": tid},
        ).fetchall()
    return {
        "total": len(rows),
        "items": [
            {
                "id": str(r.id),
                "tender_id": str(r.tender_id) if r.tender_id else None,
                "status": r.status,
                "scope_desc": r.scope_desc,
                "created_at": str(r.created_at),
            }
            for r in rows
        ],
    }



# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RFQCreate(BaseModel):
    scope_desc: str
    counterparties: list[str] = []


class ParsedOffer(BaseModel):
    counterparty: str
    price_net_pln: float | None = None
    lead_time_days: int | None = None
    notes: str = ""


class RFQMessage(BaseModel):
    direction: str       # "out" | "in"
    counterparty: str | None = None
    subject: str | None = None
    body: str | None = None
    parsed_offer: ParsedOffer | None = None
    message_uid: str | None = None


class RFQResponse(BaseModel):
    id: str
    status: str
    scope_desc: str
    messages: list[RFQMessage]
    parsed_offers: list[ParsedOffer]


class InboundMessage(BaseModel):
    message_uid: str
    counterparty: str
    subject: str = ""
    body: str


class ApprovalResponse(BaseModel):
    approval_id: str


class ApprovalRequest(BaseModel):
    id: str
    action: str
    payload: dict
    status: str
    requested_at: str


class ApproveResult(BaseModel):
    executed: bool
    result: dict


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/rfq  — gated RFQ creation
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/rfq", status_code=202, response_model=ApprovalResponse)
def create_rfq(tender_id: str, body: RFQCreate, tenant_id: TenantDep, user: AuthUser) -> ApprovalResponse:
    """Prepare RFQ emails to counterparties. GATED — returns 202 + approval_id.

    Does NOT send any emails. Creates rfq row (draft) + approval_request.
    Actual send happens only after POST /approvals/{id}/approve.
    """
    engine = get_engine()

    # Verify tender exists
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, tenant_id FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tender not found")
    tenant_id = str(row[1])

    rfq_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())

    with engine.begin() as conn:
        # Create RFQ in draft status
        conn.execute(sa.text(
            "INSERT INTO rfq (id, tenant_id, tender_id, scope_desc, status, created_at) "
            "VALUES (:id, :tid, :tender, :scope, 'draft', now())"
        ), {"id": rfq_id, "tid": tenant_id, "tender": tender_id, "scope": body.scope_desc})

        # Create approval request
        conn.execute(sa.text(
            "INSERT INTO approval_request (id, tenant_id, action, payload, status, requested_at) "
            "VALUES (:id, :tid, 'rfq_send', cast(:payload as jsonb), 'pending', now())"
        ), {
            "id": approval_id,
            "tid": tenant_id,
            "payload": json.dumps({
                "rfq_id": rfq_id,
                "tender_id": tender_id,
                "scope_desc": body.scope_desc,
                "counterparties": body.counterparties,
            }),
        })

    return ApprovalResponse(approval_id=approval_id)


# ──────────────────────────────────────────────────────────────────────────────
# GET /rfq/{id}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/rfq/{rfq_id}", response_model=RFQResponse)
def get_rfq(rfq_id: str, tenant_id: TenantDep, user: AuthUser) -> RFQResponse:
    """Get RFQ with messages and parsed offers."""
    engine = get_engine()

    with engine.connect() as conn:
        rfq_row = conn.execute(
            sa.text("SELECT id, status, scope_desc FROM rfq WHERE id = :id"), {"id": rfq_id}
        ).fetchone()
        if not rfq_row:
            raise HTTPException(status_code=404, detail="RFQ not found")

        msg_rows = conn.execute(
            sa.text(
                "SELECT direction, counterparty, subject, body, parsed_offer, message_uid "
                "FROM rfq_message WHERE rfq_id = :rid ORDER BY created_at"
            ),
            {"rid": rfq_id},
        ).fetchall()

    messages = [
        RFQMessage(
            direction=r[0], counterparty=r[1], subject=r[2],
            body=r[3], message_uid=r[5],
            parsed_offer=ParsedOffer(**r[4]) if r[4] else None,
        )
        for r in msg_rows
    ]
    parsed_offers = [m.parsed_offer for m in messages if m.parsed_offer]

    return RFQResponse(
        id=str(rfq_row[0]),
        status=rfq_row[1],
        scope_desc=rfq_row[2],
        messages=messages,
        parsed_offers=parsed_offers,
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /rfq/{id}/inbound  — fixture inbound reply (IMAP parse simulation)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/rfq/{rfq_id}/inbound")
def rfq_inbound(rfq_id: str, body: InboundMessage, tenant_id: TenantDep, user: AuthUser) -> dict:
    """Record and parse an inbound reply (fixtured IMAP message).

    Parses price and lead_time from email body using regex.
    Idempotent on message_uid.
    """
    engine = get_engine()

    with engine.connect() as conn:
        rfq_row = conn.execute(
            sa.text("SELECT id, tenant_id FROM rfq WHERE id = :id"), {"id": rfq_id}
        ).fetchone()
    if not rfq_row:
        raise HTTPException(status_code=404, detail="RFQ not found")
    tenant_id = str(rfq_row[1])

    # Idempotency check
    with engine.connect() as conn:
        dup = conn.execute(
            sa.text("SELECT id FROM rfq_message WHERE rfq_id=:rid AND message_uid=:uid"),
            {"rid": rfq_id, "uid": body.message_uid},
        ).fetchone()
    if dup:
        return {"ok": True, "duplicate": True}

    # Parse offer from body
    offer = _parse_offer_from_email(body.body, body.counterparty)

    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO rfq_message "
            "(id, tenant_id, rfq_id, direction, counterparty, subject, body, parsed_offer, message_uid, created_at) "
            "VALUES (:id, :tid, :rid, 'in', :cp, :subj, :body, cast(:offer as jsonb), :uid, now())"
        ), {
            "id": str(uuid.uuid4()), "tid": tenant_id, "rid": rfq_id,
            "cp": body.counterparty, "subj": body.subject, "body": body.body,
            "offer": json.dumps(offer),
            "uid": body.message_uid,
        })
        # Update RFQ status to received
        conn.execute(sa.text(
            "UPDATE rfq SET status='received' WHERE id=:id AND status NOT IN ('closed')"
        ), {"id": rfq_id})

    return {"ok": True, "parsed_offer": offer}


# ──────────────────────────────────────────────────────────────────────────────
# POST /tenders/{id}/autofill  — gated auto-fill draft
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/tenders/{tender_id}/autofill", status_code=202, response_model=ApprovalResponse)
def autofill_tender(tender_id: str, tenant_id: TenantDep, user: AuthUser) -> ApprovalResponse:
    """Prepare tender form auto-fill draft from owner_profile. GATED — 202 + approval_id.

    NEVER submits the form. Draft is produced; submission requires approval.
    """
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, tenant_id, title FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tender not found")
    tenant_id = str(row[1])

    # Load owner profile
    with engine.connect() as conn:
        profile = conn.execute(
            sa.text("SELECT company_name, cpv_preferred FROM owner_profile WHERE tenant_id=:tid LIMIT 1"),
            {"tid": tenant_id},
        ).fetchone()

    draft = {
        "tender_id": tender_id,
        "tender_title": row[2],
        "company_name": profile[0] if profile else "Firma Budowlana",
        "cpv": profile[1] if profile else [],
        "status": "draft",
        "note": "Wygenerowany szkic — wymaga weryfikacji przed złożeniem.",
    }

    approval_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO approval_request (id, tenant_id, action, payload, status, requested_at) "
            "VALUES (:id, :tid, 'autofill_submit', cast(:payload as jsonb), 'pending', now())"
        ), {"id": approval_id, "tid": tenant_id, "payload": json.dumps(draft)})

    return ApprovalResponse(approval_id=approval_id)


# ──────────────────────────────────────────────────────────────────────────────
# Approval gate
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/approvals", response_model=list[ApprovalRequest])
def list_approvals(tenant_id: TenantDep, user: AuthUser, status: str = "pending") -> list[ApprovalRequest]:
    """List approval requests by status — filtered by tenant (IDOR fix)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT id, action, payload, status, requested_at "
                "FROM approval_request WHERE status=:s AND tenant_id=:tid "
                "ORDER BY requested_at DESC LIMIT 50"
            ),
            {"s": status, "tid": tenant_id},
        ).fetchall()
    return [
        ApprovalRequest(
            id=str(r[0]), action=r[1], payload=r[2] or {},
            status=r[3], requested_at=str(r[4]),
        )
        for r in rows
    ]


@router.post("/approvals/{approval_id}/approve", response_model=ApproveResult)
def approve_action(approval_id: str, tenant_id: TenantDep, user: AuthUser) -> ApproveResult:
    """Execute approved action + write audit log.

    This is the ONLY path that triggers sends/submissions.
    """
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, tenant_id, action, payload, status FROM approval_request WHERE id=:id"),
            {"id": approval_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if row[4] != "pending":
        raise HTTPException(status_code=409, detail=f"Approval already {row[4]}")

    tenant_id = str(row[1])
    action = row[2]
    payload = row[3] or {}

    # Execute the gated action
    result = _execute_gated_action(engine, action, payload, tenant_id)

    # Mark approved + write audit
    with engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE approval_request SET status='approved', decided_at=now(), decided_by='system' WHERE id=:id"
        ), {"id": approval_id})
        conn.execute(sa.text(
            "INSERT INTO audit_log (tenant_id, at, actor, action, entity, entity_id, detail) "
            "VALUES (:tid, now(), 'system', :action, 'approval_request', cast(:eid as uuid), cast(:detail as jsonb))"
        ), {
            "tid": tenant_id,
            "action": f"approved:{action}",
            "eid": approval_id,
            "detail": json.dumps({"payload": payload, "result": result}),
        })

    return ApproveResult(executed=True, result=result)


@router.post("/approvals/{approval_id}/reject")
def reject_action(approval_id: str, tenant_id: TenantDep, user: AuthUser) -> dict:
    """Reject an approval request."""
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, tenant_id, status FROM approval_request WHERE id=:id"),
            {"id": approval_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if row[2] != "pending":
        raise HTTPException(status_code=409, detail=f"Approval already {row[2]}")

    tenant_id = str(row[1])
    with engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE approval_request SET status='rejected', decided_at=now(), decided_by='system' WHERE id=:id"
        ), {"id": approval_id})
        conn.execute(sa.text(
            "INSERT INTO audit_log (tenant_id, at, actor, action, entity, entity_id, detail) "
            "VALUES (:tid, now(), 'system', 'rejected', 'approval_request', cast(:eid as uuid), cast(:detail as jsonb))"
        ), {"tid": tenant_id, "eid": approval_id, "detail": json.dumps({})})

    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_offer_from_email(body: str, counterparty: str) -> dict:
    """Parse price and lead_time from email body (regex-based).

    Examples it handles:
      "Oferujemy wykonanie za 45 000 zł netto w terminie 30 dni"
      "Cena: 38500 PLN, termin: 21 dni roboczych"
    """
    price = None
    lead_time = None

    # Price patterns (PLN)
    price_patterns = [
        r"(\d[\d\s]*[\d])\s*(?:zł|PLN|pln|zl)\s*(?:netto|brutto)?",
        r"(?:cena|kwota|wycena)[:\s]+(\d[\d\s]*[\d])",
        r"za\s+(\d[\d\s]*[\d])\s*(?:zł|PLN)",
    ]
    for pat in price_patterns:
        m = re.search(pat, body, re.I)
        if m:
            raw = re.sub(r"\s", "", m.group(1))
            try:
                price = float(raw)
                break
            except ValueError:
                continue

    # Lead time patterns (days)
    lead_patterns = [
        r"(?:termin|czas|realizacja)[:\s]+(\d+)\s*(?:dni|day)",
        r"(\d+)\s*(?:dni|day)\s*(?:robocz\w+)?",
        r"w\s+ciągu\s+(\d+)\s*(?:dni|day)",
    ]
    for pat in lead_patterns:
        m = re.search(pat, body, re.I)
        if m:
            try:
                lead_time = int(m.group(1))
                break
            except ValueError:
                continue

    return {
        "counterparty": counterparty,
        "price_net_pln": price,
        "lead_time_days": lead_time,
        "notes": body[:200],
    }


def _execute_gated_action(
    engine: Any, action: str, payload: dict, tenant_id: str
) -> dict:
    """Execute the gated side-effect action after approval."""

    if action == "rfq_send":
        rfq_id = payload.get("rfq_id")
        counterparties = payload.get("counterparties", [])
        if rfq_id:
            with engine.begin() as conn:
                # Update RFQ status to sent + record outbound messages
                conn.execute(sa.text(
                    "UPDATE rfq SET status='sent' WHERE id=:id"
                ), {"id": rfq_id})
                for cp in counterparties:
                    conn.execute(sa.text(
                        "INSERT INTO rfq_message (id, tenant_id, rfq_id, direction, counterparty, "
                        "subject, body, created_at) "
                        "VALUES (:id, :tid, :rid, 'out', :cp, :subj, :body, now())"
                    ), {
                        "id": str(uuid.uuid4()), "tid": tenant_id, "rid": rfq_id,
                        "cp": cp,
                        "subj": f"Zapytanie ofertowe — {payload.get('scope_desc', '')[:50]}",
                        "body": f"Szanowni Państwo,\n\nProsimy o ofertę na: {payload.get('scope_desc', '')}\n\nPozdrawiamy",
                    })
        return {"rfq_id": rfq_id, "sent_to": counterparties}

    elif action == "autofill_submit":
        # Never actually submits — records draft as produced
        return {"status": "draft_produced", "tender_id": payload.get("tender_id")}

    else:
        return {"action": action, "status": "executed"}


# ──────────────────────────────────────────────────────────────────────────────
# S76/S77 — Send RFQ to subcontractors (dry-run)
# ──────────────────────────────────────────────────────────────────────────────

import logging as _logging

_logger = _logging.getLogger(__name__)


class RFQSendToSubcontractors(BaseModel):
    emails: list[str]
    message: str = ""


@router.post("/api/v2/rfq/{rfq_id}/send-to-subcontractors", tags=["rfq"])
def send_rfq_to_subcontractors(
    rfq_id: str,
    body: RFQSendToSubcontractors,
    tenant_id: TenantDep,
    user: AuthUser,
) -> dict:
    """S76/S77 — Wyślij RFQ do podwykonawców (dry-run: log + update status)."""
    engine = get_engine()
    with engine.connect() as conn:
        rfq = conn.execute(
            sa.text("SELECT id, status, scope_desc FROM rfq WHERE id = :id AND tenant_id = :tid"),
            {"id": rfq_id, "tid": tenant_id},
        ).fetchone()
    if not rfq:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"error": "rfq_not_found"})

    # Dry-run — log each email
    for email in body.emails:
        _logger.info(
            "[S76-RFQ] Sending RFQ %s to %s | scope: %s | msg: %s",
            rfq_id, email, rfq.scope_desc, body.message[:100],
        )

    with engine.begin() as conn:
        conn.execute(
            sa.text("UPDATE rfq SET status = 'sent' WHERE id = :id"),
            {"id": rfq_id},
        )

    return {"sent_to": body.emails, "status": "queued"}


# ── v2 POST alias — musi być po definicji ApprovalResponse + create_rfq ────────
@router_v2.post("/tenders/{tender_id}/rfq", status_code=202, response_model=ApprovalResponse)
def create_rfq_v2(tender_id: str, body: RFQCreate, tenant_id: TenantDep, user: AuthUser) -> ApprovalResponse:
    """POST /api/v2/tenders/{id}/rfq — alias v2 dla v1 RFQ gated endpoint."""
    return create_rfq(tender_id, body, tenant_id, user)
