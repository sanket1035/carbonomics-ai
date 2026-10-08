"""
test_energy_audit.py

Tests for src/benchmarks.py and src/energy_audit.py.

Hand-checked reference values (KKWIEER Master Data FY2025-26)
    Electricity 1,059,147 kWh / built-up 42,125.27 m2 = 25.14 kWh/m2/year
    5-star cut-off (Composite) 40 -> target 1,685,010.8 kWh -> x 0.71 / 1000 = 1,196.36 tCO2e
    Gap = 751.99 - 1,196.36 = -444.36 tCO2e (campus already below the target)
    Shunya 10 -> target 421,252.7 kWh = 299.09 tCO2e; gap +452.90 tCO2e
    1.5 ton x 3.517 = 5.2755 kW cooling, the sheet lists 5.27 kW as "power" per AC
"""

import pytest

import benchmarks as bm
import energy_audit as ea
from emission_factors import EMISSION_FACTORS


@pytest.fixture(scope="module")
def audit():
    return ea.build_audit(".")


def test_every_benchmark_documents_source_version_unit():
    for b in bm.benchmark_list():
        for key in ("label", "unit", "source", "version", "basis", "role"):
            assert str(b[key]).strip(), f"{b['key']}.{key} is empty"
        assert b["unit"] == "kWh/m2/year"


def test_proxy_benchmarks_are_flagged_unverified():
    assert all(b["verified"] is False for b in bm.benchmark_list())


def test_five_star_cutoffs_by_zone():
    assert bm.five_star_cutoff("composite") == 40
    assert bm.five_star_cutoff("warm_humid") == 45
    assert bm.five_star_cutoff("hot_dry") == 35


def test_star_rating_bands():
    assert bm.star_rating(25.14) == 5
    assert bm.star_rating(40) == 4          # band edge: 5 stars needs EPI strictly below 40
    assert bm.star_rating(55) == 3
    assert bm.star_rating(75) == 1
    assert bm.star_rating(120) == 0


def test_actual_epi(audit):
    a = audit["actual"]
    assert a["electricity_kwh"] == 1059147
    assert a["epi"] == pytest.approx(25.14, abs=0.01)
    assert a["kwh_per_person"] == pytest.approx(112.0, abs=0.1)
    assert a["proxy_star_rating"] == 5


def test_actual_uses_registry_factor(audit):
    f = EMISSION_FACTORS["electricity"]["factor"]
    assert audit["actual"]["grid_factor"] == f
    assert audit["actual"]["electricity_tco2e"] == pytest.approx(1059147 * f / 1000, abs=0.01)


def test_gap_is_negative_when_campus_is_below_target(audit):
    ref = next(r for r in audit["references"] if r["key"] == "bee_office_lt50ac_5star")
    assert ref["target_kwh"] == pytest.approx(1685010.8, abs=0.1)
    assert ref["target_tco2e"] == pytest.approx(1196.36, abs=0.01)
    assert ref["gap_tco2e"] == pytest.approx(-444.36, abs=0.01)
    assert ref["position"] == "below_target"


def test_shunya_gap_is_positive(audit):
    ref = next(r for r in audit["references"] if r["key"] == "shunya_net_zero")
    assert ref["gap_tco2e"] == pytest.approx(452.90, abs=0.01)
    assert ref["position"] == "above_target"


def test_zone_changes_target_not_conclusion():
    a = ea.build_audit(".", zone="warm_humid")
    ref = next(r for r in a["references"] if r["key"] == "bee_office_lt50ac_5star")
    assert ref["benchmark_epi"] == 45
    assert ref["position"] == "below_target"


def test_ac_listed_kw_is_cooling_capacity(audit):
    ac = audit["ac"]
    assert ac["listed_kw_is_cooling_capacity"] is True
    assert ac["units_total"] == 55
    assert ac["modelled_kwh"] == pytest.approx(697296.3, abs=0.1)
    assert ac["modelled_share_of_purchased"] == pytest.approx(0.6584, abs=0.0001)


def test_ac_corrected_is_modelled_divided_by_cop(audit):
    ac = audit["ac"]
    # modelled used 5.27 / 3.5 kW; corrected uses 1.5 x 3.517 / 1 x 3.517 kW cooling, divided by COP
    for k, cop in ea.ASSUMED_COP.items():
        assert ac["corrected_kwh"][k] == pytest.approx(ac["modelled_kwh"] / cop, rel=0.005)
    assert ac["corrected_kwh"]["low"] > ac["corrected_kwh"]["central"] > ac["corrected_kwh"]["high"]
    assert "ASSUMED" in ac["cop_label"]


def test_ac_corrected_share_is_plausible(audit):
    share = audit["ac"]["corrected_share_of_purchased"]
    assert all(0.10 < v < 0.35 for v in share.values())


def test_guest_house_sanity(audit):
    gh = audit["ac"]["sanity_guest_house"]
    assert gh["modelled_ac_kwh_per_m2"] == pytest.approx(338.5, abs=0.1)
    assert gh["corrected_ac_kwh_per_m2"]["central"] < gh["modelled_ac_kwh_per_m2"] / 2


def test_caveats_present(audit):
    text = " ".join(audit["caveats"])
    assert "proxy" in text and "No end-use metering" in text


def test_missing_parameter_raises():
    import pandas as pd
    with pytest.raises(KeyError):
        ea._fact(pd.DataFrame({"parameter": ["x"], "value": [1]}), "built_up_area")
