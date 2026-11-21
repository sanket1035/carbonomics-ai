"""
campus_footprint_report.py

The yearly (static) campus footprint of the published KKWIEER Carbon Footprint Report FY2025-26
(Young Indians KKWIEER Chapter): Scope 1, Scope 2 and Scope 3 in one table, total 1,992.06 tCO2e.

Source of the numbers: data/real/campus_footprint_report_fy2025_26.csv, copied row by row from that report
(the `report_location` column names the table or section). Scope 3 comes from the college survey carried out
by the Young Indians team. These are yearly totals with no time series behind them, so nothing here is
forecast, spread over weeks or added to a user's uploaded totals.

Rules kept here:
- emission = activity x factor. Factors are never typed in the CSV; a row names a key of
  emission_factors.EMISSION_FACTORS and the factor, unit, source and version come from there.
- A row with an activity and a factor is recomputed and must match the stated value (else ReportError).
  A row without them is shown as "stated only" and says why in its note.
- The scope subtotals and the total must match the published ones; otherwise ReportError.
- "Memo" rows (rooftop solar avoided, tree removals) are shown but never added to the total.
"""

from __future__ import annotations

import csv
import os
from typing import Optional

from emission_factors import EMISSION_FACTORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(ROOT, "data", "real", "campus_footprint_report_fy2025_26.csv")
PERIOD = "FY 2025-26"
SOURCE = "KKWIEER Carbon Footprint Report FY2025-26 (Young Indians KKWIEER Chapter), Table 1"
SCOPE3_SOURCE = "the college survey carried out by the Young Indians team"
PUBLISHED_BY_SCOPE = {"Scope 1": 138.29, "Scope 2": 751.99, "Scope 3": 1101.78}
PUBLISHED_TOTAL = 1992.06
MATCH_TOLERANCE_T = 0.02   # the report rounds each line to 2 decimals
TOTAL_TOLERANCE_T = 0.011


class ReportError(ValueError):
    """The report file is missing a column, disagrees with its own factors, or does not add up."""


def _num(v: str) -> Optional[float]:
    v = (v or "").strip()
    return float(v) if v else None


def _row(raw: dict) -> dict:
    activity, stated = _num(raw["activity_value"]), _num(raw["tco2e"])
    if stated is None:
        raise ReportError(f"{raw['source']}: no tco2e value")
    key = (raw["factor_key"] or "").strip()
    factor = recomputed = None
    if key:
        if key not in EMISSION_FACTORS:
            raise ReportError(f"{raw['source']}: factor '{key}' is not in emission_factors.py")
        if activity is None:
            raise ReportError(f"{raw['source']}: a factor is given but no activity")
        f = EMISSION_FACTORS[key]
        factor = {"key": key, "value": f["factor"], "unit": f["output"], "source": f["source"],
                  "version": f["version"], "verified": f["verified"]}
        recomputed = activity * f["factor"] / 1000.0
        if abs(recomputed - stated) > MATCH_TOLERANCE_T:
            raise ReportError(f"{raw['source']}: activity x factor = {recomputed:.3f} but the file says {stated}")
    return {"scope": raw["scope"], "source": raw["source"], "activity": activity, "activity_unit": raw["activity_unit"],
            "factor": factor, "tco2e": stated, "check": "recomputed" if recomputed is not None else "stated",
            "basis": raw["basis"], "note": raw["note"], "report_location": raw["report_location"]}


def load_report(path: Optional[str] = None) -> dict:
    with open(path or REPORT_PATH, encoding="utf-8", newline="") as f:
        rows = [_row(r) for r in csv.DictReader(f)]
    for r in rows:
        r["in_total"] = "memo" if r["scope"] == "Memo" else "yes"
    counted = [r for r in rows if r["in_total"] == "yes"]
    by_scope = {s: round(sum(r["tco2e"] for r in counted if r["scope"] == s), 2) for s in PUBLISHED_BY_SCOPE}
    for s, published in PUBLISHED_BY_SCOPE.items():
        if abs(by_scope[s] - published) > TOTAL_TOLERANCE_T:
            raise ReportError(f"{s} rows add up to {by_scope[s]} but the report says {published}")
    total = round(sum(by_scope.values()), 2)
    if abs(total - PUBLISHED_TOTAL) > TOTAL_TOLERANCE_T:
        raise ReportError(f"rows add up to {total} but the report says {PUBLISHED_TOTAL}")
    # Same keys as annual_inventory.load_inventory(), so the report pages can draw either.
    return {"period": PERIOD, "rows": rows, "counted": counted, "by_scope": by_scope, "total": total,
            "published_total": PUBLISHED_TOTAL, "published_source": SOURCE, "source": SOURCE,
            "alternatives": [], "memo": [r for r in rows if r["in_total"] == "memo"], "excluded": [],
            "unverified_factors": sorted({r["factor"]["key"] for r in rows if r["factor"] and not r["factor"]["verified"]}),
            "scope3_source": SCOPE3_SOURCE}
