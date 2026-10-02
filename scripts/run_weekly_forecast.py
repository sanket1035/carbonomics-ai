"""
run_weekly_forecast.py

Generate the synthetic weekly dataset (if missing) and run the weekly activity
forecast with baselines.

Usage (from repo root):
    python scripts/run_weekly_forecast.py
"""

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(ROOT, "src"))
os.chdir(ROOT)

from ml.forecast_weekly import INPUT_FILE, run_weekly_forecast  # noqa: E402


def main() -> None:
    if not os.path.exists(INPUT_FILE):
        subprocess.check_call([sys.executable, "scripts/make_synthetic_weekly.py"])
    metrics_df, _ = run_weekly_forecast()
    print("\nWeekly forecast metrics (time-based 80/20 split, SYNTHETIC data):")
    print(metrics_df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
