"""
make_synthetic_weekly.py

Build a WEEKLY SYNTHETIC activity dataset for ML development.

WHY: the Energy team provides no daily data and no multi-year history. Only 12
real monthly totals exist (data/real/real_monthly_2025.csv). That is too few
points to train or validate a forecaster, so this script spreads each real
monthly total over the days of that month and aggregates to weeks.

WHAT IS REAL: the monthly totals. Every calendar month of the daily series sums
exactly to the real monthly value (asserted below).

WHAT IS INVENTED (assumptions, not measurements - see ASSUMPTIONS):
  - the day-to-day shape inside a month (weekday/weekend ratio, random noise)
  - the random seed

Because the within-month pattern is chosen here, any model trained on this file
learns the assumptions above plus the real monthly seasonality. Its scores show
that the pipeline works; they are NOT evidence of real forecasting accuracy.

Output (never mix with real data):
  data/synthetic/weekly_synthetic.csv
  data/synthetic/weekly_synthetic_metadata.json

Usage (from repo root):
    python scripts/make_synthetic_weekly.py
"""

import json
import os

import numpy as np
import pandas as pd

REAL_FILE = "data/real/real_monthly_2025.csv"
OUT_DIR = "data/synthetic"
OUT_CSV = os.path.join(OUT_DIR, "weekly_synthetic.csv")
OUT_META = os.path.join(OUT_DIR, "weekly_synthetic_metadata.json")

SEED = 42
YEAR_START = "2025-01-01"
N_WEEKS = 52  # 52 full 7-day weeks from 1 Jan 2025; the 365th day (31 Dec) is left out

# ASSUMPTIONS - invented, not measured.
ASSUMPTIONS = {
    "electricity_weekday_weight": {"Mon-Fri": 1.0, "Sat": 0.7, "Sun": 0.5},
    "electricity_noise_lognormal_sigma": 0.08,
    "diesel_noise_lognormal_sigma": 0.6,
    "diesel_weekday_effect": "none",
}


def _allocate(month_total: float, weights: np.ndarray) -> np.ndarray:
    """Split a monthly total over days in proportion to weights."""
    return month_total * weights / weights.sum()


def build_daily(real: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    days = pd.date_range(YEAR_START, "2025-12-31", freq="D")
    daily = pd.DataFrame({"date": days})
    daily["month"] = daily["date"].dt.strftime("%Y-%m")

    wd = ASSUMPTIONS["electricity_weekday_weight"]
    dow_weight = daily["date"].dt.dayofweek.map(
        lambda d: wd["Mon-Fri"] if d < 5 else (wd["Sat"] if d == 5 else wd["Sun"])
    ).to_numpy()
    elec_w = dow_weight * rng.lognormal(
        0.0, ASSUMPTIONS["electricity_noise_lognormal_sigma"], len(daily)
    )
    dg_w = rng.lognormal(0.0, ASSUMPTIONS["diesel_noise_lognormal_sigma"], len(daily))

    daily["electricity_kwh"] = 0.0
    daily["diesel_litres"] = 0.0
    for _, row in real.iterrows():
        mask = (daily["month"] == row["month"]).to_numpy()
        daily.loc[mask, "electricity_kwh"] = _allocate(row["electricity_kwh"], elec_w[mask])
        daily.loc[mask, "diesel_litres"] = _allocate(row["dg_diesel_litres"], dg_w[mask])

    # Calibration check: daily series must reproduce the real monthly totals.
    check = daily.groupby("month")[["electricity_kwh", "diesel_litres"]].sum()
    real_i = real.set_index("month")
    assert np.allclose(check["electricity_kwh"], real_i["electricity_kwh"]), "electricity calibration failed"
    assert np.allclose(check["diesel_litres"], real_i["dg_diesel_litres"]), "diesel calibration failed"
    return daily


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.iloc[: N_WEEKS * 7].copy()
    d["week_index"] = np.arange(len(d)) // 7
    weekly = d.groupby("week_index").agg(
        week_start=("date", "min"),
        electricity_kwh=("electricity_kwh", "sum"),
        diesel_litres=("diesel_litres", "sum"),
    ).reset_index()
    weekly["electricity_kwh"] = weekly["electricity_kwh"].round(2)
    weekly["diesel_litres"] = weekly["diesel_litres"].round(2)
    weekly["is_synthetic"] = True
    return weekly


def main() -> None:
    real = pd.read_csv(REAL_FILE)
    daily = build_daily(real)
    weekly = to_weekly(daily)

    os.makedirs(OUT_DIR, exist_ok=True)
    weekly.to_csv(OUT_CSV, index=False)

    meta = {
        "label": "SYNTHETIC - calibrated to real monthly totals, NOT measured weekly data",
        "real_source": REAL_FILE,
        "seed": SEED,
        "weeks": N_WEEKS,
        "first_week_start": str(weekly["week_start"].min().date()),
        "left_out": "31 Dec 2025 (365th day does not fit in 52 full weeks)",
        "assumptions": ASSUMPTIONS,
        "real_annual_totals": {
            "electricity_kwh": int(real["electricity_kwh"].sum()),
            "dg_diesel_litres": int(real["dg_diesel_litres"].sum()),
        },
        "weekly_annual_totals": {
            "electricity_kwh": float(weekly["electricity_kwh"].sum().round(2)),
            "diesel_litres": float(weekly["diesel_litres"].sum().round(2)),
        },
    }
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Wrote {OUT_CSV} ({len(weekly)} weeks, is_synthetic=True)")
    print(f"Wrote {OUT_META}")
    print(f"Real annual electricity {meta['real_annual_totals']['electricity_kwh']} kWh vs weekly sum {meta['weekly_annual_totals']['electricity_kwh']} kWh (31 Dec left out)")


if __name__ == "__main__":
    main()
