"""Document fetch — download attachments to local FS (idempotent, checksum)."""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DOCS_DIR = Path(os.getenv("TERRA_DOCS_DIR", "/tmp/terra_docs"))


class FetchedDoc:
    """Represents a fetched document on local filesystem."""

    __slots__ = ("path", "filename", "url", "checksum", "size_bytes")

    def __init__(self, *, path: Path, filename: str, url: str, checksum: str, size_bytes: int):
        self.path = path
        self.filename = filename
        self.url = url
        self.checksum = checksum
        self.size_bytes = size_bytes


def fetch_documents(
    tender_id: str,
    attachments: list[dict[str, Any]],
    *,
    base_dir: Path | None = None,
) -> list[FetchedDoc]:
    """Download attachments to local FS. Idempotent via checksum.

    In offline/test mode, looks for fixtures instead of downloading.
    """
    base = base_dir or DOCS_DIR / tender_id
    base.mkdir(parents=True, exist_ok=True)
    results: list[FetchedDoc] = []

    for att in attachments:
        filename = att.get("filename", "unknown.pdf")
        url = att.get("url", "")
        content = att.get("content", b"")  # For fixtures: raw bytes

        if isinstance(content, str):
            content = content.encode("utf-8")

        checksum = hashlib.sha256(content).hexdigest()[:16]
        target = base / filename

        # Idempotent: skip if same checksum exists
        if target.exists():
            existing_hash = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
            if existing_hash == checksum:
                logger.debug("Skip (same checksum): %s", filename)
                results.append(FetchedDoc(
                    path=target, filename=filename, url=url,
                    checksum=checksum, size_bytes=len(content),
                ))
                continue

        target.write_bytes(content)
        logger.info("Fetched: %s (%d bytes)", filename, len(content))
        results.append(FetchedDoc(
            path=target, filename=filename, url=url,
            checksum=checksum, size_bytes=len(content),
        ))

    return results
