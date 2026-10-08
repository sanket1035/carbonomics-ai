"""
report_audit.py

Report pages for the Energy Audit (campus electricity against a documented benchmark, then data-based suggestions).

All content comes from energy_audit.build_audit(): nothing is computed or invented here except layout. Pages:
    "Energy Audit"        : yearly electricity, EPI (kWh/m2/year) against the reference points, limits of the comparison.
    "Air-conditioning check": why the listed AC load looks too high and the corrected estimate (COP is ASSUMED and labelled so).
    "Energy Audit: suggestions" (1 to 3 pages): the ordered list with source, published saving, campus number where one exists.

Like the yearly Scope 1, 2 and 3 pages these describe the campus as a whole, so they are fixed pages, not tied to an uploaded file.
"""

from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from report_cover import INK, MUTED, TEAL, TEAL_DARK, _fonts, _page_header, _text_block, _wrap
from report_pages import GREY, LEFT, RIGHT, _fmt, _h2, _howto, _table, _title

BOTTOM = 62                                   # content must stay above the footer
C_REF = HexColor("#94a3b8")
C_CAMPUS = HexColor("#0f766e")
C_ASP = HexColor("#6366f1")
STATUS = {                                    # label, text colour, chip background
    "scenario": ("Campus number", "#0b4a46", "#ccfbf1"),
    "what_if": ("Try in What-if", "#3730a3", "#e0e7ff"),
    "typical": ("Published saving", "#92400e", "#fef3c7"),
    "practice": ("Practice", "#334155", "#e2e8f0"),
    "enabler": ("Enabler", "#334155", "#e2e8f0"),
}


def _kpis(c, y, boxes) -> float:
    gap = 10
    cw = (RIGHT - LEFT - (len(boxes) - 1) * gap) / len(boxes)
    for i, (k, v, u) in enumerate(boxes):
        x = LEFT + i * (cw + gap)
        c.setFillColor(GREY)
        c.roundRect(x, y - 58, cw, 58, 8, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.setFont("Body", 9.5)
        c.drawString(x + 10, y - 17, k)
        c.setFillColor(TEAL_DARK)
        c.setFont("Title", 17)
        c.drawString(x + 10, y - 40, v)
        if u:
            c.setFont("Body", 9)
            c.setFillColor(MUTED)
            c.drawString(x + 14 + c.stringWidth(v, "Title", 17), y - 40, u)
    return y - 58 - 18


def _epi_bars(c, y, actual: dict, refs: list) -> float:
    """Three horizontal bars on one scale: this campus, the 5-star cut-off, the net-zero upper bound."""
    bars = [("This campus", actual["epi"], C_CAMPUS)]
    for r in refs:
        bars.append((("5-star cut-off (proxy)" if r["role"] == "reference" else "Net-zero label (aspirational)"),
                     r["benchmark_epi"], C_REF if r["role"] == "reference" else C_ASP))
    top = max(v for _, v, _ in bars) or 1.0
    x0, wmax = LEFT + 150, RIGHT - LEFT - 150 - 70
    for label, v, col in bars:
        c.setFillColor(INK)
        c.setFont("Body", 9.5)
        c.drawString(LEFT, y, label)
        c.setFillColor(col)
        c.roundRect(x0, y - 3, max(2.0, wmax * v / top), 12, 3, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.drawString(x0 + max(2.0, wmax * v / top) + 6, y, f"{_fmt(v, 1)}")
        y -= 20
    c.setFillColor(MUTED)
    c.setFont("Body", 8.5)
    c.drawString(x0, y + 2, "kWh per m² of built-up area per year")
    return y - 14


def draw_audit_page(c: canvas.Canvas, audit: dict, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    a, refs = audit["actual"], audit["references"]
    y = _title(c, "Energy Audit",
               f"How much electricity the campus uses for its size, and how that compares with a published reference. "
               f"{audit['period']}, purchased electricity only.")
    cut = next((r for r in refs if r["role"] == "reference"), refs[0])
    y = _kpis(c, y, (("Electricity bought", _fmt(a["electricity_kwh"] / 1000, 0), "thousand kWh"),
                     ("Built-up area", _fmt(a["built_up_area_m2"], 0), "m²"),
                     ("Energy per area (EPI)", _fmt(a["epi"], 1), "kWh/m²"),
                     ("Per person", _fmt(a["kwh_per_person"], 0), "kWh/yr")))
    y = _h2(c, "Campus against the reference points", y)
    y = _epi_bars(c, y, a, refs)
    pos = "below" if cut["position"] == "below_target" else "above"
    y = _howto(c, f"a shorter bar is better. At {_fmt(a['epi'], 1)} kWh/m² the campus is {pos} the {_fmt(cut['benchmark_epi'], 0)} kWh/m² cut-off, "
                  f"which is {_fmt(abs(cut['gap_kwh']), 0)} kWh a year ({_fmt(abs(cut['gap_tco2e']), 0)} tCO₂e) {pos} the target. "
                  "This is a position check, not a promise of savings.", y)

    y = _h2(c, "The reference points", y - 10)
    rows = [(r["label"], _fmt(r["benchmark_epi"], 0), f"{r['source']} ({r['version']})" + ("" if r["verified"] else ", not yet verified"))
            for r in refs]
    y = _table(c, y, ("Reference", "EPI", "Source and version"), rows, (190, 40, RIGHT - LEFT - 230), size=8.5)

    y = _h2(c, "What this comparison can and cannot say", y - 2)
    items = [audit["zone_note"], *audit["caveats"]]
    for it in items:
        lines = _wrap(c, "• " + it, "Body", 9, RIGHT - LEFT)
        if y - 12.5 * len(lines) < BOTTOM:
            break
        _text_block(c, lines, LEFT, y, "Body", 9, INK, 12.5)
        y -= 12.5 * len(lines) + 3


def draw_ac_page(c: canvas.Canvas, audit: dict, page_no: int) -> None:
    _fonts()
    _page_header(c, page_no)
    ac = audit["ac"]
    y = _title(c, "Air-conditioning check",
               "The campus AC list gives a very large electricity figure. This page explains why it is probably too high and what a corrected estimate looks like.")
    cen, low, high = ac["corrected_kwh"]["central"], ac["corrected_kwh"]["low"], ac["corrected_kwh"]["high"]
    y = _kpis(c, y, (("AC as listed", _fmt(ac["modelled_kwh"] / 1000, 0), "thousand kWh"),
                     ("Share of electricity", f"{100 * ac['modelled_share_of_purchased']:.0f}", "%"),
                     ("AC corrected", _fmt(cen / 1000, 0), "thousand kWh"),
                     ("Share of electricity", f"{100 * ac['corrected_share_of_purchased']['central']:.0f}", "%")))
    y = _h2(c, "What was found", y)
    paras = [f"The AC list gives a power in kW for each unit. For the listed units this equals the cooling capacity (1 ton = {ac['ton_of_refrigeration_kw_thermal']} kW of cooling), "
             "not the electricity the unit draws. An AC unit uses less electricity than the cooling it delivers.",
             f"Dividing by a coefficient of performance (COP) of {ac['assumed_cop']['low']}, {ac['assumed_cop']['central']} and {ac['assumed_cop']['high']} gives "
             f"{_fmt(high, 0)} to {_fmt(low, 0)} kWh a year, central {_fmt(cen, 0)} kWh, about {100 * ac['corrected_share_of_purchased']['central']:.0f}% of purchased electricity "
             f"({_fmt(ac['corrected_tco2e']['central'], 0)} tCO₂e). The listed figure would be {100 * ac['modelled_share_of_purchased']:.0f}%.",
             "The COP values are ASSUMED. They are not from a nameplate or a source. They should be replaced once the rated input power of the units is collected. "
             "The original sheet is left unchanged."]
    for p in paras:
        lines = _wrap(c, p, "Body", 10, RIGHT - LEFT)
        _text_block(c, lines, LEFT, y, "Body", 10, INK, 14)
        y -= 14 * len(lines) + 6
    y = _h2(c, "AC by site (yearly kWh)", y - 6)
    rows = [(s["location"], str(s["units"]), _fmt(s["modelled_kwh"], 0), _fmt(s["corrected_kwh"]["central"], 0),
             f"{_fmt(s['corrected_kwh']['high'], 0)} to {_fmt(s['corrected_kwh']['low'], 0)}") for s in ac["sites"]]
    rows.append(("All sites", str(ac["units_total"]), _fmt(ac["modelled_kwh"], 0), _fmt(cen, 0), f"{_fmt(high, 0)} to {_fmt(low, 0)}"))
    y = _table(c, y, ("Site", "Units", "As listed", "Corrected (central)", "Range (COP 4.0 to 2.5)"), rows,
               (140, 50, 100, 105, RIGHT - LEFT - 395), size=9)
    y = _howto(c, "the 'As listed' column is the sheet's own modelled figure; the corrected columns divide the listed kW by the assumed COP.", y + 2)
    g = ac.get("sanity_guest_house")
    if g:
        lines = _wrap(c, f"Cross-check: for the {g['location']} ({_fmt(g['area_m2'], 0)} m²) the listed AC alone would be {_fmt(g['modelled_ac_kwh_per_m2'], 0)} kWh/m² a year, "
                         f"against a campus total of about {_fmt(audit['actual']['epi'], 0)} kWh/m². With the correction it is {_fmt(g['corrected_ac_kwh_per_m2']['high'], 0)} to "
                         f"{_fmt(g['corrected_ac_kwh_per_m2']['low'], 0)} kWh/m². {g['note']}", "Body", 9.5, RIGHT - LEFT)
        _text_block(c, lines, LEFT, y, "Body", 9.5, MUTED, 13)
        y -= 13 * len(lines)
    note = _wrap(c, ac["note"], "Body", 9.5, RIGHT - LEFT)
    _text_block(c, note, LEFT, y - 6, "Body", 9.5, MUTED, 13)


def _suggestion_lines(c, s: dict, width: float) -> list:
    """(font, size, colour, text, leading) rows for one suggestion; the title row is drawn separately."""
    rows = []

    def add(text, font="Body", size=9, colour=INK, lead=12):
        for ln in _wrap(c, text, font, size, width):
            rows.append((font, size, colour, ln, lead))

    add(f"Where: {s['where']}.", colour=MUTED)
    add(s["why"])
    if s["status"] != "practice" or s["typical_saving"] != "No figure claimed":
        src = s["saving_source"] if s["saving_source"] and not s["saving_source"].startswith("None") else ""
        when = f", {s['source_date']}" if s["source_date"] and src else ""
        add(f"Saving: {s['typical_saving']}" + (f". Source: {src}{when}." if src else "."), "BodyBold", 9, TEAL_DARK)
    n = s["campus_number"]
    if n:
        add(f"On this campus: {n['label']} is about {_fmt(n['kwh_central'], 0)} kWh a year ({_fmt(n['kwh_low'], 0)} to {_fmt(n['kwh_high'], 0)}), "
            f"around {_fmt(n['tco2e_central'], 1)} tCO₂e. {n['note']}.", "BodyBold", 9, INK)
    for e in s["campus_evidence"]:
        add("Campus data: " + e, colour=MUTED)
    add(f"Limit: {s['evidence_scope']}.", colour=MUTED, size=8.5, lead=11.5)
    add(f"Needed to go further: {s['needs']}.", colour=MUTED, size=8.5, lead=11.5)
    return rows


def draw_suggestion_pages(c: canvas.Canvas, audit: dict, first_page: int) -> int:
    """Suggestion pages. Calls showPage between pages, not after the last; returns the number of pages."""
    _fonts()
    pages = 1
    _page_header(c, first_page)
    y = _title(c, "Energy Audit: suggestions",
               "Ordered by priority. A campus number appears only where campus data exists (air-conditioning). For the rest the published saving "
               "and its source are shown, because the campus has no meters for lights, fans or pumps. These are things to check, not guaranteed savings, and no costs are included.")
    width = RIGHT - LEFT - 30
    group = None
    for s in audit["suggestions"]:
        body = _suggestion_lines(c, s, width)
        need = 22 + sum(r[4] for r in body) + 12 + (22 if s["group"] != group else 0)
        if y - need < BOTTOM:
            c.showPage()
            pages += 1
            _page_header(c, first_page + pages - 1)
            from report_cover import H
            y = H - 104
        if s["group"] != group:
            group = s["group"]
            c.setFillColor(MUTED)
            c.setFont("BodyBold", 9.5)
            c.drawString(LEFT, y, group.upper())
            c.setStrokeColor(HexColor("#cbd5e1"))
            c.setLineWidth(0.5)
            c.line(LEFT + c.stringWidth(group.upper(), "BodyBold", 9.5) + 8, y + 3, RIGHT, y + 3)
            y -= 20
        c.setFillColor(TEAL)
        c.circle(LEFT + 9, y + 3, 9, stroke=0, fill=1)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("BodyBold", 9.5)
        c.drawCentredString(LEFT + 9, y, str(s["priority"]))
        label, fg, bg = STATUS.get(s["status"], ("", "#334155", "#e2e8f0"))
        c.setFont("BodyBold", 8)
        chip_w = c.stringWidth(label, "BodyBold", 8) + 12
        c.setFillColor(HexColor(bg))
        c.roundRect(RIGHT - chip_w, y - 2, chip_w, 14, 6, stroke=0, fill=1)
        c.setFillColor(HexColor(fg))
        c.drawString(RIGHT - chip_w + 6, y + 2, label)
        c.setFillColor(INK)
        c.setFont("BodyBold", 10.5)
        title_lines = _wrap(c, s["title"], "BodyBold", 10.5, width - chip_w - 8)
        for i, ln in enumerate(title_lines):
            c.drawString(LEFT + 28, y - 12 * i, ln)
        y -= 12 * len(title_lines) + 6
        for font, size, colour, text, lead in body:
            c.setFillColor(colour)
            c.setFont(font, size)
            c.drawString(LEFT + 28, y, text)
            y -= lead
        y -= 10
    return pages
