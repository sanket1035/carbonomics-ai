"""
make_upload_demo_csv.py

Build a DEMO weekly CSV to upload on the "Upload your data" page: electricity, rooftop solar and generator diesel
for 104 weeks (2024 and 2025). It looks like the college's data but is NOT the college's data.

WHAT COMES FROM THE REAL FILES: the shape of the year (which months use more electricity, when the generator runs,
how solar varies by month) from data/real/real_monthly_2025.csv and data/real/real_solar_monthly.csv.
WHAT IS INVENTED: the level (electricity x0.93, diesel x1.15, solar x1.10 against the real totals), a different
size for 2024, the month-to-month jitter, the weekday/weekend pattern and which days the generator runs.
Every row carries data_label = "DEMO (synthetic)". Do not present it as measured data.

The upload reads week_start, electricity_kwh and diesel_litres. solar_kwh and data_label are kept in the file but
ignored by the analysis (solar is reported separately and never netted).

Usage (repo root):  python scripts/make_upload_demo_csv.py
"""

import os

import numpy as np
import pandas as pd

REAL = "data/real/real_monthly_2025.csv"
SOLAR = "data/real/real_solar_monthly.csv"
OUT = "data/synthetic/campus_like_weekly_demo.csv"
SEED = 2026
START, END = "2024-01-01", "2025-12-28"            # Monday .. Sunday: 104 full weeks
LEVEL = {"electricity": 0.93, "diesel": 1.15, "solar": 1.10}
YEAR_SIZE = {2024: {"electricity": 1.04, "diesel": 1.30, "solar": 0.97}, 2025: {"electricity": 1.0, "diesel": 1.0, "solar": 1.0}}
DAY_SHAPE = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.98, 5: 0.82, 6: 0.70}   # Monday..Sunday, electricity only


def monthly_totals(rng: np.random.Generator) -> pd.DataFrame:
    real = pd.read_csv(REAL)
    real["m"] = real["month"].str[5:7].astype(int)
    sol = pd.read_csv(SOLAR)
    sol["m"] = sol["month"].str[5:7].astype(int)
    sol_by_m = sol.set_index("m")["solar_kwh"]
    rows = []
    for y in (2024, 2025):
        for _, r in real.iterrows():
            m = int(r["m"])
            jit = lambda s: float(rng.normal(1.0, s))  # noqa: E731
            rows.append({"year": y, "m": m,
                         "electricity": r["electricity_kwh"] * LEVEL["electricity"] * YEAR_SIZE[y]["electricity"] * jit(0.03),
                         "diesel": r["dg_diesel_litres"] * LEVEL["diesel"] * YEAR_SIZE[y]["diesel"] * jit(0.08),
                         "solar": float(sol_by_m[m]) * LEVEL["solar"] * YEAR_SIZE[y]["solar"] * jit(0.03)})
    return pd.DataFrame(rows)


def daily(rng: np.random.Generator) -> pd.DataFrame:
    tot = monthly_totals(rng).set_index(["year", "m"])
    days = pd.date_range(START, END, freq="D")
    df = pd.DataFrame({"date": days})
    df["year"], df["m"] = df["date"].dt.year, df["date"].dt.month
    for col in ("electricity", "solar", "diesel"):
        df[col] = 0.0
    for (y, m), idx in df.groupby(["year", "m"]).groups.items():
        sub = df.loc[idx]
        n = len(sub)
        full_month = pd.Period(f"{y}-{m:02d}").days_in_month
        scale = n / full_month                                   # a month cut at the end keeps its daily rate
        t = tot.loc[(y, m)]
        w = sub["date"].dt.dayofweek.map(DAY_SHAPE).to_numpy() * rng.lognormal(0, 0.03, n)
        df.loc[idx, "electricity"] = t["electricity"] * scale * w / w.sum()
        s = rng.lognormal(0, 0.15, n)
        df.loc[idx, "solar"] = t["solar"] * scale * s / s.sum()
        run_days = rng.choice(n, size=min(n, int(rng.integers(2, 5))), replace=False)   # the generator runs on a few days
        d = np.zeros(n)
        d[run_days] = rng.uniform(0.5, 1.5, len(run_days))
        df.loc[idx, "diesel"] = t["diesel"] * scale * d / d.sum()
    return df


def main() -> str:
    rng = np.random.default_rng(SEED)
    df = daily(rng)
    wk = df.set_index("date").resample("W-SUN", label="left", closed="right")[["electricity", "solar", "diesel"]].sum()
    wk.index = wk.index + pd.Timedelta(days=1)                   # week_start = Monday
    out = pd.DataFrame({"week_start": wk.index.strftime("%Y-%m-%d"),
                        "electricity_kwh": wk["electricity"].round(0).astype(int),
                        "solar_kwh": wk["solar"].round(0).astype(int),
                        "diesel_litres": wk["diesel"].round(1),
                        "data_label": "DEMO (synthetic)"})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"[Demo upload] wrote {OUT}: {len(out)} weeks, {out['week_start'].iloc[0]} to {out['week_start'].iloc[-1]}")
    return OUT


if __name__ == "__main__":
    main()
