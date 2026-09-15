"""
visualizer.py

Carbonomics-AI Plot & Visualization Generation Module (Module 3)

Generates publication-ready visual assets for PPT & documentation:
1. Actual vs Predicted Emissions Plot
2. Model Performance Comparison Chart (MAE, RMSE, R²)
3. Feature Importance Chart for the Best Model
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set cohesive modern style
sns.set_theme(style="whitegrid")
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

OUTPUT_PLOT_DIR = "outputs/plots"

def ensure_plot_dir():
    os.makedirs(OUTPUT_PLOT_DIR, exist_ok=True)

def plot_actual_vs_predicted(actual, predicted, model_name: str, save_path: str = None):
    """
    Generate Actual vs Predicted Emissions Scatter Plot with reference line.
    """
    ensure_plot_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_PLOT_DIR, "actual_vs_predicted.png")
        
    plt.figure(figsize=(8, 6), dpi=300)
    
    # Scatter plot
    plt.scatter(
        actual, predicted,
        color="#1f77b4", alpha=0.7, edgecolors="k", linewidth=0.5, s=50, label="Predictions"
    )
    
    # Perfect prediction line
    min_val = min(min(actual), min(predicted))
    max_val = max(max(actual), max(predicted))
    plt.plot(
        [min_val, max_val], [min_val, max_val],
        color="#e377c2", linestyle="--", linewidth=2, label="Ideal (1:1)"
    )
    
    plt.title(f"Actual vs Predicted Total Emissions ({model_name})", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Actual Total Emissions (kg CO2e)", fontsize=11, fontweight="bold")
    plt.ylabel("Predicted Total Emissions (kg CO2e)", fontsize=11, fontweight="bold")
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()
    
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Visualization] Saved: {save_path}")
    return save_path

def plot_model_comparison(metrics_df: pd.DataFrame, save_path: str = None):
    """
    Generate bar plot comparing Random Forest vs XGBoost across MAE, RMSE, R2.
    """
    ensure_plot_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_PLOT_DIR, "model_comparison.png")
        
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=300)
    
    colors = ["#2ca02c", "#ff7f0e"]
    
    # MAE Plot
    sns.barplot(x="Model", y="MAE", hue="Model", data=metrics_df, ax=axes[0], palette=colors, legend=False)
    axes[0].set_title("Mean Absolute Error (MAE)", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("MAE (kg CO2e)", fontsize=10)
    for p in axes[0].patches:
        if p.get_height() > 0:
            axes[0].annotate(f"{p.get_height():.2f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                             ha='center', va='bottom', fontsize=10, fontweight='bold', xytext=(0, 3),
                             textcoords='offset points')
        
    # RMSE Plot
    sns.barplot(x="Model", y="RMSE", hue="Model", data=metrics_df, ax=axes[1], palette=colors, legend=False)
    axes[1].set_title("Root Mean Squared Error (RMSE)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("RMSE (kg CO2e)", fontsize=10)
    for p in axes[1].patches:
        if p.get_height() > 0:
            axes[1].annotate(f"{p.get_height():.2f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                             ha='center', va='bottom', fontsize=10, fontweight='bold', xytext=(0, 3),
                             textcoords='offset points')

    # R2 Plot
    sns.barplot(x="Model", y="R2", hue="Model", data=metrics_df, ax=axes[2], palette=colors, legend=False)
    axes[2].set_title("R^2 Score (Coefficient of Determination)", fontsize=12, fontweight="bold")
    axes[2].set_ylabel("R^2 Score", fontsize=10)
    axes[2].set_ylim(0, 1.05)
    for p in axes[2].patches:
        if p.get_height() > 0:
            axes[2].annotate(f"{p.get_height():.4f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                             ha='center', va='bottom', fontsize=10, fontweight='bold', xytext=(0, 3),
                             textcoords='offset points')

    plt.suptitle("Machine Learning Model Performance Comparison", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[Visualization] Saved: {save_path}")
    return save_path

def plot_feature_importance(feature_names: list, importances: np.ndarray, model_name: str, save_path: str = None):
    """
    Generate horizontal bar plot for top feature importances.
    """
    ensure_plot_dir()
    if save_path is None:
        save_path = os.path.join(OUTPUT_PLOT_DIR, "feature_importance.png")
        
    df = pd.DataFrame({
        "Feature": feature_names,
        "Importance": importances
    }).sort_values(by="Importance", ascending=True)
    
    plt.figure(figsize=(9, 7), dpi=300)
    plt.barh(df["Feature"], df["Importance"], color="#1f77b4", edgecolor="#0e4b75")
    
    for index, value in enumerate(df["Importance"]):
        plt.text(value + 0.002, index, f"{value:.4f}", va='center', fontsize=9, fontweight='bold')
        
    plt.title(f"Feature Importance Breakdown ({model_name})", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Importance Score", fontsize=11, fontweight="bold")
    plt.ylabel("Operational Activity Feature", fontsize=11, fontweight="bold")
    plt.xlim(0, max(importances) * 1.15)
    plt.tight_layout()
    
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[Visualization] Saved: {save_path}")
    return save_path
