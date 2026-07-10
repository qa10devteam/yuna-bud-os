"""Alert DLQ Retry Scheduler — BPMN Faza 1, Sprint 11.

Pobiera rekordy z `alert_failed` gdzie:
  - status = 'pending'
  - next_retry_at <= now() LUB next_retry_at IS NULL
  - attempts < MAX_ATTEMPTS

Dla każdego: próbuje ponownie wysłać SMTP.
  - sukces → status = 'resolved', resolved_at = now()
  - fail    → status = 'pending', attempts += 1, next_retry_at = now() + backoff
  - attempts >= MAX → status = 'dead'

Uruchomienie:
    python -m services.ingestion.alert_retry [--dry-run]

Systemd timer: terra-alert-retry.timer (co 15 min)
"""
from __future__ import annotations

import argparse
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

from .alert_runner import send_smtp

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BACKOFF_MINUTES = [5, 15, 60, 240, 1440]  # 5m, 15m, 1h, 4h, 24h

DEFAULT_DSN = os.getenv(
    "DATABASE_URL",
    "host=127.0.0.1 dbname=terraos user=terraos",
)


def _backoff_minutes(attempt: int) -> int:
    idx = min(attempt - 1, len(BACKOFF_MINUTES) - 1)
    return BACKOFF_MINUTES[idx]


def run_alert_retry(dsn: str = DEFAULT_DSN, dry_run: bool = False) -> dict:
    stats = {"processed": 0, "resolved": 0, "failed": 0, "dead": 0}

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch pending retries due now
            cur.execute("""
                SELECT id, alert_id, user_id, to_email, subject, html_body, text_body,
                       attempts, tenant_id
                FROM alert_failed
                WHERE status = 'pending'
                  AND (next_retry_at IS NULL OR next_retry_at <= now())
                  AND attempts < %s
                ORDER BY created_at ASC
                LIMIT 50
            """, (MAX_ATTEMPTS,))
            rows = cur.fetchall()

        logger.info("Alert DLQ: %d items due for retry", len(rows))

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        from_email = os.getenv("SMTP_FROM", "noreply@terra-os.qa10.io")
        from_name = os.getenv("SMTP_FROM_NAME", "Terra.OS")

        for row in rows:
            stats["processed"] += 1
            row_id = row["id"]
            attempts = row["attempts"]

            if dry_run:
                logger.info("[DRY-RUN] Would retry alert_failed id=%s to=%s", row_id, row["to_email"])
                continue

            ok = send_smtp(
                to_email=row["to_email"] or "",
                subject=row["subject"] or "",
                html=row["html_body"] or "",
                text=row["text_body"] or "",
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_pass=smtp_pass,
                from_email=from_email,
                from_name=from_name,
                max_retries=1,   # DLQ tries once per tick (outer loop controls cadence)
                retry_delay=0.5,
            )

            now = datetime.now(timezone.utc)
            with conn.cursor() as cur:
                if ok:
                    cur.execute("""
                        UPDATE alert_failed
                        SET status = 'resolved',
                            resolved_at = %s,
                            last_attempted_at = %s
                        WHERE id = %s
                    """, (now, now, row_id))
                    stats["resolved"] += 1
                    logger.info("DLQ resolved: id=%s alert=%s", row_id, row["alert_id"])
                else:
                    new_attempts = attempts + 1
                    if new_attempts >= MAX_ATTEMPTS:
                        cur.execute("""
                            UPDATE alert_failed
                            SET status = 'dead',
                                attempts = %s,
                                last_attempted_at = %s
                            WHERE id = %s
                        """, (new_attempts, now, row_id))
                        stats["dead"] += 1
                        logger.warning("DLQ dead: id=%s after %d attempts", row_id, new_attempts)
                    else:
                        backoff = _backoff_minutes(new_attempts)
                        next_retry = now + timedelta(minutes=backoff)
                        cur.execute("""
                            UPDATE alert_failed
                            SET attempts = %s,
                                last_attempted_at = %s,
                                next_retry_at = %s
                            WHERE id = %s
                        """, (new_attempts, now, next_retry, row_id))
                        stats["failed"] += 1
                        logger.info(
                            "DLQ retry failed (attempt %d/%d): id=%s — next: +%dm",
                            new_attempts, MAX_ATTEMPTS, row_id, backoff,
                        )
            conn.commit()

    finally:
        conn.close()

    logger.info("DLQ stats: %s", stats)
    return stats


def enqueue_failed_alert(
    conn,
    tenant_id: str,
    alert_id: str,
    user_id: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    error_msg: str = "",
) -> str:
    """Insert failed alert into DLQ. Returns new row id."""
    row_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    next_retry = now + timedelta(minutes=BACKOFF_MINUTES[0])

    conn.execute(
        __import__("sqlalchemy").text("""
            INSERT INTO alert_failed
              (id, tenant_id, alert_id, user_id, to_email, subject, html_body, text_body,
               error_msg, attempts, next_retry_at, created_at, status)
            VALUES
              (:id, :tid, :aid, :uid, :email, :subj, :html, :text,
               :err, 1, :next_retry, :created, 'pending')
        """),
        {
            "id": row_id, "tid": tenant_id, "aid": alert_id, "uid": user_id,
            "email": to_email, "subj": subject, "html": html_body, "text": text_body,
            "err": error_msg, "next_retry": next_retry, "created": now,
        },
    )
    return row_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Alert DLQ Retry Scheduler")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    args = parser.parse_args()
    run_alert_retry(dsn=args.dsn, dry_run=args.dry_run)
