#!/usr/bin/env python3
"""TED (Tenders Electronic Daily) importer — pobiera ogłoszenia przetargowe UE dla Polski.

Użycie:
    python3 scripts/ted_importer.py --dry-run
    python3 scripts/ted_importer.py --days-back 30
    python3 scripts/ted_importer.py --days-back 7
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ted_importer")

TED_API_BASE = "https://api.ted.europa.eu/v3"

# TED v3 API — rzeczywiste typy ogłoszeń (notice-type field values)
NOTICE_TYPES = {
    "CN-STANDARD": "contract_notice",
    "CAN-STANDARD": "award_notice",
    "PIN-BUYER": "prior_info",
}

# TED v3 API — rzeczywiste dozwolone fields
TED_FIELDS = [
    "publication-date",
    "notice-type",
    "buyer-name",
    "organisation-name-buyer",
    "classification-cpv",
    "announcement-title",
    "description-part",
    "estimated-value-cur-lot",
    "tender-value",
    "organisation-country-buyer",
    "BT-137-LotsGroup",
]


# ──────────────────────────────────────────────────────────────────────────────
# DB setup
# ──────────────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ted_notices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ted_id TEXT UNIQUE NOT NULL,
    title TEXT,
    buyer TEXT,
    cpv_codes TEXT[],
    contract_value_eur NUMERIC(18,2),
    contract_value_pln NUMERIC(18,2),
    publication_date DATE,
    notice_type TEXT,
    country TEXT DEFAULT 'PL',
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_ted_notices_ted_id ON ted_notices(ted_id);
CREATE INDEX IF NOT EXISTS ix_ted_notices_cpv ON ted_notices USING GIN(cpv_codes);
"""

INSERT_SQL = """
INSERT INTO ted_notices (ted_id, title, buyer, cpv_codes, contract_value_eur,
    contract_value_pln, publication_date, notice_type, country, raw)
VALUES (:ted_id, :title, :buyer, :cpv_codes, :contract_value_eur,
    :contract_value_pln, :publication_date, :notice_type, :country, :raw)
ON CONFLICT (ted_id) DO NOTHING
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
    log.info("Tabela ted_notices gotowa.")


# ──────────────────────────────────────────────────────────────────────────────
# TED API v3
# ──────────────────────────────────────────────────────────────────────────────

def _build_query(notice_type_code: str, date_from: date, date_to: date) -> str:
    """Buduje query dla TED API v3 (składnia z IN () i operatorami porównania)."""
    from_str = date_from.strftime("%Y%m%d")
    to_str = date_to.strftime("%Y%m%d")
    return (
        f"buyer-country IN (POL) AND "
        f"notice-type IN ({notice_type_code}) AND "
        f"publication-date >= {from_str} AND "
        f"publication-date <= {to_str}"
    )


def _fetch_page(session: Any, query: str, page: int, limit: int = 100) -> dict:
    """Pobiera jedną stronę wyników z TED API z retry exponential backoff."""
    url = f"{TED_API_BASE}/notices/search"
    body = {
        "query": query,
        "scope": "ALL",
        "fields": TED_FIELDS,
        "page": page,
        "limit": limit,
    }

    for attempt in range(3):
        try:
            resp = session.post(url, json=body, timeout=30.0)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 400:
                data = resp.json()
                log.error("TED 400 Bad Request: %s", data.get("message", "")[:300])
                return {}
            elif resp.status_code == 429:
                wait = (2 ** attempt) * 5
                log.warning("TED rate limit (429) — czekam %ds (próba %d/3)", wait, attempt + 1)
                time.sleep(wait)
            elif resp.status_code in (401, 403):
                log.warning("TED auth error %d — kontynuuję bez auth.", resp.status_code)
                return {}
            else:
                log.warning("TED HTTP %d — %s", resp.status_code, resp.text[:200])
                if attempt < 2:
                    time.sleep((2 ** attempt) * 2)
                else:
                    return {}
        except Exception as exc:
            wait = (2 ** attempt) * 3
            log.warning("TED request error (próba %d/3): %s — czekam %ds", attempt + 1, exc, wait)
            if attempt < 2:
                time.sleep(wait)
            else:
                log.error("TED request failed po 3 próbach: %s", exc)
                return {}
    return {}


def _extract_multilang_text(val: Any, preferred_langs: list[str] | None = None) -> str:
    """Wyciąga tekst z wielojęzycznych struktur TED v3 (dict {lang: [texts]})."""
    if not val:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return str(val[0]) if val else ""
    if isinstance(val, dict):
        langs = preferred_langs or ["pol", "POL", "eng", "ENG", "pol", "pl"]
        for lang in langs:
            v = val.get(lang)
            if v:
                if isinstance(v, list):
                    return str(v[0]) if v else ""
                return str(v)
        # Fallback — pierwsze dostępne
        for v in val.values():
            if v:
                if isinstance(v, list):
                    return str(v[0]) if v else ""
                return str(v)
    return str(val) if val else ""


def _parse_notice(notice: dict, notice_type_str: str) -> dict | None:
    """Parsuje raw notice z TED API v3 do struktury tabeli."""
    # publication-number to ted_id
    ted_id = notice.get("publication-number", "")
    if not ted_id:
        return None

    # Tytuł
    title = _extract_multilang_text(notice.get("announcement-title") or
                                    notice.get("description-part", ""))

    # Zamawiający
    buyer_raw = notice.get("buyer-name") or notice.get("organisation-name-buyer", "")
    buyer = _extract_multilang_text(buyer_raw)

    # CPV
    cpv_raw = notice.get("classification-cpv", [])
    if isinstance(cpv_raw, list):
        # Usuń duplikaty
        cpv_codes = list(dict.fromkeys(str(c) for c in cpv_raw if c))
    elif isinstance(cpv_raw, str):
        cpv_codes = [cpv_raw]
    else:
        cpv_codes = []

    # Wartość (EUR — TED standardowo w EUR)
    contract_value_eur = None
    val_raw = notice.get("tender-value") or notice.get("estimated-value-cur-lot")
    if val_raw is not None:
        try:
            if isinstance(val_raw, (int, float)):
                contract_value_eur = float(val_raw)
            elif isinstance(val_raw, dict):
                contract_value_eur = float(val_raw.get("amount", 0) or 0) or None
        except (TypeError, ValueError):
            pass

    # Data publikacji
    pub_date = None
    pd_raw = notice.get("publication-date", "")
    if pd_raw:
        try:
            pub_date = date.fromisoformat(str(pd_raw)[:10])
        except Exception:
            pass

    return {
        "ted_id": str(ted_id),
        "title": str(title)[:2000] if title else None,
        "buyer": str(buyer)[:500] if buyer else None,
        "cpv_codes": cpv_codes,
        "contract_value_eur": contract_value_eur,
        "contract_value_pln": None,  # TED nie daje bezpośrednio PLN
        "publication_date": pub_date,
        "notice_type": notice_type_str,
        "country": "PL",
        "raw": json.dumps(notice, ensure_ascii=False),
    }


def fetch_ted_notices(days_back: int = 30) -> list[dict]:
    """Pobiera ogłoszenia TED dla Polski z ostatnich N dni."""
    import httpx

    date_to = date.today()
    date_from = date_to - timedelta(days=days_back)

    log.info("Pobieranie TED ogłoszeń PL: %s → %s (days_back=%d)", date_from, date_to, days_back)

    all_notices: list[dict] = []

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as session:
        for notice_type_code, notice_type_str in NOTICE_TYPES.items():
            query = _build_query(notice_type_code, date_from, date_to)
            log.info("Query [%s/%s]", notice_type_code, notice_type_str)

            page = 1
            while True:
                data = _fetch_page(session, query, page)
                if not data:
                    log.info("Pusta odpowiedź dla %s strona %d.", notice_type_code, page)
                    break

                notices_list = data.get("notices", [])
                total = data.get("total", 0)

                if not notices_list:
                    log.info("Brak ogłoszeń na stronie %d dla %s.", page, notice_type_code)
                    break

                log.info("Strona %d/%s — %d ogłoszeń (%s)",
                         page, (total // 100 + 1) if total else "?",
                         len(notices_list), notice_type_code)

                for n in notices_list:
                    parsed = _parse_notice(n, notice_type_str)
                    if parsed:
                        all_notices.append(parsed)

                # Paginacja
                if len(notices_list) < 100:
                    break
                if total and page * 100 >= total:
                    break
                page += 1
                time.sleep(0.5)  # grzeczne opóźnienie

    log.info("Łącznie pobrano %d ogłoszeń TED.", len(all_notices))
    return all_notices


def save_notices(notices: list[dict]) -> int:
    """Zapisuje ogłoszenia do DB, zwraca liczbę wstawionych rekordów."""
    if not notices:
        return 0

    from terra_db.session import get_engine
    from sqlalchemy import text

    engine = get_engine()
    inserted = 0

    with engine.connect() as conn:
        for n in notices:
            try:
                result = conn.execute(text(INSERT_SQL), n)
                inserted += result.rowcount
            except Exception as exc:
                log.warning("Insert failed dla ted_id=%s: %s", n.get("ted_id"), exc)
                try:
                    conn.rollback()
                except Exception:
                    pass
                continue
        conn.commit()

    log.info("Wstawiono %d / %d rekordów do ted_notices.", inserted, len(notices))
    return inserted


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="TED importer dla Terra.OS")
    parser.add_argument("--dry-run", action="store_true", help="Tylko pobierz, nie zapisuj do DB")
    parser.add_argument("--days-back", type=int, default=30, help="Liczba dni wstecz (domyślnie 30)")
    args = parser.parse_args()

    if not args.dry_run:
        try:
            ensure_table()
        except Exception as e:
            log.error("Błąd tworzenia tabeli: %s", e)
            sys.exit(1)

    try:
        notices = fetch_ted_notices(days_back=args.days_back)
    except Exception as e:
        log.error("Błąd pobierania TED: %s", e)
        sys.exit(1)

    if args.dry_run:
        log.info("DRY RUN — nie zapisuję do DB. Przykłady (pierwsze 3):")
        for n in notices[:3]:
            print(json.dumps({k: v for k, v in n.items() if k != "raw"}, default=str, indent=2))
        print(f"\nŁącznie: {len(notices)} ogłoszeń")
        return

    try:
        inserted = save_notices(notices)
        print(f"TED import zakończony: {inserted} nowych rekordów w ted_notices.")
    except Exception as e:
        log.error("Błąd zapisu do DB: %s", e)
        sys.exit(1)

    # Podsumowanie z DB
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM ted_notices")).scalar()
            print(f"📦 Łącznie w bazie ted_notices: {count} rekordów")
    except Exception as e:
        log.warning("Nie mogę sprawdzić liczby: %s", e)


if __name__ == "__main__":
    main()
