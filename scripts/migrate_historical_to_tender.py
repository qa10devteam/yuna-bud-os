#!/usr/bin/env python3
"""Faza 5 — migrate historical_tenders → tender table.

Selects construction-scope rows from historical_tenders (CPV 45* or tender_type
matching 'roboty') that are recent (≤90 days) and upserts them into the tender
table under the specified tenant_id.

Usage:
    python3 scripts/migrate_historical_to_tender.py [--dry-run] [--limit N] [--all-provinces]

Column mapping:
    historical_tenders.title               → tender.title
    historical_tenders.buyer               → tender.buyer
    historical_tenders.cpv_code            → tender.cpv  (as ARRAY)
    historical_tenders.province            → tender.voivodeship
    historical_tenders.estimated_value     → tender.value_pln
    historical_tenders.submitting_offers_date → tender.deadline_at
    historical_tenders.publication_date_full  → tender.published_at
    source = 'bzp'
    status = 'new'
    match_score = 0.0
    external_id = 'hist_' || historical_tenders.id
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Allow running from project root without installing the package
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://terraos:***@localhost:5432/terraos",
)

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"

# NUTS-2 codes for dolnośląskie (PL02), śląskie (PL22), opolskie (PL05)
# Also include sub-NUTS codes that start with these prefixes
TARGET_PROVINCE_PREFIXES = ("PL02", "PL22", "PL05")

DEFAULT_LIMIT = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(raw: str | None) -> datetime | None:
    """Parse various date/datetime strings into a datetime object."""
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(str(raw).strip()[:19], fmt)
        except ValueError:
            continue
    logger.debug("Cannot parse date: %r", raw)
    return None


# ---------------------------------------------------------------------------
# Core migration
# ---------------------------------------------------------------------------

def run_migration(
    *,
    dry_run: bool = False,
    limit: int = DEFAULT_LIMIT,
    all_provinces: bool = False,
) -> dict[str, int]:
    """Run the migration and return stats."""

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ------------------------------------------------------------------ #
        # 1. Count available rows first (informational)
        # ------------------------------------------------------------------ #
        province_filter = ""
        if not all_provinces:
            # Build prefix filter for dolnośląskie, śląskie, opolskie
            province_clauses = " OR ".join(
                f"province LIKE '{pfx}%'" for pfx in TARGET_PROVINCE_PREFIXES
            )
            province_filter = f"AND ({province_clauses})"

        # Determine effective date cutoff: prefer NOW()-90d, but if the dataset
        # ends before that window starts (historical data), use the last 90 days
        # of whatever data exists.
        cur.execute("SELECT MAX(date) FROM historical_tenders")
        max_row = cur.fetchone()
        max_date = max_row["max"] if max_row and max_row["max"] else None
        if max_date:
            from datetime import date as _date, timedelta as _td
            ninety_ago_real = _date.today() - _td(days=90)
            ninety_ago_data = max_date - _td(days=90)
            # If the real 90-day window starts after our data ends, use the
            # data-relative cutoff (last 90 days of available data).
            if ninety_ago_real > max_date:
                date_cutoff = ninety_ago_data
                logger.info(
                    "Dataset is historical (max_date=%s < 90d_ago=%s) — "
                    "using data-relative cutoff=%s",
                    max_date, ninety_ago_real, date_cutoff,
                )
            else:
                date_cutoff = ninety_ago_real
                logger.info(
                    "Date range: max_date=%s, using real cutoff=%s",
                    max_date, date_cutoff,
                )
        else:
            date_cutoff = None

        date_clause = f"AND date >= '{date_cutoff}'" if date_cutoff else ""

        count_sql = f"""
            SELECT COUNT(*) AS cnt
            FROM historical_tenders
            WHERE
                (cpv_code LIKE '45%%' OR tender_type ILIKE '%%roboty%%')
                {date_clause}
                {province_filter}
        """
        cur.execute(count_sql)
        row = cur.fetchone()
        available = row["cnt"] if row else 0
        logger.info(
            "Available rows (before limit): %d  [all_provinces=%s]",
            available,
            all_provinces,
        )

        if available == 0 and not all_provinces:
            logger.warning(
                "No rows found with province filter — retrying with all provinces."
            )
            all_provinces = True
            province_filter = ""
            cur.execute(f"""
                SELECT COUNT(*) AS cnt
                FROM historical_tenders
                WHERE
                    (cpv_code LIKE '45%%' OR tender_type ILIKE '%%roboty%%')
                    {date_clause}
            """)
            row = cur.fetchone()
            available = row["cnt"] if row else 0
            logger.info("Available rows (all provinces): %d", available)

        # ------------------------------------------------------------------ #
        # 2. Fetch source rows
        # ------------------------------------------------------------------ #
        # Build SELECT using string formatting for static parts, %s only for limit param
        province_clause_select = ""
        if not all_provinces:
            province_clauses_sel = " OR ".join(
                f"province LIKE '{pfx}%'" for pfx in TARGET_PROVINCE_PREFIXES
            )
            province_clause_select = f"AND ({province_clauses_sel})"

        date_clause_select = f"AND date >= '{date_cutoff}'" if date_cutoff else ""

        select_sql = f"""
            SELECT
                id,
                title,
                buyer,
                cpv_code,
                province,
                estimated_value,
                submitting_offers_date,
                publication_date_full,
                notice_url
            FROM historical_tenders
            WHERE
                (cpv_code LIKE '45%' OR tender_type ILIKE '%roboty%')
                {date_clause_select}
                {province_clause_select}
            ORDER BY date DESC
            LIMIT {int(limit)}
        """
        cur.execute(select_sql)
        rows = cur.fetchall()
        logger.info("Fetched %d source rows (limit=%d)", len(rows), limit)

        if not rows:
            logger.warning("No source rows matched — nothing to migrate.")
            return {"available": available, "fetched": 0, "inserted": 0, "skipped": 0}

        # ------------------------------------------------------------------ #
        # 3. Upsert into tender
        # ------------------------------------------------------------------ #
        upsert_sql = """
            INSERT INTO tender (
                tenant_id,
                source,
                external_id,
                title,
                buyer,
                cpv,
                voivodeship,
                value_pln,
                deadline_at,
                published_at,
                url,
                status,
                match_score,
                raw
            ) VALUES (
                %(tenant_id)s,
                'bzp'::source_kind,
                %(external_id)s,
                %(title)s,
                %(buyer)s,
                %(cpv)s,
                %(voivodeship)s,
                %(value_pln)s,
                %(deadline_at)s,
                %(published_at)s,
                %(url)s,
                'new'::tender_status,
                0.0,
                %(raw)s::jsonb
            )
            ON CONFLICT (tenant_id, source, external_id) DO UPDATE SET
                title        = EXCLUDED.title,
                buyer        = EXCLUDED.buyer,
                cpv          = EXCLUDED.cpv,
                voivodeship  = EXCLUDED.voivodeship,
                value_pln    = EXCLUDED.value_pln,
                deadline_at  = EXCLUDED.deadline_at,
                published_at = EXCLUDED.published_at,
                url          = EXCLUDED.url,
                status       = CASE
                                   WHEN tender.status = 'new' THEN 'new'::tender_status
                                   ELSE tender.status
                               END
        """

        import json

        inserted = 0
        skipped = 0

        for src in rows:
            external_id = f"hist_{src['id']}"

            # Parse dates
            deadline_at = _parse_ts(src["submitting_offers_date"])
            published_at = _parse_ts(src["publication_date_full"])

            # CPV as array
            cpv_val = src["cpv_code"]
            cpv_array = [cpv_val] if cpv_val else []

            # value_pln
            value_pln = src["estimated_value"]
            if value_pln is not None:
                try:
                    value_pln = float(value_pln)
                except (TypeError, ValueError):
                    value_pln = None

            title = (src["title"] or "").strip()
            if not title:
                skipped += 1
                continue

            params = {
                "tenant_id": TENANT_ID,
                "external_id": external_id,
                "title": title,
                "buyer": src["buyer"],
                "cpv": cpv_array,
                "voivodeship": src["province"],
                "value_pln": value_pln,
                "deadline_at": deadline_at,
                "published_at": published_at,
                "url": src["notice_url"],
                "raw": json.dumps(
                    {
                        "source": "historical_tenders",
                        "ht_id": src["id"],
                        "cpv_code": cpv_val,
                        "province": src["province"],
                    },
                    ensure_ascii=False,
                ),
            }

            if dry_run:
                inserted += 1
                continue

            try:
                cur.execute(upsert_sql, params)
                inserted += 1
            except Exception as exc:
                logger.warning("Skip %s: %s", external_id, exc)
                conn.rollback()
                skipped += 1
                # Re-open transaction after rollback
                conn.autocommit = False

        if not dry_run:
            conn.commit()
            logger.info("Committed %d rows to tender table", inserted)
        else:
            conn.rollback()
            logger.info("[DRY-RUN] Would insert %d rows (no DB changes)", inserted)

        return {
            "available": available,
            "fetched": len(rows),
            "inserted": inserted,
            "skipped": skipped,
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Verify results
# ---------------------------------------------------------------------------

def verify(dry_run: bool) -> None:
    if dry_run:
        return
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tender WHERE tenant_id = %s AND source = 'bzp' AND external_id LIKE 'hist_%%'",
        (TENANT_ID,),
    )
    row = cur.fetchone()
    total = row[0] if row else 0
    logger.info("Verification: tender table now has %d hist_ rows for tenant %s", total, TENANT_ID)
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate historical_tenders → tender table")
    ap.add_argument("--dry-run", action="store_true", help="Parse and count but do not write to DB")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max rows to migrate (default 500)")
    ap.add_argument("--all-provinces", action="store_true", help="Skip province filter (use all provinces)")
    args = ap.parse_args()

    logger.info("=== migrate_historical_to_tender ===")
    logger.info("tenant_id   : %s", TENANT_ID)
    logger.info("limit       : %d", args.limit)
    logger.info("dry_run     : %s", args.dry_run)
    logger.info("all_provinces: %s", args.all_provinces)

    stats = run_migration(
        dry_run=args.dry_run,
        limit=args.limit,
        all_provinces=args.all_provinces,
    )

    verify(args.dry_run)

    print("\n=== Migration stats ===")
    for k, v in stats.items():
        print(f"  {k:12s}: {v}")
    print("=== Done ===")


if __name__ == "__main__":
    main()
