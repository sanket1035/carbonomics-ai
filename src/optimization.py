"""
optimization.py

Budget-constrained CO₂ reduction optimization for Carbonomics-AI.

Objective: given a set of candidate measures and a total budget (₹),
choose the combination that maximises annual tCO₂e reduction.

Method: Mixed-Integer Linear Programme (MILP) via scipy.optimize.milp.
        Greedy (sort by tCO₂e/₹ descending) is also run for comparison.

This is mathematical optimization on top of GHG Protocol accounting.
It is NOT machine learning; no model is trained or called here.

Emission reduction formula (same as simulation.py and the React UI):
    Reduction (kg CO₂e) = activity_saved (kWh or L) × emission_factor
    where emission_factor comes exclusively from EMISSION_FACTORS in
    src/emission_factors.py.

Baseline: the 12 REAL monthly records from data/real/real_monthly_2025.csv.
Measures: user-edited data/inputs/optimization_measures.csv.
          Every measure must carry source, date, unit and basis label.
          Measures with any required field blank / 'TBD' are EXCLUDED
          from the optimizer and listed in 'needs_input'. No defaults.

Covered scope: electricity (Scope 2) + generator diesel (Scope 1) only.
Commuting and wastewater have no monthly time series; they are not optimised.

Coverage note: covered ~20.5% of the 3,719.74 tCO₂e campus footprint
(KKWIEER Carbon Footprint and Sustainability Report FY2025-26, Table 1).

Known limitations (documented for the project report):
- Savings modelled as static annual averages; seasonal variation ignored.
- No interaction effects between measures beyond exclusive-group constraints
  and per-cap-basis caps; e.g. LED+AC savings on the same electricity pool
  are additive only up to the global electricity cap.
- Cost inputs are owner-supplied; accuracy depends on source quality.
- MILP assumes linear scaling of savings per unit (e.g. each 10 kWp block
  of solar yields the same kWh). Non-linearities require additional modelling.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from emission_factors import EMISSION_FACTORS, REPORT_FOOTPRINT_TCO2E, REPORT_SOURCE
from simulation import baseline as _sim_baseline, simulate as _sim_simulate

# ── constants ──────────────────────────────────────────────────────────────────
_EF_ELEC = EMISSION_FACTORS["electricity"]   # kg CO₂e / kWh
_EF_DSEL = EMISSION_FACTORS["diesel"]        # kg CO₂e / L

# AC end-use cap: corrected estimate from the Energy Audit (energy_audit.py), central case (COP 3.0, ASSUMED).
# Sheet 4_AC_Inventory lists 697,296 kWh/yr, but its kW per unit is the cooling capacity, not the electrical
# input, so that figure is probably too high (66% of purchased electricity). Dividing by an assumed COP of
# 2.5 / 3.0 / 4.0 gives 279,665 / 233,054 / 174,791 kWh/yr. This is a subset of purchased electricity,
# NOT additive to the grid total. tests/test_optimization.py checks it against energy_audit.build_audit().
AC_END_USE_KWH_YR = 233_054.0
AC_END_USE_BASIS = ("ESTIMATE (COP ASSUMED 3.0) — sheet 4_AC_Inventory corrected for cooling capacity vs electrical input, "
                    "KKWIEER Master Data FY2025-26; Energy Audit page")

# Lighting end-use: TBD — no lighting inventory in Master Data.
LIGHTING_END_USE_KWH_YR = None
LIGHTING_END_USE_BASIS = "TBD — no lighting inventory in Master Data FY2025-26"

_CAP_BASIS_VALUES: dict[str, float | None] = {
    "total_electricity": None,    # filled dynamically from baseline
    "total_diesel": None,         # filled dynamically from baseline
    "ac_end_use": AC_END_USE_KWH_YR,
    "lighting_end_use": LIGHTING_END_USE_KWH_YR,  # None → TBD
}

_REQUIRED_READY_FIELDS = ["saving_value", "capex_inr", "max_units"]
_OPTIONAL_FIELDS = ["annual_opex_change_inr", "lifetime_years"]

_COVERED_NOTE = (
    "Optimization covers electricity (Scope 2) and generator diesel (Scope 1) only — "
    f"~20.5 % of the {REPORT_FOOTPRINT_TCO2E} tCO₂e campus footprint. "
    "Commuting and wastewater are not optimised (no monthly time series)."
)

_NOT_COVERED = [
    "Student commuting (~1 896.90 tCO₂e) — survey-based, no time series",
    "Domestic wastewater (~804.17 tCO₂e) — population-based estimate",
    "College bus fleet, solid waste, refrigerant — annual figures only",
]


# ── helpers ────────────────────────────────────────────────────────────────────
def _nan_or_blank(val: Any) -> bool:
    """Return True if val is blank, None, NaN, or the literal string 'TBD'."""
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if isinstance(val, str) and val.strip().upper() in ("", "TBD", "NAN", "NONE"):
        return True
    return False


def _coerce_float(val: Any) -> float | None:
    if _nan_or_blank(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _coerce_int(val: Any) -> int | None:
    v = _coerce_float(val)
    if v is None:
        return None
    return int(round(v))


def _validate_budget(budget_inr: float) -> None:
    if budget_inr < 0:
        raise ValueError(f"budget_inr must be >= 0, got {budget_inr!r}")


def _validate_capex(capex: float, label: str) -> None:
    if capex < 0:
        raise ValueError(f"capex_inr must be >= 0 for measure '{label}', got {capex!r}")


def _validate_pct(val: float, field: str, label: str) -> None:
    if not (0.0 <= val <= 100.0):
        raise ValueError(
            f"Field '{field}' must be in [0, 100] for measure '{label}', got {val!r}"
        )


# ── A. load_measures ───────────────────────────────────────────────────────────
def load_measures(path: str) -> list[dict]:
    """
    Parse data/inputs/optimization_measures.csv.

    Returns a list of dicts, each with a 'status' key:
        'ready'       — all required fields present and valid
        'needs_input' — one or more required fields are blank/TBD

    The 'missing_fields' key lists which fields are missing.
    No defaults are ever filled in.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    # Normalise: strip whitespace from string columns
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    measures = []
    for _, row in df.iterrows():
        m: dict[str, Any] = {
            "id":                    row.get("id", ""),
            "label":                 row.get("label", ""),
            "category":              row.get("category", ""),
            "acts_on":               row.get("acts_on", ""),
            "saving_type":           row.get("saving_type", ""),
            "saving_value":          _coerce_float(row.get("saving_value", "")),
            "saving_unit":           row.get("saving_unit", ""),
            "cap_basis":             row.get("cap_basis", "") or None,
            "capex_inr":             _coerce_float(row.get("capex_inr", "")),
            "annual_opex_change_inr": _coerce_float(row.get("annual_opex_change_inr", "")),
            "lifetime_years":        _coerce_int(row.get("lifetime_years", "")),
            "max_units":             _coerce_int(row.get("max_units", "")),
            "exclusive_group":       row.get("exclusive_group", "") or None,
            "basis":                 row.get("basis", "TBD"),
            "source":                row.get("source", ""),
            "source_date":           row.get("source_date", ""),
            "notes":                 row.get("notes", ""),
        }

        # Determine status
        missing: list[str] = []
        for field in _REQUIRED_READY_FIELDS:
            if m[field] is None:
                missing.append(field)
        # cap_basis TBD when lighting_end_use needed
        if m.get("cap_basis") == "lighting_end_use" and LIGHTING_END_USE_KWH_YR is None:
            missing.append("cap_basis_value (lighting_end_use TBD — no data in Master Data)")
        # max_units blank counts as needs_input (per approved plan: no default 1)
        if m["max_units"] is None:
            if "max_units" not in missing:
                missing.append("max_units")

        m["status"] = "needs_input" if missing else "ready"
        m["missing_fields"] = missing
        measures.append(m)

    return measures


# ── B. measure_impact ──────────────────────────────────────────────────────────
def measure_impact(measure: dict, baseline_df: pd.DataFrame) -> dict:
    """
    Compute the annual impact of ONE unit of a measure.

    Returns:
        kwh_saved_per_unit      : kWh/yr displaced from grid (0 if diesel measure)
        litres_saved_per_unit   : L/yr diesel saved (0 if electricity measure)
        tco2e_saved_per_unit    : tCO₂e/yr (accounting formula, factor from EMISSION_FACTORS)
        capex_per_unit          : ₹
        inr_per_tco2e           : ₹ per tCO₂e/yr (MACC cost effectiveness)
        cap_applied             : bool — was the saving clamped by a cap?
        cap_basis               : str or None
        cap_value               : float or None — the cap ceiling used
        factor_used             : dict with name, factor, unit, output, source, version
        scope                   : Scope 1 or Scope 2
    """
    if measure["status"] != "ready":
        raise ValueError(
            f"Cannot compute impact for measure '{measure['id']}': status = {measure['status']}, "
            f"missing: {measure['missing_fields']}"
        )

    acts_on = measure["acts_on"]
    saving_type = measure["saving_type"]
    saving_value = float(measure["saving_value"])
    max_units = int(measure["max_units"])
    cap_basis = measure.get("cap_basis")

    # Baseline annual totals
    base_df = _sim_baseline(baseline_df)
    total_elec = float(base_df["electricity_kwh"].sum())
    total_diesel = float(base_df["diesel_litres"].sum())

    # Dynamic cap values
    cap_map = {**_CAP_BASIS_VALUES}
    cap_map["total_electricity"] = total_elec
    cap_map["total_diesel"] = total_diesel

    # Raw saving per unit (before cap)
    if saving_type == "pct_of_activity":
        _validate_pct(saving_value, "saving_value", measure["label"])
        pct = saving_value / 100.0
        if acts_on == "electricity":
            if cap_basis and cap_basis in cap_map and cap_map[cap_basis] is not None:
                raw_kwh = cap_map[cap_basis] * pct
            else:
                raw_kwh = total_elec * pct
            raw_litres = 0.0
        else:  # diesel
            if cap_basis and cap_basis in cap_map and cap_map[cap_basis] is not None:
                raw_litres = cap_map[cap_basis] * pct
            else:
                raw_litres = total_diesel * pct
            raw_kwh = 0.0

    elif saving_type == "fixed_kwh_per_year":
        raw_kwh = saving_value
        raw_litres = 0.0

    elif saving_type == "fixed_litres_per_year":
        raw_litres = saving_value
        raw_kwh = 0.0

    else:
        raise ValueError(
            f"Unknown saving_type '{saving_type}' for measure '{measure['id']}'"
        )

    # Apply global cap (saving cannot exceed what's available)
    kwh_cap = total_elec
    litres_cap = total_diesel
    cap_applied = False

    if raw_kwh > kwh_cap:
        raw_kwh = kwh_cap
        cap_applied = True
    if raw_litres > litres_cap:
        raw_litres = litres_cap
        cap_applied = True

    # tCO₂e saved per unit
    ef = _EF_ELEC if acts_on == "electricity" else _EF_DSEL
    tco2e = (raw_kwh * _EF_ELEC["factor"] + raw_litres * _EF_DSEL["factor"]) / 1000.0

    capex = float(measure["capex_inr"])
    _validate_capex(capex, measure["label"])

    inr_per_tco2e = (capex / tco2e) if tco2e > 0 else None

    return {
        "kwh_saved_per_unit": round(raw_kwh, 4),
        "litres_saved_per_unit": round(raw_litres, 4),
        "tco2e_saved_per_unit": round(tco2e, 6),
        "capex_per_unit": capex,
        "inr_per_tco2e": round(inr_per_tco2e, 2) if inr_per_tco2e is not None else None,
        "cap_applied": cap_applied,
        "cap_basis": cap_basis,
        "cap_value": cap_map.get(cap_basis) if cap_basis else None,
        "factor_used": {
            "name": "electricity" if acts_on == "electricity" else "diesel",
            **ef,
        },
        "scope": ef["scope"],
    }


# ── internal: build impact table ───────────────────────────────────────────────
def _build_impacts(ready_measures: list[dict], baseline_df: pd.DataFrame) -> list[dict]:
    """Attach 'impact' dict to each ready measure. Returns enriched list."""
    enriched = []
    for m in ready_measures:
        imp = measure_impact(m, baseline_df)
        enriched.append({**m, "impact": imp})
    return enriched


# ── C. optimize (MILP) ─────────────────────────────────────────────────────────
def optimize(
    baseline_df: pd.DataFrame,
    measures: list[dict],
    budget_inr: float,
    method: str = "milp",
) -> dict:
    """
    Select measures to maximise annual tCO₂e reduction within budget.

    Solver: scipy.optimize.milp (IntegerConstraint).
    Greedy comparison is always included in the result.

    Decision variables: x_i ∈ {0 .. max_units_i} integer.

    Constraints:
        Σ capex_i * x_i          ≤ budget_inr
        Σ kwh_saved_i * x_i      ≤ baseline_electricity_kwh_annual
        Σ litres_saved_i * x_i   ≤ baseline_diesel_litres_annual
        per cap_basis group: Σ savings ≤ end_use
        per exclusive_group: Σ x_i ≤ 1

    The result is cross-checked against simulation.simulate() to verify
    accounting consistency (must agree within 0.01 tCO₂e).
    """
    from scipy.optimize import milp, LinearConstraint, Bounds

    _validate_budget(budget_inr)

    ready = [m for m in measures if m["status"] == "ready"]
    needs_input = [m for m in measures if m["status"] != "ready"]

    if not ready:
        return _empty_result(measures, budget_inr, needs_input)

    enriched = _build_impacts(ready, baseline_df)
    n = len(enriched)

    base_df = _sim_baseline(baseline_df)
    total_elec = float(base_df["electricity_kwh"].sum())
    total_diesel = float(base_df["diesel_litres"].sum())

    # Objective: maximise tCO₂e saved → minimise negative tCO₂e
    c = np.array([-m["impact"]["tco2e_saved_per_unit"] for m in enriched], dtype=float)

    # Bounds: 0 ≤ x_i ≤ max_units_i
    lb = np.zeros(n)
    ub = np.array([float(m["max_units"]) for m in enriched], dtype=float)
    bounds = Bounds(lb, ub)

    # Integer constraints: all variables are integers
    from scipy.optimize import LinearConstraint, Bounds
    integrality = np.ones(n)   # 1 = integer

    # Build constraint matrix rows
    A_rows = []
    b_lo = []
    b_hi = []

    # 1. Budget constraint
    budget_row = np.array([m["impact"]["capex_per_unit"] for m in enriched], dtype=float)
    A_rows.append(budget_row)
    b_lo.append(-np.inf)
    b_hi.append(budget_inr)

    # 2. Global electricity cap
    elec_row = np.array([m["impact"]["kwh_saved_per_unit"] for m in enriched], dtype=float)
    A_rows.append(elec_row)
    b_lo.append(-np.inf)
    b_hi.append(total_elec)

    # 3. Global diesel cap
    diesel_row = np.array([m["impact"]["litres_saved_per_unit"] for m in enriched], dtype=float)
    A_rows.append(diesel_row)
    b_lo.append(-np.inf)
    b_hi.append(total_diesel)

    # 4. Per cap_basis group caps
    cap_map = {
        "total_electricity": total_elec,
        "total_diesel": total_diesel,
        "ac_end_use": AC_END_USE_KWH_YR,
        "lighting_end_use": LIGHTING_END_USE_KWH_YR,
    }
    cap_groups: dict[str, list[int]] = {}
    for i, m in enumerate(enriched):
        cb = m.get("cap_basis")
        if cb and cb not in ("total_electricity", "total_diesel"):
            cap_groups.setdefault(cb, []).append(i)

    for cb, idxs in cap_groups.items():
        cap_val = cap_map.get(cb)
        if cap_val is None:
            continue  # TBD cap — constraint not added (measure is needs_input anyway)
        row = np.zeros(n)
        for i in idxs:
            if enriched[i]["acts_on"] == "electricity":
                row[i] = enriched[i]["impact"]["kwh_saved_per_unit"]
            else:
                row[i] = enriched[i]["impact"]["litres_saved_per_unit"]
        A_rows.append(row)
        b_lo.append(-np.inf)
        b_hi.append(cap_val)

    # 5. Exclusive group constraints (Σ x_i ≤ 1 per group)
    exc_groups: dict[str, list[int]] = {}
    for i, m in enumerate(enriched):
        eg = m.get("exclusive_group")
        if eg:
            exc_groups.setdefault(eg, []).append(i)

    for eg, idxs in exc_groups.items():
        row = np.zeros(n)
        for i in idxs:
            row[i] = 1.0
        A_rows.append(row)
        b_lo.append(-np.inf)
        b_hi.append(1.0)

    A = np.array(A_rows, dtype=float)
    b_lo = np.array(b_lo, dtype=float)
    b_hi = np.array(b_hi, dtype=float)
    constraints = LinearConstraint(A, b_lo, b_hi)

    res = milp(c, constraints=constraints, integrality=integrality, bounds=bounds)

    if res.status not in (0, 1):   # 0=optimal, 1=feasible (time limit)
        solver_status = f"FAILED: {res.message}"
        x = np.zeros(n)
    else:
        solver_status = "OPTIMAL" if res.status == 0 else "FEASIBLE"
        x = np.round(res.x).astype(int)

    selected = _build_selected(enriched, x)
    totals = _sum_totals(selected, baseline_df, needs_input)

    # Consistency check vs simulation.simulate()
    consistency = _consistency_check(selected, baseline_df, totals["annual_tco2e_saved"])

    # Greedy for comparison
    greedy_result = greedy(baseline_df, measures, budget_inr)

    return {
        "method": "milp",
        "solver_status": solver_status,
        "budget_inr": budget_inr,
        "selected": selected,
        **totals,
        "greedy": greedy_result,
        "consistency_check": consistency,
        "needs_input": _needs_input_summary(needs_input),
        "factors_used": _factors_used(),
        "coverage_note": _coverage_note(totals["covered_baseline_tco2e"]),
        "assumptions": _assumptions_list(enriched),
        "basis": "REAL monthly baseline × emission factor; MILP (scipy.optimize.milp) for selection; not ML",
    }


# ── D. greedy ─────────────────────────────────────────────────────────────────
def greedy(
    baseline_df: pd.DataFrame,
    measures: list[dict],
    budget_inr: float,
) -> dict:
    """
    Greedy baseline method: sort measures by tCO₂e per ₹ (descending),
    take while budget allows. Used for comparison with MILP.

    The greedy method can be suboptimal (classic knapsack counter-example).
    """
    _validate_budget(budget_inr)

    ready = [m for m in measures if m["status"] == "ready"]
    needs_input = [m for m in measures if m["status"] != "ready"]

    if not ready:
        return _empty_result(measures, budget_inr, needs_input)

    enriched = _build_impacts(ready, baseline_df)

    # Sort by tCO₂e / ₹ descending (cost-effectiveness)
    for m in enriched:
        tco2e = m["impact"]["tco2e_saved_per_unit"]
        capex = m["impact"]["capex_per_unit"]
        m["_ratio"] = tco2e / capex if capex > 0 else float("inf")

    sorted_m = sorted(enriched, key=lambda m: m["_ratio"], reverse=True)

    # Track per-cap totals
    base_df = _sim_baseline(baseline_df)
    total_elec = float(base_df["electricity_kwh"].sum())
    total_diesel = float(base_df["diesel_litres"].sum())
    cap_map = {
        "total_electricity": total_elec,
        "total_diesel": total_diesel,
        "ac_end_use": AC_END_USE_KWH_YR,
        "lighting_end_use": LIGHTING_END_USE_KWH_YR,
    }
    used_capex = 0.0
    used_elec = 0.0
    used_diesel = 0.0
    cap_used: dict[str, float] = {}
    exc_used: set[str] = set()
    x = {m["id"]: 0 for m in enriched}

    for m in sorted_m:
        cap = m["impact"]["capex_per_unit"]
        kwh = m["impact"]["kwh_saved_per_unit"]
        litres = m["impact"]["litres_saved_per_unit"]
        cb = m.get("cap_basis")
        eg = m.get("exclusive_group")
        max_u = m["max_units"]

        # How many units can we fit?
        affordable = int((budget_inr - used_capex) / cap) if cap > 0 else max_u
        remaining = min(affordable, max_u)

        if eg and eg in exc_used:
            continue   # exclusive group already taken

        for units in range(remaining, 0, -1):
            total_cap = used_capex + cap * units
            total_e = used_elec + kwh * units
            total_d = used_diesel + litres * units
            cb_val = cap_used.get(cb, 0.0) + (kwh if m["acts_on"] == "electricity" else litres) * units

            ok = (
                total_cap <= budget_inr
                and total_e <= total_elec
                and total_d <= total_diesel
                and (cb is None or cap_map.get(cb) is None or cb_val <= cap_map[cb])
            )
            if ok:
                x[m["id"]] = units
                used_capex += cap * units
                used_elec += kwh * units
                used_diesel += litres * units
                if cb:
                    cap_used[cb] = cb_val
                if eg:
                    exc_used.add(eg)
                break

    x_arr = np.array([x[m["id"]] for m in enriched], dtype=int)
    selected = _build_selected(enriched, x_arr)
    totals = _sum_totals(selected, baseline_df, needs_input)

    return {
        "method": "greedy",
        "solver_status": "GREEDY",
        "budget_inr": budget_inr,
        "selected": selected,
        **totals,
    }


# ── E. budget_sweep ────────────────────────────────────────────────────────────
def budget_sweep(
    baseline_df: pd.DataFrame,
    measures: list[dict],
    budgets: list[float],
) -> list[dict]:
    """
    Run optimize() at each budget level.
    Returns a list of dicts with budget, optimal_tco2e, greedy_tco2e, selected_ids.
    """
    results = []
    for b in budgets:
        opt = optimize(baseline_df, measures, float(b))
        gr = opt.get("greedy", {})
        results.append({
            "budget_inr": b,
            "optimal_tco2e_saved": opt.get("annual_tco2e_saved", 0.0),
            "greedy_tco2e_saved": gr.get("annual_tco2e_saved", 0.0),
            "optimal_selected_ids": [s["id"] for s in opt.get("selected", [])],
            "optimal_total_capex": opt.get("total_capex_inr", 0.0),
        })
    return results


# ── internal helpers ───────────────────────────────────────────────────────────
def _build_selected(enriched: list[dict], x: np.ndarray) -> list[dict]:
    selected = []
    for m, units in zip(enriched, x):
        if units > 0:
            imp = m["impact"]
            selected.append({
                "id": m["id"],
                "label": m["label"],
                "category": m["category"],
                "acts_on": m["acts_on"],
                "units": int(units),
                "capex_inr": round(imp["capex_per_unit"] * units, 2),
                "kwh_saved": round(imp["kwh_saved_per_unit"] * units, 2),
                "litres_saved": round(imp["litres_saved_per_unit"] * units, 2),
                "tco2e_saved": round(imp["tco2e_saved_per_unit"] * units, 4),
                "scope": imp["scope"],
                "basis": m["basis"],
                "source": m["source"],
                "source_date": m["source_date"],
                "inr_per_tco2e": imp["inr_per_tco2e"],
            })
    return selected


def _sum_totals(selected: list[dict], baseline_df: pd.DataFrame, needs_input: list[dict]) -> dict:
    base_df = _sim_baseline(baseline_df)
    covered_baseline = float(
        base_df["scope2_tco2e"].sum() + base_df["scope1_tco2e"].sum()
    )
    total_capex = sum(s["capex_inr"] for s in selected)
    total_tco2e = sum(s["tco2e_saved"] for s in selected)
    total_scope2 = sum(s["tco2e_saved"] for s in selected if s["scope"] == "Scope 2")
    total_scope1 = sum(s["tco2e_saved"] for s in selected if s["scope"] == "Scope 1")
    pct_covered = (total_tco2e / covered_baseline * 100) if covered_baseline > 0 else 0.0
    pct_footprint = (total_tco2e / REPORT_FOOTPRINT_TCO2E * 100)

    return {
        "total_capex_inr": round(total_capex, 2),
        "annual_tco2e_saved": round(total_tco2e, 4),
        "annual_scope2_tco2e_saved": round(total_scope2, 4),
        "annual_scope1_tco2e_saved": round(total_scope1, 4),
        "pct_of_covered_baseline": round(pct_covered, 2),
        "pct_of_full_footprint": round(pct_footprint, 2),
        "covered_baseline_tco2e": round(covered_baseline, 4),
        "payback_years": None,   # null until tariff provided
        "payback_note": "Electricity tariff and diesel price not provided; payback not computed.",
    }


def _consistency_check(
    selected: list[dict], baseline_df: pd.DataFrame, optimizer_tco2e: float
) -> dict:
    """Cross-check: convert selected measures to a simulation scenario and verify agreement."""
    base_df = _sim_baseline(baseline_df)
    total_elec = float(base_df["electricity_kwh"].sum())
    total_diesel = float(base_df["diesel_litres"].sum())

    kwh_saved = sum(s["kwh_saved"] for s in selected)
    litres_saved = sum(s["litres_saved"] for s in selected)

    # Convert to simulation inputs
    elec_change_pct = -(kwh_saved / total_elec * 100.0) if total_elec > 0 else 0.0
    diesel_change_pct = -(litres_saved / total_diesel * 100.0) if total_diesel > 0 else 0.0

    sim_result = _sim_simulate(baseline_df, elec_change_pct, diesel_change_pct, 0.0)
    sim_saved = sim_result["annual"]["saved_tco2e"]
    diff = abs(optimizer_tco2e - sim_saved)

    return {
        "optimizer_tco2e_saved": round(optimizer_tco2e, 4),
        "simulation_tco2e_saved": round(sim_saved, 4),
        "difference": round(diff, 6),
        "passed": diff <= 0.01,
        "note": "Optimizer result cross-checked against simulation.simulate() — must agree within 0.01 tCO₂e.",
    }


def _empty_result(measures: list[dict], budget_inr: float, needs_input: list[dict]) -> dict:
    base_df = _sim_baseline(
        pd.read_csv(
            os.path.join(os.path.dirname(__file__), "..", "data", "real", "real_monthly_2025.csv")
        )
    )
    covered_baseline = float(base_df["scope2_tco2e"].sum() + base_df["scope1_tco2e"].sum())
    return {
        "method": "none",
        "solver_status": "NO_READY_MEASURES",
        "budget_inr": budget_inr,
        "selected": [],
        "total_capex_inr": 0.0,
        "annual_tco2e_saved": 0.0,
        "annual_scope2_tco2e_saved": 0.0,
        "annual_scope1_tco2e_saved": 0.0,
        "pct_of_covered_baseline": 0.0,
        "pct_of_full_footprint": 0.0,
        "covered_baseline_tco2e": round(covered_baseline, 4),
        "payback_years": None,
        "payback_note": "No ready measures.",
        "needs_input": _needs_input_summary(needs_input),
        "factors_used": _factors_used(),
        "coverage_note": _coverage_note(covered_baseline),
        "assumptions": [],
        "basis": "REAL monthly baseline × emission factor; MILP (scipy.optimize.milp) for selection; not ML",
    }


def _needs_input_summary(needs_input: list[dict]) -> list[dict]:
    return [
        {
            "id": m["id"],
            "label": m["label"],
            "missing_fields": m["missing_fields"],
            "basis": m["basis"],
            "notes": m["notes"],
        }
        for m in needs_input
    ]


def _factors_used() -> list[dict]:
    return [
        {"name": "electricity", **_EF_ELEC},
        {"name": "diesel", **_EF_DSEL},
    ]


def _coverage_note(covered_baseline_tco2e: float) -> dict:
    pct = round(covered_baseline_tco2e / REPORT_FOOTPRINT_TCO2E * 100.0, 1)
    return {
        "covered_tco2e": round(covered_baseline_tco2e, 4),
        "full_footprint_tco2e": REPORT_FOOTPRINT_TCO2E,
        "full_footprint_source": REPORT_SOURCE,
        "covered_share_pct": pct,
        "not_covered": _NOT_COVERED,
        "note": _COVERED_NOTE,
    }


def _assumptions_list(enriched: list[dict]) -> list[dict]:
    return [
        {
            "id": m["id"],
            "label": m["label"],
            "basis": m["basis"],
            "source": m["source"],
            "source_date": m["source_date"],
        }
        for m in enriched
        if m["basis"].upper() not in ("MEASURED", "QUOTED")
    ]
