"""Chunk + embed — splits document text into chunks and computes embeddings."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from services.ai.clients import LLMClient

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512  # tokens (approximate by chars / 3.5)
CHUNK_OVERLAP = 64


@dataclass
class DocumentChunk:
    """A chunk of document text with embedding and provenance."""
    id: str
    doc_id: str
    content: str
    page: int
    position_in_doc: int
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "content": self.content,
            "page": self.page,
            "position_in_doc": self.position_in_doc,
            "embedding_dim": len(self.embedding),
        }


def chunk_and_embed(
    doc_id: str,
    pages: list[dict[str, Any]],
    *,
    llm: LLMClient,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Split pages into chunks, compute embeddings.

    pages: list of {"page_num": int, "text": str}
    """
    chunks: list[DocumentChunk] = []
    position = 0

    for page_info in pages:
        page_num = page_info.get("page_num", 1)
        text = page_info.get("text", "")
        if not text.strip():
            continue

        # Split into chunks (char-based approximation)
        char_chunk_size = chunk_size * 4  # ~4 chars per token
        char_overlap = overlap * 4

        start = 0
        while start < len(text):
            end = start + char_chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                embedding = llm.embed(chunk_text)
                chunks.append(DocumentChunk(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    content=chunk_text,
                    page=page_num,
                    position_in_doc=position,
                    embedding=embedding,
                ))
                position += 1

            start = end - char_overlap
            if start >= len(text):
                break

    logger.info("Created %d chunks for doc %s", len(chunks), doc_id)
    return chunks
