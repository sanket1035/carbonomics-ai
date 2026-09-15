# Carbonomics-AI Quality Assurance & Validation Report

**Author:** Purva (QA / Validation Lead)  
**Status:** Executed & Empirical Verification Passed  

---

## 1. Module 2: Data Pipeline Integrity Checks

| Verification Check | Target Standard | Observed Value | QA Status |
| :--- | :--- | :--- | :--- |
| **Row Count** | Matches raw dataset | `365` | **PASS** |
| **Column Count** | Expected schema | `16` | **PASS** |
| **Missing Values** | 0 Missing Values | `0` | **PASS** |
| **Duplicate Records** | 0 Duplicate Rows | `0` | **PASS** |
| **Negative Values** | 0 Negative Activity Values | `0` | **PASS** |

---

## 2. Module 1: Carbon Accounting Validation

| Calculation & Edge Case Check | Expected Result | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Scope Addition Identity** | `Total == Scope1 + Scope2 + Scope3` | Max Diff: `0.0` kg | **PASS** |
| **Electricity Factor Check** | `100 kWh -> 71.17 kg CO₂e` | `71.17 kg CO₂e` | **PASS** |
| **Diesel Factor Check** | `100 L -> 268.00 kg CO₂e` | `268.0 kg CO₂e` | **PASS** |
| **Edge Case Input Handling** | Throw `ValueError` on negative input | Exception Caught & Handled | **PASS** |

---

## 3. Module 3: Machine Learning Model Verification

| Metric / Check | Value / Condition | QA Status |
| :--- | :--- | :--- |
| **Total Model Predictions** | `365` | **PASS** |
| **Negative Predictions Count** | `0` | **PASS** |
| **Empirical Mean Error** | `108.4937 kg CO₂e` | **PASS** |
| **Max Prediction Discrepancy** | `652.87 kg CO₂e` | **PASS** |

### Verified Model Performance Table
```
        Model      MAE      RMSE     R2
Random Forest 202.7566  251.0424 0.9992
      XGBoost 315.6887 1283.7507 0.9796
```

---

## 4. Overall Quality Assurance Sign-off

- **Data Pipeline:** Verified clean dataset without duplicates, missing, or negative values.
- **Carbon Accounting:** Scope separation and GHG emission factor calculations verified 100% accurate.
- **Machine Learning:** Data leakage strictly prevented (Scope 1/2/3 excluded from predictors). Predictions verified valid and realistic.
