-- Carbonomics-AI
-- PostgreSQL Database Schema
-- Module 2: Dataset Integration

CREATE TABLE IF NOT EXISTS cleaned_dataset (
    electricity_kwh DOUBLE PRECISION,
    generator_diesel_l DOUBLE PRECISION,
    water_consumption_kl DOUBLE PRECISION,
    waste_generated_kg DOUBLE PRECISION,
    college_bus_distance_km DOUBLE PRECISION,
    sewage_generated_kl DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION,
    holiday VARCHAR(10)
);