"""
Terra-OS n8n Automation Layer — event bus + webhook dispatcher.

Simply-clever philosophy:
- Zero config: domyślne n8n webhooks działają out of the box
- One-click: frontend triggeruje eventy jednym kliknięciem
- Smart defaults: akcje inferowane z kontekstu (kosztorys gotowy → wyślij PDF)
"""
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from services.api.services.api.auth.deps import get_current_user, CurrentUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/automations", tags=["automations"])


# ─── Models ───────────────────────────────────────────────────────────────────

class WebhookConfig(BaseModel):
    """Konfiguracja outgoing webhook (do n8n)."""
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., pattern=r"^https?://")
    events: list[str] = Field(default_factory=list, description="Lista eventów do subskrypcji, np. ['kosztorys.ready', 'kosztorys.approved']")
    active: bool = True
    secret: str | None = None
    metadata: dict = Field(default_factory=dict)


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None
    secret: str | None = None


class AutomationTrigger(BaseModel):
    """One-click trigger z frontendu."""
    event: str = Field(..., description="Typ eventu: kosztorys.ready, kosztorys.send_pdf, tender.analyze")
    entity_id: str = Field(..., description="ID obiektu (kosztorys_id, tender_id)")
    payload: dict = Field(default_factory=dict, description="Dodatkowe dane")


# ─── Event Types (Simply-Clever defaults) ─────────────────────────────────────

EVENTS = {
    # Kosztorys lifecycle
    "kosztorys.created": "Nowy kosztorys utworzony",
    "kosztorys.ready": "Kosztorys gotowy do wysyłki (recalc done)",
    "kosztorys.approved": "Kosztorys zaakceptowany",
    "kosztorys.rejected": "Kosztorys odrzucony",
    "kosztorys.send_pdf": "Wyślij PDF kosztorysu (email/telegram)",
    "kosztorys.anomaly_detected": "Wykryto anomalię cenową",
    # Tender/ZWIAD lifecycle
    "tender.new": "Nowy przetarg znaleziony przez ZWIAD",
    "tender.deadline_approaching": "Termin składania ofert < 3 dni",
    "tender.analyze": "Rozpocznij analizę przetargu",
    "tender.won": "Przetarg wygrany",
    "tender.lost": "Przetarg przegrany",
    # Intelligence
    "intelligence.price_alert": "Alert cenowy — ICB zmiana > 10%",
    "intelligence.market_shift": "Zmiana trendu rynkowego",
    # System
    "system.daily_digest": "Dzienny raport",
    "system.weekly_summary": "Tygodniowe podsumowanie",
}


# ─── Webhook CRUD ─────────────────────────────────────────────────────────────

def _get_tenant(user: CurrentUser) -> str:
    return user.org_id


@router.get("/webhooks")
def list_webhooks(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """Lista skonfigurowanych webhooków."""
    tenant_id = _get_tenant(user)
    with get_engine().connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, name, url, events, active, created_at
            FROM automation_webhook
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """), {"tid": tenant_id}).mappings().all()
    return [dict(r) for r in rows]


@router.post("/webhooks", status_code=201)
def create_webhook(body: WebhookConfig, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Zarejestruj nowy webhook (np. URL n8n workflow)."""
    tenant_id = _get_tenant(user)
    wid = str(uuid.uuid4())
    with get_engine().connect() as conn:
        conn.execute(sa.text("""
            INSERT INTO automation_webhook (id, tenant_id, name, url, events, active, secret)
            VALUES (:id, :tid, :name, :url, :events, :active, :secret)
        """), {
            "id": wid, "tid": tenant_id,
            "name": body.name, "url": body.url,
            "events": body.events, "active": body.active,
            "secret": body.secret,
        })
        conn.commit()
    return {"id": wid, "status": "created"}


@router.patch("/webhooks/{wid}")
def update_webhook(wid: str, body: WebhookUpdate, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Aktualizuj webhook."""
    tenant_id = _get_tenant(user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["wid"] = wid
    updates["tid"] = tenant_id
    with get_engine().connect() as conn:
        result = conn.execute(sa.text(f"""
            UPDATE automation_webhook SET {set_clause}
            WHERE id = :wid AND tenant_id = :tid
        """), updates)
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Webhook not found")
    return {"status": "updated"}


@router.delete("/webhooks/{wid}")
def delete_webhook(wid: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    tenant_id = _get_tenant(user)
    with get_engine().connect() as conn:
        result = conn.execute(sa.text(
            "DELETE FROM automation_webhook WHERE id = :wid AND tenant_id = :tid"
        ), {"wid": wid, "tid": tenant_id})
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Webhook not found")
    return {"status": "deleted"}


# ─── Event Dispatch ───────────────────────────────────────────────────────────

@router.post("/trigger")
async def trigger_event(
    body: AutomationTrigger,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    One-click trigger — frontend wywołuje event, backend rozsyła do n8n.
    Simply-clever: zero konfiguracji, klik = akcja.
    """
    tenant_id = _get_tenant(user)

    if body.event not in EVENTS:
        raise HTTPException(422, f"Unknown event: {body.event}. Available: {list(EVENTS.keys())}")

    # Build event payload
    event_payload = {
        "event": body.event,
        "entity_id": body.entity_id,
        "tenant_id": tenant_id,
        "triggered_by": user.email,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "payload": body.payload,
    }

    # Enrich with entity data
    event_payload["entity_data"] = _enrich_entity(body.event, body.entity_id, tenant_id)

    # Log event
    _log_event(tenant_id, body.event, body.entity_id, event_payload)

    # Dispatch to all matching webhooks in background
    background_tasks.add_task(_dispatch_webhooks, tenant_id, body.event, event_payload)

    return {
        "status": "triggered",
        "event": body.event,
        "entity_id": body.entity_id,
        "webhooks_notified": "async",
    }


@router.get("/events")
def list_events(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Lista dostępnych eventów do triggerowania."""
    return {"events": EVENTS}


@router.get("/history")
def event_history(
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """Historia triggerowanych eventów."""
    tenant_id = _get_tenant(user)
    with get_engine().connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, event, entity_id, triggered_by, triggered_at, status, response_code
            FROM automation_event_log
            WHERE tenant_id = :tid
            ORDER BY triggered_at DESC
            LIMIT :lim
        """), {"tid": tenant_id, "lim": limit}).mappings().all()
    return [dict(r) for r in rows]


# ─── Simply-Clever: Suggested Actions ─────────────────────────────────────────

@router.get("/suggestions/{entity_type}/{entity_id}")
def get_suggestions(
    entity_type: str,
    entity_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """
    Smart suggestions — co można zrobić z tym obiektem?
    Simply-clever: system SAM podpowiada akcje na podstawie kontekstu.
    """
    tenant_id = _get_tenant(user)

    if entity_type == "kosztorys":
        return _suggest_kosztorys_actions(entity_id, tenant_id)
    elif entity_type == "tender":
        return _suggest_tender_actions(entity_id, tenant_id)
    return []


def _suggest_kosztorys_actions(kid: str, tenant_id: str) -> list[dict]:
    """Inteligentne podpowiedzi akcji dla kosztorysu."""
    with get_engine().connect() as conn:
        row = conn.execute(sa.text("""
            SELECT status, suma_netto, win_probability, anomaly_score,
                   (SELECT count(*) FROM kosztorys_pozycja WHERE kosztorys_id = k.id) as poz_count
            FROM kosztorys k WHERE id = :kid AND tenant_id = :tid
        """), {"kid": kid, "tid": tenant_id}).mappings().first()

    if not row:
        return []

    suggestions = []

    # Bazowe akcje zawsze dostępne
    if row.poz_count > 0:
        suggestions.append({
            "event": "kosztorys.send_pdf",
            "label": "📤 Wyślij PDF",
            "description": "Generuj i wyślij PDF do inwestora",
            "priority": "high" if row.suma_netto and float(row.suma_netto) > 0 else "low",
            "icon": "send",
        })

    if row.status in (None, "draft", "created"):
        suggestions.append({
            "event": "kosztorys.ready",
            "label": "✅ Oznacz jako gotowy",
            "description": "Kosztorys gotowy do weryfikacji",
            "priority": "high",
            "icon": "check-circle",
        })

    # Intelligence-driven suggestions
    if row.anomaly_score and float(row.anomaly_score) > 0.7:
        suggestions.append({
            "event": "kosztorys.anomaly_detected",
            "label": "⚠️ Sprawdź anomalie",
            "description": f"Anomaly score: {float(row.anomaly_score):.0%} — sprawdź ceny",
            "priority": "critical",
            "icon": "alert-triangle",
        })

    if row.win_probability and float(row.win_probability) < 0.4:
        suggestions.append({
            "event": "kosztorys.ready",
            "label": "📊 Optymalizuj cenę",
            "description": f"Win probability: {float(row.win_probability):.0%} — za wysoka cena?",
            "priority": "medium",
            "icon": "trending-down",
        })

    return suggestions


def _suggest_tender_actions(tid: str, tenant_id: str) -> list[dict]:
    """Podpowiedzi akcji dla przetargu."""
    with get_engine().connect() as conn:
        row = conn.execute(sa.text("""
            SELECT stage, deadline_at, title
            FROM tender WHERE id = :tid AND tenant_id = :tenant_id
        """), {"tid": tid, "tenant_id": tenant_id}).mappings().first()

    if not row:
        return []

    suggestions = []

    if row.stage in ("new", "discovered"):
        suggestions.append({
            "event": "tender.analyze",
            "label": "🔍 Analizuj przetarg",
            "description": "Uruchom pełną analizę ZWIAD",
            "priority": "high",
            "icon": "search",
        })

    if row.deadline_at:
        from datetime import timedelta
        days_left = (row.deadline_at.replace(tzinfo=None) - datetime.now(datetime.timezone.utc)).days
        if days_left <= 3:
            suggestions.append({
                "event": "tender.deadline_approaching",
                "label": f"⏰ Deadline za {days_left}d!",
                "description": "Termin składania ofert blisko",
                "priority": "critical",
                "icon": "clock",
            })

    suggestions.append({
        "event": "kosztorys.created",
        "label": "📋 Utwórz kosztorys",
        "description": "Nowy kosztorys z danych przetargu",
        "priority": "medium",
        "icon": "file-plus",
    })

    return suggestions


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _enrich_entity(event: str, entity_id: str, tenant_id: str) -> dict:
    """Wzbogać payload o dane encji — n8n dostaje pełny kontekst."""
    prefix = event.split(".")[0]
    with get_engine().connect() as conn:
        if prefix == "kosztorys":
            row = conn.execute(sa.text("""
                SELECT id, nazwa, inwestor, lokalizacja, typ, status,
                       suma_netto, suma_brutto, win_probability
                FROM kosztorys
                WHERE id = :eid AND tenant_id = :tid
            """), {"eid": entity_id, "tid": tenant_id}).mappings().first()
            return dict(row) if row else {}
        elif prefix == "tender":
            row = conn.execute(sa.text("""
                SELECT id, title, buyer, voivodeship, value_pln, deadline_at, stage
                FROM tender
                WHERE id = :eid AND tenant_id = :tid
            """), {"eid": entity_id, "tid": tenant_id}).mappings().first()
            if row:
                d = dict(row)
                if d.get("deadline_at"):
                    d["deadline_at"] = d["deadline_at"].isoformat()
                return d
    return {}


def _log_event(tenant_id: str, event: str, entity_id: str, payload: dict) -> None:
    """Zapisz event do historii."""
    try:
        import json
        with get_engine().connect() as conn:
            conn.execute(sa.text("""
                INSERT INTO automation_event_log
                    (id, tenant_id, event, entity_id, triggered_by, triggered_at, payload, status)
                VALUES
                    (:id, :tid, :event, :eid, :by, NOW(), :payload, 'pending')
            """), {
                "id": str(uuid.uuid4()),
                "tid": tenant_id,
                "event": event,
                "eid": entity_id,
                "by": payload.get("triggered_by", "system"),
                "payload": json.dumps(payload, default=str),
            })
            conn.commit()
    except Exception as e:
        logger.exception(f"Failed to log event: {e}", exc_info=True)


async def _dispatch_webhooks(tenant_id: str, event: str, payload: dict) -> None:
    """Roześlij event do wszystkich pasujących webhooków (async, fire-and-forget)."""
    with get_engine().connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, url, secret FROM automation_webhook
            WHERE tenant_id = :tid AND active = true
            AND (events = '{}' OR :event = ANY(events))
        """), {"tid": tenant_id, "event": event}).mappings().all()

    if not rows:
        return

    import hashlib, hmac, json

    async with httpx.AsyncClient(timeout=10.0) as client:
        for wh in rows:
            headers = {"Content-Type": "application/json", "X-Terra-Event": event}
            if wh.secret:
                body_bytes = json.dumps(payload, default=str).encode()
                sig = hmac.new(wh.secret.encode(), body_bytes, hashlib.sha256).hexdigest()
                headers["X-Terra-Signature"] = sig

            try:
                resp = await client.post(wh.url, json=payload, headers=headers)
                _update_event_log(tenant_id, event, resp.status_code)
                logger.info(f"Webhook {wh.name} → {resp.status_code}")
            except Exception as e:
                logger.exception(f"Webhook {wh.id} failed: {e}", exc_info=True)
                _update_event_log(tenant_id, event, 0)


def _update_event_log(tenant_id: str, event: str, status_code: int) -> None:
    """Update last event log with response code."""
    try:
        with get_engine().connect() as conn:
            conn.execute(sa.text("""
                UPDATE automation_event_log
                SET status = :status, response_code = :code
                WHERE tenant_id = :tid AND event = :event
                AND id = (SELECT id FROM automation_event_log
                          WHERE tenant_id = :tid AND event = :event
                          ORDER BY triggered_at DESC LIMIT 1)
            """), {
                "tid": tenant_id,
                "event": event,
                "status": "delivered" if 200 <= status_code < 300 else "failed",
                "code": status_code,
            })
            conn.commit()
    except Exception:
        pass


# ─── n8n Integration Endpoints ────────────────────────────────────────────────

@router.get("/n8n/status")
def n8n_status(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Status lokalnego n8n — health, ilość workflow, aktywne webhooki."""
    try:
        from services.api.services.api.integrations.n8n_client import get_n8n_client
        client = get_n8n_client()
        health = client.health()
        workflows = client.list_workflows()
        active = [w for w in workflows if w.get("active")]
        webhooks = client.get_webhook_urls()
        return {
            "status": health.get("status", "unknown"),
            "workflows_total": len(workflows),
            "workflows_active": len(active),
            "webhooks": webhooks,
            "base_url": client.base_url,
        }
    except Exception as e:
        logger.exception("n8n_status failed: %s", e, exc_info=True)
        return {"status": "unavailable", "error": str(e)}


@router.get("/n8n/workflows")
def n8n_workflows(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """Lista workflow z n8n."""
    try:
        from services.api.services.api.integrations.n8n_client import get_n8n_client
        workflows = get_n8n_client().list_workflows()
        return [{
            "id": w["id"],
            "name": w["name"],
            "active": w.get("active", False),
            "nodes": len(w.get("nodes", [])),
            "created_at": w.get("createdAt"),
        } for w in workflows]
    except Exception as e:
        logger.exception("n8n list_workflows failed: %s", e, exc_info=True)
        return []


@router.post("/n8n/provision")
def n8n_provision_webhook(
    event: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Auto-provision: utwórz webhook workflow w n8n dla danego event type.
    Simply-clever: one-click i n8n jest gotowe do odbioru eventów.
    """
    try:
        from services.api.services.api.integrations.n8n_client import get_n8n_client
        client = get_n8n_client()
        result = client.provision_terra_webhook(event)
        return {"status": "provisioned", **result}
    except Exception as e:
        raise HTTPException(500, f"n8n provisioning failed: {e}")

