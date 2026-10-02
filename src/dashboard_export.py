"""
dashboard_export.py

Export everything the web dashboard needs into ONE static JSON file:
    dashboard/public/data/dashboard.json

The dashboard (React, see dashboard/) is a static site: it only reads this file,
so it can be hosted anywhere (Vercel, Netlify, GitHub Pages) without Python.
Nothing is computed here that the pipeline did not already produce, except
annual emission from the REAL monthly totals (activity x factor).

Re-run after the pipeline:  python scripts/run_pipeline.py  (step 7 calls this)
"""

import json
import os

import pandas as pd

from emission_factors import EMISSION_FACTORS

OUT_FILE = "dashboard/public/data/dashboard.json"

# Full KKWIEER footprint for reference. Source: KKWIEER Carbon Footprint and
# Sustainability Report FY2025-26 (revised), Table 1.
REPORT_FOOTPRINT_TCO2E = 3719.74
REPORT_SOURCE = "KKWIEER Carbon Footprint and Sustainability Report FY2025-26 (revised), Table 1"


def _read(path):
    return pd.read_csv(path)


def _round(df: pd.DataFrame, nd: int = 2) -> list:
    return json.loads(df.round(nd).to_json(orient="records", date_format="iso"))


def parse_qa_report(text: str) -> dict:
    """Overall status and per-section statuses read from outputs/qa_report.md."""
    overall = "UNKNOWN"
    sections = []
    for line in text.splitlines():
        if line.startswith("**Overall:"):
            overall = "PASS" if "PASS" in line else ("FAIL" if "FAIL" in line else "UNKNOWN")
        elif line.startswith("## "):
            title = line[3:]
            status = "PASS" if title.rstrip().endswith("PASS") else ("FAIL" if title.rstrip().endswith("FAIL") else "")
            sections.append({"title": title.rsplit(":", 1)[0].lstrip("0123456789. ").strip(), "status": status})
    return {"overall": overall, "sections": sections, "markdown": text}


def build_payload(root: str = ".") -> dict:
    p = lambda *a: os.path.join(root, *a)  # noqa: E731
    real = _read(p("data", "real", "real_monthly_2025.csv"))
    weekly = _read(p("outputs", "weekly_emissions.csv"))
    ef = EMISSION_FACTORS

    real["electricity_tco2e"] = real["electricity_kwh"] * ef["electricity"]["factor"] / 1000
    real["diesel_tco2e"] = real["dg_diesel_litres"] * ef["diesel"]["factor"] / 1000
    elec_t = float(real["electricity_tco2e"].sum())
    dsl_t = float(real["diesel_tco2e"].sum())
    covered = elec_t + dsl_t

    fdir = p("outputs", "forecast")
    activity = {}
    for target in ("electricity_kwh", "diesel_litres"):
        activity[target] = _round(_read(os.path.join(fdir, f"weekly_predictions_{target}.csv")))
    metrics = _read(os.path.join(fdir, "weekly_metrics.csv"))
    em_metrics = _read(os.path.join(fdir, "weekly_emission_metrics.csv"))
    em_table = _read(os.path.join(fdir, "weekly_emission_forecast.csv"))

    beats = {}
    for target in metrics["target"].unique():
        sub = metrics[metrics["target"] == target].set_index("model")["MAE"]
        beats[target] = {m: bool(sub[m] < sub["naive_last_week"])
                         for m in sub.index if m not in ("naive_last_week", "train_mean")}

    with open(p("outputs", "qa_report.md"), encoding="utf-8") as f:
        qa = parse_qa_report(f.read())

    with open(p("data", "synthetic", "weekly_synthetic_metadata.json"), encoding="utf-8") as f:
        meta = json.load(f)

    return {
        "meta": {
            "title": "Carbonomics-AI",
            "campus": "K. K. Wagh Panchvati Campus, Nashik",
            "period": "Calendar year 2025",
            "weekly_label": meta["label"],
            "weekly_assumptions": meta["assumptions"],
            "weekly_left_out": meta["left_out"],
            "seed": meta["seed"],
        },
        "kpis": {
            "electricity_kwh": int(real["electricity_kwh"].sum()),
            "diesel_litres": int(real["dg_diesel_litres"].sum()),
            "electricity_tco2e": round(elec_t, 2),
            "diesel_tco2e": round(dsl_t, 2),
            "covered_tco2e": round(covered, 2),
            "report_footprint_tco2e": REPORT_FOOTPRINT_TCO2E,
            "report_source": REPORT_SOURCE,
            "covered_share_of_footprint": round(covered / REPORT_FOOTPRINT_TCO2E, 4),
            "basis": "REAL monthly totals x emission factor",
        },
        "real_monthly": _round(real, 3),
        "weekly": _round(weekly[["week_start", "electricity_kwh", "diesel_litres",
                                  "scope1_kg", "scope2_kg", "total_kg"]]),
        "forecast": {
            "activity": activity,
            "metrics": _round(metrics, 4),
            "emission": _round(em_table),
            "emission_metrics": _round(em_metrics, 4),
            "beats_naive": beats,
        },
        "factors": [
            {"name": k, "factor": v["factor"], "unit": v["unit"], "output": v["output"],
             "scope": v["scope"], "source": v["source"], "version": v["version"],
             "verified": v["verified"]}
            for k, v in ef.items()
        ],
        "qa": qa,
        "not_covered": [
            "Student commuting (1,896.90 tCO2e in the report) - survey based, no time series",
            "Domestic wastewater (804.17 tCO2e) - population based estimate",
            "College bus fleet, solid waste, refrigerant - annual figures only",
        ],
    }


def export_dashboard_data(root: str = ".", out_file: str = OUT_FILE) -> str:
    payload = build_payload(root)
    out = os.path.join(root, out_file)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    print(f"[Dashboard] Wrote {out}")
    return out


if __name__ == "__main__":
    export_dashboard_data()
