"""
db_manager.py

Carbonomics-AI PostgreSQL Database Manager (Module 2 & Module 3 Integration)

This module manages connections and operations for PostgreSQL.
If PostgreSQL credentials or dependencies (psycopg2/sqlalchemy) are not available,
it logs a clear status message and skips database insertion gracefully without breaking the pipeline.
"""

import os
import pandas as pd

def get_db_config():
    """
    Retrieve database configuration from environment variables.
    """
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    dbname = os.environ.get("DB_NAME", "carbonomics")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    
    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password
    }

def is_db_available():
    """
    Check if psycopg2 or sqlalchemy is installed and DB password/credentials are configured.
    """
    config = get_db_config()
    if not config["password"]:
        return False, "DB_PASSWORD environment variable not set."
    
    try:
        import psycopg2
        return True, "psycopg2 available"
    except ImportError:
        try:
            import sqlalchemy
            return True, "sqlalchemy available"
        except ImportError:
            return False, "Neither psycopg2 nor sqlalchemy module is installed."

def insert_cleaned_dataset(dataset_path: str) -> dict:
    """
    Insert cleaned dataset CSV into PostgreSQL cleaned_dataset table.
    """
    available, msg = is_db_available()
    if not available:
        print(f"[PostgreSQL Status] SKIPPED - {msg}")
        return {"status": "SKIPPED", "reason": msg, "inserted_rows": 0}
    
    config = get_db_config()
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["dbname"],
            user=config["user"],
            password=config["password"]
        )
        cursor = conn.cursor()
        df = pd.read_csv(dataset_path)
        
        insert_query = """
        INSERT INTO cleaned_dataset (
            electricity_kwh, diesel_litres, petrol_distance_km, diesel_distance_km,
            ev_electricity_kwh, college_bus_distance_km, public_bus_passenger_km,
            motorcycle_passenger_km, auto_passenger_km, bicycle_passenger_km,
            walking_passenger_km, waste_landfill_kg, compost_waste_kg,
            water_consumption_m3, methane_kg, nitrous_oxide_kg
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        records = [tuple(x) for x in df.to_numpy()]
        cursor.executemany(insert_query, records)
        conn.commit()
        inserted_count = len(records)
        cursor.close()
        conn.close()
        
        print(f"[PostgreSQL Status] SUCCESS - Inserted {inserted_count} records into 'cleaned_dataset'.")
        return {"status": "SUCCESS", "reason": None, "inserted_rows": inserted_count}
    except Exception as e:
        print(f"[PostgreSQL Status] FAILED - {str(e)}")
        return {"status": "FAILED", "reason": str(e), "inserted_rows": 0}

def insert_prediction_results(prediction_df: pd.DataFrame) -> dict:
    """
    Insert ML prediction results into PostgreSQL prediction_results table.
    """
    available, msg = is_db_available()
    if not available:
        print(f"[PostgreSQL Status] SKIPPED - {msg}")
        return {"status": "SKIPPED", "reason": msg, "inserted_rows": 0}
    
    config = get_db_config()
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["dbname"],
            user=config["user"],
            password=config["password"]
        )
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO prediction_results (
            actual_emission, predicted_emission, model_name, prediction_error
        ) VALUES (%s, %s, %s, %s)
        """
        
        records = []
        for _, row in prediction_df.iterrows():
            actual = float(row.get("actual_Total_Emissions", 0.0))
            predicted = float(row.get("predicted_Total_Emissions", 0.0))
            model_name = str(row.get("model_used", "Unknown"))
            error = float(row.get("prediction_error", 0.0))
            records.append((actual, predicted, model_name, error))
            
        cursor.executemany(insert_query, records)
        conn.commit()
        inserted_count = len(records)
        cursor.close()
        conn.close()
        
        print(f"[PostgreSQL Status] SUCCESS - Inserted {inserted_count} predictions into 'prediction_results'.")
        return {"status": "SUCCESS", "reason": None, "inserted_rows": inserted_count}
    except Exception as e:
        print(f"[PostgreSQL Status] FAILED - {str(e)}")
        return {"status": "FAILED", "reason": str(e), "inserted_rows": 0}
