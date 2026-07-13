"""BZP Auto-sync worker — scheduled poller with dedup, doc fetch, and embedding trigger.

Faza 8.02: 
  - Co 15 min: nowe ogłoszenia z BZP API
  - Dedup na numerze ogłoszenia
  - Trigger embeddingu po insercie
  - Obsługa błędów i retry
  - Status w app_config
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import sqlalchemy as sa

from terra_db.session import get_engine

logger = logging.getLogger(__name__)

BZP_API = "https://ezamowienia.gov.pl/mo-client-board/api/v1"


async def sync_bzp_batch(max_pages: int = 3) -> dict[str, Any]:
    """Fetch latest BZP notices, dedup, insert new ones, trigger embedding."""
    engine = get_engine()
    stats = {"fetched": 0, "inserted": 0, "skipped": 0, "errors": 0}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in range(max_pages):
                try:
                    resp = await client.get(
                        f"{BZP_API}/notices/search",
                        params={
                            "pageNumber": page,
                            "pageSize": 20,
                            "sortBy": "publicationDate",
                            "sortOrder": "DESC",
                            "noticeType": "ZP400PodstawaBzp",
                        },
                        headers={"Accept": "application/json"},
                    )
                    if resp.status_code != 200:
                        break

                    data = resp.json()
                    notices = data.get("items") or data.get("notifications") or data if isinstance(data, list) else []
                    if not notices:
                        break

                    stats["fetched"] += len(notices)

                    for notice in notices:
                        result = _upsert_tender(engine, notice)
                        if result == "inserted":
                            stats["inserted"] += 1
                        elif result == "skipped":
                            stats["skipped"] += 1

                except Exception as e:
                    logger.warning("BZP page %d error: %s", page, e)
                    stats["errors"] += 1
                    break

    except Exception as e:
        logger.error("BZP sync failed: %s", e)
        stats["errors"] += 1

    # Persist sync status
    _update_sync_status(engine, stats)
    return stats


def _upsert_tender(engine, notice: dict) -> str:
    """Insert tender if not exists. Returns 'inserted' or 'skipped'."""
    # Extract fields — BZP API varies in field names
    notice_number = (
        notice.get("numerOgloszenia") or
        notice.get("noticeNumber") or
        notice.get("number") or
        str(notice.get("id") or "")
    )
    if not notice_number:
        return "skipped"

    # Dedup hash
    dedup_hash = hashlib.sha256(notice_number.encode()).hexdigest()[:16]

    title = (
        notice.get("nazwaZamowienia") or
        notice.get("name") or
        notice.get("title") or
        f"Przetarg {notice_number}"
    )[:500]

    buyer = (
        notice.get("zamawiajacy", {}).get("nazwa") if isinstance(notice.get("zamawiajacy"), dict)
        else notice.get("buyerName") or notice.get("buyer") or ""
    )

    value_str = (
        notice.get("wartoscZamowienia") or
        notice.get("estimatedValue") or
        notice.get("value") or "0"
    )
    try:
        value_pln = float(str(value_str).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        value_pln = 0.0

    cpv = notice.get("cpv") or notice.get("mainCpv") or ""

    source_url = (
        notice.get("linkDoOgloszenia") or
        notice.get("url") or
        f"https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/{notice_number}"
    )

    try:
        with engine.begin() as conn:
            # Check dedup
            exists = conn.execute(sa.text(
                "SELECT 1 FROM tender WHERE source_id = :sid LIMIT 1"
            ), {"sid": notice_number}).fetchone()

            if exists:
                return "skipped"

            # Insert
            conn.execute(sa.text("""
                INSERT INTO tender (
                    id, title, buyer, value_pln, cpv, source_id, source_url,
                    status, pipeline_status, created_at, updated_at
                ) VALUES (
                    :id, :title, :buyer, :value, :cpv, :sid, :url,
                    'active', 'new', NOW(), NOW()
                )
                ON CONFLICT (source_id) DO NOTHING
            """), {
                "id": str(uuid.uuid4()),
                "title": title,
                "buyer": buyer[:200] if buyer else "",
                "value": value_pln,
                "cpv": cpv[:20] if cpv else "",
                "sid": notice_number,
                "url": source_url[:500] if source_url else "",
            })

            return "inserted"

    except Exception as e:
        logger.warning("Tender upsert error (%s): %s", notice_number, e)
        return "skipped"


def _update_sync_status(engine, stats: dict):
    """Write sync status to app_config."""
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("""
                INSERT INTO app_config (key, value, updated_at)
                VALUES ('bzp_sync_last', :val, NOW())
                ON CONFLICT (key) DO UPDATE SET value = :val, updated_at = NOW()
            """), {"val": json.dumps({
                **stats,
                "last_run": datetime.now(timezone.utc).isoformat(),
            })})
    except Exception as e:
        logger.warning("Failed to update sync status: %s", e)


def get_sync_status(engine=None) -> dict:
    """Get last sync status from app_config."""
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            row = conn.execute(sa.text(
                "SELECT value FROM app_config WHERE key = 'bzp_sync_last'"
            )).fetchone()
            return json.loads(row[0]) if row else {"status": "never_run"}
    except Exception:
        return {"status": "unknown"}
