"""S48/S49 — Win Probability ML model using LogisticRegression.

Features: match_score, value_pln, cpv_2digit, region, days_to_deadline.
Trains from offer_result table; falls back to synthetic data if insufficient.
Retrain trigger: called after each INSERT to offer_result.

Endpoint: GET /api/v2/intelligence/win-prob/{tender_id}
"""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
import threading
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy import text

logger = logging.getLogger(__name__)

_MODEL_PATH = "/tmp/terra_win_prob_lr.pkl"
_LOCK = threading.Lock()
_model = None
_cpv_encoder: dict[str, int] = {}
_region_encoder: dict[str, int] = {}
_last_trained: datetime | None = None
_train_count = 0  # offer_result rows at last train


def _encode_cpv(cpv: str | None) -> int:
    prefix = (cpv or "00")[:2]
    if prefix not in _cpv_encoder:
        _cpv_encoder[prefix] = len(_cpv_encoder)
    return _cpv_encoder[prefix]


def _encode_region(nuts: str | None) -> int:
    r = (nuts or "PL")[:4]
    if r not in _region_encoder:
        _region_encoder[r] = len(_region_encoder)
    return _region_encoder[r]


def _build_features(match_score: float, value_pln: float, cpv: str | None,
                    nuts: str | None, days_to_deadline: int) -> list[float]:
    return [
        float(match_score or 0.5),
        float(min(value_pln or 1e6, 1e9)) / 1e9,
        float(_encode_cpv(cpv)) / max(len(_cpv_encoder), 1),
        float(_encode_region(nuts)) / max(len(_region_encoder), 1),
        float(min(max(days_to_deadline, 0), 365)) / 365.0,
    ]


def _get_training_data(conn: Any) -> tuple[list, list]:
    """Fetch training data from offer_result table."""
    rows = conn.execute(
        text("""
            SELECT
                o.match_score,
                o.bid_value_pln,
                o.cpv_code,
                o.nuts_code,
                o.submitted_at,
                o.decided_at,
                o.status,
                t.match_score AS t_match_score,
                t.estimated_value_pln,
                t.cpv_codes,
                t.nuts_code AS t_nuts,
                t.deadline_at
            FROM offer_result o
            LEFT JOIN tender t ON t.id = o.tender_id
            WHERE o.status IN ('won', 'lost')
            ORDER BY o.created_at DESC
            LIMIT 1000
        """)
    ).fetchall()
    return rows, []


def _synthetic_training_data() -> tuple[list, list]:
    """Generate synthetic training data when real data is insufficient."""
    rng = np.random.RandomState(42)
    X, y = [], []
    # 20 won
    for _ in range(20):
        match_score = rng.uniform(0.6, 1.0)
        value = rng.uniform(0.1, 1.0)
        cpv_idx = rng.randint(0, 5) / 5.0
        reg_idx = rng.randint(0, 3) / 3.0
        days = rng.uniform(0.3, 1.0)
        X.append([match_score, value, cpv_idx, reg_idx, days])
        y.append(1)
    # 20 lost
    for _ in range(20):
        match_score = rng.uniform(0.0, 0.5)
        value = rng.uniform(0.0, 0.5)
        cpv_idx = rng.randint(0, 5) / 5.0
        reg_idx = rng.randint(0, 3) / 3.0
        days = rng.uniform(0.0, 0.3)
        X.append([match_score, value, cpv_idx, reg_idx, days])
        y.append(0)
    return X, y


def _train_model(conn: Any | None = None) -> None:
    """Train or retrain the LogisticRegression model."""
    global _model, _last_trained, _train_count
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
    except ImportError:
        logger.error("scikit-learn not installed, win probability ML disabled")
        return

    X, y = [], []
    if conn is not None:
        rows, _ = _get_training_data(conn)
        for r in rows:
            match_sc = float(r[7] or r[0] or 0.5)
            value = float(r[8] or r[1] or 1e6)
            cpv = (r[9] or [None])[0] if r[9] else r[2]
            nuts = r[10] or r[3]
            deadline = r[11]
            submitted = r[4]
            if deadline and submitted:
                days = max(0, (deadline.replace(tzinfo=None) - submitted.replace(tzinfo=None)).days)
            else:
                days = 30
            status = r[6]
            label = 1 if status == "won" else 0
            feats = _build_features(match_sc, value, cpv, nuts, days)
            X.append(feats)
            y.append(label)

    if len(X) < 5:
        logger.info("Insufficient real training data (%d rows), using synthetic", len(X))
        X, y = _synthetic_training_data()
        _train_count = 0
    else:
        _train_count = len(X)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=200, random_state=42)),
    ])
    pipe.fit(X, y)
    with _LOCK:
        _model = pipe
        _last_trained = datetime.now(timezone.utc)
    try:
        with open(_MODEL_PATH, "wb") as f:
            pickle.dump((pipe, _cpv_encoder, _region_encoder), f)
    except Exception as e:
        logger.warning("Could not save model: %s", e)
    logger.info("Win probability model trained on %d samples", len(X))


def _load_or_train(conn: Any | None = None) -> None:
    global _model, _cpv_encoder, _region_encoder, _last_trained
    if _model is not None:
        return
    if os.path.exists(_MODEL_PATH):
        try:
            with open(_MODEL_PATH, "rb") as f:
                obj = pickle.load(f)
                if isinstance(obj, tuple) and len(obj) == 3:
                    _model, _cpv_encoder, _region_encoder = obj
                    _last_trained = datetime.fromtimestamp(
                        os.path.getmtime(_MODEL_PATH), tz=timezone.utc
                    )
                    logger.info("Loaded existing win prob model")
                    return
        except Exception as e:
            logger.warning("Could not load model: %s", e)
    _train_model(conn)


def predict_win_prob(tender_id: str, tenant_id: str, conn: Any) -> float:
    """Predict win probability for a tender. Returns float 0-1."""
    _load_or_train(conn)
    if _model is None:
        return 0.5

    row = conn.execute(
        text("""
            SELECT match_score, estimated_value_pln, cpv_codes, nuts_code, deadline_at
            FROM tender
            WHERE id = :tid
            LIMIT 1
        """),
        {"tid": tender_id},
    ).fetchone()

    if not row:
        return 0.5

    match_score = float(row[0] or 0.5)
    value = float(row[1] or 1e6)
    cpv = (row[2] or [None])[0] if row[2] else None
    nuts = row[3]
    deadline = row[4]
    now = datetime.now(timezone.utc)
    if deadline:
        d = deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)
        days = max(0, (d - now).days)
    else:
        days = 30

    feats = [_build_features(match_score, value, cpv, nuts, days)]
    with _LOCK:
        prob = _model.predict_proba(feats)[0][1]
    return round(float(prob), 4)


def retrain_after_insert(conn: Any) -> None:
    """S49: Retrain model after new offer_result insert."""
    global _train_count
    cnt = conn.execute(
        text("SELECT COUNT(*) FROM offer_result WHERE status IN ('won','lost')")
    ).scalar() or 0
    if cnt > _train_count:
        logger.info("Retraining win prob model (new rows: %d → %d)", _train_count, cnt)
        _train_model(conn)
