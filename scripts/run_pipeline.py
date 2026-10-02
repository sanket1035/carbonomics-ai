"""
run_pipeline.py

Master pipeline for Carbonomics-AI (weekly flow).

1. Build the weekly SYNTHETIC dataset from the REAL monthly totals
2. Validate it (data/processed/weekly_clean.csv)
3. Carbon accounting: emission = activity x factor (outputs/weekly_emissions.csv)
4. Forecast weekly activity (time-based split, naive and mean baselines) and
   derive the weekly emission forecast = predicted activity x factor
5. Plots and QA report
6. PostgreSQL upsert (skipped if credentials are not configured)

Usage (from anywhere):
    python scripts/run_pipeline.py
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(ROOT, "src"))
sys.path.append(os.path.join(ROOT, "scripts"))
os.chdir(ROOT)

import make_synthetic_weekly  # noqa: E402
from clean_data import clean_dataset  # noqa: E402
from database.db_manager import upsert_forecast_results, upsert_weekly_activity  # noqa: E402
from ml.forecast_weekly import emission_forecast, run_weekly_forecast  # noqa: E402
from ml.visualizer import plot_emission_forecast, plot_forecast, plot_metric_comparison  # noqa: E402
from process_dataset import process_dataset  # noqa: E402
from validation.qa_validator import generate_qa_report  # noqa: E402


def run_master_pipeline() -> None:
    print("\n" + "=" * 75)
    print("                    CARBONOMICS-AI PIPELINE (WEEKLY)")
    print("=" * 75)

    print("\n[STEP 1/6] Building weekly SYNTHETIC dataset from real monthly totals...")
    make_synthetic_weekly.main()

    print("\n[STEP 2/6] Validating weekly dataset...")
    clean_dataset()

    print("\n[STEP 3/6] Carbon accounting (activity x factor)...")
    process_dataset()

    print("\n[STEP 4/6] Weekly activity forecast with baselines...")
    metrics_df, preds = run_weekly_forecast()
    for target, pred_df in preds.items():
        plot_forecast(pred_df, target)
    plot_metric_comparison(metrics_df)
    emission_table, emission_metrics = emission_forecast(preds)
    plot_emission_forecast(emission_table)

    print("\n[STEP 5/6] QA report...")
    qa_path = generate_qa_report()

    print("\n[STEP 6/6] PostgreSQL...")
    db_activity = upsert_weekly_activity()
    db_forecast = upsert_forecast_results()

    print("\n" + "=" * 75)
    print("PIPELINE FINISHED")
    print("=" * 75)
    print("[OK] data/synthetic/weekly_synthetic.csv   (SYNTHETIC)")
    print("[OK] data/processed/weekly_clean.csv")
    print("[OK] outputs/weekly_emissions.csv")
    print("[OK] outputs/forecast/ (activity + emission forecasts), outputs/plots/, outputs/models/")
    print(f"[OK] {qa_path}")
    print(f"[..] PostgreSQL: weekly_activity [{db_activity['status']}] | forecast_results [{db_forecast['status']}]")
    print("-" * 75)
    print(metrics_df.round(3).to_string(index=False))
    print("Weekly emission forecast (Scope 1 + 2, kg CO2e, activity x factor):")
    print(emission_metrics.round(1).to_string(index=False))
    print("Scores are on SYNTHETIC data and show the pipeline works, not real accuracy.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_master_pipeline()
