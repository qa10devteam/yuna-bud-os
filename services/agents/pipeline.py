"""M9 — LangGraph supervisor pipeline: M1 → M2 → M3.

Nodes:
  ingest      → POST /api/v1/ingest/run
  analyze     → POST /api/v1/tenders/{id}/analyze
  engine_run  → POST /api/v1/tenders/{id}/engine/run
  estimate    → POST /api/v1/tenders/{id}/estimate
  decide      → logic: feasible + margin_headroom_pct >= threshold → go
  contract    → POST /api/v1/contracts
  optimize    → POST /api/v1/logistics/optimize
  plan        → POST /api/v1/plans
  dispatch    → POST /api/v1/plans/{id}/dispatch (gated → approval_id)
  done        → terminal

All calls are HTTP against a running FastAPI app (TestClient offline).
In offline mode (TERRA_OFFLINE=1) uses ASGI transport directly.

Every step writes an agent_run row; errors route to an error terminal node.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

_OFFLINE = os.environ.get("TERRA_OFFLINE", "0") == "1"


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline state
# ──────────────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    tenant_id: str
    tender_id: str
    analysis_id: str
    engine_result: dict
    estimate_doc_id: str
    estimate_owner_id: str
    compare_result: dict
    go_decision: bool
    contract_id: str
    optimize_result: dict
    plan_id: str
    approval_id: str
    error: str
    steps: list[str]
    agent_run_id: str


# ──────────────────────────────────────────────────────────────────────────────
# HTTP client factory (ASGI offline or real HTTP)
# ──────────────────────────────────────────────────────────────────────────────

def _get_client():
    """Return an httpx sync client. Offline: ASGI transport. Online: real HTTP."""
    import httpx
    if _OFFLINE:
        from services.api.main import app as _app
        from httpx import ASGITransport
        return httpx.Client(transport=ASGITransport(app=_app), base_url="http://test")
    base = os.environ.get("TERRA_API_URL", "http://localhost:8000")
    return httpx.Client(base_url=base, timeout=30.0)


# ──────────────────────────────────────────────────────────────────────────────
# Node implementations
# ──────────────────────────────────────────────────────────────────────────────

def node_ingest(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("ingest")
    try:
        with _get_client() as c:
            r = c.post("/api/v1/ingest/run?offline=true")
            r.raise_for_status()
            tenders_r = c.get("/api/v1/tenders")
            tenders = tenders_r.json().get("items", [])
        if not tenders:
            return {**state, "steps": steps, "error": "ingest: no tenders found"}
        tender_id = tenders[0]["id"]
        logger.info("ingest done, tender_id=%s", tender_id)
        return {**state, "steps": steps, "tender_id": tender_id}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"ingest: {exc}"}


def node_analyze(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("analyze")
    tid = state.get("tender_id")
    if not tid:
        return {**state, "steps": steps, "error": "analyze: no tender_id"}
    try:
        with _get_client() as c:
            r = c.post(f"/api/v1/tenders/{tid}/analyze")
            r.raise_for_status()
            data = r.json()
        return {**state, "steps": steps, "analysis_id": data.get("id", "")}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"analyze: {exc}"}


def node_engine_run(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("engine_run")
    tid = state.get("tender_id")
    try:
        with _get_client() as c:
            r = c.post(f"/api/v1/tenders/{tid}/engine/run")
            r.raise_for_status()
        return {**state, "steps": steps, "engine_result": r.json()}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"engine_run: {exc}"}


def node_estimate(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("estimate")
    tid = state.get("tender_id")
    try:
        with _get_client() as c:
            r = c.post(f"/api/v1/tenders/{tid}/estimate")
            r.raise_for_status()
            pair = r.json()
            cmp_r = c.get(f"/api/v1/tenders/{tid}/estimate/compare")
            cmp_r.raise_for_status()
        return {
            **state, "steps": steps,
            "estimate_doc_id": pair.get("estimate_doc_id", ""),
            "estimate_owner_id": pair.get("estimate_owner_id", ""),
            "compare_result": cmp_r.json(),
        }
    except Exception as exc:
        return {**state, "steps": steps, "error": f"estimate: {exc}"}


def node_decide(state: PipelineState) -> PipelineState:
    """Go/No-go decision: engine feasible AND margin_headroom_pct >= 0."""
    steps = list(state.get("steps", []))
    steps.append("decide")
    engine = state.get("engine_result", {})
    compare = state.get("compare_result", {})
    feasible = engine.get("feasible", False)
    margin = float(compare.get("margin_headroom_pct", -1))
    go = feasible and margin >= 0
    logger.info("decide: feasible=%s margin=%.2f go=%s", feasible, margin, go)
    return {**state, "steps": steps, "go_decision": go}


def node_contract(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("contract")
    tid = state.get("tender_id")
    try:
        with _get_client() as c:
            # Fetch tender title for contract name
            t_r = c.get(f"/api/v1/tenders/{tid}")
            title = t_r.json().get("title", "Kontrakt") if t_r.status_code == 200 else "Kontrakt"
            r = c.post("/api/v1/contracts", json={
                "title": title,
                "tender_id": tid,
                "required_skills": [],
                "required_equipment": [],
            })
            r.raise_for_status()
        return {**state, "steps": steps, "contract_id": r.json().get("id", "")}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"contract: {exc}"}


def node_optimize(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("optimize")
    try:
        with _get_client() as c:
            r = c.post("/api/v1/logistics/optimize", json={
                "day_range": ["2026-07-01", "2026-07-07"],
            })
            r.raise_for_status()
        return {**state, "steps": steps, "optimize_result": r.json()}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"optimize: {exc}"}


def node_plan(state: PipelineState) -> PipelineState:
    steps = list(state.get("steps", []))
    steps.append("plan")
    contract_id = state.get("contract_id")
    try:
        with _get_client() as c:
            r = c.post("/api/v1/plans", json={
                "contract_id": contract_id,
                "day": "2026-07-01",
                "cautions_md": "Plan wygenerowany przez pipeline Terra.OS.",
            })
            r.raise_for_status()
        return {**state, "steps": steps, "plan_id": r.json().get("id", "")}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"plan: {exc}"}


def node_dispatch(state: PipelineState) -> PipelineState:
    """Gated dispatch — returns approval_id, does NOT send."""
    steps = list(state.get("steps", []))
    steps.append("dispatch")
    plan_id = state.get("plan_id")
    try:
        with _get_client() as c:
            r = c.post(f"/api/v1/plans/{plan_id}/dispatch")
            r.raise_for_status()
        return {**state, "steps": steps, "approval_id": r.json().get("approval_id", "")}
    except Exception as exc:
        return {**state, "steps": steps, "error": f"dispatch: {exc}"}


def node_error(state: PipelineState) -> PipelineState:
    err = state.get("error", "unknown error")
    logger.error("Pipeline error: %s", err)
    steps = list(state.get("steps", []))
    steps.append(f"ERROR:{err}")
    return {**state, "steps": steps}


# ──────────────────────────────────────────────────────────────────────────────
# Routing
# ──────────────────────────────────────────────────────────────────────────────

def _route_after_error_check(state: PipelineState, next_node: str) -> str:
    return "error" if state.get("error") else next_node


def _route_decide(state: PipelineState) -> str:
    if state.get("error"):
        return "error"
    return "contract" if state.get("go_decision") else END


# ──────────────────────────────────────────────────────────────────────────────
# Build graph
# ──────────────────────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    g = StateGraph(PipelineState)

    g.add_node("ingest", node_ingest)
    g.add_node("analyze", node_analyze)
    g.add_node("engine_run", node_engine_run)
    g.add_node("estimate", node_estimate)
    g.add_node("decide", node_decide)
    g.add_node("contract", node_contract)
    g.add_node("optimize", node_optimize)
    g.add_node("plan", node_plan)
    g.add_node("dispatch", node_dispatch)
    g.add_node("error", node_error)

    g.set_entry_point("ingest")

    # Linear with error checks
    for src, dst in [
        ("ingest", "analyze"),
        ("analyze", "engine_run"),
        ("engine_run", "estimate"),
    ]:
        g.add_conditional_edges(
            src,
            lambda s, n=dst: _route_after_error_check(s, n),
            {n: n for n in [dst, "error"]},
        )

    g.add_conditional_edges("estimate", lambda s: _route_after_error_check(s, "decide"),
                            {"decide": "decide", "error": "error"})
    g.add_conditional_edges("decide", _route_decide,
                            {"contract": "contract", END: END, "error": "error"})
    g.add_conditional_edges("contract", lambda s: _route_after_error_check(s, "optimize"),
                            {"optimize": "optimize", "error": "error"})
    g.add_conditional_edges("optimize", lambda s: _route_after_error_check(s, "plan"),
                            {"plan": "plan", "error": "error"})
    g.add_conditional_edges("plan", lambda s: _route_after_error_check(s, "dispatch"),
                            {"dispatch": "dispatch", "error": "error"})
    g.add_edge("dispatch", END)
    g.add_edge("error", END)

    return g


def run_pipeline(initial_state: PipelineState | None = None) -> PipelineState:
    """Run the full Terra.OS pipeline. Returns final state."""
    graph = build_pipeline().compile()
    state = initial_state or PipelineState(steps=[])
    result = graph.invoke(state)
    return result
