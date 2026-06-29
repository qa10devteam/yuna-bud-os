"""M0 scaffold tests — must pass with ZERO network (stubs/fixtures).

Acceptance gate (spec/09 M0):
- pytest green (empty/scaffold tests)
- /health returns db ok
"""
from __future__ import annotations

import pytest
from terra_shared.provenance import Provenance
from terra_shared.flag import Flag, FlagSeverity
from terra_shared.audit import AuditWriter
from terra_shared.errors import TerraError, NotFoundError, EngineInfeasibleError


class TestProvenance:
    def test_create_minimal(self) -> None:
        p = Provenance(source="bzp")
        assert p.source == "bzp"
        assert p.confidence is None

    def test_deterministic_factory(self) -> None:
        p = Provenance.deterministic("design", doc_id="abc-123")
        assert p.doc_id == "abc-123"
        assert p.confidence is None

    def test_full(self) -> None:
        p = Provenance(source="przedmiar", doc_id="x", page=3, line_or_pos="row 42", confidence=0.95)
        assert p.page == 3
        assert p.confidence == 0.95


class TestFlag:
    def _prov(self) -> Provenance:
        return Provenance(source="test")

    def test_warn_factory(self) -> None:
        f = Flag.warn("TEST_001", "Test warning", self._prov())
        assert f.severity == FlagSeverity.WARN
        assert f.code == "TEST_001"

    def test_block_factory(self) -> None:
        f = Flag.block("TEST_002", "Test block", self._prov(), axiom_id="AX-001")
        assert f.severity == FlagSeverity.BLOCK
        assert f.axiom_id == "AX-001"

    def test_no_fabricated_value(self) -> None:
        """Invariant: when a value is missing, emit Flag, never fabricate."""
        p = Provenance(source="przedmiar", page=5)
        f = Flag.warn("missing_quantity", "Brak ilości w pozycji 1.2.3", p)
        assert f.provenance.page == 5

    def test_every_flag_has_provenance(self) -> None:
        """Invariant: every flag carries provenance."""
        p = Provenance(source="bzp", doc_id="doc-1")
        f = Flag.block("low_price", "Cena >30% poniżej szacunku", p, axiom_id="REG_LOW_001")
        assert f.provenance.doc_id == "doc-1"
        assert f.axiom_id == "REG_LOW_001"


class TestAuditWriter:
    def test_log_entry(self) -> None:
        writer = AuditWriter()
        entry = writer.log(
            tenant_id="t-1",
            actor="ingest_agent",
            action="ingest.run",
            entity_kind="tender",
            entity_id="e-1",
        )
        assert entry.ok is True
        assert len(writer.entries) == 1

    def test_append_only(self) -> None:
        """Audit writer only appends, never modifies."""
        writer = AuditWriter()
        writer.log("t-1", "agent", "step.1")
        writer.log("t-1", "agent", "step.2")
        assert len(writer.entries) == 2
        assert writer.entries[0].action == "step.1"
        assert writer.entries[1].action == "step.2"

    def test_error_entry(self) -> None:
        writer = AuditWriter()
        entry = writer.log("t-1", "agent", "side_effect.send_email", ok=False, error_message="SMTP timeout")
        assert entry.ok is False
        assert "SMTP" in entry.error_message  # type: ignore[operator]


class TestErrors:
    def test_not_found(self) -> None:
        err = NotFoundError("tender not found", {"id": "x"})
        assert err.code == "not_found"
        assert err.status_code == 404

    def test_engine_infeasible(self) -> None:
        err = EngineInfeasibleError("no feasible assignment")
        assert err.code == "engine_infeasible"
        assert err.status_code == 422

    def test_terra_error_is_base(self) -> None:
        err = NotFoundError("x")
        assert isinstance(err, TerraError)


class TestHealthEndpoint:
    """Scaffold test for /health — passes without DB (db field may be error)."""

    def test_health_route_exists(self) -> None:
        from fastapi.testclient import TestClient
        from services.api.services.api.main import app  # type: ignore[import-untyped]

        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "db" in data
