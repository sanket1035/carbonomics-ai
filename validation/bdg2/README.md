# External check of the forecasting protocol on public data (BDG2)

**What this is.** The Carbonomics-AI weekly protocol was run, unchanged, on real public education-building meters. It tests whether the *method* generalises. It says nothing about KKWIEER accuracy.

**Data.** Building Data Genome 2 (Miller et al. 2020, CC BY-SA 4.0): hourly cleaned electricity meters, 2016-2017, 604 buildings with primary use "Education" in 6 US/UK sites. Downloaded from the project's GitHub (LFS) on 2026-11-07. Nothing imputed, mocked or invented.

**Method (repo code reused, not rewritten).** Hourly kWh summed to Monday-start weeks (a week counts only if all 168 hours exist). Then `upload_analysis.forecast_target`: past-only features, **time-based 80/20 split** (no shuffle), RF / XGBoost / Ridge tuned by rolling-origin validation inside the training weeks, naive last-week baseline, MAE / RMSE / R2, and the **5% gate** (ML is used only if its test MAE is at least 5% below naive). Target is activity (kWh) only; emission is never predicted.

**Building selection.**
- *Primary (rule fixed before any result):* all 104 weeks complete -> **36 buildings**.
- *Secondary (added after seeing n = 36, because the strict rule drops 94% of meters for tiny gaps):* longest contiguous complete run of at least 78 weeks -> **58 buildings**, 6 sites. Primary is a subset. Test windows are 15-20 weeks.

| | Primary (36) | Secondary (58) |
|---|---|---|
| Gate accepts ML (beats naive by 5%+) | 8 (22%), 95% CI 12-38% | 14 (24%), 95% CI 15-37% |
| ML better than naive by any margin | 12 (33%) | 18 (31%) |
| Median MAE ratio, ML / naive | 1.11 | 1.12 (IQR 0.96-1.45) |
| Median R2, naive / ML candidate | 0.39 / 0.22 | 0.41 / 0.18 |

**Findings.**
1. **ML usually does not beat naive.** On a typical building the ML candidate has about 11% *higher* MAE than "repeat last week". The gate rejects ML in roughly 3 of 4 buildings.
2. **This matches the synthetic KKWIEER result** (gate accepted ML for electricity in 4 of 15 seeds): the protocol behaves the same way on real data.
3. **The gate is what protects the user.** Without it, ML would be shipped in about 2 of 3 buildings where it is worse. With it, ML is used only where it won on held-out weeks (8-14 buildings), and the naive forecast is used otherwise.
4. Where ML wins it can win clearly (best buildings: MAE ratio 0.65-0.69), so the ML code is not useless; it is just not reliably better on 2 years of weekly data.

**Honest limits.**
- Only 2 years per building, so models see fewer than 2 seasonal cycles; month features cannot learn yearly seasonality well. This probably favours naive.
- Buildings of one site share weather and academic calendar, so they are not independent: effective sample is closer to 6 sites than 58 buildings. The CIs above treat buildings as independent and are therefore too narrow.
- "Cleaned" BDG2 data has outliers already removed, and the complete-week filter keeps cleaner meters.
- The acceptance decision and the reported test MAE use the same held-out weeks (same as the repo); the win rate is therefore slightly optimistic for ML, which strengthens finding 1.
- Single time-split per building, no multi-origin evaluation.

**Claim you can safely make:** "On 58 public education buildings, the same leakage-free protocol (time split, naive baseline, 5% gate) accepts ML in about a quarter of cases and falls back to naive otherwise; the protocol is reproducible beyond KKWIEER, and it is conservative by design." **Do not claim** that ML forecasts electricity better than a naive baseline.

Files: see the list at the end of this README.

## Robustness (3 time origins, site-clustered bootstrap)

`run_bdg2_robustness.py` repeats the secondary set (58 buildings) with the last 0, 10 and 20 weeks dropped, so the held-out window differs each time, and bootstraps over the 6 sites instead of the 58 buildings.

- Gate accepts ML: 24% / 26% / 31% at the three origins, 27% pooled. Site-clustered bootstrap 95% CI: **9-49%**.
- Median MAE ratio ML / naive: 1.12 pooled, site-clustered 95% CI **0.95-1.62**. The interval contains 1, so "ML is worse than naive" is **not** established; "ML is not reliably better" is.
- Strong site effect: Lamb (19 buildings) median ratio 2.14, Robin (21) 0.99, Wolf (4) 0.81.
- 30 of 58 buildings never accept ML at any origin; only 5 accept at all three. The ML win is not stable.
- 4 of 174 windows had a naive MAE of exactly 0 and are excluded from the ratio (ML is not accepted there).

Outputs: `bdg2_robustness_summary.json`, `bdg2_robustness_per_origin.csv`.

## Data

Not committed (175 MB). Download `electricity_cleaned.csv` (`data/meters/cleaned/`) and `metadata.csv` (`data/metadata/`) from https://github.com/buds-lab/building-data-genome-project-2 (Git LFS; use the `media.githubusercontent.com/media/...` URLs). CC BY-SA 4.0, Miller et al. 2020. Run: `python -I run_bdg2_validation.py <bdg2_dir> <repo_dir> <out_dir>`.
