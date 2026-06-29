"""M9 — Tier feature-flags.

TIER env var controls which modules / engine layers are active.

  TIER=1  → Module 1 only (Zwiad BZP): ingest, match, documents
  TIER=2  → Tier 1 + Module 2 (Silnik): engine L1+L2, estimator, RFQ, approvals, chat
  TIER=3  → Full (Mózg): Tier 1+2 + logistics, plans, mobile, pipeline supervisor

Use `is_enabled(feature)` anywhere in the codebase.
Guard tests verify that higher-tier endpoints return 403 when TIER is insufficient.
"""
from __future__ import annotations

import os


def current_tier() -> int:
    """Return current TIER (default 3 — full)."""
    return int(os.environ.get("TIER", "3"))


def is_enabled(feature: str) -> bool:
    """Check if a feature is enabled for the current TIER.

    Feature map:
      tier1: ingest, match, documents, analyze
      tier2: engine, estimator, rfq, approvals, chat_brain
      tier3: logistics, plans, mobile, pipeline_supervisor, learning_loop
    """
    tier = current_tier()
    tier1 = {"ingest", "match", "documents", "analyze"}
    tier2 = {"engine", "estimator", "rfq", "approvals", "chat_brain"}
    tier3 = {"logistics", "plans", "mobile", "pipeline_supervisor", "learning_loop"}

    if feature in tier1:
        return tier >= 1
    if feature in tier2:
        return tier >= 2
    if feature in tier3:
        return tier >= 3
    return True  # unknown features pass through


def require_tier(min_tier: int) -> None:
    """Raise HTTPException 403 if current tier < min_tier."""
    from fastapi import HTTPException
    if current_tier() < min_tier:
        raise HTTPException(
            status_code=403,
            detail=f"Feature requires TIER>={min_tier}, current TIER={current_tier()}",
        )
