"""RAG engine — chunking + retrieval + generation over SWZ documents.

Provides:
  chunk_document(text, chunk_size=512, overlap=64) -> list[str]
  embed_document_chunks(engine, tender_id, text, source_id=None) -> int
  rag_query(engine, query, tender_id, top_k=5) -> list[dict]
  rag_generate(engine, query, tender_id, llm_client) -> Generator[str]
"""
from __future__ import annotations

import logging
import uuid
from typing import Generator, Optional

import sqlalchemy as sa

from services.ai.embedder import embed_text, embed_texts_batch

logger = logging.getLogger(__name__)


def chunk_document(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def embed_document_chunks(
    engine,
    tender_id: str,
    text: str,
    source_id: Optional[str] = None,
    source_type: str = "bzp_document",
) -> int:
    """Chunk a document, embed chunks, store in doc_chunks table."""
    chunks = chunk_document(text)
    if not chunks:
        return 0

    embeddings = embed_texts_batch(chunks)

    with engine.begin() as conn:
        # Remove old chunks for this source
        if source_id:
            conn.execute(
                sa.text("DELETE FROM doc_chunks WHERE source_id = :sid"),
                {"sid": source_id},
            )

        for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            emb_str = "[" + ",".join(str(x) for x in emb) + "]"
            conn.execute(
                sa.text("""
                    INSERT INTO doc_chunks (id, tender_id, source_type, source_id, chunk_idx, text, embedding)
                    VALUES (:id, :tid, :stype, :sid, :idx, :text, :emb::vector)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tid": tender_id,
                    "stype": source_type,
                    "sid": source_id,
                    "idx": idx,
                    "text": chunk_text,
                    "emb": emb_str,
                },
            )

    logger.info(f"Stored {len(chunks)} chunks for tender {tender_id}")
    return len(chunks)


def rag_query(engine, query: str, tender_id: str, top_k: int = 5) -> list[dict]:
    """Retrieve top-k most similar chunks for a query + tender."""
    query_emb = embed_text(query)
    emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, chunk_idx, text,
                       1 - (embedding <=> :emb::vector) as similarity
                FROM doc_chunks
                WHERE tender_id = :tid AND embedding IS NOT NULL
                ORDER BY embedding <=> :emb::vector
                LIMIT :topk
            """),
            {"emb": emb_str, "tid": tender_id, "topk": top_k},
        ).fetchall()

    return [
        {"id": str(r[0]), "chunk_idx": r[1], "text": r[2], "similarity": float(r[3])}
        for r in rows
    ]


def rag_generate(
    engine, query: str, tender_id: str, llm_client, top_k: int = 5
) -> Generator[str, None, None]:
    """RAG: retrieve context chunks then stream LLM answer."""
    chunks = rag_query(engine, query, tender_id, top_k)

    if not chunks:
        yield "Brak dokumentów w bazie dla tego przetargu. Prześlij SWZ aby umożliwić analizę RAG."
        return

    context = "\n---\n".join(c["text"] for c in chunks)
    prompt = (
        f"Na podstawie poniższych fragmentów dokumentacji przetargowej odpowiedz na pytanie.\n\n"
        f"KONTEKST:\n{context}\n\n"
        f"PYTANIE: {query}\n\n"
        f"Odpowiedz precyzyjnie, cytując fragmenty dokumentu gdzie to możliwe."
    )

    for token in llm_client.generate_stream(prompt):
        yield token
