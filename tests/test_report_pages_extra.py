import os, sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient

os.environ["AUTH_DISABLED"] = "1"
from api.main import app  # noqa: E402

client = TestClient(app)


def _periods(n, freq="7D", start="2024-01-01"):
    return [{"period_start": str(d.date()), "electricity_kwh": 20000 + 500 * (i % 7), "diesel_litres": 80 + (i % 5)}
            for i, d in enumerate(pd.date_range(start, periods=n, freq=freq))]


def _pages(pdf: bytes) -> int:
    import re
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


def test_weekly_two_years_gives_long_report_with_forecast_and_factor_pages():
    r = client.post("/api/report", json={"periods": _periods(104), "granularity": "weekly", "file_name": "x.csv"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert _pages(r.content) >= 12


def test_short_or_monthly_file_still_gives_a_report():
    r = client.post("/api/report", json={"periods": _periods(12, "MS"), "granularity": "monthly"})
    assert r.status_code == 200 and _pages(r.content) >= 9


def test_report_without_scenario_has_no_scenario_page():
    from io import BytesIO
    pypdf = __import__("pytest").importorskip("pypdf")
    r = client.post("/api/report", json={"periods": _periods(52), "granularity": "weekly"})
    text = "\n".join(p.extract_text() for p in pypdf.PdfReader(BytesIO(r.content)).pages)
    assert "Your what-if scenario" not in text


def test_report_includes_the_saved_scenario_with_matching_numbers():
    from io import BytesIO
    pypdf = __import__("pytest").importorskip("pypdf")
    import upload_analysis
    periods = _periods(52)
    sc = {"electricity_change_pct": -10, "diesel_change_pct": -20, "solar_offset_kwh_per_period": 0}
    r = client.post("/api/report", json={"periods": periods, "granularity": "weekly", "scenario": sc})
    assert r.status_code == 200
    text = "\n".join(p.extract_text() for p in pypdf.PdfReader(BytesIO(r.content)).pages)
    sim = upload_analysis.simulate_upload(periods, **sc)
    assert "Your what-if scenario" in text
    assert f"{sim['totals']['scenario_total_tco2e']:,.2f}" in text and f"{sim['totals']['baseline_total_tco2e']:,.2f}" in text
    assert "-10%" in text and "-20%" in text


def test_report_rejects_a_scenario_outside_the_allowed_range():
    r = client.post("/api/report", json={"periods": _periods(12), "granularity": "weekly",
                                         "scenario": {"electricity_change_pct": -150}})
    assert r.status_code == 422
