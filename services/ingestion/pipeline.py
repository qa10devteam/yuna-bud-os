"""M1 — Ingestion pipeline: orchestrates fetch → normalize → filter → score → upsert."""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from sqlalchemy.engine import Engine

from .bzp_connector import BZPConnector
from .filters import apply_filters
from .fixtures import load_bzp_fixtures
from .normalize import normalize_bzp_notice, normalize_ted_notice
from .repository import get_or_create_default_tenant, upsert_tender
from .scorer import OwnerProfileSnap, ScoringWeights, load_scoring_config, score_tender
from .ted_connector import TEDConnector

try:
    from terra_shared.audit import AuditWriter
    _AUDIT_AVAILABLE = True
except ImportError:
    _AUDIT_AVAILABLE = False

logger = logging.getLogger(__name__)

TERRA_OFFLINE = os.getenv("TERRA_OFFLINE", "0") == "1"


class IngestResult:
    def __init__(self) -> None:
        self.raw_fetched: int = 0
        self.normalized: int = 0
        self.passed_filter: int = 0
        self.dropped_filter: int = 0
        self.created: int = 0
        self.updated: int = 0
        self.errors: int = 0
        self.bip_stored: int = 0
        self.dedup_pairs: int = 0

    def __repr__(self) -> str:
        return (
            f"IngestResult(fetched={self.raw_fetched}, norm={self.normalized}, "
            f"passed={self.passed_filter}, dropped={self.dropped_filter}, "
            f"created={self.created}, updated={self.updated}, errors={self.errors}, "
            f"bip={self.bip_stored}, dedup={self.dedup_pairs})"
        )


def run_ingest(
    engine: Engine,
    *,
    days_back: int = 7,
    offline: bool | None = None,
    owner_profile: OwnerProfileSnap | None = None,
    include_ted: bool = True,
    include_bip: bool = False,
    bip_region: str | None = None,
    bip_max_sites: int = 50,
    run_dedup: bool = True,
    tenant_id: str | None = None,  # explicit tenant override (multitenant SaaS)
) -> IngestResult:
    """Full M1 ingestion pipeline — BZP + TED EU.

    Steps:
      1. Fetch raw notices from BZP + TED (or fixtures if offline)
      2. Normalize each notice to TenderIn
      3. Apply CPV + geo filters
      4. Score each tender vs owner profile
      5. Upsert to DB (idempotent)
    """
    result = IngestResult()
    use_fixtures = offline if offline is not None else TERRA_OFFLINE

    date_from = date.today() - timedelta(days=days_back)
    date_to = date.today()

    # S19: BZP + TED both receive the same days_back (default 7) for consistency

    # Step 1a: BZP fetch
    if use_fixtures:
        logger.info("OFFLINE mode — loading BZP fixtures")
        bzp_raw = load_bzp_fixtures()
    else:
        connector = BZPConnector()
        bzp_raw = connector.fetch_notices(date_from=date_from, date_to=date_to)

    logger.info("BZP fetched %d raw notices", len(bzp_raw))

    # Step 1b: TED fetch
    ted_raw: list = []
    if include_ted and not use_fixtures:
        try:
            ted = TEDConnector()
            ted_raw = ted.fetch_notices(date_from=date_from, date_to=date_to)
            ted.close()
            logger.info("TED fetched %d raw notices", len(ted_raw))
        except Exception as exc:
            logger.error("TED fetch failed: %s", exc)

    result.raw_fetched = len(bzp_raw) + len(ted_raw)

    # Step 2a: Normalize BZP
    tenders_in = []
    for notice in bzp_raw:
        try:
            tin = normalize_bzp_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("BZP normalize error: %s", exc)
            result.errors += 1

    # Step 2b: Normalize TED
    for notice in ted_raw:
        try:
            tin = normalize_ted_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("TED normalize error: %s", exc)
            result.errors += 1

    result.normalized = len(tenders_in)

    # Step 3: Resolve tenant + load per-tenant scoring config
    if not tenant_id:
        tenant_id = get_or_create_default_tenant(engine)
    logger.info("Ingest for tenant_id=%s", tenant_id)

    # Load per-tenant scoring weights (falls back to defaults if not configured)
    if owner_profile is not None:
        profile: ScoringWeights = owner_profile
    else:
        profile = load_scoring_config(str(tenant_id))

    # For geo pre-filtering: use preferred_regions from profile if it's OwnerProfileSnap
    # (has .voivodeships), otherwise fall back to preferred_regions
    _voivodeships = set(getattr(profile, "voivodeships", None) or list(profile.preferred_regions))

    # Step 3 (filter): Filter
    passed, dropped = apply_filters(
        tenders_in,
        voivodeships=_voivodeships,
    )
    result.passed_filter = len(passed)
    result.dropped_filter = len(dropped)
    logger.info("Filter: %d passed, %d dropped", result.passed_filter, result.dropped_filter)

    # Step 4+5: Score + Upsert
    # tenant_id and profile already loaded above (Step 3)
    for tender in passed:
        try:
            score_result = score_tender(tender, profile)
            _, created = upsert_tender(
                engine,
                tender,
                match_score=score_result.score,
                match_reason=score_result.reason,
                tenant_id=tenant_id,
            )
            if created:
                result.created += 1
            else:
                result.updated += 1
        except Exception as exc:
            logger.warning("Upsert error for %s: %s", tender.external_id, exc)
            result.errors += 1

    logger.info("Ingest done: %r", result)

    # Step 6 (optional): BIP scraping
    if include_bip and not use_fixtures:
        try:
            from services.ingestion.bip_connector import run_bip_scraper
            bip_stats = run_bip_scraper(
                engine=engine,
                tenant_id=str(tenant_id),
                region=bip_region,
                max_sites=bip_max_sites,
                days_back=days_back,
            )
            result.bip_stored = bip_stats.get("tenders_stored", 0)
            logger.info("BIP ingest: %d tenders stored", result.bip_stored)
        except Exception as exc:
            logger.error("BIP ingest failed: %s", exc)

    # Step 7 (optional): Same-source deduplication
    if run_dedup and not use_fixtures:
        try:
            from services.ingestion.deduplicator import run_deduplicator
            dedup_stats = run_deduplicator(engine=engine, tenant_id=str(tenant_id))
            result.dedup_pairs = dedup_stats.get("new_pairs", 0)
            logger.info("Dedup: %d new duplicate pairs", result.dedup_pairs)
        except Exception as exc:
            logger.error("Dedup failed: %s", exc)

    # Step 7b (optional): Cross-source BZP↔TED deduplication
    if run_dedup and not use_fixtures:
        try:
            from services.ingestion.deduplicator import find_cross_source_duplicates
            cross_stats = find_cross_source_duplicates(engine)
            cross_pairs = cross_stats.get("pairs_marked", 0)
            result.dedup_pairs += cross_pairs
            logger.info(
                "Cross-source dedup (BZP↔TED): %d pairs marked, %d skipped",
                cross_pairs,
                cross_stats.get("skipped", 0),
            )
        except Exception as exc:
            logger.error("Cross-source dedup failed: %s", exc)

    # Step 8 (optional): Auto-fetch SWZ documents for high-score new tenders
    if not use_fixtures and result.created > 0:
        try:
            from services.ingestion.bzp_document_scraper import BZPDocumentScraper
            import sqlalchemy as sa

            # Fetch top matched new tenders (BZP only, score >= 0.5)
            with engine.connect() as conn:
                rows = conn.execute(sa.text("""
                    SELECT t.id, t.external_id
                    FROM tender t
                    LEFT JOIN bzp_documents bd ON bd.tender_id = t.id
                    WHERE t.source = 'bzp'
                      AND t.match_score >= 0.5
                      AND t.tenant_id = :tid
                      AND bd.id IS NULL
                    ORDER BY t.match_score DESC, t.created_at DESC
                    LIMIT 10
                """), {"tid": str(tenant_id)}).fetchall()

            if rows:
                logger.info("Auto-fetch SWZ: %d high-score tenders", len(rows))
                with BZPDocumentScraper(db_engine=engine) as scraper:
                    fetched_ok = 0
                    for row in rows:
                        try:
                            fr = scraper.fetch_all(
                                tender_id=str(row[0]),
                                bzp_number=row[1],
                                download_files=False,  # nie pobieraj plików, tylko metadane
                            )
                            if fr.documents:
                                fetched_ok += 1
                        except Exception as e:
                            logger.debug("Auto-fetch SWZ skip %s: %s", row[0], e)
                logger.info("Auto-fetch SWZ done: %d/%d OK", fetched_ok, len(rows))
        except Exception as exc:
            logger.warning("Auto-fetch SWZ failed (non-fatal): %s", exc)

    # Sprint 9: Audit log — ingest.complete
    if _AUDIT_AVAILABLE:
        try:
            from terra_shared.audit import AuditWriter as _AW
            _audit = _AW()
            _audit.log(
                tenant_id=str(tenant_id),
                actor="pipeline",
                action="ingest.complete",
                entity_kind="ingest_result",
                payload={
                    "raw_fetched": result.raw_fetched,
                    "normalized": result.normalized,
                    "created": result.created,
                    "updated": result.updated,
                    "errors": result.errors,
                },
                ok=result.errors == 0,
            )
            _audit.write_to_db(engine)
        except Exception as exc:
            logger.debug("Audit log failed (non-critical): %s", exc)

    # S15: Auto-refresh mv_dashboard_stats after ingest complete
    try:
        from sqlalchemy import text as _t
        with engine.connect() as _c:
            _c.execute(_t('REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_stats'))
            _c.commit()
    except Exception as e:
        logger.warning('MV refresh failed: %s', e)

    # S91: n8n trigger_webhook on ingest complete
    try:
        from services.api.services.api.integrations.n8n_client import trigger_webhook
        trigger_webhook(
            "TenderCreated",
            {"count": result.created, "normalized": result.normalized},
            str(tenant_id),
        )
    except Exception as exc:
        logger.debug("n8n trigger_webhook non-critical: %s", exc)

    return result
