"""
emission_factors.py

Central configuration file for all emission factors used in Carbonomics-AI.

Every factor carries:
    factor   - numeric value
    unit     - ACTIVITY unit the factor multiplies (kWh, Litre, km, ...)
    output   - unit of the result (kg CO2e per activity unit)
    scope    - GHG Protocol scope used by this project
    source   - publication / dataset the value comes from
    version  - edition / year of that source
    verified - True  : value matches the KKWIEER FY2025-26 Master Data
                       workbook (sheet 17_Emission_Factors) / report Table 4.4
               False : value kept from the earlier code base; the source label
                       has NOT been re-checked against the Master Data and must
                       be confirmed before it is quoted in a report.

Factors are loaded by calculations.py; update values here, not in the
calculation logic.
"""

REFERENCE_DATASET = "KKWIEER Carbon Footprint Master Data FY2025-26 (sheet 17_Emission_Factors)"

EMISSION_FACTORS = {

    "electricity": {
        "factor": 0.71,
        "scope": "Scope 2",
        "unit": "kWh",
        "output": "kg CO2e/kWh",
        "source": "CEA, CO2 Baseline Database for the Indian Power Sector, User Guide",
        "version": "V21.0, Nov 2025",
        "verified": True,
    },

    # Dataset column diesel_litres is stationary diesel-generator fuel.
    "diesel": {
        "factor": 2.89,
        "scope": "Scope 1",
        "unit": "Litre",
        "output": "kg CO2/L",
        "source": "CEA, CO2 Baseline Database, Appendix B (liquid fuel oil)",
        "version": "V20.0, Dec 2024",
        "verified": True,
    },

    # Mobile combustion (bus fleet), per litre of fuel.
    "diesel_mobile": {
        "factor": 2.68,
        "scope": "Scope 1",
        "unit": "Litre",
        "output": "kg CO2e/L",
        "source": "Derived: IPCC 2006 74,100 kgCO2/TJ x NCV 43.0 MJ/kg x 0.84 kg/L (IS 1460)",
        "version": "IPCC 2006 Guidelines",
        "verified": True,
    },

    "petrol_vehicle": {
        "factor": 0.192,
        "scope": "Scope 3",
        "unit": "km",
        "output": "kg CO2e/km",
        "source": "DEFRA (label from earlier code base; not in Master Data)",
        "version": "2024",
        "verified": False,
    },

    "diesel_vehicle": {
        "factor": 0.171,
        "scope": "Scope 3",
        "unit": "km",
        "output": "kg CO2e/km",
        "source": "DEFRA",
        "version": "2024",
        "verified": True,
    },

    # EV charging draws grid electricity, so the grid factor applies.
    "ev": {
        "factor": 0.71,
        "scope": "Scope 3",
        "unit": "kWh",
        "output": "kg CO2e/kWh",
        "source": "CEA, CO2 Baseline Database (same grid factor as 'electricity')",
        "version": "V21.0, Nov 2025",
        "verified": True,
    },

    # Fleet intensity = 56,000 L x 2.68 kgCO2e/L / 280,000 km (Master Data sheet 7).
    "college_bus": {
        "factor": 0.536,
        "scope": "Scope 1",
        "unit": "km",
        "output": "kg CO2e/km",
        "source": "KKWIEER Transport records: 56,000 L/yr x 2.68 / 280,000 km/yr",
        "version": "AY 2025-26",
        "verified": True,
    },

    "public_bus": {
        "factor": 0.105,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "output": "kg CO2e/passenger-km",
        "source": "DEFRA (label from earlier code base; not in Master Data)",
        "version": "2024",
        "verified": False,
    },

    "motorcycle": {
        "factor": 0.103,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "output": "kg CO2e/passenger-km",
        "source": "DEFRA (label from earlier code base; Master Data lists India GHG Program 0.03743 per vehicle-km)",
        "version": "2024",
        "verified": False,
    },

    "auto_rickshaw": {
        "factor": 0.110,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "output": "kg CO2e/passenger-km",
        "source": "DEFRA (label from earlier code base; Master Data lists India GHG Program 0.11779 per vehicle-km)",
        "version": "2024",
        "verified": False,
    },

    "bicycle": {
        "factor": 0.0,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "output": "kg CO2e/passenger-km",
        "source": "Zero direct emission",
        "version": "n/a",
        "verified": True,
    },

    "walking": {
        "factor": 0.0,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "output": "kg CO2e/passenger-km",
        "source": "Zero direct emission",
        "version": "n/a",
        "verified": True,
    },

    "waste_landfill": {
        "factor": 1.90,
        "scope": "Scope 3",
        "unit": "kg",
        "output": "kg CO2e/kg",
        "source": "IPCC 2006 Guidelines, Vol. 5",
        "version": "2006",
        "verified": True,
    },

    "compost_waste": {
        "factor": 0.10,
        "scope": "Scope 3",
        "unit": "kg",
        "output": "kg CO2e/kg",
        "source": "IPCC 2006 Guidelines, Vol. 5",
        "version": "2006",
        "verified": True,
    },

    # GWP-100 values: kg CO2e per kg of gas.
    "methane": {
        "factor": 27.0,
        "scope": "Scope 3",
        "unit": "kg CH4",
        "output": "kg CO2e/kg CH4",
        "source": "IPCC AR6 GWP-100, CH4 non-fossil (GHG Protocol GWP table)",
        "version": "AR6, GHG Protocol table Aug 2024",
        "verified": True,
    },

    "nitrous_oxide": {
        "factor": 273,
        "scope": "Scope 3",
        "unit": "kg N2O",
        "output": "kg CO2e/kg N2O",
        "source": "IPCC AR6 GWP-100, N2O (GHG Protocol GWP table)",
        "version": "AR6, GHG Protocol table Aug 2024",
        "verified": True,
    },
}


def unverified_factors():
    """Names of factors whose source has not been confirmed against the Master Data."""
    return [name for name, spec in EMISSION_FACTORS.items() if not spec["verified"]]


# ── Campus footprint reference ─────────────────────────────────────────────────
# Full KKWIEER footprint for reference / coverage notes.
# Source: KKWIEER Carbon Footprint and Sustainability Report FY2025-26 (revised), Table 1.
REPORT_FOOTPRINT_TCO2E = 3719.74
REPORT_SOURCE = "KKWIEER Carbon Footprint and Sustainability Report FY2025-26 (revised), Table 1"
