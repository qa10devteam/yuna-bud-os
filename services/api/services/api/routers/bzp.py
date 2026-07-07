"""
Faza 1 — Żywy feed przetargów z BZP (e-zamowienia.gov.pl)
Pobiera ContractNotice z CPV 45xxxxxx (roboty budowlane/ziemne) i zapisuje do bazy.
Nie wymaga klucza API — oficjalne darmowe API rządu PL.
"""
from __future__ import annotations
import logging
import re
import uuid as _uuid_mod
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["bzp"])

BZP_BASE = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
DEFAULT_TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"

# CPV 45xxxxxx — roboty budowlane i ziemne
CPV_WORKS_PREFIXES = (
    "45000", "45100", "45111", "45112", "45113",
    "45200", "45210", "45220", "45230", "45231", "45232", "45233",
    "45300", "45310", "45330", "45400",
)

PROVINCE_MAP = {
    "PL02": "dolnośląskie",    "PL04": "kujawsko-pomorskie",
    "PL06": "lubelskie",       "PL08": "lubuskie",
    "PL10": "łódzkie",         "PL12": "małopolskie",
    "PL14": "mazowieckie",     "PL16": "opolskie",
    "PL18": "podkarpackie",    "PL20": "podlaskie",
    "PL22": "pomorskie",       "PL24": "śląskie",
    "PL26": "świętokrzyskie",  "PL28": "warmińsko-mazurskie",
    "PL30": "wielkopolskie",   "PL32": "zachodniopomorskie",
}


def _cpv_matches(cpv_string: str) -> bool:
    for prefix in CPV_WORKS_PREFIXES:
        if prefix in (cpv_string or ""):
            return True
    return False


def _parse_value_pln(html_body: str) -> Optional[float]:
    for pattern in [
        r'(\d[\d\s]{3,}[,\.]\d{2})\s*(?:PLN|zł)',
        r'Wartość.*?(\d[\d\s]{3,})',
    ]:
        m = re.search(pattern, html_body or "", re.IGNORECASE | re.DOTALL)
        if m:
            raw = m.group(1).replace("\xa0", "").replace(" ", "").replace(",", ".")
            try:
                v = float(raw)
                if 1_000 < v < 5_000_000_000:
                    return v
            except ValueError:
                pass
    return None


def _safe_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _fetch_page(date_from: str, date_to: str, page: int, size: int = 50) -> list[dict]:
    params = {
        "pageSize": size, "pageNumber": page,
        "NoticeType": "ContractNotice",
        "PublicationDateFrom": date_from,
        "PublicationDateTo": date_to,
    }
    try:
        r = httpx.get(BZP_BASE, params=params, headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _do_sync(days_back: int) -> dict:
    engine = get_engine()
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    date_to = now.strftime("%Y-%m-%dT23:59:59")

    fetched = saved = skipped = 0

    with engine.begin() as conn:
        page = 0
        while True:
            items = _fetch_page(date_from, date_to, page)
            if not items:
                break
            fetched += len(items)

            for item in items:
                if not _cpv_matches(item.get("cpvCode", "")):
                    continue

                external_id = (item.get("bzpNumber") or item.get("noticeNumber") or "").strip()
                if not external_id:
                    continue

                # Sprawdź duplikaty
                exists = conn.execute(
                    sa.text("SELECT 1 FROM tender WHERE tenant_id=:t AND source='bzp' AND external_id=:e"),
                    {"t": DEFAULT_TENANT_ID, "e": external_id}
                ).fetchone()
                if exists:
                    skipped += 1
                    continue

                # Parsuj pola
                cpv_list = [c.strip() for c in item.get("cpvCode", "").split(",") if c.strip()]
                province = item.get("organizationProvince", "")
                voivodeship = PROVINCE_MAP.get(province, province)
                value_pln = _parse_value_pln(item.get("htmlBody", ""))
                deadline = _safe_dt(item.get("submittingOffersDate"))
                published = _safe_dt(item.get("publicationDate")) or now
                tender_id = item.get("tenderId", "")
                url = f"https://ezamowienia.gov.pl/mp-client/tenders/{tender_id}" if tender_id else None

                import json as _json
                raw_json = _json.dumps({
                    "cpvCode": item.get("cpvCode"),
                    "organizationCity": item.get("organizationCity"),
                    "organizationProvince": province,
                    "isTenderAmountBelowEU": item.get("isTenderAmountBelowEU"),
                    "noticeNumber": item.get("noticeNumber"),
                    "bzpNumber": item.get("bzpNumber"),
                }, ensure_ascii=False)

                conn.execute(sa.text("""
                    INSERT INTO tender
                        (id, tenant_id, source, external_id, title, buyer, cpv,
                         voivodeship, value_pln, deadline_at, published_at, url,
                         status, match_score, match_reason, raw, created_at)
                    VALUES
                        (:id, :tid, 'bzp', :ext, :title, :buyer, :cpv,
                         :voi, :val, :dead, :pub, :url,
                         'new', 0.0, 'BZP live import', CAST(:raw AS jsonb), NOW())
                """), {
                    "id": str(_uuid_mod.uuid4()),
                    "tid": DEFAULT_TENANT_ID,
                    "ext": external_id,
                    "title": (item.get("orderObject") or "")[:500],
                    "buyer": (item.get("organizationName") or "")[:300],
                    "cpv": cpv_list,
                    "voi": voivodeship,
                    "val": value_pln,
                    "dead": deadline,
                    "pub": published,
                    "url": url,
                    "raw": raw_json,
                })
                saved += 1

            if len(items) < 50:
                break
            page += 1

    logger.info(f"BZP sync: fetched={fetched}, saved={saved}, skipped={skipped}")
    return {"fetched": fetched, "saved": saved, "skipped": skipped, "pages": page + 1}


# ─── API Endpoints ────────────────────────────────────────────────────────────

@router.post("/bzp/sync")
def bzp_sync_bg(background_tasks: BackgroundTasks, days_back: int = 7):
    """Uruchom synchronizację przetargów z BZP w tle (domyślnie ostatnie 7 dni)."""
    background_tasks.add_task(_do_sync, days_back)
    return {"status": "started", "days_back": days_back,
            "message": f"Synchronizacja BZP uruchomiona — ostatnie {days_back} dni"}


@router.post("/bzp/sync/now")
def bzp_sync_now(days_back: int = 7):
    """Synchronizuj BZP synchronicznie i zwróć wyniki (do testów i cron)."""
    result = _do_sync(days_back)
    return {"status": "done", **result}


@router.get("/bzp/stats")
def bzp_stats_live():
    """Statystyki typów ogłoszeń z BZP za ostatnie 2 dni."""
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")
    date_to = now.strftime("%Y-%m-%dT23:59:59")
    try:
        r = httpx.get(
            f"{BZP_BASE}/stats",
            params={"PublicationDateFrom": date_from, "PublicationDateTo": date_to},
            headers={"Accept": "application/json"}, timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        # Fallback when BZP API is unavailable
        return {
            "total": 0,
            "by_type": {},
            "period": {"from": date_from, "to": date_to},
            "source": "fallback",
            "message": "BZP API temporarily unavailable"
        }


@router.get("/bzp/document/{bzp_number:path}")
def bzp_document(bzp_number: str):
    """Pobiera pełną treść ogłoszenia BZP po numerze BZP (np. 2026/BZP 00302518)."""
    from urllib.parse import unquote
    bzp_number = unquote(bzp_number)

    now = datetime.now(timezone.utc)
    item = None

    # Sprawdź czy mamy datę publikacji w bazie danych — pozwoli zawęzić okno wyszukiwania
    published_at = None
    try:
        engine_db = get_engine()
        with engine_db.connect() as conn:
            row = conn.execute(
                sa.text("SELECT published_at FROM tender WHERE source='bzp' AND external_id=:e LIMIT 1"),
                {"e": bzp_number}
            ).fetchone()
            if row and row[0]:
                published_at = row[0]
    except Exception:
        pass

    # Zdefiniuj okna wyszukiwania
    if published_at:
        # Wiemy kiedy było opublikowane — szukaj w tym dniu ±1 dzień
        from datetime import date
        pub_dt = published_at if hasattr(published_at, 'strftime') else now
        date_windows = [
            (
                (pub_dt - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00"),
                (pub_dt + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59"),
            )
        ]
    else:
        # Nieznana data — szukaj w kolejnych oknach: ostatnie 3, 7, 30 dni
        date_windows = [
            ((now - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59")),
            ((now - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59")),
            ((now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00"), now.strftime("%Y-%m-%dT23:59:59")),
        ]

    for date_from, date_to in date_windows:
        if item is not None:
            break
        page = 0
        while page < 50 and item is None:
            params = {
                "pageSize": 50,
                "pageNumber": page,
                "NoticeType": "ContractNotice",
                "PublicationDateFrom": date_from,
                "PublicationDateTo": date_to,
            }
            try:
                r = httpx.get(BZP_BASE, params=params, headers={"Accept": "application/json"}, timeout=30)
                r.raise_for_status()
                data = r.json()
                items_page = data if isinstance(data, list) else []
                if not items_page:
                    break
                for it in items_page:
                    if (it.get("bzpNumber") or "").strip() == bzp_number.strip():
                        item = it
                        break
                if len(items_page) < 50:
                    break
                page += 1
            except Exception:
                break

    if not item:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono ogłoszenia BZP: {bzp_number}")

    html_body = item.get("htmlBody") or ""
    # Pobierz pełny tekst bez limitu — cała dokumentacja przetargowa
    full_text = re.sub(r'<[^>]+>', ' ', html_body)
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    value_pln = _parse_value_pln(html_body)
    cpv_list = [c.strip() for c in (item.get("cpvCode") or "").split(",") if c.strip()]

    # Próbuj też pobrać załączniki/sekcje SIWZ przez Jina Reader jeśli dostępny URL
    bzp_url = item.get("orderLink") or item.get("internetAddress") or ""
    attachments = []
    if bzp_url:
        try:
            jina_url = f"https://r.jina.ai/{bzp_url}"
            jr = httpx.get(jina_url, timeout=15, headers={"Accept": "text/plain"})
            if jr.status_code == 200 and jr.text:
                attachments.append({"source": bzp_url, "text": jr.text[:20000]})
        except Exception:
            pass

    return {
        "bzp_number": item.get("bzpNumber") or bzp_number,
        "title": (item.get("orderObject") or "")[:500],
        "buyer": item.get("organizationName"),
        "cpv": cpv_list,
        "deadline": item.get("submittingOffersDate"),
        "value_pln": value_pln,
        "full_text": full_text,          # pełny tekst BEZ limitu
        "html_body": html_body,          # surowy HTML dla renderowania
        "internet_address": bzp_url,
        "attachments": attachments,
        "char_count": len(full_text),
    }


@router.get("/bzp/preview")
def bzp_preview(days_back: int = 3, limit: int = 10):
    """Podgląd przetargów robót budowlanych z BZP bez zapisu do bazy."""
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    date_to = now.strftime("%Y-%m-%dT23:59:59")

    items = _fetch_page(date_from, date_to, page=0, size=50)
    works = [i for i in items if _cpv_matches(i.get("cpvCode", ""))]

    return {
        "total_fetched": len(items),
        "works_filtered": len(works),
        "preview": [
            {
                "bzpNumber": i.get("bzpNumber"),
                "title": (i.get("orderObject") or "")[:200],
                "buyer": i.get("organizationName"),
                "city": i.get("organizationCity"),
                "voivodeship": PROVINCE_MAP.get(i.get("organizationProvince", ""), ""),
                "cpv": (i.get("cpvCode") or "")[:120],
                "deadline": i.get("submittingOffersDate"),
                "published": i.get("publicationDate"),
            }
            for i in works[:limit]
        ]
    }
