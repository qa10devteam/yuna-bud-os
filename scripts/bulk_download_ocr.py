#!/usr/bin/env python3
"""
bulk_download_ocr.py — Pobranie ogłoszeń PDF z BZP, OCR, chunking, embedding.

Dla tenderów które mają external_id z BZP ale nie mają tender_document.
Batch po 50, z rate limiting (1 req/s do BZP).
"""
import sys, os, time, uuid, hashlib, logging
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os/services")

with open("/home/ubuntu/terra-os/.env") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)
os.environ.update({"DB_HOST": "127.0.0.1", "DB_NAME": "terraos", "DB_USER": "terraos"})

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bulk_dl")

import sqlalchemy as sa
from terra_db.session import get_engine
import httpx

STORAGE_DIR = Path("/var/lib/terra-os/documents")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "200"))
SLEEP_BETWEEN = 0.5  # seconds between BZP requests

# pdftext for fast OCR
try:
    from pdftext.extraction import plain_text_output
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    log.warning("pdftext not available — will skip OCR")

# sentence-transformers for embedding
try:
    from sentence_transformers import SentenceTransformer
    EMBED_MODEL = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    EMBED_AVAILABLE = True
except ImportError:
    EMBED_AVAILABLE = False
    log.warning("sentence-transformers not available — will skip embedding")


def extract_bzp_number(external_id: str) -> str | None:
    """Extract full BZP number like '2026/BZP 00345582' from external_id."""
    import re
    m = re.search(r"(\d{4}/BZP\s*\d{8})", external_id)
    return m.group(1) if m else None


def download_bzp_pdf(bzp_number: str, year: str = "2026") -> bytes | None:
    """Download BZP notice PDF using correct API endpoint."""
    from urllib.parse import quote
    
    # BZP number format: "2026/BZP 00345582" → try versions /01, /02
    base = bzp_number.strip()
    
    for version in range(1, 4):
        versioned = f"{base}/{version:02d}"
        url = f"https://ezamowienia.gov.pl/mo-board/api/v1/Board/GetNoticePdf?noticeNumber={quote(versioned, safe='')}"
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200 and len(resp.content) > 500:
                    ct = resp.headers.get("content-type", "")
                    if "pdf" in ct or resp.content[:4] == b"%PDF":
                        return resp.content
                elif resp.status_code == 404:
                    if version == 1:
                        continue
                    break
        except Exception as e:
            log.debug("Failed %s: %s", url, e)
    return None


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if len(c.strip()) > 50]


def main():
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get tenders needing documents
        rows = conn.execute(sa.text("""
            SELECT t.id, t.external_id, t.tenant_id
            FROM tender t
            WHERE t.external_id LIKE '%BZP%'
              AND t.id NOT IN (SELECT tender_id FROM tender_document)
            ORDER BY t.created_at DESC
            LIMIT :limit
        """), {"limit": BATCH_SIZE}).fetchall()
    
    log.info("Found %d tenders to process", len(rows))
    
    stats = {"downloaded": 0, "ocr_ok": 0, "chunks_created": 0, "embedded": 0, "failed": 0}
    
    for i, row in enumerate(rows):
        tender_id = str(row[0])
        external_id = row[1]
        tenant_id = str(row[2])
        
        bzp_num = extract_bzp_number(external_id)
        if not bzp_num:
            log.debug("Skip %s — no BZP number in '%s'", tender_id[:8], external_id)
            stats["failed"] += 1
            continue
        
        # Download PDF
        pdf_data = download_bzp_pdf(bzp_num)
        if not pdf_data:
            stats["failed"] += 1
            if (i + 1) % 50 == 0:
                log.info("Progress: %d/%d (dl=%d, ocr=%d, chunks=%d, fail=%d)",
                         i+1, len(rows), stats["downloaded"], stats["ocr_ok"],
                         stats["chunks_created"], stats["failed"])
            time.sleep(SLEEP_BETWEEN)
            continue
        
        stats["downloaded"] += 1
        
        # Save to disk
        doc_dir = STORAGE_DIR / tender_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        safe_bzp = bzp_num.replace("/", "_").replace(" ", "_")
        filename = f"ogloszenie_{safe_bzp}.pdf"
        pdf_path = doc_dir / filename
        pdf_path.write_bytes(pdf_data)
        
        # Insert tender_document
        doc_id = str(uuid.uuid4())
        with engine.begin() as conn:
            conn.execute(sa.text("""
                INSERT INTO tender_document (id, tenant_id, tender_id, kind, filename, local_path, mime, parsed_ok)
                VALUES (:id, :tenant_id, :tender_id, 'notice', :filename, :local_path, 'application/pdf', false)
                ON CONFLICT DO NOTHING
            """), {
                "id": doc_id, "tenant_id": tenant_id, "tender_id": tender_id,
                "filename": filename, "local_path": str(pdf_path),
            })
        
        # OCR
        if OCR_AVAILABLE:
            try:
                text = plain_text_output(str(pdf_path))
                if text and len(text.strip()) > 100:
                    stats["ocr_ok"] += 1
                    chunks = chunk_text(text)
                    
                    # Generate embeddings
                    embeddings = None
                    if EMBED_AVAILABLE and chunks:
                        embeddings = EMBED_MODEL.encode(chunks)
                    
                    # Insert chunks
                    with engine.begin() as conn:
                        for idx, chunk in enumerate(chunks):
                            chunk_id = str(uuid.uuid4())
                            emb_val = None
                            if embeddings is not None:
                                emb_val = "[" + ",".join(f"{x:.6f}" for x in embeddings[idx]) + "]"
                            # Use CAST instead of :: to avoid SQLAlchemy param confusion
                            conn.execute(sa.text(
                                "INSERT INTO document_chunk (id, tenant_id, document_id, page, ordinal, content, embedding) "
                                "VALUES (:id, :tid, :did, 1, :ord, :content, CAST(:emb AS vector))"
                            ), {
                                "id": chunk_id, "tid": tenant_id, "did": doc_id,
                                "ord": idx, "content": chunk, "emb": emb_val,
                            })
                            stats["chunks_created"] += 1
                            if embeddings is not None:
                                stats["embedded"] += 1
                        
                        # Mark parsed
                        conn.execute(sa.text(
                            "UPDATE tender_document SET parsed_ok=true, pages=:p WHERE id=:id"
                        ), {"p": len(chunks), "id": doc_id})
            except Exception as e:
                log.warning("OCR failed for %s: %s", filename, e)
        
        time.sleep(SLEEP_BETWEEN)
        
        if (i + 1) % 20 == 0:
            log.info("Progress: %d/%d — dl=%d ocr=%d chunks=%d emb=%d fail=%d",
                     i+1, len(rows), stats["downloaded"], stats["ocr_ok"],
                     stats["chunks_created"], stats["embedded"], stats["failed"])
    
    log.info("DONE: %s", stats)
    
    # Refresh materialized views
    with engine.begin() as conn:
        for mv in ["mv_dashboard_stats", "mv_pipeline_kpi", "mv_scoring"]:
            try:
                conn.execute(sa.text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
                log.info("Refreshed %s", mv)
            except Exception:
                try:
                    conn.execute(sa.text(f"REFRESH MATERIALIZED VIEW {mv}"))
                except Exception as e:
                    log.warning("Failed to refresh %s: %s", mv, e)


if __name__ == "__main__":
    main()
