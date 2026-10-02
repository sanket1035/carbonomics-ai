"""
visualizer.py

Plots for the weekly activity forecast (test weeks only, time-ordered).

1. plot_forecast            : actual vs each model/baseline over the test weeks
2. plot_metric_comparison   : MAE of every model and baseline per target
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

OUTPUT_PLOT_DIR = "outputs/plots"

LABELS = {
    "electricity_kwh": "Weekly electricity (kWh)",
    "diesel_litres": "Weekly generator diesel (L)",
}


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def plot_forecast(pred_df: pd.DataFrame, target: str, save_dir: str = OUTPUT_PLOT_DIR) -> str:
    _ensure_dir(save_dir)
    path = os.path.join(save_dir, f"forecast_{target}.png")

    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    x = pd.to_datetime(pred_df["week_start"])
    ax.plot(x, pred_df[f"actual_{target}"], color="black", marker="o", linewidth=2, label="Actual (synthetic)")
    for col in [c for c in pred_df.columns if c.startswith("pred_")]:
        ax.plot(x, pred_df[col], marker=".", linewidth=1.2, label=col.replace("pred_", ""))
    ax.set_title(f"{LABELS[target]}: actual vs predicted (test weeks)")
    ax.set_xlabel("Week start")
    ax.set_ylabel(LABELS[target])
    ax.legend(frameon=False, fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"[Visualization] Saved: {path}")
    return path


def plot_metric_comparison(metrics_df: pd.DataFrame, save_dir: str = OUTPUT_PLOT_DIR) -> str:
    _ensure_dir(save_dir)
    path = os.path.join(save_dir, "model_comparison.png")

    targets = list(metrics_df["target"].unique())
    fig, axes = plt.subplots(1, len(targets), figsize=(6 * len(targets), 4.5), dpi=200)
    if len(targets) == 1:
        axes = [axes]
    for ax, target in zip(axes, targets):
        sub = metrics_df[metrics_df["target"] == target]
        ax.bar(sub["model"], sub["MAE"], color="#4c78a8")
        for i, v in enumerate(sub["MAE"]):
            ax.text(i, v, f"{v:,.1f}", ha="center", va="bottom", fontsize=8)
        ax.set_title(f"MAE: {LABELS[target]}")
        ax.set_ylabel("MAE")
        ax.tick_params(axis="x", rotation=20)
    fig.suptitle("Models vs baselines (lower is better; SYNTHETIC data)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"[Visualization] Saved: {path}")
    return path


def plot_emission_forecast(emission_table: pd.DataFrame, save_dir: str = OUTPUT_PLOT_DIR) -> str:
    """Weekly total emission (Scope 1 + Scope 2): actual vs each model/baseline."""
    _ensure_dir(save_dir)
    path = os.path.join(save_dir, "forecast_emission_total.png")

    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    x = pd.to_datetime(emission_table["week_start"])
    ax.plot(x, emission_table["actual_total_kg"], color="black", marker="o", linewidth=2, label="Actual (synthetic)")
    for col in [c for c in emission_table.columns if c.startswith("emission_pred_")]:
        ax.plot(x, emission_table[col], marker=".", linewidth=1.2, label=col.replace("emission_pred_", ""))
    ax.set_title("Weekly emission (Scope 1 + Scope 2): actual vs predicted (test weeks)")
    ax.set_xlabel("Week start")
    ax.set_ylabel("kg CO2e per week")
    ax.legend(frameon=False, fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"[Visualization] Saved: {path}")
    return path
