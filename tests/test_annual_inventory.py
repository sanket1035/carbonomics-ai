import csv
import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import pandas as pd
import pytest

import annual_inventory as ai
from emission_factors import EMISSION_FACTORS, REPORT_FOOTPRINT_TCO2E

pypdf = pytest.importorskip("pypdf")
MASTER = ROOT / "data" / "real" / "KKWIEER_Carbon_Footprint_Master_Data_FY2025-26.xlsx"


def _write(tmp_path, rows):
    path = tmp_path / "inv.csv"
    cols = ["scope", "source", "activity_value", "activity_unit", "factor_key", "tco2e", "in_total", "basis", "note", "master_data_sheet"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return str(path)


def test_totals_reconcile_with_the_published_footprint():
    inv = ai.load_inventory()
    assert inv["by_scope"] == {"Scope 1": 966.10, "Scope 2": 751.99, "Scope 3": 2001.65}
    assert inv["total"] == REPORT_FOOTPRINT_TCO2E == 3719.74


def test_rows_with_activity_and_factor_are_recomputed_from_the_registry():
    rows = ai.load_inventory()["rows"]
    done = [r for r in rows if r["check"] == "recomputed"]
    assert {r["source"] for r in done} == {"Generator diesel", "College bus fleet", "Purchased electricity",
                                           "Local business travel", "Organised field visits"}
    for r in done:
        assert r["factor"]["value"] == EMISSION_FACTORS[r["factor"]["key"]]["factor"]
        assert abs(r["activity"] * r["factor"]["value"] / 1000 - r["tco2e"]) <= ai.MATCH_TOLERANCE_T
    assert all(r["factor"]["source"] and r["factor"]["version"] and r["factor"]["unit"] for r in done)


def test_commuting_version_b_and_memo_rows_are_not_in_the_total():
    inv = ai.load_inventory()
    assert [r["tco2e"] for r in inv["alternatives"]] == [992.35]
    assert {r["source"] for r in inv["memo"]} == {"Solar avoided emissions", "Green-cover removals"}
    assert [r["source"] for r in inv["excluded"]] == ["Refrigerant leakage (R32)"]    # data gap stays a gap, no number invented
    assert not any(r["tco2e"] is None for r in inv["counted"])


def test_wrong_stated_value_is_refused(tmp_path):
    bad = _write(tmp_path, [{"scope": "Scope 2", "source": "Purchased electricity", "activity_value": "1000000", "activity_unit": "kWh",
                             "factor_key": "electricity", "tco2e": "751.99", "in_total": "yes"}])
    with pytest.raises(ai.InventoryError, match="activity x factor"):
        ai.load_inventory(bad)


def test_unknown_factor_key_is_refused(tmp_path):
    bad = _write(tmp_path, [{"scope": "Scope 1", "source": "X", "activity_value": "1", "factor_key": "made_up", "tco2e": "0.01", "in_total": "yes"}])
    with pytest.raises(ai.InventoryError, match="not in emission_factors"):
        ai.load_inventory(bad)


def test_total_that_does_not_match_the_published_one_is_refused(tmp_path):
    bad = _write(tmp_path, [{"scope": "Scope 1", "source": "Only row", "tco2e": "100", "in_total": "yes"}])
    with pytest.raises(ai.InventoryError, match="published footprint"):
        ai.load_inventory(bad)


def test_india_ghg_factors_match_the_commuting_script():
    import scope3_commuting as s
    reg = {"Two-wheeler": "two_wheeler_india", "Bus": "bus_intracity", "Auto / Cab": "auto_cab_india", "Car": "car_india"}
    for mode, key in reg.items():
        assert s.FACTORS[mode] == EMISSION_FACTORS[key]["factor"] and EMISSION_FACTORS[key]["verified"]


@pytest.mark.skipif(not MASTER.exists(), reason="master data workbook not in the checkout")
def test_stated_values_match_the_master_data_workbook():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(MASTER, data_only=True)
    summary = {(r[0], r[1]): r[2] for r in wb["18_Scope_Summary"].iter_rows(values_only=True) if r[1]}
    stated = {r["source"]: r["tco2e"] for r in ai.load_inventory()["rows"]}
    assert stated["Generator diesel"] == summary[("Scope 1", "Diesel generator")]
    assert stated["College bus fleet"] == summary[("Scope 1", "College bus fleet")]
    assert stated["Domestic wastewater (septic)"] == summary[("Scope 1", "Domestic wastewater (on-site septic)")]
    assert stated["Purchased electricity"] == summary[("Scope 2", "Purchased electricity (gross)")]
    assert stated["Student commuting (Version A)"] == summary[("Scope 3", "Student commuting (Version A)")]
    assert stated["Solid waste"] == summary[("Scope 3", "Solid waste")]
    assert stated["Local business travel"] == summary[("Scope 3", "Local business travel")]
    assert stated["Organised field visits"] == summary[("Scope 3", "Organised field/technical visits")]


@pytest.mark.skipif(not MASTER.exists(), reason="master data workbook not in the checkout")
def test_wastewater_methane_and_nitrous_oxide_add_up_with_registry_gwps():
    openpyxl = pytest.importorskip("openpyxl")
    ws = openpyxl.load_workbook(MASTER, data_only=True)["11_Wastewater"]
    v = {r[0]: r[1] for r in ws.iter_rows(values_only=True) if r[0]}
    ch4_kg, n2o_kg = v["CH4 = (TOW−S)×EF"], v["N2O = N×EF×44/28"]
    t = (ch4_kg * EMISSION_FACTORS["methane"]["factor"] + n2o_kg * EMISSION_FACTORS["nitrous_oxide"]["factor"]) / 1000
    stated = next(r["tco2e"] for r in ai.load_inventory()["rows"] if r["source"].startswith("Domestic wastewater"))
    assert abs(t - stated) <= ai.MATCH_TOLERANCE_T


def _analysis():
    from upload_analysis import analyze
    d = pd.DataFrame({"week_start": pd.date_range("2025-01-01", periods=52, freq="7D").strftime("%Y-%m-%d"),
                      "electricity_kwh": [20000.0] * 52, "diesel_litres": [80.0] * 52})
    return analyze(d.to_csv(index=False).encode())


def _text(path):
    return "\n".join(p.extract_text() for p in pypdf.PdfReader(path).pages)


def test_report_pages_show_all_three_scopes_source_and_factors(tmp_path):
    from reportlab.pdfgen import canvas
    import report_annual as ra
    inv = ai.load_inventory()
    path = str(tmp_path / "a.pdf")
    c = canvas.Canvas(path, pagesize=(595.27, 841.89))
    ends = [ra.draw_campus_page(c, inv, 6)]
    c.showPage()
    ends.append(ra.draw_campus_notes_page(c, inv, 7))
    c.showPage()
    c.save()
    assert all(y >= 60 for y in ends), ends          # nothing runs into the page number
    t = _text(path)
    for needle in ("3,719.74", "966.10", "751.99", "2,001.65", "Young Indians", "1,896.90", "992.35", "2,815.19",
                   "not measured", "India GHG Program", "V21.0", "Not subtracted"):
        assert needle in t, needle


def test_full_report_has_the_annual_pages_only_when_given(tmp_path):
    from report_pages import build_full_report
    with_inv = build_full_report(str(tmp_path / "w.pdf"), _analysis(), inventory=ai.load_inventory())
    without = build_full_report(str(tmp_path / "o.pdf"), _analysis())
    n_with, n_without = len(pypdf.PdfReader(with_inv).pages), len(pypdf.PdfReader(without).pages)
    assert n_with == n_without + 2
    t_with, t_without = _text(with_inv), _text(without)
    assert "Full campus footprint" in t_with and "Scope 3 is not included" not in t_with
    assert "Full campus footprint" not in t_without and "Scope 3 is not included" in t_without


def test_api_report_includes_the_annual_pages_by_default_and_can_skip_them():
    os.environ["AUTH_DISABLED"] = "1"
    from fastapi.testclient import TestClient
    from api.main import app
    import re
    client = TestClient(app)
    periods = [{"period_start": str(d.date()), "electricity_kwh": 20000.0, "diesel_litres": 80.0}
               for d in pd.date_range("2025-01-01", periods=52, freq="7D")]
    pages = lambda b: len(re.findall(rb"/Type\s*/Page[^s]", b))
    on = client.post("/api/report", json={"periods": periods, "granularity": "weekly"})
    off = client.post("/api/report", json={"periods": periods, "granularity": "weekly", "include_campus_inventory": False})
    assert on.status_code == off.status_code == 200
    # 2 yearly Scope 1/2/3 pages, then the Energy Audit pages (result, AC check, 2 or more suggestion pages)
    assert pages(on.content) >= pages(off.content) + 2 + 4
