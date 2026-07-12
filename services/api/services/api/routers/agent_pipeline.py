"""LangGraph Agent Pipeline v1 + v2.

POST /api/v2/agent/analyze/{tender_id}   — v1: fetch → analyze → score
POST /api/v2/agent/decision/{tender_id}  — v2: + ahp → competitor → bid_strategy → brief
GET  /api/v2/agent/runs/{agent_run_id}
GET  /api/v2/agent/brief/{tender_id}
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2", tags=["agent-pipeline"])
logger = logging.getLogger(__name__)


def _run_pipeline_sse(tender_id: str, version: str = "v1"):
    """Run LangGraph pipeline and yield SSE events."""
    from services.agents.langgraph_pipeline import app_v1, app_v2

    engine = get_engine()
    run_id = str(uuid.uuid4())

    # Record agent_run start
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO agent_run (id, tenant_id, pipeline, status, input, started_at)
            VALUES (:id, (SELECT tenant_id FROM tender WHERE id=:tid), :pipe, 'running', :inp, NOW())
        """), {"id": run_id, "tid": tender_id, "pipe": version,
               "inp": json.dumps({"tender_id": tender_id})})

    yield f"data: {json.dumps({'type': 'start', 'agent_run_id': run_id})}\n\n"

    try:
        app = app_v2 if version == "v2" else app_v1
        initial_state = {"tender_id": tender_id, "steps": []}

        # Stream node executions
        result_state = {}
        for event in app.stream(initial_state):
            for node_name, node_output in event.items():
                result_state.update(node_output)
                step_data = {"type": "step", "step": node_name}
                if node_name == "score_tender" and "score" in node_output:
                    step_data["score"] = node_output["score"]
                if node_name == "generate_brief" and "go_decision" in node_output:
                    step_data["go_decision"] = node_output["go_decision"]
                yield f"data: {json.dumps(step_data)}\n\n"

        # Mark done
        with engine.begin() as conn:
            conn.execute(sa.text("""
                UPDATE agent_run SET status='done', output=:out, finished_at=NOW()
                WHERE id=:id
            """), {"id": run_id, "out": json.dumps(result_state, default=str)})

        yield f"data: {json.dumps({'type': 'done', 'agent_run_id': run_id, 'result': result_state})}\n\n"

    except Exception as e:
        logger.error(f"Pipeline {version} error: {e}")
        with engine.begin() as conn:
            conn.execute(sa.text("""
                UPDATE agent_run SET status='error', output=:out, finished_at=NOW()
                WHERE id=:id
            """), {"id": run_id, "out": json.dumps({"error": str(e)})})
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/agent/analyze/{tender_id}")
def agent_analyze(tender_id: str) -> StreamingResponse:
    """Run v1 pipeline: fetch → analyze → score. Returns SSE stream."""
    return StreamingResponse(
        _run_pipeline_sse(tender_id, "v1"),
        media_type="text/event-stream",
    )


@router.post("/agent/decision/{tender_id}")
def agent_decision(tender_id: str) -> StreamingResponse:
    """Run v2 full pipeline: + AHP → competitor → bid strategy → brief. SSE."""
    return StreamingResponse(
        _run_pipeline_sse(tender_id, "v2"),
        media_type="text/event-stream",
    )


@router.get("/agent/runs/{agent_run_id}")
def get_agent_run(agent_run_id: str) -> dict:
    """Get agent run result."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, pipeline, status, input, output, started_at, finished_at FROM agent_run WHERE id=:id"),
            {"id": agent_run_id},
        ).fetchone()

    if not row:
        return {"error": "not_found"}

    return {
        "id": str(row[0]),
        "pipeline": row[1],
        "status": row[2],
        "input": row[3],
        "output": row[4],
        "started_at": str(row[5]) if row[5] else None,
        "finished_at": str(row[6]) if row[6] else None,
    }


@router.get("/agent/brief/{tender_id}")
def get_brief(tender_id: str) -> dict:
    """Get latest decision brief for a tender."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("""
                SELECT id, output, finished_at FROM agent_run
                WHERE pipeline='v2' AND status='done'
                  AND input::jsonb->>'tender_id' = :tid
                ORDER BY finished_at DESC LIMIT 1
            """),
            {"tid": tender_id},
        ).fetchone()

    if not row:
        return {"tender_id": tender_id, "brief": None, "message": "No decision brief generated yet"}

    output = row[1] if isinstance(row[1], dict) else json.loads(row[1]) if row[1] else {}
    return {
        "tender_id": tender_id,
        "agent_run_id": str(row[0]),
        "brief": output.get("decision_brief"),
        "go_decision": output.get("go_decision"),
        "score": output.get("score"),
        "finished_at": str(row[2]) if row[2] else None,
    }
