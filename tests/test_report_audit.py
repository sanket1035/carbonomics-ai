import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
import pytest

pypdf = pytest.importorskip("pypdf")
from energy_audit import build_audit
from report_pages import build_full_report
from upload_analysis import analyze


def _analysis():
    d = pd.DataFrame({"month": [f"2025-{m:02d}-01" for m in range(1, 13)],
                      "electricity_kwh": [90000.0] * 12, "diesel_litres": [100.0] * 12})
    a = analyze(d.to_csv(index=False).encode())
    a["forecast"] = {"status": "skipped", "reason": "test"}
    return a


def _text(path):
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(path).pages)


@pytest.fixture(scope="module")
def audit():
    return build_audit(str(ROOT), "composite")


def test_report_without_audit_has_no_audit_pages(tmp_path):
    out = build_full_report(str(tmp_path / "r.pdf"), _analysis())
    assert "Energy Audit" not in _text(out)


def test_report_with_audit_has_result_ac_check_and_every_suggestion(tmp_path, audit):
    base = len(pypdf.PdfReader(build_full_report(str(tmp_path / "a.pdf"), _analysis())).pages)
    out = build_full_report(str(tmp_path / "b.pdf"), _analysis(), energy_audit=audit)
    t = _text(out)
    assert len(pypdf.PdfReader(out).pages) >= base + 4          # result, AC check, 2+ suggestion pages
    assert "Air-conditioning check" in t and "ASSUMED" in t
    assert f"{audit['actual']['epi']:.1f}" in t
    for s in audit["suggestions"]:
        assert s["title"].split()[0] in t
        assert s["title"][:20] in t.replace("\n", " ")


def test_suggestion_pages_keep_numbers_to_the_campus_data(tmp_path, audit):
    t = _text(build_full_report(str(tmp_path / "c.pdf"), _analysis(), energy_audit=audit)).replace("\n", " ")
    # lights, fans and pumps show only a published figure with its source, never a campus kWh number
    assert "Williams et al." in t and "EESL" in t
    for s in audit["suggestions"]:
        if s["status"] != "scenario":
            assert s["campus_number"] is None


def test_every_page_after_the_cover_has_the_frame(tmp_path, audit):
    out = build_full_report(str(tmp_path / "d.pdf"), _analysis(), energy_audit=audit)
    pages = pypdf.PdfReader(out).pages
    # the frame is a stroked rectangle 20 pt from the page edge; the cover has none
    marker = "20 20 555.2756 801.8898 re S"                   # the outer frame rectangle (20 pt margin)
    assert marker not in pages[0].get_contents().get_data().decode("latin-1")
    for p in pages[1:]:
        assert marker in p.get_contents().get_data().decode("latin-1")


def test_notes_page_lists_the_benchmark_sources_only_with_the_audit(tmp_path, audit):
    with_audit = _text(build_full_report(str(tmp_path / "e.pdf"), _analysis(), energy_audit=audit)).replace("\n", " ")
    without = _text(build_full_report(str(tmp_path / "f.pdf"), _analysis())).replace("\n", " ")
    assert "Scheme for BEE Star Rating for Office Buildings" in with_audit
    assert "Scheme for BEE Star Rating for Office Buildings" not in without
