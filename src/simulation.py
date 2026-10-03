"""
simulation.py

Pure-function what-if simulation for Carbonomics-AI.

Logic: Emission = Activity × Emission Factor (GHG Protocol accounting).
This is NOT machine learning; no model is trained or called here.

Baseline:  the 12 REAL monthly records from data/real/real_monthly_2025.csv.
Scenario:  user-supplied percentage changes to electricity and/or generator
           diesel, plus optional solar offset, applied uniformly to each month.

Factors are read exclusively from src/emission_factors.py (no hard-coded
numbers here).  The return dict carries factor metadata so the UI can cite
the source and version.

Coverage note: electricity + generator diesel cover ~20.5 % of the full
campus footprint of 3 719.74 tCO₂e (KKWIEER Report FY2025-26, Table 1).
Commuting and wastewater have no monthly time series and are NOT simulated.
"""

from __future__ import annotations

import sys
import os

# Allow importing from this package when run from the repo root
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd

from emission_factors import EMISSION_FACTORS, REPORT_FOOTPRINT_TCO2E, REPORT_SOURCE

# ── constants ──────────────────────────────────────────────────────────────────
_EF_ELEC = EMISSION_FACTORS["electricity"]   # kg CO2e / kWh
_EF_DSEL = EMISSION_FACTORS["diesel"]        # kg CO2e / L

# Covered sources (electricity Scope 2 + generator diesel Scope 1)
_COVERED_SOURCES = [
    "electricity_kwh   × electricity emission factor → Scope 2",
    "dg_diesel_litres  × diesel emission factor       → Scope 1",
]
_NOT_COVERED = [
    "Student commuting (≈1 896.90 tCO₂e in the report) — survey-based, no time series",
    "Domestic wastewater (≈804.17 tCO₂e) — population-based estimate",
    "College bus fleet, solid waste, refrigerant — annual figures only",
]


# ── helpers ────────────────────────────────────────────────────────────────────
def _validate_pct(value: float, name: str) -> None:
    if not (-100.0 <= value <= 100.0):
        raise ValueError(
            f"{name} must be in [-100, +100] (got {value!r})."
        )


def _validate_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0 (got {value!r}).")


def _kg_to_t(kg: float) -> float:
    return kg / 1000.0


# ── public API ─────────────────────────────────────────────────────────────────
def baseline(real_monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-month baseline emissions from the REAL monthly activity data.

    Parameters
    ----------
    real_monthly_df : DataFrame
        Must contain columns ``month``, ``electricity_kwh``, ``dg_diesel_litres``.

    Returns
    -------
    DataFrame with columns:
        month, electricity_kwh, diesel_litres,
        scope2_kg, scope1_kg, total_kg, scope2_tco2e, scope1_tco2e, total_tco2e
    """
    df = real_monthly_df[["month", "electricity_kwh", "dg_diesel_litres"]].copy()
    df = df.rename(columns={"dg_diesel_litres": "diesel_litres"})
    df["scope2_kg"] = df["electricity_kwh"] * _EF_ELEC["factor"]
    df["scope1_kg"] = df["diesel_litres"] * _EF_DSEL["factor"]
    df["total_kg"] = df["scope2_kg"] + df["scope1_kg"]
    df["scope2_tco2e"] = df["scope2_kg"] / 1000.0
    df["scope1_tco2e"] = df["scope1_kg"] / 1000.0
    df["total_tco2e"] = df["total_kg"] / 1000.0
    return df.reset_index(drop=True)


def simulate(
    real_monthly_df: pd.DataFrame,
    electricity_change_pct: float = 0.0,
    diesel_change_pct: float = 0.0,
    solar_offset_kwh_per_month: float = 0.0,
) -> dict:
    """
    Run a what-if scenario against the REAL monthly baseline.

    Parameters
    ----------
    real_monthly_df : DataFrame
        Must contain ``month``, ``electricity_kwh``, ``dg_diesel_litres``.
    electricity_change_pct : float
        Percentage change to grid electricity drawn each month (−100 to +100).
        Negative = reduction (e.g. LED retrofit), positive = increase.
    diesel_change_pct : float
        Percentage change to generator diesel consumed each month (−100 to +100).
    solar_offset_kwh_per_month : float
        Fixed kWh of solar generation per month that displaces grid electricity.
        Must be >= 0. Scenario electricity is clamped at 0 (cannot go negative).

    Returns
    -------
    dict with keys:
        baseline_monthly  : list[dict]  — per-month baseline (activity + emissions)
        scenario_monthly  : list[dict]  — per-month scenario (activity + emissions)
        annual            : dict        — baseline vs scenario annual totals + savings
        factors_used      : list[dict]  — factor metadata for UI citation
        coverage_note     : dict        — covered tCO₂e, full footprint, share, notes
        inputs            : dict        — echo of the scenario parameters
        presets_note      : str         — disclaimer for illustrative presets
    """
    # ── validate ────────────────────────────────────────────────────────────────
    _validate_pct(electricity_change_pct, "electricity_change_pct")
    _validate_pct(diesel_change_pct, "diesel_change_pct")
    _validate_non_negative(solar_offset_kwh_per_month, "solar_offset_kwh_per_month")

    # ── baseline ────────────────────────────────────────────────────────────────
    base_df = baseline(real_monthly_df)

    # ── scenario activity ───────────────────────────────────────────────────────
    scen_df = base_df.copy()
    elec_multiplier = 1.0 + electricity_change_pct / 100.0
    dsel_multiplier = 1.0 + diesel_change_pct / 100.0

    scen_df["electricity_kwh"] = (
        base_df["electricity_kwh"] * elec_multiplier - solar_offset_kwh_per_month
    ).clip(lower=0.0)
    scen_df["diesel_litres"] = (
        base_df["diesel_litres"] * dsel_multiplier
    ).clip(lower=0.0)

    # ── scenario emissions (accounting formula) ─────────────────────────────────
    scen_df["scope2_kg"] = scen_df["electricity_kwh"] * _EF_ELEC["factor"]
    scen_df["scope1_kg"] = scen_df["diesel_litres"] * _EF_DSEL["factor"]
    scen_df["total_kg"] = scen_df["scope2_kg"] + scen_df["scope1_kg"]
    scen_df["scope2_tco2e"] = scen_df["scope2_kg"] / 1000.0
    scen_df["scope1_tco2e"] = scen_df["scope1_kg"] / 1000.0
    scen_df["total_tco2e"] = scen_df["total_kg"] / 1000.0

    # ── annual totals ───────────────────────────────────────────────────────────
    def _annual(df: pd.DataFrame, prefix: str) -> dict:
        return {
            f"{prefix}_scope2_tco2e": round(float(df["scope2_tco2e"].sum()), 4),
            f"{prefix}_scope1_tco2e": round(float(df["scope1_tco2e"].sum()), 4),
            f"{prefix}_total_tco2e": round(float(df["total_tco2e"].sum()), 4),
        }

    base_ann = _annual(base_df, "baseline")
    scen_ann = _annual(scen_df, "scenario")
    saved_t = round(base_ann["baseline_total_tco2e"] - scen_ann["scenario_total_tco2e"], 4)
    base_total = base_ann["baseline_total_tco2e"]
    saved_pct = round(saved_t / base_total * 100.0, 2) if base_total else 0.0

    covered_base = base_ann["baseline_total_tco2e"]
    annual = {
        **base_ann,
        **scen_ann,
        "saved_tco2e": saved_t,
        "saved_pct": saved_pct,
        "saved_scope2_tco2e": round(
            base_ann["baseline_scope2_tco2e"] - scen_ann["scenario_scope2_tco2e"], 4
        ),
        "saved_scope1_tco2e": round(
            base_ann["baseline_scope1_tco2e"] - scen_ann["scenario_scope1_tco2e"], 4
        ),
    }

    # ── merge monthly baseline and scenario side-by-side ──────────────────────
    monthly_records = []
    for _, (b_row, s_row) in enumerate(
        zip(base_df.to_dict("records"), scen_df.to_dict("records"))
    ):
        monthly_records.append({
            "month": b_row["month"],
            # baseline
            "base_electricity_kwh": round(b_row["electricity_kwh"], 1),
            "base_diesel_litres": round(b_row["diesel_litres"], 1),
            "base_scope2_tco2e": round(b_row["scope2_tco2e"], 4),
            "base_scope1_tco2e": round(b_row["scope1_tco2e"], 4),
            "base_total_tco2e": round(b_row["total_tco2e"], 4),
            # scenario
            "scen_electricity_kwh": round(s_row["electricity_kwh"], 1),
            "scen_diesel_litres": round(s_row["diesel_litres"], 1),
            "scen_scope2_tco2e": round(s_row["scope2_tco2e"], 4),
            "scen_scope1_tco2e": round(s_row["scope1_tco2e"], 4),
            "scen_total_tco2e": round(s_row["total_tco2e"], 4),
        })

    # ── factors used (for UI citation) ─────────────────────────────────────────
    factors_used = [
        {
            "name": "electricity",
            **{k: v for k, v in _EF_ELEC.items()},
        },
        {
            "name": "diesel",
            **{k: v for k, v in _EF_DSEL.items()},
        },
    ]

    # ── coverage note ──────────────────────────────────────────────────────────
    coverage_note = {
        "covered_tco2e": round(covered_base, 2),
        "full_footprint_tco2e": REPORT_FOOTPRINT_TCO2E,
        "full_footprint_source": REPORT_SOURCE,
        "covered_share_pct": round(covered_base / REPORT_FOOTPRINT_TCO2E * 100.0, 1),
        "covered_sources": _COVERED_SOURCES,
        "not_covered": _NOT_COVERED,
        "note": (
            f"This simulation covers ~{round(covered_base / REPORT_FOOTPRINT_TCO2E * 100.0, 1)} % "
            f"of the full {REPORT_FOOTPRINT_TCO2E} tCO₂e campus footprint. "
            "Commuting and wastewater are not simulated (no time series)."
        ),
    }

    return {
        "baseline_monthly": monthly_records,
        "scenario_monthly": monthly_records,   # same list, both views embedded per row
        "monthly": monthly_records,
        "annual": annual,
        "factors_used": factors_used,
        "coverage_note": coverage_note,
        "inputs": {
            "electricity_change_pct": electricity_change_pct,
            "diesel_change_pct": diesel_change_pct,
            "solar_offset_kwh_per_month": solar_offset_kwh_per_month,
        },
        "presets_note": (
            "Any named preset (e.g. 'LED retrofit −15 %') is an ILLUSTRATIVE ASSUMPTION, "
            "not a measured result. Actual savings depend on implementation details."
        ),
    }
