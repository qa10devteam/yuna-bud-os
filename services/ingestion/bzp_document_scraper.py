"""Terra-OS BZP Document Scraper.

Pobiera dokumenty SWZ z publicznego API ezamowienia.gov.pl (bez autoryzacji).

=== ZWERYFIKOWANE ENDPOINTY (bez auth) ===

1. Notice PDF
   GET /mo-board/api/v1/Board/GetNoticePdf?noticeNumber=2026%2FBZP%20XXXXXX%2F01
   → 200 application/pdf, ~100–400 KB
   UWAGA: wymaga sufiksu /01 (pierwsze ogłoszenie) lub /02 (zmiana).
   Strategia: próbujemy /01, jeśli 404 → /02 → /03 (max 5 prób).

2. Lista ogłoszeń (htmlBody)
   GET /mo-board/api/v1/notice?NoticeType=ContractNotice
       &PublicationDateFrom=YYYY-MM-DDTHH:MM:SS
       &PublicationDateTo=YYYY-MM-DDTHH:MM:SS
       &pageSize=50&pageNumber=N
   → JSON list. Każdy element: bzpNumber, htmlBody (HTML treść ogłoszenia).
   UWAGA: tylko NoticeType=ContractNotice zwraca 200. Inne typy → 400.
   htmlBody zawiera link do zewnętrznej platformy SWZ w sekcji 3.1.

=== DZIAŁA bez autoryzacji (zweryfikowano 2026-07-17) ===
  /mp-readmodels/api/Search/GetTenderDocuments?tenderId=<ocds-id>  → JSON lista dokumentów
  /mp-readmodels/api/Tender/DownloadDocument/<tender_id>/<obj_id>  → plik (docx/pdf/zip)
  Obsługiwane przez EZamiowieniaGovHandler w platform_document_scraper.py

=== NIE DZIAŁA (wymaga OAuth2) ===
  Inne API administracyjne (składanie ofert, komunikacja)
  authIssuer: https://ezamowienia.gov.pl/oauth2/token (clientId: epzp_MP_FE)

=== ARCHITEKTURA ===
  Dla każdego przetargu BZP generujemy max 2 dokumenty:
  1. NOTICE — PDF ogłoszenia (pobierany lokalnie)
  2. SWZ    — URL zewnętrznej platformy postępowania (link, nie plik)
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Konfiguracja
# ─────────────────────────────────────────────────────────────────────

BZP_BASE        = "https://ezamowienia.gov.pl"
NOTICE_PDF_API  = f"{BZP_BASE}/mo-board/api/v1/Board/GetNoticePdf"
NOTICE_LIST_API = f"{BZP_BASE}/mo-board/api/v1/notice"

# Zachowane dla kompatybilności importu
DOWNLOAD_API = f"{BZP_BASE}/mp-readmodels/api/Tender/DownloadDocument"

STORAGE_DIR   = Path(os.environ.get("TERRA_DOCUMENTS_DIR", "/var/lib/terra-os/documents"))
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
TIMEOUT       = 30  # sekundy
MAX_PDF_VERSIONS = 5   # próbujemy /01 → /02 → … → /05


def _is_pdf(data: bytes) -> bool:
    """Sprawdza magic bytes PDF (%PDF-)."""
    return data[:4] == b"%PDF"
RETRY_ATTEMPTS   = 3
RETRY_DELAY      = 1.5  # sekundy (backoff × attempt)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Tylko ContractNotice zwraca 200 — inne typy → 400
_VALID_NOTICE_TYPES = ("ContractNotice",)

# Znane platformy zakupowe — matchowanie po domain suffix (obsługuje subdomeny)
# np. "*.ezamawiajacy.pl", "*.logintrade.net", "*.eb2b.com.pl"
_PLATFORM_SUFFIXES = (
    # Największe platformy
    "platformazakupowa.pl",
    "ezamawiajacy.pl",        # obejmuje *.ezamawiajacy.pl
    "logintrade.net",         # obejmuje *.logintrade.net (.pl też istnieje)
    "logintrade.pl",
    "eb2b.com.pl",            # obejmuje *.eb2b.com.pl
    "smartpzp.pl",
    "josephine.pl",
    "e-propublico.pl",
    "epropublico.pl",
    "sidaspzp.pl",
    "przetargi.pl",
    "openplatform.pl",
    "miniportal.uzp.gov.pl",
    "e-zp.com",
    "zp.pzp.pl",
    "proebiz.com",
    "soldea.pl",
    "comarq.pl",
    "auctions.coig.pl",
    "biznes-polska.pl",
    "orion.pl",
    "ezp.gkbkzp.pl",
    "josephine.no",
    # Subdomeny e-zp.*.pl (np. e-zp.miedzyrzecz.pl)
    # Matchowane przez hostname startujący od "e-zp."
    "ezamowienia.qov.pl",  # literówka w danych BZP (qov zamiast gov)
)

# ─────────────────────────────────────────────────────────────────────
# Struktury danych
# ─────────────────────────────────────────────────────────────────────

@dataclass
class TenderDocument:
    object_id:    str
    name:         str
    filename:     str
    url:          str
    doc_type:     str   = "OTHER"
    state:        str   = "Published"
    file_size:    int | None = None
    content_type: str | None = None
    local_path:   str | None = None
    published_date: str | None = None


@dataclass
class FetchResult:
    tender_id:        str
    bzp_number:       str | None = None
    documents:        list[TenderDocument] = field(default_factory=list)
    downloaded:       int = 0
    errors:           list[str] = field(default_factory=list)
    notice_pdf_path:  str | None = None
    swz_platform_url: str | None = None


# ─────────────────────────────────────────────────────────────────────
# Scraper
# ─────────────────────────────────────────────────────────────────────

class BZPDocumentScraper:
    """Scraper dokumentów SWZ z publicznego API ezamowienia.gov.pl."""

    def __init__(self, storage_dir: Path | None = None, db_engine=None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._engine = db_engine
        self._client: httpx.Client | None = None

    # ── Lifecycle ────────────────────────────────────────────────────

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(connect=8.0, read=45.0, write=10.0, pool=5.0),
                limits=httpx.Limits(
                    max_connections=6,
                    max_keepalive_connections=3,
                    keepalive_expiry=60,
                ),
                follow_redirects=True,
                headers={
                    "User-Agent": _UA,
                    "Accept": "application/json, application/pdf, */*",
                    "Accept-Language": "pl-PL,pl;q=0.9",
                    "Referer": "https://ezamowienia.gov.pl/",
                },
            )
        return self._client

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── Public API ───────────────────────────────────────────────────

    async def fetch_notice_list(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page_size: int = 50,
        page_number: int = 0,
        notice_type: str = "ContractNotice",
    ) -> list[dict]:
        """Pobiera listę ogłoszeń z BZP API (async wrapper dla backward-compat).

        Returns lista dictów z polami bzpNumber, name, htmlBody, itp.
        """
        now = datetime.now(timezone.utc)
        d_from = date_from or (now - timedelta(days=1))
        d_to = date_to or now

        def _fmt(dt: datetime) -> str:
            return dt.strftime("%Y-%m-%dT%H:%M:%S")

        client = self._get_client()
        try:
            resp = client.get(
                NOTICE_LIST_API,
                params={
                    "NoticeType": notice_type,
                    "PublicationDateFrom": _fmt(d_from),
                    "PublicationDateTo": _fmt(d_to),
                    "pageSize": page_size,
                    "pageNumber": page_number,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("source=bzp_docs fetch_notice_list error=%s", exc)
            return []

    def list_documents(self, tender_id: str) -> list[TenderDocument]:
        """Lista dokumentów dostępnych dla przetargu.

        Generuje:
          1. NOTICE PDF — pobierany z GetNoticePdf (próby /01 → /05)
          2. SWZ link  — URL zewnętrznej platformy wyciągnięty z htmlBody sekcja 3.1

        Args:
            tender_id: Numer BZP (2026/BZP ...) lub OCDS ID lub wewnętrzny UUID.
        """
        bzp_number = self._resolve_to_bzp_number(tender_id)
        if not bzp_number:
            logger.warning("Nie można rozwiązać numeru BZP dla: %s", tender_id)
            return []

        safe_bzp = re.sub(r"[^0-9A-Za-z]", "_", bzp_number)
        docs: list[TenderDocument] = []

        # 1. Notice PDF — próbujemy wersje /01 → /MAX_PDF_VERSIONS
        pdf_url = self._find_valid_pdf_url(bzp_number)
        if pdf_url:
            docs.append(TenderDocument(
                object_id=f"notice_pdf_{safe_bzp}",
                name=f"Ogłoszenie o zamówieniu {bzp_number}",
                filename=f"ogloszenie_{safe_bzp}.pdf",
                url=pdf_url,
                doc_type="NOTICE",
            ))
        else:
            logger.warning("Brak PDF dla %s (próbowano /01–/%02d)", bzp_number, MAX_PDF_VERSIONS)

        # 2. SWZ platform URL (z htmlBody sekcja 3.1)
        swz_url = self._get_swz_platform_url(bzp_number)
        if swz_url:
            docs.append(TenderDocument(
                object_id=f"swz_link_{safe_bzp}",
                name=f"Platforma SWZ — {swz_url}",
                filename=f"swz_link_{safe_bzp}.url",
                url=swz_url,
                doc_type="SWZ",
            ))

            # 3. Dokumenty z zewnętrznej platformy SWZ (state-of-art multi-platform scraper)
            try:
                from services.ingestion.platform_document_scraper import PlatformDocumentScraper
                with PlatformDocumentScraper() as platform_scraper:
                    platform_docs = platform_scraper.scrape(swz_url)
                if platform_docs:
                    logger.info(
                        "source=bzp_docs platform_scraper: %d dokumentów z %s",
                        len(platform_docs), swz_url[:60],
                    )
                    for pdoc in platform_docs:
                        # Pomijamy jeśli URL jest taki sam jak swz_url (link do strony)
                        if pdoc.url == swz_url:
                            continue
                        docs.append(TenderDocument(
                            object_id=f"platform_doc_{safe_bzp}_{len(docs)}",
                            name=pdoc.name or pdoc.filename or pdoc.url.split("/")[-1],
                            filename=pdoc.filename or pdoc.name[:80],
                            url=pdoc.url,
                            doc_type=pdoc.doc_type,
                        ))
                else:
                    logger.info(
                        "source=bzp_docs platform_scraper: brak dokumentów dla %s",
                        swz_url[:60],
                    )
            except Exception as exc:
                logger.warning(
                    "source=bzp_docs platform_scraper failed for %s: %s",
                    swz_url[:60], exc,
                )

        logger.info("source=bzp_docs tender_id=%s znaleziono %d dokumentów (bzp=%s)", tender_id, len(docs), bzp_number)
        return docs

    def download_document(self, tender_id: str, doc: TenderDocument) -> Path | None:
        """Pobiera pojedynczy dokument na dysk.

        - NOTICE (PDF): stream z ezamowienia.gov.pl
        - SWZ (link): zapisuje plik .url z adresem platformy (nie pobiera binarnie)
        """
        doc_dir = self._doc_dir(tender_id)

        if doc.doc_type == "SWZ":
            dest = doc_dir / doc.filename
            dest.write_text(f"[InternetShortcut]\nURL={doc.url}\n", encoding="utf-8")
            doc.local_path = str(dest)
            doc.file_size  = dest.stat().st_size
            logger.info("Zapisano link SWZ: %s → %s", doc.url, dest)
            return dest

        # PDF — z retry
        return self._download_with_retry(doc, doc_dir)

    def fetch_all(
        self,
        tender_id: str,
        bzp_number: str | None = None,
        *,
        download_files: bool = True,
        include_notice_pdf: bool = True,  # zachowane dla kompatybilności
    ) -> FetchResult:
        """Główny entry point: listuje + pobiera dokumenty + zapisuje do DB.

        Args:
            tender_id:      Wewnętrzny UUID przetargu (z tabeli tender).
            bzp_number:     Opcjonalny numer BZP — przyspiesza lookup.
            download_files: Czy pobierać pliki na dysk.
        """
        result = FetchResult(tender_id=tender_id, bzp_number=bzp_number)

        try:
            # Użyj BZP number jeśli dostępny, inaczej tender_id
            lookup_key = (
                bzp_number
                if bzp_number and re.match(r"\d{4}/BZP", bzp_number)
                else tender_id
            )
            documents = self.list_documents(lookup_key)
            result.documents = documents

            if not documents:
                result.errors.append(f"Brak dokumentów dla przetargu {tender_id}")
                logger.warning("Brak dokumentów dla %s (bzp=%s)", tender_id, bzp_number)
                return result

            # Wypełnij SWZ URL w result
            for d in documents:
                if d.doc_type == "SWZ":
                    result.swz_platform_url = d.url
                    break

            # Pobierz pliki
            if download_files:
                for doc in documents:
                    path = self.download_document(tender_id, doc)
                    if path:
                        result.downloaded += 1
                        if doc.doc_type == "NOTICE":
                            result.notice_pdf_path = str(path)
                    else:
                        result.errors.append(f"Nie udało się pobrać: {doc.filename}")

        except Exception as exc:
            logger.exception("Nieoczekiwany błąd podczas fetch_all dla %s: %s", tender_id, exc)
            result.errors.append(f"Błąd krytyczny: {exc}")

        # Zapisz do DB
        if self._engine and result.documents:
            self._store_results(result)

        logger.info(
            "source=bzp_docs tender_id=%s fetch zakończony: docs=%d downloaded=%d errors=%d",
            tender_id, len(result.documents), result.downloaded, len(result.errors),
        )
        return result

    # ── Private helpers ──────────────────────────────────────────────

    def _resolve_to_bzp_number(self, tender_id: str) -> str | None:
        """Zwraca numer BZP (np. '2026/BZP 00331648') dla podanego identyfikatora.

        Kolejność prób:
        1. Już jest numerem BZP → strip suffix /01 jeśli obecny
        2. Lookup w DB po id / url / external_id
        3. Brak → None
        """
        # Już numer BZP
        m = re.match(r"(\d{4}/BZP[\s\u00a0]\d+)(?:/\d+)?$", tender_id.strip())
        if m:
            return m.group(1)

        if not self._engine:
            return None

        try:
            with self._engine.connect() as conn:
                row = conn.execute(
                    sa.text(
                        "SELECT external_id FROM tender "
                        "WHERE id::text = :tid OR url LIKE :purl "
                        "LIMIT 1"
                    ),
                    {"tid": str(tender_id), "purl": f"%{tender_id}%"},
                ).fetchone()
                if row and row[0]:
                    # Strip version suffix if present
                    return re.sub(r"/\d+$", "", row[0].strip())
        except Exception as exc:
            logger.warning("DB lookup nieudany dla %s: %s", tender_id, exc)

        return None

    def _find_valid_pdf_url(self, bzp_number: str) -> str | None:
        """Szuka działającego URL do Notice PDF, próbując wersje /01 → /MAX.

        Serwer ezamowienia.gov.pl:
        - Nie obsługuje HEAD (zwraca 405)
        - Ignoruje Range header (zwraca pełny plik)
        → Weryfikujemy content-type i status 200.
        """
        client = self._get_client()
        base = re.sub(r"/\d+$", "", bzp_number)

        for version in range(1, MAX_PDF_VERSIONS + 1):
            versioned = f"{base}/{version:02d}"
            url = f"{NOTICE_PDF_API}?noticeNumber={quote(versioned, safe='')}"
            try:
                resp = client.get(url, timeout=15)
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "")
                    # Weryfikuj content-type lub magic bytes
                    if "pdf" in ct or _is_pdf(resp.content[:8]):
                        logger.debug("PDF znaleziony: %s (wersja /%02d)", bzp_number, version)
                        return url
                elif resp.status_code == 404:
                    if version == 1:
                        continue
                    break
                elif resp.status_code >= 500:
                    break
            except httpx.HTTPError:
                break

        return None

    def _get_swz_platform_url(self, bzp_number: str) -> str | None:
        """Wyciąga URL zewnętrznej platformy SWZ z htmlBody ogłoszenia.

        Algorytm:
        1. Bezpośrednie zapytanie po noticeNumber (1 request!)
        2. Fallback: szukaj po dacie publikacji ± 1 dzień (jeśli direct query zwraca 0)
        """
        bzp_base = re.sub(r"/\d+$", "", bzp_number)  # strip /01
        client   = self._get_client()

        # ── Strategia 1: noticeNumber (bezpośredni filtr API) ─────────────────
        pub_date = self._get_publication_date(bzp_number)
        today    = datetime.now(timezone.utc).date()
        date_str = pub_date or str(today)
        try:
            resp = client.get(
                NOTICE_LIST_API,
                params={
                    "NoticeType":          "ContractNotice",
                    "PublicationDateFrom": f"{date_str}T00:00:00",
                    "PublicationDateTo":   f"{date_str}T23:59:59",
                    "noticeNumber":        bzp_base,
                    "pageSize":            1,
                    "pageNumber":          0,
                },
                timeout=15,
            )
            items = resp.json() if resp.status_code == 200 and isinstance(resp.json(), list) else []
            if items:
                html = items[0].get("htmlBody") or ""
                url  = _extract_platform_url(html) if html else None
                if url:
                    logger.info("SWZ URL dla %s: %s", bzp_base, url)
                else:
                    logger.debug("Znaleziono ogłoszenie %s, brak URL platformy SWZ", bzp_base)
                return url
        except httpx.HTTPError as exc:
            logger.debug("noticeNumber query failed: %s", exc)

        # ── Strategia 2: fallback — skanuj ± 1 dzień wokół daty publikacji ────
        if pub_date:
            d = datetime.strptime(pub_date, "%Y-%m-%d").date()
            fallback_dates = [pub_date, str(d - timedelta(days=1)), str(d + timedelta(days=1))]
        else:
            fallback_dates = [str(today - timedelta(days=i)) for i in range(3)]

        for date_str in fallback_dates:
            url = self._search_html_body_for_date(bzp_base, date_str)
            if url is not None:
                return url or None

        logger.debug("Brak SWZ URL dla %s", bzp_number)
        return None

    def _search_html_body_for_date(self, bzp_base: str, date_str: str) -> str | None:
        """Skanuje ogłoszenia z danego dnia szukając numeru BZP (fallback).

        Returns:
            str  — znaleziono URL platformy
            ""   — znaleziono ogłoszenie, ale bez URL platformy (caller powinien zwrócić None)
            None — ogłoszenie nie znalezione w tym dniu
        """
        client    = self._get_client()
        date_from = f"{date_str}T00:00:00"
        date_to   = f"{date_str}T23:59:59"

        for page in range(20):  # max 20 stron × 50 = 1000 ogłoszeń/dzień
            try:
                resp = client.get(
                    NOTICE_LIST_API,
                    params={
                        "NoticeType":          "ContractNotice",
                        "PublicationDateFrom": date_from,
                        "PublicationDateTo":   date_to,
                        "pageSize":            50,
                        "pageNumber":          page,
                    },
                    timeout=15,
                )
            except httpx.HTTPError as exc:
                logger.debug("htmlBody search failed page=%d date=%s: %s", page, date_str, exc)
                break

            if resp.status_code != 200:
                break
            items = resp.json() if isinstance(resp.json(), list) else []
            if not items:
                break

            for notice in items:
                n_bzp = re.sub(r"/\d+$", "", (notice.get("bzpNumber") or "").strip())
                if n_bzp == bzp_base:
                    html = notice.get("htmlBody") or ""
                    return _extract_platform_url(html) or ""

        return None

    def _get_publication_date(self, bzp_number: str) -> str | None:
        """Pobiera datę publikacji przetargu z DB (YYYY-MM-DD)."""
        if not self._engine:
            return None
        bzp_base = re.sub(r"/\d+$", "", bzp_number)
        try:
            with self._engine.connect() as conn:
                row = conn.execute(
                    sa.text(
                        "SELECT published_at FROM tender "
                        "WHERE external_id = :bzp OR external_id = :bzp_v01 "
                        "LIMIT 1"
                    ),
                    {"bzp": bzp_base, "bzp_v01": f"{bzp_base}/01"},
                ).fetchone()
                if row and row[0]:
                    return str(row[0])[:10]
        except Exception as exc:
            logger.debug("DB published_at lookup nieudany dla %s: %s", bzp_number, exc)
        return None

    def _download_with_retry(self, doc: TenderDocument, doc_dir: Path) -> Path | None:
        """Pobiera plik z retry (max RETRY_ATTEMPTS prób, exponential backoff)."""
        client = self._get_client()
        safe_name = re.sub(r'[/\\<>:"|?*]', "_", doc.filename) or f"doc_{doc.object_id[-8:]}"
        dest = doc_dir / safe_name

        last_error: Exception | None = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                with client.stream("GET", doc.url) as resp:
                    resp.raise_for_status()

                    cl = resp.headers.get("content-length")
                    if cl and int(cl) > MAX_FILE_SIZE:
                        logger.warning(
                            "source=bzp_docs tender_id=%s plik za duży %s: %s bajtów",
                            doc.object_id, doc.filename, cl,
                        )
                        return None

                    total = 0
                    header_bytes = bytearray()
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(65536):
                            total += len(chunk)
                            if total > MAX_FILE_SIZE:
                                logger.warning(
                                    "source=bzp_docs tender_id=%s plik przekroczył max rozmiar: %s",
                                    doc.object_id, doc.filename,
                                )
                                f.close()
                                dest.unlink(missing_ok=True)
                                return None
                            if len(header_bytes) < 8:
                                header_bytes.extend(chunk[:max(0, 8 - len(header_bytes))])
                            f.write(chunk)

                # Walidacja: sprawdź magic bytes PDF
                if doc.doc_type == "NOTICE" and not _is_pdf(bytes(header_bytes)):
                    logger.warning(
                        "source=bzp_docs tender_id=%s plik %s nie jest PDF (magic bytes: %r)",
                        doc.object_id, doc.filename, bytes(header_bytes)[:4],
                    )
                    dest.unlink(missing_ok=True)
                    return None

                doc.file_size  = total
                doc.local_path = str(dest)
                doc.content_type = resp.headers.get("content-type", "")
                logger.info(
                    "source=bzp_docs tender_id=%s pobrano %s (%d KB) → %s",
                    doc.object_id, doc.filename, total // 1024, dest,
                )
                return dest

            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in (404, 410):
                    logger.warning(
                        "source=bzp_docs tender_id=%s HTTP %d dla %s — brak pliku",
                        doc.object_id, exc.response.status_code, doc.url,
                    )
                    break  # Nie próbujemy ponownie dla 404/410
                logger.warning(
                    "source=bzp_docs tender_id=%s attempt=%d/%d HTTP %d dla %s",
                    doc.object_id, attempt, RETRY_ATTEMPTS, exc.response.status_code, doc.filename,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "source=bzp_docs tender_id=%s attempt=%d/%d błąd sieci dla %s: %s",
                    doc.object_id, attempt, RETRY_ATTEMPTS, doc.filename, exc,
                )

            dest.unlink(missing_ok=True)
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * attempt)

        if last_error:
            logger.error(
                "source=bzp_docs tender_id=%s nieudane pobranie %s po %d próbach: %s",
                doc.object_id, doc.filename, RETRY_ATTEMPTS, last_error,
            )
        return None

    def _doc_dir(self, tender_id: str) -> Path:
        """Zwraca katalog dla dokumentów przetargu, tworzy jeśli brak."""
        safe = re.sub(r"[^\w\-]", "_", str(tender_id))
        d = self.storage_dir / safe
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── DB Storage ───────────────────────────────────────────────────

    def _store_results(self, result: FetchResult) -> None:
        """Zapisuje pobrane dokumenty do tabeli bzp_documents."""
        try:
            with self._engine.connect() as conn:
                # Wyznacz wewnętrzne UUID przetargu
                internal_id = self._resolve_internal_id(conn, result)
                if not internal_id:
                    logger.warning(
                        "Nie znaleziono przetargu w DB dla tender=%s bzp=%s",
                        result.tender_id, result.bzp_number,
                    )
                    return

                stored = 0
                for doc in result.documents:
                    content_val = (
                        f"[file:{doc.local_path}]" if doc.local_path
                        else f"[url:{doc.url}]"
                    )
                    conn.execute(
                        sa.text("""
                            INSERT INTO bzp_documents
                                (id, tender_id, bzp_notice_id, doc_type, filename,
                                 content, url, fetched_at)
                            VALUES
                                (:id, :tid, :notice_id, :doc_type, :filename,
                                 :content, :url, now())
                            ON CONFLICT (tender_id, filename) DO UPDATE SET
                                url        = EXCLUDED.url,
                                content    = EXCLUDED.content,
                                doc_type   = EXCLUDED.doc_type,
                                fetched_at = now()
                        """),
                        {
                            "id":        str(uuid.uuid4()),
                            "tid":       internal_id,
                            "notice_id": result.bzp_number or "",
                            "doc_type":  doc.doc_type,
                            "filename":  doc.filename,
                            "content":   content_val,
                            "url":       doc.url,
                        },
                    )
                    stored += 1

                conn.commit()
                logger.info("Zapisano %d dokumentów dla przetargu %s", stored, internal_id)

        except Exception as exc:
            logger.error("Błąd zapisu do DB dla %s: %s", result.tender_id, exc)

    def _resolve_internal_id(self, conn, result: FetchResult) -> str | None:
        """Wyznacza wewnętrzne UUID przetargu z różnych identyfikatorów."""
        candidates = [
            ("id::text = :v", result.tender_id),
        ]
        if result.bzp_number:
            bzp_base = re.sub(r"/\d+$", "", result.bzp_number)
            candidates += [
                ("external_id = :v", bzp_base),
                ("external_id = :v", f"{bzp_base}/01"),
            ]

        for clause, val in candidates:
            try:
                row = conn.execute(
                    sa.text(f"SELECT id FROM tender WHERE {clause} LIMIT 1"),
                    {"v": str(val)},
                ).fetchone()
                if row:
                    return str(row[0])
            except Exception:
                continue
        return None


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _is_platform_url(url: str) -> bool:
    """Sprawdza czy URL należy do znanych platform zakupowych (obsługuje subdomeny)."""
    try:
        m = re.match(r'https?://([^/?\s]+)', url)
        if not m:
            return False
        host = m.group(1).lower().rstrip(".")
        # Suffix matching: *.ezamawiajacy.pl, *.logintrade.net, *.eb2b.com.pl itd.
        if any(host == suffix or host.endswith("." + suffix) for suffix in _PLATFORM_SUFFIXES):
            return True
        # Wzorzec e-zp.<subdomain>.pl (np. e-zp.miedzyrzecz.pl)
        if re.match(r'^e-zp\.[a-z0-9-]+\.pl$', host):
            return True
        return False
    except Exception:
        return False


def _extract_platform_url(html_body: str) -> str | None:
    """Wyciąga URL zewnętrznej platformy SWZ z sekcji 3.1 htmlBody ogłoszenia.

    Sekcja 3.1: 'Adres strony internetowej prowadzonego postępowania'
    Po nagłówku jest URL do platformy zakupowej.

    Strategia:
    1. Znajdź sekcję 3.1 i pobierz URL w promieniu ~600 znaków (precyzyjnie)
    2. Fallback: szukaj wszystkich URL z znanych platform w całym dokumencie
    """
    # Strategia 1: sekcja 3.1 (precyzyjna, unika fałszywych trafień)
    section_re = re.compile(
        r"3\.1[.\)][^<]{0,200}(?:Adres|adres)[^<]{0,150}(?:post[eę]powania|zamówienia|zamowienia)",
        re.IGNORECASE | re.DOTALL,
    )
    m = section_re.search(html_body)
    if m:
        window = html_body[m.start() : m.start() + 600]
        for raw_url in re.findall(r'https?://[^\s<"\'\\]+', window):
            url = raw_url.rstrip(".,;)<>")
            if _is_platform_url(url):
                return url

    # Strategia 2: dowolny URL z listy platform w całym dokumencie
    seen: set[str] = set()
    for raw_url in re.findall(r'https?://[^\s<"\'\\]+', html_body):
        url = raw_url.rstrip(".,;)<>")
        if url in seen:
            continue
        seen.add(url)
        if _is_platform_url(url) and "ezamowienia.gov.pl" not in url:
            return url

    return None


def _classify_document(filename: str) -> str:
    """Klasyfikuje typ dokumentu na podstawie nazwy pliku."""
    lower = filename.lower()
    if lower.endswith(".url"):
        return "SWZ"
    if lower.endswith(".pdf") and "ogloszenie" in lower:
        return "NOTICE"
    if any(k in lower for k in ("swz", "siwz", "specyfikacja")):
        return "SWZ"
    if any(k in lower for k in ("formularz", "ofert")):
        return "FORM"
    if any(k in lower for k in ("umow", "postanowieni")):
        return "CONTRACT"
    if any(k in lower for k in ("oświadczen", "oswiadczen")):
        return "DECLARATION"
    if "wykaz" in lower:
        return "LIST"
    if any(k in lower for k in ("dokumentacj", "projekt", "rysun")):
        return "TECHNICAL"
    if any(k in lower for k in ("zmian", "modyfikacj")):
        return "AMENDMENT"
    return "OTHER"


def extract_tender_id_from_url(url: str) -> str | None:
    """Wyciąga OCDS tender ID z URL ezamowienia.gov.pl."""
    m = re.search(r"(ocds-\d+-[a-f0-9\-]+)", url or "")
    return m.group(1) if m else None


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Terra-OS BZP Document Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Przykłady:
  python bzp_document_scraper.py "2026/BZP 00331648" --list-only
  python bzp_document_scraper.py "2026/BZP 00331648" --output-dir /tmp/docs
  python bzp_document_scraper.py "2026/BZP 00331648" --json
""",
    )
    parser.add_argument("tender_id", help="Numer BZP (np. '2026/BZP 00331648') lub OCDS ID")
    parser.add_argument("--list-only",   action="store_true", help="Tylko listuj, nie pobieraj")
    parser.add_argument("--output-dir",  default="/tmp/terra-docs",   help="Katalog docelowy")
    parser.add_argument("--json",        action="store_true", dest="as_json", help="Wynik jako JSON")
    args = parser.parse_args()

    scraper = BZPDocumentScraper(storage_dir=Path(args.output_dir))

    with scraper:
        if args.list_only:
            docs = scraper.list_documents(args.tender_id)
            if args.as_json:
                print(json.dumps(
                    [{"name": d.name, "filename": d.filename, "type": d.doc_type, "url": d.url}
                     for d in docs],
                    indent=2, ensure_ascii=False,
                ))
            else:
                print(f"\nDokumenty dla: {args.tender_id}")
                for i, d in enumerate(docs, 1):
                    print(f"  {i}. [{d.doc_type:8}] {d.filename}")
                    print(f"       {d.url[:100]}")
                print(f"\nŁącznie: {len(docs)}")
        else:
            result = scraper.fetch_all(args.tender_id, download_files=True)
            if args.as_json:
                print(json.dumps({
                    "tender_id":       result.tender_id,
                    "bzp_number":      result.bzp_number,
                    "documents":       len(result.documents),
                    "downloaded":      result.downloaded,
                    "errors":          result.errors,
                    "notice_pdf":      result.notice_pdf_path,
                    "swz_platform_url": result.swz_platform_url,
                    "files": [
                        {
                            "filename": d.filename,
                            "type":     d.doc_type,
                            "size_kb":  (d.file_size or 0) // 1024,
                            "path":     d.local_path,
                            "url":      d.url,
                        }
                        for d in result.documents
                    ],
                }, indent=2, ensure_ascii=False))
            else:
                print(f"\nPrzetarg:  {result.tender_id}")
                print(f"BZP:       {result.bzp_number or '—'}")
                print(f"Dokumenty: {len(result.documents)}")
                print(f"Pobrano:   {result.downloaded}")
                if result.swz_platform_url:
                    print(f"SWZ URL:   {result.swz_platform_url}")
                if result.errors:
                    print(f"\nBłędy:")
                    for e in result.errors:
                        print(f"  ! {e}")
                print("\nPliki:")
                for d in result.documents:
                    ok   = "✓" if d.local_path else "✗"
                    size = f"({d.file_size // 1024} KB)" if d.file_size else ""
                    print(f"  {ok} [{d.doc_type:8}] {d.filename} {size}")
                    if not d.local_path:
                        print(f"       → {d.url[:100]}")
