"""S63/S64/S65 — ML Scoring v2: GradientBoostingClassifier z auto-retrain."""
from __future__ import annotations

import datetime
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MLScorer:
    """Gradient Boosting scorer dla przetargów z auto-retrain po 7 nowych wynikach."""

    def __init__(self) -> None:
        self.model: Any = None
        self.trained_at: Optional[datetime.datetime] = None
        self._records_since_train: int = 0

    def _features(self, t: dict) -> list:
        return [
            float(t.get("cpv_match", 0)),
            float(t.get("value_in_range", 0)),
            float(t.get("region_match", 0)),
            float(t.get("deadline_days", 30)),
            float(t.get("title_keyword_count", 0)),
            float(t.get("historical_win_rate", 0.0)),
        ]

    def train(self, X: list, y: list) -> None:
        """Wytrenuj model na danych X, y."""
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            import numpy as np
            X_arr = np.array(X)
            y_arr = np.array(y)
            self.model = GradientBoostingClassifier(n_estimators=50)
            self.model.fit(X_arr, y_arr)
            self.trained_at = datetime.datetime.now(datetime.timezone.utc)
            self._records_since_train = 0
            logger.info("MLScorer: model wytrenowany na %d próbkach", len(y_arr))
        except ImportError:
            logger.warning("MLScorer: sklearn niedostępny, używam fallback score=0.5")

    def score_tender(self, tender_dict: dict) -> float:
        """Oblicz score dla przetargu (0.0-1.0)."""
        if self.model is None:
            return 0.5
        try:
            import numpy as np
            feat = self._features(tender_dict)
            prob = float(self.model.predict_proba(np.array([feat]))[0][1])
            return max(0.0, min(1.0, prob))
        except Exception as exc:
            logger.warning("MLScorer.score_tender error: %s", exc)
            return 0.5

    def on_new_result(self) -> None:
        """Wywołaj po każdym nowym offer_result — po 7 triggeruje retrain."""
        self._records_since_train += 1
        logger.debug("MLScorer: %d nowych wyników od ostatniego treningu", self._records_since_train)

    def retrain_from_db(self, engine: Any) -> dict:
        """S65: Pobierz offer_result, zbuduj features, wytrenuj model.

        Wywołaj po każdych 7 nowych offer_result.
        """
        try:
            import sqlalchemy as sa
            import numpy as np
        except ImportError:
            logger.warning("MLScorer.retrain_from_db: brak sklearn/sqlalchemy")
            return {"status": "skipped", "reason": "missing_deps"}

        try:
            with engine.connect() as conn:
                rows = conn.execute(sa.text("""
                    SELECT
                        or_.status,
                        or_.match_score,
                        or_.bid_value_pln,
                        or_.final_value_pln,
                        or_.cpv_code,
                        t.deadline_at,
                        t.buyer_name
                    FROM offer_result or_
                    LEFT JOIN tender t ON t.id = or_.tender_id
                    WHERE or_.status IN ('won', 'lost')
                    ORDER BY or_.created_at DESC
                    LIMIT 1000
                """)).fetchall()

            if len(rows) < 10:
                logger.info("MLScorer: za mało danych do treningu (%d wierszy)", len(rows))
                return {"status": "skipped", "reason": "insufficient_data", "rows": len(rows)}

            X = []
            y = []
            for r in rows:
                # Build features from available data
                deadline_days = 30.0
                if r.deadline_at:
                    try:
                        from datetime import date
                        now = date.today()
                        dd = r.deadline_at
                        if hasattr(dd, "date"):
                            dd = dd.date()
                        deadline_days = max(0.0, float((dd - now).days))
                    except Exception:
                        pass
                features = {
                    "cpv_match": 1.0 if r.cpv_code else 0.0,
                    "value_in_range": 1.0 if (r.bid_value_pln and 10000 < float(r.bid_value_pln) < 50_000_000) else 0.0,
                    "region_match": 0.5,  # placeholder
                    "deadline_days": deadline_days,
                    "title_keyword_count": 0.0,
                    "historical_win_rate": float(r.match_score) if r.match_score else 0.5,
                }
                X.append(self._features(features))
                y.append(1 if r.status == "won" else 0)

            self.train(X, y)
            return {
                "status": "trained",
                "samples": len(rows),
                "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            }
        except Exception as exc:
            logger.error("MLScorer.retrain_from_db error: %s", exc)
            return {"status": "error", "error": str(exc)}


# Singleton instance
_ml_scorer = MLScorer()


def get_ml_scorer() -> MLScorer:
    """Zwróć singleton ML scorer."""
    return _ml_scorer
