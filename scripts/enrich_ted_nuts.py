#!/usr/bin/env python3
"""Enrich TED tenders with voivodeship and nuts_code from raw JSONB data.

Usage:
    python scripts/enrich_ted_nuts.py

Connects to PostgreSQL, iterates over TED tenders where voivodeship IS NULL,
extracts city/NUTS data from raw JSONB, maps to voivodeship, and updates rows.
Reports counts at the end.
"""
from __future__ import annotations

import json
import os
import sys

# Add project root to path so we can import services/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

from services.ingestion.nuts_mapping import extract_nuts_from_raw

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://terraos:***@localhost:5432/terraos",
)


def main() -> None:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Fetch all TED records missing voivodeship
    cur.execute(
        "SELECT id, raw FROM tender WHERE source='ted' AND voivodeship IS NULL"
    )
    rows = cur.fetchall()
    total = len(rows)
    print(f"Fetched {total} TED records with voivodeship IS NULL")

    updated = 0
    still_null = 0
    city_hits = 0
    nuts_hits = 0

    update_cur = conn.cursor()

    for row in rows:
        tender_id = row["id"]
        raw: dict = row["raw"] if isinstance(row["raw"], dict) else json.loads(row["raw"])

        nuts_code, voivodeship = extract_nuts_from_raw(raw)

        if voivodeship:
            update_cur.execute(
                "UPDATE tender SET voivodeship = %s, nuts_code = %s WHERE id = %s",
                (voivodeship, nuts_code, tender_id),
            )
            updated += 1
            if nuts_code:
                nuts_hits += 1
            else:
                city_hits += 1
        else:
            still_null += 1

    conn.commit()
    cur.close()
    update_cur.close()
    conn.close()

    print(f"\n=== Enrichment results ===")
    print(f"Total TED records processed : {total}")
    print(f"Updated (voivodeship set)   : {updated}")
    print(f"  via NUTS code             : {nuts_hits}")
    print(f"  via city fallback         : {city_hits}")
    print(f"Still NULL after enrichment : {still_null}")
    print(f"Coverage                    : {updated/total*100:.1f}%" if total else "N/A")

    # Show breakdown by voivodeship
    if updated:
        conn2 = psycopg2.connect(DB_URL)
        cur2 = conn2.cursor()
        cur2.execute(
            """
            SELECT voivodeship, count(*) as cnt
            FROM tender
            WHERE source='ted' AND voivodeship IS NOT NULL
            GROUP BY voivodeship
            ORDER BY cnt DESC
            """
        )
        print("\n=== Voivodeship distribution (TED) ===")
        for r in cur2.fetchall():
            print(f"  {r[0]:<30} {r[1]:>4}")
        cur2.close()
        conn2.close()


if __name__ == "__main__":
    main()
