"""Semantic search + RAG endpoints.

POST /api/v2/tenders/semantic-search
POST /api/v2/rag/query
POST /api/v2/rag/chat/{tender_id}
POST /api/v2/rag/embed-document/{tender_id}
POST /api/v2/embeddings/run-batch
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import sqlalchemy as sa

from terra_db.session import get_engine
from services.ai.embedder import embed_text, embed_tenders_batch
from services.ai.rag import rag_query, rag_generate, embed_document_chunks
from services.ai.vllm_client import get_llm_client

router = APIRouter(prefix="/api/v2", tags=["semantic-search", "rag"])


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 20
    tenant_id: str


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class EmbedDocRequest(BaseModel):
    text: str
    source_id: str | None = None
    source_type: str = "manual"


# ─── Semantic Search ──────────────────────────────────────────────────────────

@router.post("/tenders/semantic-search")
def semantic_search(body: SemanticSearchRequest) -> list[dict[str, Any]]:
    """Vector similarity search over tenders."""
    query_emb = embed_text(body.query)
    emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, title, buyer, cpv, value_pln, match_score,
                       1 - (embedding <=> :emb::vector) as similarity
                FROM tender
                WHERE tenant_id = :tid AND embedding IS NOT NULL
                ORDER BY embedding <=> :emb::vector
                LIMIT :lim
            """),
            {"emb": emb_str, "tid": body.tenant_id, "lim": body.limit},
        ).fetchall()

    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "buyer": r[2],
            "cpv": r[3],
            "value_pln": float(r[4]) if r[4] else None,
            "match_score": float(r[5]) if r[5] else None,
            "similarity": round(float(r[6]), 4),
        }
        for r in rows
    ]


# ─── RAG ──────────────────────────────────────────────────────────────────────

@router.post("/rag/query")
def rag_query_endpoint(tender_id: str, body: RAGQueryRequest) -> list[dict]:
    """Return top-k similar document chunks for a query."""
    engine = get_engine()
    return rag_query(engine, body.query, tender_id, body.top_k)


@router.post("/rag/chat/{tender_id}")
def rag_chat(tender_id: str, body: RAGQueryRequest) -> StreamingResponse:
    """RAG-powered chat: retrieve + generate with SSE streaming."""
    engine = get_engine()
    llm = get_llm_client()

    def stream():
        for token in rag_generate(engine, body.query, tender_id, llm):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/rag/embed-document/{tender_id}")
def embed_document(tender_id: str, body: EmbedDocRequest) -> dict:
    """Chunk and embed a document for a tender."""
    engine = get_engine()
    count = embed_document_chunks(
        engine, tender_id, body.text, body.source_id, body.source_type
    )
    return {"chunks_created": count, "tender_id": tender_id}


# ─── Batch Embedding ──────────────────────────────────────────────────────────

@router.post("/embeddings/run-batch")
def run_batch_embedding(tenant_id: str | None = None, limit: int = 500) -> dict:
    """Embed tenders without embeddings."""
    engine = get_engine()
    count = embed_tenders_batch(engine, tenant_id, limit)
    return {"embedded_count": count}
