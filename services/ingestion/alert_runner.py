"""Faza 19 — Alert email runner: wysyłka digestu nowych przetargów.

Uruchomienie:
    python -m services.ingestion.alert_runner [--dry-run] [--tenant-id UUID]

Celery task: fire_tender_alerts (queue=normal, schedule=hourly)

Logika:
  1. Pobierz aktywne alerty (tender_alert WHERE is_active=true)
  2. Dla każdego alertu: dopasuj przetargi z tender dodane od last_fired_at
  3. Zbuduj HTML digest (do 20 przetargów per email)
  4. Wyślij SMTP lub zapisz do email_logs
  5. Ustaw last_fired_at = NOW()
"""
from __future__ import annotations

import argparse
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from uuid import UUID

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

DEFAULT_DSN = "host=127.0.0.1 dbname=terraos user=terraos"
APP_URL = os.getenv("APP_URL", "https://terra-os.qa10.io")


# ─────────────────────────────── Data classes ─────────────────────────────── #

@dataclass
class Alert:
    id: str
    tenant_id: str
    user_id: str | None
    name: str
    cpv_prefixes: list[str]
    provinces: list[str]
    keywords: list[str]
    value_min: float | None
    value_max: float | None
    notice_types: list[str]
    buyer_nips: list[str]
    frequency: str
    channel: str
    webhook_url: str | None
    last_fired_at: datetime | None


@dataclass
class MatchedTender:
    id: str
    title: str
    buyer: str | None
    cpv: list[str]
    voivodeship: str | None
    value_pln: float | None
    deadline_at: datetime | None
    published_at: datetime | None
    url: str | None
    match_score: float | None
    source: str


# ─────────────────────────────── DB queries ───────────────────────────────── #

def fetch_active_alerts(
    conn,
    tenant_id: str | None = None,
    frequency: str | None = None,
) -> list[Alert]:
    """Return active alerts, optionally filtered by tenant and frequency."""
    where = ["a.is_active = true"]
    params: list[Any] = []
    if tenant_id:
        where.append("a.tenant_id = %s")
        params.append(tenant_id)
    if frequency:
        where.append("a.frequency = %s")
        params.append(frequency)

    sql = f"""
        SELECT
            a.id, a.tenant_id, a.user_id, a.name,
            a.cpv_prefixes, a.provinces, a.keywords,
            a.value_min, a.value_max, a.notice_types, a.buyer_nips,
            a.frequency, a.channel, a.webhook_url, a.last_fired_at
        FROM tender_alert a
        WHERE {' AND '.join(where)}
        ORDER BY a.tenant_id, a.created_at
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    alerts = []
    for r in rows:
        alerts.append(Alert(
            id=str(r["id"]),
            tenant_id=str(r["tenant_id"]),
            user_id=str(r["user_id"]) if r["user_id"] else None,
            name=r["name"],
            cpv_prefixes=r["cpv_prefixes"] or [],
            provinces=r["provinces"] or [],
            keywords=r["keywords"] or [],
            value_min=float(r["value_min"]) if r["value_min"] else None,
            value_max=float(r["value_max"]) if r["value_max"] else None,
            notice_types=r["notice_types"] or [],
            buyer_nips=r["buyer_nips"] or [],
            frequency=r["frequency"],
            channel=r["channel"],
            webhook_url=r["webhook_url"],
            last_fired_at=r["last_fired_at"],
        ))
    return alerts


def match_tenders(conn, alert: Alert, since: datetime) -> list[MatchedTender]:
    """Return tenders matching the alert criteria published since `since`."""
    where = [
        "t.tenant_id = %s",
        "t.published_at >= %s",
        "t.status != 'archived'",
    ]
    params: list[Any] = [alert.tenant_id, since]

    # CPV filter
    if alert.cpv_prefixes:
        # Match if any CPV in tender starts with any prefix in alert
        where.append("""
            EXISTS (
                SELECT 1 FROM unnest(t.cpv) AS c
                WHERE c LIKE ANY(%s::text[])
            )
        """)
        params.append([p + "%" for p in alert.cpv_prefixes])

    # Province/voivodeship filter
    if alert.provinces:
        where.append("t.voivodeship = ANY(%s)")
        params.append(alert.provinces)

    # Value range
    if alert.value_min is not None:
        where.append("(t.value_pln IS NULL OR t.value_pln >= %s)")
        params.append(alert.value_min)
    if alert.value_max is not None:
        where.append("(t.value_pln IS NULL OR t.value_pln <= %s)")
        params.append(alert.value_max)

    # Keywords (full-text in title)
    if alert.keywords:
        kw_conditions = " OR ".join(["lower(t.title) LIKE %s"] * len(alert.keywords))
        where.append(f"({kw_conditions})")
        params.extend([f"%{kw.lower()}%" for kw in alert.keywords])

    sql = f"""
        SELECT
            t.id, t.title, t.buyer, t.cpv, t.voivodeship,
            t.value_pln, t.deadline_at, t.published_at, t.url,
            t.match_score, t.source
        FROM tender t
        WHERE {' AND '.join(where)}
        ORDER BY t.match_score DESC NULLS LAST, t.published_at DESC
        LIMIT 20
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    tenders = []
    for r in rows:
        tenders.append(MatchedTender(
            id=str(r["id"]),
            title=r["title"],
            buyer=r["buyer"],
            cpv=r["cpv"] or [],
            voivodeship=r["voivodeship"],
            value_pln=float(r["value_pln"]) if r["value_pln"] else None,
            deadline_at=r["deadline_at"],
            published_at=r["published_at"],
            url=r["url"],
            match_score=float(r["match_score"]) if r["match_score"] else None,
            source=r["source"],
        ))
    return tenders


def get_user_email(conn, user_id: str | None, tenant_id: str) -> str | None:
    """Get email address for the alert recipient."""
    if not user_id:
        # Fall back to first org admin email
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email FROM users WHERE org_id = %s ORDER BY created_at LIMIT 1",
                (tenant_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    with conn.cursor() as cur:
        cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None


def update_last_fired(conn, alert_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE tender_alert SET last_fired_at = now(), total_fired = total_fired + 1 WHERE id = %s",
            (alert_id,),
        )


def log_email_sent(
    conn,
    org_id: str,
    to_email: str,
    subject: str,
    template: str,
    status: str = "sent",
    error: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO email_logs (org_id, to_email, subject, template, status, error, sent_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            """,
            (org_id, to_email, subject, template, status, error),
        )


# ─────────────────────────────── Email builder ────────────────────────────── #

def _fmt_value(v: float | None) -> str:
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f} mln PLN"
    return f"{v / 1_000:.0f} tys. PLN"


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y")


def _fmt_score(s: float | None) -> str:
    if s is None:
        return ""
    pct = int(s * 100)
    if pct >= 70:
        color = "#16a34a"
    elif pct >= 40:
        color = "#d97706"
    else:
        color = "#6b7280"
    return f'<span style="color:{color};font-weight:600">{pct}%</span>'


def build_html_digest(alert: Alert, tenders: list[MatchedTender], since: datetime) -> str:
    """Build HTML email digest for a list of matched tenders."""
    tender_rows = ""
    for t in tenders:
        url = t.url or f"{APP_URL}/zwiad/{t.id}"
        cpv_str = ", ".join(t.cpv[:3]) if t.cpv else "—"
        score_str = _fmt_score(t.match_score)
        deadline_str = _fmt_date(t.deadline_at)
        value_str = _fmt_value(t.value_pln)
        region = t.voivodeship or "—"

        tender_rows += f"""
        <tr>
          <td style="padding:12px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top">
            <a href="{url}" style="color:#1e40af;text-decoration:none;font-weight:500;font-size:14px">{t.title[:120]}</a>
            <div style="color:#64748b;font-size:12px;margin-top:4px">{t.buyer or 'Nieznany zamawiający'}</div>
          </td>
          <td style="padding:12px 8px;border-bottom:1px solid #f1f5f9;text-align:center;font-size:13px;white-space:nowrap">{score_str}</td>
          <td style="padding:12px 8px;border-bottom:1px solid #f1f5f9;font-size:13px;white-space:nowrap">{value_str}</td>
          <td style="padding:12px 8px;border-bottom:1px solid #f1f5f9;font-size:13px;white-space:nowrap">{deadline_str}</td>
          <td style="padding:12px 8px;border-bottom:1px solid #f1f5f9;font-size:12px;color:#64748b">{region}</td>
        </tr>
        """

    since_str = _fmt_date(since)
    count = len(tenders)
    plural = "przetarg" if count == 1 else ("przetargi" if 2 <= count <= 4 else "przetargów")

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:700px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);padding:32px;color:#fff">
    <div style="font-size:22px;font-weight:700;margin-bottom:4px">Terra.OS Zwiad</div>
    <div style="font-size:14px;opacity:.85">Alert: <strong>{alert.name}</strong></div>
    <div style="font-size:13px;opacity:.7;margin-top:4px">Nowe przetargi od {since_str}</div>
  </div>

  <!-- Summary badge -->
  <div style="background:#eff6ff;padding:16px 32px;border-bottom:1px solid #dbeafe">
    <span style="font-size:16px;font-weight:600;color:#1e40af">{count} nowych {plural}</span>
    <span style="font-size:13px;color:#64748b;margin-left:12px">dopasowanych do Twoich kryteriów</span>
  </div>

  <!-- Table -->
  <div style="padding:0 24px 24px">
    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <thead>
        <tr style="background:#f8fafc">
          <th style="padding:10px 8px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0">Przetarg</th>
          <th style="padding:10px 8px;text-align:center;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0">Dopasowanie</th>
          <th style="padding:10px 8px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0">Wartość</th>
          <th style="padding:10px 8px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0">Deadline</th>
          <th style="padding:10px 8px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0">Region</th>
        </tr>
      </thead>
      <tbody>
        {tender_rows}
      </tbody>
    </table>
  </div>

  <!-- CTA -->
  <div style="padding:16px 32px;text-align:center;border-top:1px solid #f1f5f9">
    <a href="{APP_URL}/zwiad" style="display:inline-block;background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
      Otwórz Zwiad →
    </a>
  </div>

  <!-- Footer -->
  <div style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center">
    <div style="font-size:12px;color:#94a3b8">
      Terra.OS &middot; Zarządzasz alertami w
      <a href="{APP_URL}/settings/alerts" style="color:#2563eb">ustawieniach</a>
    </div>
  </div>

</div>
</body>
</html>"""
    return html


def build_text_digest(alert: Alert, tenders: list[MatchedTender], since: datetime) -> str:
    """Plain-text fallback."""
    lines = [
        f"Terra.OS Zwiad — Alert: {alert.name}",
        f"Nowe przetargi od {_fmt_date(since)}",
        f"Znaleziono: {len(tenders)} przetargów",
        "",
    ]
    for i, t in enumerate(tenders, 1):
        url = t.url or f"{APP_URL}/zwiad/{t.id}"
        lines.append(f"{i}. {t.title}")
        lines.append(f"   Zamawiający: {t.buyer or '—'}")
        lines.append(f"   Wartość: {_fmt_value(t.value_pln)} | Deadline: {_fmt_date(t.deadline_at)}")
        lines.append(f"   Link: {url}")
        lines.append("")
    lines.append(f"Zarządzaj alertami: {APP_URL}/settings/alerts")
    return "\n".join(lines)


# ─────────────────────────────── Delivery ─────────────────────────────────── #

def send_smtp(
    to_email: str,
    subject: str,
    html: str,
    text: str,
    smtp_host: str = "",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_pass: str = "",
    from_email: str = "noreply@terra-os.qa10.io",
    from_name: str = "Terra.OS",
) -> bool:
    """Send email via SMTP. Returns True on success."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    if not smtp_host:
        logger.info("[EMAIL-DRY] To=%s | Subject=%s", to_email, subject)
        return True

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=ctx)
            if smtp_user:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())
        logger.info("Email sent: to=%s subject=%s", to_email, subject)
        return True
    except Exception as exc:
        logger.error("SMTP error: %s", exc)
        return False


def deliver_alert(
    conn,
    alert: Alert,
    tenders: list[MatchedTender],
    since: datetime,
    dry_run: bool = False,
) -> bool:
    """Dispatch email (or log in dry-run). Returns True on success."""
    to_email = get_user_email(conn, alert.user_id, alert.tenant_id)
    if not to_email:
        logger.warning("Alert %s: no recipient email found, skipping", alert.id)
        return False

    subject = f"Terra.OS Zwiad: {len(tenders)} nowych przetargów — {alert.name}"
    html = build_html_digest(alert, tenders, since)
    text = build_text_digest(alert, tenders, since)

    if dry_run:
        logger.info("[DRY-RUN] Alert=%s to=%s tenders=%d", alert.name, to_email, len(tenders))
        # Save HTML to tmp for preview
        preview_path = f"/tmp/terra_alert_{alert.id[:8]}.html"
        with open(preview_path, "w") as f:
            f.write(html)
        logger.info("[DRY-RUN] HTML preview: %s", preview_path)
        return True

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_email = os.getenv("SMTP_FROM", "noreply@terra-os.qa10.io")
    from_name = os.getenv("SMTP_FROM_NAME", "Terra.OS")

    ok = send_smtp(
        to_email=to_email,
        subject=subject,
        html=html,
        text=text,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
        from_email=from_email,
        from_name=from_name,
    )

    status = "sent" if ok else "failed"
    log_email_sent(conn, alert.tenant_id, to_email, subject, "tender_alert_digest", status)
    return ok


# ─────────────────────────────── Main runner ──────────────────────────────── #

def _should_fire(alert: Alert) -> bool:
    """Check if alert should fire based on frequency and last_fired_at."""
    if alert.frequency == "instant":
        return True
    now = datetime.now(timezone.utc)
    if alert.last_fired_at is None:
        return True
    lf = alert.last_fired_at
    if lf.tzinfo is None:
        lf = lf.replace(tzinfo=timezone.utc)
    elapsed = now - lf
    if alert.frequency == "daily" and elapsed >= timedelta(hours=20):
        return True
    if alert.frequency == "weekly" and elapsed >= timedelta(days=6):
        return True
    return False


def run_alert_runner(
    db_dsn: str = DEFAULT_DSN,
    tenant_id: str | None = None,
    frequency: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Main entry point — runs all eligible alerts."""
    conn = psycopg2.connect(db_dsn)
    stats = {"alerts_checked": 0, "alerts_fired": 0, "emails_sent": 0, "tenders_found": 0, "skipped": 0}

    try:
        alerts = fetch_active_alerts(conn, tenant_id=tenant_id, frequency=frequency)
        stats["alerts_checked"] = len(alerts)
        logger.info("Active alerts: %d", len(alerts))

        for alert in alerts:
            if not _should_fire(alert):
                stats["skipped"] += 1
                logger.debug("Alert %s: not due yet (freq=%s)", alert.name, alert.frequency)
                continue

            # Determine since window
            now = datetime.now(timezone.utc)
            if alert.last_fired_at:
                since = alert.last_fired_at
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
            else:
                # First run: look back based on frequency
                lookback = {"instant": 1, "daily": 1, "weekly": 7}
                since = now - timedelta(days=lookback.get(alert.frequency, 1))

            tenders = match_tenders(conn, alert, since)
            stats["tenders_found"] += len(tenders)

            if not tenders:
                logger.info("Alert '%s': 0 new tenders since %s — skip", alert.name, since.date())
                if not dry_run:
                    update_last_fired(conn, alert.id)
                    conn.commit()
                continue

            logger.info("Alert '%s': %d new tenders → sending digest", alert.name, len(tenders))
            ok = deliver_alert(conn, alert, tenders, since, dry_run=dry_run)

            if ok:
                stats["emails_sent"] += 1
                stats["alerts_fired"] += 1
                if not dry_run:
                    update_last_fired(conn, alert.id)
                    conn.commit()

    except Exception as exc:
        logger.error("Alert runner error: %s", exc)
        conn.rollback()
        raise
    finally:
        conn.close()

    logger.info("Alert runner done: %s", stats)
    return stats


# ─────────────────────────────── CLI ──────────────────────────────────────── #

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Terra.OS alert email runner")
    parser.add_argument("--dry-run", action="store_true", help="Don't send emails, generate HTML previews")
    parser.add_argument("--tenant-id", help="Run only for specific tenant")
    parser.add_argument("--frequency", choices=["instant", "daily", "weekly"], help="Filter by frequency")
    parser.add_argument("--db-dsn", default=DEFAULT_DSN)
    args = parser.parse_args()

    stats = run_alert_runner(
        db_dsn=args.db_dsn,
        tenant_id=args.tenant_id,
        frequency=args.frequency,
        dry_run=args.dry_run,
    )
    print("Stats:", stats)
