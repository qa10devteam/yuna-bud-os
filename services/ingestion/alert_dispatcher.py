"""Faza 19 — Alert Dispatcher: sprawdza nowe przetargi i wysyła email alerty.

Funkcja główna:
    check_new_tenders_for_alerts(since_minutes=60)

Logika:
  1. Pobierz wszystkie aktywne alerty (is_active=true)
  2. Dla każdego alertu znajdź przetargi opublikowane w ciągu ostatnich `since_minutes` minut
  3. Filtruj po: cpv_prefixes, provinces (voivodeship), value range, keywords, match_score
  4. Wyślij email przez SMTP (jeśli SMTP_HOST skonfigurowany)
     → fallback: zapisz do /tmp/terra_alerts_pending.json i zaloguj

Uruchomienie:
    python -m services.ingestion.alert_dispatcher [--since-minutes 60] [--dry-run]

Używa istniejącej infrastruktury z alert_runner.py.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from .alert_runner import (
    Alert,
    MatchedTender,
    build_html_digest,
    build_text_digest,
    deliver_alert,
    fetch_active_alerts,
    log_email_sent,
    send_smtp,
    update_last_fired,
)

logger = logging.getLogger(__name__)

DEFAULT_DSN = os.getenv(
    "DATABASE_URL",
    "host=127.0.0.1 dbname=terraos user=terraos",
)
FALLBACK_JSON = os.getenv("ALERT_FALLBACK_FILE", "/tmp/terra_alerts_pending.json")
MIN_SCORE_DEFAULT = float(os.getenv("ALERT_MIN_SCORE", "0.0"))


# ─────────────────────────────── DB helpers ───────────────────────────────── #


def _match_tenders_since(
    conn,
    alert: Alert,
    since: datetime,
    min_score: float = 0.0,
) -> list[MatchedTender]:
    """Return tenders from `tender` table that match alert criteria since `since`.

    Filters:
      - tenant_id (multi-tenant isolation)
      - published_at >= since  (nowe przetargi)
      - cpv_prefixes (LIKE ANY)
      - provinces / voivodeship
      - value_min / value_max
      - keywords (ILIKE)
      - match_score >= min_score  (opcjonalnie)
      - status != 'archived'
    """
    where = [
        "t.tenant_id = %s",
        "t.published_at >= %s",
        "t.status != 'archived'",
    ]
    params: list[Any] = [alert.tenant_id, since]

    # CPV prefix filter
    if alert.cpv_prefixes:
        where.append("""
            EXISTS (
                SELECT 1 FROM unnest(t.cpv) AS c
                WHERE c LIKE ANY(%s::text[])
            )
        """)
        params.append([p + "%" for p in alert.cpv_prefixes])

    # Province / voivodeship filter
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
        kw_conds = " OR ".join(["lower(t.title) LIKE %s"] * len(alert.keywords))
        where.append(f"({kw_conds})")
        params.extend([f"%{kw.lower()}%" for kw in alert.keywords])

    # Minimum match_score threshold
    if min_score > 0.0:
        where.append("(t.match_score IS NULL OR t.match_score >= %s)")
        params.append(min_score)

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

    return [
        MatchedTender(
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
        )
        for r in rows
    ]


def _get_user_email(conn, user_id: str | None, tenant_id: str) -> str | None:
    """Resolve recipient email: user → org admin fallback."""
    if user_id:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    # Fallback: first org admin
    with conn.cursor() as cur:
        cur.execute(
            "SELECT email FROM users WHERE org_id = %s ORDER BY created_at LIMIT 1",
            (tenant_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


# ─────────────────────────────── Fallback writer ─────────────────────────── #


def _write_fallback_json(
    alert: Alert,
    to_email: str,
    tenders: list[MatchedTender],
    since: datetime,
) -> None:
    """Append pending alert to /tmp fallback JSON file when SMTP not configured."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "alert_id": alert.id,
        "alert_name": alert.name,
        "tenant_id": alert.tenant_id,
        "to_email": to_email,
        "since": since.isoformat(),
        "tenders_count": len(tenders),
        "tenders": [
            {
                "id": t.id,
                "title": t.title,
                "buyer": t.buyer,
                "value_pln": t.value_pln,
                "voivodeship": t.voivodeship,
                "published_at": t.published_at.isoformat() if t.published_at else None,
                "url": t.url,
                "match_score": t.match_score,
            }
            for t in tenders
        ],
    }
    try:
        existing: list[dict] = []
        if os.path.exists(FALLBACK_JSON):
            with open(FALLBACK_JSON) as f:
                try:
                    existing = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    existing = []
        existing.append(entry)
        with open(FALLBACK_JSON, "w") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info(
            "[FALLBACK] Alert '%s' → %s (%d przetargów) zapisano do %s",
            alert.name, to_email, len(tenders), FALLBACK_JSON,
        )
    except OSError as exc:
        logger.error("Nie można zapisać fallback JSON: %s", exc)


# ─────────────────────────────── Dispatch one alert ──────────────────────── #


def _dispatch_alert(
    conn,
    alert: Alert,
    tenders: list[MatchedTender],
    since: datetime,
    dry_run: bool = False,
) -> bool:
    """Send email for one alert or write fallback. Returns True on success."""
    to_email = _get_user_email(conn, alert.user_id, alert.tenant_id)
    if not to_email:
        logger.warning("Alert '%s': brak adresu email odbiorcy — pomijam", alert.name)
        return False

    subject = f"Terra.OS Zwiad: {len(tenders)} nowych przetargów — {alert.name}"
    html = build_html_digest(alert, tenders, since)
    text = build_text_digest(alert, tenders, since)

    if dry_run:
        logger.info(
            "[DRY-RUN] Alert='%s' to=%s tenders=%d",
            alert.name, to_email, len(tenders),
        )
        preview = f"/tmp/terra_alert_preview_{alert.id[:8]}.html"
        with open(preview, "w") as f:
            f.write(html)
        logger.info("[DRY-RUN] HTML preview saved: %s", preview)
        return True

    smtp_host = os.getenv("SMTP_HOST", "")
    if not smtp_host:
        # Fallback: write to JSON file
        logger.info(
            "SMTP_HOST nie skonfigurowany — zapisuję alert '%s' do fallback JSON",
            alert.name,
        )
        _write_fallback_json(alert, to_email, tenders, since)
        return True

    # SMTP delivery
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


# ─────────────────────────────── Main entry point ────────────────────────── #


def check_new_tenders_for_alerts(
    since_minutes: int = 60,
    db_dsn: str = DEFAULT_DSN,
    tenant_id: str | None = None,
    min_score: float = MIN_SCORE_DEFAULT,
    dry_run: bool = False,
) -> dict:
    """Sprawdź nowe przetargi z ostatnich `since_minutes` minut i wyślij emaile.

    Args:
        since_minutes: Okno czasowe wstecz (domyślnie 60 min).
        db_dsn:        DSN PostgreSQL.
        tenant_id:     Ogranicz do jednego tenanta (None = wszyscy).
        min_score:     Minimalne match_score przetargu (0.0 = bez filtra).
        dry_run:       Nie wysyłaj emaili, tylko zapisz HTML preview.

    Returns:
        Słownik statystyk: alerts_checked, alerts_fired, emails_sent, tenders_found, skipped.
    """
    stats = {
        "alerts_checked": 0,
        "alerts_fired": 0,
        "emails_sent": 0,
        "tenders_found": 0,
        "skipped": 0,
        "since_minutes": since_minutes,
    }

    since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    logger.info(
        "Alert dispatcher: szukam przetargów od %s (ostatnie %d min)",
        since.isoformat(), since_minutes,
    )

    try:
        conn = psycopg2.connect(db_dsn)
    except Exception as exc:
        logger.error("Nie można połączyć z bazą: %s", exc)
        raise

    try:
        alerts = fetch_active_alerts(conn, tenant_id=tenant_id)
        stats["alerts_checked"] = len(alerts)
        logger.info("Aktywnych alertów: %d", len(alerts))

        for alert in alerts:
            logger.debug("Sprawdzam alert '%s' (tenant=%s)", alert.name, alert.tenant_id)
            tenders = _match_tenders_since(conn, alert, since, min_score=min_score)
            stats["tenders_found"] += len(tenders)

            if not tenders:
                logger.info(
                    "Alert '%s': 0 nowych przetargów od %s — pomijam",
                    alert.name, since.strftime("%Y-%m-%d %H:%M"),
                )
                stats["skipped"] += 1
                continue

            logger.info(
                "Alert '%s': %d nowych przetargów → wysyłam digest",
                alert.name, len(tenders),
            )
            ok = _dispatch_alert(conn, alert, tenders, since, dry_run=dry_run)

            if ok:
                stats["emails_sent"] += 1
                stats["alerts_fired"] += 1
                if not dry_run:
                    update_last_fired(conn, alert.id)
                    conn.commit()

    except Exception as exc:
        logger.error("Alert dispatcher błąd: %s", exc)
        conn.rollback()
        raise
    finally:
        conn.close()

    logger.info("Alert dispatcher zakończony: %s", stats)
    return stats


# ─────────────────────────── S59: KRS 30-day refresh ────────────────────── #

def refresh_krs_stale_buyers(db_dsn: str = DEFAULT_DSN) -> dict:
    """S59: Co 30 dni odświeżaj dane KRS dla buyer_crm ze starym last_verified_at."""
    conn = psycopg2.connect(db_dsn)
    refreshed = 0
    errors = 0
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, buyer_nip, tenant_id
                FROM buyer_crm
                WHERE last_verified_at IS NULL
                   OR last_verified_at < now() - interval '30 days'
                LIMIT 50
            """)
            rows = cur.fetchall()

        for row in rows:
            nip = row["buyer_nip"]
            try:
                import httpx
                r = httpx.get(
                    f"https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/podmiot/nip/{nip}",
                    headers={"Accept": "application/json"}, timeout=10,
                )
                name = ""
                if r.status_code == 200:
                    d = r.json()
                    name = d.get("odpis", {}).get("dane", {}).get("dzialy", {}).get("dzial1", {}).get("danePodmiotu", {}).get("nazwa", "")
                with conn.cursor() as cur2:
                    cur2.execute(
                        "UPDATE buyer_crm SET last_verified_at = now(), notes = COALESCE(%s, notes) WHERE id = %s",
                        (name or None, str(row["id"])),
                    )
                    conn.commit()
                refreshed += 1
            except Exception as exc:
                errors += 1
                logger.debug("KRS refresh failed for NIP %s: %s", nip, exc)
    finally:
        conn.close()
    logger.info("S59 KRS refresh: %d refreshed, %d errors", refreshed, errors)
    return {"refreshed": refreshed, "errors": errors}


# ─────────────────────────────── CLI ──────────────────────────────────────── #

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Terra.OS alert dispatcher — nowe przetargi")
    parser.add_argument(
        "--since-minutes", type=int, default=60,
        help="Sprawdź przetargi z ostatnich N minut (domyślnie 60)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Nie wysyłaj emaili, zapisz HTML preview do /tmp/",
    )
    parser.add_argument("--tenant-id", help="Ogranicz do jednego tenanta (UUID)")
    parser.add_argument("--min-score", type=float, default=0.0, help="Min match_score [0.0-1.0]")
    parser.add_argument("--db-dsn", default=DEFAULT_DSN)
    args = parser.parse_args()

    result = check_new_tenders_for_alerts(
        since_minutes=args.since_minutes,
        db_dsn=args.db_dsn,
        tenant_id=args.tenant_id,
        min_score=args.min_score,
        dry_run=args.dry_run,
    )
    print("Stats:", json.dumps(result, indent=2))
