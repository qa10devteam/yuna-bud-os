"""Terra-OS Platform Document Scraper — State-of-the-Art.

Pobiera WSZYSTKIE dokumenty SWZ z zewnętrznych platform zakupowych.
Obsługuje: platformazakupowa.pl, ezamawiajacy.pl (Marketplanet),
           logintrade.net/pl, eb2b.com.pl, smartpzp.pl, e-propublico.pl,
           josephine.pl, sidaspzp.pl, openplatform.pl, proebiz.com i inne.

Architektura:
  PlatformDocumentScraper.scrape(url)  → list[PlatformDocument]
  Dispatcher wykrywa platformę po domenie i deleguje do konkretnego Handlera.
  Każdy Handler parsuje HTML/JSON/API i zwraca listę dokumentów.
  Fallback: GenericHTMLHandler (wyciąga wszystkie linki do plików).

Limity:
  - Timeout: 20s/request, max 60s łącznie
  - Max pliki: 200 per przetarg
  - Rozmiar pliku: 200 MB
  - Retry: 3x z exponential backoff
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse, unquote

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Stałe
# ─────────────────────────────────────────────────────────────────

MAX_DOCS_PER_TENDER = 200
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB
REQUEST_TIMEOUT = 20
TOTAL_TIMEOUT = 60
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.5

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_KNOWN_DOC_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".7z",
    ".odt", ".ods", ".ppt", ".pptx", ".txt", ".xml", ".csv", ".dwg",
    ".dxf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".msg", ".eml",
}

# ─────────────────────────────────────────────────────────────────
# Struktury danych
# ─────────────────────────────────────────────────────────────────

@dataclass
class PlatformDocument:
    name: str
    url: str
    filename: str = ""
    doc_type: str = "OTHER"
    file_size: Optional[int] = None
    platform: str = "unknown"
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.filename:
            self.filename = _url_to_filename(self.url) or self.name[:80]
        if self.doc_type == "OTHER":
            self.doc_type = _classify_by_name(self.name or self.filename)


# ─────────────────────────────────────────────────────────────────
# Główna klasa
# ─────────────────────────────────────────────────────────────────

class PlatformDocumentScraper:
    """Dispatcher — wykrywa platformę i deleguje do Handlera."""

    def __init__(self):
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=8.0, read=REQUEST_TIMEOUT,
                    write=10.0, pool=5.0,
                ),
                follow_redirects=True,
                headers={
                    "User-Agent": _UA,
                    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.9",
                    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.7",
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

    def scrape(self, url: str) -> list[PlatformDocument]:
        """Pobiera listę wszystkich dokumentów z platformy zakupowej.

        Args:
            url: URL ogłoszenia/postępowania na platformie zakupowej.

        Returns:
            Lista PlatformDocument (może być pusta przy błędzie lub braku dok.).
        """
        if not url or not url.startswith("http"):
            return []

        parsed = urlparse(url)
        host = parsed.netloc.lower().rstrip(".")
        client = self._get_client()

        # Dispatcher — kolejność: najbardziej specyficzne → generyczne
        handler = self._pick_handler(host)
        platform_name = handler.__class__.__name__.replace("Handler", "").lower()

        try:
            docs = handler.fetch(url, client)
        except Exception as exc:
            logger.warning("platform_scraper host=%s error=%s", host, exc)
            docs = []

        # Uzupełnij platformę
        for d in docs:
            if not d.platform or d.platform == "unknown":
                d.platform = platform_name

        docs = docs[:MAX_DOCS_PER_TENDER]
        logger.info(
            "platform_scraper url=%s platform=%s docs=%d",
            url[:80], platform_name, len(docs),
        )
        return docs

    def _pick_handler(self, host: str) -> "_BaseHandler":
        """Zwraca najlepszy handler dla danej domeny."""
        if "platformazakupowa.pl" in host:
            return OpenNexusHandler()
        if "ezamowienia.gov.pl" in host:
            return EZamiowieniaGovHandler()
        if "ezamawiajacy.pl" in host:
            return MarketplanetHandler()
        if "logintrade.net" in host or "logintrade.pl" in host:
            return LogintradeHandler()
        if "eb2b.com.pl" in host or "eb2b.pl" in host:
            return EB2BHandler()
        if "smartpzp.pl" in host:
            return SmartPZPHandler()
        if "josephine.pl" in host or "e-propublico.pl" in host or "epropublico.pl" in host:
            return JosephineHandler()
        if "sidaspzp.pl" in host:
            return SidasPZPHandler()
        if "openplatform.pl" in host:
            return OpenPlatformHandler()
        if "proebiz.com" in host:
            return ProebizHandler()
        if "oneplace.marketplanet.pl" in host:
            return MarketplanetOneplaceHandler()
        if "josephine.no" in host:
            return JosephineHandler()
        return GenericHTMLHandler()


# ─────────────────────────────────────────────────────────────────
# Base Handler
# ─────────────────────────────────────────────────────────────────

class _BaseHandler:
    """Bazowy handler — dostarcza narzędzia pomocnicze."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        raise NotImplementedError

    def _get_page(self, url: str, client: httpx.Client) -> Optional[BeautifulSoup]:
        """Pobiera stronę i zwraca BeautifulSoup lub None."""
        try:
            r = _retry_get(client, url)
            if r is None or r.status_code >= 400:
                return None
            return BeautifulSoup(r.text, "lxml")
        except Exception as exc:
            logger.debug("get_page error url=%s: %s", url[:80], exc)
            return None

    def _get_json(self, url: str, client: httpx.Client) -> Optional[dict | list]:
        """Pobiera JSON lub None."""
        try:
            r = _retry_get(client, url, extra_headers={"Accept": "application/json"})
            if r is None or r.status_code >= 400:
                return None
            return r.json()
        except Exception:
            return None

    def _extract_file_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        extra_patterns: Optional[list[str]] = None,
    ) -> list[PlatformDocument]:
        """Generyczna ekstrakcja linków do plików z HTML."""
        docs = []
        seen = set()
        patterns = [
            r"/file/",
            r"/download",
            r"/attachment",
            r"getFile",
            r"getAttach",
            r"DocumentService",
            r"pobierz",
            r"download",
        ] + (extra_patterns or [])

        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue

            # Sprawdź rozszerzenie lub wzorzec URL
            ext = _get_ext(href)
            is_doc = ext in _KNOWN_DOC_EXTENSIONS or any(
                p.lower() in href.lower() for p in patterns
            )
            if not is_doc:
                continue

            # Normalizuj URL
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = urljoin(base_url, href)

            href = href.rstrip(".,;)")
            if href in seen:
                continue
            seen.add(href)

            name = (
                a.get_text(strip=True)
                or a.get("title", "")
                or a.get("aria-label", "")
                or _url_to_filename(href)
                or href.split("/")[-1]
            )
            name = name[:200]

            docs.append(PlatformDocument(
                name=name,
                url=href,
                filename=_url_to_filename(href) or _slugify(name),
            ))

        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: Open Nexus — platformazakupowa.pl
# ─────────────────────────────────────────────────────────────────

class OpenNexusHandler(_BaseHandler):
    """Handler dla platformazakupowa.pl (Open Nexus).

    Dokumenty pod: /transakcja/{id}/dokumenty
    Pliki pod: /file/get_new/{md5hash}.{ext}
    """

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Wyciągnij ID transakcji
        m = re.search(r"/transakcja/(\d+)", url)
        if not m:
            # Może być inny format — spróbuj generic scraping
            return self._scrape_page(url, base, client)

        tid = m.group(1)
        docs_url = f"{base}/transakcja/{tid}/dokumenty"

        # Pobierz stronę dokumentów
        soup = self._get_page(docs_url, client)
        if soup is None:
            soup = self._get_page(url, client)
            if soup is None:
                return []

        return self._parse_documents_page(soup, base, tid)

    def _parse_documents_page(
        self, soup: BeautifulSoup, base: str, tid: str
    ) -> list[PlatformDocument]:
        docs = []
        seen = set()

        # Metoda 1: linki /file/get_new/{hash}.{ext}
        for a in soup.find_all("a", href=re.compile(r"/file/get_new/")):
            href = a["href"]
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = f"https://platformazakupowa.pl{href}"

            if href in seen:
                continue
            seen.add(href)

            name = a.get_text(strip=True) or _url_to_filename(href)
            # Spróbuj znaleźć nazwę w rodzicu
            parent = a.find_parent("tr") or a.find_parent("li") or a.find_parent("div")
            if parent:
                # Szukaj komórki z nazwą pliku
                cells = parent.find_all(["td", "span", "div"])
                for cell in cells:
                    txt = cell.get_text(strip=True)
                    if txt and txt != name and len(txt) > 3:
                        name = txt
                        break

            docs.append(PlatformDocument(
                name=name[:200] or _url_to_filename(href),
                url=href,
                filename=_url_to_filename(href),
                platform="platformazakupowa",
            ))

        # Metoda 2: data-file attribute
        for el in soup.find_all(attrs={"data-file": True}):
            fhash = el["data-file"]
            href = f"https://platformazakupowa.pl/file/get_new/{fhash}"
            if href not in seen:
                seen.add(href)
                docs.append(PlatformDocument(
                    name=el.get_text(strip=True) or fhash,
                    url=href,
                    platform="platformazakupowa",
                ))

        # Metoda 3: JSON embedded w <script>
        for script in soup.find_all("script"):
            txt = script.string or ""
            for m2 in re.finditer(
                r'"url"\s*:\s*"(/file/get_new/[a-f0-9]+\.[a-z]{2,5})"', txt
            ):
                href = "https://platformazakupowa.pl" + m2.group(1)
                if href not in seen:
                    seen.add(href)
                    fname = m2.group(1).split("/")[-1]
                    docs.append(PlatformDocument(
                        name=fname,
                        url=href,
                        platform="platformazakupowa",
                    ))

        # Metoda 4: pełny fallback generic
        if not docs:
            docs = self._extract_file_links(
                soup, f"https://platformazakupowa.pl", [r"/file/"]
            )

        return docs

    def _scrape_page(self, url: str, base: str, client: httpx.Client) -> list[PlatformDocument]:
        soup = self._get_page(url, client)
        if not soup:
            return []
        return self._parse_documents_page(soup, base, "")


# ─────────────────────────────────────────────────────────────────
# Handler: Marketplanet — ezamawiajacy.pl
# ─────────────────────────────────────────────────────────────────

class MarketplanetHandler(_BaseHandler):
    """Handler dla *.ezamawiajacy.pl (Marketplanet ONE).

    Platforma JS-heavy (Knockout.js). Dokumenty ładowane dynamicznie.
    Strategie:
      1. HTML parsing — szukaj linków w załadowanym HTML
      2. HomeServlet API — publicFilesList
      3. REST API probe — /api/demand/{id}/files
      4. Embed JSON parsing — szukaj JSON w skryptach
    """

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Wyciągnij org i demand_id
        m = re.search(
            r"\.ezamawiajacy\.pl/pn/([^/]+)/demand/(\d+)", url
        )
        if not m:
            return self._generic_fetch(url, base, client)

        org, demand_id = m.group(1), m.group(2)

        # Upewnij się że pobieramy stronę /notice/public/details
        details_url = f"{base}/pn/{org}/demand/{demand_id}/notice/public/details"
        soup = self._get_page(details_url, client)
        if soup is None:
            soup = self._get_page(url, client)
        if soup is None:
            return []

        return self._parse_marketplanet_table(soup, base)

    def _parse_marketplanet_table(
        self, soup: BeautifulSoup, base: str
    ) -> list[PlatformDocument]:
        """Parsuje tabelę Marketplanet z wierszami class='fileDataRow'.

        Struktura:
          <tr class="fileDataRow" id="_{identity}">
            <td class="text long">Nazwa pliku</td>
            ...
          </tr>

        URL pobierania to /download/{token} osadzony w HTML jako JS href.
        """
        docs = []
        seen = set()
        full_html = str(soup)

        # Mapa identity → /download/TOKEN z HTML (pattern: /download/\w+)
        # Tokeny są w tym samym HTML co tabela (React/Knockout hydration)
        # Zbierz wszystkie /download/ URL z HTML
        all_dl_urls = re.findall(r'(/download/[A-Za-z0-9_-]{10,})', full_html)
        # Usuń duplikaty ?openInBrowser
        all_dl_urls = [u.split("?")[0] for u in all_dl_urls]
        # Filtruj unikalne
        unique_dl_urls: list[str] = []
        seen_dl = set()
        for u in all_dl_urls:
            if u not in seen_dl:
                seen_dl.add(u)
                unique_dl_urls.append(u)

        # Zbierz nazwy plików z tabeli - wiersze class="fileDataRow"
        rows = soup.find_all("tr", class_="fileDataRow")
        file_names: list[str] = []
        for row in rows:
            name_td = row.find("td", class_="text long") or row.find("td", class_=re.compile(r"\blong\b"))
            if name_td:
                name = name_td.get_text(strip=True)
                if name:
                    file_names.append(name)

        # Zip nazwy z URL-ami (kolejność jest zachowana w HTML)
        for i, name in enumerate(file_names):
            if i < len(unique_dl_urls):
                dl_url = base + unique_dl_urls[i]
            else:
                dl_url = ""

            if not dl_url:
                continue
            if dl_url in seen:
                continue
            seen.add(dl_url)

            docs.append(PlatformDocument(
                name=name,
                url=dl_url,
                filename=name,
                platform="ezamawiajacy",
            ))

        # Fallback: jeśli nie było tabeli fileDataRow, spróbuj generic link extraction
        if not docs:
            for u in unique_dl_urls:
                full_u = base + u
                if full_u not in seen:
                    seen.add(full_u)
                    docs.append(PlatformDocument(
                        name=u.split("/")[-1],
                        url=full_u,
                        platform="ezamawiajacy",
                    ))

        return docs

    def _parse_marketplanet_html(
        self,
        soup: BeautifulSoup,
        base: str,
        org: str,
        demand_id: str,
    ) -> list[PlatformDocument]:
        docs = []
        seen = set()

        # Wzorzec 1: linki z getFile, download, attachment
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not any(k in href.lower() for k in [
                "getfile", "download", "attachment", ".pdf", ".doc", ".docx",
                ".zip", ".xls", "getdoc", "pobierz",
            ]):
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = urljoin(base, href)
            href = href.rstrip(".,;)")
            if href in seen:
                continue
            seen.add(href)
            name = a.get_text(strip=True) or _url_to_filename(href)
            docs.append(PlatformDocument(
                name=name[:200], url=href, platform="ezamawiajacy"
            ))

        # Wzorzec 2: JSON embedded w skryptach
        for script in soup.find_all("script"):
            txt = script.string or ""
            # fileId + fileName
            for m in re.finditer(
                r'"fileId"\s*:\s*"([^"]+)"[^}]*"fileName"\s*:\s*"([^"]+)"', txt
            ):
                fid, fname = m.group(1), m.group(2)
                dl_url = (
                    f"{base}/pn/{org}/demand/{demand_id}/notice/public/attachments/{fid}"
                )
                if dl_url not in seen:
                    seen.add(dl_url)
                    docs.append(PlatformDocument(
                        name=fname, url=dl_url,
                        filename=fname, platform="ezamawiajacy",
                    ))

            # documentId + documentName
            for m in re.finditer(
                r'"documentId"\s*:\s*"([^"]+)"[^}]*"documentName"\s*:\s*"([^"]+)"', txt
            ):
                did, dname = m.group(1), m.group(2)
                dl_url = f"{base}/pn/{org}/demand/{demand_id}/documents/{did}"
                if dl_url not in seen:
                    seen.add(dl_url)
                    docs.append(PlatformDocument(
                        name=dname, url=dl_url,
                        filename=dname, platform="ezamawiajacy",
                    ))

        return docs

    def _parse_marketplanet_json(
        self,
        data: dict | list,
        base: str,
        org: str,
        demand_id: str,
    ) -> list[PlatformDocument]:
        docs = []
        items = data if isinstance(data, list) else data.get("files", data.get("documents", data.get("attachments", [])))
        for item in items:
            if not isinstance(item, dict):
                continue
            fid = item.get("fileId") or item.get("id") or item.get("documentId", "")
            fname = item.get("fileName") or item.get("name") or item.get("documentName", "")
            dl_url = item.get("url") or item.get("downloadUrl") or (
                f"{base}/pn/{org}/demand/{demand_id}/notice/public/attachments/{fid}" if fid else ""
            )
            if dl_url:
                docs.append(PlatformDocument(
                    name=fname or fid,
                    url=dl_url,
                    filename=fname or fid,
                    platform="ezamawiajacy",
                ))
        return docs

    def _generic_fetch(self, url: str, base: str, client: httpx.Client) -> list[PlatformDocument]:
        soup = self._get_page(url, client)
        if not soup:
            return []
        return self._extract_file_links(soup, base, ["getFile", "download", "attachment"])


# ─────────────────────────────────────────────────────────────────
# Handler: Logintrade — *.logintrade.net / *.logintrade.pl
# ─────────────────────────────────────────────────────────────────

class LogintradeHandler(_BaseHandler):
    """Handler dla *.logintrade.net i *.logintrade.pl.

    Pliki jako: DocumentService,getAttachmentUnlogged,{base64token}.html
    URL musi być: https://{host}/DocumentService,getAttachmentUnlogged,{token}.html
    """

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        soup = self._get_page(url, client)
        if soup is None:
            return []

        docs = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue

            # DocumentService,getAttachmentUnlogged
            if "DocumentService" in href or "getAttachmentUnlogged" in href:
                # Napraw URL — często brakuje separatora /
                if not href.startswith("http"):
                    # Relative: "DocumentService,getAttachmentUnlogged,TOKEN.html"
                    # Buduj: https://{host}/DocumentService,...
                    full = f"{base}/{href.lstrip('/')}"
                else:
                    full = href

                if full in seen:
                    continue
                seen.add(full)

                # Spróbuj pobrać nazwę pliku z Content-Disposition headera
                name = a.get_text(strip=True) or ""
                filename = _url_to_filename(full)
                if not filename or filename.endswith(".html"):
                    # Pobierz HEAD żeby zobaczyć Content-Disposition
                    try:
                        head_r = client.head(full, timeout=8)
                        cd = head_r.headers.get("content-disposition", "")
                        fn = _parse_content_disposition(cd)
                        if fn:
                            filename = fn
                            if not name:
                                name = fn
                    except Exception:
                        pass

                # Szukaj nazwy pliku w sąsiedniej komórce tabeli
                if not name:
                    parent_row = a.find_parent("tr")
                    if parent_row:
                        cells = parent_row.find_all("td")
                        for cell in cells:
                            txt = cell.get_text(strip=True)
                            if txt and len(txt) > 3 and "pobierz" not in txt.lower():
                                name = txt
                                break

                docs.append(PlatformDocument(
                    name=name or filename or "dokument",
                    url=full,
                    filename=filename or "dokument",
                    platform="logintrade",
                ))

            # Standardowe linki do plików
            elif _get_ext(href) in _KNOWN_DOC_EXTENSIONS:
                if href.startswith("//"):
                    href = "https:" + href
                elif not href.startswith("http"):
                    href = urljoin(base, href)
                if href not in seen:
                    seen.add(href)
                    name = a.get_text(strip=True) or _url_to_filename(href)
                    docs.append(PlatformDocument(
                        name=name, url=href, platform="logintrade"
                    ))

        # Fallback jeśli nic nie znaleziono
        if not docs:
            docs = self._extract_file_links(soup, base, ["DocumentService", "download"])

        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: EB2B — *.eb2b.com.pl
# ─────────────────────────────────────────────────────────────────

class EB2BHandler(_BaseHandler):
    """Handler dla *.eb2b.com.pl."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        soup = self._get_page(url, client)
        if soup is None:
            return []

        docs = []
        seen = set()

        # EB2B: linki z /download/, /file/, .pdf, .docx itd.
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            ext = _get_ext(href)
            is_doc = ext in _KNOWN_DOC_EXTENSIONS or any(
                k in href.lower() for k in ["/download/", "/file/", "/attachment/", "getFile", "pobierz"]
            )
            if not is_doc:
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = urljoin(base, href)
            href = href.rstrip(".,;)")
            if href in seen:
                continue
            seen.add(href)
            name = a.get_text(strip=True) or _url_to_filename(href)
            docs.append(PlatformDocument(name=name, url=href, platform="eb2b"))

        # EB2B może mieć API /api/tender/{id}/attachments
        m = re.search(r"/tender[s]?/(\d+)", url)
        if not m:
            m = re.search(r"/announcement/(\d+)", url)
        if m and not docs:
            api_url = f"{base}/api/announcements/{m.group(1)}/attachments"
            data = self._get_json(api_url, client)
            if data:
                docs.extend(self._parse_eb2b_json(data, base))

        return docs

    def _parse_eb2b_json(self, data: list | dict, base: str) -> list[PlatformDocument]:
        docs = []
        items = data if isinstance(data, list) else data.get("attachments", data.get("files", []))
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("downloadUrl") or item.get("href", "")
            name = item.get("name") or item.get("fileName") or item.get("title", "")
            if url:
                if not url.startswith("http"):
                    url = urljoin(base, url)
                docs.append(PlatformDocument(
                    name=name or _url_to_filename(url),
                    url=url,
                    platform="eb2b",
                ))
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: SmartPZP — smartpzp.pl
# ─────────────────────────────────────────────────────────────────

class SmartPZPHandler(_BaseHandler):
    """Handler dla smartpzp.pl."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        soup = self._get_page(url, client)
        if soup is None:
            return []

        docs = []
        seen = set()

        # SmartPZP: linki /api/v1/attachments/{id} lub /download/{id}
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            is_doc = (
                _get_ext(href) in _KNOWN_DOC_EXTENSIONS
                or any(k in href for k in ["/download/", "/attachment", "/api/v1/attach", "getFile"])
            )
            if not is_doc:
                continue
            if not href.startswith("http"):
                href = urljoin(base, href)
            if href in seen:
                continue
            seen.add(href)
            name = a.get_text(strip=True) or _url_to_filename(href)
            docs.append(PlatformDocument(name=name, url=href, platform="smartpzp"))

        # API probe
        if not docs:
            m = re.search(r"/tender[s]?/([a-f0-9-]{36})", url)
            if not m:
                m = re.search(r"/postepowania?/([a-f0-9-]{36})", url)
            if m:
                tid = m.group(1)
                for api_path in [
                    f"/api/v1/tender/{tid}/attachments",
                    f"/api/v1/procurement/{tid}/documents",
                    f"/api/tenders/{tid}/files",
                ]:
                    data = self._get_json(base + api_path, client)
                    if data:
                        docs = self._parse_generic_json(data, base, "smartpzp")
                        if docs:
                            break

        return docs

    def _parse_generic_json(self, data, base, platform) -> list[PlatformDocument]:
        docs = []
        items = data if isinstance(data, list) else (
            data.get("data", data.get("items", data.get("attachments", data.get("documents", []))))
        )
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("downloadUrl") or item.get("href") or item.get("fileUrl", "")
            name = item.get("name") or item.get("fileName") or item.get("title") or item.get("documentName", "")
            if url:
                if not url.startswith("http"):
                    url = urljoin(base, url)
                docs.append(PlatformDocument(
                    name=name or _url_to_filename(url),
                    url=url,
                    platform=platform,
                ))
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: Josephine/e-ProPublico — josephine.pl, e-propublico.pl
# ─────────────────────────────────────────────────────────────────

class JosephineHandler(_BaseHandler):
    """Handler dla josephine.pl, e-propublico.pl."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        soup = self._get_page(url, client)
        if soup is None:
            return []

        docs = self._extract_file_links(soup, base, [
            "download", "attachment", "file", "getDoc",
        ])
        for d in docs:
            d.platform = "josephine"
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: SidasPZP — sidaspzp.pl
# ─────────────────────────────────────────────────────────────────

class SidasPZPHandler(_BaseHandler):
    """Handler dla sidaspzp.pl."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        soup = self._get_page(url, client)
        if soup is None:
            return []

        docs = self._extract_file_links(soup, base, ["download", "attachment", "getFile"])
        for d in docs:
            d.platform = "sidaspzp"

        # SidasPZP REST API probe
        if not docs:
            m = re.search(r"/postepowania?/(\d+)", url)
            if m:
                pid = m.group(1)
                data = self._get_json(f"{base}/api/postepowania/{pid}/dokumenty", client)
                if data:
                    for item in (data if isinstance(data, list) else []):
                        iurl = item.get("url") or item.get("link", "")
                        iname = item.get("nazwa") or item.get("name", "")
                        if iurl:
                            if not iurl.startswith("http"):
                                iurl = urljoin(base, iurl)
                            docs.append(PlatformDocument(
                                name=iname or iurl.split("/")[-1],
                                url=iurl, platform="sidaspzp",
                            ))
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: OpenPlatform — openplatform.pl
# ─────────────────────────────────────────────────────────────────

class OpenPlatformHandler(_BaseHandler):
    """Handler dla openplatform.pl."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        soup = self._get_page(url, client)
        if soup is None:
            return []
        docs = self._extract_file_links(soup, base, ["download", "attachment", "file"])
        for d in docs:
            d.platform = "openplatform"
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: Proebiz — proebiz.com
# ─────────────────────────────────────────────────────────────────

class ProebizHandler(_BaseHandler):
    """Handler dla proebiz.com."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        soup = self._get_page(url, client)
        if soup is None:
            return []
        docs = self._extract_file_links(soup, base, ["download", "attachment", "file"])
        for d in docs:
            d.platform = "proebiz"
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: Marketplanet Oneplace — oneplace.marketplanet.pl
# ─────────────────────────────────────────────────────────────────

class MarketplanetOneplaceHandler(_BaseHandler):
    """Handler dla oneplace.marketplanet.pl."""

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        soup = self._get_page(url, client)
        if soup is None:
            return []
        docs = self._extract_file_links(soup, base, ["getFile", "download", "attachment"])
        for d in docs:
            d.platform = "marketplanet_oneplace"
        return docs


# ─────────────────────────────────────────────────────────────────
# Handler: Generic HTML — fallback dla nieznanych platform
# ─────────────────────────────────────────────────────────────────

class EZamiowieniaGovHandler(_BaseHandler):
    """Handler dla ezamowienia.gov.pl (Angular SPA z publicznym REST API).

    URL wejściowy: https://ezamowienia.gov.pl/mp-client/search/list/<tender_id>
    Endpointy (bez autoryzacji):
      GET /mp-readmodels/api/Search/GetTenderDocuments?tenderId=<id>   → JSON lista
      GET /mp-readmodels/api/Tender/DownloadDocument/<tender_id>/<obj_id> → plik
    """

    BASE = "https://ezamowienia.gov.pl"
    LIST_API = BASE + "/mp-readmodels/api/Search/GetTenderDocuments"
    DOWNLOAD_API = BASE + "/mp-readmodels/api/Tender/DownloadDocument"

    _OCDS_RE = re.compile(r"(ocds-[a-z0-9]+-[a-f0-9-]{32,})", re.IGNORECASE)

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        m = self._OCDS_RE.search(url)
        if not m:
            logger.warning("ezamowienia handler: brak OCDS ID w URL: %s", url)
            return []

        tender_id = m.group(1)

        # Krok 1: Pobierz listę dokumentów
        try:
            resp = client.get(
                self.LIST_API,
                params={"tenderId": tender_id},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("ezamowienia GetTenderDocuments failed: %s", exc)
            return []

        docs: list[PlatformDocument] = []

        # data może być listą lub dict z listą
        items = data if isinstance(data, list) else data.get("tenderDocuments", data.get("documents", []))
        if not isinstance(items, list):
            logger.warning("ezamowienia: nieznana struktura odpowiedzi: %s", str(data)[:200])
            return []

        for item in items:
            obj_id = item.get("objectId") or item.get("id") or item.get("objectID")
            name = item.get("name") or item.get("fileName") or item.get("filename") or str(obj_id)
            filename = item.get("fileName") or item.get("filename") or name
            if not obj_id:
                continue

            download_url = f"{self.DOWNLOAD_API}/{tender_id}/{obj_id}"

            # Wykryj typ dokumentu
            name_lower = name.lower()
            if "swz" in name_lower or "specyfikacja" in name_lower:
                doc_type = "SWZ"
            elif "opz" in name_lower or "opis przedmiotu" in name_lower:
                doc_type = "OPZ"
            elif "umow" in name_lower or "kontrakt" in name_lower:
                doc_type = "CONTRACT"
            elif "formularz" in name_lower or "ofert" in name_lower:
                doc_type = "FORM"
            else:
                doc_type = "OTHER"

            docs.append(PlatformDocument(
                name=name,
                filename=filename,
                url=download_url,
                doc_type=doc_type,
                platform="ezamowienia",
                file_size=item.get("size") or item.get("fileSize"),
            ))

        logger.info("ezamowienia: znaleziono %d dokumentów dla %s", len(docs), tender_id)
        return docs


class GenericHTMLHandler(_BaseHandler):
    """Generyczny handler — parsuje HTML i wyciąga wszystkie linki do plików.

    Działa dla większości platform, które renderują listę plików w HTML.
    Obsługuje: typowe rozszerzenia, słowa kluczowe download/file/pobierz.
    """

    def fetch(self, url: str, client: httpx.Client) -> list[PlatformDocument]:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        soup = self._get_page(url, client)
        if soup is None:
            return []

        docs = self._extract_file_links(soup, base)
        for d in docs:
            d.platform = "generic"

        # Spróbuj też sub-stron dokumentów
        if not docs:
            doc_pages = self._find_doc_subpages(soup, base, url)
            for sub_url in doc_pages[:3]:
                sub_soup = self._get_page(sub_url, client)
                if sub_soup:
                    sub_docs = self._extract_file_links(sub_soup, base)
                    docs.extend(sub_docs)

        return docs

    def _find_doc_subpages(
        self, soup: BeautifulSoup, base: str, current_url: str
    ) -> list[str]:
        """Szuka linków do podstron z dokumentami."""
        subpages = []
        keywords = ["dokument", "document", "attachment", "plik", "file", "swz", "siwz", "pobierz"]
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True).lower()
            if any(kw in text for kw in keywords) or any(kw in href.lower() for kw in keywords):
                if not href.startswith("http"):
                    href = urljoin(base, href)
                if href != current_url and href not in subpages:
                    subpages.append(href)
        return subpages[:5]


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _retry_get(
    client: httpx.Client,
    url: str,
    extra_headers: Optional[dict] = None,
) -> Optional[httpx.Response]:
    """GET z retry + exponential backoff."""
    headers = extra_headers or {}
    last_exc: Optional[Exception] = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            r = client.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if r.status_code < 500:
                return r
            if r.status_code == 429:
                time.sleep(RETRY_DELAY * attempt * 2)
                continue
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY * attempt)
        except httpx.HTTPError as exc:
            last_exc = exc
            break
    if last_exc:
        logger.debug("_retry_get failed url=%s: %s", url[:80], last_exc)
    return None


def _get_ext(url_or_path: str) -> str:
    """Zwraca rozszerzenie pliku z URL (np. '.pdf')."""
    # Usuń query string
    path = url_or_path.split("?")[0].split("#")[0]
    # Wyciągnij ostatnią część
    last = path.rstrip("/").split("/")[-1]
    dot_idx = last.rfind(".")
    if dot_idx == -1:
        return ""
    ext = last[dot_idx:].lower()
    # Tylko rozsądne rozszerzenia (max 6 znaków)
    return ext if len(ext) <= 6 else ""


def _url_to_filename(url: str) -> str:
    """Wyciąga nazwę pliku z URL."""
    path = url.split("?")[0].split("#")[0].rstrip("/")
    name = path.split("/")[-1]
    name = unquote(name)
    # Usuń tokenowe identyfikatory bez rozszerzenia
    if len(name) > 60 and "." not in name:
        return ""
    return name[:200]


def _slugify(text: str) -> str:
    """Prosta normalizacja nazwy na bezpieczny filename."""
    text = re.sub(r"[^\w\s\-.]", "_", text.lower())
    text = re.sub(r"\s+", "_", text.strip())
    return text[:80] or "dokument"


def _classify_by_name(name: str) -> str:
    """Klasyfikuje dokument na podstawie nazwy."""
    lower = name.lower()
    if any(k in lower for k in ("swz", "siwz", "specyfikacja")):
        return "SWZ"
    if any(k in lower for k in ("ogłoszenie", "ogloszenie", "notice")):
        return "NOTICE"
    if any(k in lower for k in ("formularz", "oferta", "wzór")):
        return "FORM"
    if any(k in lower for k in ("umow", "kontrakt", "contract")):
        return "CONTRACT"
    if any(k in lower for k in ("projekt", "rysunek", "rys.", "plan")):
        return "TECHNICAL"
    if any(k in lower for k in ("zmian", "modyfikacj", "poprawka")):
        return "AMENDMENT"
    if any(k in lower for k in ("oświadczen", "oswiadczen", "declaration")):
        return "DECLARATION"
    return "OTHER"


def _parse_content_disposition(cd: str) -> str:
    """Wyciąga filename z Content-Disposition headera."""
    # filename*=UTF-8''encoded_name
    m = re.search(r"filename\*\s*=\s*(?:UTF-8''|utf-8'')([^\s;]+)", cd, re.I)
    if m:
        try:
            from urllib.parse import unquote
            return unquote(m.group(1))
        except Exception:
            pass
    # filename="name"
    m = re.search(r'filename\s*=\s*["\']?([^"\';\r\n]+)["\']?', cd, re.I)
    if m:
        return m.group(1).strip().strip("\"'")
    return ""


# ─────────────────────────────────────────────────────────────────
# Moduł-level convenience
# ─────────────────────────────────────────────────────────────────

def scrape_platform_documents(url: str) -> list[PlatformDocument]:
    """One-shot helper: scrape i zwróć dokumenty dla platformy URL."""
    with PlatformDocumentScraper() as scraper:
        return scraper.scrape(url)
