"""
energy_audit.py

Energy Audit calculation for Carbonomics-AI (formula only, no machine learning).

What it does
    1. Actual campus electricity EPI = annual kWh / built-up area (kWh per m2 per year).
    2. Compares it with the documented benchmarks in benchmarks.py:
           target kWh   = benchmark EPI x built-up area
           target tCO2e = target kWh x grid factor (emission_factors.py)
           gap          = actual - target   (NEGATIVE = campus already below the target)
    3. Re-estimates the air-conditioning load. Sheet 4_AC_Inventory of the Master Data lists
       5.27 kW per 1.5-ton and 3.5 kW per 1-ton AC. Those are the COOLING capacity (1 ton of
       refrigeration = 3.517 kW thermal), not the electrical input. Electrical input is roughly
       cooling capacity / COP. The COP below is an ASSUMPTION, shown as a range, until nameplate
       ratings (rated input kW or ISEER) are collected. The original sheet is not changed.

    4. Builds the suggestion list (data/inputs/energy_audit_suggestions.csv). Every suggestion carries
       its source, date and scope. A campus number is computed ONLY where the campus has data (the AC
       levers, the generator, the solar share); everything else shows the published typical saving as
       text and says what data would turn it into a number.

What it does NOT do
    No end-use metering exists (AC, lights, fans, pumps are not metered), so no "waste" is claimed
    here. Savings per measure are added later, each with its own source / assumption label.

Inputs: data/real/real_monthly_2025.csv, data/real/campus_facts.csv, data/real/ac_inventory.csv
        (the last two are copied from the KKWIEER Master Data FY2025-26 workbook).
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from benchmarks import (  # noqa: E402
    BENCHMARK_UNIT, DEFAULT_ZONE, ZONE_NOTE, benchmark_list, star_rating,
)
from emission_factors import EMISSION_FACTORS  # noqa: E402

# 1 ton of refrigeration = 12,000 BTU/h = 3.517 kW of cooling (thermal, not electrical).
TON_REFRIGERATION_KW_THERMAL = 3.517

# ASSUMED COP range (no source: replace with nameplate rated input power / ISEER when collected).
ASSUMED_COP = {"low": 2.5, "central": 3.0, "high": 4.0}
COP_LABEL = ("ASSUMED coefficient of performance (cooling kW per electrical kW). Not from a source; "
             "replace with nameplate rated input power or ISEER once collected.")


def _fact(facts: pd.DataFrame, name: str) -> float:
    row = facts.loc[facts["parameter"] == name]
    if row.empty:
        raise KeyError(f"campus_facts.csv has no parameter '{name}'")
    return float(row["value"].iloc[0])


def _ac_block(ac: pd.DataFrame, total_kwh: float, guest_house_area_m2: float) -> dict:
    ef = EMISSION_FACTORS["electricity"]["factor"]
    sites = []
    for _, r in ac.iterrows():
        thermal_kw = r["capacity_ton"] * TON_REFRIGERATION_KW_THERMAL
        hours = r["units"] * r["operating_days_per_year"] * r["daily_hours"]
        site = {
            "location": r["location"],
            "units": int(r["units"]),
            "capacity_ton": float(r["capacity_ton"]),
            "listed_power_per_unit_kw": float(r["listed_power_per_unit_kw"]),
            "cooling_capacity_per_unit_kw": round(thermal_kw, 3),
            "listed_equals_cooling_capacity": bool(abs(r["listed_power_per_unit_kw"] / thermal_kw - 1) < 0.01),
            "modelled_kwh": float(r["modelled_annual_kwh"]),
            "corrected_kwh": {k: round(hours * thermal_kw / cop, 1) for k, cop in ASSUMED_COP.items()},
        }
        sites.append(site)
    modelled = sum(s["modelled_kwh"] for s in sites)
    corrected = {k: round(sum(s["corrected_kwh"][k] for s in sites), 1) for k in ASSUMED_COP}
    gh = next((s for s in sites if "guest house" in s["location"].lower()), None)
    return {
        "basis": "MODELLED (Master Data sheet 4_AC_Inventory), not metered",
        "units_total": sum(s["units"] for s in sites),
        "sites": sites,
        "modelled_kwh": round(modelled, 1),
        "modelled_share_of_purchased": round(modelled / total_kwh, 4),
        "listed_kw_is_cooling_capacity": all(s["listed_equals_cooling_capacity"] for s in sites),
        "ton_of_refrigeration_kw_thermal": TON_REFRIGERATION_KW_THERMAL,
        "assumed_cop": ASSUMED_COP,
        "cop_label": COP_LABEL,
        "corrected_kwh": corrected,
        "corrected_tco2e": {k: round(v * ef / 1000, 2) for k, v in corrected.items()},
        "corrected_share_of_purchased": {k: round(v / total_kwh, 4) for k, v in corrected.items()},
        "sanity_guest_house": None if gh is None else {
            "location": gh["location"],
            "area_m2": guest_house_area_m2,
            "modelled_ac_kwh_per_m2": round(gh["modelled_kwh"] / guest_house_area_m2, 1),
            "corrected_ac_kwh_per_m2": {k: round(v / guest_house_area_m2, 1)
                                        for k, v in gh["corrected_kwh"].items()},
            "note": "AC electricity only, so the guest house total EPI is higher than these figures.",
        },
        "note": ("The original sheet is left unchanged. The corrected figures depend on the ASSUMED COP "
                 "and on the same operating days and hours as the sheet, which are also unverified."),
    }


def _n(x, d=0) -> str:
    return f"{x:,.{d}f}"


def load_suggestions(root: str = ".") -> pd.DataFrame:
    df = pd.read_csv(os.path.join(root, "data", "inputs", "energy_audit_suggestions.csv"), keep_default_na=False)
    return df.sort_values("priority").reset_index(drop=True)


def _ac_levers(ac_block: dict, pct_per_degc: float, ef: float) -> dict:
    """AC lever numbers from the corrected AC estimate (ASSUMED COP). Sites are sorted by corrected kWh, largest first."""
    base = ac_block["corrected_kwh"]
    sites = sorted(ac_block["sites"], key=lambda s: -s["corrected_kwh"]["central"])
    return {"sites": sites, "setpoint_kwh": {k: round(v * pct_per_degc, 1) for k, v in base.items()},
            "setpoint_tco2e": {k: round(v * pct_per_degc * ef / 1000, 2) for k, v in base.items()}}


def build_suggestions(root: str, ac_block: dict, ac_df: pd.DataFrame, real: pd.DataFrame, facts: pd.DataFrame,
                      kwh: float, area: float) -> list:
    ef = EMISSION_FACTORS["electricity"]["factor"]
    ef_dsl = EMISSION_FACTORS["diesel"]["factor"]
    df = load_suggestions(root)
    hours_by_site = {r["location"]: float(r["daily_hours"]) for _, r in ac_df.iterrows()}
    lev = _ac_levers(ac_block, float(df.loc[df["id"] == "ac_setpoint", "typical_saving_pct"].iloc[0] or 0), ef)
    sites = lev["sites"]
    total_t_elec = kwh * ef / 1000
    ac_c = ac_block["corrected_kwh"]
    out = []
    for _, r in df.iterrows():
        evidence, numbers = [], None
        key = r["evidence_key"]
        if key == "ac_setpoint":
            sp = lev["setpoint_kwh"]
            numbers = {"label": "Raise setpoint by 1 degC", "kwh_low": sp["high"], "kwh_central": sp["central"], "kwh_high": sp["low"],
                       "tco2e_central": lev["setpoint_tco2e"]["central"],
                       "note": "Six percent of the corrected AC estimate; the AC estimate itself uses an ASSUMED COP"}
            evidence.append(f"Corrected AC estimate: {_n(ac_c['central'])} kWh a year ({_n(ac_c['high'])} to {_n(ac_c['low'])} kWh for COP {ASSUMED_COP['high']} to {ASSUMED_COP['low']}), about {_n(ac_block['corrected_share_of_purchased']['central'] * 100)}% of purchased electricity.")
        elif key in ("ac_hours_top", "ac_hours_second"):
            idx = 0 if key == "ac_hours_top" else 1
            if len(sites) > idx:
                st = sites[idx]
                h = hours_by_site.get(st["location"], 0) or 1
                per_h = {k: round(v / h, 1) for k, v in st["corrected_kwh"].items()}
                numbers = {"label": f"{st['location']}: 1 hour a day less AC", "kwh_low": per_h["high"], "kwh_central": per_h["central"], "kwh_high": per_h["low"],
                           "tco2e_central": round(per_h["central"] * ef / 1000, 2),
                           "note": "Formula on the listed days and hours and the ASSUMED COP"}
                evidence.append(f"{st['location']}: {st['units']} units, {_n(h)} hours a day listed, {_n(st['corrected_kwh']['central'])} kWh a year (corrected estimate, {_n(st['corrected_kwh']['central'] / ac_c['central'] * 100)}% of campus AC).")
        elif key == "sensors":
            row = facts.loc[facts["parameter"] == "hostel_built_up_area"]
            if not row.empty:
                ha = float(row["value"].iloc[0])
                evidence.append(f"Hostel and mess floor area is {_n(ha)} m2, {_n(ha / area * 100)}% of the campus built-up area.")
        elif key == "dg":
            dsl = float(real["dg_diesel_litres"].sum())
            top = real.loc[real["dg_diesel_litres"].idxmax()]
            t = dsl * ef_dsl / 1000
            evidence.append(f"Generator diesel: {_n(dsl)} litres a year = {_n(t, 2)} tCO2e, only {_n(t / total_t_elec * 100, 1)}% of the electricity emissions. Highest month: {top['month']} with {_n(float(top['dg_diesel_litres']))} litres.")
        elif key == "solar":
            sp_path = os.path.join(root, "data", "real", "real_solar_monthly.csv")
            if os.path.exists(sp_path):
                sk = float(pd.read_csv(sp_path)["solar_kwh"].sum())
                evidence.append(f"Existing rooftop solar generated {_n(sk)} kWh in the last 12 months, {_n(sk / kwh * 100, 1)}% of purchased electricity. It is reported separately and not subtracted from the purchased total.")
        elif key == "submeter":
            evidence.append(f"Only the AC load can be estimated, about {_n(ac_c['central'] / kwh * 100)}% of purchased electricity. The other {_n(100 - ac_c['central'] / kwh * 100)}% has no end-use split.")
        out.append({
            "id": r["id"], "priority": int(r["priority"]), "group": r["group"], "title": r["title"], "where": r["where"],
            "why": r["why"], "status": r["status"], "typical_saving": r["typical_saving"],
            "typical_saving_pct": float(r["typical_saving_pct"]) if str(r["typical_saving_pct"]).strip() else None,
            "saving_source": r["saving_source"], "source_date": r["source_date"], "evidence_scope": r["evidence_scope"],
            "needs": r["needs"], "campus_evidence": evidence, "campus_number": numbers,
        })
    return out


def build_audit(root: str = ".", zone: str = DEFAULT_ZONE) -> dict:
    p = lambda *a: os.path.join(root, *a)  # noqa: E731
    real = pd.read_csv(p("data", "real", "real_monthly_2025.csv"))
    facts = pd.read_csv(p("data", "real", "campus_facts.csv"))
    ac = pd.read_csv(p("data", "real", "ac_inventory.csv"))

    ef = EMISSION_FACTORS["electricity"]
    kwh = float(real["electricity_kwh"].sum())
    area = _fact(facts, "built_up_area")
    persons = _fact(facts, "total_persons")
    actual_t = kwh * ef["factor"] / 1000
    epi = kwh / area

    ac_block = _ac_block(ac, kwh, _fact(facts, "guest_house_built_up_area"))
    references = []
    for b in benchmark_list(zone):
        target_kwh = b["value"] * area
        target_t = target_kwh * ef["factor"] / 1000
        references.append({
            "key": b["key"], "label": b["label"], "role": b["role"],
            "benchmark_epi": b["value"], "unit": b["unit"],
            "source": b["source"], "version": b["version"], "basis": b["basis"], "verified": b["verified"],
            "target_kwh": round(target_kwh, 1),
            "target_tco2e": round(target_t, 2),
            "gap_kwh": round(kwh - target_kwh, 1),
            "gap_tco2e": round(actual_t - target_t, 2),
            "position": "below_target" if kwh <= target_kwh else "above_target",
        })

    return {
        "period": "Calendar year 2025",
        "basis": "REAL monthly electricity (Energy team log) / built-up area; formula only, no ML",
        "zone": zone,
        "zone_note": ZONE_NOTE,
        "actual": {
            "electricity_kwh": round(kwh, 1),
            "electricity_tco2e": round(actual_t, 2),
            "grid_factor": ef["factor"], "grid_factor_unit": ef["output"],
            "grid_factor_source": f"{ef['source']}, {ef['version']}",
            "built_up_area_m2": area,
            "area_source": "Admission Brochure 2024-25 (Master Data sheet 15_Campus_Infrastructure)",
            "epi": round(epi, 2), "epi_unit": BENCHMARK_UNIT,
            "persons": int(persons),
            "kwh_per_person": round(kwh / persons, 1),
            "proxy_star_rating": star_rating(epi, zone),
        },
        "references": references,
        "ac": ac_block,
        "suggestions": build_suggestions(root, ac_block, ac, real, facts, kwh, area),
        "caveats": [
            "No official BEE/ECBC EPI exists for educational buildings: every benchmark here is a proxy.",
            "The climate-zone mapping of the BEE bands is inferred from extracted PDF text, not checked against the original.",
            "Built-up area is the brochure figure; a larger real area would lower the EPI further.",
            "No end-use metering exists (AC, lights, fans, pumps), so no waste is claimed from this calculation.",
            "A negative gap means the campus is already below the reference, not that no saving is possible.",
        ],
    }
