"""Advanced Scoring v2 — Model calibration, backtesting, and A/B weight experiments.

Endpoints:
  POST /api/v2/scoring/backtest         — run historical backtest on scoring config
  GET  /api/v2/scoring/calibration      — model calibration metrics
  POST /api/v2/scoring/experiment       — create A/B experiment with alternate weights
  GET  /api/v2/scoring/experiments      — list experiments + results
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/scoring", tags=["scoring-v2"])
logger = logging.getLogger(__name__)


class WeightsModel(BaseModel):
    cpv_match: float = 25
    value_range: float = 20
    deadline_pressure: float = 20
    buyer_history: float = 20
    document_quality: float = 15


class BacktestRequest(BaseModel):
    weights: WeightsModel
    lookback_days: int = 90
    min_pipeline_status: str = "qualified"


class ExperimentRequest(BaseModel):
    name: str
    variant_weights: WeightsModel
    sample_pct: float = 50  # % of tenders to score with variant


# ── Backtest ───────────────────────────────────────────────────────────────────

@router.post("/backtest")
def run_backtest(req: BacktestRequest) -> dict[str, Any]:
    """Historical backtest: how would these weights have scored tenders that were won/lost?"""
    engine = get_engine()

    with engine.connect() as conn:
        # Get tenders with known outcomes in the lookback window
        rows = conn.execute(sa.text("""
            SELECT id, title, cpv, value_pln, deadline_at, pipeline_status, match_score,
                   buyer, created_at
            FROM tender
            WHERE pipeline_status IN ('won', 'lost')
              AND created_at > NOW() - INTERVAL '1 day' * :days
            ORDER BY created_at DESC
        """), {"days": req.lookback_days}).fetchall()

    if not rows:
        return {"error": "No won/lost tenders in lookback window", "lookback_days": req.lookback_days, "results": []}

    results = []
    tp, fp, tn, fn = 0, 0, 0, 0
    threshold = 60.0  # Score above this = "would bid"

    for r in rows:
        # Simulate scoring with proposed weights
        simulated_score = _simulate_score(
            cpv=r[2], value=float(r[3]) if r[3] else 0,
            deadline=r[4], buyer=r[7],
            weights=req.weights.model_dump(),
        )
        actual_won = r[5] == 'won'
        would_bid = simulated_score >= threshold

        if would_bid and actual_won:
            tp += 1
        elif would_bid and not actual_won:
            fp += 1
        elif not would_bid and not actual_won:
            tn += 1
        else:
            fn += 1

        results.append({
            "tender_id": str(r[0]),
            "title": r[1][:60] if r[1] else "",
            "original_score": float(r[6]) if r[6] else 0,
            "simulated_score": round(simulated_score, 2),
            "actual_outcome": r[5],
            "decision": "BID" if would_bid else "SKIP",
            "correct": (would_bid and actual_won) or (not would_bid and not actual_won),
        })

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / total if total > 0 else 0

    return {
        "lookback_days": req.lookback_days,
        "total_tenders": total,
        "threshold": threshold,
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        },
        "weights_tested": req.weights.model_dump(),
        "results": results[:20],
    }


def _simulate_score(cpv: str | None, value: float, deadline, buyer: str | None, weights: dict) -> float:
    """Simulate a tender score given weights."""
    # Simple simulation: each dimension 0-100, weighted
    cpv_score = 70 if cpv and len(cpv) >= 8 else 40  # Specific CPV = better match
    value_score = min(value / 5_000_000 * 100, 100) if value else 30
    
    deadline_score = 50
    if deadline:
        try:
            days_left = (deadline - datetime.utcnow()).days
            if days_left < 7:
                deadline_score = 90
            elif days_left < 14:
                deadline_score = 70
            elif days_left < 30:
                deadline_score = 50
            else:
                deadline_score = 30
        except (TypeError, AttributeError):
            pass

    buyer_score = 60 if buyer else 30
    doc_score = 50  # Neutral without actual doc analysis

    total = (
        cpv_score * weights.get("cpv_match", 25) +
        value_score * weights.get("value_range", 20) +
        deadline_score * weights.get("deadline_pressure", 20) +
        buyer_score * weights.get("buyer_history", 20) +
        doc_score * weights.get("document_quality", 15)
    ) / 100

    return total


# ── Calibration ────────────────────────────────────────────────────────────────

@router.get("/calibration")
def get_calibration() -> dict[str, Any]:
    """Model calibration — how well do scores predict outcomes?"""
    engine = get_engine()

    with engine.connect() as conn:
        # Bin tenders by score decile and check actual win rates
        rows = conn.execute(sa.text("""
            SELECT 
                CASE 
                    WHEN match_score >= 90 THEN '90-100'
                    WHEN match_score >= 80 THEN '80-89'
                    WHEN match_score >= 70 THEN '70-79'
                    WHEN match_score >= 60 THEN '60-69'
                    WHEN match_score >= 50 THEN '50-59'
                    WHEN match_score >= 40 THEN '40-49'
                    WHEN match_score >= 30 THEN '30-39'
                    ELSE '0-29'
                END as score_bin,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE pipeline_status = 'won') as wins,
                AVG(match_score) as avg_score
            FROM tender
            WHERE match_score IS NOT NULL
              AND pipeline_status IN ('won', 'lost')
            GROUP BY 1
            ORDER BY 1 DESC
        """)).fetchall()

    bins = []
    for r in rows:
        total = int(r[1])
        wins = int(r[2])
        bins.append({
            "bin": r[0],
            "count": total,
            "wins": wins,
            "actual_win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "avg_score": round(float(r[3]), 1) if r[3] else 0,
        })

    # Calculate Brier score (calibration metric)
    brier_sum = 0
    n = 0
    for b in bins:
        predicted_prob = b["avg_score"] / 100
        actual_prob = b["actual_win_rate"] / 100
        brier_sum += b["count"] * (predicted_prob - actual_prob) ** 2
        n += b["count"]

    brier_score = brier_sum / n if n > 0 else 1.0

    return {
        "bins": bins,
        "brier_score": round(brier_score, 4),
        "calibration_quality": "good" if brier_score < 0.1 else "fair" if brier_score < 0.25 else "poor",
        "total_evaluated": n,
        "recommendation": _calibration_recommendation(bins),
    }


def _calibration_recommendation(bins: list) -> str:
    """Generate calibration recommendation."""
    if not bins:
        return "Za mało danych do kalibracji. Potrzeba min. 20 przetargów z rozstrzygniętym wynikiem."
    over_confident = [b for b in bins if b["avg_score"] > 70 and b["actual_win_rate"] < 30]
    under_confident = [b for b in bins if b["avg_score"] < 40 and b["actual_win_rate"] > 50]
    if over_confident:
        return f"Model przeszacowuje szanse w binach: {', '.join(b['bin'] for b in over_confident)}. Rozważ zmniejszenie wag."
    if under_confident:
        return f"Model niedoszacowuje szanse w binach: {', '.join(b['bin'] for b in under_confident)}. Rozważ zwiększenie wag."
    return "Kalibracja w normie."


# ── Experiments ────────────────────────────────────────────────────────────────

@router.post("/experiment")
def create_experiment(req: ExperimentRequest) -> dict[str, Any]:
    """Create A/B experiment with alternate scoring weights."""
    engine = get_engine()
    exp_id = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO app_config (key, value, updated_at)
            VALUES (:key, :val, NOW())
            ON CONFLICT (key) DO UPDATE SET value = :val, updated_at = NOW()
        """), {
            "key": f"experiment_{exp_id}",
            "val": json.dumps({
                "id": exp_id,
                "name": req.name,
                "variant_weights": req.variant_weights.model_dump(),
                "sample_pct": req.sample_pct,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
            }),
        })

    return {
        "experiment_id": exp_id,
        "name": req.name,
        "variant_weights": req.variant_weights.model_dump(),
        "sample_pct": req.sample_pct,
        "status": "active",
    }


@router.get("/experiments")
def list_experiments() -> list[dict[str, Any]]:
    """List all scoring experiments."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT key, value FROM app_config WHERE key LIKE 'experiment_%'
            ORDER BY updated_at DESC
        """)).fetchall()

    return [json.loads(r[1]) for r in rows if r[1]]
