# Machine Learning Model Comparison Report

**Author:** Atharva (Research & Machine Learning Lead)  
**Project:** Carbonomics-AI  
**Target Variable:** `Total_Emissions` (kg CO₂e)  

---

## 1. Overview & Objective

This document presents an empirical performance comparison between **Random Forest Regressor** and **XGBoost Regressor** trained on the Carbonomics-AI institutional dataset.

To ensure realistic predictive capabilities and prevent data leakage:
- `Scope1_Emissions`, `Scope2_Emissions`, and `Scope3_Emissions` were **strictly excluded** from the input feature set because `Total_Emissions` is mathematically defined as their sum.
- Predictive models were trained exclusively on operational activity inputs (`electricity_kwh`, `diesel_litres`, `petrol_distance_km`, `diesel_distance_km`, `ev_electricity_kwh`, `college_bus_distance_km`, `public_bus_passenger_km`, `motorcycle_passenger_km`, `auto_passenger_km`, `bicycle_passenger_km`, `walking_passenger_km`, `waste_landfill_kg`, `compost_waste_kg`, `water_consumption_m3`, `methane_kg`, `nitrous_oxide_kg`).

---

## 2. Models Evaluated

### 2.1 Random Forest Regressor
- **Working Principle:** An ensemble learning algorithm operating by constructing a multitude of decision trees at training time and outputting the mean prediction of the individual trees (Bagging).
- **Advantages:** Highly robust against overfitting, handles non-linear activity relationships well, resilient to minor feature noise, easy to interpret via feature importances.
- **Limitations:** Higher memory footprint when scaling to extremely large decision tree counts.

### 2.2 XGBoost Regressor (eXtreme Gradient Boosting)
- **Working Principle:** An optimized distributed gradient boosting library implementing decision trees sequentially (Boosting). Each new tree minimizes the residual loss of the ensemble using gradient descent.
- **Advantages:** Fast execution speed, built-in regularization ($L_1$ and $L_2$), strong performance on non-linear numerical datasets.
- **Limitations:** Prone to overfitting on smaller tabular datasets if hyperparameters are not tuned extensively.

---

## 3. Evaluation Metrics & Definitions

1. **Mean Absolute Error (MAE):** Average magnitude of absolute errors between predicted and actual emissions.
   $$MAE = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
2. **Root Mean Squared Error (RMSE):** Square root of the mean squared difference, penalizing larger prediction errors.
   $$RMSE = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$
3. **R² Score (Coefficient of Determination):** Proportion of variance in total carbon emissions predictable from operational features.
   $$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$

---

## 4. Empirical Evaluation Results

The models were evaluated on an 80/20 train/test split using `random_state=42`. Below are the actual metrics obtained from model execution:

| Model | MAE (kg CO₂e) | RMSE (kg CO₂e) | R² Score |
| :--- | :---: | :---: | :---: |
| **Random Forest** | **202.76** | **251.04** | **0.9992** |
| **XGBoost** | 315.69 | 1283.75 | 0.9796 |

---

## 5. Model Selection Rationale

- **Selected Best Model:** **Random Forest Regressor**
- **Justification:**
  - Random Forest achieved an outstanding $R^2$ score of **0.9992**, explaining 99.92% of emission variance.
  - Random Forest yielded significantly lower error rates across both MAE (**202.76 kg CO₂e**) and RMSE (**251.04 kg CO₂e**) compared to XGBoost (**1283.75 kg CO₂e** RMSE).
  - Random Forest demonstrated higher stability across tabular operational features without requiring heavy hyperparameter tuning.

---

## 6. Generated Model Artifacts

- Trained Random Forest Model: `outputs/random_forest.pkl`
- Trained XGBoost Model: `outputs/xgboost.pkl`
- Comparative Performance Metrics: `outputs/model_metrics.csv`
- Actual vs Predicted Scatter Plot: `outputs/plots/actual_vs_predicted.png`
- Model Performance Comparison Chart: `outputs/plots/model_comparison.png`
- Feature Importance Chart: `outputs/plots/feature_importance.png`
