"""Flag — 'Don't guess, flag' pattern enforced everywhere."""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from .provenance import Provenance


class FlagSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    BLOCK = "block"


class Flag(BaseModel):
    """A structured warning/block emitted instead of a fabricated value.

    Rule: when a value is missing or ambiguous, emit Flag(severity=warn|block),
    never a fabricated value. This is enforced by L1 invariants and tested.
    """

    code: str
    """Machine-readable code, e.g. 'missing_dewatering', 'mass_balance_off'."""

    severity: FlagSeverity

    message: str
    """Polish-language human-readable description."""

    provenance: Provenance

    axiom_id: Optional[str] = None
    """L1 axiom that triggered this flag, e.g. 'ENG_DEWATER_001'."""

    @classmethod
    def warn(cls, code: str, message: str, provenance: Provenance, axiom_id: Optional[str] = None) -> "Flag":
        return cls(code=code, severity=FlagSeverity.WARN, message=message, provenance=provenance, axiom_id=axiom_id)

    @classmethod
    def block(cls, code: str, message: str, provenance: Provenance, axiom_id: Optional[str] = None) -> "Flag":
        return cls(code=code, severity=FlagSeverity.BLOCK, message=message, provenance=provenance, axiom_id=axiom_id)
