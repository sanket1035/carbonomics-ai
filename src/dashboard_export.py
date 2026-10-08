"""
dashboard_export.py

Export everything the web dashboard needs into ONE static JSON file (REAL data, kept out of the public site):
    outputs/dashboard_real.json   (the public demo file is made by scripts/make_demo_data.py)

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
from optimization import load_measures, optimize as opt_optimize, budget_sweep as opt_sweep
from energy_audit import build_audit

OUT_FILE = "outputs/dashboard_real.json"   # real data: NOT in the public site; the public demo uses scripts/make_demo_data.py


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


# Default illustrative budget levels for the sweep chart (₹).
# These are round numbers for visualization only; owner should supply actual budget.
_DEFAULT_SWEEP_BUDGETS = [
    500_000, 1_000_000, 2_000_000, 5_000_000,
    10_000_000, 15_000_000, 20_000_000, 25_000_000,
]


def _build_optimization_payload(real_df, root: str = ".") -> dict:
    """
    Build the optimization section for dashboard.json.

    If all measures are TBD (no costs filled in yet), the payload is still
    valid — result=null, sweep=[], needs_input lists all measures.
    Pipeline continues without error.
    """
    measures_path = os.path.join(root, "data", "inputs", "optimization_measures.csv")
    try:
        measures = load_measures(measures_path)
    except Exception as e:
        return {
            "error": f"Could not load measures file: {e}",
            "measures": [],
            "needs_input": [],
            "result": None,
            "greedy": None,
            "budget_sweep": [],
            "factors_used": [
                {"name": "electricity", **EMISSION_FACTORS["electricity"]},
                {"name": "diesel", **EMISSION_FACTORS["diesel"]},
            ],
            "coverage_note": {},
            "assumptions": [],
            "basis": "REAL monthly baseline × emission factor; MILP (scipy.optimize.milp); not ML",
        }

    ready = [m for m in measures if m["status"] == "ready"]
    needs_input = [m for m in measures if m["status"] != "ready"]

    # Per-measure summary for the dashboard table
    measures_summary = []
    for m in measures:
        entry = {
            "id": m["id"],
            "label": m["label"],
            "category": m["category"],
            "acts_on": m["acts_on"],
            "status": m["status"],
            "missing_fields": m["missing_fields"],
            "basis": m["basis"],
            "source": m["source"],
            "source_date": m["source_date"],
            "capex_inr": m["capex_inr"],
            "max_units": m["max_units"],
            "saving_value": m["saving_value"],
            "saving_unit": m["saving_unit"],
            "notes": m["notes"],
            "impact": None,
        }
        if m["status"] == "ready":
            try:
                from optimization import measure_impact
                entry["impact"] = measure_impact(m, real_df)
            except Exception:
                pass
        measures_summary.append(entry)

    # No ready measures → skip solver
    if not ready:
        base_df = sim_baseline(real_df)
        covered = float(base_df["scope2_tco2e"].sum() + base_df["scope1_tco2e"].sum())
        return {
            "measures": measures_summary,
            "needs_input": [
                {"id": m["id"], "label": m["label"],
                 "missing_fields": m["missing_fields"], "notes": m["notes"]}
                for m in needs_input
            ],
            "result": None,
            "greedy": None,
            "budget_sweep": [],
            "factors_used": [
                {"name": "electricity", **EMISSION_FACTORS["electricity"]},
                {"name": "diesel", **EMISSION_FACTORS["diesel"]},
            ],
            "coverage_note": {
                "covered_tco2e": round(covered, 4),
                "full_footprint_tco2e": REPORT_FOOTPRINT_TCO2E,
                "covered_share_pct": round(covered / REPORT_FOOTPRINT_TCO2E * 100, 1),
            },
            "assumptions": [],
            "default_budget_inr": None,
            "basis": "REAL monthly baseline × emission factor; MILP (scipy.optimize.milp); not ML",
            "status_message": (
                "All measures need input before optimization can run. "
                "Fill in data/inputs/optimization_measures.csv and re-run the pipeline."
            ),
        }

    # Run solver at a default budget (lowest illustrative level or None)
    default_budget = _DEFAULT_SWEEP_BUDGETS[0]
    result = opt_optimize(real_df, measures, budget_inr=float(default_budget))

    # Budget sweep
    sweep = opt_sweep(real_df, measures, _DEFAULT_SWEEP_BUDGETS)

    return {
        "measures": measures_summary,
        "needs_input": [
            {"id": m["id"], "label": m["label"],
             "missing_fields": m["missing_fields"], "notes": m["notes"]}
            for m in needs_input
        ],
        "result": result,
        "greedy": result.get("greedy"),
        "budget_sweep": sweep,
        "factors_used": result.get("factors_used", []),
        "coverage_note": result.get("coverage_note", {}),
        "assumptions": result.get("assumptions", []),
        "default_budget_inr": default_budget,
        "basis": "REAL monthly baseline × emission factor; MILP (scipy.optimize.milp); not ML",
        "status_message": None,
    }


def _build_energy_audit_payload(root: str = "."):
    """Energy Audit block. None when the campus facts / AC inventory files are absent (the public demo build)."""
    needed = [os.path.join(root, "data", "real", f) for f in ("campus_facts.csv", "ac_inventory.csv")]
    if not all(os.path.exists(f) for f in needed):
        return None
    return build_audit(root)


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
        "optimization": _build_optimization_payload(real, root),
        "energy_audit": _build_energy_audit_payload(root),
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
