"""BZP Result Notice Scraper → market_results table.

Fetches TenderResultNotice from BZP API (ogłoszenia o wyniku postępowania).
Extracts: who won, for how much, estimated value, offers count.

State-of-art upgrade (v2):
  - Async httpx via scraper_base.AsyncHTTPClient
  - Retry/backoff/circuit-breaker unified z scraper_base
  - ScraperMetrics — latency, bytes, items
  - Rate limiting (2 req/s)
  - Structured logging
  - Batch DB insert z psycopg2 execute_values

Usage:
    python3 bzp_result_scraper.py --days 30 --order-type Works
    python3 bzp_result_scraper.py --date-from 2026-06-01 --date-to 2026-07-08
"""
from __future__ import annotations

import argparse
import asyncio
import re
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
import psycopg2
from psycopg2.extras import execute_values

from .scraper_base import AsyncHTTPClient, RetryPolicy, parse_pln

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BZP_API = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
PAGE_SIZE = 100

_RETRY = RetryPolicy(max_attempts=4, base_delay=2.0, max_delay=60.0)
_TIMEOUT = httpx.Timeout(connect=8.0, read=45.0, write=10.0, pool=5.0)
_LIMITS = httpx.Limits(max_connections=5, max_keepalive_connections=3)


# ---------------------------------------------------------------------------
# HTML parsers (kept from v1)
# ---------------------------------------------------------------------------

def parse_price_from_html(html: str, pattern: str) -> Optional[float]:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    match = re.search(pattern, text)
    if match:
        return parse_pln(match.group(1))
    return None


def extract_prices_from_html(html: str) -> dict:
    prices = {}
    prices["estimated_value"] = parse_price_from_html(
        html, r"Warto[śs][ćc] zam[óo]wienia[:\s]+([\d\s,\.]+)\s*(?:PLN|zł)"
    )
    prices["lowest_price"] = parse_price_from_html(
        html, r"najni[żz]sz[ąa] cen[ąa][^:]*:[:\s]*([\d\s,\.]+)\s*(?:PLN|zł)"
    )
    prices["highest_price"] = parse_price_from_html(
        html, r"najwy[żz]sz[ąa] cen[ąa][^:]*:[:\s]*([\d\s,\.]+)\s*(?:PLN|zł)"
    )
    prices["winning_price"] = parse_price_from_html(
        html, r"kt[óo]remu udzielono[^:]*:[:\s]*([\d\s,\.]+)\s*(?:PLN|zł)"
    )
    offers_match = re.search(
        r"Liczba ofert sk[łl]adanych[:\s]*(\d+)",
        re.sub(r"<[^>]+>", " ", html),
    )
    if offers_match:
        prices["offers_count"] = int(offers_match.group(1))
    return prices


# ---------------------------------------------------------------------------
# Async fetch
# ---------------------------------------------------------------------------

async def _fetch_result_notices_async(
    date_from: str,
    date_to: str,
    order_type: str = "Works",
    max_pages: int = 50,
) -> list[dict]:
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    all_notices: dict[str, dict] = {}

    async with AsyncHTTPClient(
        source="bzp_results",
        timeout=_TIMEOUT,
        limits=_LIMITS,
        retry=_RETRY,
        rate_per_second=2.0,
        burst=6,
    ) as http:
        current = start
        while current <= end:
            day_str = current.isoformat()
            page = 0
            day_count = 0

            while page < max_pages:
                params = {
                    "pageSize": PAGE_SIZE,
                    "pageNumber": page,
                    "NoticeType": "TenderResultNotice",
                    "PublicationDateFrom": day_str,
                    "PublicationDateTo": day_str,
                    "OrderType": order_type,
                }
                try:
                    resp = await http.get(BZP_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "source=bzp_results day=%s page=%d status=%d",
                        day_str, page, exc.response.status_code,
                    )
                    break
                except Exception as exc:
                    logger.warning("source=bzp_results day=%s page=%d error=%s", day_str, page, exc)
                    break

                if not data:
                    break

                filtered = [n for n in data if n.get("orderType") == order_type]
                added = 0
                for n in filtered:
                    nn = n.get("noticeNumber", "")
                    if nn and nn not in all_notices:
                        all_notices[nn] = n
                        added += 1
                        day_count += 1

                http.metrics.record_items(fetched=added)

                if len(data) < PAGE_SIZE:
                    break
                page += 1

            if day_count:
                logger.info(
                    "source=bzp_results day=%s new=%d total=%d",
                    day_str, day_count, len(all_notices),
                )
            current += timedelta(days=1)

        m = http.metrics
        logger.info(
            "source=bzp_results fetched=%d requests=%d errors=%d p50=%.0fms",
            len(all_notices), m.requests_total, m.requests_error, m.p50_ms,
        )

    return list(all_notices.values())


# ---------------------------------------------------------------------------
# Public sync API
# ---------------------------------------------------------------------------

def fetch_result_notices(
    date_from: str,
    date_to: str,
    order_type: str = "Works",
    max_pages: int = 50,
) -> list[dict]:
    return asyncio.run(_fetch_result_notices_async(date_from, date_to, order_type, max_pages))


def transform_notice(notice: dict) -> list[dict]:
    """Transform a BZP result notice into market_results rows (one per contractor)."""
    html = notice.get("htmlBody", "")
    prices = extract_prices_from_html(html)

    contractors = notice.get("contractors") or []
    contractors = [c for c in contractors if c.get("contractorName")]
    if not contractors:
        contractors = [{"contractorName": notice.get("procedureResult", "BRAK DANYCH"),
                        "contractorNationalId": None, "contractorCity": None}]

    cpv_raw = notice.get("cpvCode", "")
    cpv_codes = [c.split(" ")[0] for c in cpv_raw.split(",") if c.strip()] if cpv_raw else []

    rows = []
    for c in contractors:
        rows.append({
            "ocds_tender_id": notice.get("tenderId", ""),
            "bzp_number": notice.get("bzpNumber"),
            "result_notice_number": notice.get("noticeNumber", ""),
            "procedure_result": notice.get("procedureResult"),
            "contractor_name": c.get("contractorName", "NIEZNANY"),
            "contractor_nip": c.get("contractorNationalId"),
            "contractor_city": c.get("contractorCity"),
            "winning_price_pln": prices.get("winning_price"),
            "lowest_price_pln": prices.get("lowest_price"),
            "highest_price_pln": prices.get("highest_price"),
            "estimated_value_pln": prices.get("estimated_value"),
            "offers_count": prices.get("offers_count"),
            "published_at": notice.get("publicationDate"),
            "cpv_codes": cpv_codes,
            "order_object": notice.get("orderObject"),
            "buyer_name": notice.get("organizationName"),
            "buyer_city": notice.get("organizationCity"),
        })
    return rows


def store_results(
    rows: list[dict],
    tenant_id: str,
    db_dsn: str = "dbname=terraos user=postgres host=localhost",
) -> int:
    if not rows:
        return 0
    conn = psycopg2.connect(db_dsn)
    try:
        with conn.cursor() as cur:
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                values = [
                    (
                        tenant_id,
                        r["ocds_tender_id"], r["bzp_number"], r["result_notice_number"],
                        r["procedure_result"], r["contractor_name"], r["contractor_nip"],
                        r["contractor_city"], r["winning_price_pln"], r["lowest_price_pln"],
                        r["highest_price_pln"], r["estimated_value_pln"], r["offers_count"],
                        r["published_at"], r["cpv_codes"], r["order_object"],
                        r["buyer_name"], r["buyer_city"],
                    )
                    for r in batch
                ]
                execute_values(
                    cur,
                    """INSERT INTO market_results (
                        tenant_id, ocds_tender_id, bzp_number, result_notice_number,
                        procedure_result, contractor_name, contractor_nip, contractor_city,
                        winning_price_pln, lowest_price_pln, highest_price_pln, estimated_value_pln,
                        offers_count, published_at, cpv_codes, order_object, buyer_name, buyer_city
                    ) VALUES %s
                    ON CONFLICT (result_notice_number, contractor_name) DO NOTHING""",
                    values,
                )
                conn.commit()
            cur.execute(
                "SELECT count(*) FROM market_results WHERE tenant_id = %s", (tenant_id,)
            )
            row = cur.fetchone()
            total: int = row[0] if row else 0
        return total
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="BZP Result Notice Scraper → market_results")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--date-from", type=str)
    parser.add_argument("--date-to", type=str)
    parser.add_argument("--order-type", default="Works", choices=["Works", "Supplies", "Services"])
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--tenant-id", default="00000000-0000-0000-0000-000000000001")
    parser.add_argument("--db-dsn", default="host=127.0.0.1 dbname=terraos user=terraos")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    if args.date_from:
        date_from = args.date_from
        date_to = args.date_to or now.strftime("%Y-%m-%d")
    else:
        date_from = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")

    logger.info("Fetching BZP TenderResultNotice: %s → %s (%s)", date_from, date_to, args.order_type)
    notices = fetch_result_notices(date_from, date_to, args.order_type, max_pages=args.max_pages)
    logger.info("Fetched %d unique notices", len(notices))

    all_rows: list[dict] = []
    for notice in notices:
        all_rows.extend(transform_notice(notice))
    logger.info("Transformed into %d market_result rows", len(all_rows))

    if args.dry_run:
        for r in all_rows[:5]:
            logger.info(
                "  %s | %s | %.2f PLN",
                r["contractor_name"][:30],
                r["result_notice_number"],
                r["winning_price_pln"] or 0,
            )
        logger.info("DRY RUN — not storing to DB")
        return

    inserted = store_results(all_rows, args.tenant_id, args.db_dsn)
    logger.info("Total rows in market_results: %d", inserted)


if __name__ == "__main__":
    main()
