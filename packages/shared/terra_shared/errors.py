"""Typed exceptions for YU-NA."""
from __future__ import annotations
from typing import Optional


class TerraError(Exception):
    """Base exception for all YU-NA errors."""
    code: str = "internal"
    status_code: int = 500

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(TerraError):
    code = "not_found"
    status_code = 404


class ValidationError(TerraError):
    code = "validation_error"
    status_code = 422


class ConflictError(TerraError):
    code = "conflict"
    status_code = 409


class ApprovalRequiredError(TerraError):
    """Raised when a side-effectful action needs human approval."""
    code = "approval_required"
    status_code = 202


class CostCapExceededError(TerraError):
    """Raised when per-call or per-day LLM cost cap is breached."""
    code = "cost_cap_exceeded"
    status_code = 429


class EngineInfeasibleError(TerraError):
    """Raised when L1/L2 engine finds no feasible solution."""
    code = "engine_infeasible"
    status_code = 422


class SourceUnavailableError(TerraError):
    """Raised when an external tender source is unreachable."""
    code = "source_unavailable"
    status_code = 503
