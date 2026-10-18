# October 14–16 Research Progress

## October 14

Research data and baseline modelling:
- generated a reproducible controlled monitor-reliability benchmark;
- split complete episodes into train / validation / test sets;
- compared Logistic Regression, Random Forest, XGBoost and Isolation Forest;
- validation data selects model thresholds;
- generated preliminary metrics and model-comparison figure.

## October 15

Adaptive reliability:
- combined model reliability with challenge and policy evidence;
- implemented temporal trust update;
- implemented trust states ACTIVE / REDUCED / REVIEW / ISOLATE;
- demonstrated trust decrease during compromise and recovery after normal behavior returns.

## October 16

Decision fusion:
- implemented Single Guard baseline;
- implemented Equal Majority baseline;
- implemented Static Weighting baseline;
- implemented proposed Adaptive Trust-Weighted Fusion;
- added a controlled majority-failure demonstration.

## Research-integrity note

All current benchmark/model results are preliminary PP1 evidence from a controlled synthetic reliability benchmark. They must not be described as production enterprise performance.
