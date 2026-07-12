"""Faza 49 — Email Notifications: SMTP wysyłka, szablony.
Faza 50 — Webhook System: outgoing webhooks przy zmianie statusu.
"""
from __future__ import annotations


import hashlib
import hmac
import json
import uuid
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/email", tags=["email-notifications"])
webhook_router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATES: dict[str, dict[str, str]] = {
    "tender_status_changed": {
        "subject": "[YU-NA] Zmiana statusu przetargu: {tender_title}",
        "body": """
<html><body>
<h2 style="color:#1e40af">YU-NA — Zmiana statusu</h2>
<p>Przetarg <strong>{tender_title}</strong> zmienił status na: <strong>{new_status}</strong></p>
<p><a href="{tender_url}" style="color:#3b82f6">Przejdź do przetargu →</a></p>
<hr><p style="font-size:12px;color:#6b7280">YU-NA - System Zarządzania Przetargami</p>
</body></html>
""",
    },
    "new_comment": {
        "subject": "[YU-NA] Nowy komentarz: {tender_title}",
        "body": """
<html><body>
<h2 style="color:#1e40af">YU-NA — Nowy komentarz</h2>
<p><strong>{author}</strong> skomentował przetarg <strong>{tender_title}</strong>:</p>
<blockquote style="border-left:3px solid #3b82f6;padding:8px;color:#374151">{comment_body}</blockquote>
<p><a href="{tender_url}">Przejdź do przetargu →</a></p>
</body></html>
""",
    },
    "mention": {
        "subject": "[YU-NA] Wspomniano Cię w komentarzu",
        "body": """
<html><body>
<h2 style="color:#1e40af">YU-NA — @wzmianka</h2>
<p><strong>{author}</strong> wspomniał Cię w przetargu <strong>{tender_title}</strong>:</p>
<blockquote style="border-left:3px solid #3b82f6;padding:8px">{comment_body}</blockquote>
<p><a href="{tender_url}">Przejdź do przetargu →</a></p>
</body></html>
""",
    },
    "deadline_reminder": {
        "subject": "[YU-NA] Przypomnienie: termin za {days_left} dni — {tender_title}",
        "body": """
<html><body>
<h2 style="color:#dc2626">⚠ YU-NA — Zbliżający się termin</h2>
<p>Przetarg <strong>{tender_title}</strong> ma termin składania ofert za <strong>{days_left} dni</strong>.</p>
<p>Termin: <strong>{deadline}</strong></p>
<p><a href="{tender_url}">Przejdź do przetargu →</a></p>
</body></html>
""",
    },
}


class EmailConfigCreate(BaseModel):
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    from_email: str | None = None
    from_name: str = "YU-NA"
    enabled: bool = True


class SendEmailRequest(BaseModel):
    to_email: str
    template: str
    context: dict = {}


def _send_smtp_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str | None,
    smtp_pass: str | None,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """Send email via SMTP. Returns True on success."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
    try:
        server.ehlo()
        if smtp_port == 587:
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, [to_email], msg.as_string())
        return True
    finally:
        server.quit()


# ─── Email config endpoints ───────────────────────────────────────────────────

@router.post("/config")
def set_email_config(config: EmailConfigCreate, user: AuthUser) -> dict:
    """Skonfiguruj SMTP dla organizacji."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO email_configs
                    (id, org_id, smtp_host, smtp_port, smtp_user, smtp_pass, from_email, from_name, enabled)
                VALUES (:id, :org_id, :host, :port, :user, :pass, :from_email, :from_name, :enabled)
                ON CONFLICT (org_id) DO UPDATE SET
                    smtp_host = EXCLUDED.smtp_host,
                    smtp_port = EXCLUDED.smtp_port,
                    smtp_user = EXCLUDED.smtp_user,
                    smtp_pass = EXCLUDED.smtp_pass,
                    from_email = EXCLUDED.from_email,
                    from_name = EXCLUDED.from_name,
                    enabled = EXCLUDED.enabled
            """),
            {
                "id": str(uuid.uuid4()),
                "org_id": user.org_id or None,
                "host": config.smtp_host,
                "port": config.smtp_port,
                "user": config.smtp_user,
                "pass": config.smtp_pass,
                "from_email": config.from_email,
                "from_name": config.from_name,
                "enabled": config.enabled,
            },
        )
        conn.commit()
    return {"status": "saved", "org_id": user.org_id}


@router.get("/config")
def get_email_config(user: AuthUser) -> dict:
    """Pobierz konfigurację SMTP organizacji."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("""
                SELECT id, smtp_host, smtp_port, smtp_user, from_email, from_name, enabled
                FROM email_configs WHERE org_id = :org_id
            """),
            {"org_id": user.org_id or ""},
        ).fetchone()
    if not row:
        return {"configured": False}
    return {
        "configured": True,
        "smtp_host": row.smtp_host,
        "smtp_port": row.smtp_port,
        "smtp_user": row.smtp_user,
        "from_email": row.from_email,
        "from_name": row.from_name,
        "enabled": row.enabled,
    }


@router.post("/send")
def send_email(req: SendEmailRequest, background_tasks: BackgroundTasks, user: AuthUser) -> dict:
    """Wyślij e-mail używając szablonu."""
    if req.template not in TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Nieznany szablon. Dostępne: {list(TEMPLATES.keys())}",
        )
    template = TEMPLATES[req.template]
    try:
        subject = template["subject"].format(**req.context)
        body = template["body"].format(**req.context)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Brak parametru szablonu: {e}")

    engine = get_engine()
    with engine.connect() as conn:
        cfg = conn.execute(
            sa.text("SELECT * FROM email_configs WHERE org_id = :org_id"),
            {"org_id": user.org_id or ""},
        ).fetchone()

    log_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO email_logs (id, org_id, to_email, subject, template, status)
                VALUES (:id, :org_id, :to, :subj, :tmpl, 'queued')
            """),
            {
                "id": log_id,
                "org_id": user.org_id or None,
                "to": req.to_email,
                "subj": subject,
                "tmpl": req.template,
            },
        )
        conn.commit()

    if cfg and cfg.enabled:
        background_tasks.add_task(
            _send_email_bg,
            log_id,
            cfg.smtp_host, cfg.smtp_port, cfg.smtp_user, cfg.smtp_pass,
            cfg.from_email or "noreply@yu-na.local",
            cfg.from_name,
            req.to_email, subject, body,
        )
    return {
        "log_id": log_id,
        "template": req.template,
        "to": req.to_email,
        "status": "queued" if cfg else "no_smtp_configured",
    }


def _send_email_bg(
    log_id: str, smtp_host: str, smtp_port: int, smtp_user, smtp_pass,
    from_email: str, from_name: str, to_email: str, subject: str, body: str,
) -> None:
    engine = get_engine()
    try:
        _send_smtp_email(smtp_host, smtp_port, smtp_user, smtp_pass, from_email, from_name, to_email, subject, body)
        with engine.connect() as conn:
            conn.execute(
                sa.text("UPDATE email_logs SET status='sent', sent_at=now() WHERE id=:id"),
                {"id": log_id},
            )
            conn.commit()
    except Exception as exc:
        with engine.connect() as conn:
            conn.execute(
                sa.text("UPDATE email_logs SET status='failed', error=:err WHERE id=:id"),
                {"err": str(exc), "id": log_id},
            )
            conn.commit()


@router.get("/logs")
def list_email_logs(user: AuthUser, limit: int = Query(50)) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, to_email, subject, template, status, error, sent_at, created_at
                FROM email_logs
                ORDER BY created_at DESC LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()
    return {
        "items": [
            {
                "id": str(r.id),
                "to_email": r.to_email,
                "subject": r.subject,
                "template": r.template,
                "status": r.status,
                "error": r.error,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/templates")
def list_templates(user: AuthUser) -> dict:
    return {
        "templates": [
            {"name": k, "subject_template": v["subject"]}
            for k, v in TEMPLATES.items()
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK SYSTEM (Faza 50)
# ═══════════════════════════════════════════════════════════════════════════════

class WebhookCreate(BaseModel):
    name: str
    url: str
    secret: str | None = None
    events: list[str] = ["tender.status_changed"]
    enabled: bool = True


def fire_webhooks(event: str, payload: dict, org_id: str | None) -> None:
    """Fire all active webhooks for an event. Call in background task."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, url, secret FROM webhooks
                WHERE enabled = true
                  AND :event = ANY(events)
                  AND (org_id = :org_id OR org_id IS NULL)
            """),
            {"event": event, "org_id": org_id or ""},
        ).fetchall()

    for wh in rows:
        delivery_id = str(uuid.uuid4())
        body = json.dumps({"event": event, "data": payload, "id": delivery_id})
        headers = {"Content-Type": "application/json", "X-Terra-Event": event}

        if wh.secret:
            sig = hmac.new(wh.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Terra-Signature"] = f"sha256={sig}"

        status, code, resp_body, duration = "failed", None, None, 0
        start = time.monotonic()
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(wh.url, content=body, headers=headers)
                code = r.status_code
                resp_body = r.text[:500]
                duration = int((time.monotonic() - start) * 1000)
                status = "success" if 200 <= r.status_code < 300 else "failed"
        except Exception as e:
            resp_body = str(e)[:500]
            duration = int((time.monotonic() - start) * 1000)

        with engine.connect() as conn:
            conn.execute(
                sa.text("""
                    INSERT INTO webhook_deliveries
                        (id, webhook_id, event, payload, response_code, response_body, duration_ms, status)
                    VALUES (:id, :wh_id, :event, :payload::jsonb, :code, :body, :dur, :status)
                """),
                {
                    "id": delivery_id,
                    "wh_id": str(wh.id),
                    "event": event,
                    "payload": json.dumps(payload),
                    "code": code,
                    "body": resp_body,
                    "dur": duration,
                    "status": status,
                },
            )
            conn.execute(
                sa.text("UPDATE webhooks SET last_fired_at = now() WHERE id = :id"),
                {"id": str(wh.id)},
            )
            conn.commit()


@webhook_router.post("")
def create_webhook(wh: WebhookCreate, user: AuthUser) -> dict:
    """Utwórz nowy webhook."""
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO webhooks (id, org_id, name, url, secret, events, enabled)
                VALUES (:id, :org_id, :name, :url, :secret, :events, :enabled)
            """),
            {
                "id": rec_id,
                "org_id": user.org_id or None,
                "name": wh.name,
                "url": wh.url,
                "secret": wh.secret,
                "events": wh.events,
                "enabled": wh.enabled,
            },
        )
        conn.commit()
    return {"id": rec_id, "status": "created"}


@webhook_router.get("")
def list_webhooks(user: AuthUser) -> dict:
    """Lista webhooków organizacji."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, name, url, events, enabled, last_fired_at, created_at
                FROM webhooks
                ORDER BY created_at DESC
            """),
        ).fetchall()
    return {
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "url": r.url,
                "events": list(r.events) if r.events else [],
                "enabled": r.enabled,
                "last_fired_at": r.last_fired_at.isoformat() if r.last_fired_at else None,
            }
            for r in rows
        ]
    }


@webhook_router.delete("/{webhook_id}")
def delete_webhook(webhook_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM webhooks WHERE id = :id"), {"id": webhook_id})
        conn.commit()
    return {"status": "deleted"}


@webhook_router.post("/{webhook_id}/test")
def test_webhook(webhook_id: str, background_tasks: BackgroundTasks, user: AuthUser) -> dict:
    """Wyślij testowe zdarzenie do webhooka."""
    background_tasks.add_task(
        fire_webhooks,
        "webhook.test",
        {"message": "Test webhook delivery", "webhook_id": webhook_id},
        user.org_id,
    )
    return {"status": "fired", "webhook_id": webhook_id}


@webhook_router.get("/{webhook_id}/deliveries")
def webhook_deliveries(webhook_id: str, user: AuthUser, limit: int = Query(50)) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, event, response_code, duration_ms, status, created_at
                FROM webhook_deliveries
                WHERE webhook_id = :id
                ORDER BY created_at DESC LIMIT :limit
            """),
            {"id": webhook_id, "limit": limit},
        ).fetchall()
    return {
        "webhook_id": webhook_id,
        "deliveries": [
            {
                "id": str(r.id),
                "event": r.event,
                "response_code": r.response_code,
                "duration_ms": r.duration_ms,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
