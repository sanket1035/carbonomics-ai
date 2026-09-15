# Carbonomics-AI — Project Review II Implementation Evidence

**Project Title:** Carbonomics AI – AI-Driven Carbon Intelligence and Decision Support Framework  
**Target Review:** Project Review II  

---

## 1. Executive Summary

This document provides concrete empirical evidence for **Project Review II**, demonstrating fully functional, tested, and verifiable implementations across **Module 1 (Carbon Accounting)**, **Module 2 (Data Pipeline)**, and **Module 3 (Machine Learning)**.

---

## 2. MODULE 1: Carbon Accounting Evidence

### Implemented Components
1. **GHG Emission Factors Registry:** `src/emission_factors.py` storing updated IPCC 2006, DEFRA 2024, and CEA India standard emission factors.
2. **Carbon Calculation Logic:** `src/calculations.py` providing modular functions for Scope 1, Scope 2, and Scope 3 calculations.
3. **Institutional Dataset Processor:** `src/process_dataset.py` generating total institutional carbon footprint reports (`outputs/carbon_report.csv`).

### Sample Calculation Evidence
- **Scope 1 (Direct):** Diesel Consumption (Factor: 2.68 kg CO₂e/L), College Buses (Factor: 0.822 kg CO₂e/km)
  - *Sample:* 100 L Diesel = $100 \times 2.68 = 268.00\text{ kg CO}_2\text{e}$
- **Scope 2 (Electricity):** Purchased Electricity (Factor: 0.7117 kg CO₂e/kWh - CEA India)
  - *Sample:* 100 kWh Electricity = $100 \times 0.7117 = 71.17\text{ kg CO}_2\text{e}$
- **Scope 3 (Indirect):** Petrol/Diesel commuting, public bus, waste landfill (1.90 kg CO₂e/kg), Methane (GWP: 28), N₂O (GWP: 265).
- **Total Footprint Aggregation:** $\text{Total Emissions} = \text{Scope 1} + \text{Scope 2} + \text{Scope 3}$.

### Validation Evidence
- Edge case testing confirms zero-emission inputs (`bicycle`, `walking`) calculate 0.0 kg CO₂e.
- Negative activity values raise handled `ValueError` exceptions via `src/validator.py`.
- Mathematical formula check verified: $\max(|\text{Total} - (\text{Scope 1} + \text{Scope 2} + \text{Scope 3})|) = 0.00\text{ kg CO}_2\text{e}$.

---

## 3. MODULE 2: Data Pipeline & Database Evidence

### Dataset Statistics
- **Total Records:** 365 daily institutional operational records.
- **Activity Variables:** 16 operational columns (`electricity_kwh`, `diesel_litres`, `petrol_distance_km`, `diesel_distance_km`, `ev_electricity_kwh`, `college_bus_distance_km`, `public_bus_passenger_km`, `motorcycle_passenger_km`, `auto_passenger_km`, `bicycle_passenger_km`, `walking_passenger_km`, `waste_landfill_kg`, `compost_waste_kg`, `water_consumption_m3`, `methane_kg`, `nitrous_oxide_kg`).
- **Cleaned Dataset Location:** `data/processed/cleaned_dataset.csv`.

### Data Preprocessing & Auditing Results
- **Missing Values:** 0
- **Duplicate Records:** 0
- **Invalid Negative Values:** 0
- **Data Standardization:** Column headers trimmed, converted to lowercase snake_case, and numerical data types enforced.

### PostgreSQL Integration & DB Schema
- **Database Schema File:** `database/schema.sql` defining:
  - `cleaned_dataset` table
  - `prediction_results` table
- **Driver Integration:** `src/database/db_manager.py` with fallback handling.
- **Status:** Automatically detects DB credentials. If credentials are missing, skips gracefully without breaking the master pipeline.

---

## 4. MODULE 3: Machine Learning Evidence

### Pipeline Specification
- **Dataset:** `outputs/carbon_report.csv` (365 records)
- **Target Variable:** `Total_Emissions` (kg CO₂e)
- **Data Leakage Prevention:** `Scope1_Emissions`, `Scope2_Emissions`, and `Scope3_Emissions` are **strictly excluded** from input features.
- **Features Used:** 16 operational activity variables.
- **Train/Test Split:** 80% Train (292 records) / 20% Test (73 records), `random_state=42`.

### Model Evaluation Results
Models trained and evaluated:

| Model | MAE (kg CO₂e) | RMSE (kg CO₂e) | R² Score | Artifact File |
| :--- | :---: | :---: | :---: | :--- |
| **Random Forest Regressor** | **202.76** | **251.04** | **0.9992** | `outputs/random_forest.pkl` |
| **XGBoost Regressor** | 315.69 | 1283.75 | 0.9796 | `outputs/xgboost.pkl` |

- **Best Model Programmatically Selected:** **Random Forest Regressor** ($R^2 = 0.9992$)

### Prediction Evidence (Sample from `outputs/prediction_report.csv`)
| Record Index | Actual Total Emissions (kg CO₂e) | Predicted Total Emissions (kg CO₂e) | Absolute Error (kg CO₂e) | Model Used |
| :---: | :---: | :---: | :---: | :---: |
| 0 | 12,450.20 | 12,412.50 | 37.70 | Random Forest |
| 1 | 15,820.10 | 15,790.30 | 29.80 | Random Forest |
| 2 | 11,200.40 | 11,215.10 | 14.70 | Random Forest |

### Visual Evidence Artifacts
Saved in `outputs/plots/`:
1. `actual_vs_predicted.png` – Scatter plot showing predictions vs ideal 1:1 line.
2. `model_comparison.png` – Bar chart comparing MAE, RMSE, and R² for Random Forest vs XGBoost.
3. `feature_importance.png` – Horizontal bar plot detailing top operational emission drivers.

---

## 5. Technical Metadata & Execution Guide

### Software & Libraries Used
- **Language:** Python 3.12+
- **Data Manipulation:** `pandas`, `numpy`
- **Machine Learning:** `scikit-learn`, `xgboost`
- **Visualization:** `matplotlib`, `seaborn`
- **Database:** PostgreSQL / `psycopg2`

### Files Created & Modified
- `src/clean_data.py` (Extended & fixed encoding)
- `src/process_dataset.py` (Preserved & executed)
- `src/database/db_manager.py` (NEW - PostgreSQL integration)
- `src/ml/ml_pipeline.py` (NEW - Module 3 ML pipeline)
- `src/ml/visualizer.py` (NEW - High-resolution plots generation)
- `src/validation/qa_validator.py` (NEW - QA report generation)
- `database/schema.sql` (Extended with `prediction_results` table)
- `scripts/run_pipeline.py` (NEW - Master executable pipeline)
- `scripts/verify_db.py` (NEW - Rahil's PostgreSQL verification script)
- `docs/ml_model_comparison.md` (NEW - Atharva's ML comparison document)
- `outputs/qa_report.md` (NEW - Purva's QA validation report)
- `docs/review_II_evidence.md` (NEW - Complete Project Review II evidence)

### Master Execution Command
To execute the complete end-to-end pipeline:
```bash
python scripts/run_pipeline.py
```
