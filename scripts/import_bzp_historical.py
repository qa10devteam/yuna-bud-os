"""Historyczny import wyników przetargów BZP (TenderResultNotice) do bzp_results i market_results.

Używa DZIAŁAJĄCEGO API: https://ezamowienia.gov.pl/mo-board/api/v1/notice
(search.uzp.gov.pl jest nieaktywny — NXDOMAIN)

Uruchomienie:
    cd /home/ubuntu/terra-os
    .venv/bin/python3.12 scripts/import_bzp_historical.py --days-back 30
    .venv/bin/python3.12 scripts/import_bzp_historical.py --days-back 30 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone, date
from typing import Optional

# Dodaj ścieżki
sys.path.insert(0, '/home/ubuntu/terra-os/packages/db')
sys.path.insert(0, '/home/ubuntu/terra-os/packages/vendor')
sys.path.insert(0, '/home/ubuntu/terra-os/packages/shared')
sys.path.insert(0, '/home/ubuntu/terra-os/services/api')
sys.path.insert(0, '/home/ubuntu/terra-os')

import httpx
from sqlalchemy import text
from terra_db.session import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BZP_API = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
PAGE_SIZE = 100

VOIVODESHIP_NUTS = {
    "dolnośląskie": "PL51", "kujawsko-pomorskie": "PL61", "lubelskie": "PL81",
    "lubuskie": "PL43", "łódzkie": "PL71", "małopolskie": "PL21", "mazowieckie": "PL91",
    "opolskie": "PL52", "podkarpackie": "PL82", "podlaskie": "PL84", "pomorskie": "PL63",
    "śląskie": "PL22", "świętokrzyskie": "PL72", "warmińsko-mazurskie": "PL62",
    "wielkopolskie": "PL41", "zachodniopomorskie": "PL42",
}

NUTS_VOIVODESHIP = {v: k for k, v in VOIVODESHIP_NUTS.items()}


def parse_price_from_html(html: str, pattern: str) -> Optional[float]:
    text_clean = re.sub(r"<[^>]+>", " ", html)
    text_clean = re.sub(r"\s+", " ", text_clean)
    match = re.search(pattern, text_clean)
    if match:
        raw = match.group(1).strip()
        raw = raw.replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def extract_prices_from_html(html: str) -> dict:
    prices = {}
    prices["estimated_value"] = parse_price_from_html(
        html, r"Warto[śs][ćc] zam[óo]wienia[^<:]*[:\s]+([\d\s,\.]+)\s*(?:PLN|zł)"
    )
    prices["lowest_price"] = parse_price_from_html(
        html, r"6\.2\.[^\d]*[\d]+[\s\S]*?([\d\s]+(?:,\d+)?)\s*PLN"
    )
    # Cena wygranej — 6.4 lub "udzielono zamówienia"
    prices["winning_price"] = parse_price_from_html(
        html, r"6\.4\.[^\d]*[\d]+[\s\S]*?([\d\s]+(?:,\d+)?)\s*PLN"
    )
    prices["highest_price"] = parse_price_from_html(
        html, r"6\.3\.[^\d]*[\d]+[\s\S]*?([\d\s]+(?:,\d+)?)\s*PLN"
    )
    # Liczba ofert
    offers_match = re.search(
        r"6\.1\.\)[^\d]*(\d+)",
        re.sub(r"<[^>]+>", " ", html),
    )
    if offers_match:
        prices["offers_count"] = int(offers_match.group(1))
    
    # Wartość umowy (sekcja 8.2) — fallback dla ceny wygranej
    contract_value = parse_price_from_html(
        html, r"8\.2\.[^<]*Warto[śs][ćc][^<]*<[^>]+>([\d\s,\.]+)\s*PLN"
    )
    if not prices.get("winning_price") and contract_value:
        prices["winning_price"] = contract_value
    
    return prices


def nuts_to_voivodeship_name(nuts_code: str) -> Optional[str]:
    """Zamień kod NUTS (np. PL22) na nazwę województwa."""
    # Skróć do PL + 2 znaki
    code = nuts_code[:4] if len(nuts_code) >= 4 else nuts_code
    return NUTS_VOIVODESHIP.get(code)


async def fetch_notices(
    date_from: str,
    date_to: str,
    order_type: str = "Works",
    max_pages_per_day: int = 50,
) -> list[dict]:
    """Pobierz ogłoszenia z API ezamowienia.gov.pl."""
    all_notices: dict[str, dict] = {}
    
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0),
        follow_redirects=True,
        headers={"Accept": "application/json"},
    ) as client:
        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
        current = start
        
        while current <= end:
            day_str = current.isoformat()
            page = 0
            day_count = 0
            
            while page < max_pages_per_day:
                params = {
                    "pageSize": PAGE_SIZE,
                    "pageNumber": page,
                    "NoticeType": "TenderResultNotice",
                    "PublicationDateFrom": day_str,
                    "PublicationDateTo": day_str,
                    "OrderType": order_type,
                }
                
                try:
                    resp = await client.get(BZP_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.warning("Błąd dla dnia %s strona %d: %s", day_str, page, exc)
                    break
                
                if not data:
                    break
                
                for n in data:
                    nn = n.get("noticeNumber", "")
                    if nn and nn not in all_notices:
                        all_notices[nn] = n
                        day_count += 1
                
                if len(data) < PAGE_SIZE:
                    break
                page += 1
                await asyncio.sleep(0.3)  # rate limit
            
            if day_count:
                logger.info("Dzień %s (%s): +%d ogłoszeń (stron: %d, łącznie: %d)",
                           day_str, order_type, day_count, page + 1, len(all_notices))
            
            current += timedelta(days=1)
    
    return list(all_notices.values())


def transform_to_bzp_result(notice: dict) -> Optional[dict]:
    """Zamień ogłoszenie z API na rekord dla bzp_results."""
    notice_num = notice.get("noticeNumber", "").strip()
    if not notice_num:
        return None
    
    # Wyciągnij wykonawców
    contractors = notice.get("contractors") or []
    contractor_name = None
    contractor_nip = None
    contractor_city = None
    
    if contractors:
        c = contractors[0]
        raw_cn = c.get("contractorName") or ""
        contractor_name = raw_cn.strip() if raw_cn else None
        raw_nip = c.get("contractorNationalId") or ""
        # Wyczyść NIP/REGON
        nip_clean = re.sub(r"[^\d]", "", raw_nip)
        contractor_nip = nip_clean if nip_clean else None
        contractor_city = c.get("contractorCity")
    
    if not contractor_name:
        return None
    
    # Pobierz wartość z HTML
    html = notice.get("htmlBody", "")
    prices = extract_prices_from_html(html)
    awarded_value = prices.get("winning_price") or prices.get("estimated_value")
    
    # CPV - pierwszy kod
    cpv_raw = notice.get("cpvCode", "") or ""
    cpv_main = cpv_raw.split(" ")[0].strip()[:8] if cpv_raw else None
    
    # Województwo
    province_code = notice.get("organizationProvince", "") or ""
    voivodeship_name = nuts_to_voivodeship_name(province_code)
    if not voivodeship_name and province_code:
        voivodeship_name = province_code  # fallback: zachowaj kod NUTS
    
    # Daty
    pub_date_raw = notice.get("publicationDate", "")
    try:
        publication_date = datetime.fromisoformat(pub_date_raw.replace("Z", "+00:00")).date() if pub_date_raw else None
    except Exception:
        publication_date = None
    
    return {
        "notice_number": notice_num,
        "contract_number": notice.get("bzpNumber"),
        "original_notice": None,
        "buyer_name": notice.get("organizationName", "").strip() or None,
        "buyer_regon": None,
        "contractor_name": contractor_name,
        "contractor_nip": contractor_nip,
        "awarded_value": awarded_value,
        "currency": "PLN",
        "cpv_main": cpv_main,
        "voivodeship": voivodeship_name,
        "awarded_date": None,
        "publication_date": publication_date,
        "raw": notice,
        "_contractor_city": contractor_city,
        "_prices": prices,
        "_cpv_raw": cpv_raw,
        "_tender_id": notice.get("tenderId"),
        "_procedure_result": notice.get("procedureResult"),
        "_buyer_city": notice.get("organizationCity"),
        "_order_object": notice.get("orderObject"),
    }


def upsert_bzp_results(records: list[dict], dry_run: bool = False) -> int:
    """Wstaw/zaktualizuj rekordy w bzp_results."""
    if not records:
        return 0
    
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
            cpv_main         = EXCLUDED.cpv_main,
            raw              = EXCLUDED.raw
    """)
    
    engine = get_engine()
    saved = 0
    errors = 0
    
    with engine.begin() as conn:
        for rec in records:
            if dry_run:
                saved += 1
                continue
            try:
                rec_db = {
                    "notice_number": rec["notice_number"],
                    "contract_number": rec.get("contract_number"),
                    "original_notice": rec.get("original_notice"),
                    "buyer_name": rec.get("buyer_name"),
                    "buyer_regon": rec.get("buyer_regon"),
                    "contractor_name": rec["contractor_name"],
                    "contractor_nip": rec.get("contractor_nip"),
                    "awarded_value": rec.get("awarded_value"),
                    "currency": rec.get("currency", "PLN"),
                    "cpv_main": rec.get("cpv_main"),
                    "voivodeship": rec.get("voivodeship"),
                    "awarded_date": rec.get("awarded_date"),
                    "publication_date": rec.get("publication_date"),
                    "raw": json.dumps(rec.get("raw", {}), ensure_ascii=False),
                }
                conn.execute(upsert_sql, rec_db)
                saved += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    logger.warning("Pominięto %s: %s", rec.get("notice_number"), e)
    
    if errors:
        logger.warning("Łączna liczba błędów przy wstawianiu: %d", errors)
    return saved


def insert_market_results(records: list[dict], dry_run: bool = False) -> int:
    """Wstaw rekordy do market_results na podstawie sparsowanych danych."""
    if not records:
        return 0
    
    insert_sql = text("""
        INSERT INTO market_results (
            ocds_tender_id, bzp_number, result_notice_number,
            procedure_result, contractor_name, contractor_nip, contractor_city,
            winning_price_pln, lowest_price_pln, highest_price_pln, estimated_value_pln,
            offers_count, published_at, cpv_codes, order_object, buyer_name, buyer_city
        ) VALUES (
            :ocds_tender_id, :bzp_number, :result_notice_number,
            :procedure_result, :contractor_name, :contractor_nip, :contractor_city,
            :winning_price_pln, :lowest_price_pln, :highest_price_pln, :estimated_value_pln,
            :offers_count, :published_at, :cpv_codes, :order_object, :buyer_name, :buyer_city
        )
        ON CONFLICT (result_notice_number, contractor_name) DO NOTHING
    """)
    
    engine = get_engine()
    saved = 0
    errors = 0
    
    if dry_run:
        return len(records)
    
    # Każdy rekord w osobnej transakcji aby błąd nie abortował całej serii
    for rec in records:
        try:
            prices = rec.get("_prices", {})
            cpv_raw = rec.get("_cpv_raw", "")
            cpv_codes = [c.split(" ")[0].strip() for c in cpv_raw.split(",") if c.strip()] if cpv_raw else []
            
            pub_date = rec.get("publication_date")
            pub_at = datetime(pub_date.year, pub_date.month, pub_date.day, tzinfo=timezone.utc) if pub_date else None
            
            with engine.begin() as conn:
                conn.execute(insert_sql, {
                    "ocds_tender_id": rec.get("_tender_id"),
                    "bzp_number": rec.get("contract_number"),
                    "result_notice_number": rec["notice_number"],
                    "procedure_result": rec.get("_procedure_result"),
                    "contractor_name": rec["contractor_name"],
                    "contractor_nip": rec.get("contractor_nip"),
                    "contractor_city": rec.get("_contractor_city"),
                    "winning_price_pln": prices.get("winning_price"),
                    "lowest_price_pln": prices.get("lowest_price"),
                    "highest_price_pln": prices.get("highest_price"),
                    "estimated_value_pln": prices.get("estimated_value"),
                    "offers_count": prices.get("offers_count"),
                    "published_at": pub_at,
                    "cpv_codes": cpv_codes if cpv_codes else None,
                    "order_object": rec.get("_order_object"),
                    "buyer_name": rec.get("buyer_name"),
                    "buyer_city": rec.get("_buyer_city"),
                })
            saved += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning("market_results pominięto %s: %s", rec.get("notice_number"), e)
    
    if errors:
        logger.warning("market_results łączna liczba błędów: %d", errors)
    return saved


async def run_import(
    days_back: int = 30,
    dry_run: bool = False,
    order_types: list[str] | None = None,
    max_pages_per_day: int = 50,
) -> dict:
    if order_types is None:
        order_types = ["Works", "Supplies", "Services"]
    
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d")
    
    logger.info("Import BZP ResultNotice: %s → %s (%d dni)", date_from, date_to, days_back)
    logger.info("OrderTypes: %s | dry_run=%s | max_pages_per_day=%d", order_types, dry_run, max_pages_per_day)
    
    all_notices: dict[str, dict] = {}
    
    for order_type in order_types:
        logger.info("Pobieranie: OrderType=%s...", order_type)
        notices = await fetch_notices(date_from, date_to, order_type, max_pages_per_day=max_pages_per_day)
        before = len(all_notices)
        for n in notices:
            nn = n.get("noticeNumber", "")
            if nn and nn not in all_notices:
                all_notices[nn] = n
        logger.info("OrderType=%s: %d ogłoszeń (+%d nowych)", order_type, len(notices), len(all_notices) - before)
    
    logger.info("Łącznie pobrano: %d unikalnych ogłoszeń", len(all_notices))
    
    # Parsuj
    parsed = []
    skipped = 0
    for notice in all_notices.values():
        rec = transform_to_bzp_result(notice)
        if rec:
            parsed.append(rec)
        else:
            skipped += 1
    
    logger.info("Sparsowano: %d OK, %d pominięto (brak wykonawcy/numeru)", len(parsed), skipped)
    
    # Wstaw do bzp_results
    saved_bzp = upsert_bzp_results(parsed, dry_run=dry_run)
    logger.info("bzp_results: zapisano %d rekordów%s", saved_bzp, " (dry-run)" if dry_run else "")
    
    # Wstaw do market_results
    saved_market = insert_market_results(parsed, dry_run=dry_run)
    logger.info("market_results: zapisano %d rekordów%s", saved_market, " (dry-run)" if dry_run else "")
    
    return {
        "fetched": len(all_notices),
        "parsed": len(parsed),
        "skipped": skipped,
        "saved_bzp": saved_bzp,
        "saved_market": saved_market,
        "dry_run": dry_run,
    }


def main():
    ap = argparse.ArgumentParser(description="Import historyczny BZP ResultNotice → bzp_results + market_results")
    ap.add_argument("--days-back", type=int, default=30, help="Liczba dni wstecz (domyślnie 30)")
    ap.add_argument("--dry-run", action="store_true", help="Tylko test, bez zapisu do DB")
    ap.add_argument("--order-type", choices=["Works", "Supplies", "Services", "all"],
                    default="all", help="Typ zamówienia (domyślnie all)")
    args = ap.parse_args()
    
    if args.order_type == "all":
        order_types = ["Works", "Supplies", "Services"]
    else:
        order_types = [args.order_type]
    
    result = asyncio.run(run_import(
        days_back=args.days_back,
        dry_run=args.dry_run,
        order_types=order_types,
    ))
    
    print("\n" + "="*60)
    print("WYNIKI IMPORTU BZP:")
    print(f"  Pobrano z API:          {result['fetched']:,}")
    print(f"  Sparsowano poprawnie:   {result['parsed']:,}")
    print(f"  Pominięto (brak danych):{result['skipped']:,}")
    print(f"  Zapisano bzp_results:   {result['saved_bzp']:,}")
    print(f"  Zapisano market_results:{result['saved_market']:,}")
    print(f"  Tryb:                   {'DRY-RUN (bez zapisu)' if result['dry_run'] else 'PRODUKCJA'}")
    print("="*60)
    
    return result


if __name__ == "__main__":
    main()
