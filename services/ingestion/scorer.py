"""M1 — Matcher/scorer: computes match_score for each tender vs owner profile.

Score ∈ [0.0, 1.0] — higher = better match.

Scoring factors (v2 — configurable weights per tenant):
  1. CPV overlap with owner preferred CPVs        (0–W_CPV pts)
  2. Voivodeship match                             (0–W_GEO pts)
  3. Value range fit                               (0–W_VAL pts)
  4. Deadline proximity bonus                      (0–W_DDL pts)   ← F17
  5. Keyword match in title                        (0–W_KW pts)
  6. Historical win rate CPV boost (market_results)(0–W_WIN pts)   ← F18
  ──────────────────────────────────────────────────────────────
  Total: sum(weights) pts → normalized to 0.0–1.0

Weights are configurable per tenant via ScoringWeights dataclass (F16).
Default weights sum to 100.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple

from .normalize import TenderIn

logger = logging.getLogger(__name__)


# ─────────────────────────────── Weights ──────────────────────────────── #

@dataclass
class ScoringWeights:
    """Configurable scoring weights per tenant (F16).

    All values are in points (not fractions). The scorer normalizes by
    the sum of weights, so you can add/remove factors freely.
    """
    cpv: int = 35       # CPV match
    geo: int = 25       # Voivodeship match
    value: int = 20     # Value range fit
    deadline: int = 10  # Deadline proximity bonus (F17)
    keywords: int = 10  # Keyword match in title

    # F18 — historical win rate CPV boost
    # Points added on top when CPV has high historical win rate.
    # The win_boost value is added to cpv score when win_rate >= win_threshold.
    win_boost: int = 10     # extra pts on high win-rate CPV
    win_threshold: float = 0.20  # min win rate fraction to trigger boost

    @property
    def total(self) -> int:
        return self.cpv + self.geo + self.value + self.deadline + self.keywords

    def max_score(self) -> int:
        """Max achievable score (total + win_boost)."""
        return self.total + self.win_boost


# ─────────────────────────────── Profile ──────────────────────────────── #

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
        weights: ScoringWeights | None = None,
        # F18: CPV win rates from market_results {cpv5_prefix: win_rate}
        cpv_win_rates: dict[str, float] | None = None,
    ) -> None:
        self.cpv_preferred: set[str] = set(cpv_preferred or [
            "45111200-0",
            "45233120-6",
            "45112000-5",
            "45112700-2",
            "45232410-9",
        ])
        self.voivodeships: set[str] = set(v.lower() for v in (voivodeships or []))
        self.value_min = Decimal(str(value_min_pln))
        self.value_max = Decimal(str(value_max_pln))
        self.keywords: list[str] = keywords or [
            "roboty budowlane", "roboty ziemne", "budowa", "przebudowa", "remont",
            "instalacja", "sieć", "wodociąg", "kanalizacja", "droga", "most",
            "kubatura", "hala", "budynek", "rozbiórka", "modernizacja",
        ]
        self.weights: ScoringWeights = weights or ScoringWeights()
        # F18: historical win rate per CPV 5-char prefix
        self.cpv_win_rates: dict[str, float] = cpv_win_rates or {}


# ─────────────────────────────── Result ───────────────────────────────── #

class ScoreResult(NamedTuple):
    score: float          # 0.0–1.0
    reason: str           # human-readable explanation


# ─────────────────────────────── Factors ──────────────────────────────── #

def _cpv_score(tender_cpv: list[str], preferred: set[str], weight: int) -> int:
    """0–weight pts: exact match = weight, prefix match = weight//2, no match = 0."""
    if not tender_cpv:
        return 0
    for code in tender_cpv:
        if code in preferred:
            return weight
    # prefix match (first 5 chars = CPV division+group)
    for code in tender_cpv:
        for pref in preferred:
            if code[:5] == pref[:5]:
                return weight // 2
    return 0


def _geo_score(voivodeship: str | None, target: set[str], weight: int) -> int:
    """0–weight pts."""
    if not voivodeship or not target:
        return weight // 4  # unknown — partial credit
    if voivodeship.lower() in target:
        return weight
    return 0


def _value_score(value_pln: Decimal | None, vmin: Decimal, vmax: Decimal, weight: int) -> int:
    """0–weight pts: in range = weight, within 2× = weight//2, outside = 0."""
    if value_pln is None or value_pln <= Decimal("0"):
        return 0
    if vmin <= value_pln <= vmax:
        return weight
    if value_pln < vmin and vmin / value_pln <= Decimal("2"):
        return weight // 2
    if value_pln > vmax and value_pln / vmax <= Decimal("2"):
        return weight // 2
    return 0


def _deadline_score(deadline_at: datetime | None, weight: int) -> int:
    """F17 — Deadline proximity bonus.

    More points when the deadline is closer (urgency matters).
    None/past → 0. >60 days → minimal. 7–21 days → sweet spot.
    """
    if not deadline_at:
        return weight // 2  # unknown deadline — neutral
    now = datetime.now(timezone.utc)
    if deadline_at.tzinfo is None:
        deadline_at = deadline_at.replace(tzinfo=timezone.utc)
    days = (deadline_at - now).days
    if days < 0:
        return 0          # already past
    if days <= 7:
        return weight // 5  # too tight — low priority
    if days <= 14:
        return weight     # sweet spot: 1–2 weeks
    if days <= 21:
        return int(weight * 0.8)  # still good
    if days <= 45:
        return int(weight * 0.5)  # comfortable
    return int(weight * 0.2)      # plenty of time — lower urgency


def _keyword_score(title: str, keywords: list[str], weight: int) -> int:
    """0–weight pts: any keyword match = weight."""
    title_lower = title.lower()
    for kw in keywords:
        if kw.lower() in title_lower:
            return weight
    return 0


def _win_rate_boost(
    tender_cpv: list[str],
    cpv_win_rates: dict[str, float],
    win_boost: int,
    win_threshold: float,
) -> int:
    """F18 — Historical win rate CPV boost.

    Returns win_boost pts if any of the tender's CPV 5-prefixes has a
    historical win rate >= win_threshold in the owner's market_results.
    Rewards CPVs where the company has proven track record.
    """
    if not cpv_win_rates or not tender_cpv:
        return 0
    for code in tender_cpv:
        prefix = code[:5]
        rate = cpv_win_rates.get(prefix, 0.0)
        if rate >= win_threshold:
            return win_boost
    return 0


# ─────────────────────────────── Main ─────────────────────────────────── #

def score_tender(tender: TenderIn, profile: OwnerProfileSnap) -> ScoreResult:
    """Compute deterministic match score (v2) for a tender vs owner profile."""
    w = profile.weights

    pts_cpv = _cpv_score(tender.cpv, profile.cpv_preferred, w.cpv)
    pts_geo = _geo_score(tender.voivodeship, profile.voivodeships, w.geo)
    pts_val = _value_score(tender.value_pln, profile.value_min, profile.value_max, w.value)
    pts_ddl = _deadline_score(tender.deadline_at, w.deadline)    # F17
    pts_kw  = _keyword_score(tender.title, profile.keywords, w.keywords)
    pts_win = _win_rate_boost(                                     # F18
        tender.cpv,
        profile.cpv_win_rates,
        w.win_boost,
        w.win_threshold,
    )

    total = pts_cpv + pts_geo + pts_val + pts_ddl + pts_kw + pts_win
    max_pts = w.max_score()
    score = round(total / max_pts, 4) if max_pts > 0 else 0.0

    reasons: list[str] = []
    if pts_cpv >= w.cpv:
        reasons.append("CPV dokładny")
    elif pts_cpv >= w.cpv // 2:
        reasons.append("CPV zbliżony")
    else:
        reasons.append("CPV nie pasuje")
    if pts_geo == w.geo:
        reasons.append("region docelowy")
    elif pts_geo == 0:
        reasons.append("inny region")
    if pts_val == w.value:
        reasons.append("wartość w zakresie")
    elif pts_val > 0:
        reasons.append("wartość blisko zakresu")
    else:
        reasons.append("wartość poza zakresem")
    if pts_ddl >= w.deadline:
        reasons.append("deadline optymalny")
    elif pts_ddl == 0:
        reasons.append("deadline minął")
    if pts_kw > 0:
        reasons.append("słowa kluczowe")
    if pts_win > 0:
        reasons.append("wygrane CPV historycznie")

    return ScoreResult(score=score, reason="; ".join(reasons))


# ─────────────────────────────── Helpers ──────────────────────────────── #

def load_cpv_win_rates(
    db_dsn: str = "host=127.0.0.1 dbname=terraos user=terraos",
    tenant_id: str | None = None,
    days_back: int = 90,
) -> dict[str, float]:
    """F18 — Load CPV win rates from market_results.

    Returns dict {cpv5_prefix: win_rate} where win_rate = contracts/total_bids
    for TenderResultNotice with procedure_result='zawarcieUmowy'.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(db_dsn)
        try:
            with conn.cursor() as cur:
                q = """
                    SELECT
                        left(cpv_codes[1], 5) AS cpv5,
                        count(*) FILTER (WHERE procedure_result = 'zawarcieUmowy') AS wins,
                        count(*) AS total
                    FROM market_results
                    WHERE
                        cpv_codes IS NOT NULL
                        AND array_length(cpv_codes, 1) > 0
                        AND published_at >= now() - interval '%s days'
                        %s
                    GROUP BY cpv5
                    HAVING count(*) >= 3
                """ % (
                    days_back,
                    f"AND tenant_id = '{tenant_id}'" if tenant_id else "",
                )
                cur.execute(q)
                rows = cur.fetchall()
                rates = {}
                for cpv5, wins, total in rows:
                    if cpv5 and total > 0:
                        rates[cpv5] = wins / total
                return rates
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("load_cpv_win_rates failed: %s", exc)
        return {}
