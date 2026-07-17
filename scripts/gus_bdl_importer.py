#!/usr/bin/env python3
"""GUS BDL (Bank Danych Lokalnych) importer — wskaźniki budownictwa dla Terra.OS.

Pobiera dane makroekonomiczne dla budownictwa z API GUS BDL.
Użycie:
    python3 scripts/gus_bdl_importer.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gus_bdl_importer")

GUS_BDL_BASE = "https://bdl.stat.gov.pl/api/v1"

# Zmienne budownicze zgodnie z task specyfikacją
CONSTRUCTION_VARIABLES = [
    ("216851", "Produkcja budowlano-montażowa (wartość)"),
    ("216853", "Liczba budów rozpoczętych"),
    ("287671", "Wynagrodzenia w budownictwie"),
]

YEARS = [2022, 2023, 2024]


# ──────────────────────────────────────────────────────────────────────────────
# DB setup
# ──────────────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS gus_indicators (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    variable_id TEXT NOT NULL,
    variable_name TEXT,
    unit_id TEXT,
    unit_name TEXT,
    year INT,
    value NUMERIC(18,4),
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(variable_id, unit_id, year)
);
"""

INSERT_SQL = """
INSERT INTO gus_indicators (variable_id, variable_name, unit_id, unit_name, year, value, raw)
VALUES (:variable_id, :variable_name, :unit_id, :unit_name, :year, :value, :raw)
ON CONFLICT (variable_id, unit_id, year) DO UPDATE SET
    value = EXCLUDED.value,
    variable_name = EXCLUDED.variable_name,
    unit_name = EXCLUDED.unit_name,
    raw = EXCLUDED.raw
"""


def ensure_table() -> None:
    from terra_db.session import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        conn.commit()
    log.info("Tabela gus_indicators gotowa.")


# ──────────────────────────────────────────────────────────────────────────────
# GUS BDL API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_variable(variable_id: str, variable_name: str, years: list[int],
                   unit_level: int = 2) -> list[dict]:
    """Pobiera dane zmiennej GUS BDL dla województw (unit-level=2).
    
    unit-level=2 = województwa
    unit-level=5 = gminy
    """
    import httpx

    years_str = ",".join(str(y) for y in years)
    url = f"{GUS_BDL_BASE}/data/by-variable/{variable_id}"
    params = {
        "format": "json",
        "unit-level": str(unit_level),
        "year": years_str,
        "page-size": 100,  # GUS BDL max pageSize = 100
        "page": 0,
    }

    headers = {
        "Accept": "application/json",
        # GUS BDL API jest publiczne — bez X-ClientId (powoduje 403 jeśli niezarejestrowany)
    }

    records: list[dict] = []

    for attempt in range(3):
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=30.0,
                             follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                log.info("GUS BDL variable=%s: %d jednostek", variable_id, len(results))

                for unit in results:
                    unit_id = str(unit.get("id", ""))
                    unit_name = unit.get("name", "")
                    values_list = unit.get("values", [])

                    for v_entry in values_list:
                        year = v_entry.get("year")
                        val = v_entry.get("val")
                        # GUS BDL może zwracać None jako brak danych
                        if year is None:
                            continue

                        records.append({
                            "variable_id": variable_id,
                            "variable_name": variable_name,
                            "unit_id": unit_id,
                            "unit_name": unit_name,
                            "year": int(year),
                            "value": float(val) if val is not None else None,
                            "raw": json.dumps({"unit": unit_id, "unit_name": unit_name,
                                               "year": year, "val": val,
                                               "variable_id": variable_id}),
                        })
                return records

            elif resp.status_code == 404:
                log.warning("GUS BDL: zmienna %s nie znaleziona (404)", variable_id)
                return []
            elif resp.status_code == 429:
                wait = (2 ** attempt) * 5
                log.warning("GUS rate limit — czekam %ds", wait)
                time.sleep(wait)
            else:
                log.warning("GUS BDL HTTP %d dla %s: %s", resp.status_code, variable_id,
                            resp.text[:200])
                return []

        except Exception as exc:
            wait = (2 ** attempt) * 3
            log.warning("GUS BDL request error (próba %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(wait)
            else:
                log.error("GUS BDL failed po 3 próbach dla var=%s: %s", variable_id, exc)
                return []

    return records


def save_indicators(records: list[dict]) -> int:
    """Zapisuje wskaźniki do DB, zwraca liczbę upsertowanych rekordów."""
    if not records:
        return 0

    from terra_db.session import get_engine
    from sqlalchemy import text

    engine = get_engine()
    upserted = 0

    with engine.connect() as conn:
        for r in records:
            try:
                result = conn.execute(text(INSERT_SQL), r)
                upserted += result.rowcount
            except Exception as exc:
                log.warning("Insert failed dla var=%s unit=%s year=%s: %s",
                            r.get("variable_id"), r.get("unit_id"), r.get("year"), exc)
                conn.rollback()
                continue
        conn.commit()

    return upserted


def print_top_regions(records: list[dict]) -> None:
    """Drukuje województwa z najwyższymi wskaźnikami."""
    from collections import defaultdict

    # Grupuj po variable_name i znajdź top regions dla 2024
    by_var: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("year") == 2024 and r.get("value") is not None:
            by_var[r["variable_name"]].append(r)

    for var_name, items in by_var.items():
        sorted_items = sorted(items, key=lambda x: x.get("value") or 0, reverse=True)
        print(f"\n📊 {var_name} (2024) — Top 5 województw:")
        for i, item in enumerate(sorted_items[:5], 1):
            val = item.get("value")
            unit = item.get("unit_name", "?")
            print(f"  {i}. {unit}: {val:,.2f}" if val else f"  {i}. {unit}: brak danych")


def main() -> None:
    try:
        ensure_table()
    except Exception as e:
        log.error("Błąd tworzenia tabeli: %s", e)
        sys.exit(1)

    all_records: list[dict] = []

    for var_id, var_name in CONSTRUCTION_VARIABLES:
        log.info("Pobieranie zmiennej: %s — %s", var_id, var_name)
        try:
            records = fetch_variable(var_id, var_name, YEARS, unit_level=2)
            all_records.extend(records)
            log.info("  → %d rekordów dla %s", len(records), var_name)
        except Exception as exc:
            log.error("Błąd pobierania %s: %s — kontynuuję.", var_id, exc)
        time.sleep(1.0)  # grzeczność wobec API

    log.info("Łącznie %d rekordów GUS BDL do zapisu.", len(all_records))

    try:
        upserted = save_indicators(all_records)
        print(f"\n✅ GUS BDL import zakończony: {upserted} rekordów w gus_indicators.")
    except Exception as e:
        log.error("Błąd zapisu do DB: %s", e)
        sys.exit(1)

    # Statystyki
    print_top_regions(all_records)

    # Podsumowanie z DB
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM gus_indicators")).scalar()
            print(f"\n📦 Łącznie w bazie gus_indicators: {count} rekordów")
    except Exception as e:
        log.warning("Nie mogę sprawdzić liczby rekordów w DB: %s", e)


if __name__ == "__main__":
    main()
