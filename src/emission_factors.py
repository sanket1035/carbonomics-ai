"""
emission_factors.py

Central configuration file for all emission factors used in Carbonomics-AI.

All emission factors, units, scopes, and reference sources are stored
here so that updates can be made without modifying calculation logic.
"""

EMISSION_FACTORS = {

    "electricity": {
        "factor": 0.7117,
        "scope": "Scope 2",
        "unit": "kWh",
        "source": "CEA India"
    },

    "diesel": {
        "factor": 2.68,
        "scope": "Scope 1",
        "unit": "Litre",
        "source": "IPCC 2006"
    },

    "petrol_vehicle": {
        "factor": 0.192,
        "scope": "Scope 3",
        "unit": "km",
        "source": "DEFRA 2024"
    },

    "diesel_vehicle": {
        "factor": 0.171,
        "scope": "Scope 3",
        "unit": "km",
        "source": "DEFRA 2024"
    },

    "ev": {
        "factor": 0.716,
        "scope": "Scope 3",
        "unit": "kWh",
        "source": "CEA India"
    },

    "college_bus": {
        "factor": 0.822,
        "scope": "Scope 1",
        "unit": "km",
        "source": "GHG Protocol"
    },

    "public_bus": {
        "factor": 0.105,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "source": "DEFRA 2024"
    },

    "motorcycle": {
        "factor": 0.103,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "source": "DEFRA 2024"
    },

    "auto_rickshaw": {
        "factor": 0.110,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "source": "DEFRA 2024"
    },

    "bicycle": {
        "factor": 0.0,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "source": "Zero Emission"
    },

    "walking": {
        "factor": 0.0,
        "scope": "Scope 3",
        "unit": "passenger-km",
        "source": "Zero Emission"
    },

    "waste_landfill": {
        "factor": 1.90,
        "scope": "Scope 3",
        "unit": "kg",
        "source": "IPCC 2006"
    },

    "compost_waste": {
        "factor": 0.10,
        "scope": "Scope 3",
        "unit": "kg",
        "source": "IPCC Guidelines"
    },

    "methane": {
        "factor": 28,
        "scope": "Scope 3",
        "unit": "kg CH4",
        "source": "IPCC AR6"
    },

    "nitrous_oxide": {
        "factor": 265,
        "scope": "Scope 3",
        "unit": "kg N2O",
        "source": "IPCC AR6"
    }
}