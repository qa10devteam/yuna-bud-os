"""Faza 8 — BIP Connector: scraper zamówień podprogowych z Biuletynów Informacji Publicznej.

BIP sites are decentralized (each municipality has its own).
Strategy:
  1. Fetch subject list from gov.pl API (municipalities, counties)
  2. For each subject → get BIP URL from contact card HTML
  3. Try RSS feed heuristics first (fast, structured)
  4. Fallback: HTML scrape of procurement listing page
  5. Normalize → tender table with source='bip'

Usage:
    python -m services.ingestion.bip_connector --region slaskie --max-sites 50
    python -m services.ingestion.bip_connector --discover-only  # just build site index
"""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class BIPSite:
    """A single BIP site (municipality, county etc.)."""
    subject_id: int
    name: str
    slug: str  # gov.pl slug from API
    bip_url: str = ""  # actual BIP homepage URL
    region: str = ""  # województwo
    county: str = ""  # powiat
    municipality: str = ""  # gmina
    rss_url: str = ""  # discovered RSS feed for procurement
    procurement_page: str = ""  # URL of procurement listing page
    last_scraped: Optional[str] = None
    
    @property
    def source_id(self) -> str:
        return f"bip:{self.subject_id}"


@dataclass
class BIPTender:
    """A tender scraped from a BIP site."""
    title: str
    url: str
    published: Optional[date] = None
    description: str = ""
    bip_site_id: int = 0
    bip_site_name: str = ""
    region: str = ""
    
    @property
    def external_id(self) -> str:
        """Deterministic ID from URL hash."""
        return hashlib.md5(self.url.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOV_BIP_API = "https://aplikacje.gov.pl/app/bip-back/api/subjects"
GOV_BIP_CARD = "https://www.gov.pl/web/bip{slug}"

# Group IDs from gov.pl API
GROUP_GMINY = 100061       # 1664 municipalities
GROUP_POWIATY = 100062     # 271 counties
GROUP_WOJEWODZTWA = 100063 # 16 voivodeships

# Regions mapping (voivodeship slug fragments)
REGIONS = {
    "dolnoslaskie": "dolnośląskie",
    "kujawsko-pomorskie": "kujawsko-pomorskie",
    "lubelskie": "lubelskie",
    "lubuskie": "lubuskie",
    "lodzkie": "łódzkie",
    "malopolskie": "małopolskie",
    "mazowieckie": "mazowieckie",
    "opolskie": "opolskie",
    "podkarpackie": "podkarpackie",
    "podlaskie": "podlaskie",
    "pomorskie": "pomorskie",
    "slaskie": "śląskie",
    "swietokrzyskie": "świętokrzyskie",
    "warminsko-mazurskie": "warmińsko-mazurskie",
    "wielkopolskie": "wielkopolskie",
    "zachodniopomorskie": "zachodniopomorskie",
}

# Common RSS feed URL patterns across different BIP CMS systems
RSS_PATTERNS = [
    "/feeds.xml?name=bip-zampub&co=rss",
    "/feeds.xml?name=zamowienia&co=rss",
    "/rss/zamowienia-publiczne",
    "/rss/zamowienia",
    "/rss.xml?category=zamowienia",
    "/?module=rss&category=zamowienia",
    "/feed/zamowienia",
    "/bip/feeds.xml?name=bip-zampub&co=rss",
]

# Link text patterns that indicate a procurement section
PROCUREMENT_LINK_PATTERNS = re.compile(
    r"(zamówien|przetarg|postępowan|zakup|konkurs.*ofert|zapytani.*ofert|"
    r"zamowien|zamówienia\s+publiczne|zamówienia\s+podprogowe)",
    re.IGNORECASE,
)

# Patterns to extract individual tender items from listing pages
TENDER_ITEM_PATTERNS = [
    # Common: <a href="...">TITLE</a> with date nearby
    re.compile(
        r'<a\s+href="([^"]{10,200})"[^>]*>\s*([^<]{15,300})\s*</a>'
        r'.*?(\d{4}[-./]\d{2}[-./]\d{2}|\d{2}[-./]\d{2}[-./]\d{4})',
        re.DOTALL,
    ),
    # Without date
    re.compile(
        r'<a\s+href="([^"]{10,200})"[^>]*>\s*([^<]{15,300})\s*</a>',
    ),
]


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

def _make_client() -> httpx.Client:
    return httpx.Client(
        timeout=15.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "pl,en;q=0.5",
            "Referer": "https://www.gov.pl/web/bip/spis-podmiotow",
            "Origin": "https://www.gov.pl",
        },
    )


# ---------------------------------------------------------------------------
# Step 1: Fetch subject list from gov.pl API
# ---------------------------------------------------------------------------

def fetch_subjects(client: httpx.Client, parent_id: int) -> list[dict]:
    """Fetch all subjects (SUBJECT type) under a group, using browser endpoint."""
    try:
        resp = client.get(
            GOV_BIP_API,
            params={"archive": "false", "parentId": parent_id},
            timeout=45.0,  # Large groups (1664 gminy) need more time
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("list", [])
        # Separate groups vs subjects
        subjects = [i for i in items if i.get("type") == "SUBJECT"]
        groups = [i for i in items if i.get("type") == "GROUP"]
        # Recurse into sub-groups (max 1 level usually)
        for g in groups:
            if g.get("childCount", 0) > 0:
                try:
                    sub = fetch_subjects(client, g["id"])
                    subjects.extend(sub)
                except Exception as e:
                    logger.warning("Failed to fetch group %s: %s", g.get("name"), e)
        return subjects
    except Exception as e:
        logger.error("Failed to fetch subjects for parentId=%d: %s", parent_id, e)
        return []


def build_site_index(
    client: httpx.Client,
    group_id: int = GROUP_GMINY,
    region_filter: str | None = None,
    max_sites: int = 0,
) -> list[BIPSite]:
    """Build index of BIP sites from gov.pl API."""
    logger.info("Fetching subjects from group %d...", group_id)
    subjects = fetch_subjects(client, group_id)
    logger.info("Found %d subjects", len(subjects))
    
    sites: list[BIPSite] = []
    for subj in subjects:
        slug = subj.get("url", "")
        if not slug:
            continue
        
        # Extract region from slug: /name-REGION-powiat-gmina
        parts = slug.strip("/").split("-")
        region = ""
        for key, display in REGIONS.items():
            if key in slug:
                region = key
                break
        
        if region_filter and region != region_filter:
            continue
        
        site = BIPSite(
            subject_id=subj["id"],
            name=subj.get("name", ""),
            slug=slug,
            region=region,
        )
        sites.append(site)
        
        if max_sites and len(sites) >= max_sites:
            break
    
    logger.info("Index: %d sites (filter=%s)", len(sites), region_filter or "all")
    return sites


# ---------------------------------------------------------------------------
# Step 2: Get BIP URL from contact card HTML
# ---------------------------------------------------------------------------

def fetch_bip_url(client: httpx.Client, site: BIPSite) -> str:
    """Discover BIP URL using heuristic URL patterns based on municipality name.
    
    gov.pl contact cards are no longer publicly accessible (302 redirect).
    Instead we try common BIP URL patterns and verify with HEAD request.
    """
    # Extract city name from slug: /gmina-NAME-region-powiat-city
    slug_parts = site.slug.strip("/").split("-")
    
    # Extract the actual city/municipality name from the subject name
    name_lower = site.name.lower()
    
    # Get city from slug (after gmina-/miasto-/starostwo-powiatowe-w-)
    city = ""
    slug_clean = site.slug.strip("/")
    
    if slug_clean.startswith("gmina-") or slug_clean.startswith("urzad-gminy-") or slug_clean.startswith("urzad-gminy-i-miasta-"):
        # /gmina-bojszowy-slaskie-... → bojszowy
        # /urzad-gminy-bestwina-slaskie-... → bestwina
        # /urzad-gminy-i-miasta-kozieglowy-slaskie-... → kozieglowy
        parts = slug_clean.split("-")
        # Skip prefix: "gmina" (1), "urzad-gminy" (2), "urzad-gminy-i-miasta" (4)
        if slug_clean.startswith("urzad-gminy-i-miasta-"):
            prefix_len = 4
        elif slug_clean.startswith("urzad-gminy-"):
            prefix_len = 2
        else:
            prefix_len = 1
        # City name is between prefix and region name
        for region_key in REGIONS:
            region_idx = None
            for i, p in enumerate(parts):
                if p == region_key or (i > 0 and f"{parts[i-1]}-{p}" == region_key):
                    region_idx = i if parts[i-1] != region_key.split("-")[0] else i - 1
                    break
            if region_idx:
                city = "-".join(parts[prefix_len:region_idx])
                break
        if not city and len(parts) > prefix_len:
            city = parts[prefix_len]
    elif slug_clean.startswith("miasto-") or slug_clean.startswith("urzad-miasta-"):
        parts = slug_clean.split("-")
        prefix_len = 2 if slug_clean.startswith("urzad-miasta-") else 1
        for region_key in REGIONS:
            for i, p in enumerate(parts):
                if p == region_key:
                    city = "-".join(parts[prefix_len:i])
                    break
            if city:
                break
        if not city and len(parts) > prefix_len:
            city = parts[prefix_len]
    elif "starostwo-powiatowe" in slug_clean:
        # /starostwo-powiatowe-w-bielsku-bialej-slaskie-... → bielsko
        m = re.search(r"starostwo-powiatowe-(?:w-)?([^-]+-?[^-]*?)-(?:" + "|".join(REGIONS) + ")", slug_clean)
        if m:
            city = m.group(1).rstrip("-")
    
    if not city:
        # Fallback: extract from name
        m = re.search(r"(?:Gmina|Miasto|w)\s+(\S+)", site.name)
        if m:
            city = m.group(1).lower()
    
    if not city:
        return ""
    
    # Transliterate Polish characters (9 chars each)
    trans = str.maketrans("łóśżźąęćń", "loszzaecn")
    city_ascii = city.translate(trans)
    
    # Generate candidate URLs based on entity type
    is_powiat = "powiat" in name_lower or "starostwo" in name_lower
    
    if is_powiat:
        candidates = [
            f"https://bip.powiat.{city_ascii}.pl",
            f"https://bip.powiat{city_ascii}.pl",
            f"https://www.bip.powiat{city_ascii}.pl",
            f"https://bip.{city_ascii}.powiat.pl",
        ]
    else:
        candidates = [
            f"https://bip.{city_ascii}.pl",
            f"https://www.bip.{city_ascii}.pl",
            f"https://bip.gmina-{city_ascii}.pl",
            f"https://bip.gmina{city_ascii}.pl",
            f"https://bip.um.{city_ascii}.pl",
            f"https://{city_ascii}.bip.info.pl",
            f"https://bip.malopolska.pl/um{city_ascii}",
        ]
    
    for url in candidates:
        try:
            resp = client.head(url, timeout=5.0)
            if resp.status_code in (200, 301, 302):
                # Follow to final URL
                if resp.status_code in (301, 302):
                    final = resp.headers.get("location", url)
                    if final.startswith("/"):
                        from urllib.parse import urlparse as up
                        p = up(url)
                        final = f"{p.scheme}://{p.netloc}{final}"
                    return final
                return str(resp.url) if hasattr(resp, 'url') else url
        except Exception:
            continue
    
    return ""


# ---------------------------------------------------------------------------
# Step 3: Discover RSS feed
# ---------------------------------------------------------------------------

def discover_rss(client: httpx.Client, bip_url: str) -> str:
    """Try common RSS feed patterns to find procurement feed."""
    base = bip_url.rstrip("/")
    
    for pattern in RSS_PATTERNS:
        feed_url = base + pattern
        try:
            resp = client.head(feed_url)
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "xml" in ct or "rss" in ct or "atom" in ct or "text" in ct:
                    # Verify it's actually XML with items
                    resp2 = client.get(feed_url)
                    if "<item" in resp2.text or "<entry" in resp2.text:
                        logger.info("Found RSS feed: %s", feed_url)
                        return feed_url
        except Exception:
            continue
    
    # Try to find RSS from homepage <link> tags
    try:
        resp = client.get(base)
        if resp.status_code == 200:
            rss_links = re.findall(
                r'<link[^>]*type="application/(rss|atom)\+xml"[^>]*href="([^"]+)"',
                resp.text,
            )
            for _, href in rss_links:
                url = urljoin(base, href)
                if any(k in url.lower() for k in ["zam", "przetarg", "procurement"]):
                    return url
            # Also check for feed links in content
            feed_links = re.findall(r'href="([^"]*(?:rss|feed|xml)[^"]*)"', resp.text, re.I)
            for href in feed_links:
                url = urljoin(base, href)
                if any(k in url.lower() for k in ["zam", "przetarg"]):
                    try:
                        r = client.get(url)
                        if "<item" in r.text or "<entry" in r.text:
                            return url
                    except Exception:
                        pass
    except Exception:
        pass
    
    return ""


# ---------------------------------------------------------------------------
# Step 4: Parse RSS feed
# ---------------------------------------------------------------------------

def parse_rss(client: httpx.Client, rss_url: str) -> list[BIPTender]:
    """Parse RSS/Atom feed into tender items."""
    tenders: list[BIPTender] = []
    try:
        resp = client.get(rss_url)
        if resp.status_code != 200:
            return []
        
        root = ET.fromstring(resp.text)
        
        # RSS 2.0
        channel = root.find("channel")
        if channel is not None:
            items = channel.findall("item")
        else:
            # Atom
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall("atom:entry", ns) or root.findall("entry")
        
        for item in items:
            title = (
                item.findtext("title")
                or item.findtext("{http://www.w3.org/2005/Atom}title")
                or ""
            ).strip()
            
            link = (
                item.findtext("link")
                or item.findtext("{http://www.w3.org/2005/Atom}link")
                or ""
            ).strip()
            if not link:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.get("href", "")
            
            pub_date_str = (
                item.findtext("pubDate")
                or item.findtext("{http://www.w3.org/2005/Atom}published")
                or item.findtext("{http://www.w3.org/2005/Atom}updated")
                or ""
            )
            
            desc = (
                item.findtext("description")
                or item.findtext("{http://www.w3.org/2005/Atom}summary")
                or item.findtext("{http://www.w3.org/2005/Atom}content")
                or ""
            ).strip()
            # Strip HTML from description
            desc = re.sub(r"<[^>]+>", " ", desc)
            desc = re.sub(r"\s+", " ", desc).strip()[:500]
            
            pub_date = _parse_date(pub_date_str)
            
            if title and link:
                tenders.append(BIPTender(
                    title=title,
                    url=link,
                    published=pub_date,
                    description=desc,
                ))
    except Exception as e:
        logger.warning("Failed to parse RSS %s: %s", rss_url, e)
    
    return tenders


def _parse_date(s: str) -> Optional[date]:
    """Best-effort date parsing from various formats."""
    if not s:
        return None
    s = s.strip()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 (RSS)
        "%Y-%m-%dT%H:%M:%S%z",         # ISO 8601
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(s[:30], fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Step 5: HTML fallback scraper
# ---------------------------------------------------------------------------

def find_procurement_page(client: httpx.Client, bip_url: str) -> str:
    """Find the procurement listing page by following navigation links."""
    try:
        resp = client.get(bip_url)
        if resp.status_code != 200:
            return ""
        html = resp.text
        
        links = re.findall(r'href="([^"]{1,300})"[^>]*>\s*([^<]{2,100})', html)
        for href, text in links:
            if PROCUREMENT_LINK_PATTERNS.search(text):
                url = urljoin(bip_url, href)
                return url
        
        return ""
    except Exception as e:
        logger.debug("Failed to find procurement page on %s: %s", bip_url, e)
        return ""


def find_sub_procurement_pages(client: httpx.Client, page_url: str) -> list[str]:
    """Find sub-category pages within a procurement listing (depth-2 crawl).
    
    Many BIP sites have structure like:
        Zamówienia publiczne/
            ├── Zamówienia poniżej 130 000 PLN
            ├── Zamówienia powyżej 130 000 PLN
            └── Plan zamówień
    """
    try:
        resp = client.get(page_url)
        if resp.status_code != 200:
            return []
        html = resp.text
        
        links = re.findall(r'href="([^"]{5,200})"[^>]*>\s*([^<]{10,200})\s*</a>', html)
        sub_pages = []
        
        # Keywords for sub-sections that contain actual tenders
        SUB_KEYWORDS = [
            "zamówien", "przetarg", "postępowan", "poniżej", "powyżej",
            "podprog", "krajow", "unijn", "bieżące", "aktualne",
        ]
        SUB_BLACKLIST = [
            "archiwalne", "zakończone", "plan ", "regulamin", "procedur",
        ]
        
        seen = set()
        for href, text in links:
            text_lower = text.strip().lower()
            if len(text.strip()) < 15:
                continue
            if not any(kw in text_lower for kw in SUB_KEYWORDS):
                continue
            if any(bl in text_lower for bl in SUB_BLACKLIST):
                continue
            
            url = urljoin(page_url, href)
            if url == page_url or url in seen:
                continue
            seen.add(url)
            sub_pages.append(url)
        
        return sub_pages
    except Exception:
        return []


def scrape_listing_page(client: httpx.Client, page_url: str) -> list[BIPTender]:
    """Scrape a procurement listing page for individual tenders."""
    tenders: list[BIPTender] = []
    try:
        resp = client.get(page_url)
        if resp.status_code != 200:
            return []
        html = resp.text
        
        # Strategy: find <a> links that look like individual tenders
        # Usually in a list/table with title + date
        links = re.findall(
            r'<a\s+href="([^"]{5,300})"[^>]*>\s*([^<]{10,300})\s*</a>',
            html,
        )
        
        # Keywords that signal a real procurement notice
        PROCUREMENT_KEYWORDS = [
            "zamówien", "przetarg", "zapytanie ofertowe", "dostaw",
            "roboty budowlan", "usług", "ogłoszenie", "postępowani",
            "konkurs", "ofert", "wykonan", "przebudow", "remont",
            "budow", "moderniz", "zakup", "montaż", "instalac",
            "nadzór", "projekt", "obsług", "utrzyman", "odbiór",
            "transport", "koszeni", "termomoderniz", "kanalizacj",
            "wodociąg", "drog", "chodnik", "oświetlen",
        ]
        
        # Extended blacklist for non-tender content
        BLACKLIST = [
            "menu", "strona główna", "archiwum", "rejestr", "kontakt",
            "deklaracja", "mapa strony", "bip", "redakcja", "polityka",
            "informacj", "jednostk", "samodzielne stanowisk", "regulamin",
            "statut", "uchwał", "zarządzen", "protokoł", "sesj",
            "komisj", "radni", "sołectw", "wybor", "oświadczen",
            "petycj", "skargi", "wnioski", "budżet", "sprawozdani",
            "majątk", "nieruchomości", "plan zagospodarow", "studium",
            "system informacj", "epuap", "rodo", "cookies", "dostępnoś",
            "osoby uprawnion", "specjalnymi potrzeb",
            "archiwalne ogłoszenia", "przetargi - rozstrzygnięte",
            "przetargi - unieważnione", "zamówienia zakończone",
        ]
        
        seen_urls = set()
        for href, text in links:
            text = text.strip()
            text_lower = text.lower()
            
            # Must be long enough
            if len(text) < 25:
                continue
            
            # Blacklist check
            if any(skip in text_lower for skip in BLACKLIST):
                continue
            
            # Must contain at least one procurement keyword
            if not any(kw in text_lower for kw in PROCUREMENT_KEYWORDS):
                continue
            
            url = urljoin(page_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            tenders.append(BIPTender(title=text[:300], url=url))
        
        # Try to extract dates from surrounding context
        for tender in tenders:
            date_match = re.search(
                r'(\d{4}[-./]\d{2}[-./]\d{2}|\d{2}[-./]\d{2}[-./]\d{4})',
                html[html.find(tender.title[:30]):html.find(tender.title[:30]) + 200]
                if tender.title[:30] in html else "",
            )
            if date_match:
                tender.published = _parse_date(date_match.group(1))
        
        logger.info("Scraped %d tenders from %s", len(tenders), page_url)
    except Exception as e:
        logger.warning("Failed to scrape listing %s: %s", page_url, e)
    
    return tenders


# ---------------------------------------------------------------------------
# Step 6: Store to DB
# ---------------------------------------------------------------------------

def store_tenders(
    engine,
    tenders: list[BIPTender],
    tenant_id: str,
    site: BIPSite,
) -> int:
    """Store scraped BIP tenders into the tender table."""
    from sqlalchemy import text as sql_text
    
    stored = 0
    with engine.begin() as conn:
        for t in tenders:
            # Skip if already exists (by external_id)
            exists = conn.execute(
                sql_text(
                    "SELECT 1 FROM tender WHERE external_id = :eid AND source = 'bip' AND tenant_id = :tid LIMIT 1"
                ),
                {"eid": t.external_id, "tid": tenant_id},
            ).fetchone()
            
            if exists:
                continue
            
            conn.execute(
                sql_text("""
                    INSERT INTO tender (
                        tenant_id, title, source, external_id,
                        url, voivodeship, buyer, published_at, status, raw, created_at
                    ) VALUES (
                        :tenant_id, :title, 'bip', :eid,
                        :url, :voivodeship, :buyer, :pub, 'new', CAST(:raw AS jsonb), NOW()
                    )
                    ON CONFLICT (tenant_id, source, external_id) DO NOTHING
                """),
                {
                    "tenant_id": tenant_id,
                    "title": t.title[:500],
                    "eid": t.external_id,
                    "url": t.url,
                    "voivodeship": site.region or t.region,
                    "buyer": t.bip_site_name,
                    "pub": t.published,
                    "raw": json.dumps(asdict(t), ensure_ascii=False, default=str),
                },
            )
            stored += 1
    
    return stored


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

SITE_INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "bip_site_index.json"


def save_site_index(sites: list[BIPSite]) -> None:
    """Persist site index to JSON for incremental runs."""
    SITE_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(s) for s in sites]
    SITE_INDEX_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info("Saved %d sites to %s", len(sites), SITE_INDEX_PATH)


def load_site_index() -> list[BIPSite]:
    """Load previously saved site index."""
    if not SITE_INDEX_PATH.exists():
        return []
    data = json.loads(SITE_INDEX_PATH.read_text())
    return [BIPSite(**d) for d in data]


def _discover_site(site: BIPSite) -> BIPSite:
    """Discover BIP URL + procurement page for a single site (thread-safe)."""
    with _make_client() as client:
        if not site.bip_url:
            site.bip_url = fetch_bip_url(client, site)
        if site.bip_url and not site.rss_url:
            site.rss_url = discover_rss(client, site.bip_url)
        if site.bip_url and not site.procurement_page:
            site.procurement_page = find_procurement_page(client, site.bip_url)
    return site


def _scrape_site(args: tuple) -> tuple[BIPSite, list[BIPTender]]:
    """Scrape tenders from a single site (thread-safe). Returns (site, tenders)."""
    site, cutoff = args
    tenders: list[BIPTender] = []
    
    if not site.bip_url:
        return site, tenders
    
    with _make_client() as client:
        if site.rss_url:
            tenders = parse_rss(client, site.rss_url)
        
        if not tenders and site.procurement_page:
            tenders = scrape_listing_page(client, site.procurement_page)
            if len(tenders) < 3:
                sub_pages = find_sub_procurement_pages(client, site.procurement_page)
                for sub_url in sub_pages[:5]:
                    tenders.extend(scrape_listing_page(client, sub_url))
                    time.sleep(0.2)
    
    # Filter by date + annotate
    tenders = [t for t in tenders if t.published is None or t.published >= cutoff]
    for t in tenders:
        t.bip_site_id = site.subject_id
        t.bip_site_name = site.name
        t.region = site.region
    
    site.last_scraped = datetime.now().isoformat()
    return site, tenders


def run_bip_scraper(
    engine=None,
    tenant_id: str = "",
    region: str | None = None,
    max_sites: int = 50,
    discover_only: bool = False,
    days_back: int = 30,
    workers: int = 10,
) -> dict:
    """Main entry point for BIP scraping pipeline."""
    client = _make_client()
    stats = {"sites_checked": 0, "rss_found": 0, "html_scraped": 0, "tenders_found": 0, "tenders_stored": 0}
    
    # Load or build site index
    sites = load_site_index()
    if not sites:
        logger.info("No site index found, building from API...")
        sites = build_site_index(client, GROUP_GMINY, region_filter=region, max_sites=max_sites)
        powiaty = build_site_index(client, GROUP_POWIATY, region_filter=region, max_sites=max_sites)
        sites.extend(powiaty)
    elif region:
        sites = [s for s in sites if s.region == region]
    
    if max_sites:
        sites = sites[:max_sites]
    
    logger.info("Processing %d BIP sites (workers=%d)...", len(sites), workers)
    
    # Phase 1: parallel discovery (BIP URL + procurement page)
    to_discover = [s for s in sites if not s.bip_url]
    if to_discover:
        logger.info("Discovering BIP URLs for %d sites...", len(to_discover))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            discovered = list(pool.map(_discover_site, to_discover))
        # Merge back
        discovered_map = {s.subject_id: s for s in discovered}
        sites = [discovered_map.get(s.subject_id, s) for s in sites]
    
    found_bip = sum(1 for s in sites if s.bip_url)
    logger.info("BIP URLs resolved: %d/%d", found_bip, len(sites))
    
    if discover_only:
        save_site_index(sites)
        stats["sites_checked"] = len(sites)
        return stats
    
    # Phase 2: parallel scraping
    cutoff = date.today() - timedelta(days=days_back)
    scrape_args = [(s, cutoff) for s in sites if s.bip_url]
    
    all_tenders: list[BIPTender] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_scrape_site, scrape_args))
    
    for site_result, tenders in results:
        stats["sites_checked"] += 1
        if tenders:
            if site_result.rss_url:
                stats["rss_found"] += 1
            else:
                stats["html_scraped"] += 1
            all_tenders.extend(tenders)
            stats["tenders_found"] += len(tenders)
        # Merge updated site back
        for i, s in enumerate(sites):
            if s.subject_id == site_result.subject_id:
                sites[i] = site_result
                break
    
    # Save updated index
    save_site_index(sites)
    
    
    # Store to DB
    if engine and tenant_id and all_tenders and not discover_only:
        stats["tenders_stored"] = store_tenders(engine, all_tenders, tenant_id, sites[0] if sites else BIPSite(0, "", ""))
    
    logger.info(
        "BIP scraper done: %d sites, %d RSS feeds, %d HTML pages, %d tenders found, %d stored",
        stats["sites_checked"],
        stats["rss_found"],
        stats["html_scraped"],
        stats["tenders_found"],
        stats["tenders_stored"],
    )
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    
    parser = argparse.ArgumentParser(description="BIP procurement scraper")
    parser.add_argument("--region", help="Filter by voivodeship (e.g. slaskie)")
    parser.add_argument("--max-sites", type=int, default=50, help="Max sites to process")
    parser.add_argument("--discover-only", action="store_true", help="Only build site index, don't scrape")
    parser.add_argument("--days", type=int, default=30, help="How many days back")
    parser.add_argument("--tenant-id", default="", help="Tenant UUID")
    parser.add_argument("--db-dsn", default="", help="PostgreSQL DSN")
    parser.add_argument("--workers", type=int, default=10, help="Parallel worker threads")
    args = parser.parse_args()
    
    engine = None
    if args.db_dsn and args.tenant_id:
        from sqlalchemy import create_engine
        engine = create_engine(args.db_dsn)
    
    stats = run_bip_scraper(
        engine=engine,
        tenant_id=args.tenant_id,
        region=args.region,
        max_sites=args.max_sites,
        discover_only=args.discover_only,
        days_back=args.days,
        workers=args.workers,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
