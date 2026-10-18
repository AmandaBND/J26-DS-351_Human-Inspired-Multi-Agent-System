# October 14 — Reliability Benchmark and Baseline ML Models

## Purpose

The PP1 system needs enough monitor-reliability observations to compare candidate models.

The benchmark is explicitly controlled and synthetic. It creates complete experiment episodes with three monitor roles and known controller-owned compromise states.

## Episode conditions

- NORMAL
- FALSE_ALLOW
- FALSE_BLOCK
- SELECTIVE_FALSE_ALLOW
- INTERMITTENT_FLIP
- UNAVAILABLE
- COLLUDING
- PROMPT_MANIPULATED

## Split rule

Train, validation and test are generated as separate complete episodes. Rows from one episode are not randomly divided across splits.

## Candidate models

- Logistic Regression
- Random Forest
- XGBoost
- Isolation Forest

Isolation Forest is trained only on normal training rows.

Validation data selects the decision threshold. The test set is used once for preliminary reporting.

## Important limitation

This is a PP1 controlled benchmark, not evidence of production enterprise performance. Final research must expand the benchmark, test unseen conditions, repeat random seeds and include stronger external validation.
