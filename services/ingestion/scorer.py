"""M1 — Matcher/scorer: computes match_score for each tender vs owner profile.

Score ∈ [0.0, 1.0] — higher = better match.

Scoring factors (deterministic, no LLM in M1):
  1. CPV overlap with owner preferred CPVs      (0–35 pts)
  2. Voivodeship match                           (0–25 pts)
  3. Value range fit                             (0–20 pts)
  4. Deadline urgency (days remaining)           (0–10 pts)
  5. Keyword match in title                      (0–10 pts)
  ──────────────────────────────────────────────
  Total: 0–100 pts → normalized to 0.0–1.0
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple

from .normalize import TenderIn

logger = logging.getLogger(__name__)


class OwnerProfileSnap:
    """Minimal snapshot of owner profile for scoring (no DB dep)."""

    def __init__(
        self,
        *,
        cpv_preferred: list[str] | None = None,
        voivodeships: list[str] | None = None,
        value_min_pln: float = 100_000,
        value_max_pln: float = 5_000_000,
        keywords: list[str] | None = None,
    ) -> None:
        self.cpv_preferred: set[str] = set(cpv_preferred or [
            "45111200-0",
            "45233120-6",
            "45112000-5",
            "45112700-2",
            "45232410-9",
        ])
        self.voivodeships: set[str] = set(v.lower() for v in (voivodeships or ["dolnośląskie"]))
        self.value_min = Decimal(str(value_min_pln))
        self.value_max = Decimal(str(value_max_pln))
        self.keywords: list[str] = keywords or [
            "roboty budowlane", "roboty ziemne", "budowa", "przebudowa", "remont",
            "instalacja", "sieć", "wodociąg", "kanalizacja", "droga", "most",
            "kubatura", "hala", "budynek", "rozbiórka", "modernizacja",
        ]


class ScoreResult(NamedTuple):
    score: float          # 0.0–1.0
    reason: str           # human-readable explanation


def _cpv_score(tender_cpv: list[str], preferred: set[str]) -> int:
    """0–35 pts: exact match = 35, prefix match = 15, no match = 0."""
    if not tender_cpv:
        return 0
    for code in tender_cpv:
        if code in preferred:
            return 35
    # prefix match
    for code in tender_cpv:
        for pref in preferred:
            if code[:5] == pref[:5]:
                return 15
    return 0


def _geo_score(voivodeship: str | None, target: set[str]) -> int:
    """0–25 pts."""
    if not voivodeship or not target:
        return 10  # unknown — partial credit
    if voivodeship.lower() in target:
        return 25
    return 0


def _value_score(value_pln: Decimal | None, vmin: Decimal, vmax: Decimal) -> int:
    """0–20 pts: in range = 20, within 2× range = 10, outside = 0."""
    if value_pln is None:
        return 10  # unknown — partial
    if vmin <= value_pln <= vmax:
        return 20
    if value_pln < vmin and vmin / value_pln <= Decimal("2"):
        return 10
    if value_pln > vmax and value_pln / vmax <= Decimal("2"):
        return 10
    return 0


def _deadline_score(deadline_at: datetime | None) -> int:
    """0–10 pts: >21 days = 10, 14–21 = 7, 7–14 = 5, <7 = 2, past/None = 0."""
    if not deadline_at:
        return 5
    now = datetime.now(timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    days = (deadline_at - now).days
    if days < 0:
        return 0
    if days >= 21:
        return 10
    if days >= 14:
        return 7
    if days >= 7:
        return 5
    return 2


def _keyword_score(title: str, keywords: list[str]) -> int:
    """0–10 pts: any keyword match = 10."""
    title_lower = title.lower()
    for kw in keywords:
        if kw.lower() in title_lower:
            return 10
    return 0


def score_tender(tender: TenderIn, profile: OwnerProfileSnap) -> ScoreResult:
    """Compute deterministic match score for a tender vs owner profile."""
    pts_cpv = _cpv_score(tender.cpv, profile.cpv_preferred)
    pts_geo = _geo_score(tender.voivodeship, profile.voivodeships)
    pts_val = _value_score(tender.value_pln, profile.value_min, profile.value_max)
    pts_ddl = _deadline_score(tender.deadline_at)
    pts_kw = _keyword_score(tender.title, profile.keywords)

    total = pts_cpv + pts_geo + pts_val + pts_ddl + pts_kw
    score = round(total / 100, 4)

    reasons = []
    if pts_cpv >= 35:
        reasons.append("CPV dokładny")
    elif pts_cpv >= 15:
        reasons.append("CPV zbliżony")
    else:
        reasons.append("CPV nie pasuje")
    if pts_geo == 25:
        reasons.append("region docelowy")
    elif pts_geo == 0:
        reasons.append("inny region")
    if pts_val == 20:
        reasons.append("wartość w zakresie")
    elif pts_val == 10:
        reasons.append("wartość blisko zakresu")
    else:
        reasons.append("wartość poza zakresem")
    if pts_kw == 10:
        reasons.append("słowa kluczowe")

    reason = "; ".join(reasons)
    return ScoreResult(score=score, reason=reason)
