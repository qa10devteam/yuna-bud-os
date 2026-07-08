"""BZP Result Notice Scraper → market_results table.

Fetches TenderResultNotice from BZP API (ogłoszenia o wyniku postępowania).
Extracts: who won, for how much, estimated value, offers count.

Usage:
    python3 bzp_result_scraper.py --days 30 --order-type Works
    python3 bzp_result_scraper.py --date-from 2026-06-01 --date-to 2026-07-08
"""

import argparse
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BZP_API = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
PAGE_SIZE = 100


def parse_price_from_html(html: str, pattern: str) -> Optional[float]:
    """Extract price value from HTML body text using regex pattern."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    match = re.search(pattern, text)
    if match:
        val = match.group(1).replace(" ", "").replace(",", ".")
        try:
            return float(val)
        except ValueError:
            return None
    return None


def extract_prices_from_html(html: str) -> dict:
    """Extract all price data from BZP result notice HTML body."""
    prices = {}

    # 4.3.) Wartość zamówienia: 447185,75 PLN
    prices["estimated_value"] = parse_price_from_html(
        html, r"Warto[śs][ćc] zam[óo]wienia[:\s]+([\d\s,\.]+)\s*(?:PLN|zł)"
    )

    # 6.2.) Cena lub koszt oferty z najniższą ceną: 351165,00 PLN
    prices["lowest_price"] = parse_price_from_html(
        html, r"najni[żz]sz[ąa] cen[ąa][^:]*:[:\s]*([\d\s,\.]+)\s*(?:PLN|zł)"
    )

    # 6.3.) Cena lub koszt oferty z najwyższą ceną: 627300,00 PLN
    prices["highest_price"] = parse_price_from_html(
        html, r"najwy[żz]sz[ąa] cen[ąa][^:]*:[:\s]*([\d\s,\.]+)\s*(?:PLN|zł)"
    )

    # 6.4.) Cena lub koszt oferty wykonawcy, któremu udzielono zamówienia: X PLN
    prices["winning_price"] = parse_price_from_html(
        html, r"kt[óo]remu udzielono[^:]*:[:\s]*([\d\s,\.]+)\s*(?:PLN|zł)"
    )

    # 6.1.2.) Liczba ofert składanych: N
    offers_match = re.search(r"Liczba ofert sk[łl]adanych[:\s]*(\d+)", re.sub(r"<[^>]+>", " ", html))
    if offers_match:
        prices["offers_count"] = int(offers_match.group(1))

    return prices


def fetch_result_notices(
    date_from: str,
    date_to: str,
    order_type: str = "Works",
    max_pages: int = 50,
) -> list[dict]:
    """Fetch TenderResultNotice from BZP API, splitting into day-windows to bypass 100-result limit."""
    from datetime import date, timedelta as td

    all_notices = {}  # keyed by noticeNumber for global dedup
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)

    with httpx.Client(timeout=30) as client:
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
                resp = client.get(BZP_API, params=params)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                # Post-filter by orderType
                filtered = [n for n in data if n.get("orderType") == order_type]
                for n in filtered:
                    nn = n.get("noticeNumber", "")
                    if nn and nn not in all_notices:
                        all_notices[nn] = n
                        day_count += 1

                if len(data) < PAGE_SIZE:
                    break
                page += 1

            if day_count > 0:
                logger.info("Day %s: %d new notices (total unique: %d)", day_str, day_count, len(all_notices))
            current += td(days=1)

    return list(all_notices.values())


def transform_notice(notice: dict) -> list[dict]:
    """Transform a BZP result notice into market_results rows (one per contractor)."""
    html = notice.get("htmlBody", "")
    prices = extract_prices_from_html(html)

    contractors = notice.get("contractors") or []
    # Filter out contractors without names
    contractors = [c for c in contractors if c.get("contractorName")]
    if not contractors:
        # Use buyer as placeholder when no contractors listed (cancelled or unknown)
        contractors = [{"contractorName": notice.get("procedureResult", "BRAK DANYCH"), "contractorNationalId": None, "contractorCity": None}]

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


def store_results(rows: list[dict], tenant_id: str, db_dsn: str = "dbname=terraos user=postgres host=localhost"):
    """Insert market results into DB, skip duplicates."""
    if not rows:
        return 0

    conn = psycopg2.connect(db_dsn)
    try:
        with conn.cursor() as cur:
            # Insert in batches to avoid memory issues
            batch_size = 500
            total_inserted = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                values = [
                    (
                        tenant_id,
                        r["ocds_tender_id"],
                        r["bzp_number"],
                        r["result_notice_number"],
                        r["procedure_result"],
                        r["contractor_name"],
                        r["contractor_nip"],
                        r["contractor_city"],
                        r["winning_price_pln"],
                        r["lowest_price_pln"],
                        r["highest_price_pln"],
                        r["estimated_value_pln"],
                        r["offers_count"],
                        r["published_at"],
                        r["cpv_codes"],
                        r["order_object"],
                        r["buyer_name"],
                        r["buyer_city"],
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
            # Get actual count
            cur.execute("SELECT count(*) FROM market_results WHERE tenant_id = %s", (tenant_id,))
            total_inserted = cur.fetchone()[0]
        return total_inserted
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="BZP Result Notice Scraper → market_results")
    parser.add_argument("--days", type=int, default=90, help="Fetch results from last N days")
    parser.add_argument("--date-from", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-to", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--order-type", default="Works", choices=["Works", "Supplies", "Services"])
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to fetch (100 items/page)")
    parser.add_argument("--tenant-id", default="00000000-0000-0000-0000-000000000001", help="Tenant UUID")
    parser.add_argument("--db-dsn", default="host=127.0.0.1 dbname=terraos user=terraos")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    args = parser.parse_args()

    if args.date_from:
        date_from = args.date_from
        date_to = args.date_to or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        now = datetime.now(timezone.utc)
        date_from = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")

    logger.info("Fetching BZP TenderResultNotice: %s → %s (%s)", date_from, date_to, args.order_type)

    notices = fetch_result_notices(date_from, date_to, args.order_type, max_pages=args.max_pages)
    # Deduplicate by noticeNumber (BZP API returns duplicates across pages)
    seen = set()
    unique_notices = []
    for n in notices:
        nn = n.get("noticeNumber", "")
        if nn not in seen:
            seen.add(nn)
            unique_notices.append(n)
    logger.info("Fetched %d notices, %d unique after dedup", len(notices), len(unique_notices))

    all_rows = []
    for notice in unique_notices:
        rows = transform_notice(notice)
        all_rows.extend(rows)

    logger.info("Transformed into %d market_result rows", len(all_rows))

    if args.dry_run:
        for r in all_rows[:5]:
            logger.info("  %s | %s | %.2f PLN | %s",
                        r["contractor_name"][:30],
                        r["result_notice_number"],
                        r["winning_price_pln"] or 0,
                        r["order_object"][:50] if r["order_object"] else "")
        logger.info("DRY RUN — not storing to DB")
        return

    inserted = store_results(all_rows, args.tenant_id, args.db_dsn)
    logger.info("Total rows in market_results: %d (from %d transformed rows)", inserted, len(all_rows))


if __name__ == "__main__":
    main()
