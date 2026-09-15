"""
run_pipeline.py

Master Executable Pipeline for Carbonomics-AI

Executes end-to-end:
1. Data Pipeline: Auditing, Cleaning & Validation (Module 2)
2. Carbon Accounting: GHG Emission Calculations & Scope Aggregation (Module 1)
3. Machine Learning: Preprocessing, Feature Selection (No Leakage), Training (RF & XGBoost),
   Evaluation, Model Selection, Prediction & Plot Generation (Module 3)
4. Quality Assurance: Edge case testing, dataset QA, formula verification & QA Report generation
5. Database Integration: PostgreSQL storage (if credentials configured, else graceful skip)

Usage:
    python scripts/run_pipeline.py
"""

import sys
import os

# Add src to python path for seamless imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from clean_data import clean_dataset
from process_dataset import process_dataset
from ml.ml_pipeline import run_ml_pipeline
from validation.qa_validator import generate_qa_report
from database.db_manager import insert_cleaned_dataset, insert_prediction_results

def run_master_pipeline():
    print("\n" + "=" * 75)
    print("                      CARBONOMICS-AI PIPELINE EXECUTION")
    print("           AI-Driven Carbon Intelligence & Decision Support")
    print("=" * 75)
    
    # ---------------------------------------------------------
    # STEP 1: Data Pipeline (Module 2)
    # ---------------------------------------------------------
    print("\n[STEP 1/5] Executing Data Pipeline (Data Cleaning & Auditing)...")
    clean_dataset()
    
    # ---------------------------------------------------------
    # STEP 2: Carbon Accounting (Module 1)
    # ---------------------------------------------------------
    print("\n[STEP 2/5] Executing Carbon Accounting Calculations...")
    process_dataset()
    
    # ---------------------------------------------------------
    # STEP 3: Machine Learning Pipeline (Module 3)
    # ---------------------------------------------------------
    print("\n[STEP 3/5] Executing Machine Learning Training & Predictions...")
    ml_results = run_ml_pipeline()
    
    # ---------------------------------------------------------
    # STEP 4: Quality Assurance & Validation (Purva)
    # ---------------------------------------------------------
    print("\n[STEP 4/5] Executing Quality Assurance & Edge Case Validation...")
    qa_path = generate_qa_report()
    
    # ---------------------------------------------------------
    # STEP 5: Database Integration (Rahil - Optional PostgreSQL)
    # ---------------------------------------------------------
    print("\n[STEP 5/5] Attempting PostgreSQL Database Integration...")
    db_clean_res = insert_cleaned_dataset("data/processed/cleaned_dataset.csv")
    db_pred_res = insert_prediction_results(ml_results["pred_df"])
    
    # ---------------------------------------------------------
    # Final Pipeline Execution Summary
    # ---------------------------------------------------------
    print("\n" + "=" * 75)
    print("                PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print("=" * 75)
    print(f"[OK] Cleaned Dataset File   : data/processed/cleaned_dataset.csv")
    print(f"[OK] Carbon Report File    : outputs/carbon_report.csv")
    print(f"[OK] Trained RF Model      : outputs/random_forest.pkl")
    print(f"[OK] Trained XGBoost Model : outputs/xgboost.pkl")
    print(f"[OK] Model Metrics CSV     : outputs/model_metrics.csv")
    print(f"[OK] Prediction Report CSV : outputs/prediction_report.csv")
    print(f"[OK] Visualization Plots   : outputs/plots/ (actual_vs_predicted.png, model_comparison.png, feature_importance.png)")
    print(f"[OK] QA Validation Report  : {qa_path}")
    print(f"[OK] PostgreSQL DB Status  : Cleaned Dataset [{db_clean_res['status']}] | Predictions [{db_pred_res['status']}]")
    print("-" * 75)
    print(f"Selected ML Model       : {ml_results['best_model_name']}")
    print("Model Evaluation Metrics:")
    print(ml_results['metrics_df'].to_string(index=False))
    print("=" * 75 + "\n")

if __name__ == "__main__":
    run_master_pipeline()
