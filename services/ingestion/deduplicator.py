"""Cross-source tender deduplicator.

Finds near-duplicate tenders across bzp / ted / bip using:
1. PostgreSQL pg_trgm similarity on normalized title
2. Buyer name fuzzy match
3. Value similarity (within 20%)
4. Published-date proximity (within 30 days)

Writes results to tender_duplicate table:
    master_id    → the "best" record (prefer bzp > ted > bip)
    duplicate_id → the lower-quality duplicate

Usage:
    python deduplicator.py --tenant-id <UUID> --db-dsn <DSN>
    python deduplicator.py --tenant-id <UUID> --db-dsn <DSN> --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Source priority: lower = preferred master
SOURCE_PRIORITY = {"bzp": 0, "ted": 1, "bip": 2, "bk": 3, "manual": 4, "excel": 5}

# Thresholds
TITLE_SIM_THRESHOLD = 0.55   # pg_trgm similarity
BUYER_SIM_THRESHOLD = 0.50
VALUE_RATIO_MAX = 0.25        # max 25% difference in value_pln
DATE_DAYS_MAX = 30            # max 30 days apart

# Minimum title similarity to even consider a pair
MIN_TITLE_SIM = 0.45


def normalize_text(s: str) -> str:
    """Lowercase, strip diacritics, remove common stopwords."""
    if not s:
        return ""
    # Lowercase + remove diacritics
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Remove punctuation except spaces
    s = re.sub(r"[^\w\s]", " ", s)
    # Remove stopwords
    STOPWORDS = {
        "w", "z", "na", "do", "i", "oraz", "dla", "nr", "ul", "al",
        "gmina", "miasto", "powiat", "urzad", "spolka", "sp", "zoo",
        "budowa", "przebudowa", "remont", "wykonanie", "dostawa", "zakup",
        "realizacja", "opracowanie", "usluga", "roboty",
    }
    words = [w for w in s.split() if w not in STOPWORDS and len(w) > 2]
    return " ".join(words)


@dataclass
class TenderRow:
    id: str
    source: str
    title: str
    buyer: str
    value_pln: float | None
    published_at: date | None
    title_norm: str = ""
    buyer_norm: str = ""

    def __post_init__(self):
        self.title_norm = normalize_text(self.title or "")
        self.buyer_norm = normalize_text(self.buyer or "")


def run_deduplicator(
    engine: sa.Engine,
    tenant_id: str,
    dry_run: bool = False,
    min_title_sim: float = TITLE_SIM_THRESHOLD,
) -> dict:
    """Find and record duplicate tenders for a tenant."""
    stats = {"pairs_found": 0, "new_pairs": 0, "skipped": 0}

    with engine.connect() as conn:
        # Step 1: Load all tenders for tenant
        rows = conn.execute(
            text("""
                SELECT id::text, source::text, title, buyer, value_pln,
                       published_at::date
                FROM tender
                WHERE tenant_id = :tid
                ORDER BY source, created_at
            """),
            {"tid": tenant_id},
        ).fetchall()

    if not rows:
        logger.info("No tenders found for tenant %s", tenant_id)
        return stats

    tenders = [
        TenderRow(
            id=str(r[0]),
            source=str(r[1]),
            title=str(r[2] or ""),
            buyer=str(r[3] or ""),
            value_pln=float(r[4]) if r[4] is not None else None,
            published_at=r[5],
        )
        for r in rows
    ]
    logger.info("Loaded %d tenders for deduplication", len(tenders))

    # Step 2: Use PostgreSQL pg_trgm to find candidate pairs efficiently
    # We'll do this in batches via SQL to avoid O(N^2) Python loop
    with engine.connect() as conn:
        # Create temp table with normalized titles
        conn.execute(text("DROP TABLE IF EXISTS _dedup_work"))
        conn.execute(text("""
            CREATE TEMP TABLE _dedup_work AS
            SELECT
                id,
                source::text as source,
                title,
                buyer,
                value_pln,
                published_at::date as pub_date
            FROM tender
            WHERE tenant_id = :tid
        """), {"tid": tenant_id})

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS _dedup_work_trgm
            ON _dedup_work USING gin (title gin_trgm_ops)
        """))

        # Step 3: Find candidate pairs using pg_trgm similarity
        logger.info("Searching for duplicate pairs (title sim >= %.2f)...", min_title_sim)
        pairs = conn.execute(text("""
            SELECT
                a.id      AS id_a,
                b.id      AS id_b,
                a.source  AS src_a,
                b.source  AS src_b,
                similarity(a.title, b.title) AS title_sim,
                a.value_pln AS val_a,
                b.value_pln AS val_b,
                a.pub_date  AS pub_a,
                b.pub_date  AS pub_b,
                a.buyer     AS buyer_a,
                b.buyer     AS buyer_b
            FROM _dedup_work a
            JOIN _dedup_work b
              ON a.id < b.id
             AND similarity(a.title, b.title) >= :min_sim
             AND a.source <> b.source
        """), {"min_sim": min_title_sim}).fetchall()

        logger.info("Candidate pairs from pg_trgm: %d", len(pairs))

        # Step 4: Score each pair
        duplicate_pairs: list[tuple[str, str, float, list[str]]] = []

        for row in pairs:
            id_a, id_b = str(row[0]), str(row[1])
            src_a, src_b = row[2], row[3]
            title_sim = float(row[4])
            val_a, val_b = row[5], row[6]
            pub_a, pub_b = row[7], row[8]
            buyer_a, buyer_b = str(row[9] or ""), str(row[10] or "")

            match_fields = ["title"]
            score = title_sim

            # Value check
            if val_a and val_b:
                ratio = abs(val_a - val_b) / max(val_a, val_b)
                if ratio <= VALUE_RATIO_MAX:
                    match_fields.append("value")
                    score += 0.15
                elif ratio > 0.5:
                    continue  # Values too different, skip

            # Date check
            if pub_a and pub_b:
                days_diff = abs((pub_a - pub_b).days)
                if days_diff <= DATE_DAYS_MAX:
                    match_fields.append("date")
                    score += 0.10
                elif days_diff > 90:
                    continue  # Too far apart in time

            # Buyer check (simple token overlap)
            buyer_a_norm = normalize_text(buyer_a)
            buyer_b_norm = normalize_text(buyer_b)
            if buyer_a_norm and buyer_b_norm:
                tokens_a = set(buyer_a_norm.split())
                tokens_b = set(buyer_b_norm.split())
                if tokens_a and tokens_b:
                    overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
                    if overlap >= 0.5:
                        match_fields.append("buyer")
                        score += 0.10

            # Final threshold — require buyer match if title_sim < 0.70
            if title_sim < 0.70 and "buyer" not in match_fields:
                continue
            if score < min_title_sim:
                continue

            # Determine master: prefer bzp > ted > bip
            pri_a = SOURCE_PRIORITY.get(src_a, 9)
            pri_b = SOURCE_PRIORITY.get(src_b, 9)
            if pri_a <= pri_b:
                master_id, dup_id = id_a, id_b
            else:
                master_id, dup_id = id_b, id_a

            duplicate_pairs.append((master_id, dup_id, round(score, 4), match_fields))
            stats["pairs_found"] += 1

        logger.info("Confirmed duplicate pairs: %d", len(duplicate_pairs))

        if dry_run:
            for master_id, dup_id, score, fields in duplicate_pairs[:20]:
                # Look up titles
                t_m = next((t for t in tenders if t.id == master_id), None)
                t_d = next((t for t in tenders if t.id == dup_id), None)
                if t_m and t_d:
                    logger.info(
                        "DUP [%.2f] %s|%s  ≈  %s|%s  fields=%s",
                        score, t_m.source, t_m.title[:60],
                        t_d.source, t_d.title[:60], fields,
                    )
            return stats

        # Step 5: Write to tender_duplicate
        for master_id, dup_id, score, fields in duplicate_pairs:
            try:
                conn.execute(text("""
                    INSERT INTO tender_duplicate
                        (tenant_id, master_id, duplicate_id, similarity, match_fields)
                    VALUES
                        (:tid, :master, :dup, :sim, :fields)
                    ON CONFLICT (tenant_id, master_id, duplicate_id) DO UPDATE
                        SET similarity = EXCLUDED.similarity,
                            match_fields = EXCLUDED.match_fields
                """), {
                    "tid": tenant_id,
                    "master": master_id,
                    "dup": dup_id,
                    "sim": score,
                    "fields": fields,
                })
                stats["new_pairs"] += 1
            except Exception as e:
                logger.warning("Failed to insert duplicate pair: %s", e)
                stats["skipped"] += 1

        conn.commit()

    logger.info(
        "Deduplication done: %d pairs found, %d new, %d skipped",
        stats["pairs_found"], stats["new_pairs"], stats["skipped"],
    )
    return stats


def find_cross_source_duplicates(
    conn,
    similarity_threshold: float = 0.65,
    deadline_days: int = 14,
    dry_run: bool = False,
) -> dict:
    """Find tenders published in both BZP and TED simultaneously.

    Matching criteria:
      1. title pg_trgm similarity > similarity_threshold (default 0.65)
      2. buyer name token overlap >= 50% OR buyer ILIKE match
      3. deadline_at within ±deadline_days (default ±14)

    When a duplicate pair is found:
      - BZP record is the master (preferred source)
      - TED record gets  duplicate_of = <bzp_id>, status = 'archived'
      - Also recorded in tender_duplicate table for audit trail

    Accepts both psycopg2 connections and SQLAlchemy engines/connections.
    Returns dict with: pairs_found, pairs_marked, skipped, dry_run.
    """
    import psycopg2  # noqa: F401 – just for type-hint clarity

    stats: dict = {"pairs_found": 0, "pairs_marked": 0, "skipped": 0, "dry_run": dry_run}

    # --- normalised helper (SQL-side) ---
    QUERY_FIND = """
        SELECT
            a.id          AS bzp_id,
            b.id          AS ted_id,
            a.tenant_id   AS tenant_id,
            similarity(a.title, b.title) AS title_sim,
            a.title       AS bzp_title,
            b.title       AS ted_title,
            a.buyer       AS bzp_buyer,
            b.buyer       AS ted_buyer,
            a.deadline_at AS bzp_deadline,
            b.deadline_at AS ted_deadline
        FROM tender a
        JOIN tender b
          ON a.source = 'bzp'
         AND b.source = 'ted'
         AND a.tenant_id = b.tenant_id
         AND similarity(a.title, b.title) >= :thresh
         AND (
               a.deadline_at IS NULL
               OR b.deadline_at IS NULL
               OR ABS(EXTRACT(EPOCH FROM (a.deadline_at - b.deadline_at)) / 86400) <= :days
             )
         AND b.duplicate_of IS NULL
        ORDER BY title_sim DESC
    """

    # Support both raw psycopg2 connections and SQLAlchemy connections/engines
    def _execute(connection, sql, params):
        """Execute query with named params; returns list of row mappings."""
        try:
            # SQLAlchemy engine
            from sqlalchemy import text as sa_text
            if hasattr(connection, "connect"):
                with connection.connect() as c:
                    return c.execute(sa_text(sql), params).fetchall()
            elif hasattr(connection, "execute") and hasattr(connection, "dialect"):
                return connection.execute(sa_text(sql), params).fetchall()
        except ImportError:
            pass
        # psycopg2 connection — translate :name → %(name)s
        import re as _re
        pg_sql = _re.sub(r":([a-z_]+)", r"%(\1)s", sql)
        cur = connection.cursor()
        cur.execute(pg_sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _run_update(connection, sql, params):
        """Execute DML; auto-commit for psycopg2."""
        try:
            from sqlalchemy import text as sa_text
            if hasattr(connection, "connect"):
                with connection.connect() as c:
                    c.execute(sa_text(sql), params)
                    c.commit()
                return
            elif hasattr(connection, "execute") and hasattr(connection, "dialect"):
                connection.execute(sa_text(sql), params)
                return
        except ImportError:
            pass
        import re as _re
        pg_sql = _re.sub(r":([a-z_]+)", r"%(\1)s", sql)
        cur = connection.cursor()
        cur.execute(pg_sql, params)
        connection.commit()

    rows = _execute(conn, QUERY_FIND, {"thresh": similarity_threshold, "days": deadline_days})
    logger.info(
        "Cross-source candidate pairs (trgm >= %.2f, deadline ±%d d): %d",
        similarity_threshold, deadline_days, len(rows),
    )

    seen_ted_ids: set[str] = set()

    for row in rows:
        # Support both dict-like and tuple rows
        if isinstance(row, dict):
            bzp_id    = str(row["bzp_id"])
            ted_id    = str(row["ted_id"])
            tenant_id = str(row["tenant_id"])
            title_sim = float(row["title_sim"])
            bzp_buyer = str(row.get("bzp_buyer") or "")
            ted_buyer = str(row.get("ted_buyer") or "")
        else:
            bzp_id    = str(row[0])
            ted_id    = str(row[1])
            tenant_id = str(row[2])
            title_sim = float(row[3])
            bzp_buyer = str(row[6] or "")
            ted_buyer = str(row[7] or "")

        # Skip if we already tagged this TED record
        if ted_id in seen_ted_ids:
            continue

        # Buyer token overlap check (secondary criterion)
        bzp_buyer_norm = normalize_text(bzp_buyer)
        ted_buyer_norm = normalize_text(ted_buyer)
        if bzp_buyer_norm and ted_buyer_norm:
            t_a = set(bzp_buyer_norm.split())
            t_b = set(ted_buyer_norm.split())
            if t_a and t_b:
                overlap = len(t_a & t_b) / max(len(t_a), len(t_b))
                if overlap < 0.30 and title_sim < 0.80:
                    logger.debug(
                        "Skipping pair (buyer overlap=%.2f, title_sim=%.2f): %s ↔ %s",
                        overlap, title_sim, bzp_id, ted_id,
                    )
                    stats["skipped"] += 1
                    continue

        stats["pairs_found"] += 1
        seen_ted_ids.add(ted_id)

        logger.info(
            "Cross-source DUP [trgm=%.3f] BZP %s  ≈  TED %s",
            title_sim, bzp_id, ted_id,
        )

        if dry_run:
            continue

        # Mark TED as duplicate of BZP
        try:
            _run_update(conn, """
                UPDATE tender
                   SET duplicate_of = CAST(:bzp_id AS UUID),
                       status        = 'archived'
                 WHERE id = CAST(:ted_id AS UUID)
                   AND duplicate_of IS NULL
            """, {"bzp_id": bzp_id, "ted_id": ted_id})

            # Also record in audit table
            _run_update(conn, """
                INSERT INTO tender_duplicate
                    (tenant_id, master_id, duplicate_id, similarity, match_fields)
                VALUES
                    (CAST(:tid AS UUID), CAST(:master AS UUID), CAST(:dup AS UUID),
                     CAST(:sim AS NUMERIC), ARRAY['cross_source','bzp_ted'])
                ON CONFLICT (tenant_id, master_id, duplicate_id) DO UPDATE
                    SET similarity    = EXCLUDED.similarity,
                        match_fields  = EXCLUDED.match_fields
            """, {
                "tid":    tenant_id,
                "master": bzp_id,
                "dup":    ted_id,
                "sim":    round(title_sim, 4),
            })

            stats["pairs_marked"] += 1
        except Exception as exc:
            logger.warning("Failed to mark duplicate %s → %s: %s", ted_id, bzp_id, exc)
            stats["skipped"] += 1

    logger.info(
        "Cross-source dedup done: %d pairs found, %d marked, %d skipped%s",
        stats["pairs_found"], stats["pairs_marked"], stats["skipped"],
        " [DRY RUN]" if dry_run else "",
    )
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-source tender deduplicator")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--db-dsn", required=True, help="PostgreSQL DSN")
    parser.add_argument("--dry-run", action="store_true", help="Only print, don't write")
    parser.add_argument("--min-sim", type=float, default=TITLE_SIM_THRESHOLD,
                        help=f"Min title similarity threshold (default {TITLE_SIM_THRESHOLD})")
    args = parser.parse_args()

    engine = sa.create_engine(args.db_dsn, pool_pre_ping=True)
    stats = run_deduplicator(
        engine=engine,
        tenant_id=args.tenant_id,
        dry_run=args.dry_run,
        min_title_sim=args.min_sim,
    )
    print(json.dumps(stats, indent=2))
