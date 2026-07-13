"""BZP ResultNotice connector — pobiera ogłoszenia o wynikach przetargów.

Używa BZP Search API (NoticeType=ResultNotice) żeby zebrać:
- kto wygrał przetarg (contractor_name, NIP)
- za ile (awarded_value)
- CPV, voivodeship, daty

CLI:
    python3 bzp_results_connector.py [--days-back 30] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Any

import httpx
from sqlalchemy import text
from terra_db.session import get_engine

from .scraper_base import AsyncHTTPClient, RetryPolicy, ScraperMetrics, parse_pln

logger = logging.getLogger(__name__)

BZP_URL = "https://bzp.uzp.gov.pl/ZP400PodgladOpublikowanego.aspx"
BZP_SEARCH_URL = "https://search.uzp.gov.pl/api/search/notices"

VOIVODESHIP_MAP = {
    "dolnośląskie": "PL51", "kujawsko-pomorskie": "PL61", "lubelskie": "PL81",
    "lubuskie": "PL43", "łódzkie": "PL71", "małopolskie": "PL21", "mazowieckie": "PL91",
    "opolskie": "PL52", "podkarpackie": "PL82", "podlaskie": "PL84", "pomorskie": "PL63",
    "śląskie": "PL22", "świętokrzyskie": "PL72", "warmińsko-mazurskie": "PL62",
    "wielkopolskie": "PL41", "zachodniopomorskie": "PL42",
}

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://bzp.uzp.gov.pl",
    "Referer": "https://bzp.uzp.gov.pl/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
}

# ---------------------------------------------------------------------------
# _parse_value: kept as thin wrapper around parse_pln for backward compat
# (parse_pln handles Polish numeric strings; _parse_value handled plain floats
# with "PLN" suffix — behaviour is equivalent)
# ---------------------------------------------------------------------------

def _parse_value(raw: Any) -> float | None:
    """Extract PLN value from BZP result field (delegates to parse_pln)."""
    return parse_pln(raw)


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(str(raw)[:19], fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Core async fetch
# ---------------------------------------------------------------------------

async def fetch_result_notices(
    days_back: int = 30,
    page_size: int = 500,
) -> list[dict]:
    """Pobiera ResultNotice z BZP za ostatnie N dni (async)."""
    date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(
        "source=bzp_results fetch_result_notices days_back=%d date_from=%s date_to=%s",
        days_back, date_from, date_to,
    )

    all_items: list[dict] = []
    offset = 0

    async with AsyncHTTPClient(
        source="bzp_results_connector",
        retry=RetryPolicy(max_attempts=4, base_delay=2.0, max_delay=60.0),
        rate_per_second=2.0,
        burst=5,
        timeout=httpx.Timeout(connect=8.0, read=45.0, write=10.0, pool=5.0),
        headers=HEADERS,
    ) as client:
        while True:
            payload = {
                "searchPhrase": "",
                "pageSize": page_size,
                "offset": offset,
                "sortingFieldName": "PublicationDate",
                "sortDirection": "DESC",
                "noticeType": ["ResultNotice"],
                "publicationDateFrom": date_from,
                "publicationDateTo": date_to,
            }
            try:
                resp = await client.post(BZP_SEARCH_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("source=bzp_results BZP search error at offset=%d: %s", offset, e)
                break

            items = data.get("notices") or data.get("items") or data.get("results") or []
            if not items:
                # Try alternative response shapes
                if isinstance(data, list):
                    items = data
                else:
                    logger.debug(
                        "source=bzp_results no items at offset=%d keys=%s",
                        offset, list(data.keys())[:5],
                    )
                    break

            all_items.extend(items)
            logger.info(
                "source=bzp_results fetched=%d ResultNotice offset=%d total=%d",
                len(items), offset, len(all_items),
            )

            total = data.get("totalCount") or data.get("total") or 0
            if len(all_items) >= total or len(items) < page_size:
                break
            offset += page_size

    # Emit ScraperMetrics summary
    m = client.metrics
    logger.info(
        "source=bzp_results fetched=%d requests=%d errors=%d p50=%.0fms",
        m.items_fetched, m.requests_total, m.requests_error, m.p50_ms,
    )

    return all_items


def fetch_result_notices_sync(
    days_back: int = 30,
    page_size: int = 500,
) -> list[dict]:
    """Sync wrapper around fetch_result_notices for backward compatibility."""
    return asyncio.run(fetch_result_notices(days_back=days_back, page_size=page_size))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_result_notice(raw: dict) -> dict | None:
    """Parsuje jeden ResultNotice do słownika do DB."""
    # Normalize field names (BZP uses various casing)
    r = {k.lower(): v for k, v in raw.items()}

    contractor = (
        r.get("contractorname") or r.get("contractor_name") or
        r.get("wykonawca") or r.get("winnername") or
        r.get("selectedcontractorname") or ""
    ).strip()
    if not contractor:
        return None

    notice_num = (
        r.get("noticenumber") or r.get("notice_number") or
        r.get("numerogloszenia") or r.get("publicationnumber") or ""
    ).strip()
    if not notice_num:
        return None

    value_raw = (
        r.get("contractvalue") or r.get("contract_value") or
        r.get("wartosczamowienia") or r.get("awardedvalue") or
        r.get("offervalue") or r.get("bestofferprice")
    )

    cpv = (
        r.get("cpvcode") or r.get("cpv_code") or r.get("cpv") or
        (r.get("cpvcodes") or [""])[0] if isinstance(r.get("cpvcodes"), list) else
        r.get("maincpvcode") or ""
    )
    if isinstance(cpv, list):
        cpv = cpv[0] if cpv else ""
    cpv = str(cpv).strip()[:8] if cpv else None

    voiv_raw = (
        r.get("voivodeship") or r.get("voivodship") or
        r.get("region") or r.get("wojewodztwo") or ""
    ).strip().lower()

    return {
        "notice_number": notice_num,
        "contract_number": r.get("contractnumber") or r.get("contract_number"),
        "original_notice": r.get("originalnoticenumber") or r.get("originalpublicationnumber"),
        "buyer_name": (r.get("buyername") or r.get("buyer_name") or r.get("zamawiajacy") or "").strip() or None,
        "buyer_regon": r.get("buyerregon") or r.get("regon"),
        "contractor_name": contractor,
        "contractor_nip": r.get("contractornip") or r.get("nip") or r.get("contractortaxnumber"),
        "awarded_value": _parse_value(value_raw),
        "currency": "PLN",
        "cpv_main": cpv,
        "voivodeship": voiv_raw or None,
        "awarded_date": _parse_date(r.get("awarddate") or r.get("award_date") or r.get("datawyboruoferty")),
        "publication_date": _parse_date(r.get("publicationdate") or r.get("publication_date")),
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# DB upsert (public API — unchanged)
# ---------------------------------------------------------------------------

def upsert_results(records: list[dict], dry_run: bool = False) -> int:
    """Wstawia/aktualizuje rekordy w bzp_results. Zwraca liczbę zapisanych."""
    if not records:
        return 0

    engine = get_engine()
    upsert_sql = text("""
        INSERT INTO bzp_results (
            notice_number, contract_number, original_notice,
            buyer_name, buyer_regon, contractor_name, contractor_nip,
            awarded_value, currency, cpv_main, voivodeship,
            awarded_date, publication_date, raw
        ) VALUES (
            :notice_number, :contract_number, :original_notice,
            :buyer_name, :buyer_regon, :contractor_name, :contractor_nip,
            :awarded_value, :currency, :cpv_main, :voivodeship,
            :awarded_date, :publication_date, CAST(:raw AS jsonb)
        )
        ON CONFLICT (notice_number) DO UPDATE SET
            contractor_name  = EXCLUDED.contractor_name,
            contractor_nip   = EXCLUDED.contractor_nip,
            awarded_value    = EXCLUDED.awarded_value,
            voivodeship      = EXCLUDED.voivodeship,
            raw              = EXCLUDED.raw
    """)

    import json
    saved = 0
    with engine.begin() as conn:
        for rec in records:
            if dry_run:
                saved += 1
                continue
            try:
                rec_copy = dict(rec)
                rec_copy["raw"] = json.dumps(rec_copy["raw"], ensure_ascii=False)
                conn.execute(upsert_sql, rec_copy)
                saved += 1
            except Exception as e:
                logger.warning("source=bzp_results skip %s: %s", rec.get("notice_number"), e)

    return saved


# ---------------------------------------------------------------------------
# run_bzp_results (public API — unchanged, stays sync)
# ---------------------------------------------------------------------------

def run_bzp_results(days_back: int = 30, dry_run: bool = False) -> dict:
    logger.info("source=bzp_results fetching BZP ResultNotice last=%d days", days_back)
    raw_items = fetch_result_notices_sync(days_back=days_back)
    logger.info("source=bzp_results fetched=%d raw ResultNotice", len(raw_items))

    parsed = []
    skipped = 0
    for item in raw_items:
        p = parse_result_notice(item)
        if p:
            parsed.append(p)
        else:
            skipped += 1

    logger.info("source=bzp_results parsed=%d valid skipped=%d", len(parsed), skipped)
    saved = upsert_results(parsed, dry_run=dry_run)
    logger.info(
        "source=bzp_results saved=%d to bzp_results%s",
        saved, " (dry-run)" if dry_run else "",
    )
    return {"fetched": len(raw_items), "parsed": len(parsed), "saved": saved, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="BZP ResultNotice connector")
    ap.add_argument("--days-back", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    result = run_bzp_results(days_back=args.days_back, dry_run=args.dry_run)
    print(f"Done: {result}")
