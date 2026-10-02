# Carbonomics-AI Database

PostgreSQL storage for the weekly activity data, emissions and forecast results.

## Tables (`schema.sql`, safe to run repeatedly)
- `weekly_activity`: one row per week (`week_start` is the key): electricity_kwh, diesel_litres,
  `is_synthetic`, scope1_kg, scope2_kg, total_kg.
- `forecast_results`: one row per week x target x model (key on all three): actual, predicted, abs_error.

## Setup
1. Create a database (default name `carbonomics_db`).
2. Set the variables from `.env.example`: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.
3. `pip install -r requirements.txt` (includes psycopg2-binary).
4. `python scripts/run_pipeline.py`. The last step creates the tables if needed and upserts the
   rows, so running it again does not duplicate anything. Without DB_PASSWORD the step is skipped
   with a message.
5. `python scripts/verify_db.py` prints row counts and sample rows.

Manual alternative: run `schema.sql`, then `import.sql` (replace `ABSOLUTE_PATH_TO_PROJECT`) or use
pgAdmin Import/Export on `data/processed/weekly_clean.csv`. This fills activity only; the scope
columns are filled by the pipeline.

## Status
Tested on a local PostgreSQL 16: 52 `weekly_activity` rows and 80 `forecast_results` rows, the same
counts after a second run. Not tested against pgAdmin or a hosted database.
