"""
report_extra.py

Report pages that follow "Results": Trend, Sources, Forecast, Model training, Sensitivity,
Grid factor and Data and method notes. Same style as report_pages.py (A4, ReportLab, plain words).

Every number is passed in or recomputed from the periods of the user's own file. Nothing is invented:
a page whose input is missing (for example no forecast for a short file) says so instead of guessing.
Sensitivity figures are inputs chosen by the report, not predictions.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from emission_factors import EMISSION_FACTORS, GRID_FACTOR_BY_FY, GRID_FACTOR_SOURCE, GRID_FACTOR_UNIT
from report_cover import H, INK, MUTED, TEAL, TEAL_DARK, W, _fonts, _page_header, _text_block, _wrap
from report_pages import C_S1, C_S2, GREY, LEFT, LINE, RIGHT, _fmt, _h2, _howto, _table, _title

MODEL_LABEL = {"naive_last_week": "Naive (last week)", "train_mean": "Training mean", "random_forest": "Random Forest",
               "xgboost": "XGBoost", "ridge": "Ridge regression"}
TARGET_LABEL = {"electricity_kwh": "Electricity", "diesel_litres": "Generator diesel"}
TARGET_UNIT = {"electricity_kwh": "kWh", "diesel_litres": "litres"}
FORECAST_COLOR = HexColor("#7c3aed")
WIDTH = RIGHT - LEFT


def _para(c, text: str, y: float, size: float = 10, color=INK, leading: Optional[float] = None, x: float = LEFT,
          width: float = WIDTH, font: str = "Body") -> float:
    lead = leading or size * 1.4
    lines = _wrap(c, text, font, size, width)
    _text_block(c, lines, x, y, font, size, color, lead)
    return y - lead * len(lines) - 4


def _bullets(c, items: List[str], y: float, size: float = 10) -> float:
    for it in items:
        y = _para(c, "• " + it, y, size, x=LEFT, width=WIDTH)
    return y


def _nice_top(v: float) -> float:
    if v <= 0:
        return 1.0
    step = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if v <= step * m:
            return step * m
    return step * 10


def _line_chart(c, x, y, w, h, series: List[dict], labels: List[str], unit: str = "") -> None:
    """Line chart. series: [{values: [float|None], color, dashed, width}]; y is the TOP of the plot area."""
    vals = [v for s in series for v in s["values"] if v is not None]
    top = _nice_top(max(vals) if vals else 1.0)
    base = y - h
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.setFont("Body", 8)
    c.setFillColor(MUTED)
    for i in range(5):
        gy = base + h * i / 4
        c.line(x, gy, x + w, gy)
        c.drawRightString(x - 4, gy - 3, f"{top * i / 4:,.0f}")
    n = max(1, len(labels) - 1)
    for s in series:
        c.setStrokeColor(s["color"])
        c.setLineWidth(s.get("width", 1.8))
        c.setDash(*s["dashed"]) if s.get("dashed") else c.setDash()
        pen = False
        p = None
        for i, v in enumerate(s["values"]):
            if v is None:
                if p is not None:
                    c.drawPath(p, stroke=1, fill=0)
                p, pen = None, False
                continue
            px, py = x + w * i / n, base + h * v / top
            if p is None:
                p = c.beginPath()
                p.moveTo(px, py)
            else:
                p.lineTo(px, py)
        if p is not None:
            c.drawPath(p, stroke=1, fill=0)
        c.setDash()
    c.setFillColor(MUTED)
    c.setFont("Body", 8)
    for i in sorted({0, len(labels) // 4, len(labels) // 2, (3 * len(labels)) // 4, len(labels) - 1}):
        if 0 <= i < len(labels):
            c.drawCentredString(x + w * i / n, base - 11, labels[i])
    if unit:
        c.drawString(x, y + 6, unit)


def _legend(c, x, y, items) -> None:
    for name, color, dashed in items:
        c.setStrokeColor(color)
        c.setLineWidth(2)
        c.setDash(4, 3) if dashed else c.setDash()
        c.line(x, y + 3, x + 18, y + 3)
        c.setDash()
        c.setFillColor(INK)
        c.setFont("Body", 9)
        c.drawString(x + 23, y, name)
        x += 30 + c.stringWidth(name, "Body", 9) + 10


def _stat_boxes(c, y, boxes) -> float:
    """Row of big-number boxes: [(label, value, sub)]."""
    n = len(boxes)
    gap = 10
    bw = (WIDTH - gap * (n - 1)) / n
    for i, (label, value, sub) in enumerate(boxes):
        x = LEFT + i * (bw + gap)
        c.setFillColor(HexColor("#ecfdf5"))
        c.setStrokeColor(HexColor("#99f6e4"))
        c.setLineWidth(0.8)
        c.roundRect(x, y - 66, bw, 66, 8, stroke=1, fill=1)
        c.setFillColor(MUTED)
        c.setFont("Body", 8.5)
        c.drawString(x + 10, y - 16, label.upper())
        c.setFillColor(TEAL_DARK)
        c.setFont("Title", 20)
        c.drawString(x + 10, y - 40, value)
        c.setFillColor(MUTED)
        c.setFont("Body", 8.5)
        c.drawString(x + 10, y - 56, sub)
    return y - 90


def _periods(analysis: dict) -> List[dict]:
    return analysis["accounting"]["periods"]


def _unit(analysis: dict) -> str:
    return "week" if analysis["input"]["granularity_analysed"] == "weekly" else "month"


# ── Trend ─────────────────────────────────────────────────────────────────────
def draw_trend_page(c: canvas.Canvas, analysis: dict, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    ps = _periods(analysis)
    unit = _unit(analysis)
    y = _title(c, "Emission trend", f"How total emissions moved from one {unit} to the next.")
    tot = [p["total_kg"] / 1000.0 for p in ps]
    k = 4
    roll = [None if i < k - 1 else sum(tot[i - k + 1:i + 1]) / k for i in range(len(tot))]
    peak_i, low_i = max(range(len(tot)), key=tot.__getitem__), min(range(len(tot)), key=tot.__getitem__)
    half = len(tot) // 2
    first, second = sum(tot[:half]) / max(1, half), sum(tot[half:]) / max(1, len(tot) - half)
    change = 100 * (second - first) / first if first else 0.0
    y = _stat_boxes(c, y, [
        (f"Average per {unit}", _fmt(sum(tot) / len(tot), 2), "tCO₂e"),
        ("Highest", _fmt(tot[peak_i], 2), ps[peak_i]["period_start"]),
        ("Lowest", _fmt(tot[low_i], 2), ps[low_i]["period_start"]),
        ("Second half vs first", f"{change:+.1f}%", "average per " + unit),
    ])
    y = _h2(c, f"Total emissions per {unit}", y)
    _line_chart(c, LEFT + 34, y - 6, WIDTH - 34, 170, [
        {"values": tot, "color": C_S2, "width": 1.6},
        {"values": roll, "color": C_S1, "width": 2.4},
    ], [p["period_start"] for p in ps], "tCO₂e")
    y -= 200
    _legend(c, LEFT + 34, y, [(f"Each {unit}", C_S2, False), (f"{k}-{unit} moving average (smooths out spikes)", C_S1, True)])
    y -= 18
    y = _howto(c, f"the thin line is each {unit}; the thick line averages {k} {unit}s, so the direction is easier to see. "
                  "A line that climbs means emissions are growing.", y)

    months: Dict[int, List[float]] = {}
    for p, v in zip(ps, tot):
        months.setdefault(datetime.strptime(p["period_start"], "%Y-%m-%d").month, []).append(v)
    y = _h2(c, f"Typical {unit} by calendar month", y - 4)
    avg = {m: sum(v) / len(v) for m, v in months.items()}
    top = max(avg.values()) or 1.0
    bw = WIDTH / 12
    ch = 70
    base = y - ch - 8
    names = "JFMAMJJASOND"
    for m in range(1, 13):
        bx = LEFT + (m - 1) * bw + bw * 0.15
        h = ch * avg.get(m, 0) / top
        c.setFillColor(C_S2 if m in avg else GREY)
        c.rect(bx, base, bw * 0.7, h if m in avg else 2, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.setFont("Body", 8.5)
        c.drawCentredString(bx + bw * 0.35, base - 11, names[m - 1])
    y = base - 26
    hi_m = max(avg, key=avg.get)
    lo_m = min(avg, key=avg.get)
    cal = "January February March April May June July August September October November December".split()
    y = _howto(c, f"each bar is the average {unit}ly emission in that month of the year. Taller bars are heavier months. "
                  f"In this file {cal[hi_m - 1]} is the heaviest ({_fmt(avg[hi_m], 2)} tCO₂e per {unit}) and "
                  f"{cal[lo_m - 1]} the lightest ({_fmt(avg[lo_m], 2)}). With under two years of data, a month's pattern "
                  "may just be one year's weather.", y)


# ── Sources ───────────────────────────────────────────────────────────────────
def draw_sources_page(c: canvas.Canvas, analysis: dict, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    ps = _periods(analysis)
    unit = _unit(analysis)
    y = _title(c, "Where the emissions come from", "Each source on its own: how much was used, how much it emitted, and why.")
    total_kg = sum(p["total_kg"] for p in ps) or 1.0
    fmap = {f["activity"]: f for f in analysis["factors_used"]}
    rows = []
    for key, scope_col in (("electricity_kwh", "scope2_kg"), ("diesel_litres", "scope1_kg")):
        if key not in fmap:
            continue
        vals = [p[key] for p in ps]
        kg = sum(p[scope_col] for p in ps)
        f = fmap[key]
        pk = max(range(len(vals)), key=vals.__getitem__)
        rows.append((TARGET_LABEL[key], f["scope"] if "scope" in f else ("Scope 2" if key == "electricity_kwh" else "Scope 1"),
                     f"{_fmt(sum(vals), 0)} {TARGET_UNIT[key]}", f"{_fmt(sum(vals) / len(vals), 0)}",
                     f"{_fmt(min(vals), 0)} to {_fmt(max(vals), 0)}", f"{f['factor']} {f['output']}", _fmt(kg / 1000.0, 2),
                     f"{100 * kg / total_kg:.0f}%", ps[pk]["period_start"]))
    y = _h2(c, "At a glance", y)
    y = _table(c, y, ("Source", "Scope", "Total used", f"Avg/{unit}", "Range", "Factor", "tCO₂e", "Share", "Peak"),
               [r[:8] + (r[8],) for r in rows], (64, 40, 70, 42, 70, 80, 36, 32, WIDTH - 434), size=8.5)
    y = _howto(c, f"'Range' is the lowest to highest use in one {unit}. 'Peak' is the {unit} with the highest use. "
                  "'Share' is the part of the total emissions that source causes.", y)

    y = _h2(c, "Share of total emissions", y - 4)
    for r in rows:
        share = float(r[7].rstrip("%")) / 100.0
        c.setFillColor(INK)
        c.setFont("Body", 10)
        c.drawString(LEFT, y, r[0])
        c.setFillColor(GREY)
        c.roundRect(LEFT + 110, y - 4, 280, 14, 3, stroke=0, fill=1)
        c.setFillColor(C_S2 if r[0] == "Electricity" else C_S1)
        c.roundRect(LEFT + 110, y - 4, max(2, 280 * share), 14, 3, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.drawString(LEFT + 400, y, f"{r[7]}  ({r[6]} tCO₂e)")
        y -= 22
    y = _howto(c, "a longer filled bar means that source is a bigger part of the footprint, so cutting it matters more.", y)

    y = _h2(c, "Why the numbers look like this", y - 4)
    pts = []
    for key in ("electricity_kwh", "diesel_litres"):
        if key in fmap:
            f = fmap[key]
            pts.append(f"{TARGET_LABEL[key]}: emission = activity x factor = {_fmt(sum(p[key] for p in ps), 0)} {TARGET_UNIT[key]} x "
                       f"{f['factor']} {f['output']}. Factor source: {f['source']} ({f['version']}).")
    if "electricity_kwh" in fmap and "diesel_litres" in fmap:
        e = sum(p["scope2_kg"] for p in ps)
        d = sum(p["scope1_kg"] for p in ps)
        big, small = ("electricity", "diesel") if e >= d else ("diesel", "electricity")
        pts.append(f"Most emissions come from {big}. Reducing {big} use has a larger effect than the same percentage cut in {small}.")
    pts.append("Diesel has a much higher factor per unit than electricity, so even a small diesel volume can matter.")
    _bullets(c, pts, y, 10)


# ── Forecast ──────────────────────────────────────────────────────────────────
def _skipped_page(c, page_no: int, reason: str) -> None:
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "Forecast", "A look ahead from the weekly pattern in your data.")
    y = _para(c, "No forecast was made for this file.", y, 12, TEAL_DARK, font="BodyBold")
    y = _para(c, reason, y, 10.5)
    _para(c, "Carbon accounting (the other pages) does not depend on a forecast. Upload weekly or daily data with at least "
             "26 weeks to get one.", y, 10.5, MUTED)


def draw_forecast_page(c: canvas.Canvas, analysis: dict, target: str, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    fc = analysis["forecast"]["targets"][target]
    label, unit = TARGET_LABEL[target], TARGET_UNIT[target]
    y = _title(c, f"Forecast: {label.lower()}", f"The next {len(fc['future'])} weeks, with the models checked on weeks they had not seen.")
    ps = _periods(analysis)
    hist = [p[target] for p in ps][-30:]
    hist_dates = [p["period_start"] for p in ps][-30:]
    chosen = fc["chosen_model"]
    back = {b["week_start"]: b[chosen] for b in fc["backtest"]}
    fut = fc["future"]
    labels = hist_dates + [f["week_start"] for f in fut]
    s_act = hist + [None] * len(fut)
    s_back = [back.get(d) for d in hist_dates] + [None] * len(fut)
    last = hist[-1]
    s_fut = [None] * (len(hist) - 1) + [last] + [f["predicted"] for f in fut]
    y = _h2(c, f"{label} ({unit} per week)", y)
    _line_chart(c, LEFT + 38, y - 6, WIDTH - 38, 160, [
        {"values": s_act, "color": INK, "width": 2.0},
        {"values": s_back, "color": C_S2, "width": 1.4},
        {"values": s_fut, "color": FORECAST_COLOR, "width": 2.4, "dashed": (5, 3)},
    ], labels, unit)
    y -= 188
    _legend(c, LEFT + 38, y, [("Actual", INK, False), (f"{MODEL_LABEL[chosen]} on test weeks", C_S2, False), ("Forecast", FORECAST_COLOR, True)])
    y -= 18
    y = _howto(c, "the black line is what happened. The teal line is what the chosen method predicted for the last weeks "
                  "when it had not seen them; the closer to black, the better. The dashed purple line is the forecast.", y)

    emis = analysis["forecast"]["emission_future"]
    cmp_ = "beats" if fc["beats_naive"] else "did not beat"
    y = _para(c, f"Method used: {MODEL_LABEL[chosen]}. The best learning model {cmp_} the simple 'same as last week' guess by "
                 f"the required margin, so {'it is used' if fc['beats_naive'] else 'the forecast repeats the last observed week'}. "
                 f"Forecast total for the next {len(fut)} weeks: {_fmt(sum(f['predicted'] for f in fut), 0)} {unit}.", y, 10)
    y = _h2(c, "How well each method did on the held-out weeks", y - 2)
    best = min(m["MAE"] for m in fc["metrics"])
    rows = [(MODEL_LABEL[m["model"]] + ("  (baseline)" if m["model"] == "naive_last_week" else "") + ("  (best)" if m["MAE"] == best else ""),
             _fmt(m["MAE"], 1), _fmt(m["RMSE"], 1), _fmt(m["R2"], 2)) for m in fc["metrics"]]
    y = _table(c, y, ("Method", f"MAE ({unit})", f"RMSE ({unit})", "R²"), rows, (200, 100, 100, WIDTH - 400), size=9.5)
    y = _howto(c, "MAE is the average miss in the same unit as the data; lower is better. RMSE punishes big misses more. "
                  "R² near 1 means the pattern is captured, near 0 or below means it is not. (best) marks the lowest MAE. "
                  f"Split by time: {fc['train_weeks']} earlier weeks to learn, the last {fc['test_weeks']} weeks to test, no shuffling.", y)
    if fc["warnings"]:
        y = _para(c, " ".join(fc["warnings"]), y, 9.5, MUTED)
    _para(c, f"The emission forecast is not learned: it is the predicted activity x the same emission factor. "
             f"Forecast emission for these weeks: {_fmt(sum(e['total_kg'] for e in emis) / 1000.0, 2)} tCO₂e (all sources).", y, 9.5, MUTED)


# ── Training ──────────────────────────────────────────────────────────────────
def draw_training_page(c: canvas.Canvas, analysis: dict, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "How the models were trained", "Three learning methods were trained on this file and compared fairly.")
    y = _bullets(c, [
        "Random Forest, XGBoost and Ridge regression each tried several settings. Every setting was scored by rolling validation: "
        "train on the early weeks, test on the next block, move forward, repeat. Time order is never shuffled.",
        "Settings were chosen on the training weeks only. The final test weeks were kept apart and used once, for an honest score.",
        "The model learns weekly electricity and diesel use (activity), never emissions. Emissions are then activity x emission factor.",
        "A model is used only if it beats the naive 'same as last week' guess by at least 5% on the test weeks. Otherwise the naive guess is used.",
        "Each new file is trained from scratch; nothing learned from another file is reused. The summary below is kept in your History.",
    ], y, 10)
    for target, fc in analysis["forecast"]["targets"].items():
        tr = fc["training"]
        y = _h2(c, f"{TARGET_LABEL[target]}: selection log", y - 4)
        rows = []
        for m in tr["models"]:
            best = ", ".join(f"{k} {v}" for k, v in m["best_settings"].items())
            rows.append((m["label"], str(m["settings_tried"]), best, _fmt(m["validation_mae"], 1), _fmt(m["test_mae"], 1), f"{m['seconds']:.2f}"))
        rows.append(("Naive (last week)", "-", "-", _fmt(tr["naive_validation_mae"], 1), _fmt([x for x in fc["metrics"] if x["model"] == "naive_last_week"][0]["MAE"], 1), "-"))
        y = _table(c, y, ("Model", "Tried", "Best setting", "Validation MAE", "Test MAE", "Secs"), rows,
                   (110, 40, 175, 78, 60, WIDTH - 463), size=8.5)
        y = _para(c, f"Chosen for the forecast: {MODEL_LABEL[fc['chosen_model']]}. Total training time {tr['seconds']:.1f} s.", y, 9.5, MUTED)
    _howto(c, "validation MAE is the average miss during rolling validation (used to pick the setting and the model); "
              "test MAE is the miss on the final held-out weeks. Lower is better for both.", y)


# ── Sensitivity ───────────────────────────────────────────────────────────────
def draw_sensitivity_page(c: canvas.Canvas, analysis: dict, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "What if use changes?", "A simple look at how the total moves if electricity or diesel use goes up or down.")
    fmap = {f["activity"]: f for f in analysis["factors_used"]}
    ps = _periods(analysis)
    e_kwh = sum(p.get("electricity_kwh", 0.0) for p in ps)
    d_l = sum(p.get("diesel_litres", 0.0) for p in ps)
    fe = fmap["electricity_kwh"]["factor"] if "electricity_kwh" in fmap else 0.0
    fd = fmap["diesel_litres"]["factor"] if "diesel_litres" in fmap else 0.0
    base = (e_kwh * fe + d_l * fd) / 1000.0
    steps = (-20, -10, 0, 10, 20)
    cols = ["Electricity ↓ / Diesel →"] + [f"{s:+d}%" for s in steps]
    rows = []
    for se in steps:
        rows.append(tuple([f"{se:+d}%"] + [_fmt((e_kwh * (1 + se / 100) * fe + d_l * (1 + sd / 100) * fd) / 1000.0, 1) for sd in steps]))
    y = _h2(c, "Total emissions (tCO2e) for each combination", y)
    y = _table(c, y, tuple(cols), rows, (130,) + ((WIDTH - 130) / 5,) * 5, size=9.5)
    y = _howto(c, f"rows are the change in electricity use, columns the change in diesel use. The middle cell ({_fmt(base, 1)} tCO₂e) is "
                  "today's total. Move up and left for lower emissions.", y)
    y = _h2(c, "Saving from a 10% cut in one source", y - 4)
    es, ds = e_kwh * 0.10 * fe / 1000.0, d_l * 0.10 * fd / 1000.0
    rows2 = []
    if fe:
        rows2.append(("Electricity use down 10%", _fmt(es, 2), f"{100 * es / base:.1f}%" if base else "-"))
    if fd:
        rows2.append(("Diesel use down 10%", _fmt(ds, 2), f"{100 * ds / base:.1f}%" if base else "-"))
    y = _table(c, y, ("Change", "Saves (tCO₂e)", "Of the total"), rows2, (230, 130, WIDTH - 360), size=10)
    _para(c, "These figures are what-if inputs chosen for this report, not predictions of what any measure will achieve. They use the same "
             "rule as everywhere else: emission = activity x emission factor. The Simulation and Optimization pages let you set your own numbers.",
          y, 9.5, MUTED)


# ── Grid factor ───────────────────────────────────────────────────────────────
def draw_factor_page(c: canvas.Canvas, analysis: dict, page_no: int, change: Optional[dict] = None) -> None:
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "The grid factor over the years", "Why the same electricity gives a different emission from one year to the next.")
    y = _para(c, "Emission = energy used x emission factor. India adds more clean power every year, so each unit of grid electricity "
                 "carries less carbon than before. That part is outside your control; the other part, how much energy you use, is yours.", y, 10)
    rows = [(f"FY {fy}", f"{v['factor']:.3f}", GRID_FACTOR_UNIT, v["first_published"]) for fy, v in sorted(GRID_FACTOR_BY_FY.items())]
    y = _h2(c, "Documented grid factors used by this app", y - 10)
    y = _table(c, y, ("Year", "Factor", "Unit", "First published in"), rows, (90, 90, 120, WIDTH - 300), size=10)
    y = _para(c, f"Source: {GRID_FACTOR_SOURCE}. These values are fixed by the app; users never type them. "
                 f"This report's electricity figures use {EMISSION_FACTORS['electricity']['factor']} ({EMISSION_FACTORS['electricity']['version']}).", y, 9, MUTED)
    if not change:
        _para(c, "A split of your own change into 'energy use' and 'grid' needs two complete calendar years in the file; this file does not have them.",
              y - 4, 10)
        return
    y = _h2(c, f"Your change, {change['year_a']} to {change['year_b']}", y - 4)
    t = change["totals"]
    y = _stat_boxes(c, y, [("Total change", f"{t['change_t']:+,.1f}", "tCO₂e"),
                           ("Your energy use", f"{t['activity_effect_t']:+,.1f}", "tCO₂e"),
                           ("The grid factor", f"{t['factor_effect_t']:+,.1f}", "tCO₂e")])
    y = _bullets(c, change["sentences"], y, 10)
    _howto(c, f"electricity was counted with {change['grid_factor_a']} for {change['year_a']} (FY {change['fy_a']}) and "
              f"{change['grid_factor_b']} for {change['year_b']} (FY {change['fy_b']}). The two parts add up exactly to the total change. "
              "Diesel has no yearly factor series, so all of its change counts as energy use.", y)


# ── Notes ─────────────────────────────────────────────────────────────────────
def draw_notes_page(c: canvas.Canvas, analysis: dict, page_no: int, scope3: Optional[dict] = None,
                    inventory: Optional[dict] = None, energy_audit: Optional[dict] = None) -> None:
    _fonts()
    _page_header(c, page_no)
    inp = analysis["input"]
    y = _title(c, "Data, method and limits", "What went in, how it was checked, and what this report does not cover.")
    y = _h2(c, "The data", y)
    items = [f"{inp['rows']} {inp['granularity_analysed']} rows from {inp['period_start']} to {inp['period_end']}.",
             "Columns used: " + ", ".join(f"{k} = '{v}'" for k, v in inp["columns_used"].items()) + "."]
    items += list(inp.get("notes") or [])
    y = _bullets(c, items, y, 9.5)
    y = _h2(c, "Emission factors used", y - 10)
    rows = [(f["activity"].replace("_", " "), str(f["factor"]), f["output"], f["version"], f["source"]) for f in analysis["factors_used"]]
    y = _table(c, y, ("Activity", "Factor", "Unit", "Version", "Source"), rows, (80, 40, 70, 90, WIDTH - 280), size=8.5)
    y = _h2(c, "Limits to keep in mind", y - 10)
    y = _bullets(c, [
        ("The weekly pages count only electricity (Scope 2) and generator diesel (Scope 1), the two columns in the file. Other "
         "sources appear only as yearly totals on the 'Full campus footprint' page, with no weekly breakdown or forecast.") if inventory else
        "Only electricity (Scope 2) and generator diesel (Scope 1) are in the file, so other sources (travel, waste, water) are not counted"
        + (" except student commuting, which comes from a survey estimate." if scope3 else "."),
        "A forecast is a pattern-based estimate, not a promise. When the models do not beat 'same as last week', that is what is shown.",
        "Results depend on the quality of the uploaded numbers; the file is checked for gaps and bad values but not audited.",
        "Scenario figures are inputs chosen to illustrate, not predictions of what a measure will achieve.",
    ] + ([
        "The Energy Audit compares yearly campus electricity with proxy benchmarks (no official EPI exists for educational buildings) and "
        "uses an assumed COP for the air-conditioning estimate. Its suggestions are things to check, not guaranteed savings.",
    ] if energy_audit else []), y, 9.5)
    y = _h2(c, "References", y - 10)
    _bullets(c, [
        "Central Electricity Authority (CEA), CO₂ Baseline Database for the Indian Power Sector, User Guide (versions 19.0 to 22.0).",
        "IPCC 2006 Guidelines for National Greenhouse Gas Inventories (fuel emission factors).",
        "GHG Protocol Corporate Accounting and Reporting Standard (Scope 1, 2 and 3 definitions).",
    ] + ([
        "WRI, TERI, CII, India GHG Program (2015), road transport emission factors.",
        "UK DEFRA greenhouse gas conversion factors (2024), diesel passenger vehicle.",
        "IPCC 2019 Refinement to the 2006 Guidelines, domestic wastewater (Tier 1).",
        "KKWIEER Carbon Footprint Master Data FY 2025-26, and the college survey carried out by the Young Indians team.",
    ] if inventory else []) + ([
        f"{r['source']} ({r['version']})." for r in energy_audit["references"]
    ] + ["Sources for each Energy Audit suggestion are given on the suggestion pages."] if energy_audit else []), y, 9.5)
