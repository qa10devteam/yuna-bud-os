#!/usr/bin/env python3
"""
Retrain CostEstimator na realnych danych Atlas Przetargów.

Usage:
    python3 scripts/retrain_cost_estimator.py [--min-records 1000] [--output models/cost_estimator.pkl]

Dane: historical_tenders (PostgreSQL) — CPV 45x, z estimated_value
"""
from __future__ import annotations
import argparse, json, os, sys, time, pickle, logging
from pathlib import Path

import psycopg2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── province → NUTS-2 mapping ──────────────────────────────────────────────
NUTS2_NAME = {
    "PL21": "małopolskie",  "PL213": "małopolskie",
    "PL22": "śląskie",      "PL22A": "śląskie",
    "PL41": "wielkopolskie","PL415": "wielkopolskie",
    "PL42": "zachodniopomorskie",
    "PL43": "lubuskie",
    "PL51": "dolnośląskie", "PL514": "dolnośląskie",
    "PL52": "opolskie",
    "PL61": "kujawsko-pomorskie", "PL613": "kujawsko-pomorskie",
    "PL62": "warmińsko-mazurskie",
    "PL63": "pomorskie",    "PL633": "pomorskie",
    "PL71": "łódzkie",      "PL711": "łódzkie",
    "PL72": "świętokrzyskie",
    "PL81": "lubelskie",    "PL814": "lubelskie",
    "PL82": "podkarpackie",
    "PL84": "podlaskie",
    "PL91": "mazowieckie",  "PL911": "mazowieckie",  "PL92": "mazowieckie",
    # Stary format NUTS2
    "PL02": "dolnośląskie", "PL04": "kujawsko-pomorskie",
    "PL06": "lubelskie",    "PL08": "lubuskie",
    "PL10": "łódzkie",      "PL12": "małopolskie",
    "PL14": "mazowieckie",  "PL16": "opolskie",
    "PL18": "podkarpackie", "PL20": "podlaskie",
    "PL22": "śląskie",      "PL24": "śląskie",
    "PL26": "świętokrzyskie","PL28": "warmińsko-mazurskie",
    "PL30": "wielkopolskie","PL32": "zachodniopomorskie",
}

REGION_COEFF = {
    "mazowieckie": 1.15, "małopolskie": 1.05, "śląskie": 1.08,
    "dolnośląskie": 1.06, "wielkopolskie": 1.02, "pomorskie": 1.07,
    "łódzkie": 0.98, "lubelskie": 0.93, "podkarpackie": 0.91,
    "warmińsko-mazurskie": 0.92, "świętokrzyskie": 0.90, "opolskie": 0.96,
    "podlaskie": 0.91, "lubuskie": 0.95, "kujawsko-pomorskie": 0.97,
    "zachodniopomorskie": 1.00,
}

CPV_GROUP_MAP = {
    "45": 45, "451": 451, "452": 452, "453": 453, "454": 454,
}


def cpv_to_features(cpv_raw: str) -> tuple[int, int, int]:
    """CPV string → (group2, group3, group4). Handles '45453000-7 (Roboty...)' format."""
    if not cpv_raw:
        return 45, 450, 4500
    # Take only digits before first space, dash or paren
    import re
    m = re.match(r'(\d+)', str(cpv_raw).strip())
    digits = m.group(1) if m else ""
    g2 = int(digits[:2]) if len(digits) >= 2 else 45
    g3 = int(digits[:3]) if len(digits) >= 3 else g2 * 10
    g4 = int(digits[:4]) if len(digits) >= 4 else g3 * 10
    return g2, g3, g4


def load_data(conn, min_value: float = 10_000, max_value: float = 500_000_000) -> list[dict]:
    """Załaduj dane treningowe z PostgreSQL."""
    cur = conn.cursor()
    log.info("Querying historical_tenders for CPV 45x...")
    cur.execute("""
        SELECT id, cpv_code, province, estimated_value, offers_count,
               order_type, notice_type, date
        FROM historical_tenders
        WHERE cpv_code LIKE %(cpv_prefix)s
          AND estimated_value IS NOT NULL
          AND estimated_value BETWEEN %(min_val)s AND %(max_val)s
          AND province IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 200000
    """, {"cpv_prefix": "45%", "min_val": min_value, "max_val": max_value})
    rows = cur.fetchall()
    log.info(f"Loaded {len(rows):,} rows from DB")
    cur.close()
    return rows


def prepare_features(rows: list) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Konwertuj DB rows → X (features), y (target)."""
    X_list = []
    y_list = []
    ids = []

    for row in rows:
        id_, cpv_raw, province, value, offers_count, order_type, notice_type, date_ = row

        g2, g3, g4 = cpv_to_features(cpv_raw or "")
        region_name = NUTS2_NAME.get(province or "", "mazowieckie")
        region_coeff = REGION_COEFF.get(region_name, 1.0)
        offers = float(offers_count) if offers_count else 3.0
        year = int(str(date_)[:4]) if date_ else 2024

        # one-hot: notice_type
        is_result = 1 if notice_type and "Result" in str(notice_type) else 0
        is_works = 1 if order_type and "Roboty" in str(order_type) else 0

        X_list.append([g2, g3, g4, region_coeff, offers, year, is_result, is_works])
        y_list.append(float(value))
        ids.append(str(id_))

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.float64)
    return X, y, ids


def train_model(X: np.ndarray, y: np.ndarray) -> dict:
    """Trenuj GradientBoosting + conformal calibration."""
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_absolute_percentage_error
    import numpy as np

    log.info(f"Training on {len(X):,} samples, {X.shape[1]} features")

    # Log-transform target (rozkład prawostronny)
    y_log = np.log1p(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_log, test_size=0.15, random_state=42
    )
    X_train, X_cal, y_train_tr, y_cal = train_test_split(
        X_train, y_train, test_size=0.15, random_state=0
    )

    log.info(f"Train={len(X_train):,}, Cal={len(X_cal):,}, Test={len(X_test):,}")

    # GBR (szybszy niż NGBoost, porównywalny)
    model = GradientBoostingRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=20,
        random_state=42,
        verbose=1,
    )
    model.fit(X_train, y_train_tr)

    # Evaluate on test
    pred_test_log = model.predict(X_test)
    pred_test = np.expm1(pred_test_log)
    y_test_orig = np.expm1(y_test)
    mape = mean_absolute_percentage_error(y_test_orig, pred_test)
    log.info(f"Test MAPE: {mape:.3f} ({mape*100:.1f}%)")

    # Median APE
    ape = np.abs(pred_test - y_test_orig) / np.maximum(y_test_orig, 1)
    mdape = float(np.median(ape))
    log.info(f"Test MdAPE: {mdape:.3f} ({mdape*100:.1f}%)")

    # Conformal calibration na cal set
    pred_cal_log = model.predict(X_cal)
    pred_cal = np.expm1(pred_cal_log)
    y_cal_orig = np.expm1(y_cal)
    residuals = np.abs(pred_cal - y_cal_orig) / np.maximum(y_cal_orig, 1)
    sorted_residuals = sorted(residuals.tolist())
    q80 = sorted_residuals[int(0.80 * len(sorted_residuals))]
    q90 = sorted_residuals[int(0.90 * len(sorted_residuals))]
    q95 = sorted_residuals[int(0.95 * len(sorted_residuals))]
    log.info(f"Conformal quantiles — q80={q80:.3f}, q90={q90:.3f}, q95={q95:.3f}")

    # Feature importance
    feature_names: list[str] = ["cpv_g2", "cpv_g3", "cpv_g4", "region_coeff", "offers_count", "year", "is_result", "is_works"]
    fi: dict[str, float] = {name: float(val) for name, val in zip(feature_names, model.feature_importances_.tolist())}
    log.info(f"Feature importances: {fi}")

    return {
        "model": model,
        "calibration_residuals": sorted_residuals,
        "q80": q80, "q90": q90, "q95": q95,
        "mape": float(mape),
        "mdape": mdape,
        "n_train": len(X_train),
        "n_cal": len(X_cal),
        "n_test": len(X_test),
        "feature_importances": fi,
    }


def update_cost_estimator(result: dict, output_path: Path) -> None:
    """Zapisz wytrenowany model do pliku."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(result, f)
    log.info(f"Model saved to {output_path}")

    # Zapisz też metryki JSON
    metrics_path = output_path.with_suffix(".json")
    metrics = {k: v for k, v in result.items() if k != "model" and k != "calibration_residuals"}
    metrics["calibration_samples"] = len(result["calibration_residuals"])
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    log.info(f"Metrics saved to {metrics_path}")


def patch_estimator_source(result: dict) -> None:
    """Aktualizuj CPV_BENCHMARKS w cost_estimation.py na podstawie realnych danych."""
    # Dummy — w pełnej wersji pobierz median z DB per CPV prefix
    log.info("CPV benchmarks update skipped (patch separately)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-records", type=int, default=1000)
    parser.add_argument("--output", default="models/cost_estimator.pkl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "terraos"),
        password=os.getenv("DB_PASSWORD", "terra_dev_2026"),
        dbname=os.getenv("DB_NAME", "terraos"),
    )

    rows = load_data(conn)
    conn.close()

    if len(rows) < args.min_records:
        log.error(f"Insufficient data: {len(rows)} < {args.min_records}")
        sys.exit(1)

    log.info(f"Loaded {len(rows):,} records for training")

    X, y, ids = prepare_features(rows)
    log.info(f"Features shape: {X.shape}, target shape: {y.shape}")
    log.info(f"Target stats: min={y.min():.0f}, median={np.median(y):.0f}, max={y.max():.0f} PLN")

    if args.dry_run:
        log.info("Dry-run: skipping training")
        return

    t0 = time.time()
    result = train_model(X, y)
    elapsed = time.time() - t0
    log.info(f"Training completed in {elapsed:.1f}s")
    log.info(f"MAPE={result['mape']*100:.1f}%, MdAPE={result['mdape']*100:.1f}%")
    log.info(f"95% CI width: ±{result['q95']*100:.1f}%")

    output_path = Path(args.output)
    update_cost_estimator(result, output_path)

    print(f"\n{'='*50}")
    print(f"Training complete!")
    print(f"  Records: {len(rows):,}")
    print(f"  MAPE:    {result['mape']*100:.1f}%")
    print(f"  MdAPE:   {result['mdape']*100:.1f}%")
    print(f"  95% CI:  ±{result['q95']*100:.1f}%")
    print(f"  Model:   {output_path}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
