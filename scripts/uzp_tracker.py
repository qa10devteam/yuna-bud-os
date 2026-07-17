#!/usr/bin/env python3
"""UZP Change Tracker — monitoruje zmiany prawne i przetargowe z portalu UZP.

Źródła:
1. www.gov.pl/web/uzp/aktualnosci — aktualności UZP (zmiany prawa, interpretacje)
2. www.gov.pl/web/uzp/krajowy-plan-zamowien-publicznych — plany zamówień
3. ezamowienia.gov.pl — nowe ogłoszenia TED/e-zamówienia (BZP API)

Użycie:
    python3 uzp_tracker.py --dry-run   # test bez zapisu do DB
    python3 uzp_tracker.py              # normalny tryb — zapis do DB
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Konfiguracja ─────────────────────────────────────────────────────────────

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://terraos:terraos@127.0.0.1:5432/terraos",
)
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-20250514-v1:0")
HTTP_TIMEOUT = 15.0
MAX_DAYS_BACK = 7

# gov.pl przekierowuje uzp.gov.pl → www.gov.pl/web/uzp/
UZP_NEWS_URL = "https://www.gov.pl/web/uzp/aktualnosci"
UZP_PLANS_URL = "https://www.gov.pl/web/uzp/krajowy-plan-zamowien-publicznych"
UZP_BASE = "https://www.gov.pl"

# e-zamówienia API — ogłoszenia BZP
EZAM_BZP_URL = "https://ezamowienia.gov.pl/mo-board/api/v1/notice/search"
EZAM_API_URL = "https://ezamowienia.gov.pl/mp-client/api/list/ocds/publication-spot-pl/tenders"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TerraOS-UZP-Tracker/1.0; +https://terra.ai)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}

# ─── Schemat tabeli DB ────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS uzp_changes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMPTZ,
    summary TEXT,
    category TEXT,
    severity TEXT DEFAULT 'info',
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_uzp_changes_source_created ON uzp_changes(source, created_at DESC);
"""

# ─── Słowa kluczowe do klasyfikacji ──────────────────────────────────────────

LEGAL_KEYWORDS = [
    "zmiana", "nowelizacja", "ustawa", "rozporządzenie", "dyrektywa",
    "wyrok", "certyfikacja", "obowiązek", "przepis", "aktualizacja informacji",
    "wejście w życie", "stosowanie przepisów",
]

HIGH_SEVERITY_KEYWORDS = [
    "ustawa", "nowelizacja", "wyrok tsue", "wyrok kio",
    "certyfikacja", "wejście w życie",
]

ARTICLE_URL_KEYWORDS = [
    "zamow", "przetarg", "ustaw", "zmian", "aktuali", "ogłosz",
    "interpretacja", "wyrok", "opinia", "seminarium", "warsztaty",
    "certyfikacja", "szkolenie", "informacja", "krajowy-plan",
    "aktualizacja", "obowiazki", "przedluzenie",
]

# ─── Scraper: UZP aktualności (gov.pl) ───────────────────────────────────────

async def fetch_uzp_news(client: httpx.AsyncClient, since: datetime) -> list[dict]:
    """Pobiera aktualności z www.gov.pl/web/uzp/aktualnosci."""
    items = []
    try:
        resp = await client.get(UZP_NEWS_URL, headers=HTTP_HEADERS, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text

        # Wyciągnij linki do artykułów z gov.pl/web/uzp/
        all_links = re.findall(r'<a[^>]+href="(/web/uzp/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        seen_titles: set[str] = set()
        seen_hrefs: set[str] = set()

        for href, raw_text in all_links:
            # Oczyść tekst z tagów HTML
            title = re.sub(r'<[^>]+>', '', raw_text).strip()
            title = ' '.join(title.split())

            # Filtruj nawigację i duplikaty
            if len(title) < 10 or title in seen_titles or href in seen_hrefs:
                continue

            # Sprawdź czy to artykuł merytoryczny (nie nawigacja)
            href_lower = href.lower()
            if not any(kw in href_lower for kw in ARTICLE_URL_KEYWORDS):
                # Sprawdź czy tytuł jest merytoryczny
                title_lower = title.lower()
                if not any(kw in title_lower for kw in LEGAL_KEYWORDS + ["seminarium", "warsztaty", "szkolenie"]):
                    continue

            seen_titles.add(title)
            seen_hrefs.add(href)

            full_url = UZP_BASE + href
            title_lower = title.lower()
            severity = "high" if any(kw in title_lower for kw in HIGH_SEVERITY_KEYWORDS) else "info"
            category = "legal_change" if any(kw in title_lower for kw in LEGAL_KEYWORDS) else "announcement"

            items.append({
                "source": "uzp_news",
                "title": title[:500],
                "url": full_url,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "category": category,
                "severity": severity,
                "raw": {"href": href},
            })

            if len(items) >= 15:
                break

        logger.info("UZP aktualności: znaleziono %d pozycji", len(items))

    except Exception as e:
        logger.error("Błąd pobierania UZP aktualności: %s", e)

    return items


# ─── Scraper: UZP plany zamówień ──────────────────────────────────────────────

async def fetch_uzp_plans(client: httpx.AsyncClient, since: datetime) -> list[dict]:
    """Pobiera informacje o krajowym planie zamówień publicznych."""
    items = []
    try:
        # Najpierw spróbuj dedykowanej strony planów
        url = UZP_PLANS_URL
        resp = await client.get(url, headers=HTTP_HEADERS, follow_redirects=True)

        if resp.status_code == 404:
            # Fallback na główną stronę UZP
            url = "https://www.gov.pl/web/uzp/strona-glowna"
            resp = await client.get(url, headers=HTTP_HEADERS, follow_redirects=True)

        resp.raise_for_status()
        html = resp.text

        # Szukaj linków do planów
        plan_patterns = [
            r'<a[^>]+href="(/web/uzp/[^"]*(?:plan|zamow|kpz)[^"]*)"[^>]*>(.*?)</a>',
            r'<a[^>]+href="(/web/uzp/[^"]+)"[^>]*>\s*([^<]{15,200}(?:plan|zamówi)[^<]*)\s*</a>',
        ]
        seen: set[str] = set()
        for pat in plan_patterns:
            for href, raw_text in re.findall(pat, html, re.DOTALL | re.IGNORECASE):
                title = re.sub(r'<[^>]+>', '', raw_text).strip()
                title = ' '.join(title.split())
                if len(title) < 10 or title in seen:
                    continue
                seen.add(title)
                items.append({
                    "source": "uzp_plans",
                    "title": title[:500],
                    "url": UZP_BASE + href,
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "category": "announcement",
                    "severity": "info",
                    "raw": {"href": href},
                })

        # Fallback: ogólna informacja o stronie planów
        if not items:
            items.append({
                "source": "uzp_plans",
                "title": "Krajowy Plan Zamówień Publicznych — strona UZP (aktualizacja)",
                "url": url,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "category": "announcement",
                "severity": "info",
                "raw": {"status": "page_fetched", "final_url": str(resp.url)},
            })

        logger.info("UZP plany: znaleziono %d pozycji", len(items))

    except Exception as e:
        logger.error("Błąd pobierania UZP planów: %s", e)

    return items


# ─── Scraper: e-zamówienia / BZP API ─────────────────────────────────────────

async def fetch_ezamowienia(client: httpx.AsyncClient, since: datetime) -> list[dict]:
    """Pobiera nowe ogłoszenia z e-zamówienia.gov.pl (BZP API)."""
    items = []
    try:
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        # BZP API — szukaj zamówień z ostatnich dni
        payload = {
            "searchPhrase": "",
            "pageSize": 20,
            "pageNumber": 1,
            "sortingField": "publicationDate",
            "sortingOrder": "DESC",
            "filterNoticeType": ["ContractNotice"],
            "filterPublicationDateFrom": since.strftime("%Y-%m-%d"),
        }

        resp = await client.post(
            EZAM_BZP_URL,
            json=payload,
            headers={
                **HTTP_HEADERS,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            follow_redirects=True,
        )

        if resp.status_code == 200:
            data = resp.json()
            notices = data.get("noticeList", data.get("items", data if isinstance(data, list) else []))
            for rec in (notices or [])[:20]:
                if not isinstance(rec, dict):
                    continue
                title = (
                    rec.get("name") or
                    rec.get("title") or
                    rec.get("subject") or
                    f"Ogłoszenie BZP {rec.get('noticeNumber', '')}"
                )
                notice_number = rec.get("noticeNumber") or rec.get("id") or ""
                url = f"https://ezamowienia.gov.pl/mo-board/api/v1/notice/{notice_number}" if notice_number else EZAM_BZP_URL
                pub_date = rec.get("publicationDate") or rec.get("date") or datetime.now(timezone.utc).isoformat()

                items.append({
                    "source": "ezamowienia",
                    "title": str(title)[:500],
                    "url": url,
                    "published_at": pub_date,
                    "category": "new_tender",
                    "severity": "info",
                    "raw": {k: v for k, v in rec.items() if k in (
                        "noticeNumber", "name", "title", "publicationDate",
                        "buyerName", "estimatedValue", "cpvMainCode",
                    )},
                })
        else:
            logger.warning("BZP API status %s — próbuję OCDS endpoint", resp.status_code)
            raise httpx.HTTPStatusError("", request=resp.request, response=resp)

    except (httpx.HTTPStatusError, Exception) as e:
        if "HTTPStatusError" not in type(e).__name__:
            logger.warning("BZP POST failed (%s), próbuję OCDS API: %s", type(e).__name__, e)

        # Fallback: OCDS API (może zwrócić HTML Angular app)
        try:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            r2 = await client.get(
                EZAM_API_URL,
                params={"limit": 10, "offset": 0, "publishedFrom": since_str},
                headers={**HTTP_HEADERS, "Accept": "application/json"},
                follow_redirects=True,
            )
            ct = r2.headers.get("content-type", "")
            if "json" in ct and r2.status_code == 200:
                data = r2.json()
                records = (
                    data.get("tenders") or data.get("items") or
                    data.get("releases") or data.get("data") or
                    (data if isinstance(data, list) else [])
                )
                for rec in (records or [])[:20]:
                    if not isinstance(rec, dict):
                        continue
                    title = rec.get("title") or rec.get("ocid") or "Ogłoszenie OCDS"
                    items.append({
                        "source": "ezamowienia",
                        "title": str(title)[:500],
                        "url": rec.get("url") or EZAM_API_URL,
                        "published_at": rec.get("date") or datetime.now(timezone.utc).isoformat(),
                        "category": "new_tender",
                        "severity": "info",
                        "raw": {"ocid": rec.get("ocid"), "title": rec.get("title")},
                    })
            elif r2.status_code == 200:
                # Angular SPA — API niedostępne publicznie, zwróć placeholder
                logger.info("e-zamówienia OCDS zwróciło HTML (SPA) — placeholder")
                items.append({
                    "source": "ezamowienia",
                    "title": "e-Zamówienia BZP — monitorowanie ogłoszeń aktywne",
                    "url": "https://ezamowienia.gov.pl",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "category": "new_tender",
                    "severity": "info",
                    "raw": {"status": "spa_html", "note": "API publiczne niedostępne — używamy BZP API"},
                })
        except Exception as e2:
            logger.error("e-zamówienia OCDS fallback błąd: %s", e2)

    logger.info("e-zamówienia: znaleziono %d ogłoszeń", len(items))
    return items


# ─── Bedrock AI summary ───────────────────────────────────────────────────────

def generate_ai_summary(items: list[dict]) -> str:
    """Generuje AI summary nowych zmian przez Bedrock Claude."""
    if not items:
        return "Brak nowych zmian w monitorowanych źródłach UZP."

    try:
        import boto3

        titles_text = "\n".join(
            f"- [{item['source']}] {item['title']}" for item in items[:30]
        )
        prompt = (
            f"Na podstawie poniższych nowych pozycji z portali UZP i e-zamówień, "
            f"odpowiedz na pytanie: Co najważniejszego zmieniło się w prawie zamówień "
            f"publicznych w Polsce w tym tygodniu?\n\n"
            f"Nowe pozycje:\n{titles_text}\n\n"
            f"Podaj krótkie, konkretne podsumowanie w języku polskim (max 3 akapity)."
        )

        bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }),
            contentType="application/json",
            accept="application/json",
        )
        text = json.loads(response["body"].read())["content"][0]["text"]
        logger.info("Wygenerowano AI summary (%d znaków)", len(text))
        return text

    except Exception as e:
        logger.warning("Bedrock niedostępny: %s — używam prostego summary", e)
        sources = ", ".join(sorted(set(i["source"] for i in items)))
        return (
            f"Znaleziono {len(items)} nowych pozycji ze źródeł: {sources}. "
            f"Bedrock tymczasowo niedostępny — szczegóły w bazie danych."
        )


# ─── Zapis do DB ──────────────────────────────────────────────────────────────

def save_to_db(items: list[dict]) -> int:
    """Zapisuje nowe rekordy do tabeli uzp_changes. Zwraca liczbę wstawionych."""
    if not items:
        return 0

    try:
        import sqlalchemy as sa

        engine = sa.create_engine(DB_URL, future=True)

        with engine.begin() as conn:
            # Twórz tabelę jeśli nie istnieje
            for stmt in CREATE_TABLE_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(sa.text(stmt))

            # Załaduj istniejące tytuły z ostatnich 7 dni per source (anty-duplikacja)
            sources = list(set(i["source"] for i in items))
            last_titles: dict[str, set] = {}
            for source in sources:
                rows = conn.execute(
                    sa.text(
                        "SELECT title FROM uzp_changes "
                        "WHERE source = :src AND created_at > NOW() - INTERVAL '7 days'"
                    ),
                    {"src": source},
                ).fetchall()
                last_titles[source] = {r[0] for r in rows}

            inserted = 0
            for item in items:
                source = item["source"]
                title = item["title"]

                # Skip duplikaty
                if title in last_titles.get(source, set()):
                    logger.debug("Pomijam duplikat: [%s] %s", source, title[:60])
                    continue

                # Parsuj datę
                pub_at = None
                if item.get("published_at"):
                    try:
                        pub_at = datetime.fromisoformat(
                            str(item["published_at"]).replace("Z", "+00:00")
                        )
                    except Exception:
                        pub_at = datetime.now(timezone.utc)

                raw_json = json.dumps(item.get("raw") or {})
                conn.execute(
                    sa.text("""
                        INSERT INTO uzp_changes
                            (source, title, url, published_at, category, severity, raw)
                        VALUES
                            (:source, :title, :url, :published_at, :category, :severity, CAST(:raw AS jsonb))
                    """),
                    {
                        "source": source,
                        "title": title,
                        "url": item.get("url"),
                        "published_at": pub_at,
                        "category": item.get("category", "announcement"),
                        "severity": item.get("severity", "info"),
                        "raw": raw_json,
                    },
                )
                inserted += 1
                last_titles.setdefault(source, set()).add(title)

        logger.info("Zapisano %d nowych rekordów do uzp_changes", inserted)
        return inserted

    except Exception as e:
        logger.error("Błąd zapisu do DB: %s", e)
        return 0


def save_to_file(items: list[dict], path: str = "/tmp/uzp_changes.json") -> None:
    """Fallback: zapisuje do pliku JSON (tryb dry-run lub brak DB)."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Zapisano %d pozycji do %s", len(items), path)
    except Exception as e:
        logger.error("Błąd zapisu do pliku: %s", e)


# ─── Główna logika ────────────────────────────────────────────────────────────

async def main(dry_run: bool = False) -> None:
    since = datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_BACK)
    logger.info(
        "UZP Tracker — startuję (dry_run=%s, since=%s)",
        dry_run,
        since.strftime("%Y-%m-%d"),
    )

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Pobierz wszystkie źródła równolegle
        results = await asyncio.gather(
            fetch_uzp_news(client, since),
            fetch_uzp_plans(client, since),
            fetch_ezamowienia(client, since),
            return_exceptions=True,
        )

    all_items: list[dict] = []
    source_names = ["uzp_news", "uzp_plans", "ezamowienia"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Błąd źródła %s: %s", source_names[i], result)
        elif isinstance(result, list):
            all_items.extend(result)

    logger.info("Łącznie pobranych pozycji: %d", len(all_items))

    if dry_run:
        logger.info("--- DRY RUN — podgląd pozycji ---")
        for item in all_items[:15]:
            sev = f"[{item.get('severity','info')}]"
            print(f"  {sev:8} [{item['source']}] {item['title'][:80]}")
        save_to_file(all_items)
        print(f"\nDRY RUN zakończony: {len(all_items)} pozycji (zapisane do /tmp/uzp_changes.json)")
        return

    # Zapis do DB
    inserted = save_to_db(all_items)

    # AI summary jeśli są nowe rekordy
    if inserted > 0:
        summary = generate_ai_summary(all_items)
        print("\n" + "=" * 60)
        print("SUMMARY UZP — co nowego w prawie zamówień publicznych:")
        print("=" * 60)
        print(summary)
        print("=" * 60)
    else:
        logger.info("Brak nowych pozycji do zapisania")

    print(f"\nRaport: wstawiono {inserted} nowych rekordów do uzp_changes")
    sources_count: dict[str, int] = {}
    for item in all_items:
        sources_count[item["source"]] = sources_count.get(item["source"], 0) + 1
    for src, cnt in sources_count.items():
        print(f"  {src}: {cnt} pozycji pobrano")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UZP Change Tracker")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nie zapisuj do DB — tylko pobierz i pokaż wyniki",
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
