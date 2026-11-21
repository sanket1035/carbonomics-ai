"""
report_annual.py

Two report pages with the yearly campus footprint (Scope 1, 2 and 3), drawn from annual_inventory.load_inventory() or campus_footprint_report.load_report() (same keys).

Nothing is computed here except what the inventory already holds: the figures are fixed yearly totals, so there is
no chart over time and no forecast. Pages: "Full campus footprint" (totals and every source) and
"Where the yearly figures come from" (basis of each figure, factors with source and version).
"""

from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from report_cover import INK, MUTED, TEAL_DARK, _fonts, _page_header, _text_block, _wrap
from report_pages import (GREY, LEFT, RIGHT, SCOPE_COLORS, _fmt, _h2, _howto, _table, _title)


def _activity(r: dict) -> str:
    return f"{_fmt(r['activity'], 0)} {r['activity_unit']}" if r["activity"] is not None else "-"


def _factor(r: dict) -> str:
    return f"{r['factor']['value']} {r['factor']['unit']}" if r["factor"] else "-"


def _bullet_block(c, items, y, size=9.5, gap=3):
    for it in items:
        lines = _wrap(c, "• " + it, "Body", size, RIGHT - LEFT)
        _text_block(c, lines, LEFT, y, "Body", size, INK, size + 3.5)
        y -= (size + 3.5) * len(lines) + gap
    return y


def draw_campus_page(c: canvas.Canvas, inv: dict, page_no: int) -> float:
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "Full campus footprint",
               f"Yearly totals for {inv['period']} from the published campus report. Fixed yearly figures, not forecasts.")
    total = inv["total"]
    c.setFillColor(HexColor("#ecfdf5"))
    c.setStrokeColor(HexColor("#99f6e4"))
    c.setLineWidth(0.8)
    c.roundRect(LEFT, y - 62, RIGHT - LEFT, 62, 10, stroke=1, fill=1)
    c.setFillColor(TEAL_DARK)
    c.setFont("Title", 36)
    c.drawString(LEFT + 20, y - 40, _fmt(total, 2))
    c.setFont("BodyBold", 13)
    c.drawString(LEFT + 20 + c.stringWidth(_fmt(total, 2), "Title", 36) + 10, y - 40, "tCO₂e in a year")
    c.setFillColor(MUTED)
    c.setFont("Body", 9.5)
    c.drawString(LEFT + 20, y - 55, "Scope 1 + Scope 2 + Scope 3. Same total as the published campus report.")
    y -= 62 + 12

    gap = 10
    cw = (RIGHT - LEFT - 2 * gap) / 3
    names = {"Scope 1": "Fuel burned on campus", "Scope 2": "Purchased electricity", "Scope 3": "Indirect, from the survey"}
    for i, s in enumerate(("Scope 1", "Scope 2", "Scope 3")):
        x = LEFT + i * (cw + gap)
        v = inv["by_scope"][s]
        c.setFillColor(GREY)
        c.roundRect(x, y - 56, cw, 56, 8, stroke=0, fill=1)
        c.setFillColor(SCOPE_COLORS[s])
        c.roundRect(x, y - 56, 5, 56, 2, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.setFont("BodyBold", 10.5)
        c.drawString(x + 16, y - 16, s)
        c.setFont("Body", 9)
        c.drawString(x + 16, y - 28, names[s])
        c.setFillColor(INK)
        c.setFont("Title", 20)
        c.drawString(x + 16, y - 48, _fmt(v, 2))
        c.setFont("Body", 9)
        c.setFillColor(MUTED)
        c.drawString(x + 16 + c.stringWidth(_fmt(v, 2), "Title", 20) + 5, y - 48, f"tCO₂e ({100 * v / total:.0f}%)")
    y -= 56 + 14

    y = _h2(c, "Every source", y)
    rows = []
    for r in inv["rows"]:
        if r["in_total"] not in ("yes", "no"):
            continue
        rows.append((r["scope"], r["source"], _activity(r), _factor(r),
                     _fmt(r["tco2e"], 2) if r["tco2e"] is not None else "not measured"))
    rows.append(("Total", "", "", "", _fmt(total, 2)))
    y = _table(c, y, ("Scope", "Source", "Activity", "Factor", "tCO₂e"), rows, (44, 136, 108, 140, RIGHT - LEFT - 428), size=8.5)
    y = _howto(c, "emission = activity × factor. Rows with '-' are yearly figures carried over from the campus report (next page).", y + 4)

    y = _h2(c, "Emission factors used", y - 4)
    seen, frows = set(), []
    for r in inv["rows"]:
        f = r["factor"]
        if f and f["key"] not in seen:
            seen.add(f["key"])
            frows.append((r["source"], f"{f['value']} {f['unit']}", f["source"],
                          f["version"] + ("" if f["verified"] else " (not yet verified)")))
    return _table(c, y, ("Used for", "Factor", "Source", "Version"), frows, (92, 128, RIGHT - LEFT - 304, 84), size=8)


def draw_campus_notes_page(c: canvas.Canvas, inv: dict, page_no: int) -> float:
    _fonts()
    _page_header(c, page_no)
    y = _title(c, "Where the yearly figures come from", "How each number was made and how far to trust it.")
    alt = inv["alternatives"][0] if inv["alternatives"] else None
    main = next((r for r in inv["counted"] if r["source"].startswith("Student commuting")), None)
    items = [f"Scope 3 data was taken from {inv['scope3_source']}. Scope 1 and 2 come from the energy and transport records.",
             "These are yearly totals with no weekly data behind them, so they are not forecast. The weekly pages use the "
             "uploaded file, so their totals can differ slightly."]
    if alt and main:
        items.append(f"Student commuting has two versions in the master data. The first ({_fmt(main['tco2e'], 2)} tCO₂e) is in the total, which "
                     f"matches the published {inv['published_total']:,.2f}. The revised one ({_fmt(alt['tco2e'], 2)} tCO₂e) would "
                     f"give {_fmt(inv['total'] - main['tco2e'] + alt['tco2e'], 2)}. They are never added together.")
    for r in inv["excluded"]:
        items.append(f"{r['source']} is left out of the total. {r['note']}.")
    if inv["memo"]:
        items.append("Not subtracted from the total: " + "; ".join(
            f"{r['source'].lower()} {_fmt(r['tco2e'], 2)} tCO₂e" for r in inv["memo"]) + ".")
    y = _bullet_block(c, items, y)

    y = _h2(c, "How each figure was made", y - 4)
    rows = [(r["source"], r["basis"], "Rechecked" if r["check"] == "recomputed" else "As stated",
             r["note"]) for r in inv["rows"] if r["in_total"] in ("yes", "alt")]
    return _table(c, y, ("Source", "Basis", "Check", "Note"), rows, (132, 95, 62, RIGHT - LEFT - 289), size=8)
