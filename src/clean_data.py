"""
clean_data.py

Carbonomics-AI weekly dataset validation module.

Loads the weekly activity dataset, checks structure and quality, and exports a
validated copy to data/processed/weekly_clean.csv.

Checks: required columns, missing values, numeric types, negative values,
duplicate rows, strictly increasing weekly dates (7-day steps).
Nothing is imputed or invented: a failed check raises an error.
"""

import os
from typing import List

import pandas as pd

from data_loader import load_dataset

INPUT_FILE = "data/synthetic/weekly_synthetic.csv"
OUTPUT_DIRECTORY = "data/processed"
OUTPUT_FILE = os.path.join(OUTPUT_DIRECTORY, "weekly_clean.csv")

DATE_COLUMN = "week_start"
ACTIVITY_COLUMNS = ["electricity_kwh", "diesel_litres"]
REQUIRED_COLUMNS = [DATE_COLUMN] + ACTIVITY_COLUMNS


def validate_required_columns(dataset: pd.DataFrame, required_columns: List[str]) -> None:
    missing = [c for c in required_columns if c not in dataset.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_missing_values(dataset: pd.DataFrame) -> None:
    missing = dataset[REQUIRED_COLUMNS].isnull().sum()
    if missing.any():
        raise ValueError(f"Dataset contains missing values:\n{missing}")


def validate_numeric_columns(dataset: pd.DataFrame) -> None:
    non_numeric = [c for c in ACTIVITY_COLUMNS if not pd.api.types.is_numeric_dtype(dataset[c])]
    if non_numeric:
        raise TypeError(f"Required numeric columns found as non-numeric: {non_numeric}")


def validate_negative_values(dataset: pd.DataFrame) -> None:
    negative = [c for c in ACTIVITY_COLUMNS if (dataset[c] < 0).any()]
    if negative:
        raise ValueError(f"Negative values detected in: {negative}")


def validate_weekly_dates(dataset: pd.DataFrame) -> pd.DataFrame:
    """Parse week_start and require strictly increasing 7-day steps."""
    dataset = dataset.copy()
    dataset[DATE_COLUMN] = pd.to_datetime(dataset[DATE_COLUMN])
    steps = dataset[DATE_COLUMN].diff().dropna()
    if not (steps == pd.Timedelta(days=7)).all():
        raise ValueError("week_start must increase in exact 7-day steps with no gaps or repeats.")
    return dataset


def remove_duplicates(dataset: pd.DataFrame) -> pd.DataFrame:
    before = len(dataset)
    dataset = dataset.drop_duplicates()
    print(f"Duplicate Records Removed : {before - len(dataset)}")
    return dataset


def clean_dataset(input_file: str = INPUT_FILE, output_file: str = OUTPUT_FILE) -> pd.DataFrame:
    print("=" * 70)
    print("Carbonomics-AI - Weekly Dataset Validation")
    print("=" * 70)

    dataset = load_dataset(input_file)
    print(f"Rows Loaded      : {len(dataset)}")
    print(f"Columns Loaded   : {len(dataset.columns)}")
    if "is_synthetic" in dataset.columns and dataset["is_synthetic"].all():
        print("Data Label       : SYNTHETIC (calibrated to real monthly totals)")

    dataset.columns = dataset.columns.str.strip().str.lower()
    validate_required_columns(dataset, REQUIRED_COLUMNS)
    validate_missing_values(dataset)
    validate_numeric_columns(dataset)
    validate_negative_values(dataset)
    dataset = remove_duplicates(dataset)
    dataset = validate_weekly_dates(dataset)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    dataset.to_csv(output_file, index=False)

    print("-" * 70)
    print("[OK] Required Columns / Missing / Numeric / Negative / Duplicates / Weekly dates : PASS")
    print(f"Rows Exported      : {len(dataset)}")
    print(f"Output File        : {output_file}")
    print("=" * 70)
    return dataset


if __name__ == "__main__":
    clean_dataset()
