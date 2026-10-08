"""
report_pages.py

Report pages 3 to 5 (A4, ReportLab): At a glance, What was counted and how, Results.

Every number comes from the caller: `analysis` is the result of upload_analysis.analyze()
(accounting totals and per-period rows, factors_used), `scope3` is an optional dict from
commuting_scope3() (the survey estimate). Nothing is computed here except sums and shares of
what was passed in, and no figure is invented: a part without data is simply left out and the
page says so.

Charts are drawn directly with ReportLab (no extra libraries) in plain style: big numbers,
one donut, simple bars, each with a one-line "how to read this".
"""

from __future__ import annotations

import csv
import json
import math
import os
from typing import List, Optional

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from report_cover import (H, INK, MUTED, ROOT, TEAL, TEAL_DARK, W, _fonts, _page_header, _text_block, _wrap)

C_S1 = HexColor("#f59e0b")     # Scope 1 amber
C_S2 = HexColor("#0f766e")     # Scope 2 teal
C_S3 = HexColor("#6366f1")     # Scope 3 indigo
SCOPE_COLORS = {"Scope 1": C_S1, "Scope 2": C_S2, "Scope 3": C_S3}
LEFT, RIGHT = 48, W - 48
GREY = HexColor("#f1f5f9")
LINE = HexColor("#cbd5e1")


def commuting_scope3(summary_path: Optional[str] = None, by_mode_path: Optional[str] = None) -> dict:
    """Load the survey estimate written by scripts/scope3_commuting.py."""
    base = os.path.join(ROOT, "outputs", "scope3")
    s = json.load(open(summary_path or os.path.join(base, "commuting_summary.json"), encoding="utf-8"))
    modes = []
    with open(by_mode_path or os.path.join(base, "commuting_by_mode.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            modes.append({"mode": r["mode"], "responses": int(r["responses"]), "tco2e": float(r["tco2e"]),
                          "share_pct": float(r["share_pct"])})
    scale = s["scale"]
    for m in modes:
        m["tco2e_scaled"] = m["tco2e"] * scale
    return {"tco2e": s["estimated_tco2e_per_year"], "population": s["population"],
            "responses_used": s["responses_used"], "responses_total": s["responses_total"],
            "excluded": s["excluded"], "modes": modes, "factors": s["factors_kg_per_km"],
            "sensitivity": s["sensitivity_tco2e"]}


def _fmt(v: float, d: int = 1) -> str:
    return f"{v:,.{d}f}"


def _title(c, text: str, sub: str = "") -> float:
    c.setFillColor(INK)
    c.setFont("Title", 27)
    c.drawString(LEFT, H - 118, text)
    c.setStrokeColor(TEAL)
    c.setLineWidth(2.5)
    c.line(LEFT, H - 130, LEFT + 56, H - 130)
    y = H - 156
    if sub:
        lines = _wrap(c, sub, "Body", 11, RIGHT - LEFT)
        _text_block(c, lines, LEFT, y, "Body", 11, MUTED, 15)
        y -= 15 * len(lines)
    return y - 14


def _h2(c, text: str, y: float) -> float:
    c.setFillColor(INK)
    c.setFont("Title", 15)
    c.drawString(LEFT, y, text)
    return y - 18


def _howto(c, text: str, y: float, x: float = LEFT, width: float = RIGHT - LEFT) -> float:
    lines = _wrap(c, "How to read this: " + text, "Body", 9.5, width)
    _text_block(c, lines, x, y, "Body", 9.5, MUTED, 13)
    return y - 13 * len(lines) - 6


def _scopes(analysis: dict, scope3: Optional[dict]) -> List[dict]:
    t = analysis["accounting"]["totals"]
    out = [{"name": "Scope 1", "what": "Generator diesel", "t": t["scope1_tco2e"]},
           {"name": "Scope 2", "what": "Purchased electricity", "t": t["scope2_tco2e"]}]
    if scope3:
        out.append({"name": "Scope 3", "what": "Student commuting (survey)", "t": scope3["tco2e"]})
    return out


def _arc(c, cx, cy, r_out, r_in, a0, a1, color):
    """Filled ring segment from angle a0 to a1 (degrees, 0 = 12 o'clock, clockwise)."""
    p = c.beginPath()
    steps = max(2, int(abs(a1 - a0) / 3))

    def pt(r, i):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        return cx + r * math.sin(a), cy + r * math.cos(a)

    pts = [pt(r_out, i) for i in range(steps + 1)] + [pt(r_in, i) for i in range(steps, -1, -1)]
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    c.setFillColor(color)
    c.setStrokeColor(HexColor("#ffffff"))
    c.setLineWidth(1.5)
    c.drawPath(p, stroke=1, fill=1)


def draw_glance_page(c: canvas.Canvas, analysis: dict, scope3: Optional[dict] = None, page_no: int = 3,
                     inventory: Optional[dict] = None) -> None:
    """Page 3: the headline numbers and one donut."""
    _fonts()
    _page_header(c, page_no)
    scopes = _scopes(analysis, scope3)
    total = sum(s["t"] for s in scopes)
    inp = analysis["input"]
    y = _title(c, "At a glance",
               f"Greenhouse gas emissions for {inp['period_start']} to {inp['period_end']}, in tonnes of CO₂e "
               "(carbon dioxide equivalent).")

    c.setFillColor(HexColor("#ecfdf5"))
    c.setStrokeColor(HexColor("#99f6e4"))
    c.setLineWidth(0.8)
    c.roundRect(LEFT, y - 92, RIGHT - LEFT, 92, 10, stroke=1, fill=1)
    c.setFillColor(TEAL_DARK)
    c.setFont("Title", 44)
    c.drawString(LEFT + 20, y - 58, _fmt(total))
    c.setFont("BodyBold", 14)
    c.drawString(LEFT + 20 + c.stringWidth(_fmt(total), "Title", 44) + 10, y - 58, "tCO₂e in total")
    c.setFillColor(MUTED)
    c.setFont("Body", 10.5)
    c.drawString(LEFT + 20, y - 79, "Adds up " + " + ".join(s["name"] for s in scopes) + ".")
    y -= 92 + 20

    gap = 10
    n = len(scopes)
    cw = (RIGHT - LEFT - gap * (n - 1)) / n
    for i, s in enumerate(scopes):
        x = LEFT + i * (cw + gap)
        c.setFillColor(GREY)
        c.roundRect(x, y - 78, cw, 78, 8, stroke=0, fill=1)
        c.setFillColor(SCOPE_COLORS[s["name"]])
        c.roundRect(x, y - 78, 5, 78, 2, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.setFont("BodyBold", 10.5)
        c.drawString(x + 16, y - 20, s["name"])
        c.setFont("Body", 9.5)
        c.drawString(x + 16, y - 33, s["what"])
        c.setFillColor(INK)
        c.setFont("Title", 24)
        c.drawString(x + 16, y - 62, _fmt(s["t"]))
        c.setFont("Body", 9.5)
        c.setFillColor(MUTED)
        c.drawString(x + 16 + c.stringWidth(_fmt(s["t"]), "Title", 24) + 5, y - 62, "tCO₂e")
    y -= 78 + 28

    y = _h2(c, "Where the emissions come from", y)
    cx, cy, ro, ri = LEFT + 100, y - 105, 92, 56
    angle = 0.0
    for s in scopes:
        sweep = 360.0 * s["t"] / total if total else 0
        if sweep > 0:
            _arc(c, cx, cy, ro, ri, angle, angle + min(sweep, 359.99), SCOPE_COLORS[s["name"]])
        angle += sweep
    c.setFillColor(INK)
    c.setFont("Title", 20)
    c.drawCentredString(cx, cy - 2, _fmt(total, 0))
    c.setFont("Body", 9.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, cy - 15, "tCO₂e")
    lx, ly = LEFT + 230, y - 38
    for s in scopes:
        c.setFillColor(SCOPE_COLORS[s["name"]])
        c.roundRect(lx, ly - 3, 12, 12, 3, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("BodyBold", 11.5)
        share = 100 * s["t"] / total if total else 0
        c.drawString(lx + 20, ly, f"{s['name']}: {share:.0f}%")
        c.setFillColor(MUTED)
        c.setFont("Body", 10)
        c.drawString(lx + 20, ly - 14, f"{s['what']}, {_fmt(s['t'])} tCO₂e")
        ly -= 42
    y = cy - ro - 22
    biggest = max(scopes, key=lambda s: s["t"])
    y = _howto(c, "each coloured slice is one source of emissions; the bigger the slice, the more it adds. "
                  f"The largest here is {biggest['what'].lower()} ({biggest['name']}).", y)

    notes = []
    if inventory:
        notes.append("The weekly figures on this page cover generator diesel and electricity only. Scope 3 and the rest of "
                     "Scope 1 (college buses, wastewater) are yearly totals on the 'Full campus footprint' page.")
    elif not scope3:
        notes.append("Scope 3 is not included in this report because no data for it was provided.")
    else:
        notes.append(f"Scope 3 covers student commuting only. It is an estimate from a survey of "
                     f"{scope3['responses_used']:,} students, scaled to {scope3['population']:,} students. Other Scope 3 "
                     "sources (waste, business travel, field visits) are not part of this report.")
    notes.append("Scope 1 and 2 here come from the activity data in the uploaded file; nothing was estimated or filled in.")
    c.setFillColor(INK)
    c.setFont("BodyBold", 10)
    c.drawString(LEFT, y - 6, "Please note")
    _text_block(c, [ln for n_ in notes for ln in _wrap(c, "• " + n_, "Body", 10, RIGHT - LEFT)],
                LEFT, y - 22, "Body", 10, INK, 14)


def _table(c, y, cols, rows, widths, size=9.5, head_color=TEAL_DARK):
    """Simple wrapped-cell table; returns the y under the table."""
    x0 = LEFT
    c.setFillColor(head_color)
    c.roundRect(x0, y - 20, sum(widths), 20, 4, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("BodyBold", size)
    x = x0
    for col, w in zip(cols, widths):
        c.drawString(x + 6, y - 14, col)
        x += w
    y -= 20
    for i, row in enumerate(rows):
        cells = [_wrap(c, str(v), "Body", size, w - 12) or [""] for v, w in zip(row, widths)]
        h = 8 + 12.5 * max(len(cl) for cl in cells)
        if i % 2 == 0:
            c.setFillColor(GREY)
            c.rect(x0, y - h, sum(widths), h, stroke=0, fill=1)
        x = x0
        for cl, w in zip(cells, widths):
            _text_block(c, cl, x + 6, y - 12, "Body", size, INK, 12.5)
            x += w
        y -= h
    return y - 10


def draw_method_page(c: canvas.Canvas, analysis: dict, scope3: Optional[dict] = None, page_no: int = 4) -> None:
    """Page 4: how the numbers were made, with every factor's source and version."""
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "What was counted and how",
               "Every emission figure in this report is worked out with one simple rule.")

    bw, g = 150, 28
    x0 = LEFT + (RIGHT - LEFT - (3 * bw + 2 * g)) / 2
    items = (("Activity", "how much was used", "e.g. kWh of electricity"),
             ("Emission factor", "CO₂e per unit used", "from a published source"),
             ("Emission", "what is reported", "kg, then tonnes CO₂e"))
    for i, (t, a, b) in enumerate(items):
        x = x0 + i * (bw + g)
        c.setFillColor(HexColor("#ecfdf5") if i < 2 else HexColor("#ccfbf1"))
        c.setStrokeColor(HexColor("#99f6e4"))
        c.roundRect(x, y - 62, bw, 62, 8, stroke=1, fill=1)
        c.setFillColor(TEAL_DARK)
        c.setFont("BodyBold", 13)
        c.drawCentredString(x + bw / 2, y - 22, t)
        c.setFillColor(INK)
        c.setFont("Body", 10)
        c.drawCentredString(x + bw / 2, y - 37, a)
        c.setFillColor(MUTED)
        c.drawCentredString(x + bw / 2, y - 50, b)
        if i < 2:
            c.setFillColor(TEAL)
            c.setFont("BodyBold", 20)
            c.drawCentredString(x + bw + g / 2, y - 38, "×" if i == 0 else "=")
    y -= 62 + 18

    fac = analysis["factors_used"]
    totals = {}
    for p in analysis["accounting"]["periods"]:
        for k in ("electricity_kwh", "diesel_litres"):
            if k in p:
                totals[k] = totals.get(k, 0.0) + p[k]
    ex = next((f for f in fac if f["activity"] in totals), None)
    if ex:
        act = totals[ex["activity"]]
        y = _howto(c, f"for example, {_fmt(act, 0)} {ex['unit']} × {ex['factor']} {ex['output']} = "
                      f"{_fmt(act * ex['factor'] / 1000)} tCO₂e ({ex['scope']}).", y)

    y = _h2(c, "Emission factors used", y - 4)
    rows = []
    for f in fac:
        rows.append((f["scope"], f"{f['factor']} {f['output']}", f["source"],
                     f["version"] + ("" if f["verified"] else " (not yet verified)")))
    if scope3:
        fx = scope3["factors"]
        for mode in ("Two-wheeler", "Bus", "Auto / Cab", "Car"):
            if mode in fx:
                rows.append(("Scope 3", f"{fx[mode]} kg CO₂/km ({mode.lower()})",
                             "India GHG Program (WRI, TERI, CII), road transport emission factors", "2015"))
    y = _table(c, y, ("Scope", "Factor", "Source", "Version"), rows, (52, 135, 220, RIGHT - LEFT - 407))

    if scope3:
        y = _h2(c, "How student commuting was estimated", y - 2)
        pts = [f"A survey of students gave one-way distance, days per week and mode of travel. {scope3['responses_used']:,} of "
               f"{scope3['responses_total']:,} responses were usable.",
               "Per student: distance × 2 (to and back) × days per week × 41 academic weeks × factor. "
               f"The sample total is scaled up to {scope3['population']:,} students.",
               "Walking and cycling count as zero. Carpooling and electric two-wheelers are not adjusted, "
               "because no sourced factor was given."]
        lines = [ln for p_ in pts for ln in _wrap(c, "• " + p_, "Body", 10, RIGHT - LEFT)]
        _text_block(c, lines, LEFT, y, "Body", 10, INK, 14)
    c.setFillColor(MUTED)
    c.setFont("Body", 9)
    c.drawString(LEFT, 52, "kg CO₂e = kilograms of carbon dioxide equivalent. 1 tonne = 1,000 kg.")


def _stacked_bars(c, x, y, w, h, periods):
    """Stacked bars per period: Scope 2 (bottom) and Scope 1 (top), in tCO2e."""
    vals = [(p["scope2_kg"] / 1000.0, p["scope1_kg"] / 1000.0) for p in periods]
    top = max((a + b) for a, b in vals) or 1.0
    step = 10 ** math.floor(math.log10(top))
    top_axis = step * 10
    for m in (1, 2, 2.5, 5, 10):
        if top <= step * m:
            top_axis = step * m
            break
    base = y - h
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.setFont("Body", 8)
    c.setFillColor(MUTED)
    for i in range(5):
        gy = base + h * i / 4
        c.line(x, gy, x + w, gy)
        c.drawRightString(x - 4, gy - 3, f"{top_axis * i / 4:,.0f}")
    n = len(vals)
    bw = w / n
    for i, (s2, s1) in enumerate(vals):
        bx = x + i * bw + bw * 0.12
        ww = bw * 0.76
        h2 = h * s2 / top_axis
        h1 = h * s1 / top_axis
        c.setFillColor(C_S2)
        c.rect(bx, base, ww, h2, stroke=0, fill=1)
        c.setFillColor(C_S1)
        c.rect(bx, base + h2, ww, h1, stroke=0, fill=1)
    c.setFillColor(MUTED)
    c.setFont("Body", 8)
    for i in sorted({0, n // 4, n // 2, (3 * n) // 4, n - 1}):
        c.drawCentredString(x + i * bw + bw / 2, base - 11, periods[i]["period_start"])


def draw_results_page(c: canvas.Canvas, analysis: dict, scope3: Optional[dict] = None, page_no: int = 5) -> None:
    """Page 5: the numbers per scope, emissions over time, Scope 3 by mode."""
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "Results", "The same totals as the first page, with the detail behind them.")
    scopes = _scopes(analysis, scope3)
    total = sum(s["t"] for s in scopes)

    acts = {}
    for p in analysis["accounting"]["periods"]:
        for k in ("electricity_kwh", "diesel_litres"):
            if k in p:
                acts[k] = acts.get(k, 0.0) + p[k]
    fmap = {f["activity"]: f for f in analysis["factors_used"]}
    rows = []
    for s in scopes:
        if s["name"] == "Scope 2" and "electricity_kwh" in acts:
            rows.append((s["name"], s["what"], f"{_fmt(acts['electricity_kwh'], 0)} kWh",
                         f"{fmap['electricity_kwh']['factor']}", _fmt(s["t"], 2)))
        elif s["name"] == "Scope 1" and "diesel_litres" in acts:
            rows.append((s["name"], s["what"], f"{_fmt(acts['diesel_litres'], 0)} litres",
                         f"{fmap['diesel_litres']['factor']}", _fmt(s["t"], 2)))
        elif s["name"] == "Scope 3":
            rows.append((s["name"], s["what"], f"{scope3['responses_used']:,} responses, scaled to "
                         f"{scope3['population']:,} students", "by mode", _fmt(s["t"], 2)))
        else:
            rows.append((s["name"], s["what"], "-", "-", _fmt(s["t"], 2)))
    rows.append(("Total", "", "", "", _fmt(total, 2)))
    y = _table(c, y, ("Scope", "Source", "Activity", "Factor", "tCO₂e"), rows, (52, 140, 175, 60, RIGHT - LEFT - 427))

    periods = analysis["accounting"]["periods"]
    unit = "week" if analysis["input"]["granularity_analysed"] == "weekly" else "month"
    y = _h2(c, f"Emissions over time ({unit}s)", y - 2)
    chart_h = 150
    _stacked_bars(c, LEFT + 30, y - 4, RIGHT - LEFT - 30, chart_h, periods)
    y -= chart_h + 36
    c.setFillColor(C_S2)
    c.roundRect(LEFT + 30, y + 2, 10, 10, 2, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Body", 9.5)
    c.drawString(LEFT + 45, y + 3, "Scope 2, electricity")
    c.setFillColor(C_S1)
    c.roundRect(LEFT + 170, y + 2, 10, 10, 2, stroke=0, fill=1)
    c.setFillColor(INK)
    c.drawString(LEFT + 185, y + 3, "Scope 1, generator diesel")
    c.setFillColor(MUTED)
    c.drawRightString(RIGHT, y + 3, f"tCO₂e per {unit}")
    y -= 14
    y = _howto(c, f"each bar is one {unit}; a taller bar means more emissions in that {unit}. "
                  "Dates are the start of each period.", y)

    if scope3:
        y = _h2(c, "Student commuting by way of travel", y - 4)
        biggest = max(m["tco2e_scaled"] for m in scope3["modes"]) or 1.0
        label_w, bar_w = 90, 250
        for m in sorted(scope3["modes"], key=lambda m: -m["tco2e_scaled"]):
            c.setFillColor(INK)
            c.setFont("Body", 10)
            c.drawString(LEFT, y, m["mode"])
            c.setFillColor(C_S3)
            c.roundRect(LEFT + label_w, y - 3, max(1.5, bar_w * m["tco2e_scaled"] / biggest), 11, 2, stroke=0, fill=1)
            c.setFillColor(MUTED)
            share = 100 * m["tco2e_scaled"] / scope3["tco2e"] if scope3["tco2e"] else 0
            c.drawString(LEFT + label_w + bar_w + 10, y, f"{_fmt(m['tco2e_scaled'])} tCO₂e ({share:.0f}%)")
            y -= 17
        y = _howto(c, "a longer bar means that way of travelling adds more emissions. Walking and cycling add none.", y - 2)
        sens = scope3.get("sensitivity", {})
        if sens:
            txt = ("This depends on how many students are assumed. With the same survey, "
                   + " and ".join(f"{k} ({_fmt(v, 0)} tCO₂e)" for k, v in sens.items()) + " would give those totals instead.")
            _text_block(c, _wrap(c, txt, "Body", 9.5, RIGHT - LEFT), LEFT, y, "Body", 9.5, MUTED, 13)


def build_sections(path: str, analysis: dict, scope3: Optional[dict] = None, first_page: int = 3) -> str:
    """Write pages 3 to 5 as a stand-alone PDF (the full report joins them after the cover and page 2)."""
    c = canvas.Canvas(path, pagesize=(W, H))
    for i, draw in enumerate((draw_glance_page, draw_method_page, draw_results_page)):
        draw(c, analysis, scope3, first_page + i)
        c.showPage()
    c.save()
    return path


def _money(v) -> str:
    """Rupees in the Indian way (lakh, crore) so a non-technical reader recognises the size."""
    if v is None:
        return "-"
    v = float(v)
    if v >= 1e7:
        return f"Rs {v / 1e7:,.2f} crore"
    if v >= 1e5:
        return f"Rs {v / 1e5:,.2f} lakh"
    return f"Rs {v:,.0f}"


def draw_optimization_page(c: canvas.Canvas, opt: dict, page_no: int = 6) -> None:
    """Page 6: the plan the optimiser picked from the measures the user entered."""
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "Optimization",
               "Which of the measures you entered gives the biggest cut in emissions for your budget. "
               "All measure figures (cost, saving) are the ones you typed in.")
    o, base = opt["optimal"], opt["baseline"]
    box = (("Budget", _money(opt["budget_inr"])), ("Planned spend", _money(o["total_capex_inr"])),
           ("Cut per year", f"{_fmt(o['tco2e_saved'], 1)} tCO₂e"), ("Share of your total", f"{_fmt(o['pct_of_baseline'], 1)} %"))
    gap = 10
    cw = (RIGHT - LEFT - 3 * gap) / 4
    for i, (k, v) in enumerate(box):
        x = LEFT + i * (cw + gap)
        c.setFillColor(GREY)
        c.roundRect(x, y - 58, cw, 58, 8, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.setFont("Body", 9.5)
        c.drawString(x + 10, y - 18, k)
        c.setFillColor(TEAL_DARK)
        big, _, unit = v.partition("|")
        c.setFont("Title", 15)
        c.drawString(x + 10, y - 40, big)
        if unit:
            c.setFont("Body", 10)
            c.drawString(x + 14 + c.stringWidth(big, "Title", 15), y - 40, unit)
    y -= 58 + 22
    y = _h2(c, "Recommended plan", y)
    if not o["selected"]:
        _text_block(c, _wrap(c, "With this budget none of the measures could be chosen. Increase the budget or check the costs entered.",
                             "Body", 10.5, RIGHT - LEFT), LEFT, y, "Body", 10.5, INK, 14)
        y -= 34
    else:
        rows = [(s["label"], f"{s['units']}", _money(s["capex_inr"]), _fmt(s["tco2e_saved"], 2), f"{_fmt(s['pct_of_baseline'], 1)} %")
                for s in o["selected"]]
        rows.append(("Total", "", _money(o["total_capex_inr"]), _fmt(o["tco2e_saved"], 2), f"{_fmt(o['pct_of_baseline'], 1)} %"))
        y = _table(c, y, ("Measure", "Units", "Cost", "tCO₂e saved / yr", "Share"), rows,
                   (200, 50, 100, 90, RIGHT - LEFT - 440))
    y = _howto(c, "the plan lists what to do, how many units, what it costs and how much yearly emission it removes. "
                  f"Your yearly total before any measure is {_fmt(base['tco2e_per_year'], 1)} tCO₂e.", y)

    y = _h2(c, "Each measure on its own (per unit)", y - 4)
    biggest = max((r["pct_of_baseline_per_unit"] for r in opt["ranking"]), default=0) or 1.0
    for r in opt["ranking"]:
        c.setFillColor(INK)
        c.setFont("Body", 9.5)
        c.drawString(LEFT, y, (r["label"][:34] + "...") if len(r["label"]) > 36 else r["label"])
        c.setFillColor(C_S2)
        c.roundRect(LEFT + 200, y - 3, max(1.5, 200 * r["pct_of_baseline_per_unit"] / biggest), 10, 2, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.drawString(LEFT + 410, y, f"{_fmt(r['pct_of_baseline_per_unit'], 1)} % of total per unit")
        y -= 16
    y = _howto(c, "a longer bar means one unit of that measure removes a bigger share of your emissions.", y - 2)
    notes = list(opt.get("notes", [])) + [opt["disclaimer"]]
    c.setFillColor(MUTED)
    _text_block(c, [ln for n in notes for ln in _wrap(c, n, "Body", 9, RIGHT - LEFT)], LEFT, max(y - 4, 150), "Body", 9, MUTED, 12)


def draw_steps_page(c: canvas.Canvas, opt: dict, page_no: int = 7) -> None:
    """Page 7: recommended steps over 5 and 10 years, built only from the user's plan."""
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "Recommended steps",
               "What to do, in order, based on the measures and costs you entered. "
               "These are suggestions from your own inputs, not a guarantee.")
    o, base = opt["optimal"], opt["baseline"]
    if not o["selected"]:
        _text_block(c, _wrap(c, "No measure fits the budget entered, so no steps are suggested. Enter a larger budget or lower costs and run the optimization again.",
                             "Body", 10.5, RIGHT - LEFT), LEFT, y, "Body", 10.5, INK, 14)
        return
    rank = {r["id"]: r for r in opt["ranking"]}
    steps = sorted(o["selected"], key=lambda s: (rank.get(s["id"], {}).get("inr_per_tco2e") is None, rank.get(s["id"], {}).get("inr_per_tco2e") or 0))
    y = _h2(c, "Steps, cheapest cut first", y)
    for i, s in enumerate(steps, 1):
        r = rank.get(s["id"], {})
        c.setFillColor(TEAL)
        c.circle(LEFT + 10, y + 3, 9, stroke=0, fill=1)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("BodyBold", 10)
        c.drawCentredString(LEFT + 10, y, str(i))
        c.setFillColor(INK)
        c.setFont("BodyBold", 11)
        c.drawString(LEFT + 28, y + 3, f"{s['label']} ({s['units']} unit{'s' if s['units'] != 1 else ''})")
        c.setFillColor(MUTED)
        c.setFont("Body", 9.5)
        extra = f", about {_money(r['inr_per_tco2e'])} per tCO₂e saved per year" if r.get("inr_per_tco2e") else ""
        c.drawString(LEFT + 28, y - 11, f"Cost {_money(s['capex_inr'])}; removes {_fmt(s['tco2e_saved'], 2)} tCO₂e a year{extra}.")
        y -= 34
    y -= 6
    y = _h2(c, "What this means over 5 and 10 years", y)
    saved, total = o["tco2e_saved"], base["tco2e_per_year"]
    rows = [("After the plan, per year", f"{_fmt(total - saved, 1)} tCO₂e (now {_fmt(total, 1)})"),
            ("Emission avoided in 5 years", f"{_fmt(saved * 5, 1)} tCO₂e"),
            ("Emission avoided in 10 years", f"{_fmt(saved * 10, 1)} tCO₂e")]
    if o.get("annual_saving_inr") is not None:
        rows.append(("Money saved per year", _money(o["annual_saving_inr"])))
    if o.get("payback_years"):
        rows.append(("Cost paid back in", f"about {_fmt(o['payback_years'], 1)} years"))
    y = _table(c, y, ("", "Result"), rows, (230, RIGHT - LEFT - 230))
    lines = _wrap(c, "How these were worked out: yearly saving of the plan x 5 or x 10. It assumes the measures stay in use, "
                     "your usage and the electricity emission factor stay as they are today, and the plan is carried out in full. "
                     "Usage growth, a cleaner grid and Scope 3 are not included.", "Body", 9.5, RIGHT - LEFT)
    _text_block(c, lines, LEFT, y - 2, "Body", 9.5, MUTED, 13)


def _factor_text(analysis: dict) -> str:
    return "; ".join(f"{f['activity'].replace('_', ' ')} {f['factor']} {f['output']} ({f['version']})" for f in analysis["factors_used"])


def build_full_report(path: str, analysis: dict, optimization: Optional[dict] = None, scope3: Optional[dict] = None,
                      prepared_for: str = "", data_source: str = "", generated_on: str = "",
                      inventory: Optional[dict] = None, energy_audit: Optional[dict] = None) -> str:
    """Cover, About, At a glance, Method, Results, the yearly campus footprint (when `inventory` is given), Trend, Sources, Forecast and Training (when forecast ran), What-if,
    Grid factor, plus Optimization and Recommended steps when a plan is given, then Data and limits.
    With `energy_audit` (energy_audit.build_audit) the campus Energy Audit pages follow the yearly campus pages: result, AC check, suggestions.
    Every page after the cover has a border."""
    from report_cover import CoverInfo, ReportDetails, draw_cover, draw_details_page
    inp = analysis["input"]
    sources = [k for k in ("electricity_kwh", "diesel_litres") if k in inp["columns_used"]]
    boundary = " and ".join({"electricity_kwh": "Scope 2 (purchased electricity)", "diesel_litres": "Scope 1 (generator diesel)"}[k] for k in sources[::-1])
    if inventory:
        boundary += "; yearly Scope 1, 2 and 3 totals on one page"
    info = CoverInfo(period=f"{inp['period_start']} to {inp['period_end']}", boundary=boundary)
    details = ReportDetails(generated_on=generated_on, prepared_for=prepared_for,
                            data_period=f"{inp['period_start']} to {inp['period_end']} ({inp['rows']} {inp['granularity_analysed']} rows)",
                            data_source=data_source, boundary=boundary, factors=_factor_text(analysis), version="1.0")
    c = canvas.Canvas(path, pagesize=(W, H))
    c.setTitle("Carbon Footprint Report")
    c.setAuthor("Carbonomics-AI")
    draw_cover(c, info, "classic")
    c.showPage()
    draw_details_page(c, info, details)
    c.showPage()
    import report_extra as rx
    n = 3
    for draw in (draw_glance_page, draw_method_page, draw_results_page):
        if draw is draw_glance_page:
            draw(c, analysis, scope3, n, inventory)
        else:
            draw(c, analysis, scope3, n)
        c.showPage()
        n += 1
    if inventory:
        import report_annual as ra
        ra.draw_campus_page(c, inventory, n)
        c.showPage()
        ra.draw_campus_notes_page(c, inventory, n + 1)
        c.showPage()
        n += 2
    if energy_audit:
        import report_audit as rau
        rau.draw_audit_page(c, energy_audit, n)
        c.showPage()
        rau.draw_ac_page(c, energy_audit, n + 1)
        c.showPage()
        n += 2 + rau.draw_suggestion_pages(c, energy_audit, n + 2)
        c.showPage()
    rx.draw_trend_page(c, analysis, n)
    c.showPage()
    rx.draw_sources_page(c, analysis, n + 1)
    c.showPage()
    n += 2
    fc = analysis.get("forecast")
    if fc and fc.get("status") == "ok":
        for target in fc["targets"]:
            rx.draw_forecast_page(c, analysis, target, n)
            c.showPage()
            n += 1
        rx.draw_training_page(c, analysis, n)
        c.showPage()
        n += 1
    else:
        rx._skipped_page(c, n, (fc or {}).get("reason", "The data was too short for a forecast."))
        c.showPage()
        n += 1
    rx.draw_sensitivity_page(c, analysis, n)
    c.showPage()
    rx.draw_factor_page(c, analysis, n + 1, analysis.get("factor_change"))
    c.showPage()
    n += 2
    if optimization:
        draw_optimization_page(c, optimization, n)
        c.showPage()
        draw_steps_page(c, optimization, n + 1)
        c.showPage()
        n += 2
    rx.draw_notes_page(c, analysis, n, scope3, inventory)
    c.showPage()
    c.save()
    return path
