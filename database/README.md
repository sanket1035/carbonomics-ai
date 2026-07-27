# Carbonomics-AI Database Setup

This folder contains the PostgreSQL database setup files for Module 2 of the Carbonomics-AI project.

## Database Details

- **Database:** `carbonomics_db`
- **PostgreSQL Version:** 18
- **Database Tool:** pgAdmin 4
- **Table:** `cleaned_dataset`
- **Dataset:** `data/processed/cleaned_dataset.csv`
- **Total Records:** 365
- **Dataset Features:** 16

## Dataset Features

- electricity_kwh
- diesel_litres
- petrol_distance_km
- diesel_distance_km
- ev_electricity_kwh
- college_bus_distance_km
- public_bus_passenger_km
- motorcycle_passenger_km
- auto_passenger_km
- bicycle_passenger_km
- walking_passenger_km
- waste_landfill_kg
- compost_waste_kg
- water_consumption_m3
- methane_kg
- nitrous_oxide_kg

## Files

- `schema.sql` - Creates the `cleaned_dataset` table.
- `import.sql` - Imports the cleaned dataset into PostgreSQL.
- `screenshots/` - Database setup and SQL verification screenshots.

## Setup

### 1. Create Database

Create a PostgreSQL database named:

```text
carbonomics_db
```

### 2. Create Table

Connect to `carbonomics_db` and execute:

```text
database/schema.sql
```

### 3. Import Dataset

The cleaned dataset is available at:

```text
data/processed/cleaned_dataset.csv
```

Before executing `database/import.sql`, replace:

```text
ABSOLUTE_PATH_TO_PROJECT
```

with the absolute path of your local Carbonomics-AI project.

Alternatively, use **pgAdmin → Import/Export Data** with the following settings:

- Format: CSV
- Header: Yes
- Delimiter: `,`
- Encoding: UTF-8

## Verify Data

Verify the total number of records:

```sql
SELECT COUNT(*) AS total_rows
FROM cleaned_dataset;
```

**Expected Output**

```text
365
```

View sample records:

```sql
SELECT *
FROM cleaned_dataset
LIMIT 10;
```

## Status

✅ PostgreSQL integration completed successfully.

- Database created
- Table schema configured
- Cleaned dataset imported
- 365 records verified
- Ready for Module 3 (Machine Learning)