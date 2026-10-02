# Carbonomics-AI

## AI-Driven Carbon Intelligence and Decision Support Framework

Carbonomics-AI is an AI-powered decision support system designed to help institutions measure, analyze, predict, and optimize carbon emissions using machine learning and sustainability analytics.

Unlike conventional carbon management systems that primarily focus on reporting, Carbonomics-AI combines carbon accounting, predictive analytics, scenario simulation, and optimization to support data-driven sustainability decisions.

---

## Project Vision

The objective of Carbonomics-AI is to develop an intelligent platform that enables organizations to:

- Measure carbon emissions accurately
- Predict future emission trends
- Identify major emission drivers
- Evaluate sustainability strategies through simulation
- Optimize emission reduction decisions
- Support long-term environmental planning

---

## Problem Statement

Traditional carbon management systems mainly emphasize emission reporting and regulatory compliance. While these systems provide valuable insights into current emissions, they often lack predictive capabilities and decision-support mechanisms.

Carbonomics-AI addresses this limitation by integrating carbon accounting, machine learning, simulation, and optimization into a unified framework that enables organizations to move from analysis to action.

---

## Core Features

- Carbon Emission Calculation
- GHG-Based Carbon Accounting
- Machine Learning Prediction
- Feature Importance Analysis
- Scenario-Based Simulation
- Optimization Engine
- Decision Support System
- Interactive Dashboard
- Sustainability Reports
- Data Visualization

---

## Planned System Architecture

```
Raw Data
   │
   ▼
Data Processing
   │
   ▼
Carbon Accounting
   │
   ▼
Machine Learning Prediction
   │
   ▼
Feature Analysis
   │
   ▼
Scenario Simulation
   │
   ▼
Optimization
   │
   ▼
Decision Support
```

---

## Planned Tech Stack

### Programming Language

- Python

### Data Processing

- Pandas
- NumPy

### Machine Learning

- Scikit-learn
- XGBoost

### Data Visualization

- Plotly
- Matplotlib

### Web Application

- Streamlit

### Database

- PostgreSQL
- SQLite

### Version Control

- Git
- GitHub

---

## Development Roadmap

### Phase 1 – Research & Planning

- [x] Literature Survey
- [x] Problem Identification
- [x] Research Gap Analysis
- [x] System Architecture
- [x] Research Methodology
- [x] Repository Setup

### Phase 2 – Carbon Accounting

- [x] Carbon Emission Calculator
- [x] GHG Emission Factors
- [x] Dataset Integration
- [x] Carbon Footprint Report

### Phase 3 – Machine Learning

- [x] Weekly dataset validation (synthetic, calibrated to real monthly totals)
- [x] Weekly activity forecast: Random Forest and XGBoost vs naive and mean baselines (time-based split)
- [x] Model Evaluation (MAE, RMSE, R2)
- [ ] Forecast on real weekly data (waiting for data)
- [ ] Emission Forecasting for Scope 3 sources (no activity data yet)

### Phase 4 – Analytics

- [ ] Feature Importance Analysis
- [ ] Interactive Dashboard
- [ ] Trend Analysis
- [ ] KPI Monitoring

### Phase 5 – Scenario Simulation

- [ ] What-if Analysis
- [ ] Renewable Energy Simulation
- [ ] Electric Vehicle Adoption
- [ ] Energy Efficiency Simulation

### Phase 6 – Optimization

- [ ] Strategy Comparison
- [ ] Constraint-Based Optimization
- [ ] Cost-Benefit Analysis
- [ ] Recommendation Engine

### Phase 7 – Web Application

- [ ] Streamlit Dashboard
- [ ] CSV Upload
- [ ] User Interaction
- [ ] Report Generation

### Phase 8 – Deployment

- [ ] Testing
- [ ] Documentation
- [ ] Performance Optimization
- [ ] Cloud Deployment

---

## Project Status

**Status:** Under Active Development

The project is being developed incrementally. Each module will be implemented, tested, documented, and released through regular commits.

---

## Research Foundation

Carbonomics-AI is inspired by recent research in:

- Carbon Accounting
- Machine Learning
- Explainable Artificial Intelligence
- Sustainability Analytics
- Optimization Techniques
- Decision Support Systems

---

## Repository Structure

```
Carbonomics-AI/
│── data/real/        real monthly 2025 electricity and generator diesel (Master Data)
│── data/synthetic/   weekly SYNTHETIC dataset + metadata (assumptions, seed)
│── data/processed/   validated weekly dataset
│── src/              emission_factors, calculations, clean_data, process_dataset
│── src/ml/           forecast_weekly (models + baselines), visualizer
│── src/validation/   QA checks and report
│── src/database/     PostgreSQL manager
│── scripts/          run_pipeline.py (full flow), make_synthetic_weekly.py, verify_db.py
│── database/         schema.sql, import.sql
│── tests/            pytest
│── outputs/          emissions, forecast metrics, plots, QA report
│── docs/
│── requirements.txt
```

## Run

```
pip install -r requirements.txt
python scripts/run_pipeline.py
pytest tests
```

The weekly dataset is SYNTHETIC: only the monthly totals are real. See
`docs/weekly_synthetic_forecast.md` for what is real, what is assumed and how to read the scores.

---

## Future Scope

Future versions of Carbonomics-AI will include:

- Real-time IoT data integration
- Carbon credit estimation
- Net-Zero planning
- Renewable energy optimization
- Multi-institution benchmarking
- AI-powered sustainability assistant

---

## License

Copyright © 2026 Team Carbonomics. All rights reserved.
This code is published for viewing and evaluation only. See LICENSE.
For permission to use it, contact Carbonomics.app@gmail.com

---

## Author

© 2026 Sanket Chaudhari 

This project is developed as an academic and portfolio project.
Unauthorized plagiarism or direct submission as one's own academic work is prohibited.

B.Tech Artificial Intelligence & Data Science

GitHub: https://github.com/sanket1035

LinkedIn: https://linkedin.com/in/sanketchaudhari1035
