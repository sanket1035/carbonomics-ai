"""
process_dataset.py

Carbonomics-AI weekly carbon accounting.

Emission = activity x emission factor (src/emission_factors.py), via calculations.py.

Sources covered (the only ones with real or calibrated weekly activity data):
    diesel_litres   -> stationary diesel generator, Scope 1
    electricity_kwh -> purchased grid electricity, Scope 2
Scope 3 and the other Scope 1 sources (college bus, refrigerant) have no weekly
activity data, so they are NOT included and no values are invented for them.
"""

import os

import pandas as pd

from calculations import (
    calculate_diesel_emissions,
    calculate_electricity_emissions,
    calculate_total_emissions,
)
from data_loader import load_dataset

INPUT_FILE = "data/processed/weekly_clean.csv"
OUTPUT_DIRECTORY = "outputs"
OUTPUT_FILE = os.path.join(OUTPUT_DIRECTORY, "weekly_emissions.csv")


def process_dataset(input_file: str = INPUT_FILE, output_file: str = OUTPUT_FILE) -> pd.DataFrame:
    dataset = load_dataset(input_file)

    dataset["diesel_emission_kg"] = dataset["diesel_litres"].apply(calculate_diesel_emissions)
    dataset["electricity_emission_kg"] = dataset["electricity_kwh"].apply(calculate_electricity_emissions)

    dataset["scope1_kg"] = dataset["diesel_emission_kg"]
    dataset["scope2_kg"] = dataset["electricity_emission_kg"]
    dataset["scope3_kg"] = 0.0  # not measured; excluded, see module docstring
    dataset["total_kg"] = [
        calculate_total_emissions(s1, s2, s3)
        for s1, s2, s3 in zip(dataset["scope1_kg"], dataset["scope2_kg"], dataset["scope3_kg"])
    ]

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    dataset.to_csv(output_file, index=False)

    print("=" * 70)
    print("Carbonomics-AI - weekly carbon accounting")
    print(f"Records Processed : {len(dataset)}")
    print("Scope coverage    : Scope 1 (generator diesel) + Scope 2 (electricity); Scope 3 not measured")
    print(f"Report Generated  : {output_file}")
    print("=" * 70)
    return dataset


if __name__ == "__main__":
    process_dataset()
