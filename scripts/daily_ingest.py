#!/usr/bin/env python3
"""Daily BZP ingest — standalone script for systemd timer.

Fetches yesterday's + today's tenders from BZP API and upserts into DB.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta

# Paths — same as terra-api.service
sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/services")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/shared")
sys.path.insert(0, "/home/ubuntu/terra-os/services/ingestion")

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/ubuntu/terra-os/logs/ingest.log"),
    ],
)
logger = logging.getLogger("daily_ingest")


def _notify_slack_failure(message: str) -> None:
    """Send a failure alert to Slack if SLACK_WEBHOOK_URL is configured (optional)."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        import requests
        requests.post(
            webhook_url,
            json={"text": message},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Failed to send Slack alert: %s", exc)


def main() -> None:
    days_back = int(os.getenv("INGEST_DAYS_BACK", "2"))
    include_ted = os.getenv("INGEST_INCLUDE_TED", "true").lower() == "true"
    include_bip = os.getenv("INGEST_INCLUDE_BIP", "false").lower() == "true"
    bip_region = os.getenv("INGEST_BIP_REGION") or None          # e.g. "slaskie"
    bip_max_sites = int(os.getenv("INGEST_BIP_MAX_SITES", "50"))
    logger.info(
        "Starting daily ingest (days_back=%d, ted=%s, bip=%s, bip_region=%s)",
        days_back, include_ted, include_bip, bip_region,
    )

    try:
        from terra_db.session import get_engine
        from ingestion.pipeline import run_ingest

        engine = get_engine()
        result = run_ingest(
            engine=engine,
            days_back=days_back,
            offline=False,
            include_ted=include_ted,
            include_bip=include_bip,
            bip_region=bip_region,
            bip_max_sites=bip_max_sites,
        )
    except Exception as exc:
        error_msg = f":rotating_light: *Terra daily ingest FAILED*\n```{exc}```"
        logger.error("Ingest pipeline failed: %s", exc)
        _notify_slack_failure(error_msg)
        raise

    logger.info(
        "Ingest complete: fetched=%d, created=%d, updated=%d, dropped=%d, errors=%d",
        result.raw_fetched,
        result.created,
        result.updated,
        result.dropped_filter,
        result.errors,
    )

    if result.errors:
        _notify_slack_failure(
            f":warning: *Terra ingest completed with errors*\n"
            f"fetched={result.raw_fetched}, created={result.created}, "
            f"updated={result.updated}, errors={result.errors}"
        )

    # Faza 19 — Alert Dispatcher: wyślij emaile dla nowych przetargów
    _run_alert_dispatcher()


def _run_alert_dispatcher() -> None:
    """Uruchom alert dispatcher po ingresie — sprawdź przetargi z ostatnich 25 godzin.

    Używamy 25h (nie 24h) jako margines bezpieczeństwa na wypadek opóźnień.
    """
    logger.info("Starting alert dispatcher (post-ingest)...")
    try:
        from ingestion.alert_dispatcher import check_new_tenders_for_alerts

        db_dsn = (
            f"host={os.getenv('DB_HOST', '127.0.0.1')} "
            f"port={os.getenv('DB_PORT', '5432')} "
            f"dbname={os.getenv('DB_NAME', 'terraos')} "
            f"user={os.getenv('DB_USER', 'terraos')}"
        )
        stats = check_new_tenders_for_alerts(since_minutes=25 * 60, db_dsn=db_dsn)
        logger.info(
            "Alert dispatcher done: checked=%d fired=%d emails=%d tenders=%d",
            stats["alerts_checked"],
            stats["alerts_fired"],
            stats["emails_sent"],
            stats["tenders_found"],
        )
    except Exception as exc:
        # Nie przerywamy ingresu z powodu błędu alertów
        logger.error("Alert dispatcher error (non-fatal): %s", exc)


if __name__ == "__main__":
    main()
