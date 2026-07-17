#!/usr/bin/env python3
"""Pre-tender Intelligence Scanner — sygnały pre-przetargowe dla Terra.OS.

Pobiera:
1. ContractNotice (aktualne ogłoszenia przetargowe) z BZP e-Zamówienia
2. TenderResultNotice (wyniki przetargów — analiza rynku) z BZP

UWAGA: BZP mo-board API obsługuje tylko NoticeType=ContractNotice i TenderResultNotice.
       e-Zamówienia plans API zwraca HTML (SPA), nie JSON — używamy BZP bezpośrednio.

Użycie:
    python3 scripts/pretender_scanner.py
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pretender_scanner")

BZP_BASE = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"

# ──────────────────────────────────────────────────────────────────────────────
# DB setup
# ──────────────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pretender_signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source TEXT NOT NULL,
    signal_id TEXT UNIQUE,
    title TEXT,
    buyer TEXT,
    estimated_value_pln NUMERIC(18,2),
    cpv_codes TEXT[],
    expected_date DATE,
    published_at TIMESTAMPTZ,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_pretender_cpv ON pretender_signals USING GIN(cpv_codes);
"""

INSERT_SQL = """
INSERT INTO pretender_signals (source, signal_id, title, buyer, estimated_value_pln,
    cpv_codes, expected_date, published_at, raw)
VALUES (:source, :signal_id, :title, :buyer, :estimated_value_pln,
    :cpv_codes, :expected_date, :published_at, :raw)
ON CONFLICT (signal_id) DO NOTHING
"""


def ensure_table() -> None:
    from terra_db.session import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        for stmt in CREATE_TABLE_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    log.info("Tabela pretender_signals gotowa.")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_date(val: Any) -> date | None:
    if not val:
        return None
    try:
        s = str(val)[:10]
        return date.fromisoformat(s)
    except Exception:
        return None


def _parse_datetime(val: Any) -> datetime | None:
    if not val:
        return None
    try:
        s = str(val).replace("Z", "+00:00").replace(" ", "T")
        return datetime.fromisoformat(s[:26])
    except Exception:
        return None


def _extract_cpv_codes(cpv_code_str: str | None) -> list[str]:
    """Wyciąga kody CPV z stringów jak '34110000-1 (Samochody osobowe),30213100-6 (...)'.
    
    Zwraca listę kodów 8-cyfrowych bez sufiksu (-X).
    """
    if not cpv_code_str:
        return []
    codes: list[str] = []
    # Znajdź wzorce: 8 cyfr opcjonalnie myślnik i cyfra
    matches = re.findall(r'\b(\d{8})(?:-\d)?\b', cpv_code_str)
    codes = list(dict.fromkeys(matches))  # deduplicate, preserve order
    return codes


def _bzp_get(notice_type: str, date_from: date, date_to: date,
             page: int = 1, page_size: int = 100) -> list[dict]:
    """Pobiera ogłoszenia z BZP mo-board API."""
    import httpx

    params = {
        "NoticeType": notice_type,
        "PublicationDateFrom": date_from.strftime("%Y-%m-%d"),
        "PublicationDateTo": date_to.strftime("%Y-%m-%d"),
        "PageSize": page_size,
        "PageNumber": page,
    }

    for attempt in range(3):
        try:
            resp = httpx.get(
                BZP_BASE,
                params=params,
                headers={"Accept": "application/json"},
                timeout=30.0,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("results", data.get("items", data.get("notices", [])))
                return []
            elif resp.status_code == 400:
                log.warning("BZP 400 dla NoticeType=%s: %s", notice_type, resp.text[:200])
                return []
            elif resp.status_code == 429:
                wait = (2 ** attempt) * 5
                log.warning("BZP rate limit — czekam %ds", wait)
                time.sleep(wait)
            else:
                log.warning("BZP HTTP %d dla %s: %s", resp.status_code, notice_type, resp.text[:100])
                if attempt < 2:
                    time.sleep((2 ** attempt) * 2)
                else:
                    return []
        except Exception as exc:
            log.warning("BZP request error (próba %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep((2 ** attempt) * 3)
            else:
                return []
    return []


# ──────────────────────────────────────────────────────────────────────────────
# Source 1: BZP ContractNotice (ogłoszenia o zamówieniu = pre-tender)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_bzp_contract_notices(days_back: int = 7) -> list[dict]:
    """Pobiera ContractNotice z BZP jako sygnały pre-tender.
    
    ContractNotice = ogłoszenie o wszczęciu postępowania — to jest właśnie
    pre-tender signal: zamawiający ogłasza zamówienie przed rozstrzygnięciem.
    """
    signals: list[dict] = []
    date_to = date.today()
    date_from = date_to - timedelta(days=days_back)

    log.info("Pobieranie BZP ContractNotice (%s → %s)...", date_from, date_to)

    page = 1
    while page <= 5:  # max 5 stron = 500 ogłoszeń
        items = _bzp_get("ContractNotice", date_from, date_to, page=page)
        if not items:
            log.info("Brak ContractNotice na stronie %d.", page)
            break

        log.info("BZP ContractNotice strona %d: %d ogłoszeń", page, len(items))

        for item in items:
            sig = _parse_bzp_item(item, source="bzp_contract_notice")
            if sig:
                signals.append(sig)

        if len(items) < 100:
            break
        page += 1
        time.sleep(0.5)

    log.info("BZP ContractNotice: %d sygnałów", len(signals))
    return signals


# ──────────────────────────────────────────────────────────────────────────────
# Source 2: BZP TenderResultNotice (wyniki — dla analizy rynku)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_bzp_result_notices(days_back: int = 7) -> list[dict]:
    """Pobiera TenderResultNotice z BZP (wyniki przetargów)."""
    signals: list[dict] = []
    date_to = date.today()
    date_from = date_to - timedelta(days=days_back)

    log.info("Pobieranie BZP TenderResultNotice (%s → %s)...", date_from, date_to)

    page = 1
    while page <= 3:  # max 3 strony = 300 wyników
        items = _bzp_get("TenderResultNotice", date_from, date_to, page=page)
        if not items:
            break

        log.info("BZP TenderResultNotice strona %d: %d ogłoszeń", page, len(items))

        for item in items:
            sig = _parse_bzp_item(item, source="bzp_result_notice")
            if sig:
                signals.append(sig)

        if len(items) < 100:
            break
        page += 1
        time.sleep(0.5)

    log.info("BZP TenderResultNotice: %d sygnałów", len(signals))
    return signals


def _parse_bzp_item(item: dict, source: str) -> dict | None:
    """Parsuje ogłoszenie BZP do struktury pretender_signals."""
    notice_number = item.get("noticeNumber", "")
    if not notice_number:
        return None

    signal_id = f"{source}_{notice_number.replace('/', '_').replace(' ', '_')}"

    title = item.get("orderObject", "")
    buyer = item.get("organizationName", "")

    # CPV — format "34110000-1 (Samochody osobowe)"
    cpv_str = item.get("cpvCode", "")
    cpv_codes = _extract_cpv_codes(cpv_str)

    # Wartość — BZP rzadko podaje wartość szacunkową w tym endpoint
    value = None
    for val_key in ["tenderAmount", "estimatedValue", "contractValue"]:
        v = item.get(val_key)
        if v is not None:
            try:
                value = float(v)
                break
            except (TypeError, ValueError):
                pass

    # Daty
    pub_dt = _parse_datetime(item.get("publicationDate", ""))
    expected_date = _parse_date(item.get("submittingOffersDate", ""))

    return {
        "source": source,
        "signal_id": signal_id[:500],
        "title": str(title)[:2000] if title else None,
        "buyer": str(buyer)[:500] if buyer else None,
        "estimated_value_pln": value,
        "cpv_codes": cpv_codes,
        "expected_date": expected_date,
        "published_at": pub_dt,
        "raw": json.dumps(item, ensure_ascii=False),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Save
# ──────────────────────────────────────────────────────────────────────────────

def save_signals(signals: list[dict]) -> int:
    if not signals:
        return 0

    from terra_db.session import get_engine
    from sqlalchemy import text

    engine = get_engine()
    inserted = 0

    with engine.connect() as conn:
        for s in signals:
            try:
                result = conn.execute(text(INSERT_SQL), s)
                inserted += result.rowcount
            except Exception as exc:
                log.warning("Insert failed dla signal_id=%s: %s", s.get("signal_id"), exc)
                try:
                    conn.rollback()
                except Exception:
                    pass
                continue
        conn.commit()

    return inserted


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        ensure_table()
    except Exception as e:
        log.error("Błąd tworzenia tabeli: %s", e)
        sys.exit(1)

    all_signals: list[dict] = []
    errors: list[str] = []

    # Źródło 1: BZP ContractNotice (ogłoszenia o zamówieniu)
    try:
        contracts = fetch_bzp_contract_notices(days_back=7)
        all_signals.extend(contracts)
    except Exception as exc:
        log.error("Błąd fetch_bzp_contract_notices: %s — kontynuuję.", exc)
        errors.append(f"bzp_contract_notice: {exc}")

    # Źródło 2: BZP TenderResultNotice (wyniki przetargów)
    try:
        results = fetch_bzp_result_notices(days_back=7)
        all_signals.extend(results)
    except Exception as exc:
        log.error("Błąd fetch_bzp_result_notices: %s — kontynuuję.", exc)
        errors.append(f"bzp_result_notice: {exc}")

    log.info("Łącznie %d sygnałów pre-przetargowych do zapisu.", len(all_signals))

    try:
        inserted = save_signals(all_signals)
        print(f"\n✅ Pre-tender scan zakończony: {inserted} nowych sygnałów w pretender_signals.")
    except Exception as e:
        log.error("Błąd zapisu do DB: %s", e)
        sys.exit(1)

    if errors:
        print(f"⚠️  Błędy źródeł (graceful degradation): {', '.join(errors)}")

    # Podsumowanie z DB
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM pretender_signals")).scalar()
            by_source = conn.execute(
                text("SELECT source, COUNT(*) as cnt FROM pretender_signals GROUP BY source ORDER BY cnt DESC")
            ).fetchall()
            print(f"\n📦 Łącznie w bazie pretender_signals: {count} rekordów")
            for row in by_source:
                print(f"  • {row[0]}: {row[1]}")
    except Exception as e:
        log.warning("Nie mogę sprawdzić liczby rekordów: %s", e)


if __name__ == "__main__":
    main()
