"""
upload_analysis.py

Analyse a user-uploaded CSV of activity data (electricity kWh, generator diesel litres).

Reuses the existing modules instead of re-implementing them:
    emission_factors.py   factor registry (source, version, unit)
    calculations.py       emission = activity x factor
    ml/forecast_weekly.py features, time-based split, naive baseline, metrics

Rules (same as the weekly pipeline):
  - nothing is imputed or invented: a bad file raises UploadError with a plain message
  - ML predicts ACTIVITY only; emission is always activity x factor
  - time-based split only; the model is compared with the naive last-week baseline and the
    forecast falls back to naive when the model does not beat it
  - uploaded data is processed in memory and never written to disk or the database

Supported input granularity: daily (aggregated to 7-day weeks), weekly, monthly.
Monthly files get carbon accounting only; the ML forecast needs weekly history.
"""

import io
import math
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from calculations import calculate_diesel_emissions, calculate_electricity_emissions
from emission_factors import EMISSION_FACTORS
from simulation import simulate
from ml.model_selection import MODELS as ML_MODELS, evaluate, fit_future

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 100_000
MIN_WEEKS_FOR_ML = 26          # default, to be tuned; below this no ML forecast is attempted
SMALL_TEST_WARNING_WEEKS = 8
MIN_MAE_IMPROVEMENT = 0.05     # a model must cut MAE by at least 5% vs naive; a smaller win is noise
DEFAULT_FUTURE_WEEKS = 8
MAX_FUTURE_WEEKS = 26
MAX_SIM_PERIODS = 5000

ELECTRICITY = "electricity_kwh"
DIESEL = "diesel_litres"
SOURCES = {
    ELECTRICITY: {"scope": "Scope 2", "factor_key": "electricity", "calc": calculate_electricity_emissions},
    DIESEL: {"scope": "Scope 1", "factor_key": "diesel", "calc": calculate_diesel_emissions},
}

_DATE_ALIASES = ["date", "week_start", "week", "month", "period", "timestamp", "datetime"]
_ELEC_ALIASES = ["electricity_kwh", "kwh", "electricity", "energy_kwh", "grid_kwh"]
_DIESEL_ALIASES = ["diesel_litres", "dg_diesel_litres", "diesel_l", "diesel_liters", "diesel"]

DISCLAIMER = (
    "Results are computed from your file only. Emission = activity x emission factor; "
    "the forecast predicts activity, never emission. No accuracy is guaranteed for your site."
)


class UploadError(ValueError):
    """The uploaded file cannot be analysed; the message is safe to show to the user."""


# ── reading and column mapping ────────────────────────────────────────────────
def read_upload(raw: bytes) -> pd.DataFrame:
    if len(raw) == 0:
        raise UploadError("The file is empty.")
    if len(raw) > MAX_BYTES:
        raise UploadError(f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if raw[:4] == b"\xd0\xcf\x11\xe0":
        raise UploadError("This looks like an old Excel (.xls) file. Please save it as .xlsx or .csv and upload again.")
    try:
        if raw[:2] == b"PK":                      # .xlsx is a zip file
            sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, header=None, engine="openpyxl")
            df = _combine_sheets(sheets) if len(sheets) > 1 else None
            if df is None:                        # one sheet, or no sheet we recognise: first sheet, header in row 1
                df = pd.read_excel(io.BytesIO(raw), sheet_name=0, engine="openpyxl")
        else:
            df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # pandas raises several parser error types
        raise UploadError(f"Could not read the file as CSV or Excel (.xlsx): {exc}") from exc
    if len(df) > MAX_ROWS:
        raise UploadError(f"The file has more than {MAX_ROWS} rows.")
    if df.empty:
        raise UploadError("The file has no data rows.")
    attrs = dict(df.attrs)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df.attrs.update(attrs)
    return df


# ── workbooks with several sheets ─────────────────────────────────────────────
# A report-style workbook can keep electricity and diesel on separate sheets, each with a title above the
# header row and a total below the data. Each sheet is scanned for a header row that has a date column and an
# electricity (kWh) or diesel (litres) column; the sheets found are joined on the date. Nothing is guessed:
# a sheet without such a header row (README, inventories, solar generation, emission-factor tables) is skipped.
_HEADER_SCAN_ROWS = 15
_NOT_ACTIVITY = ("ef", "emission", "co2", "solar", "generation", "avoided", "old", "capacity", "annual")


def _header_kind(cell: str) -> Optional[str]:
    c = cell.strip().lower()
    if c in _DATE_ALIASES:
        return "date"
    if c in _ELEC_ALIASES:
        return ELECTRICITY
    if c in _DIESEL_ALIASES:
        return DIESEL
    words = c.replace("(", " ").replace(")", " ").replace("/", " ").split()
    if any(w in _NOT_ACTIVITY for w in words) or any(w in c for w in ("emission", "solar", "avoided")):
        return None
    if "kwh" in c:
        return ELECTRICITY
    if "diesel" in c and any(u in c for u in ("(l)", "litre", "liter")):
        return DIESEL
    return None


def _extract_sheet(raw: pd.DataFrame) -> Optional[pd.DataFrame]:
    for i in range(min(_HEADER_SCAN_ROWS, len(raw))):
        kinds: Dict[str, int] = {}
        for j, cell in enumerate(raw.iloc[i]):
            if isinstance(cell, str):
                kind = _header_kind(cell)
                if kind and kind not in kinds:
                    kinds[kind] = j
        if "date" not in kinds or not ({ELECTRICITY, DIESEL} & set(kinds)):
            continue
        body = raw.iloc[i + 1:]
        with warnings.catch_warnings():           # month names such as "January 2025" make pandas parse one by one
            warnings.simplefilter("ignore", UserWarning)
            dates = pd.to_datetime(body.iloc[:, kinds["date"]], errors="coerce")
        n = 0                                     # data rows end at the first row without a valid date (e.g. TOTAL)
        while n < len(dates) and pd.notna(dates.iloc[n]):
            n += 1
        if n < 2:
            continue
        out = pd.DataFrame({"date": dates.iloc[:n].to_numpy()})
        for kind in (ELECTRICITY, DIESEL):
            if kind in kinds:
                out[kind] = body.iloc[:n, kinds[kind]].to_numpy()
        return out
    return None


def _combine_sheets(sheets: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    frames: List[Tuple[str, pd.DataFrame]] = []
    for name, raw in sheets.items():
        found = _extract_sheet(raw)
        if found is not None:
            frames.append((str(name), found))
    if not frames:
        return None
    combined: Optional[pd.DataFrame] = None
    used: List[str] = []
    for name, f in frames:
        new = [c for c in (ELECTRICITY, DIESEL) if c in f.columns and (combined is None or c not in combined.columns)]
        if not new:
            continue
        part = f[["date"] + new]
        combined = part if combined is None else combined.merge(part, on="date", how="outer")
        used.append(name)
    combined.attrs["sheets_used"] = used
    return combined


def _pick(columns: List[str], aliases: List[str], explicit: Optional[str], label: str) -> Optional[str]:
    if explicit:
        name = explicit.strip().lower()
        if name not in columns:
            raise UploadError(f"Column '{explicit}' (for {label}) was not found. Columns in file: {columns}")
        return name
    for alias in aliases:
        if alias in columns:
            return alias
    return None


def map_columns(df: pd.DataFrame, date_col=None, electricity_col=None, diesel_col=None) -> Dict[str, Optional[str]]:
    cols = list(df.columns)
    mapping = {
        "date": _pick(cols, _DATE_ALIASES, date_col, "date"),
        ELECTRICITY: _pick(cols, _ELEC_ALIASES, electricity_col, "electricity (kWh)"),
        DIESEL: _pick(cols, _DIESEL_ALIASES, diesel_col, "diesel (litres)"),
    }
    if mapping["date"] is None:
        raise UploadError(
            f"No date column found. Expected one of {_DATE_ALIASES}, or choose the column. Columns in file: {cols}"
        )
    if mapping[ELECTRICITY] is None and mapping[DIESEL] is None:
        raise UploadError(
            "No activity column found. Provide electricity in kWh and/or generator diesel in litres "
            f"(accepted names: {_ELEC_ALIASES + _DIESEL_ALIASES}). Columns in file: {cols}"
        )
    return mapping


# ── validation and granularity ────────────────────────────────────────────────
def _clean_frame(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    out = pd.DataFrame()
    try:
        out["date"] = pd.to_datetime(df[mapping["date"]])
    except Exception as exc:
        raise UploadError(f"Column '{mapping['date']}' contains values that are not valid dates: {exc}") from exc
    if out["date"].isnull().any():
        raise UploadError(f"Column '{mapping['date']}' has missing dates.")
    for target in (ELECTRICITY, DIESEL):
        col = mapping[target]
        if col is None:
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        if values.isnull().any():
            bad = int(values.isnull().sum())
            raise UploadError(
                f"Column '{col}' has {bad} missing or non-numeric value(s). Nothing is filled in automatically; "
                "please fix or remove those rows."
            )
        if (values < 0).any():
            raise UploadError(f"Column '{col}' has negative values.")
        out[target] = values.astype(float)
    out = out.sort_values("date").reset_index(drop=True)
    if out["date"].duplicated().any():
        raise UploadError("The date column has repeated dates.")
    return out


def detect_granularity(dates: pd.Series) -> str:
    if len(dates) < 2:
        raise UploadError("At least 2 rows are needed.")
    steps = dates.diff().dropna()
    if (steps == pd.Timedelta(days=1)).all():
        return "daily"
    if (steps == pd.Timedelta(days=7)).all():
        return "weekly"
    months = dates.dt.year * 12 + dates.dt.month
    if months.is_unique and (months.diff().dropna() == 1).all():
        return "monthly"
    raise UploadError(
        "Dates must be a complete daily, weekly (exact 7-day steps) or monthly series with no gaps. "
        "Nothing is filled in automatically."
    )


def _daily_to_weekly(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    """Sum 7-day blocks counted from the first date; an incomplete last block is dropped."""
    activity = [c for c in (ELECTRICITY, DIESEL) if c in df.columns]
    block = ((df["date"] - df["date"].iloc[0]).dt.days // 7).to_numpy()
    sizes = pd.Series(block).value_counts().sort_index()
    complete = sizes[sizes == 7].index
    if len(complete) == 0:
        raise UploadError("Daily data must cover at least 7 consecutive days.")
    note = None
    dropped = int((sizes != 7).sum())
    if dropped:
        note = f"The last {int(sizes.iloc[-1])} day(s) did not fill a whole week and were left out of the weekly series."
    df = df.assign(_block=block)
    weekly = df[df["_block"].isin(complete)].groupby("_block").agg(
        week_start=("date", "min"), **{c: (c, "sum") for c in activity}
    ).reset_index(drop=True)
    return weekly, note


# ── accounting ────────────────────────────────────────────────────────────────
def factors_used(sources: List[str]) -> List[dict]:
    rows = []
    for t in sources:
        key = SOURCES[t]["factor_key"]
        spec = EMISSION_FACTORS[key]
        rows.append({
            "activity": t, "factor_key": key, "factor": spec["factor"], "unit": spec["unit"],
            "output": spec["output"], "scope": spec["scope"], "source": spec["source"],
            "version": spec["version"], "verified": spec["verified"],
        })
    return rows


def account(df: pd.DataFrame, date_col: str, sources: List[str]) -> dict:
    """Per-period emission = activity x factor, plus totals in tCO2e."""
    out = df.copy()
    out["scope1_kg"] = 0.0
    out["scope2_kg"] = 0.0
    for t in sources:
        kg = out[t].apply(SOURCES[t]["calc"])
        out["scope2_kg" if SOURCES[t]["scope"] == "Scope 2" else "scope1_kg"] += kg
    out["total_kg"] = out["scope1_kg"] + out["scope2_kg"]
    periods = []
    for _, r in out.iterrows():
        row = {"period_start": r[date_col].strftime("%Y-%m-%d")}
        for t in sources:
            row[t] = float(r[t])
        row["scope1_kg"] = float(r["scope1_kg"])
        row["scope2_kg"] = float(r["scope2_kg"])
        row["total_kg"] = float(r["total_kg"])
        periods.append(row)
    totals = {
        "scope1_tco2e": float(out["scope1_kg"].sum() / 1000.0),
        "scope2_tco2e": float(out["scope2_kg"].sum() / 1000.0),
        "total_tco2e": float(out["total_kg"].sum() / 1000.0),
    }
    return {"periods": periods, "totals": totals}


# ── forecasting ───────────────────────────────────────────────────────────────
def _future_naive(last_value: float, n: int) -> np.ndarray:
    return np.full(n, last_value)


def forecast_target(df: pd.DataFrame, target: str, future_weeks: int) -> dict:
    ev = evaluate(df[["week_start", target]], target)
    pred_df = ev["pred_df"]
    by_model = {r["model"]: r for r in ev["metrics"]}
    naive_mae = by_model["naive_last_week"]["MAE"]
    ml = {m: by_model[m]["MAE"] for m in ML_MODELS}
    best_ml = ev["candidate"]            # lowest rolling-validation MAE; the test weeks only decide whether it is used
    beats_naive = ml[best_ml] < naive_mae and ml[best_ml] <= naive_mae * (1 - MIN_MAE_IMPROVEMENT)

    if beats_naive:
        chosen = best_ml
        future = fit_future(df, target, best_ml, ev["best_settings"][best_ml], future_weeks)
        message = (f"{best_ml} had the best validation score of the {len(ML_MODELS)} models and beat the naive last-week baseline by at "
                   f"least {MIN_MAE_IMPROVEMENT:.0%} on the held-out weeks (MAE {ml[best_ml]:.1f} vs {naive_mae:.1f}); it is used for the forecast.")
    else:
        chosen = "naive_last_week"
        future = _future_naive(float(df[target].iloc[-1]), future_weeks)
        message = (f"No model beat the naive last-week baseline by {MIN_MAE_IMPROVEMENT:.0%} or more on the held-out weeks "
                   f"(best model {best_ml}, MAE {ml[best_ml]:.1f} vs naive {naive_mae:.1f}), so the forecast repeats the last "
                   "observed week.")

    first_future = df["week_start"].iloc[-1] + pd.Timedelta(days=7)
    future_dates = pd.date_range(first_future, periods=future_weeks, freq="7D")
    test_weeks = int(by_model["naive_last_week"]["test_weeks"])
    warnings = []
    if test_weeks < SMALL_TEST_WARNING_WEEKS:
        warnings.append(f"Only {test_weeks} weeks were held out for testing, so the comparison is weak.")

    backtest = []
    for _, r in pred_df.iterrows():
        row = {"week_start": r["week_start"].strftime("%Y-%m-%d"), "actual": float(r[f"actual_{target}"])}
        for m in ("naive_last_week", "train_mean", *ML_MODELS):
            row[m] = float(r[f"pred_{m}"])
        backtest.append(row)

    return {
        "target": target,
        "train_weeks": int(by_model["naive_last_week"]["train_weeks"]),
        "test_weeks": test_weeks,
        "metrics": [
            {"model": m, "MAE": r["MAE"], "RMSE": r["RMSE"], "R2": r["R2"]} for m, r in by_model.items()
        ],
        "beats_naive": bool(beats_naive),
        "chosen_model": chosen,
        "message": message,
        "training": ev["training"],
        "warnings": warnings,
        "backtest": backtest,
        "future": [{"week_start": d.strftime("%Y-%m-%d"), "predicted": float(v)}
                   for d, v in zip(future_dates, future)],
    }


def forecast(df: pd.DataFrame, sources: List[str], future_weeks: int) -> dict:
    out = {"status": "ok", "targets": {}, "emission_future": []}
    for t in sources:
        out["targets"][t] = forecast_target(df, t, future_weeks)
    # derived, never learned: predicted activity x factor
    first = out["targets"][sources[0]]["future"]
    for i in range(len(first)):
        row = {"week_start": first[i]["week_start"], "scope1_kg": 0.0, "scope2_kg": 0.0}
        for t in sources:
            kg = SOURCES[t]["calc"](out["targets"][t]["future"][i]["predicted"])
            row["scope2_kg" if SOURCES[t]["scope"] == "Scope 2" else "scope1_kg"] += float(kg)
        row["total_kg"] = row["scope1_kg"] + row["scope2_kg"]
        out["emission_future"].append(row)
    return out


# ── energy audit from the building and AC rows of a master CSV ───────────────
def _energy_audit(raw_df, mapping, df, date_col_out, grain_out, granularity, sources, building_rows, ac_rows):
    """(audit dict or None, status). A problem with the building or AC rows never stops the carbon analysis."""
    import upload_audit
    if building_rows is None:
        return None, {"status": "missing", "reason": "The file has no 'section' column, so no building area or AC list. "
                      "Use the master CSV format (sections weekly, building, ac) to get the Energy Audit."}
    solar = None
    if granularity == "weekly" and "solar_kwh" in raw_df.columns:
        s = pd.DataFrame({"d": pd.to_datetime(raw_df[mapping["date"]]), "s": pd.to_numeric(raw_df["solar_kwh"], errors="coerce")})
        s = s.sort_values("d")
        solar = None if s["s"].isnull().any() or (s["s"] < 0).any() else s["s"].reset_index(drop=True)
    try:
        audit = upload_audit.build_from_upload(df, date_col_out, grain_out, sources, building_rows, ac_rows, solar)
    except UploadError as exc:
        return None, {"status": "error", "reason": str(exc)}
    return audit, {"status": "ok", "reason": None}


# ── entry point ───────────────────────────────────────────────────────────────
def analyze(raw: bytes, date_col=None, electricity_col=None, diesel_col=None,
            future_weeks: int = DEFAULT_FUTURE_WEEKS) -> dict:
    if not 1 <= future_weeks <= MAX_FUTURE_WEEKS:
        raise UploadError(f"future_weeks must be between 1 and {MAX_FUTURE_WEEKS}.")
    import upload_audit      # imported here: upload_audit imports UploadError from this module
    raw_df, building_rows, ac_rows = upload_audit.split_sections(read_upload(raw))
    mapping = map_columns(raw_df, date_col, electricity_col, diesel_col)
    sources = [t for t in (ELECTRICITY, DIESEL) if mapping[t] is not None]
    df = _clean_frame(raw_df, mapping)
    granularity = detect_granularity(df["date"])

    notes: List[str] = []
    if raw_df.attrs.get("sheets_used"):
        notes.append("Read from sheet(s): " + ", ".join(raw_df.attrs["sheets_used"]) + ". Other sheets were not used.")
    if granularity == "daily":
        df, note = _daily_to_weekly(df)
        if note:
            notes.append(note)
        notes.append("Daily data was summed into 7-day weeks (counted from the first date) for forecasting.")
        date_col_out, grain_out = "week_start", "weekly"
    elif granularity == "weekly":
        df = df.rename(columns={"date": "week_start"})
        date_col_out, grain_out = "week_start", "weekly"
    else:
        date_col_out, grain_out = "date", "monthly"

    result = {
        "input": {
            "rows": int(len(df)),
            "granularity_detected": granularity,
            "granularity_analysed": grain_out,
            "period_start": df[date_col_out].iloc[0].strftime("%Y-%m-%d"),
            "period_end": df[date_col_out].iloc[-1].strftime("%Y-%m-%d"),
            "columns_used": {"date": mapping["date"], **{t: mapping[t] for t in sources}},
            "notes": notes,
        },
        "factors_used": factors_used(sources),
        "accounting": account(df, date_col_out, sources),
        "disclaimer": DISCLAIMER,
    }
    result["energy_audit"], result["energy_audit_status"] = _energy_audit(
        raw_df, mapping, df, date_col_out, grain_out, granularity, sources, building_rows, ac_rows)

    if grain_out == "monthly":
        result["forecast"] = {"status": "skipped",
                              "reason": "Monthly data has too few points for an ML forecast. "
                                        "Carbon accounting is shown; upload daily or weekly data to forecast."}
    elif len(df) < MIN_WEEKS_FOR_ML:
        result["forecast"] = {"status": "skipped",
                              "reason": f"Only {len(df)} weeks of data; at least {MIN_WEEKS_FOR_ML} are needed "
                                        "for a forecast that can be tested against a naive baseline."}
    else:
        result["forecast"] = forecast(df, sources, future_weeks)
    return result


# ── what-if simulation on the uploaded periods ───────────────────────────────
def _finite_non_negative(value, label: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise UploadError(f"{label} must be a number.") from exc
    if not math.isfinite(v) or v < 0:
        raise UploadError(f"{label} must be a finite number that is not negative.")
    return v


def simulate_upload(periods: List[dict], electricity_change_pct: float = 0.0,
                    diesel_change_pct: float = 0.0, solar_offset_kwh_per_period: float = 0.0) -> dict:
    """
    What-if scenario on the periods returned by analyze() (weeks or months).

    Reuses simulation.simulate(): scenario activity = baseline x (1 + change %), minus the solar offset per
    period (floored at 0), and emission = activity x factor. A source that is not in the file is left out
    (treated as 0 and not simulated). Nothing is stored.
    """
    if not periods:
        raise UploadError("No periods were given.")
    if len(periods) > MAX_SIM_PERIODS:
        raise UploadError(f"More than {MAX_SIM_PERIODS} periods were given.")
    has_e = all(p.get(ELECTRICITY) is not None for p in periods)
    has_d = all(p.get(DIESEL) is not None for p in periods)
    if any(p.get(ELECTRICITY) is not None for p in periods) and not has_e:
        raise UploadError("Electricity is given for some periods but not all.")
    if any(p.get(DIESEL) is not None for p in periods) and not has_d:
        raise UploadError("Diesel is given for some periods but not all.")
    if not (has_e or has_d):
        raise UploadError("Each period needs electricity_kwh and/or diesel_litres.")

    rows = []
    for i, p in enumerate(periods):
        rows.append({
            "month": str(p.get("period_start", i)),
            "electricity_kwh": _finite_non_negative(p[ELECTRICITY], "electricity_kwh") if has_e else 0.0,
            "dg_diesel_litres": _finite_non_negative(p[DIESEL], "diesel_litres") if has_d else 0.0,
        })
    solar = _finite_non_negative(solar_offset_kwh_per_period, "solar_offset_kwh_per_period")
    try:
        res = simulate(pd.DataFrame(rows), electricity_change_pct=float(electricity_change_pct),
                       diesel_change_pct=float(diesel_change_pct), solar_offset_kwh_per_month=solar)
    except ValueError as exc:
        raise UploadError(str(exc)) from exc

    sources = [t for t, ok in ((ELECTRICITY, has_e), (DIESEL, has_d)) if ok]
    out_periods = [{"period_start": r["month"], **{k: v for k, v in r.items() if k != "month"}} for r in res["monthly"]]
    return {
        "sources_simulated": sources,
        "periods": out_periods,
        "totals": res["annual"],
        "factors_used": factors_used(sources),
        "inputs": {"electricity_change_pct": electricity_change_pct, "diesel_change_pct": diesel_change_pct,
                   "solar_offset_kwh_per_period": solar},
        "note": ("Scenario numbers are inputs you chose, not predictions of what a measure will achieve. "
                 "Emission = activity x emission factor. Only the sources in your file are simulated."),
    }
