"""
Win Probability Estimator — computes bid win probability using quantile
statistics derived from historical market results.

Uses empirical CDF from market_results table. Falls back to a logistic
curve centered at 97.1% of estimated value when data is scarce.
"""
import logging
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from terra_db.session import get_engine

logger = logging.getLogger(__name__)

# National fallback constants (empirical median from Polish public procurement)
_NATIONAL_MEDIAN_PCT = 97.1
_FALLBACK_QUANTILES = {
    "p10": 85.0,
    "p25": 91.0,
    "p50": 97.1,
    "p75": 99.5,
    "p90": 100.8,
}


def _logistic_win_prob(offer_pct: float, center: float = _NATIONAL_MEDIAN_PCT, k: float = 0.15) -> float:
    """
    Fallback logistic curve: P(win) increases as offer_pct decreases below center.
    Lower bid → higher win probability.
    """
    x = center - offer_pct  # positive when offer is below center
    prob = 1.0 / (1.0 + np.exp(-k * x))
    return float(np.clip(prob, 0.0, 1.0))


def _fetch_ratios(cpv_prefix: str, nuts2: Optional[str] = None) -> list[float]:
    """Fetch winning_price / estimated_value ratios from market_results."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Use actual column names: winning_price_pln, estimated_value_pln, cpv_codes (array)
            if nuts2:
                rows = conn.execute(
                    text(
                        """
                        SELECT winning_price_pln, estimated_value_pln
                        FROM market_results
                        WHERE :cpv_pattern = ANY(cpv_codes)
                          AND estimated_value_pln > 0
                          AND winning_price_pln IS NOT NULL
                        """
                    ),
                    {"cpv_pattern": f"{cpv_prefix}"},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT winning_price_pln, estimated_value_pln
                        FROM market_results
                        WHERE EXISTS (
                            SELECT 1 FROM unnest(cpv_codes) c
                            WHERE c LIKE :cpv_pattern
                        )
                          AND estimated_value_pln > 0
                          AND winning_price_pln IS NOT NULL
                        LIMIT 2000
                        """
                    ),
                    {"cpv_pattern": f"{cpv_prefix}%"},
                ).fetchall()
    except SQLAlchemyError:
        logger.exception(
            "DB error fetching market ratios for CPV=%s nuts2=%s", cpv_prefix, nuts2
        )
        return []

    return [
        float(r[0]) / float(r[1])
        for r in rows
        if r[0] is not None and r[1] and float(r[1]) > 0
    ]


def compute_win_probability(
    estimated_value: float,
    cpv_prefix: str,
    nuts2: Optional[str] = None,
) -> dict:
    """
    Compute win probability statistics for a given estimated value and CPV.

    Queries market_results for historical winning_price/estimated_value ratios,
    computes quantile distribution, and derives optimal bidding range.

    Args:
        estimated_value: The project's estimated contract value.
        cpv_prefix:      CPV code prefix to filter results (e.g. '45' for construction).
        nuts2:           Optional NUTS-2 region code to narrow the sample.

    Returns:
        dict with cpv, nuts2, sample_size, quantiles, optimal_bid_pct, sweet_spot.
        Falls back to national averages when sample_size < 5.
    """
    ratios = _fetch_ratios(cpv_prefix, nuts2)
    sample_size = len(ratios)

    if sample_size < 5:
        logger.info(
            "compute_win_probability: insufficient sample (%d) for CPV=%s, using fallback",
            sample_size,
            cpv_prefix,
        )
        quantiles = _FALLBACK_QUANTILES.copy()
        optimal_bid_pct = _NATIONAL_MEDIAN_PCT
        sweet_spot = {"low": quantiles["p25"], "high": quantiles["p75"]}
    else:
        arr = np.array(ratios) * 100.0  # convert to percentages
        quantiles = {
            "p10": round(float(np.percentile(arr, 10)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p50": round(float(np.percentile(arr, 50)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "p90": round(float(np.percentile(arr, 90)), 4),
        }
        optimal_bid_pct = quantiles["p50"]
        sweet_spot = {"low": quantiles["p25"], "high": quantiles["p75"]}

    return {
        "cpv": cpv_prefix,
        "nuts2": nuts2,
        "sample_size": sample_size,
        "quantiles": quantiles,
        "optimal_bid_pct": round(optimal_bid_pct, 4),
        "sweet_spot": {
            "low": round(sweet_spot["low"], 4),
            "high": round(sweet_spot["high"], 4),
        },
    }


def estimate_win_prob(
    offer_pct: float,
    cpv_prefix: str,
    nuts2: Optional[str] = None,
) -> float:
    """
    Estimate probability of winning given offer as percentage of estimated value.

    Uses empirical CDF from historical market data. Lower offers (relative to
    estimate) correspond to higher win probability.

    Args:
        offer_pct:   offer_value / estimated_value * 100  (e.g. 95.0 = 95% of estimate)
        cpv_prefix:  CPV code prefix for market data lookup.
        nuts2:       Optional NUTS-2 region code.

    Returns:
        Float between 0.0 and 1.0 representing win probability.
    """
    ratios = _fetch_ratios(cpv_prefix, nuts2)

    if len(ratios) < 5:
        logger.info(
            "estimate_win_prob: insufficient data for CPV=%s, using logistic fallback",
            cpv_prefix,
        )
        return _logistic_win_prob(offer_pct)

    # Empirical CDF: P(win) = fraction of historical winners whose ratio >= offer_pct/100
    # (i.e. our offer is at or below the historical winning price)
    arr = np.array(ratios) * 100.0  # convert to percentages
    # Win probability: how often historical offers were >= our offer_pct
    # (lower offer → more historical winners are above → higher P(win))
    prob = float(np.mean(arr >= offer_pct))
    return round(float(np.clip(prob, 0.0, 1.0)), 4)


def get_market_benchmarks(cpv_prefix: str) -> dict:
    """
    Compute aggregate benchmarks for a CPV code prefix from market_results.

    Returns:
        dict with count, avg_ratio, median_ratio, std_ratio
        (all ratios are winning_price / estimated_value).
        Returns empty dict on error.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS cnt,
                        AVG(winning_price_pln::float / NULLIF(estimated_value_pln, 0))  AS avg_ratio,
                        STDDEV(winning_price_pln::float / NULLIF(estimated_value_pln, 0)) AS std_ratio,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY winning_price_pln::float / NULLIF(estimated_value_pln, 0)
                        ) AS median_ratio
                    FROM market_results
                    WHERE EXISTS (
                        SELECT 1 FROM unnest(cpv_codes) c WHERE c LIKE :cpv_pattern
                    )
                      AND estimated_value_pln > 0
                      AND winning_price_pln IS NOT NULL
                    """
                ),
                {"cpv_pattern": f"{cpv_prefix}%"},
            ).fetchone()
    except SQLAlchemyError:
        logger.exception("DB error fetching market benchmarks for CPV=%s", cpv_prefix)
        return {}

    if row is None or row[0] == 0:
        return {"cpv": cpv_prefix, "count": 0}

    return {
        "cpv": cpv_prefix,
        "count": int(row[0]),
        "avg_ratio": round(float(row[1]), 6) if row[1] is not None else None,
        "median_ratio": round(float(row[3]), 6) if row[3] is not None else None,
        "std_ratio": round(float(row[2]), 6) if row[2] is not None else None,
    }
