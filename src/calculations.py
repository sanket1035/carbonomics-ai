"""
calculations.py

Business logic for Carbonomics-AI.

This module contains all carbon emission calculation
functions based on approved emission factors.
"""

from emission_factors import EMISSION_FACTORS


# ==========================================================
# Generic Helper Function
# ==========================================================

def calculate_emission(activity: str, value: float) -> float:
    """
    Generic emission calculator.

    Parameters:
        activity (str): Activity key from EMISSION_FACTORS.
        value (float): Activity value (kWh, litres, km, etc.)

    Returns:
        float: Carbon emissions in kg CO₂e.
    """

    factor = EMISSION_FACTORS[activity]["factor"]

    return round(value * factor, 2)


# ==========================================================
# Scope 1 — Direct Emissions
# ==========================================================

def calculate_diesel_emissions(diesel_litres: float) -> float:
    """Calculate emissions from diesel consumption."""
    return calculate_emission("diesel", diesel_litres)


def calculate_college_bus_emissions(distance_km: float) -> float:
    """Calculate emissions from college-owned buses."""
    return calculate_emission("college_bus", distance_km)


# ==========================================================
# Scope 2 — Purchased Electricity
# ==========================================================

def calculate_electricity_emissions(electricity_kwh: float) -> float:
    """Calculate emissions from purchased electricity."""
    return calculate_emission("electricity", electricity_kwh)


# ==========================================================
# Scope 3 — Other Indirect Emissions
# ==========================================================

def calculate_petrol_transport_emissions(distance_km: float) -> float:
    """Calculate emissions from petrol vehicles."""
    return calculate_emission("petrol_vehicle", distance_km)


def calculate_diesel_transport_emissions(distance_km: float) -> float:
    """Calculate emissions from diesel vehicles."""
    return calculate_emission("diesel_vehicle", distance_km)


def calculate_ev_transport_emissions(electricity_kwh: float) -> float:
    """Calculate emissions from electric vehicle charging."""
    return calculate_emission("ev", electricity_kwh)


def calculate_public_bus_emissions(passenger_km: float) -> float:
    """Calculate emissions from public bus transport."""
    return calculate_emission("public_bus", passenger_km)

def calculate_motorcycle_emissions(passenger_km: float) -> float:
    """Calculate emissions from motorcycle transport."""
    return calculate_emission("motorcycle", passenger_km)


def calculate_auto_rickshaw_emissions(passenger_km: float) -> float:
    """Calculate emissions from auto-rickshaw transport."""
    return calculate_emission("auto_rickshaw", passenger_km)


def calculate_bicycle_emissions(passenger_km: float) -> float:
    """Calculate emissions from bicycle transport."""
    return calculate_emission("bicycle", passenger_km)


def calculate_walking_emissions(passenger_km: float) -> float:
    """Calculate emissions from walking."""
    return calculate_emission("walking", passenger_km)


def calculate_waste_emissions(waste_kg: float) -> float:
    """Calculate emissions from landfill waste."""
    return calculate_emission("waste_landfill", waste_kg)


def calculate_compost_waste_emissions(waste_kg: float) -> float:
    """Calculate emissions from compost waste."""
    return calculate_emission("compost_waste", waste_kg)


def calculate_methane_emissions(methane_kg: float) -> float:
    """Calculate methane emissions."""
    return calculate_emission("methane", methane_kg)


def calculate_nitrous_oxide_emissions(nitrous_oxide_kg: float) -> float:
    """Calculate nitrous oxide emissions."""
    return calculate_emission("nitrous_oxide", nitrous_oxide_kg)


# ==========================================================
# Total Emission Calculator
# ==========================================================

def calculate_total_emissions(
    scope1: float,
    scope2: float,
    scope3: float,
) -> float:
    """
    Calculate total carbon emissions.

    Parameters:
        scope1 (float): Scope 1 emissions.
        scope2 (float): Scope 2 emissions.
        scope3 (float): Scope 3 emissions.

    Returns:
        float: Total carbon emissions.
    """

    return round(
        scope1 + scope2 + scope3,
        2,
    )