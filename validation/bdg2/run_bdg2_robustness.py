"""
Robustness for the BDG2 check: (a) 3 different time origins per building (full series, last 10 weeks dropped,
last 20 weeks dropped -> different held-out windows), (b) site-clustered bootstrap CI, since buildings of one site are not independent.
Reuses the same selection (secondary set: longest contiguous complete run >= 78 weeks) and repo forecast_target.
Run: python -I run_bdg2_robustness.py <bdg2_dir> <repo_dir> <out_dir>
"""
import json, sys, warnings
import numpy as np, pandas as pd
bdg_dir, repo_dir, out_dir = sys.argv[1:4]
sys.path.insert(0, f"{repo_dir}/src"); warnings.filterwarnings("ignore")
from upload_analysis import forecast_target

meta = pd.read_csv(f"{bdg_dir}/metadata.csv")
elec = pd.read_csv(f"{bdg_dir}/electricity_cleaned.csv", parse_dates=["timestamp"]).set_index("timestamp")
edu = sorted(b for b in meta[meta["primaryspaceusage"] == "Education"]["building_id"] if b in elec.columns)
first_mon = elec.index[elec.index.dayofweek == 0][0].normalize()
n_weeks = int((elec.index[-1].normalize() + pd.Timedelta(days=1) - first_mon).days // 7)
elec = elec.loc[first_mon: first_mon + pd.Timedelta(days=7 * n_weeks) - pd.Timedelta(hours=1)]
week = (elec.index - first_mon).days // 7

series = {}
for b in edu:
    s = elec[b]
    ok = (s.notna().groupby(week).sum() == 168).reindex(range(n_weeks), fill_value=False).to_numpy()
    w = s.groupby(week).sum().reindex(range(n_weeks)).to_numpy()
    best = cur = 0; end = -1
    for i, v in enumerate(ok):
        cur = cur + 1 if v else 0
        if cur > best: best, end = cur, i
    if best < 78: continue
    vals = w[end - best + 1:end + 1]
    if (vals <= 0).any(): continue
    series[b] = pd.DataFrame({"week_start": [first_mon + pd.Timedelta(days=7 * i) for i in range(end - best + 1, end + 1)], "electricity_kwh": vals})

rows = []
for b, d in sorted(series.items()):
    for drop in (0, 10, 20):
        dd = d.iloc[:len(d) - drop].reset_index(drop=True)
        r = forecast_target(dd, "electricity_kwh", 8)
        m = {x["model"]: x for x in r["metrics"]}
        cand = min(r["training"]["models"], key=lambda e: e["validation_mae"])["model"]
        rows.append({"building_id": b, "site": b.split("_")[0], "drop_last_weeks": drop, "weeks": len(dd), "test_weeks": r["test_weeks"],
                     "naive_MAE": m["naive_last_week"]["MAE"], "cand_MAE": m[cand]["MAE"], "candidate": cand,
                     "ratio": (m[cand]["MAE"] / m["naive_last_week"]["MAE"]) if m["naive_last_week"]["MAE"] > 0 else np.nan, "gate": bool(r["beats_naive"])})
df = pd.DataFrame(rows); df.round(4).to_csv(f"{out_dir}/bdg2_robustness_per_origin.csv", index=False)

rng = np.random.RandomState(42)
sites = df["site"].unique()
def boot(col_fn, B=5000):
    out = []
    for _ in range(B):
        pick = rng.choice(sites, size=len(sites), replace=True)
        out.append(col_fn(pd.concat([df[df.site == s] for s in pick])))
    return [round(float(np.percentile(out, 2.5)), 3), round(float(np.percentile(out, 97.5)), 3)]

res = {"windows_with_zero_naive_MAE_excluded_from_ratio": int(df.ratio.isna().sum()), "n_buildings": int(df.building_id.nunique()), "n_sites": int(len(sites))}
for drop in (0, 10, 20):
    x = df[df.drop_last_weeks == drop]
    res[f"origin_drop{drop}"] = {"gate_accept_frac": round(float(x.gate.mean()), 3), "median_ratio": round(float(x.ratio.median()), 3),
                                  "ratio_lt1_frac": round(float((x.ratio.dropna() < 1).mean()), 3)}
res["pooled_gate_accept_frac"] = round(float(df.gate.mean()), 3)
res["pooled_gate_accept_site_cluster_bootstrap_ci95"] = boot(lambda z: z.gate.mean())
res["pooled_median_ratio"] = round(float(df.ratio.median()), 3)
res["pooled_median_ratio_site_cluster_bootstrap_ci95"] = boot(lambda z: z.ratio.median())
# per building: how many of 3 origins accept ML
per_b = df.groupby("building_id").gate.sum()
res["buildings_accepting_in_0_1_2_3_origins"] = [int((per_b == k).sum()) for k in range(4)]
res["per_site"] = {s: {"n_buildings": int(df[df.site == s].building_id.nunique()), "gate_accept_frac": round(float(df[df.site == s].gate.mean()), 3),
                       "median_ratio": round(float(df[df.site == s].ratio.median()), 3)} for s in sorted(sites)}
json.dump(res, open(f"{out_dir}/bdg2_robustness_summary.json", "w"), indent=2)
print(json.dumps(res, indent=2))
