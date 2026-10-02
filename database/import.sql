-- ==========================================================
-- Carbonomics-AI
-- Manual import of the validated weekly dataset (pgAdmin / psql).
-- scope*_kg and total_kg stay NULL here; scripts/run_pipeline.py fills them.
-- Replace ABSOLUTE_PATH_TO_PROJECT first.
-- ==========================================================

COPY weekly_activity (
    week_index,
    week_start,
    electricity_kwh,
    diesel_litres,
    is_synthetic
)
FROM 'ABSOLUTE_PATH_TO_PROJECT/data/processed/weekly_clean.csv'
WITH (
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    ENCODING 'UTF8'
);
