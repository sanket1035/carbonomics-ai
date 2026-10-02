from emission_factors import EMISSION_FACTORS, unverified_factors
from calculations import calculate_electricity_emissions, calculate_diesel_emissions

REQUIRED = {"factor", "scope", "unit", "output", "source", "version", "verified"}


def test_every_factor_documents_source_version_unit():
    for name, spec in EMISSION_FACTORS.items():
        assert REQUIRED <= spec.keys(), name
        for key in ("unit", "output", "source", "version"):
            assert str(spec[key]).strip(), f"{name}.{key} is empty"


def test_master_data_values():
    assert EMISSION_FACTORS["electricity"]["factor"] == 0.71
    assert EMISSION_FACTORS["diesel"]["factor"] == 2.89
    assert EMISSION_FACTORS["diesel_mobile"]["factor"] == 2.68
    assert EMISSION_FACTORS["methane"]["factor"] == 27.0
    assert EMISSION_FACTORS["nitrous_oxide"]["factor"] == 273


def test_calculations_use_registry():
    assert calculate_electricity_emissions(100.0) == 71.0
    assert calculate_diesel_emissions(100.0) == 289.0


def test_unverified_factors_are_listed():
    assert "public_bus" in unverified_factors()
    assert "electricity" not in unverified_factors()
