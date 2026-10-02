"""
db_manager.py

Carbonomics-AI PostgreSQL manager.

Writes the weekly activity/emissions (weekly_activity) and the forecast test
results (forecast_results). Inserts are upserts on the primary key, so running
the pipeline again does not create duplicate rows. Tables are created from
database/schema.sql if missing.

If DB_PASSWORD is not set or psycopg2 is missing, the step is SKIPPED with a
clear message and the pipeline continues.

Environment variables: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
(see .env.example).
"""

import glob
import os

import pandas as pd

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "database", "schema.sql")


def get_db_config() -> dict:
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "dbname": os.environ.get("DB_NAME", "carbonomics_db"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
    }


def is_db_available():
    if not get_db_config()["password"]:
        return False, "DB_PASSWORD environment variable not set."
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        return False, "psycopg2 is not installed (pip install psycopg2-binary)."
    return True, "psycopg2 available"


def _connect():
    import psycopg2

    c = get_db_config()
    conn = psycopg2.connect(host=c["host"], port=c["port"], dbname=c["dbname"],
                            user=c["user"], password=c["password"])
    with conn.cursor() as cur, open(SCHEMA_FILE, encoding="utf-8") as f:
        cur.execute(f.read())
    conn.commit()
    return conn


def _run(label: str, writer) -> dict:
    available, msg = is_db_available()
    if not available:
        print(f"[PostgreSQL Status] SKIPPED - {msg}")
        return {"status": "SKIPPED", "reason": msg, "inserted_rows": 0}
    try:
        conn = _connect()
        try:
            count = writer(conn)
            conn.commit()
        finally:
            conn.close()
        print(f"[PostgreSQL Status] SUCCESS - Upserted {count} rows into '{label}'.")
        return {"status": "SUCCESS", "reason": None, "inserted_rows": count}
    except Exception as e:  # noqa: BLE001
        print(f"[PostgreSQL Status] FAILED - {e}")
        return {"status": "FAILED", "reason": str(e), "inserted_rows": 0}


def upsert_weekly_activity(emissions_path: str = "outputs/weekly_emissions.csv") -> dict:
    def writer(conn):
        df = pd.read_csv(emissions_path)
        sql = """
        INSERT INTO weekly_activity
            (week_start, week_index, electricity_kwh, diesel_litres, is_synthetic,
             scope1_kg, scope2_kg, total_kg)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (week_start) DO UPDATE SET
            week_index = EXCLUDED.week_index,
            electricity_kwh = EXCLUDED.electricity_kwh,
            diesel_litres = EXCLUDED.diesel_litres,
            is_synthetic = EXCLUDED.is_synthetic,
            scope1_kg = EXCLUDED.scope1_kg,
            scope2_kg = EXCLUDED.scope2_kg,
            total_kg = EXCLUDED.total_kg
        """
        rows = [
            (r.week_start, int(r.week_index), float(r.electricity_kwh), float(r.diesel_litres),
             bool(r.is_synthetic), float(r.scope1_kg), float(r.scope2_kg), float(r.total_kg))
            for r in df.itertuples()
        ]
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        return len(rows)

    return _run("weekly_activity", writer)


def upsert_forecast_results(pred_dir: str = "outputs/forecast") -> dict:
    def writer(conn):
        sql = """
        INSERT INTO forecast_results (week_start, target, model_name, actual, predicted, abs_error)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (week_start, target, model_name) DO UPDATE SET
            actual = EXCLUDED.actual,
            predicted = EXCLUDED.predicted,
            abs_error = EXCLUDED.abs_error,
            created_at = CURRENT_TIMESTAMP
        """
        rows = []
        for path in glob.glob(os.path.join(pred_dir, "weekly_predictions_*.csv")):
            df = pd.read_csv(path)
            target = os.path.basename(path)[len("weekly_predictions_"):-len(".csv")]
            for model_col in [c for c in df.columns if c.startswith("pred_")]:
                model = model_col[len("pred_"):]
                for _, r in df.iterrows():
                    actual, pred = float(r[f"actual_{target}"]), float(r[model_col])
                    rows.append((r["week_start"], target, model, actual, pred, abs(actual - pred)))
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        return len(rows)

    return _run("forecast_results", writer)
