"""Faza 31-33 — Cost Estimation with Conformal Prediction.

Używa sklearn GradientBoostingRegressor jako fallback dla NGBoost.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# CPV benchmark — średnie wartości kontraktów na m² wg CPV (PLN)
CPV_BENCHMARKS: dict[str, dict] = {
    "45": {"label": "Roboty budowlane ogólne", "price_per_m2": 2800, "std_pct": 0.35},
    "45100": {"label": "Przygotowanie terenu", "price_per_m2": 180, "std_pct": 0.40},
    "45111": {"label": "Roboty ziemne", "price_per_m2": 210, "std_pct": 0.38},
    "45112": {"label": "Kopanie i niwelacja terenu", "price_per_m2": 195, "std_pct": 0.40},
    "45200": {"label": "Roboty budowlane", "price_per_m2": 3200, "std_pct": 0.30},
    "45210": {"label": "Kubatura", "price_per_m2": 2800, "std_pct": 0.28},
    "45221": {"label": "Mosty i wiadukty", "price_per_m2": 4500, "std_pct": 0.40},
    "45230": {"label": "Drogi i autostrady", "price_per_m2": 650, "std_pct": 0.25},
    "45231": {"label": "Sieci rurociągowe", "price_per_m2": 650, "std_pct": 0.35},
    "45233": {"label": "Drogi i chodniki", "price_per_m2": 380, "std_pct": 0.30},
    "45300": {"label": "Instalacje budowlane", "price_per_m2": 450, "std_pct": 0.30},
    "45310": {"label": "Instalacje elektryczne", "price_per_m2": 280, "std_pct": 0.22},
    "45330": {"label": "Instalacje sanitarne", "price_per_m2": 320, "std_pct": 0.24},
    "45400": {"label": "Roboty wykończeniowe", "price_per_m2": 450, "std_pct": 0.25},
}

REGION_COEFFICIENTS: dict[str, float] = {
    "mazowieckie": 1.15,
    "małopolskie": 1.05,
    "śląskie": 1.08,
    "dolnośląskie": 1.06,
    "wielkopolskie": 1.02,
    "pomorskie": 1.07,
    "łódzkie": 0.98,
    "lubelskie": 0.93,
    "podkarpackie": 0.91,
    "warmińsko-mazurskie": 0.92,
    "świętokrzyskie": 0.90,
    "opolskie": 0.96,
    "podlaskie": 0.91,
    "lubuskie": 0.95,
    "kujawsko-pomorskie": 0.97,
    "zachodniopomorskie": 1.00,
}


class CostEstimator:
    """Estymator kosztów z przedziałami ufności (conformal prediction)."""

    def __init__(self) -> None:
        self._model: Any = None
        self._calibration_residuals: list[float] = []
        self._is_trained = False

    def train(self, data: list[dict]) -> dict:
        """Trenuje model na danych historycznych.

        data: lista dicts z kluczami:
            cpv, region, area_m2, floors, value_pln (target)
        """
        if len(data) < 10:
            return {"status": "insufficient_data", "samples": len(data)}

        try:
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import LabelEncoder

            X = []
            y = []
            for d in data:
                cpv_group = (d.get("cpv", "45") or "45")[:2]
                region = d.get("region", "mazowieckie") or "mazowieckie"
                area = float(d.get("area_m2", 1000) or 1000)
                floors = float(d.get("floors", 1) or 1)
                value = float(d.get("value_pln", 0) or 0)
                if value <= 0:
                    continue
                X.append([int(cpv_group), REGION_COEFFICIENTS.get(region, 1.0), area, floors])
                y.append(value)

            if len(X) < 10:
                return {"status": "insufficient_data", "samples": len(X)}

            X_train, X_cal, y_train, y_cal = train_test_split(X, y, test_size=0.2, random_state=42)
            self._model = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
            self._model.fit(X_train, y_train)

            # Conformal calibration
            preds = self._model.predict(X_cal)
            self._calibration_residuals = sorted(
                [abs(p - t) / max(t, 1) for p, t in zip(preds, y_cal)]
            )
            self._is_trained = True
            return {"status": "trained", "samples": len(X_train), "calibration_samples": len(X_cal)}

        except Exception as e:
            logger.warning(f"Training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def predict(self, features: dict) -> dict:
        """Zwraca predykcję z przedziałem ufności 95%."""
        cpv = str(features.get("cpv", "45"))
        region = features.get("region", "mazowieckie") or "mazowieckie"
        area_m2 = float(features.get("area_m2", 1000) or 1000)
        floors = float(features.get("floors", 1) or 1)

        # Zawsze licz benchmark
        benchmark = self._get_benchmark(cpv, region, area_m2)

        if self._is_trained and self._model is not None:
            try:
                cpv_group = int(cpv[:2]) if len(cpv) >= 2 and cpv[:2].isdigit() else 45
                region_coeff = REGION_COEFFICIENTS.get(region, 1.0)
                X = [[cpv_group, region_coeff, area_m2, floors]]
                estimate = float(self._model.predict(X)[0])

                # 95% conformal interval
                q95 = self._calibration_residuals[
                    min(int(0.95 * len(self._calibration_residuals)), len(self._calibration_residuals) - 1)
                ] if self._calibration_residuals else 0.3
                low95 = estimate * (1 - q95)
                high95 = estimate * (1 + q95)

                # SHAP
                shap_values = self._compute_shap(X)

                return {
                    "estimate": round(estimate, 2),
                    "low95": round(low95, 2),
                    "high95": round(high95, 2),
                    "benchmark": benchmark,
                    "shap_values": shap_values,
                    "method": "ml",
                }
            except Exception as e:
                logger.warning(f"ML predict failed: {e}")

        # Fallback do benchmarku
        lo = round(benchmark * 0.7, 2)
        hi = round(benchmark * 1.3, 2)
        return {
            "estimate": round(benchmark, 2),
            "low95": lo,
            "high95": hi,
            "benchmark": benchmark,
            "shap_values": {},
            "method": "benchmark",
        }

    def _get_benchmark(self, cpv: str, region: str, area_m2: float) -> float:
        """Zwraca benchmark cenowy wg CPV i regionu."""
        bench = None
        for prefix_len in [5, 4, 3, 2]:
            key = cpv[:prefix_len]
            if key in CPV_BENCHMARKS:
                bench = CPV_BENCHMARKS[key]
                break
        if bench is None:
            bench = CPV_BENCHMARKS.get("45", {"price_per_m2": 2000, "std_pct": 0.40})

        region_coeff = REGION_COEFFICIENTS.get(region, 1.0)
        return bench["price_per_m2"] * area_m2 * region_coeff

    def _compute_shap(self, X: list) -> dict:
        """Oblicza SHAP values (uproszczone)."""
        try:
            import shap  # type: ignore

            explainer = shap.TreeExplainer(self._model)
            shap_vals = explainer.shap_values(X)
            feature_names = ["cpv_group", "region_coeff", "area_m2", "floors"]
            return {name: float(val) for name, val in zip(feature_names, shap_vals[0])}
        except Exception:
            return {}


# Singleton
_estimator = CostEstimator()


def get_estimator() -> CostEstimator:
    return _estimator
