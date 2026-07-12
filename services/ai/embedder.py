"""Embedder — sentence-transformers (multilingual-MiniLM-L12-v2, dim=384).

Provides:
  embed_text(text) -> list[float]
  embed_texts_batch(texts) -> list[list[float]]
  embed_tenders_batch(engine, tenant_id=None) -> int  (count embedded)
"""
from __future__ import annotations

import logging
from typing import Optional

import sqlalchemy as sa

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("Loaded embedding model: paraphrase-multilingual-MiniLM-L12-v2 (dim=384)")
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string, returns 384-dim vector."""
    model = _get_model()
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()


def embed_texts_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Embed multiple texts efficiently."""
    model = _get_model()
    embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
    return embeddings.tolist()


def embed_tenders_batch(engine, tenant_id: Optional[str] = None, limit: int = 500) -> int:
    """Embed tenders that don't have embeddings yet. Returns count of embedded."""
    where_clause = "WHERE embedding IS NULL"
    params: dict = {}
    if tenant_id:
        where_clause += " AND tenant_id = :tid"
        params["tid"] = tenant_id

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f"SELECT id, title, buyer, cpv FROM tender {where_clause} LIMIT :lim"),
            {**params, "lim": limit},
        ).fetchall()

    if not rows:
        return 0

    texts = []
    ids = []
    for row in rows:
        text = f"{row[1] or ''} | {row[2] or ''} | {' '.join(row[3] or [])}"
        texts.append(text)
        ids.append(str(row[0]))

    embeddings = embed_texts_batch(texts)

    with engine.begin() as conn:
        for i, (tid, emb) in enumerate(zip(ids, embeddings)):
            emb_str = "[" + ",".join(str(x) for x in emb) + "]"
            conn.execute(
                sa.text("UPDATE tender SET embedding = :emb::vector WHERE id = :id"),
                {"emb": emb_str, "id": tid},
            )

    logger.info(f"Embedded {len(ids)} tenders")
    return len(ids)
