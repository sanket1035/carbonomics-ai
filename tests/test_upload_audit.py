"""Tests for src/upload_audit.py: the Energy Audit built from an uploaded master CSV. All data here is generated test data."""

import io

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import energy_audit
import upload_analysis as ua
from api.main import app

client = TestClient(app)

COLS = ["section", "name", "week_start", "electricity_kwh", "solar_kwh", "diesel_litres", "value", "unit",
        "units", "capacity_ton", "listed_kw_per_unit", "daily_hours", "days_per_year"]


@pytest.fixture(autouse=True)
def _no_login(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "1")


def master(weeks=52, area=10000.0, persons=None, ac=True, kwh=20000.0):
    rows = [{"section": "building", "name": "built_up_area", "value": area, "unit": "m2"}]
    if persons:
        rows.append({"section": "building", "name": "total_persons", "value": persons, "unit": "persons"})
    if ac:
        rows += [{"section": "ac", "name": "Block A", "units": 10, "capacity_ton": 1.5, "listed_kw_per_unit": 5.27, "daily_hours": 8, "days_per_year": 250},
                 {"section": "ac", "name": "Block B", "units": 4, "capacity_ton": 1.0, "listed_kw_per_unit": 3.5, "daily_hours": 10, "days_per_year": 250}]
    for i, d in enumerate(pd.date_range("2025-01-06", periods=weeks, freq="7D")):
        rows.append({"section": "weekly", "week_start": d.strftime("%Y-%m-%d"), "electricity_kwh": kwh, "solar_kwh": 100.0,
                     "diesel_litres": 10.0 if i % 4 == 0 else 0.0})
    return pd.DataFrame(rows, columns=COLS)


def raw(df):
    return df.to_csv(index=False).encode()


def test_master_csv_gives_audit_and_normal_analysis():
    r = ua.analyze(raw(master(persons=500)))
    assert r["energy_audit_status"]["status"] == "ok"
    a = r["energy_audit"]
    assert r["input"]["rows"] == 52 and r["input"]["granularity_analysed"] == "weekly"
    assert a["from_upload"] is True
    assert a["actual"]["electricity_kwh"] == pytest.approx(20000 * 52)
    assert a["actual"]["epi"] == pytest.approx(20000 * 52 / 10000, abs=0.01)
    assert a["actual"]["persons"] == 500 and a["actual"]["kwh_per_person"] == pytest.approx(20000 * 52 / 500, abs=0.1)
    assert a["actual"]["area_source"] == "Your file (building section)"


def test_ac_estimate_is_the_formula_with_assumed_cop():
    a = ua.analyze(raw(master()))["energy_audit"]["ac"]
    thermal = lambda ton: ton * energy_audit.TON_REFRIGERATION_KW_THERMAL  # noqa: E731
    hours = [10 * 250 * 8 * thermal(1.5), 4 * 250 * 10 * thermal(1.0)]
    assert a["corrected_kwh"]["central"] == pytest.approx(sum(hours) / 3.0, abs=1)
    assert a["modelled_kwh"] == pytest.approx(10 * 250 * 8 * 5.27 + 4 * 250 * 10 * 3.5, abs=1)
    assert a["sanity_guest_house"] is None          # no guest house area in the file


def test_nothing_from_the_campus_files_leaks_into_an_upload():
    a = ua.analyze(raw(master()))["energy_audit"]
    assert a["reduction"]["bus"] is None
    text = str(a)
    assert "KKWIEER" not in text and "Admission Brochure" not in text and "College bus fleet" not in text


def test_solar_in_file_is_used_for_the_solar_suggestion():
    sug = ua.analyze(raw(master()))["energy_audit"]["suggestions"]
    ev = " ".join(e for s in sug for e in s["campus_evidence"] if "rooftop solar generated" in e)
    assert "5,200 kWh" in ev                         # 52 weeks x 100 kWh, not the campus 21,720 kWh


def test_fewer_than_40_weeks_gives_a_reason_not_a_guess():
    r = ua.analyze(raw(master(weeks=30)))
    assert r["energy_audit"] is None and r["energy_audit_status"]["status"] == "error"
    assert "at least 40 weeks" in r["energy_audit_status"]["reason"]
    assert r["input"]["rows"] == 30                  # the carbon analysis still ran


def test_partial_year_is_scaled_and_labelled():
    a = ua.analyze(raw(master(weeks=48)))["energy_audit"]
    assert a["actual"]["electricity_kwh"] == pytest.approx(20000 * 52, rel=1e-6)
    assert "scaled" in a["period"]


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d[~((d.section == "building") & (d.name == "built_up_area"))], "built_up_area"),
    (lambda d: d[d.section != "ac"], "No 'ac' rows"),
    (lambda d: d.assign(daily_hours=d.daily_hours.where(d.section != "ac", 30)), "at most 24"),
    (lambda d: d.assign(value=d.value.where(d.section != "building", -5)), "greater than 0"),
])
def test_bad_building_or_ac_rows_are_explained(mutate, msg):
    r = ua.analyze(raw(mutate(master())))
    assert r["energy_audit"] is None and msg in r["energy_audit_status"]["reason"]


def test_plain_weekly_file_has_no_audit_but_says_why():
    plain = master().query("section == 'weekly'")[["week_start", "electricity_kwh", "diesel_litres"]]
    r = ua.analyze(raw(plain))
    assert r["energy_audit"] is None and r["energy_audit_status"]["status"] == "missing"


def test_unknown_section_is_refused():
    d = master()
    d.loc[0, "section"] = "roof"
    with pytest.raises(ua.UploadError, match="Unknown section"):
        ua.analyze(raw(d))


def test_endpoint_returns_audit_as_json():
    resp = client.post("/api/analyze", files={"file": ("m.csv", io.BytesIO(raw(master())), "text/csv")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["energy_audit"]["actual"]["built_up_area_m2"] == 10000.0
    assert body["energy_audit_status"]["status"] == "ok"


def test_campus_audit_is_unchanged():
    a = energy_audit.build_audit(".")
    assert a["from_upload"] is False and a["actual"]["epi"] == pytest.approx(25.14, abs=0.01)
    assert a["reduction"]["bus"] is not None
