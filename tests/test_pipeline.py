import pandas as pd
import pytest

import clean_data
import make_synthetic_weekly as syn
from database import db_manager
from process_dataset import process_dataset
from validation import qa_validator


@pytest.fixture()
def clean_file(tmp_path):
    weekly = syn.to_weekly(syn.build_daily(pd.read_csv(syn.REAL_FILE)))
    src, out = tmp_path / "weekly.csv", tmp_path / "clean.csv"
    weekly.to_csv(src, index=False)
    clean_data.clean_dataset(str(src), str(out))
    return out


def test_clean_rejects_negative_and_gaps(tmp_path):
    weekly = syn.to_weekly(syn.build_daily(pd.read_csv(syn.REAL_FILE)))
    bad = weekly.copy()
    bad.loc[3, "electricity_kwh"] = -1
    with pytest.raises(ValueError):
        clean_data.validate_negative_values(bad)
    gap = weekly.drop(index=5)
    with pytest.raises(ValueError):
        clean_data.validate_weekly_dates(gap)


def test_emission_is_activity_times_factor(clean_file, tmp_path):
    out = tmp_path / "emissions.csv"
    df = process_dataset(str(clean_file), str(out))
    assert (df["scope1_kg"] + df["scope2_kg"] + df["scope3_kg"] - df["total_kg"]).abs().max() < 0.011
    assert (df["electricity_emission_kg"] - (df["electricity_kwh"] * 0.71).round(2)).abs().max() < 0.011


def test_db_step_skips_without_credentials(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    assert db_manager.upsert_weekly_activity()["status"] == "SKIPPED"
    assert db_manager.upsert_forecast_results()["status"] == "SKIPPED"


def test_qa_report_status_is_computed(tmp_path, monkeypatch):
    monkeypatch.setattr(qa_validator, "CLEAN_FILE", str(tmp_path / "missing.csv"))
    assert qa_validator.run_data_qa(str(tmp_path / "missing.csv"))["ok"] is False
