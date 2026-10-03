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

from emission_factors import EMISSION_FACTORS, REPORT_FOOTPRINT_TCO2E, REPORT_SOURCE
from simulation import baseline as sim_baseline, simulate

OUT_FILE = "dashboard/public/data/dashboard.json"


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


_ILLUSTRATIVE_PRESETS = [
    {
        "id": "led_retrofit",
        "label": "LED retrofit −15 %",
        "description": "Replace all fluorescent fittings with LED — ILLUSTRATIVE ASSUMPTION, not measured.",
        "electricity_change_pct": -15.0,
        "diesel_change_pct": 0.0,
        "solar_offset_kwh_per_month": 0.0,
    },
    {
        "id": "solar_100kwp",
        "label": "100 kWp rooftop solar",
        "description": "100 kWp @ 4.5 peak-sun-hours/day × 30 days ≈ 13 500 kWh/month offset, on top of the existing rooftop solar (~1,810 kWh/month real) — ILLUSTRATIVE ASSUMPTION, not measured.",
        "electricity_change_pct": 0.0,
        "diesel_change_pct": 0.0,
        "solar_offset_kwh_per_month": 13_500.0,
    },
    {
        "id": "dg_optimise",
        "label": "DG optimisation −30 %",
        "description": "Reduce generator run-time by scheduling around grid outages — ILLUSTRATIVE ASSUMPTION, not measured.",
        "electricity_change_pct": 0.0,
        "diesel_change_pct": -30.0,
        "solar_offset_kwh_per_month": 0.0,
    },
]
_PRESETS_NOTE = (
    "Presets are ILLUSTRATIVE ASSUMPTIONS only — not measured results. "
    "Actual savings depend on implementation details, equipment specifications, and site conditions."
)


def _build_simulation_payload(real_df: pd.DataFrame) -> dict:
    """Return simulation baseline + factor metadata + illustrative presets for the dashboard JSON."""
    # baseline (zero-change) result carries monthly data + coverage note + factors
    zero = simulate(real_df)
    presets = []
    for p in _ILLUSTRATIVE_PRESETS:
        result = simulate(
            real_df,
            electricity_change_pct=p["electricity_change_pct"],
            diesel_change_pct=p["diesel_change_pct"],
            solar_offset_kwh_per_month=p["solar_offset_kwh_per_month"],
        )
        presets.append({
            **p,
            "annual": result["annual"],
        })
    return {
        "baseline_monthly": zero["monthly"],
        "factors_used": zero["factors_used"],
        "coverage_note": zero["coverage_note"],
        "presets": presets,
        "presets_note": _PRESETS_NOTE,
        "basis": "REAL monthly activity × emission factor (GHG Protocol accounting, not ML)",
    }


SOLAR_NOTE = (
    "Rooftop solar is self-consumed on campus and reported separately, NOT netted: "
    "purchased grid electricity (Scope 2) stays as billed. Avoided emission = solar kWh x grid factor. "
    "Solar period is Mar 2025 - Feb 2026; electricity and diesel are Jan - Dec 2025."
)


def build_solar_payload(solar: pd.DataFrame, electricity_kwh_total: float) -> dict:
    """REAL monthly rooftop solar generation and avoided emission (not netted from Scope 2)."""
    ef = EMISSION_FACTORS["electricity"]
    solar = solar[["month", "solar_kwh"]].copy()
    solar["avoided_tco2e"] = solar["solar_kwh"] * ef["factor"] / 1000
    total_kwh = int(solar["solar_kwh"].sum())
    return {
        "monthly": _round(solar, 3),
        "annual_kwh": total_kwh,
        "avg_kwh_per_month": round(total_kwh / len(solar), 1),
        "annual_avoided_tco2e": round(float(solar["avoided_tco2e"].sum()), 2),
        "share_of_purchased_electricity": round(total_kwh / electricity_kwh_total, 4),
        "period": f"{solar['month'].iloc[0]} to {solar['month'].iloc[-1]}",
        "factor": {"name": "electricity", "factor": ef["factor"], "output": ef["output"],
                   "source": ef["source"], "version": ef["version"]},
        "note": SOLAR_NOTE,
        "basis": "REAL monthly generation (Master Data sheet 6_Solar_Monthly)",
    }


def build_payload(root: str = ".") -> dict:
    p = lambda *a: os.path.join(root, *a)  # noqa: E731
    real = _read(p("data", "real", "real_monthly_2025.csv"))
    solar = _read(p("data", "real", "real_solar_monthly.csv"))
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
        "solar": build_solar_payload(solar, float(real["electricity_kwh"].sum())),
        "simulation": _build_simulation_payload(real),
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
