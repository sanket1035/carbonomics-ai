"""
process_dataset.py

Carbonomics-AI Dataset Processing Module

This module:
1. Loads the cleaned institutional dataset.
2. Calculates carbon emissions for each record.
3. Computes Scope 1, Scope 2, Scope 3, and Total emissions.
4. Exports the processed dataset as a CSV report.
"""

import os

from data_loader import load_dataset

from calculations import (
    calculate_electricity_emissions,
    calculate_diesel_emissions,
    calculate_petrol_transport_emissions,
    calculate_diesel_transport_emissions,
    calculate_ev_transport_emissions,
    calculate_college_bus_emissions,
    calculate_public_bus_emissions,
    calculate_motorcycle_emissions,
    calculate_auto_rickshaw_emissions,
    calculate_bicycle_emissions,
    calculate_walking_emissions,
    calculate_waste_emissions,
    calculate_compost_waste_emissions,
    calculate_methane_emissions,
    calculate_nitrous_oxide_emissions,
    calculate_total_emissions,
)

INPUT_FILE = "data/processed/cleaned_dataset.csv"

OUTPUT_DIRECTORY = "outputs"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIRECTORY,
    "carbon_report.csv",
)


def process_dataset():
    """
    Process the institutional dataset and generate
    a carbon emission report.
    """

    # ==========================================================
    # Load Dataset
    # ==========================================================

    dataset = load_dataset(INPUT_FILE)

    # ==========================================================
    # Result Storage
    # ==========================================================

    scope1_results = []
    scope2_results = []
    scope3_results = []
    total_results = []

    # ==========================================================
    # Process Each Record
    # ==========================================================

    for _, row in dataset.iterrows():

        # -------------------------
        # Activity Data
        # -------------------------

        electricity = row["electricity_kwh"]

        diesel = row["diesel_litres"]

        petrol_distance = row["petrol_distance_km"]

        diesel_distance = row["diesel_distance_km"]

        ev_electricity = row["ev_electricity_kwh"]

        college_bus = row["college_bus_distance_km"]

        public_bus = row["public_bus_passenger_km"]

        motorcycle = row["motorcycle_passenger_km"]

        auto = row["auto_passenger_km"]

        bicycle = row["bicycle_passenger_km"]

        walking = row["walking_passenger_km"]

        landfill_waste = row["waste_landfill_kg"]

        compost_waste = row["compost_waste_kg"]

        methane = row["methane_kg"]

        nitrous_oxide = row["nitrous_oxide_kg"]

        # -------------------------
        # Individual Calculations
        # -------------------------

        electricity_emission = calculate_electricity_emissions(
            electricity
        )

        diesel_emission = calculate_diesel_emissions(
            diesel
        )

        college_bus_emission = calculate_college_bus_emissions(
            college_bus
        )

        petrol_emission = calculate_petrol_transport_emissions(
            petrol_distance
        )

        diesel_transport_emission = (
            calculate_diesel_transport_emissions(
                diesel_distance
            )
        )

        ev_emission = calculate_ev_transport_emissions(
            ev_electricity
        )

        public_bus_emission = (
            calculate_public_bus_emissions(
                public_bus
            )
        )

        motorcycle_emission = (
            calculate_motorcycle_emissions(
                motorcycle
            )
        )

        auto_emission = (
            calculate_auto_rickshaw_emissions(
                auto
            )
        )

        bicycle_emission = (
            calculate_bicycle_emissions(
                bicycle
            )
        )

        walking_emission = (
            calculate_walking_emissions(
                walking
            )
        )

        landfill_emission = (
            calculate_waste_emissions(
                landfill_waste
            )
        )

        compost_emission = (
            calculate_compost_waste_emissions(
                compost_waste
            )
        )

        methane_emission = (
            calculate_methane_emissions(
                methane
            )
        )

        nitrous_oxide_emission = (
            calculate_nitrous_oxide_emissions(
                nitrous_oxide
            )
        )

                # -------------------------
        # Scope Calculations
        # -------------------------

        scope1 = (
            diesel_emission +
            college_bus_emission
        )

        scope2 = electricity_emission

        scope3 = (
            petrol_emission +
            diesel_transport_emission +
            ev_emission +
            public_bus_emission +
            motorcycle_emission +
            auto_emission +
            bicycle_emission +
            walking_emission +
            landfill_emission +
            compost_emission +
            methane_emission +
            nitrous_oxide_emission
        )

        total = calculate_total_emissions(
            scope1,
            scope2,
            scope3,
        )

        # -------------------------
        # Store Results
        # -------------------------

        scope1_results.append(scope1)
        scope2_results.append(scope2)
        scope3_results.append(scope3)
        total_results.append(total)

    # ==========================================================
    # Append New Columns
    # ==========================================================

    dataset["Scope1_Emissions"] = scope1_results
    dataset["Scope2_Emissions"] = scope2_results
    dataset["Scope3_Emissions"] = scope3_results
    dataset["Total_Emissions"] = total_results

    # ==========================================================
    # Export Report
    # ==========================================================

    os.makedirs(
        OUTPUT_DIRECTORY,
        exist_ok=True,
    )

    dataset.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("=" * 70)
    print("Carbonomics-AI")
    print("=" * 70)
    print("Dataset processed successfully.")
    print(f"Records Processed : {len(dataset)}")
    print(f"Report Generated  : {OUTPUT_FILE}")
    print("=" * 70)


def main():
    """
    Run dataset processing.
    """

    process_dataset()


if __name__ == "__main__":
    main()