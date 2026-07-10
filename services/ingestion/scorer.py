"""Scorer v3 — konfigurowalny per-tenant, z deadline bonus + CPV win rate.

Zmiany względem v2:
- load_scoring_config() → ScoringWeights z DB (scoring_config table)
- _deadline_score(): <14d→1.0, <30d→0.7, <60d→0.4, else→0.1
- _cpv_win_rate_score(): bazuje na bzp_results (kto wygrywał w CPV)
- score_tender() uwzględnia historical_win_weight z konfigu
"""
from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

# ─── Simple TTL cache (thread-safe, no external deps) ──────────────────────────

_CACHE_TTL = 300  # 5 minutes
_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}  # key → (expires_at, value)


def _cache_get(key: str) -> Any:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() < entry[0]:
            return entry[1]
    return None


def _cache_set(key: str, value: Any, ttl: int = _CACHE_TTL) -> None:
    with _cache_lock:
        _cache[key] = (time.monotonic() + ttl, value)


def invalidate_scorer_cache(tenant_id: str | None = None) -> None:
    """Czyści cache scorera — wywołaj po zmianie scoring_config."""
    with _cache_lock:
        if tenant_id:
            keys = [k for k in _cache if tenant_id in k]
            for k in keys:
                del _cache[k]
        else:
            _cache.clear()
    logger.info("Scorer cache invalidated (tenant=%s)", tenant_id or "all")

# ─── ScoringWeights ────────────────────────────────────────────────────────────

@dataclass
class ScoringWeights:
    cpv_weight:            float = 0.35
    value_weight:          float = 0.20
    region_weight:         float = 0.15
    deadline_weight:       float = 0.10
    historical_win_weight: float = 0.20
    min_value_pln:         float | None = None
    max_value_pln:         float | None = None
    preferred_cpvs:        list[str] = field(default_factory=list)
    preferred_regions:     list[str] = field(default_factory=list)

    def normalize(self) -> "ScoringWeights":
        """Normalizuje wagi do sumy 1.0."""
        total = self.cpv_weight + self.value_weight + self.region_weight + \
                self.deadline_weight + self.historical_win_weight
        if total <= 0:
            return ScoringWeights()
        factor = 1.0 / total
        return ScoringWeights(
            cpv_weight=self.cpv_weight * factor,
            value_weight=self.value_weight * factor,
            region_weight=self.region_weight * factor,
            deadline_weight=self.deadline_weight * factor,
            historical_win_weight=self.historical_win_weight * factor,
            min_value_pln=self.min_value_pln,
            max_value_pln=self.max_value_pln,
            preferred_cpvs=self.preferred_cpvs,
            preferred_regions=self.preferred_regions,
        )


_DEFAULT_WEIGHTS = ScoringWeights()


# ─── OwnerProfileSnap ──────────────────────────────────────────────────────────

@dataclass
class OwnerProfileSnap(ScoringWeights):
    """Snapshot of owner preferences used by the ingestion pipeline.

    Default presets for a construction-industry firm in Dolnośląskie.
    Extends ScoringWeights with voivodeships for geo pre-filtering.
    """
    preferred_cpvs:    list[str]    = field(default_factory=lambda: ["45", "45100000", "45111200", "45200000", "45300000", "45400000"])
    preferred_regions: list[str]    = field(default_factory=lambda: ["dolnośląskie", "śląskie", "opolskie"])
    min_value_pln:     float | None = 100_000
    max_value_pln:     float | None = 10_000_000
    voivodeships:      list[str]    = field(default_factory=lambda: ["dolnośląskie", "śląskie", "opolskie"])
    cpv_weight:        float        = 0.40
    region_weight:     float        = 0.20



# ─── ScoreResult ───────────────────────────────────────────────────────────────

@dataclass
class ScoreResult:
    """Result returned by score_tender()."""
    score: float
    reason: str | None = None


# ─── DB helpers ────────────────────────────────────────────────────────────────

def load_scoring_config(tenant_id: str) -> ScoringWeights:
    """Ładuje konfigurację scoringu z DB dla tenanta. Cache TTL=5min. Fallback → defaults."""
    cache_key = f"scoring_config:{tenant_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT cpv_weight, value_weight, region_weight,
                       deadline_weight, historical_win_weight,
                       min_value_pln, max_value_pln,
                       preferred_cpvs, preferred_regions
                FROM scoring_config
                WHERE tenant_id = :tid
                LIMIT 1
            """), {"tid": tenant_id}).fetchone()
        if row:
            result = ScoringWeights(
                cpv_weight=float(row[0] or 0.35),
                value_weight=float(row[1] or 0.20),
                region_weight=float(row[2] or 0.15),
                deadline_weight=float(row[3] or 0.10),
                historical_win_weight=float(row[4] or 0.20),
                min_value_pln=float(row[5]) if row[5] else None,
                max_value_pln=float(row[6]) if row[6] else None,
                preferred_cpvs=list(row[7] or []),
                preferred_regions=list(row[8] or []),
            ).normalize()
            _cache_set(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"load_scoring_config failed: {e}")
    _cache_set(cache_key, _DEFAULT_WEIGHTS)
    return _DEFAULT_WEIGHTS


def load_cpv_win_rates(tenant_id: str | None = None) -> dict[str, float]:
    """
    Ładuje win-rates per CPV prefix (5 cyfr) z historical_bids. Cache TTL=5min.
    Zwraca {cpv_prefix: 0.0–1.0} — ratio won/total dla każdego CPV.
    Fallback: jeśli brak danych per-tenant, użyj globalnych.
    """
    cache_key = f"cpv_win_rates:{tenant_id or 'global'}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    engine = get_engine()
    win_rates: dict[str, float] = {}
    try:
        with engine.connect() as conn:
            # Per-tenant win rates z historical_bids
            tenant_filter = "AND org_id = :tid" if tenant_id else ""
            rows = conn.execute(text(f"""
                SELECT
                    LEFT(cpv, 5) as prefix,
                    COUNT(*) FILTER (WHERE won = true) as wins,
                    COUNT(*) as total
                FROM historical_bids
                WHERE cpv IS NOT NULL AND length(cpv) >= 5
                {tenant_filter}
                GROUP BY prefix
                HAVING COUNT(*) >= 2
                ORDER BY wins DESC
                LIMIT 500
            """), {"tid": tenant_id} if tenant_id else {}).fetchall()

            if not rows:
                # Fallback: globalne dane (wszystkie tenantów)
                rows = conn.execute(text("""
                    SELECT
                        LEFT(cpv, 5) as prefix,
                        COUNT(*) FILTER (WHERE won = true) as wins,
                        COUNT(*) as total
                    FROM historical_bids
                    WHERE cpv IS NOT NULL AND length(cpv) >= 5
                    GROUP BY prefix
                    HAVING COUNT(*) >= 1
                    ORDER BY wins DESC
                    LIMIT 500
                """)).fetchall()

        for prefix, wins, total in rows:
            win_rates[prefix] = round(wins / max(total, 1), 4)

    except Exception as e:
        logger.warning(f"load_cpv_win_rates failed: {e}")

    _cache_set(cache_key, win_rates)
    return win_rates


# ─── Scoring components ────────────────────────────────────────────────────────

def _cpv_score(tender_cpv: str | None, preferred_cpvs: list[str]) -> float:
    """CPV match: exact prefix match → 1.0, partial → 0.5, brak konfiguracji → 0.5 (neutral)."""
    if not preferred_cpvs:
        return 0.5  # neutral — tenant nie skonfigurował preferencji
    if not tender_cpv:
        return 0.0
    cpv = str(tender_cpv).strip()
    for pref in preferred_cpvs:
        p = str(pref).strip()
        if cpv.startswith(p) or p.startswith(cpv[:len(p)]):
            if len(p) >= 5:
                return 1.0
            return 0.5
    return 0.0


def _value_score(value_pln: float | None, weights: ScoringWeights) -> float:
    """Wartość w preferowanym przedziale → 1.0, brak konfiguracji → 0.5 (neutral)."""
    if weights.min_value_pln is None and weights.max_value_pln is None:
        return 0.5  # neutral
    if value_pln is None or value_pln <= 0:
        return 0.0
    lo = weights.min_value_pln or 0
    hi = weights.max_value_pln or float("inf")
    if lo <= value_pln <= hi:
        return 1.0
    if value_pln < lo:
        return max(0.0, 1.0 - (lo - value_pln) / max(lo, 1))
    return max(0.0, 1.0 - (value_pln - hi) / max(hi, 1))


def _region_score(voivodeship: str | None, preferred_regions: list[str]) -> float:
    if not preferred_regions:
        return 0.5  # neutral
    if not voivodeship:
        return 0.0
    v = voivodeship.lower().strip()
    for r in preferred_regions:
        if r.lower().strip() in v or v in r.lower().strip():
            return 1.0
    return 0.0


def _deadline_score(deadline: date | datetime | str | None) -> float:
    """
    Deadline proximity bonus:
    <14 dni → 1.0 (pilne, działaj teraz)
    <30 dni → 0.7
    <60 dni → 0.4
    ≥60 dni → 0.1
    brak    → 0.0
    """
    if deadline is None:
        return 0.5  # neutral — brak danych o deadline
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if isinstance(deadline, datetime):
        deadline = deadline.date()
    today = date.today()
    delta = (deadline - today).days
    if delta < 0:
        return 0.0  # Minął
    if delta < 14:
        return 1.0
    if delta < 30:
        return 0.7
    if delta < 60:
        return 0.4
    return 0.1


def _cpv_win_rate_score(tender_cpv: str | None, win_rates: dict[str, float]) -> float:
    """CPV win rate z historycznych wygranych."""
    if not tender_cpv or not win_rates:
        return 0.0
    prefix5 = str(tender_cpv)[:5]
    return win_rates.get(prefix5, 0.0)


# ─── Main scoring function ──────────────────────────────────────────────────────

def score_tender(
    tender: dict[str, Any],
    weights: ScoringWeights,
    win_rates: dict[str, float] | None = None,
) -> "ScoreResult":
    """
    Oblicza match_score (0.0–1.0) dla jednego przetargu.
    tender dict musi mieć: cpv_main, value_pln, voivodeship, deadline
    Zwraca ScoreResult z polami .score i .reason.
    """
    w = weights.normalize()
    # Support both dict and dataclass (TenderIn)
    if hasattr(tender, "__dict__") and not isinstance(tender, dict):
        _t = tender.__dict__
    else:
        _t = tender  # type: ignore[assignment]
    def _g(key: str, *alt: str):
        for k in (key,) + alt:
            v = _t.get(k) if isinstance(_t, dict) else getattr(_t, k, None)
            if v is not None:
                # unwrap single-item list (e.g. cpv=['45111200-0'])
                if isinstance(v, list):
                    return v[0] if v else None
                return v
        return None
    cpv   = _g("cpv_main", "cpv")
    value = _g("value_pln", "estimated_value_pln")
    region = _g("voivodeship", "region")
    deadline = _g("deadline", "submission_deadline")

    if value is not None:
        try:
            value = float(value)
        except (ValueError, TypeError):
            value = None

    components = {
        "cpv":    (w.cpv_weight,            _cpv_score(cpv, w.preferred_cpvs)),
        "value":  (w.value_weight,           _value_score(value, w)),
        "region": (w.region_weight,          _region_score(region, w.preferred_regions)),
        "deadline": (w.deadline_weight,      _deadline_score(deadline)),
        "win_rate": (w.historical_win_weight, _cpv_win_rate_score(cpv, win_rates or {})),
    }

    score = round(min(1.0, max(0.0, sum(wt * sc for wt, sc in components.values()))), 4)

    # S64: ML Scorer override if enabled in scoring_config
    try:
        if getattr(weights, "ml_scorer_enabled", False):
            from services.ingestion.scorer_ml import get_ml_scorer
            ml = get_ml_scorer()
            if ml.model is not None:
                tender_feats = {
                    "cpv_match": components["cpv"][1],
                    "value_in_range": components["value"][1],
                    "region_match": components["region"][1],
                    "deadline_days": float(_g("deadline_days") or 30),
                    "title_keyword_count": 0.0,
                    "historical_win_rate": components["win_rate"][1],
                }
                ml_score = ml.score_tender(tender_feats)
                # blend: 60% rule-based + 40% ML
                score = round(0.6 * score + 0.4 * ml_score, 4)
    except Exception:
        pass  # ML scorer optional — fallback to rule-based

    # Build human-readable reason string
    reason_parts = []
    if components["cpv"][1] >= 0.8:
        reason_parts.append(f"CPV match ({cpv})")
    if components["region"][1] >= 0.8:
        reason_parts.append(f"region {region}")
    if components["deadline"][1] >= 0.7:
        reason_parts.append("pilny deadline")
    if components["win_rate"][1] >= 0.5:
        reason_parts.append("wysoki win-rate")
    reason = "; ".join(reason_parts) if reason_parts else None

    return ScoreResult(score=score, reason=reason)


# ─── Batch rescore ─────────────────────────────────────────────────────────────

def rescore_tenant(tenant_id: str, batch_size: int = 500) -> dict:
    """Rescoruje wszystkie przetargi tenanta. Zwraca statystyki."""
    weights = load_scoring_config(tenant_id)
    win_rates = load_cpv_win_rates(tenant_id)

    engine = get_engine()
    total = 0
    avg_before = 0.0
    avg_after = 0.0

    with engine.connect() as conn:
        count_row = conn.execute(text(
            "SELECT COUNT(*), AVG(match_score) FROM tender WHERE tenant_id = :tid"
        ), {"tid": tenant_id}).fetchone()
        if count_row:
            total = count_row[0]
            avg_before = float(count_row[1] or 0)

    offset = 0
    processed = 0
    with engine.begin() as conn:
        while True:
            rows = conn.execute(text("""
                SELECT id, cpv, value_pln, voivodeship, deadline_at, match_score
                FROM tender
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT :lim OFFSET :off
            """), {"tid": tenant_id, "lim": batch_size, "off": offset}).fetchall()

            if not rows:
                break

            for row in rows:
                tender_dict = {
                    "id": str(row[0]),
                    "cpv_main": row[1],
                    "value_pln": row[2],
                    "voivodeship": row[3],
                    "deadline": row[4],
                }
                new_score = score_tender(tender_dict, weights, win_rates)
                conn.execute(text(
                    "UPDATE tender SET match_score = :score WHERE id = :id"
                ), {"score": new_score.score, "id": str(row[0])})
                avg_after += new_score.score
                processed += 1

            offset += batch_size
            if len(rows) < batch_size:
                break

    if processed > 0:
        avg_after /= processed

    logger.info(
        f"Rescore tenant={tenant_id}: {processed} tenders, "
        f"avg {avg_before:.3f} → {avg_after:.3f}"
    )
    return {
        "total": total,
        "processed": processed,
        "avg_score_before": round(avg_before, 4),
        "avg_score_after": round(avg_after, 4),
    }


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--batch-size", type=int, default=500)
    args = ap.parse_args()
    result = rescore_tenant(args.tenant_id, batch_size=args.batch_size)
    print(f"Done: {result}")
