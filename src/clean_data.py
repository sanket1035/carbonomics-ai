"""
clean_data.py

Carbonomics-AI Dataset Cleaning & Validation Module

This module:
1. Loads the raw institutional dataset.
2. Validates dataset structure and quality.
3. Checks for missing values, duplicates, negative values,
   required columns, and numeric data types.
4. Exports a validated dataset as cleaned_dataset.csv.
"""

import os
from typing import List

import pandas as pd

from data_loader import load_dataset


# ==========================================================
# Configuration
# ==========================================================

INPUT_FILE = "data/raw/carbonomics_institutional_dataset.csv"

OUTPUT_DIRECTORY = "data/processed"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIRECTORY,
    "cleaned_dataset.csv",
)

REQUIRED_COLUMNS = [
    "electricity_kwh",
    "diesel_litres",
    "petrol_distance_km",
    "diesel_distance_km",
    "ev_electricity_kwh",
    "college_bus_distance_km",
    "public_bus_passenger_km",
    "motorcycle_passenger_km",
    "auto_passenger_km",
    "bicycle_passenger_km",
    "walking_passenger_km",
    "waste_landfill_kg",
    "compost_waste_kg",
    "water_consumption_m3",
    "methane_kg",
    "nitrous_oxide_kg",
]


# ==========================================================
# Validation Functions
# ==========================================================

def validate_required_columns(
    dataset: pd.DataFrame,
    required_columns: List[str],
) -> None:
    """
    Ensure all required columns exist.
    """

    missing_columns = [
        column
        for column in required_columns
        if column not in dataset.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )


def validate_missing_values(
    dataset: pd.DataFrame,
) -> None:
    """
    Check for missing values.
    """

    missing = dataset.isnull().sum()

    if missing.any():
        raise ValueError(
            f"Dataset contains missing values:\n{missing}"
        )


def remove_duplicates(
    dataset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove duplicate records.
    """

    before = len(dataset)

    dataset = dataset.drop_duplicates()

    removed = before - len(dataset)

    print(f"Duplicate Records Removed : {removed}")

    return dataset


def validate_numeric_columns(
    dataset: pd.DataFrame,
) -> None:
    """
    Ensure all required columns are numeric.
    """

    non_numeric = []

    for column in REQUIRED_COLUMNS:

        if not pd.api.types.is_numeric_dtype(
            dataset[column]
        ):
            non_numeric.append(column)

    if non_numeric:
        raise TypeError(
            f"Required numeric columns found as non-numeric: {non_numeric}"
        )


def validate_negative_values(
    dataset: pd.DataFrame,
) -> None:
    """
    Ensure required numeric columns do not
    contain negative values.
    """

    negative_columns = []

    for column in REQUIRED_COLUMNS:

        if (dataset[column] < 0).any():
            negative_columns.append(column)

    if negative_columns:
        raise ValueError(
            f"Negative values detected in: {negative_columns}"
        )

# ==========================================================
# Cleaning Pipeline
# ==========================================================

def clean_dataset() -> None:
    """
    Validate and prepare the institutional dataset.
    """

    print("=" * 70)
    print("Carbonomics-AI")
    print("Module 2 - Dataset Validation Pipeline")
    print("=" * 70)

    dataset = load_dataset(INPUT_FILE)

    print(f"Rows Loaded      : {len(dataset)}")
    print(f"Columns Loaded   : {len(dataset.columns)}")

    validate_required_columns(
        dataset,
        REQUIRED_COLUMNS,
    )

    validate_missing_values(
        dataset,
    )

    validate_numeric_columns(
        dataset,
    )

    validate_negative_values(
        dataset,
    )

    dataset = remove_duplicates(
        dataset,
    )

    # ==========================================================
    # Standardize Column Names
    # ==========================================================

    dataset.columns = (
        dataset.columns
        .str.strip()
        .str.lower()
    )

    # ==========================================================
    # Export Clean Dataset
    # ==========================================================

    os.makedirs(
        OUTPUT_DIRECTORY,
        exist_ok=True,
    )

    dataset.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("-" * 70)
    print("Validation Summary")
    print("-" * 70)
    print("✓ Required Columns : PASS")
    print("✓ Missing Values   : PASS")
    print("✓ Numeric Data     : PASS")
    print("✓ Negative Values  : PASS")
    print("✓ Duplicates       : PASS")
    print("-" * 70)

    print(f"Rows Exported      : {len(dataset)}")
    print(f"Output File        : {OUTPUT_FILE}")

    print("=" * 70)
    print("Module 2 Validation Completed Successfully")
    print("=" * 70)


# ==========================================================
# Main
# ==========================================================

def main() -> None:
    """
    Entry point.
    """

    clean_dataset()


if __name__ == "__main__":
    main()