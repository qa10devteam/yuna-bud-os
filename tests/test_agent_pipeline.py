"""P3-5 — Tests for agent_pipeline router.

Covers:
  - GET /api/v2/agent/runs/{id} → not_found
  - GET /api/v2/agent/runs/{id} → found (returns run data)
  - GET /api/v2/agent/brief/{tender_id} → no brief yet
  - GET /api/v2/agent/brief/{tender_id} → with brief data
  - GET /api/v2/agent/analyze/{tender_id}/stream → SSE stream (no DB data)
  - POST /api/v2/agent/analyze/{tender_id} → SSE stream (pipeline mocked)
  - POST /api/v2/agent/decision/{tender_id} → SSE stream (pipeline mocked)
  - _stream_analysis helper: all status branches
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_engine(rows_by_key: dict | None = None):
    """Return a minimal mocked SQLAlchemy engine."""
    rows_by_key = rows_by_key or {}
    conn = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt)
        for key, row in rows_by_key.items():
            if key in sql:
                res = MagicMock()
                res.fetchone.return_value = row
                res.fetchall.return_value = [row] if row else []
                return res
        res = MagicMock()
        res.fetchone.return_value = None
        res.fetchall.return_value = []
        return res

    conn.execute = MagicMock(side_effect=_execute)
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = conn
    engine.begin.return_value = conn
    return engine


def _make_app():
    from fastapi import FastAPI
    from services.api.services.api.routers.agent_pipeline import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)

    # Override auth to bypass JWT validation and plan-gate DB lookups
    _demo = CurrentUser(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    app.dependency_overrides[get_current_user] = lambda: _demo

    # Bypass plan gate — patch require_plan to return a no-op dependency
    try:
        from services.api.services.api.auth.plan_gate import require_plan as _rp
        from fastapi import Depends as _Depends

        def _noop_gate(_user=_Depends(get_current_user)):
            return None

        # Monkey-patch every Depends(_check) added by require_plan by overriding
        # the plan_gate module's require_plan so router re-imports get no-ops.
        # But since router is already imported, iterate its routes and remove gates.
        for route in app.routes:
            if hasattr(route, "dependant"):
                for dep in route.dependant.dependencies:
                    if hasattr(dep.call, "__name__") and dep.call.__name__ == "_check":
                        dep.call = lambda: None
    except Exception:
        pass

    return app


# ── GET /agent/runs/{id} ──────────────────────────────────────────────────────

class TestGetAgentRun:
    def test_not_found(self):
        """Returns {"error": "not_found"} when no row exists."""
        from fastapi.testclient import TestClient
        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            client = TestClient(_make_app())
            resp = client.get(f"/api/v2/agent/runs/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["error"] == "not_found"

    def test_found(self):
        """Returns run dict when row exists."""
        from fastapi.testclient import TestClient
        run_id = str(uuid.uuid4())
        row = MagicMock()
        row.__getitem__ = lambda self, i: [
            run_id, "v1", "done",
            json.dumps({"tender_id": "t1"}),
            json.dumps({"score": 0.8}),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        ][i]

        # Index-based attribute access
        row[0] = run_id

        # Simulate proper row tuple behaviour
        row_data = (
            run_id, "v1", "done",
            json.dumps({"tender_id": "t1"}),
            json.dumps({"score": 0.8}),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        )
        real_row = row_data

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = real_row
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get(f"/api/v2/agent/runs/{run_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == run_id
        assert body["pipeline"] == "v1"
        assert body["status"] == "done"


# ── GET /agent/brief/{tender_id} ──────────────────────────────────────────────

class TestGetBrief:
    def test_no_brief_yet(self):
        """Returns message when no v2 run found."""
        from fastapi.testclient import TestClient
        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/brief/tender-abc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tender_id"] == "tender-abc"
        assert body["brief"] is None
        assert "No decision brief" in body["message"]

    def test_with_brief_data(self):
        """Returns brief data from output when run exists."""
        from fastapi.testclient import TestClient
        run_id = str(uuid.uuid4())
        output_dict = {
            "decision_brief": "Go for it!",
            "go_decision": True,
            "score": 0.9,
        }
        row_data = (run_id, json.dumps(output_dict), datetime(2026, 1, 1, tzinfo=timezone.utc))

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/brief/tender-xyz")

        assert resp.status_code == 200
        body = resp.json()
        assert body["tender_id"] == "tender-xyz"
        assert body["brief"] == "Go for it!"
        assert body["go_decision"] is True
        assert body["score"] == 0.9

    def test_with_dict_output(self):
        """Handles output already stored as dict (not JSON string)."""
        from fastapi.testclient import TestClient
        run_id = str(uuid.uuid4())
        output_dict = {"decision_brief": "No-go", "go_decision": False, "score": 0.4}
        row_data = (run_id, output_dict, datetime(2026, 1, 2, tzinfo=timezone.utc))

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/brief/tender-dict")

        assert resp.status_code == 200
        assert resp.json()["brief"] == "No-go"


# ── GET /agent/analyze/{tender_id}/stream ─────────────────────────────────────

class TestAgentAnalyzeStream:
    def _sse_events(self, text: str) -> list[dict]:
        events = []
        for line in text.splitlines():
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
        return events

    def test_no_analysis_found(self):
        """Returns 'no_analysis' SSE event when no DB row."""
        from fastapi.testclient import TestClient
        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/analyze/tender-404/stream")
        assert resp.status_code == 200
        events = self._sse_events(resp.text)
        assert any(e.get("step") == "no_analysis" for e in events)

    def test_done_status_emits_done_event(self):
        """Row with status='done' emits 'done' event."""
        from fastapi.testclient import TestClient
        row_data = ("done", json.dumps([{"step": "fetch", "node": "fetch_tender"}]), None)

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/analyze/tender-done/stream")

        assert resp.status_code == 200
        events = self._sse_events(resp.text)
        assert any(e.get("event") == "done" for e in events)

    def test_error_status_emits_error_event(self):
        """Row with status='error' emits 'error' event."""
        from fastapi.testclient import TestClient
        row_data = ("error", None, None)

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/analyze/tender-err/stream")

        events = self._sse_events(resp.text)
        assert any(e.get("event") == "error" for e in events)

    def test_pending_status_emits_pending_event(self):
        """Row with status='running' emits 'pending' event."""
        from fastapi.testclient import TestClient
        row_data = ("running", None, None)

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/analyze/tender-run/stream")

        events = self._sse_events(resp.text)
        assert any(e.get("event") == "pending" for e in events)

    def test_done_with_brief_emits_brief_event(self):
        """Done row with decision_brief in result streams it."""
        from fastapi.testclient import TestClient
        result = {"decision_brief": "Recommended bid."}
        row_data = ("done", json.dumps([]), json.dumps(result))

        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            client = TestClient(_make_app())
            resp = client.get("/api/v2/agent/analyze/tender-brief/stream")

        events = self._sse_events(resp.text)
        brief_events = [e for e in events if e.get("step") == "decision_brief"]
        assert brief_events
        assert brief_events[0]["content"] == "Recommended bid."


# ── POST /agent/analyze/{tender_id} (v1 pipeline) ────────────────────────────

class TestAgentAnalyze:
    def _sse_events(self, text: str) -> list[dict]:
        return [
            json.loads(line[6:])
            for line in text.splitlines()
            if line.startswith("data: ")
        ]

    def test_v1_pipeline_happy_path(self):
        """POST /agent/analyze → SSE stream with start, step, done events."""
        from fastapi.testclient import TestClient

        # Mock app_v1.stream to yield fake events
        fake_stream = [
            {"fetch_tender": {"tender_id": "t1"}},
            {"analyze_tender": {"analysis": "ok"}},
            {"score_tender": {"score": 0.75}},
        ]

        mock_app_v1 = MagicMock()
        mock_app_v1.stream.return_value = iter(fake_stream)

        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            with patch(
                "services.api.services.api.routers.agent_pipeline._run_pipeline_sse",
                wraps=None,
            ):
                pass

        # Directly patch the langgraph import inside _run_pipeline_sse
        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            with patch.dict("sys.modules", {
                "services.agents.langgraph_pipeline": MagicMock(
                    app_v1=mock_app_v1,
                    app_v2=MagicMock(),
                ),
            }):
                client = TestClient(_make_app())
                resp = client.post("/api/v2/agent/analyze/tender-v1")

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = self._sse_events(resp.text)
        types = [e.get("type") for e in events]
        assert "start" in types
        assert "done" in types
        # score_tender step should include score
        step_events = [e for e in events if e.get("type") == "step"]
        score_events = [e for e in step_events if e.get("step") == "score_tender"]
        assert score_events
        assert score_events[0]["score"] == 0.75

    def test_v1_pipeline_error_path(self):
        """POST /agent/analyze → error SSE event when pipeline raises."""
        from fastapi.testclient import TestClient

        mock_app_v1 = MagicMock()
        mock_app_v1.stream.side_effect = RuntimeError("pipeline exploded")

        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            with patch.dict("sys.modules", {
                "services.agents.langgraph_pipeline": MagicMock(
                    app_v1=mock_app_v1,
                    app_v2=MagicMock(),
                ),
            }):
                client = TestClient(_make_app())
                resp = client.post("/api/v2/agent/analyze/tender-fail")

        assert resp.status_code == 200
        events = self._sse_events(resp.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert error_events
        assert "pipeline exploded" in error_events[0]["message"]


# ── POST /agent/decision/{tender_id} (v2 pipeline) ───────────────────────────

class TestAgentDecision:
    def _sse_events(self, text: str) -> list[dict]:
        return [
            json.loads(line[6:])
            for line in text.splitlines()
            if line.startswith("data: ")
        ]

    def test_v2_pipeline_happy_path(self):
        """POST /agent/decision → SSE stream with start + done, go_decision in step."""
        from fastapi.testclient import TestClient

        fake_stream = [
            {"ahp_score": {"ahp_result": 0.9}},
            {"generate_brief": {"go_decision": True, "decision_brief": "Go!"}},
        ]
        mock_app_v2 = MagicMock()
        mock_app_v2.stream.return_value = iter(fake_stream)

        with patch("services.api.services.api.routers.agent_pipeline.get_engine") as mock_ge:
            mock_ge.return_value = _make_engine()
            with patch.dict("sys.modules", {
                "services.agents.langgraph_pipeline": MagicMock(
                    app_v1=MagicMock(),
                    app_v2=mock_app_v2,
                ),
            }):
                client = TestClient(_make_app())
                resp = client.post("/api/v2/agent/decision/tender-v2")

        assert resp.status_code == 200
        events = self._sse_events(resp.text)
        types = [e.get("type") for e in events]
        assert "start" in types
        assert "done" in types
        # generate_brief step should include go_decision
        brief_steps = [e for e in events if e.get("step") == "generate_brief"]
        assert brief_steps
        assert brief_steps[0]["go_decision"] is True


# ── _stream_analysis helper unit tests ────────────────────────────────────────

class TestStreamAnalysisHelper:
    """Unit-test _stream_analysis generator directly."""

    def _collect(self, tender_id: str, engine) -> list[dict]:
        from services.api.services.api.routers.agent_pipeline import _stream_analysis
        with patch("services.api.services.api.routers.agent_pipeline.get_engine", return_value=engine):
            return [
                json.loads(line[6:])
                for line in "".join(_stream_analysis(tender_id)).splitlines()
                if line.startswith("data: ")
            ]

    def test_no_row_yields_no_analysis(self):
        events = self._collect("t-none", _make_engine())
        assert any(e.get("step") == "no_analysis" for e in events)

    def test_steps_as_list_are_streamed(self):
        steps = [{"step": "fetch_tender"}, {"step": "analyze"}]
        row_data = ("done", json.dumps(steps), None)
        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        events = self._collect("t-list", engine)
        step_names = [e.get("step") for e in events]
        assert "fetch_tender" in step_names
        assert "analyze" in step_names

    def test_steps_as_string_list_parses(self):
        """Steps stored as JSON string are parsed correctly."""
        steps = ["fetch_tender", "analyze_tender"]
        row_data = ("done", json.dumps(steps), None)
        conn = MagicMock()
        res = MagicMock()
        res.fetchone.return_value = row_data
        conn.execute.return_value = res
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn

        events = self._collect("t-strlist", engine)
        assert any(e.get("step") == "fetch_tender" for e in events)
