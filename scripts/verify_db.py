"""
verify_db.py

Carbonomics-AI PostgreSQL Database Verification Script (Rahil - PostgreSQL)

Confirms:
1. PostgreSQL connection & credential setup
2. Records inserted in cleaned_dataset table
3. Records inserted in prediction_results table
4. Sample prediction records query
"""

import sys
import os

# Ensure src path is available
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database.db_manager import is_db_available, get_db_config

def verify_postgresql_setup():
    print("=" * 60)
    print("        Carbonomics-AI PostgreSQL Verification")
    print("=" * 60)
    
    available, reason = is_db_available()
    if not available:
        print(f"Status: SKIPPED / UNAVAILABLE")
        print(f"Reason: {reason}")
        print("Note: PostgreSQL database integration is optional and configured via environment variables.")
        print("      Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD to enable DB features.")
        print("=" * 60)
        return False
        
    config = get_db_config()
    print(f"Connecting to database '{config['dbname']}' on {config['host']}:{config['port']} as user '{config['user']}'...")
    
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
        
        # Check cleaned_dataset row count
        cursor.execute("SELECT COUNT(*) FROM cleaned_dataset;")
        cleaned_count = cursor.fetchone()[0]
        
        # Check prediction_results row count
        cursor.execute("SELECT COUNT(*) FROM prediction_results;")
        pred_count = cursor.fetchone()[0]
        
        # Sample predictions
        cursor.execute("SELECT prediction_id, actual_emission, predicted_emission, model_name, prediction_error FROM prediction_results LIMIT 5;")
        samples = cursor.fetchall()
        
        print("\n[VERIFICATION RESULTS]")
        print(f"[OK] Table 'cleaned_dataset' Row Count  : {cleaned_count}")
        print(f"[OK] Table 'prediction_results' Row Count: {pred_count}")
        print("\nSample Records from 'prediction_results':")
        print("-" * 65)
        print(f"{'ID':<6} | {'Actual (kg)':<12} | {'Predicted (kg)':<14} | {'Model':<14} | {'Error':<8}")
        print("-" * 65)
        for s in samples:
            print(f"{s[0]:<6} | {s[1]:<12.2f} | {s[2]:<14.2f} | {s[3]:<14} | {s[4]:<8.2f}")
        print("-" * 65)
        
        cursor.close()
        conn.close()
        print("\nPostgreSQL Database Verification Successful!")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"PostgreSQL Connection Error: {str(e)}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    verify_postgresql_setup()
