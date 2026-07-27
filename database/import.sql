-- ==========================================================
-- Carbonomics-AI
-- Dataset Import Script
-- Module 2
-- ==========================================================

COPY cleaned_dataset (
    electricity_kwh,
    diesel_litres,
    petrol_distance_km,
    diesel_distance_km,
    ev_electricity_kwh,
    college_bus_distance_km,
    public_bus_passenger_km,
    motorcycle_passenger_km,
    auto_passenger_km,
    bicycle_passenger_km,
    walking_passenger_km,
    waste_landfill_kg,
    compost_waste_kg,
    water_consumption_m3,
    methane_kg,
    nitrous_oxide_kg
)

FROM 'ABSOLUTE_PATH_TO_PROJECT/data/processed/cleaned_dataset.csv'

WITH (
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    ENCODING 'UTF8'
);