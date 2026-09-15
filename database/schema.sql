-- ==========================================================
-- Carbonomics-AI
-- PostgreSQL Database Schema
-- Module 2: Dataset Integration
-- ==========================================================

CREATE TABLE IF NOT EXISTS cleaned_dataset (
    electricity_kwh DOUBLE PRECISION,
    diesel_litres DOUBLE PRECISION,
    petrol_distance_km DOUBLE PRECISION,
    diesel_distance_km DOUBLE PRECISION,
    ev_electricity_kwh DOUBLE PRECISION,
    college_bus_distance_km DOUBLE PRECISION,
    public_bus_passenger_km DOUBLE PRECISION,
    motorcycle_passenger_km DOUBLE PRECISION,
    auto_passenger_km DOUBLE PRECISION,
    bicycle_passenger_km DOUBLE PRECISION,
    walking_passenger_km DOUBLE PRECISION,
    waste_landfill_kg DOUBLE PRECISION,
    compost_waste_kg DOUBLE PRECISION,
    water_consumption_m3 DOUBLE PRECISION,
    methane_kg DOUBLE PRECISION,
    nitrous_oxide_kg DOUBLE PRECISION
);

-- Table for ML Prediction Results
CREATE TABLE IF NOT EXISTS prediction_results (
    prediction_id SERIAL PRIMARY KEY,
    actual_emission DOUBLE PRECISION,
    predicted_emission DOUBLE PRECISION,
    model_name VARCHAR(50),
    prediction_error DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);