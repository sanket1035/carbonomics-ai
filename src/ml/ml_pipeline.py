"""
ml_pipeline.py

Carbonomics-AI Machine Learning Pipeline (Module 3)

This module implements the complete end-to-end Machine Learning pipeline:
1. Data Preprocessing & Validation
2. Feature Selection (STRICT DATA LEAKAGE PREVENTION: Excludes Scope1, Scope2, Scope3 emissions)
3. Train/Test Split
4. Model Training: Random Forest Regressor & XGBoost Regressor
5. Metric Evaluation (MAE, RMSE, R²)
6. Programmatic Best Model Selection
7. Output Generation:
   - outputs/random_forest.pkl
   - outputs/xgboost.pkl
   - outputs/model_metrics.csv
   - outputs/prediction_report.csv
   - outputs/plots/ (actual vs predicted, model comparison, feature importance)
"""

import os
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from ml.visualizer import (
    plot_actual_vs_predicted,
    plot_model_comparison,
    plot_feature_importance,
)

INPUT_FILE = "outputs/carbon_report.csv"
OUTPUT_DIR = "outputs"
TARGET_COLUMN = "Total_Emissions"
LEAKAGE_COLUMNS = ["Scope1_Emissions", "Scope2_Emissions", "Scope3_Emissions"]

def load_and_preprocess_data(file_path: str = INPUT_FILE):
    """
    Load dataset, handle missing values, validate numeric columns, and separate features/target.
    Ensures strict prevention of data leakage.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input carbon report dataset not found at '{file_path}'. Run Module 1 & 2 first.")
        
    df = pd.read_csv(file_path)
    
    # Handle missing values if any
    df = df.fillna(df.median(numeric_only=True))
    
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not present in dataset.")
        
    y = df[TARGET_COLUMN]
    
    # Exclude target and leakage columns
    drop_cols = [TARGET_COLUMN] + [col for col in LEAKAGE_COLUMNS if col in df.columns]
    X = df.drop(columns=drop_cols)
    
    # Select only numeric features
    X = X.select_dtypes(include=[np.number])
    
    print(f"[ML Pipeline] Loaded dataset with {len(df)} records.")
    print(f"[ML Pipeline] Target: {TARGET_COLUMN}")
    print(f"[ML Pipeline] Features ({len(X.columns)}): {list(X.columns)}")
    print(f"[ML Pipeline] Excluded Leakage Features: {[col for col in LEAKAGE_COLUMNS if col in df.columns]}")
    
    return df, X, y

def train_and_evaluate_models(X, y):
    """
    Train RandomForestRegressor and XGBRegressor, compute MAE, RMSE, R2, and select the best model.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # ---------------------------------------------------------
    # 1. Random Forest Regressor
    # ---------------------------------------------------------
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    
    rf_mae = mean_absolute_error(y_test, rf_preds)
    rf_rmse = np.sqrt(mean_squared_error(y_test, rf_preds))
    rf_r2 = r2_score(y_test, rf_preds)
    
    rf_path = os.path.join(OUTPUT_DIR, "random_forest.pkl")
    with open(rf_path, "wb") as f:
        pickle.dump(rf_model, f)
        
    # ---------------------------------------------------------
    # 2. XGBoost Regressor
    # ---------------------------------------------------------
    xgb_model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    xgb_model.fit(X_train, y_train)
    xgb_preds = xgb_model.predict(X_test)
    
    xgb_mae = mean_absolute_error(y_test, xgb_preds)
    xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_preds))
    xgb_r2 = r2_score(y_test, xgb_preds)
    
    xgb_path = os.path.join(OUTPUT_DIR, "xgboost.pkl")
    with open(xgb_path, "wb") as f:
        pickle.dump(xgb_model, f)
        
    # ---------------------------------------------------------
    # 3. Model Metrics Compilation
    # ---------------------------------------------------------
    metrics_data = [
        {"Model": "Random Forest", "MAE": round(rf_mae, 4), "RMSE": round(rf_rmse, 4), "R2": round(rf_r2, 4)},
        {"Model": "XGBoost", "MAE": round(xgb_mae, 4), "RMSE": round(xgb_rmse, 4), "R2": round(xgb_r2, 4)}
    ]
    metrics_df = pd.DataFrame(metrics_data)
    
    metrics_csv_path = os.path.join(OUTPUT_DIR, "model_metrics.csv")
    metrics_df.to_csv(metrics_csv_path, index=False)
    
    # ---------------------------------------------------------
    # 4. Best Model Selection
    # ---------------------------------------------------------
    # Higher R2 score indicates better fit
    if xgb_r2 >= rf_r2:
        best_model_name = "XGBoost"
        best_model = xgb_model
        best_r2 = xgb_r2
    else:
        best_model_name = "Random Forest"
        best_model = rf_model
        best_r2 = rf_r2
        
    print("\n" + "=" * 60)
    print("           ML MODEL EVALUATION RESULTS")
    print("=" * 60)
    print(metrics_df.to_string(index=False))
    print("-" * 60)
    print(f"Selected Best Model : {best_model_name} (R^2 = {best_r2:.4f})")
    print("=" * 60 + "\n")
    
    return {
        "rf_model": rf_model,
        "xgb_model": xgb_model,
        "best_model_name": best_model_name,
        "best_model": best_model,
        "metrics_df": metrics_df,
        "X_test": X_test,
        "y_test": y_test,
        "X": X,
        "y": y
    }

def generate_predictions_and_reports(df, X, y, best_model, best_model_name):
    """
    Generate predictions across the full dataset using the best model,
    save prediction_report.csv, and generate plot visual assets.
    """
    full_preds = best_model.predict(X)
    prediction_errors = np.abs(y - full_preds)
    
    pred_df = pd.DataFrame({
        "actual_Total_Emissions": np.round(y, 2),
        "predicted_Total_Emissions": np.round(full_preds, 2),
        "prediction_error": np.round(prediction_errors, 2),
        "model_used": best_model_name
    })
    
    pred_csv_path = os.path.join(OUTPUT_DIR, "prediction_report.csv")
    pred_df.to_csv(pred_csv_path, index=False)
    print(f"[ML Pipeline] Prediction report generated: '{pred_csv_path}' ({len(pred_df)} records)")
    
    return pred_df

def run_ml_pipeline():
    """
    Execute full ML pipeline.
    """
    df, X, y = load_and_preprocess_data()
    eval_res = train_and_evaluate_models(X, y)
    
    best_model_name = eval_res["best_model_name"]
    best_model = eval_res["best_model"]
    metrics_df = eval_res["metrics_df"]
    
    pred_df = generate_predictions_and_reports(df, X, y, best_model, best_model_name)
    
    # ---------------------------------------------------------
    # Visualizations
    # ---------------------------------------------------------
    plot_actual_vs_predicted(
        pred_df["actual_Total_Emissions"],
        pred_df["predicted_Total_Emissions"],
        best_model_name
    )
    
    plot_model_comparison(metrics_df)
    
    feature_importances = best_model.feature_importances_
    plot_feature_importance(list(X.columns), feature_importances, best_model_name)
    
    return {
        "metrics_df": metrics_df,
        "best_model_name": best_model_name,
        "pred_df": pred_df
    }

if __name__ == "__main__":
    run_ml_pipeline()
