# Weekly synthetic dataset and activity forecast

## Why
The Energy team provides no daily data and no multi-year history. The only real
activity data is 12 monthly totals for 2025 (`data/real/real_monthly_2025.csv`,
copied from the KKWIEER Master Data workbook, sheets 2 and 3). That is too few
points to train or validate a forecaster.

## What is real and what is invented
| Item | Status |
| :--- | :--- |
| Monthly electricity (kWh) and DG diesel (L) | REAL (Energy team) |
| Emission factors (`src/emission_factors.py`) | REAL, with source/version/unit; `verified=False` entries are not yet confirmed |
| Day-to-day shape inside a month (weekend ratio, noise) | INVENTED assumptions, listed in `scripts/make_synthetic_weekly.py` |
| `data/synthetic/weekly_synthetic.csv` | SYNTHETIC (`is_synthetic=True`), 52 weeks from 2025-01-01; 31 Dec left out |

Each calendar month of the underlying daily series sums exactly to the real
monthly total (asserted in the script and in `tests/`).

## Run
```
python scripts/make_synthetic_weekly.py
python scripts/run_weekly_forecast.py
pytest tests
```

## Forecast design
- Targets: weekly `electricity_kwh` and `diesel_litres` (activity, not emission).
- Emission = predicted activity x factor from `emission_factors.py`.
- Features: lag 1/2/4 weeks, 4-week rolling mean (all past-only), month, ISO week.
- Time-based split: first 80% of weeks train, last 20% test, no shuffling.
- Metrics MAE, RMSE, R2 next to baselines `naive_last_week` and `train_mean`.

## How to read the scores
The within-month pattern is set by the generator, so a model can only learn that
pattern plus the real monthly seasonality. Scores show the pipeline works; they
are not evidence of real forecasting accuracy. With about 38 training weeks the
tree models do not reliably beat the naive baseline; that is reported as is.
Replace `data/synthetic/weekly_synthetic.csv` with real weekly data when it
exists and rerun.

## Not touched in this change
`src/ml/ml_pipeline.py` still predicts `Total_Emissions` from its own activity
columns (target leakage) on the old `data/raw` dataset, whose scale does not
match the real campus data. Committed files under `outputs/` (except
`outputs/forecast/`) were produced by that old pipeline with the old factors.
