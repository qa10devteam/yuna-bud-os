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


def main() -> None:
    days_back = int(os.getenv("INGEST_DAYS_BACK", "2"))
    include_ted = os.getenv("INGEST_INCLUDE_TED", "true").lower() == "true"
    logger.info("Starting daily ingest (days_back=%d, ted=%s)", days_back, include_ted)

    from terra_db.session import get_engine
    from ingestion.pipeline import run_ingest

    engine = get_engine()
    result = run_ingest(engine=engine, days_back=days_back, offline=False, include_ted=include_ted)

    logger.info(
        "Ingest complete: fetched=%d, created=%d, updated=%d, dropped=%d, errors=%d",
        result.raw_fetched,
        result.created,
        result.updated,
        result.dropped_filter,
        result.errors,
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
