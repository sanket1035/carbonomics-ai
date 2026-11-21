import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pytest

import campus_footprint_report as cfr

COLS = ["scope", "source", "activity_value", "activity_unit", "factor_key", "tco2e", "basis", "note", "report_location"]


def _copy(tmp_path, edit):
    rows = list(csv.DictReader(open(cfr.REPORT_PATH, encoding="utf-8", newline="")))
    edit(rows)
    path = tmp_path / "r.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    return str(path)


def test_report_matches_published_figures():
    r = cfr.load_report()
    assert r["by_scope"] == {"Scope 1": 138.29, "Scope 2": 751.99, "Scope 3": 1101.78}
    assert r["total"] == 1992.06


def test_memo_rows_are_not_in_the_total():
    r = cfr.load_report()
    assert {m["source"] for m in r["memo"]} == {"Rooftop solar avoided emissions", "Campus trees (carbon removal)"}
    assert all(row["in_total"] == "yes" for row in r["counted"])
    assert round(sum(row["tco2e"] for row in r["counted"]), 2) == 1992.06


def test_rows_with_a_factor_are_recomputed_from_the_registry():
    rows = {x["source"]: x for x in cfr.load_report()["rows"]}
    e = rows["Purchased electricity"]
    assert e["check"] == "recomputed" and e["factor"]["version"] and e["factor"]["source"] and e["factor"]["unit"]
    assert rows["Student commuting"]["check"] == "stated" and rows["Student commuting"]["factor"] is None


def test_a_wrong_stated_value_is_rejected(tmp_path):
    def edit(rows):
        next(r for r in rows if r["source"] == "Purchased electricity")["tco2e"] = "800.00"
    with pytest.raises(cfr.ReportError):
        cfr.load_report(_copy(tmp_path, edit))


def test_scope_subtotal_mismatch_is_rejected(tmp_path):
    def edit(rows):
        next(r for r in rows if r["source"] == "Solid waste")["tco2e"] = "70.00"
    with pytest.raises(cfr.ReportError):
        cfr.load_report(_copy(tmp_path, edit))


def test_unknown_factor_key_is_rejected(tmp_path):
    def edit(rows):
        next(r for r in rows if r["source"] == "Diesel generator")["factor_key"] = "made_up"
    with pytest.raises(cfr.ReportError):
        cfr.load_report(_copy(tmp_path, edit))


def test_report_pdf_shows_the_campus_report_scope3(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    pytest.importorskip("reportlab")
    import report_annual as ra
    from reportlab.pdfgen import canvas
    path = tmp_path / "a.pdf"
    c = canvas.Canvas(str(path))
    inv = cfr.load_report()
    ra.draw_campus_page(c, inv, 1)
    c.showPage()
    ra.draw_campus_notes_page(c, inv, 2)
    c.showPage()
    c.save()
    text = " ".join(p.extract_text() for p in pypdf.PdfReader(str(path)).pages)
    for needle in ("1,992.06", "138.29", "751.99", "1,101.78", "992.35", "Young Indians", "15.42"):
        assert needle in text
    assert "3,719.74" not in text
