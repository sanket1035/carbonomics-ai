"""
test_simulation.py

Tests for src/simulation.py — what-if accounting simulation.

Hand-checked reference values
------------------------------
Annual electricity 2025: 1,059,147 kWh × 0.71 kg CO2e/kWh = 752,994.37 kg = 752.99 tCO2e
Annual diesel 2025:      4,100 L    × 2.89 kg CO2/L       =  11,849.00 kg =  11.85 tCO2e
Total baseline:                                                             764.84 tCO2e (rounded)

−10 % electricity: saves 752.99 × 0.10 = 75.30 tCO2e (approx)
Solar offset 10 000 kWh/month = 120 000 kWh/year × 0.71 / 1000 = 85.20 tCO2e (approx)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd
import pytest
import simulation as sim


# ── fixture ────────────────────────────────────────────────────────────────────
REAL_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "real", "real_monthly_2025.csv")


@pytest.fixture()
def real_df():
    return pd.read_csv(REAL_CSV)


# ── baseline ───────────────────────────────────────────────────────────────────
def test_baseline_row_count(real_df):
    df = sim.baseline(real_df)
    assert len(df) == 12


def test_baseline_scope_labels(real_df):
    """electricity → Scope 2, diesel → Scope 1."""
    df = sim.baseline(real_df)
    # Scope 2 = electricity × 0.71
    for _, row in df.iterrows():
        assert abs(row["scope2_kg"] - row["electricity_kwh"] * 0.71) < 1e-6
        assert abs(row["scope1_kg"] - row["diesel_litres"] * 2.89) < 1e-6


def test_baseline_annual_electricity_tco2e(real_df):
    """Annual electricity tCO2e ≈ 752.99 (1 059 147 kWh × 0.71 / 1000)."""
    df = sim.baseline(real_df)
    annual_scope2 = df["scope2_tco2e"].sum()
    expected = 1059147 * 0.71 / 1000  # 751.994...  ← 2025 sum from real data
    assert abs(annual_scope2 - expected) < 0.01


def test_baseline_annual_diesel_tco2e(real_df):
    """Annual diesel tCO2e ≈ 11.85 (4 100 L × 2.89 / 1000)."""
    df = sim.baseline(real_df)
    annual_scope1 = df["scope1_tco2e"].sum()
    expected = 4100 * 2.89 / 1000
    assert abs(annual_scope1 - expected) < 0.01


# ── simulate: zero change is identity ─────────────────────────────────────────
def test_zero_change_returns_baseline(real_df):
    result = sim.simulate(real_df)
    base_df = sim.baseline(real_df)
    for row, base_row in zip(result["monthly"], base_df.to_dict("records")):
        # simulate() rounds monthly rows to 4 decimals, so tolerance = 1e-4
        assert abs(row["base_total_tco2e"] - base_row["total_tco2e"]) < 1e-4
        assert abs(row["scen_total_tco2e"] - base_row["total_tco2e"]) < 1e-4
    assert result["annual"]["saved_tco2e"] == pytest.approx(0.0, abs=1e-4)


# ── simulate: −10 % electricity ───────────────────────────────────────────────
def test_minus_10pct_electricity_saves_approx_75t(real_df):
    result = sim.simulate(real_df, electricity_change_pct=-10.0)
    saved = result["annual"]["saved_tco2e"]
    # 1 059 147 × 0.10 × 0.71 / 1000 ≈ 75.20 tCO2e
    assert 74.0 < saved < 77.0


def test_minus_10pct_electricity_only_affects_scope2(real_df):
    result = sim.simulate(real_df, electricity_change_pct=-10.0)
    assert result["annual"]["saved_scope1_tco2e"] == pytest.approx(0.0, abs=1e-4)
    assert result["annual"]["saved_scope2_tco2e"] > 70.0


# ── simulate: diesel change ───────────────────────────────────────────────────
def test_minus_100pct_diesel_zeroes_scope1(real_df):
    result = sim.simulate(real_df, diesel_change_pct=-100.0)
    assert result["annual"]["scenario_scope1_tco2e"] == pytest.approx(0.0, abs=1e-6)


def test_plus_50pct_diesel_increases_scope1(real_df):
    result = sim.simulate(real_df, diesel_change_pct=50.0)
    assert result["annual"]["saved_scope1_tco2e"] < 0  # negative saving = increase


# ── simulate: solar offset ────────────────────────────────────────────────────
def test_solar_offset_10000_kwh_per_month(real_df):
    """10 000 kWh/month × 12 × 0.71 / 1000 ≈ 85.20 tCO2e saved."""
    result = sim.simulate(real_df, solar_offset_kwh_per_month=10_000)
    saved = result["annual"]["saved_tco2e"]
    assert 80.0 < saved < 90.0


def test_solar_offset_does_not_push_electricity_negative(real_df):
    """Extremely large solar offset → electricity clamped at 0, not negative."""
    result = sim.simulate(real_df, solar_offset_kwh_per_month=1_000_000)
    for row in result["monthly"]:
        assert row["scen_electricity_kwh"] >= 0.0
        assert row["scen_scope2_tco2e"] >= 0.0


# ── input validation ──────────────────────────────────────────────────────────
def test_electricity_change_above_100_raises(real_df):
    with pytest.raises(ValueError, match="electricity_change_pct"):
        sim.simulate(real_df, electricity_change_pct=101.0)


def test_electricity_change_below_minus_100_raises(real_df):
    with pytest.raises(ValueError, match="electricity_change_pct"):
        sim.simulate(real_df, electricity_change_pct=-101.0)


def test_diesel_change_out_of_range_raises(real_df):
    with pytest.raises(ValueError, match="diesel_change_pct"):
        sim.simulate(real_df, diesel_change_pct=200.0)


def test_negative_solar_offset_raises(real_df):
    with pytest.raises(ValueError, match="solar_offset_kwh_per_month"):
        sim.simulate(real_df, solar_offset_kwh_per_month=-1.0)


# ── result structure ───────────────────────────────────────────────────────────
def test_result_has_required_keys(real_df):
    result = sim.simulate(real_df, electricity_change_pct=-5.0, diesel_change_pct=-5.0)
    for key in ("monthly", "annual", "factors_used", "coverage_note", "inputs", "presets_note"):
        assert key in result, f"Missing key: {key}"


def test_factors_used_cites_electricity_and_diesel(real_df):
    result = sim.simulate(real_df)
    names = {f["name"] for f in result["factors_used"]}
    assert "electricity" in names
    assert "diesel" in names
    for f in result["factors_used"]:
        assert f["source"] and f["version"] and f["unit"]


def test_coverage_note_structure(real_df):
    result = sim.simulate(real_df)
    cn = result["coverage_note"]
    assert cn["full_footprint_tco2e"] == 3719.74
    assert 19.0 < cn["covered_share_pct"] < 22.0  # ~20.5 %
    assert len(cn["not_covered"]) >= 3


def test_inputs_echoed_back(real_df):
    result = sim.simulate(real_df, electricity_change_pct=-15.0, solar_offset_kwh_per_month=5000.0)
    inp = result["inputs"]
    assert inp["electricity_change_pct"] == -15.0
    assert inp["solar_offset_kwh_per_month"] == 5000.0


def test_presets_note_says_illustrative(real_df):
    result = sim.simulate(real_df)
    assert "ILLUSTRATIVE" in result["presets_note"].upper()


# ── scope labels correct ───────────────────────────────────────────────────────
def test_monthly_row_contains_scope_columns(real_df):
    result = sim.simulate(real_df, electricity_change_pct=-10.0)
    row = result["monthly"][0]
    for col in ("base_scope2_tco2e", "base_scope1_tco2e", "scen_scope2_tco2e", "scen_scope1_tco2e"):
        assert col in row
