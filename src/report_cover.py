"""
report_cover.py

First page (cover) of the PDF report, drawn with ReportLab on A4.

Two designs are available so the team can pick one:
    "classic" : photo across the top, white panel with the title below.
    "full"    : full-page photo with a dark teal gradient and white title.

The cover shows only labels the caller passes in (organisation, period, boundary text, date). It contains
no emission figures. Photos and fonts live in assets/ and are bundled with the repository.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Optional

from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
PHOTOS = os.path.join(ROOT, "assets", "report")

W, H = A4
TEAL = HexColor("#0f766e")
TEAL_DARK = HexColor("#0b4a46")
INK = HexColor("#0f172a")
MUTED = HexColor("#475569")
LEAF = HexColor("#ecfdf5")

_FONTS_DONE = False


def _fonts() -> None:
    global _FONTS_DONE
    if _FONTS_DONE:
        return
    for name, file in (("Title", "Caladea-Bold.ttf"), ("TitleRegular", "Caladea-Regular.ttf"),
                       ("Body", "Carlito-Regular.ttf"), ("BodyBold", "Carlito-Bold.ttf")):
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, file)))
    _FONTS_DONE = True


@dataclass
class CoverInfo:
    organisation: str = "K. K. Wagh Institute of Engineering Education and Research"
    place: str = "Panchvati Campus, Nashik, Maharashtra"
    title: str = "Carbon Footprint Report"
    period: str = "Calendar Year 2025"
    boundary: str = "Scope 1 (generator diesel) and Scope 2 (purchased electricity)"
    prepared_by: str = "Team Carbonomics, Department of AI & DS, KKWIEER, Nashik"
    date: str = ""                      # the cover is static: the date and version go on the second page
    version: str = ""
    status: str = ""                    # optional small tag under the title; "" hides it
    logo_path: Optional[str] = None     # institute logo, only if the college allows its use


def _photo(name: str) -> Image.Image:
    return Image.open(os.path.join(PHOTOS, name)).convert("RGB")


def _crop_to(im: Image.Image, ratio: float, cx: float = 0.5, cy: float = 0.5) -> Image.Image:
    """Crop to width/height = ratio, centred at (cx, cy) as fractions of the image, staying inside it."""
    w, h = im.size
    if w / h > ratio:
        nw, nh = int(h * ratio), h
    else:
        nw, nh = w, int(w / ratio)
    x = min(max(int(cx * w - nw / 2), 0), w - nw)
    y = min(max(int(cy * h - nh / 2), 0), h - nh)
    return im.crop((x, y, x + nw, y + nh))


def _draw_image(c: canvas.Canvas, im: Image.Image, x: float, y: float, w: float, h: float) -> None:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    buf.seek(0)
    c.drawImage(ImageReader(buf), x, y, w, h)


def _gradient(size, top_rgba, bottom_rgba, y0: float, y1: float) -> Image.Image:
    """Vertical alpha gradient layer: transparent above y0, blending from top_rgba at y0 to bottom_rgba at y1."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    px = layer.load()
    for y in range(h):
        t = min(max((y / h - y0) / (y1 - y0), 0.0), 1.0)
        col = tuple(int(top_rgba[i] + (bottom_rgba[i] - top_rgba[i]) * t) for i in range(4))
        for x in range(w):
            px[x, y] = col
    return layer


def _mark(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    """The Carbonomics logo symbol (G with a leaf) on a rounded cream tile, so it reads on any background."""
    r = s * 0.2
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, s, s, r)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(os.path.join(PHOTOS, "logo_mark.png"), x, y, s, s)
    c.restoreState()


def _old_mark(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    """The earlier plain leaf icon (kept for reference, not used): teal rounded square with a leaf (same shapes as dashboard/public/favicon.svg)."""
    k = s / 32.0
    c.setFillColor(TEAL)
    c.roundRect(x, y, s, s, 8 * k, stroke=0, fill=1)
    c.setFillColor(LEAF)
    p = c.beginPath()
    X = lambda v: x + v * k
    Y = lambda v: y + s - v * k
    p.moveTo(X(9), Y(20))
    p.curveTo(X(9), Y(14), X(13), Y(10), X(23), Y(9))
    p.curveTo(X(22), Y(19), X(18), Y(23), X(12), Y(23))
    p.lineTo(X(11), Y(20))
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _wrap(c: canvas.Canvas, text: str, font: str, size: float, width: float) -> list:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if c.stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _text_block(c, lines, x, y, font, size, color, leading):
    c.setFillColor(color)
    c.setFont(font, size)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading
    return y


def _classic(c: canvas.Canvas, info: CoverInfo) -> None:
    hero_h = 470
    hero = _crop_to(_photo("campus_front.jpg").crop((0, 0, 2020, 1500)), W / hero_h, cx=0.5, cy=0.45)
    # darken the top edge a little so the white header stays readable on the bright sky
    hero = hero.resize((1400, int(1400 * hero_h / W)))
    hero = Image.alpha_composite(hero.convert("RGBA"), _gradient(hero.size, (8, 40, 38, 150), (8, 40, 38, 0), 0.0, 0.32))
    # the bottom of the photo fades into the white page, so there is no hard dark-to-light edge
    hero = Image.alpha_composite(hero, _gradient(hero.size, (255, 255, 255, 0), (255, 255, 255, 255), 0.64, 0.99)).convert("RGB")
    _draw_image(c, hero, 0, H - hero_h, W, hero_h)

    _mark(c, 48, H - 90, 42)
    c.setFillColor(white)
    c.setFont("BodyBold", 16)
    c.drawString(100, H - 74, "Carbonomics-AI")
    c.setFont("Body", 10)
    c.drawRightString(W - 48, H - 70, "CARBON ACCOUNTING REPORT")

    # title block
    left, right = 48, W - 48
    y = H - hero_h - 38
    c.setFillColor(TEAL)
    c.setFont("BodyBold", 11)
    c.drawString(left, y + 24, info.period.upper())
    c.setFillColor(INK)
    c.setFont("Title", 38)
    c.drawString(left, y - 14, info.title)
    c.setStrokeColor(TEAL)
    c.setLineWidth(2.5)
    c.line(left, y - 32, left + 64, y - 32)

    y -= 66
    y = _text_block(c, _wrap(c, info.organisation, "BodyBold", 17, right - left), left, y, "BodyBold", 17, INK, 22)
    y = _text_block(c, [info.place], left, y - 1, "Body", 12.5, MUTED, 17)
    y -= 12
    c.setFillColor(MUTED)
    c.setFont("Body", 11)
    for ln in _wrap(c, "Reporting boundary: " + info.boundary, "Body", 11, right - left):
        c.drawString(left, y, ln)
        y -= 15
    if info.status:
        c.setFillColor(TEAL)
        c.roundRect(left, y - 24, c.stringWidth(info.status.upper(), "BodyBold", 9) + 20, 18, 9, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("BodyBold", 9)
        c.drawString(left + 10, y - 18.5, info.status.upper())

    # two small campus photos
    th_w, th_h, gap = 124, 78, 10
    ty = 88
    for i, (name, cy) in enumerate((("campus_aerial_field.jpg", 0.5), ("campus_aerial_trees.jpg", 0.45))):
        x = right - (2 - i) * th_w - (1 - i) * gap
        _draw_image(c, _crop_to(_photo(name), th_w / th_h, cy=cy), x, ty, th_w, th_h)

    # footer
    c.setStrokeColor(HexColor("#cbd5e1"))
    c.setLineWidth(0.6)
    c.line(left, 66, right, 66)
    c.setFillColor(MUTED)
    c.setFont("Body", 9.5)
    c.drawString(left, 49, "Prepared with Carbonomics-AI by " + info.prepared_by)
    c.drawRightString(right, 33, "  ·  ".join(x for x in (info.date, info.version) if x))
    c.setFont("Body", 8)
    c.drawString(left, 33, "Estimates are activity x emission factor. Every factor is listed with its source, version and unit.")


def _full(c: canvas.Canvas, info: CoverInfo) -> None:
    im = _crop_to(_photo("campus_front.jpg").crop((0, 0, 2020, 1500)), W / H, cx=0.46, cy=0.5)
    im = im.resize((1240, int(1240 * H / W)))
    top = _gradient(im.size, (8, 50, 46, 175), (8, 50, 46, 0), 0.0, 0.30)
    bottom = _gradient(im.size, (7, 56, 52, 0), (6, 44, 41, 245), 0.40, 0.78)
    im = Image.alpha_composite(Image.alpha_composite(im.convert("RGBA"), top), bottom).convert("RGB")
    _draw_image(c, im, 0, 0, W, H)

    _mark(c, 48, H - 94, 44)
    c.setFillColor(white)
    c.setFont("BodyBold", 17)
    c.drawString(102, H - 77, "Carbonomics-AI")
    c.setFont("Body", 10)
    c.drawRightString(W - 48, H - 73, "CARBON ACCOUNTING REPORT")

    left, right = 52, W - 52
    c.setFillColor(HexColor("#5eead4"))
    c.setFont("BodyBold", 12)
    c.drawString(left, 292, info.period.upper())
    c.setFillColor(white)
    c.setFont("Title", 44)
    c.drawString(left, 246, info.title)
    c.setStrokeColor(HexColor("#5eead4"))
    c.setLineWidth(3)
    c.line(left, 228, left + 70, 228)
    y = _text_block(c, _wrap(c, info.organisation, "BodyBold", 18, right - left), left, 198, "BodyBold", 18, white, 23)
    y = _text_block(c, [info.place], left, y - 1, "Body", 13, HexColor("#cbd5e1"), 18)
    y -= 8
    c.setFillColor(HexColor("#cbd5e1"))
    c.setFont("Body", 11)
    for ln in _wrap(c, "Reporting boundary: " + info.boundary, "Body", 11, right - left):
        c.drawString(left, y, ln)
        y -= 15

    c.setStrokeColor(HexColor("#2dd4bf"))
    c.setLineWidth(0.6)
    c.line(left, 72, right, 72)
    c.setFillColor(HexColor("#e2e8f0"))
    c.setFont("Body", 9.5)
    c.drawString(left, 54, "Prepared with Carbonomics-AI by " + info.prepared_by)
    c.setFillColor(HexColor("#94a3b8"))
    c.setFont("Body", 9)
    c.drawString(left, 39, "  ·  ".join(x for x in (info.date, info.version, info.status) if x))


@dataclass
class ReportDetails:
    """What the second page says about this particular report. Empty values show as '-'."""
    generated_on: str = ""          # date the report was generated, e.g. "6 October 2026"
    prepared_for: str = ""          # the person who generated it, e.g. "Dr. A. B. Name, Principal"
    data_period: str = ""           # e.g. "1 Jan 2025 to 31 Dec 2025 (12 months)"
    data_source: str = ""           # e.g. the uploaded file name
    boundary: str = "Scope 1 (generator diesel) and Scope 2 (purchased electricity)"
    factors: str = ""               # e.g. "Electricity 0.71 kg CO2e/kWh (CEA v21.0); diesel 2.89 kg CO2e/L (CEA v20.0)"
    version: str = ""               # e.g. "1.0"


GLOSSARY = (
    ("tCO\u2082e", "Tonnes of carbon dioxide equivalent. One number that adds up different greenhouse gases so they can be compared."),
    ("Scope 1", "Emissions from fuel the campus burns itself. In this report: diesel used in generators."),
    ("Scope 2", "Emissions from the electricity the campus buys from the grid. The power plant emits, the campus pays for it."),
)


def _page_frame(c: canvas.Canvas) -> None:
    """Border drawn on every page after the cover: a teal rule with a thin inner line and a short teal corner accent."""
    m = 20
    c.saveState()
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.2)
    c.rect(m, m, W - 2 * m, H - 2 * m, stroke=1, fill=0)
    c.setStrokeColor(HexColor("#99f6e4"))
    c.setLineWidth(0.4)
    c.rect(m + 4, m + 4, W - 2 * m - 8, H - 2 * m - 8, stroke=1, fill=0)
    c.setStrokeColor(TEAL_DARK)
    c.setLineWidth(3)
    for x, y, dx, dy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        c.line(x, y, x + dx * 26, y)
        c.line(x, y, x, y + dy * 26)
    c.restoreState()


def _page_header(c: canvas.Canvas, page_no: int) -> None:
    _page_frame(c)
    left, right = 48, W - 48
    _mark(c, left, H - 62, 26)
    c.setFillColor(TEAL_DARK)
    c.setFont("BodyBold", 12)
    c.drawString(left + 34, H - 54, "Carbonomics-AI")
    c.setFillColor(MUTED)
    c.setFont("Body", 9.5)
    c.drawRightString(right, H - 54, "Carbon Footprint Report")
    c.setStrokeColor(HexColor("#cbd5e1"))
    c.setLineWidth(0.6)
    c.line(left, H - 72, right, H - 72)
    c.setFillColor(MUTED)
    c.setFont("Body", 9)
    c.drawString(left, 34, "Carbonomics-AI · KKWIEER, Nashik")
    c.drawRightString(right, 34, f"Page {page_no}")


def draw_details_page(c: canvas.Canvas, info: CoverInfo, d: ReportDetails) -> None:
    """Page 2: the facts of this report, plain-language terms, and where the campus is."""
    _fonts()
    _page_header(c, 2)
    left, right = 48, W - 48
    c.setFillColor(INK)
    c.setFont("Title", 27)
    c.drawString(left, H - 118, "About this report")
    c.setStrokeColor(TEAL)
    c.setLineWidth(2.5)
    c.line(left, H - 130, left + 56, H - 130)

    rows = (("Prepared for", info.organisation), ("Report generated on", d.generated_on), ("Generated by", d.prepared_for),
            ("Data period", d.data_period), ("Data source", d.data_source), ("What is counted", d.boundary),
            ("Emission factors", d.factors), ("Report version", d.version))
    y = H - 160
    lab_w = 118
    for i, (label, value) in enumerate(rows):
        lines = _wrap(c, value or "-", "Body", 10.5, right - left - lab_w - 16)
        h = 10 + 14 * len(lines)
        if i % 2 == 0:
            c.setFillColor(HexColor("#f1f5f9"))
            c.rect(left, y - h + 6, right - left, h, stroke=0, fill=1)
        c.setFillColor(MUTED)
        c.setFont("BodyBold", 10)
        c.drawString(left + 8, y - 8, label)
        _text_block(c, lines, left + lab_w + 8, y - 8, "Body", 10.5, INK, 14)
        y -= h
    y -= 22

    # plain-language terms
    c.setFillColor(INK)
    c.setFont("Title", 15)
    c.drawString(left, y, "Three terms used in this report")
    y -= 14
    gap = 10
    cw = (right - left - 2 * gap) / 3
    top = y
    heights = []
    for term, text in GLOSSARY:
        heights.append(34 + 13 * len(_wrap(c, text, "Body", 9.5, cw - 20)))
    ch = max(heights)
    for i, (term, text) in enumerate(GLOSSARY):
        x = left + i * (cw + gap)
        c.setFillColor(HexColor("#ecfdf5"))
        c.setStrokeColor(HexColor("#99f6e4"))
        c.setLineWidth(0.8)
        c.roundRect(x, top - ch, cw, ch, 8, stroke=1, fill=1)
        c.setFillColor(TEAL_DARK)
        c.setFont("BodyBold", 12)
        c.drawString(x + 10, top - 20, term)
        _text_block(c, _wrap(c, text, "Body", 9.5, cw - 20), x + 10, top - 35, "Body", 9.5, INK, 13)
    y = top - ch - 26

    # where the campus is
    c.setFillColor(INK)
    c.setFont("Title", 15)
    c.drawString(left, y, "Where the campus is")
    y -= 10
    mw = right - left
    mh = mw * 619 / 1600
    p = c.beginPath()
    p.roundRect(left, y - mh, mw, mh, 8)
    c.saveState()
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(os.path.join(PHOTOS, "campus_map.jpg"), left, y - mh, mw, mh)
    c.restoreState()
    c.setStrokeColor(HexColor("#bae6fd"))
    c.setLineWidth(0.8)
    c.roundRect(left, y - mh, mw, mh, 8, stroke=1, fill=0)


def draw_cover(c: canvas.Canvas, info: CoverInfo, design: str = "classic") -> None:
    """Draw the cover on the current page of canvas `c` (call c.showPage() afterwards)."""
    _fonts()
    if design == "classic":
        _classic(c, info)
    elif design == "full":
        _full(c, info)
    else:
        raise ValueError("design must be 'classic' or 'full'")


def build_cover(path: str, info: Optional[CoverInfo] = None, design: str = "classic",
                details: Optional[ReportDetails] = None) -> str:
    """Write the cover (page 1) and, if `details` is given, the 'About this report' page (page 2)."""
    info = info or CoverInfo()
    c = canvas.Canvas(path, pagesize=A4)
    c.setTitle(info.title)
    c.setAuthor("Team Carbonomics")
    draw_cover(c, info, design)
    c.showPage()
    if details is not None:
        draw_details_page(c, info, details)
        c.showPage()
    c.save()
    return path
