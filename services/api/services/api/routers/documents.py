"""M2 — /tenders/{id}/analyze, /analysis endpoints."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from services.ai.clients import StubClient
from services.documents.ocr import extract_text, _fixture_extract
from services.documents.parse_przedmiar import parse_przedmiar
from services.documents.classify import classify_document
from services.documents.chunk import chunk_and_embed
from services.documents.analysis import analyze_tender

router = APIRouter(prefix="/api/v1", tags=["documents"])


# ──────────────────────────────────────────────────────────────── #
# Schemas
# ──────────────────────────────────────────────────────────────── #

class AnalyzeResponse(BaseModel):
    agent_run_id: str
    status: str
    przedmiar_items_count: int
    red_flags_count: int
    chunks_count: int


class RedFlagSchema(BaseModel):
    severity: str
    category: str
    message: str
    provenance: dict
    confidence: float


class AnalysisResponse(BaseModel):
    summary_md: str
    red_flags: list[RedFlagSchema]
    key_facts: dict
    przedmiar_items: list[dict]


# ──────────────────────────────────────────────────────────────── #
# POST /tenders/{id}/analyze
# ──────────────────────────────────────────────────────────────── #

@router.post("/tenders/{tender_id}/analyze", response_model=AnalyzeResponse)
def analyze_tender_endpoint(tender_id: str) -> AnalyzeResponse:
    """Fetch docs + OCR + parse przedmiar + RAG analysis + red flags.

    In offline mode (M2 CI): uses fixture documents + StubClient.
    """
    import sqlalchemy as sa
    engine = get_engine()

    # Verify tender exists
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, title FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Run document pipeline
    llm = StubClient()
    run_id = str(uuid.uuid4())

    # Step 1: Extract text (fixture in M2)
    from pathlib import Path
    extracted = _fixture_extract(Path("/dev/null"))

    # Step 2: Parse przedmiar
    full_text = extracted.full_text
    items = parse_przedmiar(full_text, llm=llm)

    # Step 3: Chunk + embed
    pages_data = [{"page_num": p.page_num, "text": p.text} for p in extracted.pages]
    chunks = chunk_and_embed(f"doc-{tender_id[:8]}", pages_data, llm=llm)

    # Step 4: Analysis (summary + red flags)
    result = analyze_tender(
        full_text,
        doc_id=f"doc-{tender_id[:8]}",
        llm=llm,
        przedmiar_items=[it.to_dict() for it in items],
    )

    # Step 5: Store in DB
    _store_analysis(engine, tender_id, result, items, chunks, run_id)

    return AnalyzeResponse(
        agent_run_id=run_id,
        status="completed",
        przedmiar_items_count=len(items),
        red_flags_count=len(result.red_flags),
        chunks_count=len(chunks),
    )


# ──────────────────────────────────────────────────────────────── #
# GET /tenders/{id}/analysis
# ──────────────────────────────────────────────────────────────── #

@router.get("/tenders/{tender_id}/analysis", response_model=AnalysisResponse)
def get_analysis(tender_id: str) -> AnalysisResponse:
    """Get stored analysis for a tender."""
    import sqlalchemy as sa
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT summary_md, red_flags, key_facts, przedmiar_items "
                "FROM analysis WHERE tender_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tender_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found. Run POST /analyze first.")

    return AnalysisResponse(
        summary_md=row[0] or "",
        red_flags=row[1] or [],
        key_facts=row[2] or {},
        przedmiar_items=row[3] or [],
    )


# ──────────────────────────────────────────────────────────────── #
# Internal: store analysis
# ──────────────────────────────────────────────────────────────── #

def _store_analysis(engine, tender_id, analysis, items, chunks, run_id):
    """Store analysis result in DB."""
    import sqlalchemy as sa
    import json

    with engine.begin() as conn:
        # Upsert analysis
        conn.execute(
            sa.text(
                "INSERT INTO analysis (id, tender_id, summary_md, red_flags, key_facts, "
                "przedmiar_items, agent_run_id, created_at) "
                "VALUES (:id, :tid, :summary, cast(:flags as jsonb), "
                "cast(:facts as jsonb), cast(:items as jsonb), :run_id, now()) "
                "ON CONFLICT (tender_id) DO UPDATE SET "
                "summary_md = EXCLUDED.summary_md, red_flags = EXCLUDED.red_flags, "
                "key_facts = EXCLUDED.key_facts, przedmiar_items = EXCLUDED.przedmiar_items, "
                "agent_run_id = EXCLUDED.agent_run_id, created_at = now()"
            ),
            {
                "id": str(uuid.uuid4()),
                "tid": tender_id,
                "summary": analysis.summary_md,
                "flags": json.dumps([rf.to_dict() for rf in analysis.red_flags], ensure_ascii=False),
                "facts": json.dumps(analysis.key_facts, ensure_ascii=False),
                "items": json.dumps(analysis.przedmiar_items, ensure_ascii=False),
                "run_id": run_id,
            },
        )
