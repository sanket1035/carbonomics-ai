# Carbonomics-AI Database Setup

This folder contains the PostgreSQL database setup files for Module 2 of the Carbonomics-AI project.

## Database Details

- Database: `carbonomics_db`
- PostgreSQL Version: 18
- Database Tool: pgAdmin 4
- Table: `cleaned_dataset`
- Dataset: `data/processed/cleaned_dataset.csv`
- Total Records: 365

## Files

- `schema.sql` - Creates the required `cleaned_dataset` table.
- `import.sql` - Imports the cleaned dataset into PostgreSQL.
- `screenshots/` - Contains screenshots showing database setup and SQL verification.

## Setup

### 1. Create Database

Create a PostgreSQL database named:

`carbonomics_db`

### 2. Create Table

Connect to `carbonomics_db` and execute:

`database/schema.sql`

This creates the `cleaned_dataset` table.

### 3. Import Dataset

The cleaned dataset is available at:

`data/processed/cleaned_dataset.csv`

Before executing `database/import.sql`, replace:

`ABSOLUTE_PATH_TO_PROJECT`

with the actual location of the cloned Carbonomics-AI project on your computer.

Then execute `import.sql`.

Alternatively, the CSV file can be imported using the pgAdmin Import/Export Data option.

Use:

- Format: CSV
- Header: Yes
- Delimiter: `,`
- Encoding: UTF-8

## Verify Data

Run:

```sql
SELECT COUNT(*) AS total_rows
FROM cleaned_dataset;




```sql
SELECT COUNT(*) AS total_rows
FROM cleaned_dataset;
```

Expected result:

`365`

To verify sample records:

```sql
SELECT *
FROM cleaned_dataset
LIMIT 10;
```

## Status

PostgreSQL integration completed successfully. The cleaned dataset was imported and all 365 records were verified using SQL.