"""
verify_db.py

Check the PostgreSQL setup: connection, row counts and a few forecast rows.

Usage: python scripts/verify_db.py   (needs DB_* env vars, see .env.example)
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from database.db_manager import get_db_config, is_db_available  # noqa: E402


def verify_postgresql_setup() -> bool:
    print("=" * 60)
    print("        Carbonomics-AI PostgreSQL Verification")
    print("=" * 60)

    available, reason = is_db_available()
    if not available:
        print("Status: SKIPPED / UNAVAILABLE")
        print(f"Reason: {reason}")
        print("Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD (see .env.example).")
        return False

    config = get_db_config()
    print(f"Connecting to '{config['dbname']}' on {config['host']}:{config['port']} as '{config['user']}'...")
    try:
        import psycopg2

        conn = psycopg2.connect(**{k: config[k] for k in ("host", "port", "dbname", "user", "password")})
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM weekly_activity;")
        weekly = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM forecast_results;")
        forecasts = cur.fetchone()[0]
        cur.execute("SELECT week_start, target, model_name, actual, predicted, abs_error "
                    "FROM forecast_results ORDER BY week_start LIMIT 5;")
        samples = cur.fetchall()

        print(f"[OK] weekly_activity rows  : {weekly}")
        print(f"[OK] forecast_results rows : {forecasts}")
        for s in samples:
            print("   ", s)
        cur.close()
        conn.close()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"PostgreSQL Connection Error: {e}")
        return False


if __name__ == "__main__":
    verify_postgresql_setup()
