-- ==========================================================
-- Carbonomics-AI
-- PostgreSQL schema (weekly activity, emissions, forecasts)
-- Safe to run repeatedly.
-- ==========================================================

-- Weekly activity data. is_synthetic marks calibrated synthetic rows.
CREATE TABLE IF NOT EXISTS weekly_activity (
    week_start      DATE PRIMARY KEY,
    week_index      INTEGER,
    electricity_kwh DOUBLE PRECISION NOT NULL,
    diesel_litres   DOUBLE PRECISION NOT NULL,
    is_synthetic    BOOLEAN NOT NULL DEFAULT TRUE,
    scope1_kg       DOUBLE PRECISION,   -- generator diesel x factor
    scope2_kg       DOUBLE PRECISION,   -- electricity x factor
    total_kg        DOUBLE PRECISION
);

-- Forecast results on the test weeks, one row per week x target x model.
CREATE TABLE IF NOT EXISTS forecast_results (
    week_start      DATE NOT NULL,
    target          VARCHAR(30) NOT NULL,
    model_name      VARCHAR(50) NOT NULL,
    actual          DOUBLE PRECISION,
    predicted       DOUBLE PRECISION,
    abs_error       DOUBLE PRECISION,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (week_start, target, model_name)
);
