#!/usr/bin/env python3
"""Terra.OS — Alert Dispatcher runner script.

Uruchamia check_new_tenders_for_alerts() z alertami z ostatniej godziny.

Użycie:
    python scripts/run_alert_dispatcher.py
    python scripts/run_alert_dispatcher.py --since-minutes 30 --dry-run
    python scripts/run_alert_dispatcher.py --since-minutes 1440  # 24h lookback

Systemd timer:
    Patrz: /etc/systemd/system/terra-alert-dispatcher.service
           /etc/systemd/system/terra-alert-dispatcher.timer
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Path setup — identyczny jak daily_ingest.py
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

LOG_DIR = "/home/ubuntu/terra-os/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # systemd journal (gdy uruchamiany przez systemd)
        logging.FileHandler(f"{LOG_DIR}/alert_dispatcher.log"),
    ],
)
logger = logging.getLogger("run_alert_dispatcher")

DEFAULT_DSN = (
    f"host={os.getenv('DB_HOST', '127.0.0.1')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'terraos')} "
    f"user={os.getenv('DB_USER', 'terraos')}"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Terra.OS Alert Dispatcher")
    parser.add_argument(
        "--since-minutes", type=int, default=60,
        help="Okno czasowe wstecz w minutach (domyślnie 60)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Testuj bez wysyłania — HTML preview w /tmp/",
    )
    parser.add_argument("--tenant-id", help="Ogranicz do jednego tenanta")
    parser.add_argument(
        "--min-score", type=float, default=0.0,
        help="Minimalne match_score przetargu [0.0-1.0]",
    )
    parser.add_argument("--db-dsn", default=DEFAULT_DSN)
    args = parser.parse_args()

    logger.info(
        "Starting alert dispatcher (since_minutes=%d, dry_run=%s)",
        args.since_minutes, args.dry_run,
    )

    from ingestion.alert_dispatcher import check_new_tenders_for_alerts

    stats = check_new_tenders_for_alerts(
        since_minutes=args.since_minutes,
        db_dsn=args.db_dsn,
        tenant_id=args.tenant_id,
        min_score=args.min_score,
        dry_run=args.dry_run,
    )

    logger.info(
        "Alert dispatcher complete: checked=%d fired=%d emails=%d tenders=%d skipped=%d",
        stats["alerts_checked"],
        stats["alerts_fired"],
        stats["emails_sent"],
        stats["tenders_found"],
        stats["skipped"],
    )


if __name__ == "__main__":
    main()
