"""
Carbonomics-AI web API.

POST /api/analyze  - upload a CSV, get validation, carbon accounting and a forecast as JSON.
POST /api/simulate - what-if scenario on the periods returned by /api/analyze.
POST /api/factor-change - why emissions changed between two years: your energy use vs the grid factor.
GET  /api/grid-factors - the documented grid-factor versions the user can pick from.
POST /api/optimize - best measures within a budget, from the user's own cost inputs.
POST /api/report   - the PDF report, rebuilt on the server from the periods (and plan inputs) of the user's analysis.
GET  /api/runs, GET /api/runs/{id}, DELETE /api/runs/{id} - the logged-in user's saved history.
GET  /api/health   - liveness check (no login needed).

Every /api route except health needs a login (Supabase token). The uploaded CSV itself is never stored;
only the file name, the aggregated periods and the results are saved to the user's history.

Run locally (from the repository root):
    uvicorn api.main:app --reload --port 8000

CORS: set ALLOWED_ORIGINS to a comma-separated list (default: the Vite dev server).
"""

import os
import sys
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(ROOT, "src"))

import emission_factors  # noqa: E402
import factor_change  # noqa: E402
import upload_analysis  # noqa: E402
import upload_optimization  # noqa: E402
from api import history  # noqa: E402
from api.auth import User, current_user  # noqa: E402

app = FastAPI(title="Carbonomics-AI API", version="0.1.0")

_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip().rstrip("/") for o in _origins.split(",") if o.strip()],  # browsers send no trailing "/"
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    date_col: Optional[str] = Form(None),
    electricity_col: Optional[str] = Form(None),
    diesel_col: Optional[str] = Form(None),
    future_weeks: int = Form(upload_analysis.DEFAULT_FUTURE_WEEKS),
    title: Optional[str] = Form(None),
    user: User = Depends(current_user),
) -> dict:
    # read one byte more than the limit so an oversized file is detected without loading all of it
    raw = await file.read(upload_analysis.MAX_BYTES + 1)
    try:
        result = upload_analysis.analyze(
            raw,
            date_col=date_col or None,
            electricity_col=electricity_col or None,
            diesel_col=diesel_col or None,
            future_weeks=future_weeks,
        )
    except upload_analysis.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["run"] = _save(user, "analysis", title, {
        "file_name": (file.filename or "upload.csv")[:200], "future_weeks": future_weeks, **result["input"],
    }, result, {**result["accounting"]["totals"], "rows": result["input"]["rows"],
                "period_start": result["input"]["period_start"], "period_end": result["input"]["period_end"]})
    return result


def _save(user: User, kind: str, title, input_: dict, result: dict, summary: dict, parent=None) -> dict:
    """Save to the user's history. A failure to save never hides the analysis; the caller is told."""
    if not history.enabled(user):
        return {"saved": False, "id": None, "error": None}
    try:
        return {"saved": True, "error": None,
                "id": history.save_run(user, kind, input_, result, summary, title=title, parent_run_id=parent)}
    except history.HistoryError as exc:
        return {"saved": False, "id": None, "error": str(exc)}


class Period(BaseModel):
    period_start: str = Field(max_length=32)
    electricity_kwh: Optional[float] = None
    diesel_litres: Optional[float] = None


class SimulateRequest(BaseModel):
    periods: List[Period] = Field(max_length=upload_analysis.MAX_SIM_PERIODS)
    electricity_change_pct: float = 0.0
    diesel_change_pct: float = 0.0
    solar_offset_kwh_per_period: float = 0.0
    save: bool = False                      # only when the user presses "Save scenario"
    title: Optional[str] = Field(None, max_length=200)
    parent_run_id: Optional[UUID] = None    # the analysis run this scenario belongs to


@app.post("/api/simulate")
def simulate(req: SimulateRequest, user: User = Depends(current_user)) -> dict:
    """What-if scenario on the periods returned by /api/analyze. Saved to history only if save=true."""
    try:
        result = upload_analysis.simulate_upload(
            [p.model_dump() for p in req.periods],
            electricity_change_pct=req.electricity_change_pct,
            diesel_change_pct=req.diesel_change_pct,
            solar_offset_kwh_per_period=req.solar_offset_kwh_per_period,
        )
    except upload_analysis.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if req.save:
        result["run"] = _save(user, "simulation", req.title, {**result["inputs"], "periods": len(req.periods)},
                              result, result["totals"], parent=req.parent_run_id)
    return result


class FactorChangeRequest(BaseModel):
    periods: List[Period] = Field(max_length=upload_analysis.MAX_SIM_PERIODS)
    year_a: Optional[int] = None
    year_b: Optional[int] = None
    fy_a: Optional[str] = Field(None, max_length=10)
    fy_b: Optional[str] = Field(None, max_length=10)


@app.get("/api/grid-factors")
def grid_factors(user: User = Depends(current_user)) -> list:
    return emission_factors.grid_factor_versions()


@app.post("/api/factor-change")
def factor_change_route(req: FactorChangeRequest, user: User = Depends(current_user)) -> dict:
    """Split the emission change between two years into an energy-use part and a grid-factor part."""
    periods = [p.model_dump() for p in req.periods]
    try:
        years = factor_change.years_available(periods)
        if None in (req.year_a, req.year_b, req.fy_a, req.fy_b):
            return {"years": years, "versions": emission_factors.grid_factor_versions()}
        res = factor_change.compare(periods, req.year_a, req.year_b, req.fy_a, req.fy_b)
    except factor_change.FactorChangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {**res, "years": years}


class MeasureIn(BaseModel):
    label: str = Field(max_length=100)
    acts_on: str = Field(max_length=20)
    saving_type: str = Field(max_length=30)
    saving_value: float
    capex_inr: float                         # cost of ONE unit of the measure
    max_units: int = Field(ge=1, le=upload_optimization.MAX_UNITS)
    exclusive_group: Optional[str] = Field(None, max_length=40)
    annual_saving_inr: Optional[float] = None  # optional, per unit, for payback


class OptimizeRequest(BaseModel):
    periods: List[Period] = Field(max_length=upload_analysis.MAX_SIM_PERIODS)
    granularity: str = Field(max_length=10)  # "weekly" or "monthly" (input.granularity_analysed)
    budget_inr: float
    measures: List[MeasureIn] = Field(max_length=upload_optimization.MAX_MEASURES)
    save: bool = False                       # only when the user presses "Save this plan"
    title: Optional[str] = Field(None, max_length=200)
    parent_run_id: Optional[UUID] = None


@app.post("/api/optimize")
def optimize(req: OptimizeRequest, user: User = Depends(current_user)) -> dict:
    """Best measures within a budget, from the user's own measure figures. Saved only if save=true."""
    try:
        result = upload_optimization.optimize_upload(
            [p.model_dump() for p in req.periods], req.granularity, req.budget_inr,
            [m.model_dump() for m in req.measures],
        )
    except upload_analysis.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if req.save:
        summary = {"budget_inr": result["budget_inr"], "tco2e_saved": result["optimal"]["tco2e_saved"],
                   "pct_of_baseline": result["optimal"]["pct_of_baseline"], "total_capex_inr": result["optimal"]["total_capex_inr"]}
        result["run"] = _save(user, "optimization", req.title,
                              {"budget_inr": req.budget_inr, "granularity": req.granularity,
                               "measures": [m.model_dump() for m in req.measures], "periods": len(req.periods)},
                              result, summary, parent=req.parent_run_id)
    return result


def _report_forecast(df, sources, granularity) -> dict:
    """The forecast is recomputed here from the periods (training takes a few seconds), never trusted from the browser."""
    if granularity != "weekly":
        return {"status": "skipped", "reason": "Monthly data has too few points for an ML forecast."}
    if len(df) < upload_analysis.MIN_WEEKS_FOR_ML:
        return {"status": "skipped", "reason": f"Only {len(df)} weeks of data; at least {upload_analysis.MIN_WEEKS_FOR_ML} are needed."}
    try:
        return upload_analysis.forecast(df.rename(columns={"period_start": "week_start"}), sources, upload_analysis.DEFAULT_FUTURE_WEEKS)
    except Exception as exc:  # a failed forecast must not block the rest of the report
        return {"status": "skipped", "reason": f"The forecast could not be computed ({type(exc).__name__})."}


def _report_factor_change(periods: list) -> Optional[dict]:
    """Default comparison for the report: the last two complete years, each with the grid factor of the fiscal year that ends in it."""
    try:
        years = factor_change.years_available(periods)
        if len(years) < 2:
            return None
        fys = sorted(emission_factors.GRID_FACTOR_BY_FY)

        def fy_for(year):
            ending = [f for f in fys if int(f[:4]) + 1 == year]
            return ending[0] if ending else min(fys, key=lambda f: abs(int(f[:4]) + 1 - year))
        ya, yb = years[-2:]
        return factor_change.compare(periods, ya, yb, fy_for(ya), fy_for(yb))
    except factor_change.FactorChangeError:
        return None


class ReportRequest(BaseModel):
    periods: List[Period] = Field(min_length=1, max_length=upload_analysis.MAX_SIM_PERIODS)
    granularity: str = Field(max_length=10)
    file_name: str = Field("", max_length=200)
    prepared_for: str = Field("", max_length=200)
    budget_inr: Optional[float] = None       # with measures: adds the Optimization and Recommended steps pages
    measures: List[MeasureIn] = Field(default_factory=list, max_length=upload_optimization.MAX_MEASURES)


@app.post("/api/report")
def report(req: ReportRequest, user: User = Depends(current_user)) -> Response:
    """PDF report. Numbers are recomputed here (activity x factor), not copied from the browser."""
    import tempfile
    from datetime import date

    import pandas as pd
    from report_pages import build_full_report
    periods = [p.model_dump() for p in req.periods]
    sources = [t for t in (upload_analysis.ELECTRICITY, upload_analysis.DIESEL) if any(p.get(t) is not None for p in periods)]
    if not sources:
        raise HTTPException(status_code=422, detail="The data has no electricity or diesel values.")
    try:
        df = pd.DataFrame([{"period_start": pd.Timestamp(p["period_start"]), **{t: float(p.get(t) or 0.0) for t in sources}} for p in periods])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="A period date could not be read.") from exc
    df = df.sort_values("period_start").reset_index(drop=True)
    analysis = {
        "input": {"rows": int(len(df)), "granularity_analysed": req.granularity,
                  "period_start": df["period_start"].iloc[0].strftime("%Y-%m-%d"), "period_end": df["period_start"].iloc[-1].strftime("%Y-%m-%d"),
                  "columns_used": {t: t for t in sources}},
        "factors_used": upload_analysis.factors_used(sources),
        "accounting": upload_analysis.account(df, "period_start", sources),
    }
    analysis["forecast"] = _report_forecast(df, sources, req.granularity)
    analysis["factor_change"] = _report_factor_change(periods)
    plan = None
    if req.budget_inr is not None and req.measures:
        try:
            plan = upload_optimization.optimize_upload(periods, req.granularity, req.budget_inr, [m.model_dump() for m in req.measures])
        except upload_analysis.UploadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    today = date.today()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "report.pdf")
        build_full_report(path, analysis, plan, None, prepared_for=req.prepared_for, data_source=req.file_name,
                          generated_on=f"{today.day} {today.strftime('%B %Y')}")
        pdf = open(path, "rb").read()
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="carbon-footprint-report.pdf"'})


@app.get("/api/runs")
def list_runs(limit: int = 50, user: User = Depends(current_user)) -> list:
    try:
        return history.list_runs(user, limit)
    except history.HistoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/runs/{run_id}")
def get_run(run_id: UUID, user: User = Depends(current_user)) -> dict:
    try:
        row = history.get_run(user, run_id)
    except history.HistoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return row


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: UUID, user: User = Depends(current_user)) -> dict:
    try:
        deleted = history.delete_run(user, run_id)
    except history.HistoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found.")
    return {"deleted": True}
