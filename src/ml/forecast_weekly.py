"""
forecast_weekly.py

Weekly ACTIVITY forecasting for Carbonomics-AI.

The models predict the activity (electricity_kwh, diesel_litres), never the
emission. Emission is derived afterwards with the accounting formula
    emission = predicted activity x emission factor
using src/emission_factors.py, so there is no target leakage.

Rules followed:
  - time-based split only (first 80% of weeks train, last 20% test, no shuffle)
  - features use only past information (lags and rolling means are shifted)
  - metrics MAE, RMSE, R2, always next to two baselines:
      naive_last_week (predict previous week) and train_mean
  - input is the validated weekly file (currently SYNTHETIC); scores demonstrate the pipeline, not
    real forecasting accuracy (see scripts/make_synthetic_weekly.py)
"""

import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from emission_factors import EMISSION_FACTORS

INPUT_FILE = "data/processed/weekly_clean.csv"
OUTPUT_DIR = "outputs/forecast"
TARGETS = {
    # target column -> emission factor key
    "electricity_kwh": "electricity",
    "diesel_litres": "diesel",
}
TEST_FRACTION = 0.2
SEED = 42


def make_features(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Past-only features for one target. Row t uses weeks <= t-1 plus calendar."""
    out = pd.DataFrame(index=df.index)
    s = df[target]
    out["lag_1"] = s.shift(1)
    out["lag_2"] = s.shift(2)
    out["lag_4"] = s.shift(4)
    out["roll_mean_4"] = s.shift(1).rolling(4).mean()
    out["month"] = df["week_start"].dt.month
    out["week_of_year"] = df["week_start"].dt.isocalendar().week.astype(int)
    return out


def time_split(n_rows: int, test_fraction: float = TEST_FRACTION):
    """Chronological split point: train = [:k], test = [k:]."""
    k = int(round(n_rows * (1 - test_fraction)))
    return k


def metrics(y_true, y_pred) -> dict:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def run_target(df: pd.DataFrame, target: str):
    feats = make_features(df, target)
    data = pd.concat([df[["week_start", target]], feats], axis=1).dropna().reset_index(drop=True)
    k = time_split(len(data))
    train, test = data.iloc[:k], data.iloc[k:]
    cols = list(feats.columns)

    rows = []
    preds = {}

    preds["naive_last_week"] = test["lag_1"].to_numpy()
    preds["train_mean"] = np.full(len(test), train[target].mean())

    rf = RandomForestRegressor(n_estimators=200, random_state=SEED)
    rf.fit(train[cols], train[target])
    preds["random_forest"] = rf.predict(test[cols])

    xgb = XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=3, random_state=SEED)
    xgb.fit(train[cols], train[target])
    preds["xgboost"] = xgb.predict(test[cols])

    for name, p in preds.items():
        rows.append({"target": target, "model": name, "train_weeks": len(train),
                     "test_weeks": len(test), **metrics(test[target], p)})

    factor = EMISSION_FACTORS[TARGETS[target]]["factor"]
    pred_df = test[["week_start", target]].rename(columns={target: f"actual_{target}"}).copy()
    for name, p in preds.items():
        pred_df[f"pred_{name}"] = p
    pred_df["actual_emission_kgco2e"] = pred_df[f"actual_{target}"] * factor
    pred_df["emission_factor"] = factor
    return pd.DataFrame(rows), pred_df


def run_weekly_forecast(input_file: str = INPUT_FILE, output_dir: str = OUTPUT_DIR):
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"{input_file} not found. Run: python scripts/run_pipeline.py"
        )
    df = pd.read_csv(input_file, parse_dates=["week_start"])
    if "is_synthetic" in df.columns and df["is_synthetic"].all():
        print("[Forecast] NOTE: input is SYNTHETIC weekly data; scores demonstrate the pipeline only.")

    os.makedirs(output_dir, exist_ok=True)
    all_metrics, all_preds = [], {}
    for target in TARGETS:
        m, p = run_target(df, target)
        all_metrics.append(m)
        all_preds[target] = p
        p.to_csv(os.path.join(output_dir, f"weekly_predictions_{target}.csv"), index=False)

    metrics_df = pd.concat(all_metrics, ignore_index=True)
    metrics_df.round(4).to_csv(os.path.join(output_dir, "weekly_metrics.csv"), index=False)
    return metrics_df, all_preds


if __name__ == "__main__":
    mdf, _ = run_weekly_forecast()
    print(mdf.round(3).to_string(index=False))
