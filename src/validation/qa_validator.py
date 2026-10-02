"""
qa_validator.py

Carbonomics-AI Quality Assurance module.

Every status in outputs/qa_report.md is computed from the files and functions
below; nothing is hard-coded to PASS.

Checks
  1. Data      : weekly_clean.csv structure, nulls, duplicates, negatives, dates
  2. Calibration: weekly annual totals vs the REAL monthly totals
  3. Accounting: emission == activity x factor, total == scope1+scope2, edge cases
  4. Forecast  : baselines present, chronological split, non-negative predictions
Informational (not pass/fail): whether each model beats the naive baseline.
"""

import os

import numpy as np
import pandas as pd

from calculations import calculate_diesel_emissions, calculate_electricity_emissions
from emission_factors import EMISSION_FACTORS, unverified_factors
from validator import validate_non_negative

CLEAN_FILE = "data/processed/weekly_clean.csv"
EMISSIONS_FILE = "outputs/weekly_emissions.csv"
METRICS_FILE = "outputs/forecast/weekly_metrics.csv"
PRED_DIR = "outputs/forecast"
REAL_FILE = "data/real/real_monthly_2025.csv"
OUTPUT_QA_REPORT = "outputs/qa_report.md"

ROUNDING_TOL = 0.0100001  # emissions are rounded to 0.01 kg; allow one rounding step
CALIBRATION_TOLERANCE = 0.01  # weekly total may differ from real annual by <= 1% (31 Dec left out)


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def run_data_qa(path: str = CLEAN_FILE) -> dict:
    if not os.path.exists(path):
        return {"ok": False, "error": f"{path} missing"}
    df = pd.read_csv(path, parse_dates=["week_start"])
    steps = df["week_start"].diff().dropna()
    checks = {
        "rows": len(df),
        "missing_values": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "negative_values": int((df[["electricity_kwh", "diesel_litres"]] < 0).sum().sum()),
        "weekly_7_day_steps": bool((steps == pd.Timedelta(days=7)).all()),
        "labelled_synthetic": bool("is_synthetic" in df.columns and df["is_synthetic"].all()),
    }
    checks["ok"] = (checks["missing_values"] == 0 and checks["duplicate_rows"] == 0
                    and checks["negative_values"] == 0 and checks["weekly_7_day_steps"])
    return checks


def run_calibration_qa(clean_path: str = CLEAN_FILE, real_path: str = REAL_FILE) -> dict:
    if not (os.path.exists(clean_path) and os.path.exists(real_path)):
        return {"ok": False, "error": "clean or real file missing"}
    df = pd.read_csv(clean_path)
    real = pd.read_csv(real_path)
    out, ok = {}, True
    for weekly_col, real_col in [("electricity_kwh", "electricity_kwh"), ("diesel_litres", "dg_diesel_litres")]:
        w, r = float(df[weekly_col].sum()), float(real[real_col].sum())
        rel = abs(w - r) / r
        out[weekly_col] = {"weekly_sum": round(w, 2), "real_annual": r, "relative_gap": round(rel, 5)}
        ok &= rel <= CALIBRATION_TOLERANCE
    out["ok"] = bool(ok)
    return out


def run_accounting_qa(path: str = EMISSIONS_FILE) -> dict:
    if not os.path.exists(path):
        return {"ok": False, "error": f"{path} missing"}
    df = pd.read_csv(path)
    ef = EMISSION_FACTORS
    exp_e = (df["electricity_kwh"] * ef["electricity"]["factor"]).round(2)
    exp_d = (df["diesel_litres"] * ef["diesel"]["factor"]).round(2)
    max_diff_activity = float(max((df["electricity_emission_kg"] - exp_e).abs().max(),
                                  (df["diesel_emission_kg"] - exp_d).abs().max()))
    max_diff_total = float((df["total_kg"] - (df["scope1_kg"] + df["scope2_kg"] + df["scope3_kg"])).abs().max())

    edge = True
    try:
        edge &= calculate_electricity_emissions(0.0) == 0.0
        edge &= calculate_electricity_emissions(100.0) == round(100.0 * ef["electricity"]["factor"], 2)
        edge &= calculate_diesel_emissions(100.0) == round(100.0 * ef["diesel"]["factor"], 2)
        try:
            validate_non_negative(-5.0)
            edge = False
        except ValueError:
            pass
    except Exception:
        edge = False

    return {
        "max_diff_emission_vs_formula": round(max_diff_activity, 4),
        "max_diff_total_vs_scopes": round(max_diff_total, 4),
        "edge_cases": bool(edge),
        "unverified_factors": unverified_factors(),
        "ok": bool(max_diff_activity <= ROUNDING_TOL and max_diff_total <= ROUNDING_TOL and edge),
    }


def run_forecast_qa(metrics_path: str = METRICS_FILE, clean_path: str = CLEAN_FILE) -> dict:
    if not (os.path.exists(metrics_path) and os.path.exists(clean_path)):
        return {"ok": False, "error": "metrics or clean file missing"}
    metrics = pd.read_csv(metrics_path)
    clean = pd.read_csv(clean_path, parse_dates=["week_start"])

    has_baselines = all(
        {"naive_last_week", "train_mean"} <= set(metrics[metrics["target"] == t]["model"])
        for t in metrics["target"].unique()
    )

    chronological, non_negative = True, True
    for target in metrics["target"].unique():
        p = pd.read_csv(os.path.join(PRED_DIR, f"weekly_predictions_{target}.csv"), parse_dates=["week_start"])
        n_test = len(p)
        chronological &= bool(
            p["week_start"].is_monotonic_increasing
            and list(p["week_start"]) == list(clean["week_start"].iloc[-n_test:])
        )
        pred_cols = [c for c in p.columns if c.startswith("pred_")]
        non_negative &= bool((p[pred_cols] >= 0).all().all())

    beats = {}
    for target in metrics["target"].unique():
        sub = metrics[metrics["target"] == target].set_index("model")["MAE"]
        naive = sub["naive_last_week"]
        beats[target] = {m: bool(sub[m] < naive) for m in sub.index if m not in ("naive_last_week", "train_mean")}

    return {
        "baselines_present": bool(has_baselines),
        "chronological_split": bool(chronological),
        "non_negative_predictions": bool(non_negative),
        "beats_naive_info": beats,
        "ok": bool(has_baselines and chronological and non_negative),
    }


def generate_qa_report() -> str:
    data, cal, acc, fc = run_data_qa(), run_calibration_qa(), run_accounting_qa(), run_forecast_qa()
    overall = all(r.get("ok") for r in (data, cal, acc, fc))

    lines = [
        "# Carbonomics-AI QA Report",
        "",
        "All statuses below are computed from the pipeline outputs. Data is SYNTHETIC (calibrated to real monthly totals).",
        "",
        f"**Overall: {_status(overall)}**",
        "",
        f"## 1. Weekly dataset: {_status(data.get('ok', False))}",
        "",
        f"- Rows: {data.get('rows')} | missing: {data.get('missing_values')} | duplicates: {data.get('duplicate_rows')} | negatives: {data.get('negative_values')}",
        f"- Exact 7-day week steps: {data.get('weekly_7_day_steps')} | labelled synthetic: {data.get('labelled_synthetic')}",
        "",
        f"## 2. Calibration to real monthly totals: {_status(cal.get('ok', False))}",
        "",
        f"- Tolerance {CALIBRATION_TOLERANCE:.0%} (31 Dec is not in the 52 weeks)",
    ]
    for col in ("electricity_kwh", "diesel_litres"):
        if col in cal:
            c = cal[col]
            lines.append(f"- {col}: weekly sum {c['weekly_sum']} vs real {c['real_annual']} (gap {c['relative_gap']:.3%})")
    lines += [
        "",
        f"## 3. Carbon accounting: {_status(acc.get('ok', False))}",
        "",
        f"- Max difference emission vs activity x factor: {acc.get('max_diff_emission_vs_formula')} kg",
        f"- Max difference total vs scope1+scope2+scope3: {acc.get('max_diff_total_vs_scopes')} kg",
        f"- Edge cases (zero, known sample, negative rejected): {acc.get('edge_cases')}",
        f"- Factors not yet verified against Master Data: {', '.join(acc.get('unverified_factors', [])) or 'none'}",
        "- Scope 3 and bus/refrigerant are not measured weekly and are excluded.",
        "",
        f"## 4. Forecast: {_status(fc.get('ok', False))}",
        "",
        f"- Naive and mean baselines present: {fc.get('baselines_present')}",
        f"- Test weeks are chronologically after training weeks: {fc.get('chronological_split')}",
        f"- Non-negative predictions: {fc.get('non_negative_predictions')}",
        f"- Beats naive-last-week MAE (information only): {fc.get('beats_naive_info')}",
        "",
    ]
    os.makedirs(os.path.dirname(OUTPUT_QA_REPORT), exist_ok=True)
    with open(OUTPUT_QA_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[QA Validator] Generated QA Report: '{OUTPUT_QA_REPORT}' (overall {_status(overall)})")
    return OUTPUT_QA_REPORT


if __name__ == "__main__":
    generate_qa_report()
