"""
process_dataset.py

Carbonomics-AI Dataset Processing Module

This module:
1. Loads the institutional dataset.
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
    calculate_waste_emissions,
    calculate_methane_emissions,
    calculate_nitrous_oxide_emissions,
    calculate_total_emissions,
)

INPUT_FILE = "data/processed/cleaned_dataset.csv"
OUTPUT_DIRECTORY = "outputs"
OUTPUT_FILE = os.path.join(OUTPUT_DIRECTORY, "carbon_report.csv")


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

        electricity = row["Electricity_kWh"]
        diesel = row["Generator_Diesel_L"]
        college_bus = row["College_Bus_Distance_km"]
        waste = row["Waste_Generated_kg"]

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

        waste_emission = calculate_waste_emissions(
            waste
        )

        # ----------------------------------------------------
        # Future Modules (Dataset currently does not contain
        # these columns. Keep as placeholders.)
        # ----------------------------------------------------

        petrol_emission = 0.0
        diesel_transport_emission = 0.0
        ev_emission = 0.0
        public_bus_emission = 0.0
        methane_emission = 0.0
        nitrous_oxide_emission = 0.0

        # -------------------------
        # Scope Calculations
        # -------------------------

        scope1 = (
            diesel_emission +
            college_bus_emission
        )

        scope2 = electricity_emission

        scope3 = (
            waste_emission +
            petrol_emission +
            diesel_transport_emission +
            ev_emission +
            public_bus_emission +
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

    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

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
    """Run dataset processing."""
    process_dataset()


if __name__ == "__main__":
    main()