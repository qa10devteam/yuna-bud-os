"""Provenance — every analytical output carries source tracing."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class Provenance(BaseModel):
    """Source reference for any analytical claim.

    Invariant: no claim is emitted without a Provenance.
    confidence=None means 'extracted from structured data, N/A'.
    """

    source: str
    """Connector or document kind, e.g. 'bzp', 'przedmiar', 'design'."""

    doc_id: Optional[str] = None
    """Internal document UUID (document table)."""

    page: Optional[int] = None
    """1-indexed page number in source document."""

    line_or_pos: Optional[str] = None
    """Section/line reference, e.g. 'row 42' or 'section 2.3'."""

    confidence: Optional[float] = None
    """0..1 extraction confidence; None = deterministic."""

    @classmethod
    def deterministic(cls, source: str, doc_id: Optional[str] = None) -> "Provenance":
        """Factory for deterministic (non-LLM) outputs."""
        return cls(source=source, doc_id=doc_id)
