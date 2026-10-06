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
