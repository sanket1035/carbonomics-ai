import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from upload_analysis import analyze  # noqa: E402

CSV = os.path.join(ROOT, "data", "synthetic", "campus_like_weekly_demo.csv")


def test_demo_csv_is_labelled_complete_and_uploadable():
    d = pd.read_csv(CSV)
    assert list(d.columns) == ["week_start", "electricity_kwh", "solar_kwh", "diesel_litres", "data_label"]
    assert len(d) == 104 and (d["data_label"] == "DEMO (synthetic)").all()
    assert d[["electricity_kwh", "solar_kwh", "diesel_litres"]].ge(0).all().all() and not d.isnull().any().any()
    assert pd.to_datetime(d["week_start"]).diff().dropna().eq(pd.Timedelta(days=7)).all()
    a = analyze(open(CSV, "rb").read())
    assert a["input"]["rows"] == 104 and a["input"]["granularity_detected"] == "weekly"


def test_demo_csv_is_close_to_but_not_the_real_campus_totals():
    d = pd.read_csv(CSV)
    real = pd.read_csv(os.path.join(ROOT, "data", "real", "real_monthly_2025.csv"))["electricity_kwh"].sum()
    y25 = d.loc[d["week_start"].str.startswith("2025"), "electricity_kwh"].sum()
    assert 0.8 * real < y25 < 1.05 * real and abs(y25 - real) > 1000


def test_demo_csv_script_is_repeatable(tmp_path):
    before = open(CSV, "rb").read()
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_upload_demo_csv.py")], cwd=ROOT, check=True, capture_output=True)
    assert open(CSV, "rb").read() == before
