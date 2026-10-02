import numpy as np
import pandas as pd

import make_synthetic_weekly as syn
from ml import forecast_weekly as fw


def test_synthetic_matches_real_monthly_totals():
    real = pd.read_csv(syn.REAL_FILE)
    daily = syn.build_daily(real)  # asserts calibration internally
    sums = daily.groupby("month")[["electricity_kwh", "diesel_litres"]].sum()
    assert np.allclose(sums["electricity_kwh"].to_numpy(), real["electricity_kwh"].to_numpy())
    assert np.allclose(sums["diesel_litres"].to_numpy(), real["dg_diesel_litres"].to_numpy())


def test_weekly_file_is_labelled_synthetic():
    weekly = syn.to_weekly(syn.build_daily(pd.read_csv(syn.REAL_FILE)))
    assert len(weekly) == 52
    assert weekly["is_synthetic"].all()


def test_split_is_chronological():
    df = syn.to_weekly(syn.build_daily(pd.read_csv(syn.REAL_FILE)))
    df["week_start"] = pd.to_datetime(df["week_start"])
    _, pred = fw.run_target(df, "electricity_kwh")
    feats = fw.make_features(df, "electricity_kwh").dropna()
    k = fw.time_split(len(feats))
    assert pred["week_start"].min() > df.loc[feats.index[:k], "week_start"].max()


def test_features_use_only_past():
    df = pd.DataFrame({"week_start": pd.date_range("2025-01-01", periods=10, freq="7D"),
                       "electricity_kwh": np.arange(10, dtype=float)})
    f = fw.make_features(df, "electricity_kwh")
    assert f.loc[5, "lag_1"] == 4.0
    assert f.loc[5, "roll_mean_4"] == np.mean([1, 2, 3, 4])


def test_target_is_activity_not_emission():
    assert set(fw.TARGETS) == {"electricity_kwh", "diesel_litres"}
