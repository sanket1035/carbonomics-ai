"""
upload_audit.py

Energy Audit for an uploaded master CSV (formula only, no machine learning).

An uploaded file can hold three kinds of rows, told apart by a `section` column:
    weekly    week_start, electricity_kwh, diesel_litres (and solar_kwh): the time series, as before
    building  name + value (+ unit): built_up_area (m2, required); guest_house_built_up_area,
              hostel_built_up_area (m2) and total_persons are optional
    ac        name (location), units, capacity_ton, listed_kw_per_unit, daily_hours, days_per_year

A file with no `section` column is read as before (all rows are the time series) and has no Energy Audit.
The audit itself is energy_audit.build_audit(upload=...), the same code as the campus page. Nothing from the
KKWIEER campus files (bus fleet, solar, brochure source) is used for an upload.

Annual basis: the benchmarks are kWh per m2 per YEAR, so the uploaded period must be about a year. 40 or more
weeks (10 or more months) are scaled to a full year (x 52/weeks or x 12/months) and the page says so; fewer are
refused. Nothing is filled in.
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

import energy_audit  # noqa: E402
from upload_analysis import DIESEL, ELECTRICITY, UploadError  # noqa: E402

SECTION = "section"
MIN_WEEKS, MIN_MONTHS = 40, 10
MAX_AC_ROWS = 200
BUILDING_NAMES = {"built_up_area": "m2", "guest_house_built_up_area": "m2",
                  "hostel_built_up_area": "m2", "total_persons": "persons"}
AC_COLUMNS = ["units", "capacity_ton", "listed_kw_per_unit", "daily_hours", "days_per_year"]


def split_sections(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """(time series rows, building rows, ac rows). Without a `section` column all rows are the time series."""
    if SECTION not in df.columns:
        return df, None, None
    sec = df[SECTION].astype(str).str.strip().str.lower()
    unknown = sorted(set(sec) - {"weekly", "building", "ac"})
    if unknown:
        raise UploadError(f"Unknown section(s) {unknown}. Use weekly, building or ac in the 'section' column.")
    weekly = df[sec == "weekly"].drop(columns=[SECTION]).dropna(axis=1, how="all").reset_index(drop=True)
    if weekly.empty:
        raise UploadError("The file has a 'section' column but no rows with section = weekly.")
    weekly.attrs.update(df.attrs)
    return weekly, df[sec == "building"].copy(), df[sec == "ac"].copy()


def _positive(value, label: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise UploadError(f"{label} must be a number.") from None
    if not v > 0 or v != v or v == float("inf"):
        raise UploadError(f"{label} must be greater than 0.")
    return v


def parse_building(building: Optional[pd.DataFrame], ac: Optional[pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validate the building and ac rows and return frames shaped like campus_facts.csv and ac_inventory.csv."""
    if building is None or building.empty or "name" not in building.columns or "value" not in building.columns:
        raise UploadError("No 'building' rows with built_up_area. Add a row: section=building, name=built_up_area, value=<m2>.")
    facts = []
    for _, r in building.iterrows():
        name = str(r["name"]).strip().lower()
        if name not in BUILDING_NAMES:
            raise UploadError(f"Unknown building item '{name}'. Accepted: {sorted(BUILDING_NAMES)}.")
        facts.append({"parameter": name, "value": _positive(r["value"], f"building '{name}'"),
                      "unit": BUILDING_NAMES[name], "source": "Your file", "master_data_sheet": ""})
    facts = pd.DataFrame(facts)
    if facts["parameter"].duplicated().any():
        raise UploadError("A building item is repeated; list each once.")
    if "built_up_area" not in set(facts["parameter"]):
        raise UploadError("The building section needs built_up_area (m2).")

    if ac is None or ac.empty:
        raise UploadError("No 'ac' rows. Add the air-conditioner list: name, units, capacity_ton, listed_kw_per_unit, daily_hours, days_per_year.")
    if len(ac) > MAX_AC_ROWS:
        raise UploadError(f"More than {MAX_AC_ROWS} AC rows.")
    missing = [c for c in AC_COLUMNS + ["name"] if c not in ac.columns]
    if missing:
        raise UploadError(f"The AC rows need the column(s) {missing}.")
    rows = []
    for _, r in ac.iterrows():
        name = str(r["name"]).strip()
        if not name or name.lower() == "nan":
            raise UploadError("An AC row has no name (location).")
        units = _positive(r["units"], f"AC '{name}' units")
        hours = _positive(r["daily_hours"], f"AC '{name}' daily_hours")
        days = _positive(r["days_per_year"], f"AC '{name}' days_per_year")
        if hours > 24 or days > 366 or units != int(units):
            raise UploadError(f"AC '{name}': units must be a whole number, daily_hours at most 24, days_per_year at most 366.")
        cap = _positive(r["capacity_ton"], f"AC '{name}' capacity_ton")
        kw = _positive(r["listed_kw_per_unit"], f"AC '{name}' listed_kw_per_unit")
        rows.append({"location": name, "units": int(units), "capacity_ton": cap, "listed_power_per_unit_kw": kw,
                     "operating_days_per_year": days, "daily_hours": hours,
                     "modelled_annual_kwh": round(units * days * hours * kw, 1),
                     "source": "Your file (modelled; not metered)", "master_data_sheet": ""})
    return facts, pd.DataFrame(rows)


def _annual_months(df: pd.DataFrame, date_col: str, grain: str, solar: Optional[pd.Series]):
    """Monthly frame (month, electricity_kwh, dg_diesel_litres) scaled to one year, plus text about the scaling."""
    n = len(df)
    if grain == "weekly":
        if n < MIN_WEEKS:
            raise UploadError(f"The Energy Audit compares a whole year with an annual benchmark, so it needs at least {MIN_WEEKS} weeks of data; the file has {n}.")
        df, solar = df.tail(52), (None if solar is None else solar.tail(52))
        n = len(df)
        scale, unit_txt = 52.0 / n, f"{n} weeks"
    else:
        if n < MIN_MONTHS:
            raise UploadError(f"The Energy Audit needs at least {MIN_MONTHS} months of data; the file has {n}.")
        df, solar = df.tail(12), (None if solar is None else solar.tail(12))
        n = len(df)
        scale, unit_txt = 12.0 / n, f"{n} months"
    month = df[date_col].dt.strftime("%Y-%m")
    out = pd.DataFrame({"month": month, ELECTRICITY: df[ELECTRICITY].to_numpy(),
                        "dg_diesel_litres": df[DIESEL].to_numpy() if DIESEL in df.columns else 0.0})
    out = out.groupby("month", as_index=False).sum()
    out[[ELECTRICITY, "dg_diesel_litres"]] *= scale
    span = f"{df[date_col].iloc[0]:%d %b %Y} to {df[date_col].iloc[-1]:%d %b %Y}"
    note = f"{unit_txt} ({span})" + (f", scaled by {scale:.3f} to one year" if abs(scale - 1) > 1e-9 else "")
    return out, note, (None if solar is None else float(solar.sum()) * scale)


def build_from_upload(weekly: pd.DataFrame, date_col: str, grain: str, sources: list,
                      building: Optional[pd.DataFrame], ac: Optional[pd.DataFrame],
                      solar: Optional[pd.Series] = None) -> dict:
    """energy_audit.build_audit() on the uploaded rows. Raises UploadError with a message safe to show."""
    if ELECTRICITY not in sources:
        raise UploadError("The Energy Audit needs electricity (kWh) in the file.")
    facts, ac_df = parse_building(building, ac)
    real, span, solar_kwh = _annual_months(weekly, date_col, grain, solar)
    return energy_audit.build_audit(upload={
        "real": real, "facts": facts, "ac": ac_df, "solar_kwh": solar_kwh,
        "period": f"Your file: {span}",
        "basis": f"Your uploaded electricity, {span}, divided by the built-up area in your file; formula only, no ML",
        "area_source": "Your file (building section)",
    })
