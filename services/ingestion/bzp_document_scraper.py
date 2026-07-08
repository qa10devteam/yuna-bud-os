"""Terra-OS BZP Document Scraper.

Fetches SWZ documents from ezamowienia.gov.pl public API.
No authentication required — all endpoints are public.

Key endpoints discovered:
  1. Document list:   GET /mp-readmodels/api/Search/GetTenderDocuments?tenderId={tenderId}
  2. Download file:   GET /mp-readmodels/api/Tender/DownloadDocument/{tenderId}/{objectId}
  3. Notice PDF:      GET /mo-board/api/v1/Board/GetNoticePdf?noticeNumber={encoded_bzp_number}
  4. Tender details:  GET /mp-readmodels/api/Search/GetTender?id={tenderId}
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────

BZP_BASE = "https://ezamowienia.gov.pl"
DOCUMENTS_API = f"{BZP_BASE}/mp-readmodels/api/Search/GetTenderDocuments"
DOWNLOAD_API = f"{BZP_BASE}/mp-readmodels/api/Tender/DownloadDocument"
NOTICE_PDF_API = f"{BZP_BASE}/mo-board/api/v1/Board/GetNoticePdf"
TENDER_DETAILS_API = f"{BZP_BASE}/mp-readmodels/api/Search/GetTender"

STORAGE_DIR = Path(os.environ.get("TERRA_DOCUMENTS_DIR", "/var/lib/terra-os/documents"))
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per file
TIMEOUT = 60  # seconds


# ────────────────────────────────────────────────────────────────────
# Data structures
# ────────────────────────────────────────────────────────────────────

@dataclass
class TenderDocument:
    """Represents a single document from BZP."""
    object_id: str
    name: str
    filename: str
    url: str
    published_date: str | None = None
    state: str = "Published"
    file_size: int | None = None
    content_type: str | None = None
    local_path: str | None = None


@dataclass
class FetchResult:
    """Result of fetching documents for a tender."""
    tender_id: str
    bzp_number: str | None = None
    documents: list[TenderDocument] = field(default_factory=list)
    downloaded: int = 0
    errors: list[str] = field(default_factory=list)
    notice_pdf_path: str | None = None


# ────────────────────────────────────────────────────────────────────
# Core Scraper
# ────────────────────────────────────────────────────────────────────

class BZPDocumentScraper:
    """Scrapes SWZ documents from ezamowienia.gov.pl public API."""

    def __init__(self, storage_dir: Path | None = None, db_engine=None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._engine = db_engine
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": "Terra-OS/1.0 (Document Fetcher)",
                    "Accept": "application/json, application/octet-stream, */*",
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

    # ─── Public API ──────────────────────────────────────────────────

    def list_documents(self, tender_id: str) -> list[TenderDocument]:
        """List all published documents for a tender (by OCDS tenderId).

        Args:
            tender_id: OCDS tender identifier (e.g. "ocds-148610-xxx-yyy-zzz")

        Returns:
            List of TenderDocument objects
        """
        client = self._get_client()
        try:
            resp = client.get(DOCUMENTS_API, params={"tenderId": tender_id})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Failed to list documents for %s: %s", tender_id, exc)
            return []

        documents = []
        for item in data:
            if item.get("tenderDocumentState") != "Published":
                continue
            if item.get("deleteDate"):
                continue
            doc = TenderDocument(
                object_id=item["objectId"],
                name=item.get("name", ""),
                filename=item.get("fileName", "unknown"),
                url=item.get("url", ""),
                published_date=item.get("publishedDate"),
                state=item.get("tenderDocumentState", "Published"),
            )
            documents.append(doc)

        logger.info("Found %d published documents for tender %s", len(documents), tender_id)
        return documents

    def download_document(self, tender_id: str, doc: TenderDocument) -> Path | None:
        """Download a single document file.

        Args:
            tender_id: OCDS tender identifier
            doc: TenderDocument to download

        Returns:
            Path to downloaded file, or None on failure
        """
        client = self._get_client()
        download_url = f"{DOWNLOAD_API}/{tender_id}/{doc.object_id}"

        # Create tender-specific directory
        safe_tender_dir = re.sub(r'[^\w\-]', '_', tender_id)
        doc_dir = self.storage_dir / safe_tender_dir
        doc_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = re.sub(r'[/\\<>:"|?*]', '_', doc.filename)
        if not safe_filename:
            safe_filename = f"document_{doc.object_id.split('_')[-1]}"
        dest = doc_dir / safe_filename

        try:
            with client.stream("GET", download_url) as resp:
                resp.raise_for_status()

                # Get content info from headers
                doc.content_type = resp.headers.get("content-type", "application/octet-stream")
                content_length = resp.headers.get("content-length")

                if content_length and int(content_length) > MAX_FILE_SIZE:
                    logger.warning("File too large: %s (%s bytes)", doc.filename, content_length)
                    return None

                # Stream download
                total = 0
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        total += len(chunk)
                        if total > MAX_FILE_SIZE:
                            logger.warning("File exceeded max size during download: %s", doc.filename)
                            f.close()
                            dest.unlink(missing_ok=True)
                            return None
                        f.write(chunk)

                doc.file_size = total
                doc.local_path = str(dest)
                logger.debug("Downloaded %s (%d bytes) -> %s", doc.filename, total, dest)
                return dest

        except httpx.HTTPError as exc:
            logger.error("Failed to download %s: %s", doc.filename, exc)
            dest.unlink(missing_ok=True)
            return None

    def download_notice_pdf(self, bzp_number: str) -> Path | None:
        """Download the official notice PDF from BZP.

        Args:
            bzp_number: BZP notice number (e.g. "2026/BZP 00306437/01")
                        If no version suffix, "/01" is appended automatically.

        Returns:
            Path to downloaded PDF or None on failure
        """
        client = self._get_client()

        # Ensure version suffix
        if not re.search(r'/\d+$', bzp_number):
            bzp_number = f"{bzp_number}/01"

        encoded = quote(bzp_number, safe='')
        url = f"{NOTICE_PDF_API}?noticeNumber={encoded}"

        try:
            resp = client.get(url)
            resp.raise_for_status()

            # Save PDF
            safe_name = re.sub(r'[/\\<>:"|?*\s]', '_', bzp_number) + ".pdf"
            dest = self.storage_dir / "notices" / safe_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)

            logger.info("Downloaded notice PDF: %s (%d bytes)", bzp_number, len(resp.content))
            return dest

        except httpx.HTTPError as exc:
            logger.error("Failed to download notice PDF for %s: %s", bzp_number, exc)
            return None

    def fetch_all(
        self,
        tender_id: str,
        bzp_number: str | None = None,
        *,
        download_files: bool = True,
        include_notice_pdf: bool = True,
    ) -> FetchResult:
        """Fetch all documents for a tender: list + download + notice PDF.

        This is the main entry point for the scraper.

        Args:
            tender_id: OCDS tender identifier
            bzp_number: BZP notice number (optional, for notice PDF)
            download_files: Whether to download document files
            include_notice_pdf: Whether to download the official notice PDF

        Returns:
            FetchResult with all documents and download status
        """
        result = FetchResult(tender_id=tender_id, bzp_number=bzp_number)

        # 1. List documents
        documents = self.list_documents(tender_id)
        result.documents = documents

        if not documents:
            result.errors.append(f"No documents found for tender {tender_id}")
            logger.warning("No documents found for tender %s", tender_id)

        # 2. Download files
        if download_files:
            for doc in documents:
                path = self.download_document(tender_id, doc)
                if path:
                    result.downloaded += 1
                else:
                    result.errors.append(f"Failed to download: {doc.filename}")

        # 3. Notice PDF
        if include_notice_pdf and bzp_number:
            pdf_path = self.download_notice_pdf(bzp_number)
            if pdf_path:
                result.notice_pdf_path = str(pdf_path)
            else:
                result.errors.append(f"Failed to download notice PDF: {bzp_number}")

        # 4. Store in DB if engine available
        if self._engine:
            self._store_results(result)

        logger.info(
            "Fetch complete for %s: %d docs listed, %d downloaded, %d errors",
            tender_id, len(documents), result.downloaded, len(result.errors),
        )
        return result

    # ─── DB Storage ──────────────────────────────────────────────────

    def _store_results(self, result: FetchResult):
        """Store fetch results in bzp_documents table."""
        try:
            with self._engine.connect() as conn:
                # Get internal tender UUID from external tender_id (OCDS)
                row = conn.execute(
                    sa.text("SELECT id FROM tender WHERE url LIKE :pattern LIMIT 1"),
                    {"pattern": f"%{result.tender_id}%"},
                ).fetchone()

                internal_id = str(row.id) if row else None
                if not internal_id:
                    logger.warning("No internal tender found for OCDS ID %s", result.tender_id)
                    return

                for doc in result.documents:
                    conn.execute(
                        sa.text("""
                            INSERT INTO bzp_documents
                                (id, tender_id, bzp_notice_id, doc_type, filename, content, url, fetched_at)
                            VALUES (:id, :tid, :notice_id, :doc_type, :filename, :content, :url, now())
                            ON CONFLICT (tender_id, filename) DO UPDATE SET
                                url = EXCLUDED.url,
                                content = EXCLUDED.content,
                                fetched_at = now()
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "tid": internal_id,
                            "notice_id": result.bzp_number or "",
                            "doc_type": _classify_document(doc.filename),
                            "filename": doc.filename,
                            "content": f"[file:{doc.local_path}]" if doc.local_path else f"[url:{doc.url}]",
                            "url": f"{DOWNLOAD_API}/{result.tender_id}/{doc.object_id}",
                        },
                    )
                conn.commit()
                logger.info("Stored %d document records for tender %s", len(result.documents), internal_id)

        except Exception as exc:
            logger.error("Failed to store results in DB: %s", exc)


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _classify_document(filename: str) -> str:
    """Classify document type based on filename."""
    lower = filename.lower()
    if "swz" in lower or "siwz" in lower or "specyfikacja" in lower:
        return "SWZ"
    elif "formularz" in lower or "ofert" in lower:
        return "FORM"
    elif "umow" in lower or "postanowieni" in lower:
        return "CONTRACT"
    elif "oświadczen" in lower or "oswiadczen" in lower:
        return "DECLARATION"
    elif "wykaz" in lower:
        return "LIST"
    elif "dokumentacj" in lower or "projekt" in lower or "rysun" in lower:
        return "TECHNICAL"
    elif "zmian" in lower or "modyfikacj" in lower:
        return "AMENDMENT"
    else:
        return "OTHER"


def extract_tender_id_from_url(url: str) -> str | None:
    """Extract OCDS tender ID from ezamowienia.gov.pl URL.

    Examples:
        https://ezamowienia.gov.pl/mp-client/tenders/ocds-148610-xxx → ocds-148610-xxx
        https://ezamowienia.gov.pl/mp-client/search/list/ocds-148610-xxx → ocds-148610-xxx
    """
    m = re.search(r'(ocds-\d+-[a-f0-9\-]+)', url or "")
    return m.group(1) if m else None


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Terra-OS BZP Document Scraper")
    parser.add_argument("tender_id", help="OCDS tender ID (ocds-148610-...)")
    parser.add_argument("--bzp-number", help="BZP notice number for PDF download")
    parser.add_argument("--list-only", action="store_true", help="List documents without downloading")
    parser.add_argument("--output-dir", default="/var/lib/terra-os/documents", help="Download directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    scraper = BZPDocumentScraper(storage_dir=Path(args.output_dir))

    with scraper:
        if args.list_only:
            docs = scraper.list_documents(args.tender_id)
            if args.json:
                print(json.dumps([{"name": d.name, "filename": d.filename, "id": d.object_id, "published": d.published_date} for d in docs], indent=2, ensure_ascii=False))
            else:
                for i, d in enumerate(docs, 1):
                    print(f"  {i}. {d.filename} ({d.name})")
                print(f"\nTotal: {len(docs)} documents")
        else:
            result = scraper.fetch_all(
                args.tender_id,
                bzp_number=args.bzp_number,
                download_files=True,
                include_notice_pdf=bool(args.bzp_number),
            )
            if args.json:
                print(json.dumps({
                    "tender_id": result.tender_id,
                    "documents": len(result.documents),
                    "downloaded": result.downloaded,
                    "errors": result.errors,
                    "notice_pdf": result.notice_pdf_path,
                    "files": [{"name": d.filename, "type": _classify_document(d.filename), "size": d.file_size, "path": d.local_path} for d in result.documents],
                }, indent=2, ensure_ascii=False))
            else:
                print(f"Tender: {result.tender_id}")
                print(f"Documents: {len(result.documents)}")
                print(f"Downloaded: {result.downloaded}")
                if result.errors:
                    print(f"Errors: {len(result.errors)}")
                    for e in result.errors:
                        print(f"  ! {e}")
                print("\nFiles:")
                for d in result.documents:
                    status = "✓" if d.local_path else "✗"
                    size = f"({d.file_size//1024}KB)" if d.file_size else ""
                    print(f"  {status} [{_classify_document(d.filename):10}] {d.filename} {size}")
