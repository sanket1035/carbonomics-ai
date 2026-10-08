"""
make_demo_data.py

Build the data behind the public "View Demo": a made-up campus with RANDOM, FAKE numbers.
The real KKWIEER figures are never shown on the public site.

It runs the normal weekly pipeline (accounting, forecast, QA, simulation, optimization) on a fake
monthly table in a temporary folder, so the demo behaves exactly like the real thing, then writes
dashboard/public/data/dashboard.json. Every label says the data is fake. Fixed seed, so the output is repeatable.

Usage (repo root):  python scripts/make_demo_data.py
"""
import json
import os
import re
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]
OUT = os.path.join(ROOT, "dashboard", "public", "data", "dashboard.json")
SEED = 2026
FAKE = "FAKE demo data (random numbers, not a real campus)"

# fake optimization inputs, clearly labelled; none of these come from any real quote or audit
FAKE_MEASURES = (
    "id,label,category,acts_on,saving_type,saving_value,saving_unit,cap_basis,capex_inr,annual_opex_change_inr,lifetime_years,max_units,exclusive_group,basis,source,source_date,notes\n"
    "solar_new_10kwp,New rooftop solar (per 10 kWp block),solar,electricity,fixed_kwh_per_year,14000,kWh/yr per block,total_electricity,500000,5000,25,5,,demo,FAKE demo value,demo,Made-up numbers for the demo only.\n"
    "dg_scheduling,Generator scheduling,diesel,diesel,fixed_litres_per_year,150,L/yr,total_diesel,60000,0,10,1,dg,demo,FAKE demo value,demo,Made-up numbers for the demo only.\n"
    "dg_replace,Generator replaced by battery backup (30% of diesel),diesel,diesel,pct_of_activity,0.3,% of total_diesel,total_diesel,400000,2000,10,1,dg,demo,FAKE demo value,demo,Made-up numbers for the demo only.\n"
)


def fake_monthly(rng):
    months = [f"2025-{m:02d}" for m in range(1, 13)]
    season = np.array([0.85, 0.9, 1.05, 1.15, 1.2, 1.0, 0.9, 0.9, 1.0, 1.05, 0.95, 0.9])
    kwh = (42000 * season * rng.uniform(0.94, 1.06, 12)).round()
    dsl = (rng.uniform(15, 90, 12)).round()
    solar = (1100 * np.array([1.0, 1.05, 1.2, 1.25, 1.2, 0.8, 0.7, 0.75, 0.95, 1.05, 1.0, 0.95]) * rng.uniform(0.95, 1.05, 12)).round()
    return (pd.DataFrame({"month": months, "electricity_kwh": kwh.astype(int), "dg_diesel_litres": dsl.astype(int), "source": FAKE}),
            pd.DataFrame({"month": months, "solar_kwh": solar.astype(int), "source": FAKE}))


def fake_audit_inputs(tmp):
    """FAKE built-up area and AC inventory for the demo Energy Audit page (same file layout as the real ones)."""
    facts = pd.DataFrame([
        ("built_up_area", 20000.0, "m2", "FAKE demo figure", "demo"),
        ("guest_house_built_up_area", 600.0, "m2", "FAKE demo figure", "demo"),
        ("total_persons", 4500, "persons", "FAKE demo figure", "demo"),
    ], columns=["parameter", "value", "unit", "source", "master_data_sheet"])
    rows = []
    for name, units, ton, days, hours in [("Demo block A", 8, 1.5, 290, 9), ("Demo block B", 10, 1.5, 290, 9),
                                          ("Demo guest house", 12, 1.0, 290, 12), ("Demo office", 4, 1.0, 290, 9)]:
        listed = round(ton * 3.517, 2)   # the same cooling-capacity mix-up the audit checks for
        rows.append((name, units, ton, listed, days, hours, round(units * listed * days * hours, 1), "FAKE demo figure", "demo"))
    ac = pd.DataFrame(rows, columns=["location", "units", "capacity_ton", "listed_power_per_unit_kw", "operating_days_per_year",
                                     "daily_hours", "modelled_annual_kwh", "source", "master_data_sheet"])
    facts.to_csv(os.path.join(tmp, "data/real/campus_facts.csv"), index=False)
    ac.to_csv(os.path.join(tmp, "data/real/ac_inventory.csv"), index=False)


def build(tmp):
    for d in ("data/real", "data/inputs", "data/synthetic", "data/processed", "outputs/forecast", "outputs/plots", "outputs/models"):
        os.makedirs(os.path.join(tmp, d), exist_ok=True)
    rng = np.random.default_rng(SEED)
    real, solar = fake_monthly(rng)
    real.to_csv(os.path.join(tmp, "data/real/real_monthly_2025.csv"), index=False)
    solar.to_csv(os.path.join(tmp, "data/real/real_solar_monthly.csv"), index=False)
    open(os.path.join(tmp, "data/inputs/optimization_measures.csv"), "w").write(FAKE_MEASURES)
    fake_audit_inputs(tmp)
    os.chdir(tmp)
    import make_synthetic_weekly
    from clean_data import clean_dataset
    from process_dataset import process_dataset
    from ml.forecast_weekly import emission_forecast, run_weekly_forecast
    from validation.qa_validator import generate_qa_report
    import dashboard_export as de
    make_synthetic_weekly.main()
    clean_dataset()
    process_dataset()
    _, preds = run_weekly_forecast()
    emission_forecast(preds)
    generate_qa_report()
    return de.build_payload(".")


def relabel(p):
    k = p["kpis"]
    full = round(k["covered_tco2e"] * 5, 2)       # made-up "full footprint" so the coverage donut has something to show
    share = round(k["covered_tco2e"] / full, 4)
    p["meta"].update({"campus": "Demo campus (FAKE data)", "period": "Demo year (fake)", "weekly_label": FAKE, "demo": True})
    k.update({"report_footprint_tco2e": full, "report_source": "FAKE demo figure", "covered_share_of_footprint": share,
              "basis": "FAKE monthly totals x emission factor"})
    p["not_covered"] = ["Other sources of a campus footprint (commuting, waste, wastewater, buses) are not in this demo."]
    p["solar"].update({"period": "2025-01 to 2025-12 (fake)", "basis": "FAKE monthly generation",
                       "note": "Fake rooftop solar numbers. Solar is self-consumed and reported separately, not netted from purchased electricity."})
    def walk(o):
        if isinstance(o, dict):
            if "full_footprint_tco2e" in o:
                o["full_footprint_tco2e"] = full
                o["covered_share_pct"] = round(share * 100, 1)
                if "full_footprint_source" in o:
                    o["full_footprint_source"] = "FAKE demo figure"
                if "note" in o:
                    o["note"] = f"Demo only: this covers about {share * 100:.1f} % of a made-up {full} tCO\u2082e campus footprint."
            if "not_covered" in o:
                o["not_covered"] = ["Other sources of a campus footprint (commuting, waste, wastewater, buses) are not in this demo."]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(p["simulation"])
    walk(p["optimization"])
    # the public demo has no Emission factors or Data & QA page, so their data is not shipped
    p["factors"] = []
    ea = p["energy_audit"]   # built from the FAKE area and AC inventory above; text that names the real campus is replaced
    ea["period"] = "Demo year (fake)"
    ea["basis"] = "FAKE monthly electricity / FAKE built-up area; formula only, no ML"
    ea["zone_note"] = ("The climate zone of a real site matters: the 5-star cut-off is 40 (Composite) or 45 (Warm and Humid) "
                       "kWh/m2/year. The demo uses Composite.")
    ea["actual"]["area_source"] = "FAKE demo figure"
    ea["ac"]["basis"] = "FAKE demo inventory, not metered"
    ea["ac"]["note"] = "Fake inventory. The corrected figures depend on the ASSUMED COP and on fake operating days and hours."
    p["qa"] = {"overall": "n/a", "sections": [], "markdown": ""}
    return p


REPL = [(r"KKWIEER Master Data[^\"]*", "fake demo data"), (r"K\. ?K\. Wagh[^\"]*", "Demo campus"), (r"Energy team[^\"]*", "fake demo data"),
        (r"calibrated to real monthly totals", "fake demo numbers"), (r"REAL monthly", "FAKE monthly"), (r"\bREAL\b", "FAKE"),
        (r"real monthly", "fake monthly")]


def main():
    here = os.getcwd()
    tmp = tempfile.mkdtemp()
    try:
        payload = relabel(build(tmp))
    finally:
        os.chdir(here)
        shutil.rmtree(tmp, ignore_errors=True)
    text = json.dumps(payload, indent=1, default=str)
    for pat, rep in REPL:
        text = re.sub(pat, rep, text)
    bad = [w for w in ("KKWIEER", "Wagh", "Nashik", "Master Data", "3719", "3,719", "1059147", "4100", "896.90", "804.17") if w in text]
    if bad:
        raise SystemExit(f"Real campus text left in demo data: {bad}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"[Demo] wrote {OUT} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
