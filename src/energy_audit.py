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
    gh = next(s for s in sites if s["location"] == "Guest House")
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
        "sanity_guest_house": {
            "area_m2": guest_house_area_m2,
            "modelled_ac_kwh_per_m2": round(gh["modelled_kwh"] / guest_house_area_m2, 1),
            "corrected_ac_kwh_per_m2": {k: round(v / guest_house_area_m2, 1)
                                        for k, v in gh["corrected_kwh"].items()},
            "note": "AC electricity only, so the Guest House total EPI is higher than these figures.",
        },
        "note": ("The original sheet is left unchanged. The corrected figures depend on the ASSUMED COP "
                 "and on the same operating days and hours as the sheet, which are also unverified."),
    }


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
        "ac": _ac_block(ac, kwh, _fact(facts, "guest_house_built_up_area")),
        "caveats": [
            "No official BEE/ECBC EPI exists for educational buildings: every benchmark here is a proxy.",
            "The climate-zone mapping of the BEE bands is inferred from extracted PDF text, not checked against the original.",
            "Built-up area is the brochure figure; a larger real area would lower the EPI further.",
            "No end-use metering exists (AC, lights, fans, pumps), so no waste is claimed from this calculation.",
            "A negative gap means the campus is already below the reference, not that no saving is possible.",
        ],
    }
