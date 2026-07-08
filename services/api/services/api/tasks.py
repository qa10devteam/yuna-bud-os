"""Terra.OS background tasks — Celery workers.

Faza 5: task definitions for BZP sync, document processing, analysis.
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import os
import logging
from datetime import datetime, timezone

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="services.api.services.api.tasks.sync_bzp_task",
    queue="normal",
    bind=True,
    max_retries=3,
)
def sync_bzp_task(self, days_back: int = 7, offline: bool = False):
    """Synchronize BZP tenders — runs every 15 minutes."""
    try:
        from terra_db.session import get_engine
        from services.ingestion.pipeline import run_ingest

        engine = get_engine()
        result = run_ingest(engine, days_back=days_back, offline=offline)
        logger.info(
            "BZP sync complete: fetched=%d created=%d updated=%d",
            result.raw_fetched, result.created, result.updated,
        )
        return {
            "status": "ok",
            "fetched": result.raw_fetched,
            "created": result.created,
            "updated": result.updated,
        }
    except Exception as exc:
        logger.error("BZP sync failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    name="services.api.services.api.tasks.process_document_task",
    queue="normal",
    bind=True,
    max_retries=2,
)
def process_document_task(self, document_id: str, org_id: str):
    """Process uploaded document — OCR, embedding, AI classification."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            # Update job status to running
            conn.execute(
                text("""
                    UPDATE tender_document
                    SET parsed_ok = false
                    WHERE id = :doc_id
                """),
                {"doc_id": document_id},
            )
            conn.commit()

        logger.info("Document %s processing queued (placeholder)", document_id)
        return {"status": "ok", "document_id": document_id}
    except Exception as exc:
        logger.error("Document processing failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    name="services.api.services.api.tasks.run_analysis_task",
    queue="normal",
    bind=True,
    max_retries=2,
)
def run_analysis_task(self, tender_id: str, org_id: str):
    """Run full analysis on a tender — cost estimation + risk extraction."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            tender = conn.execute(
                text("SELECT id, title, tenant_id FROM tender WHERE id = :tid"),
                {"tid": tender_id},
            ).fetchone()

            if not tender:
                return {"status": "error", "message": "Tender not found"}

            # Update status to analyzing
            conn.execute(
                text("UPDATE tender SET status = 'analyzing' WHERE id = :tid"),
                {"tid": tender_id},
            )
            conn.commit()

        logger.info("Analysis task for tender %s started (placeholder)", tender_id)
        return {"status": "ok", "tender_id": tender_id}
    except Exception as exc:
        logger.error("Analysis task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    name="services.api.services.api.tasks.fire_tender_alerts",
    queue="normal",
    bind=True,
    max_retries=2,
)
def fire_tender_alerts(self, tenant_id: str | None = None, frequency: str = "daily"):
    """Faza 19 — Send alert email digests for all due tender_alert rows."""
    try:
        from services.ingestion.alert_runner import run_alert_runner
        stats = run_alert_runner(tenant_id=tenant_id, frequency=frequency)
        logger.info("Alert runner done: %s", stats)
        return {"status": "ok", **stats}
    except Exception as exc:
        logger.error("fire_tender_alerts failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(
    name="services.api.services.api.tasks.notify_task",
    queue="critical",
)
def notify_task(user_id: str, org_id: str, notif_type: str, title: str, body: str = "", link: str = ""):
    """Create in-app notification."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO notifications (user_id, org_id, type, title, body, link)
                    VALUES (:uid, :oid, :type, :title, :body, :link)
                """),
                {"uid": user_id, "oid": org_id, "type": notif_type,
                 "title": title, "body": body, "link": link},
            )
            conn.commit()
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Notify task failed: %s", exc)
        return {"status": "error", "message": str(exc)}
