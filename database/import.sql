-- Carbonomics-AI
-- Dataset Import Script
-- Dataset source: data/processed/cleaned_dataset.csv

COPY cleaned_dataset (
    electricity_kwh,
    generator_diesel_l,
    water_consumption_kl,
    waste_generated_kg,
    college_bus_distance_km,
    sewage_generated_kl,
    temperature_c,
    holiday
)
FROM 'ABSOLUTE_PATH_TO_PROJECT/data/processed/cleaned_dataset.csv'
WITH (
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ','
);