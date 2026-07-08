"""BZP Documents API Router — Faza 3.

Endpoints:
  POST /api/v1/bzp/documents/{tender_id}/fetch   — trigger document scraping
  GET  /api/v1/bzp/documents/{tender_id}         — list fetched documents
  GET  /api/v1/bzp/documents/{tender_id}/download/{doc_id} — proxy download
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
import sqlalchemy as sa

from terra_db.session import get_engine
from ..auth.deps import AuthUser, TenantDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bzp/documents", tags=["bzp-documents"])

# Import scraper
from bzp_document_scraper import (
    BZPDocumentScraper,
    extract_tender_id_from_url,
    DOWNLOAD_API,
    _classify_document,
    BZP_BASE,
)


def _resolve_ocds_id(url: str | None, external_id: str | None) -> str | None:
    """Resolve OCDS tender ID from URL or by querying BZP API with bzpNumber."""
    import httpx

    # Try from URL first
    if url:
        ocds_id = extract_tender_id_from_url(url)
        if ocds_id:
            return ocds_id

        # Also try to extract tenderId directly from URL path if not ocds- format
        # e.g. https://ezamowienia.gov.pl/mp-client/tenders/some-uuid
        import re as _re
        m = _re.search(r'/tenders/([^/?#]+)', url)
        if m:
            candidate = m.group(1)
            if candidate and len(candidate) > 5:
                return candidate

    # Fallback: query BZP notice details by bzpNumber
    if external_id:
        try:
            resp = httpx.get(
                f"{BZP_BASE}/mp-readmodels/api/Tender/GetTenderNoticeDetails",
                params={"bzpNumber": external_id},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "tenderId" in data:
                    return data["tenderId"]
        except Exception:
            pass

        # Second fallback: search via the notice board API
        try:
            resp = httpx.get(
                f"{BZP_BASE}/mo-board/api/v1/notice/search",
                params={"bzpNumber": external_id, "pageSize": 1, "pageNumber": 0},
                headers={"Accept": "application/json"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("items", [])
                if items and isinstance(items, list) and items[0].get("tenderId"):
                    return items[0]["tenderId"]
        except Exception:
            pass

    return None


def _run_fetch(internal_tender_id: str, ocds_tender_id: str, bzp_number: str | None):
    """Background task: fetch all documents for a tender."""
    engine = get_engine()
    scraper = BZPDocumentScraper(
        storage_dir=Path("/var/lib/terra-os/documents"),
    )
    with scraper:
        # Only list, don't download files
        documents = scraper.list_documents(ocds_tender_id)

        # Store document metadata in DB
        import uuid
        with engine.connect() as conn:
            for doc in documents:
                conn.execute(
                    sa.text("""
                        INSERT INTO bzp_documents
                            (id, tender_id, bzp_notice_id, doc_type, filename, content, url, fetched_at)
                        VALUES (:id, :tid, :notice_id, :doc_type, :filename, :content, :url, now())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "tid": internal_tender_id,
                        "notice_id": bzp_number or "",
                        "doc_type": _classify_document(doc.filename),
                        "filename": doc.filename,
                        "content": doc.object_id,
                        "url": f"{DOWNLOAD_API}/{ocds_tender_id}/{doc.object_id}",
                    },
                )
            conn.commit()

    logger.info("BZP fetch complete: %d documents for %s", len(documents), ocds_tender_id)


@router.post("/{tender_id}/fetch")
def fetch_tender_documents(
    tender_id: str,
    background_tasks: BackgroundTasks,
    user: AuthUser,
    tenant_id: TenantDep,
) -> dict:
    """Pobierz listę dokumentów SWZ z BZP dla danego przetargu.
    
    Scraper łączy się z publicznym API ezamowienia.gov.pl (nie wymaga logowania)
    i pobiera listę wszystkich dokumentów postępowania.
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, url, source, external_id FROM tender WHERE id = :id AND tenant_id = :tid"),
            {"id": tender_id, "tid": tenant_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Przetarg nie istnieje")

    # Extract OCDS tender ID from URL or resolve via BZP API
    ocds_id = _resolve_ocds_id(row.url, row.external_id)
    if not ocds_id:
        source_info = f"source={row.source}, external_id={row.external_id or 'brak'}, url={row.url or 'brak'}"
        raise HTTPException(
            status_code=400,
            detail={
                "error": "cannot_resolve_ocds_id",
                "message": (
                    "Nie udało się ustalić OCDS ID przetargu. "
                    "Przetarg nie posiada linku do ezamowienia.gov.pl lub numer BZP jest nieznany. "
                    f"({source_info})"
                ),
                "hint": "Przetargi spoza BZP (TED, BIP, manual) nie mają dokumentów SWZ w ezamowienia.gov.pl",
            },
        )

    bzp_number = row.external_id

    background_tasks.add_task(_run_fetch, tender_id, ocds_id, bzp_number)
    return {
        "status": "queued",
        "tender_id": tender_id,
        "ocds_id": ocds_id,
        "bzp_number": bzp_number,
        "message": "Pobieranie dokumentów SWZ z ezamowienia.gov.pl w tle",
    }


@router.get("/{tender_id}")
def list_tender_documents(tender_id: str, user: AuthUser) -> dict:
    """Lista pobranych dokumentów SWZ dla przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, bzp_notice_id, doc_type, filename, url, fetched_at,
                       LENGTH(content) as content_length
                FROM bzp_documents
                WHERE tender_id = :tid
                ORDER BY fetched_at DESC
            """),
            {"tid": tender_id},
        ).fetchall()

    return {
        "tender_id": tender_id,
        "total": len(rows),
        "documents": [
            {
                "id": str(r.id),
                "notice_id": r.bzp_notice_id,
                "doc_type": r.doc_type,
                "filename": r.filename,
                "download_url": r.url,
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in rows
        ],
    }


@router.get("/{tender_id}/download/{doc_id}")
async def download_document(tender_id: str, doc_id: str, user: AuthUser):
    """Proxy download dokumentu z ezamowienia.gov.pl.
    
    Przekierowuje bezpośrednio do publicznego URL downloadu.
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT url, filename FROM bzp_documents WHERE id = :id AND tender_id = :tid"),
            {"id": doc_id, "tid": tender_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dokument nie istnieje")

    # Stream from BZP
    async def _stream():
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("GET", row.url) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(65536):
                    yield chunk

    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{row.filename}"',
        },
    )
