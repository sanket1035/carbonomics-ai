"""
External validation of the Carbonomics-AI forecasting protocol on public data (BDG2).

Data : Building Data Genome 2 (Miller et al. 2020), CC BY-SA 4.0, hourly cleaned electricity meters 2016-2017.
Method: REUSES the repo's own modules unchanged (src/upload_analysis.forecast_target, src/ml/model_selection):
        weekly series -> time-based 80/20 split -> RF / XGBoost / Ridge tuned by rolling-origin validation ->
        naive last-week baseline -> MAE, RMSE, R2 -> 5% acceptance gate.
Target: electricity_kwh (activity) only. Emission is never predicted.

Building selection (no imputation, no invented data; a week counts only if all 168 hourly readings exist):
  PRIMARY  : primaryspaceusage == 'Education' AND all 104 weeks complete AND weekly sum > 0  (rule fixed before any result).
  SECONDARY: same, but the longest contiguous run of complete weeks is used, if it is >= 78 weeks.
             Added AFTER the primary rule gave only 36 buildings (strict rule drops 94% of meters for tiny gaps);
             the primary result is reported separately and is a subset of this one.

Run: python -I run_bdg2_validation.py <bdg2_dir> <repo_dir> <out_dir>
"""
import json
import sys
import warnings

import numpy as np
import pandas as pd

bdg_dir, repo_dir, out_dir = sys.argv[1:4]
sys.path.insert(0, f"{repo_dir}/src")
warnings.filterwarnings("ignore")
from upload_analysis import forecast_target, MIN_MAE_IMPROVEMENT  # noqa: E402

meta = pd.read_csv(f"{bdg_dir}/metadata.csv")
elec = pd.read_csv(f"{bdg_dir}/electricity_cleaned.csv", parse_dates=["timestamp"]).set_index("timestamp")

edu = meta[meta["primaryspaceusage"] == "Education"]["building_id"].tolist()
edu = sorted(b for b in edu if b in elec.columns)

# complete Monday-start weeks only
first_mon = elec.index[elec.index.dayofweek == 0][0].normalize()
last_end = elec.index[-1].normalize() + pd.Timedelta(days=1)
n_weeks = int((last_end - first_mon).days // 7)
elec = elec.loc[first_mon: first_mon + pd.Timedelta(days=7 * n_weeks) - pd.Timedelta(hours=1)]
week = (elec.index - first_mon).days // 7

series, runs = {}, {}
for b in edu:
    s = elec[b]
    ok = (s.notna().groupby(week).sum() == 168).reindex(range(n_weeks), fill_value=False).to_numpy()
    w = s.groupby(week).sum().reindex(range(n_weeks)).to_numpy()
    best, cur, end = 0, 0, -1
    for i, v in enumerate(ok):
        cur = cur + 1 if v else 0
        if cur > best:
            best, end = cur, i
    if best < 78:
        continue
    lo = end - best + 1
    vals = w[lo:end + 1]
    if (vals <= 0).any():
        continue
    series[b] = pd.DataFrame({"week_start": [first_mon + pd.Timedelta(days=7 * i) for i in range(lo, end + 1)],
                              "electricity_kwh": vals})
    runs[b] = best

qual = sorted(series)
strict = sorted(b for b in qual if runs[b] == n_weeks)


def run(b):
    r = forecast_target(series[b], "electricity_kwh", 8)
    m = {x["model"]: x for x in r["metrics"]}
    naive = m["naive_last_week"]
    ml = {k: m[k] for k in ("random_forest", "xgboost", "ridge")}
    cand = min(r["training"]["models"], key=lambda e: e["validation_mae"])["model"]
    site = b.split("_")[0]
    return {"building_id": b, "site": site, "weeks": len(series[b]), "train_weeks": r["train_weeks"], "test_weeks": r["test_weeks"],
            "mean_weekly_kwh": float(series[b]["electricity_kwh"].mean()),
            "candidate_model": cand,
            "naive_MAE": naive["MAE"], "naive_RMSE": naive["RMSE"], "naive_R2": naive["R2"],
            "mean_MAE": m["train_mean"]["MAE"],
            "cand_MAE": ml[cand]["MAE"], "cand_RMSE": ml[cand]["RMSE"], "cand_R2": ml[cand]["R2"],
            "mae_ratio_cand_vs_naive": ml[cand]["MAE"] / naive["MAE"],
            "gate_accepts_ml": bool(r["beats_naive"]),
            "ml_better_than_naive_any_margin": bool(ml[cand]["MAE"] < naive["MAE"])}


rows = {b: run(b) for b in qual}
df = pd.DataFrame(rows.values())
df["in_strict_104_set"] = df["building_id"].isin(strict)
df.round(4).to_csv(f"{out_dir}/bdg2_per_building_results.csv", index=False)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def summ(d):
    n = len(d)
    g, a = int(d["gate_accepts_ml"].sum()), int(d["ml_better_than_naive_any_margin"].sum())
    ratio = d["mae_ratio_cand_vs_naive"]
    return {"n_buildings": n,
            "gate_accepts_ml": g, "gate_accepts_ml_frac": round(g / n, 3), "gate_ci95": wilson(g, n),
            "ml_better_any_margin": a, "ml_better_any_margin_frac": round(a / n, 3), "any_margin_ci95": wilson(a, n),
            "median_mae_ratio_ml_over_naive": round(float(ratio.median()), 3),
            "q25_q75_mae_ratio": [round(float(ratio.quantile(.25)), 3), round(float(ratio.quantile(.75)), 3)],
            "median_R2_naive": round(float(d["naive_R2"].median()), 3),
            "median_R2_ml_candidate": round(float(d["cand_R2"].median()), 3),
            "candidate_model_counts": d["candidate_model"].value_counts().to_dict(),
            "mean_MAE_naive_kwh": round(float(d["naive_MAE"].mean()), 1),
            "mean_MAE_ml_kwh": round(float(d["cand_MAE"].mean()), 1)}


out = {"data": "BDG2 electricity_cleaned.csv (hourly, 2016-2017), metadata.csv; CC BY-SA 4.0",
       "n_education_buildings_in_file": len(edu), "n_secondary": len(qual), "n_primary_strict": len(strict),
       "gate_min_improvement": MIN_MAE_IMPROVEMENT,
       "n_sites_secondary": int(df["site"].nunique()),
       "primary_strict_104_weeks": summ(df[df["in_strict_104_set"]]),
       "secondary_contiguous_ge78_weeks": summ(df),
       "secondary_only_extra_buildings": summ(df[~df["in_strict_104_set"]])}
json.dump(out, open(f"{out_dir}/bdg2_summary.json", "w"), indent=2)
print(json.dumps(out, indent=2))
