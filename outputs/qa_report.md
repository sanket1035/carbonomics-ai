# Carbonomics-AI QA Report

All statuses below are computed from the pipeline outputs. Data is SYNTHETIC (calibrated to real monthly totals).

**Overall: PASS**

## 1. Weekly dataset: PASS

- Rows: 52 | missing: 0 | duplicates: 0 | negatives: 0
- Exact 7-day week steps: True | labelled synthetic: True

## 2. Calibration to real monthly totals: PASS

- Tolerance 1% (31 Dec is not in the 52 weeks)
- electricity_kwh: weekly sum 1056458.31 vs real 1059147.0 (gap 0.254%)
- diesel_litres: weekly sum 4095.15 vs real 4100.0 (gap 0.118%)

## 3. Carbon accounting: PASS

- Max difference emission vs activity x factor: 0.01 kg
- Max difference total vs scope1+scope2+scope3: 0.0 kg
- Edge cases (zero, known sample, negative rejected): True
- Factors not yet verified against Master Data: petrol_vehicle, public_bus, motorcycle, auto_rickshaw
- Scope 3 and bus/refrigerant are not measured weekly and are excluded.

## 4. Forecast: PASS

- Naive and mean baselines present: True
- Test weeks are chronologically after training weeks: True
- Non-negative predictions: True
- Beats naive-last-week MAE (information only): {'electricity_kwh': {'random_forest': False, 'xgboost': False}, 'diesel_litres': {'random_forest': False, 'xgboost': True}}
