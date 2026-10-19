# 02 - What I Developed: Technologies, Folders and Files

## Main Technologies I Used

| Technology | Why I used it |
|---|---|
| Python | Main implementation language |
| Pydantic | Validating security events and experiment records |
| JSON / JSONL | Scenario files, policies and experiment logs |
| CSV | Feature datasets and result tables |
| Pandas | Reading and preparing tabular experiment data |
| NumPy | Numerical processing |
| scikit-learn | Isolation Forest, Logistic Regression, Random Forest and metrics |
| XGBoost | Additional supervised reliability model |
| Hugging Face Transformers | Loading the Prompt Guard model |
| PyTorch | Running the Prompt Guard neural model |
| Meta Llama Prompt Guard 2 86M | Semantic/prompt attack monitor |
| pytest | Automated tests |
| Matplotlib | Research graphs |
| joblib | Saving trained ML models |
| Git / GitHub | Version control and research progress evidence |

I have not used LangChain or LangGraph in this component because the current monitor and experiment logic can be implemented directly using Python classes.

---

## Main Folder Structure

```text
project/
|
|-- config/
|-- data/
|-- docs/
|-- models/
|-- results/
|-- scripts/
|-- src/security_framework/
|-- tests/
|-- requirements.txt
`-- README.md
```

I use each folder for a different purpose.

---

## 1. `config/`

This folder contains settings instead of hard-coding everything inside Python.

### `policies.json`

Contains allowed and blocked resources/tools for the Policy Monitor.

### `monitor_settings.json`

Contains Prompt Guard settings such as model name and prototype decision thresholds.

### `behavior_monitor.json`

Contains Behavior Monitor feature order and Isolation Forest settings.

### `challenge_bank.json`

Contains known-answer security challenges for monitor verification.

### `reliability_experiment.json`

Contains the controlled benchmark settings such as:

- random seed;
- number of train/validation/test episodes;
- events per episode;
- compromise conditions.

### `trust.json`

Contains initial adaptive-trust settings:

- initial trust;
- alpha;
- evidence weights;
- trust thresholds.

### `fusion.json`

Contains final decision-fusion settings such as:

- review threshold;
- block threshold;
- static baseline weights.

---

## 2. `src/security_framework/models/`

These files define the common data structures used by the whole experiment.

### `security_event.py`

Defines:

- `SecurityEvent`
- `MonitorDecision`
- event types;
- attack types;
- ALLOW / REVIEW / BLOCK;
- NORMAL / COMPROMISED / UNAVAILABLE states.

A `SecurityEvent` is the standard object given to the security monitors.

### `experiment_scenario.py`

Defines controlled experiment scenarios and monitor behavior modes.

Its purpose is to keep the experimental ground truth structured and repeatable.

---

## 3. `src/security_framework/monitors/`

These files contain the three security monitors.

### `base.py`

Defines the common monitor interface and `MonitorResult`.

All monitors return the same structure:

```text
monitor_id
monitor_type
event_id
decision
risk_score
confidence
latency_ms
reason_codes
metadata
```

This makes later comparison and fusion easier.

### `semantic_monitor.py`

Runs **Llama Prompt Guard 2 86M**.

Purpose:

```text
text / prompt
     |
     v
Prompt Guard
     |
     v
risk + decision
```

### `policy_monitor.py`

Runs deterministic Python policy checks using `policies.json`.

Purpose:

```text
role + resource/tool
        |
        v
policy rules
        |
        v
ALLOW / REVIEW / BLOCK
```

### `behavior_monitor.py`

Runs **Isolation Forest** over numeric application-agent behavior features.

Purpose:

```text
application-agent behavior features
              |
              v
       Isolation Forest
              |
              v
         anomaly risk
```

---

## 4. `src/security_framework/history/`

### `decision_logger.py`

Stores monitor decisions as JSONL and can export them to CSV.

This is important because later features such as false-allow rate and decision accuracy need historical monitor decisions.

The logger also stores experiment labels separately for evaluation.

---

## 5. `src/security_framework/experiment/`

### `compromise_injector.py`

Creates controlled unreliable monitor behavior such as:

- false allow;
- false block;
- intermittent errors;
- unavailability;
- collusion.

Purpose:

```text
real monitor output
       |
       v
controlled experiment condition
       |
       v
normal or intentionally unreliable output
```

### `synthetic_reliability_benchmark.py`

Creates a larger reproducible PP1 benchmark.

The uploaded repository currently contains:

- **80 training episodes**
- **24 validation episodes**
- **32 test episodes**

Each episode uses three monitors.

The generated benchmark contains:

- 5,760 training decision records;
- 1,440 training challenge records;
- 240 training feature rows;
- 1,728 validation decision records;
- 432 validation challenge records;
- 72 validation feature rows;
- 2,304 test decision records;
- 576 test challenge records;
- 96 test feature rows.

This is controlled synthetic research data, not production enterprise data.

---

## 6. `src/security_framework/attestation/`

### `challenge_runner.py`

Loads known-answer challenges and records whether a monitor gives the correct decision.

It produces evidence such as:

```text
challenge_accuracy
```

This is one part of the self-attestation mechanism.

---

## 7. `src/security_framework/features/`

### `reliability_features.py`

Converts monitor history and challenge results into ML features.

The current ten model features are:

1. challenge_accuracy
2. verified_decision_accuracy
3. false_allow_rate
4. false_block_rate
5. disagreement_rate
6. policy_violation_rate
7. decision_flip_rate
8. risk_score_drift
9. missing_response_rate
10. response_latency_zscore

One feature row currently represents one monitor during one controlled experiment episode.

The hidden compromise state is used as the target label and is not included in the model input.

---

## 8. `src/security_framework/ml/`

### `reliability_models.py`

Trains and compares four monitor-reliability models:

- Logistic Regression
- Random Forest
- XGBoost
- Isolation Forest

The first three use labelled normal and compromised training examples.

Isolation Forest is used as a normal-only anomaly-detection baseline.

Validation data is used to select the decision threshold before the test data is evaluated.

---

## 9. `src/security_framework/trust/`

### `adaptive_trust.py`

Converts model predictions and verification evidence into a changing trust score.

It uses:

```text
model reliability
+ challenge accuracy
+ policy integrity
        |
        v
raw reliability
        |
        v
temporal trust update
```

Current trust states are:

- ACTIVE
- REDUCED
- REVIEW
- ISOLATE

The current equation is:

```text
T(t) = alpha * T(t-1) + (1-alpha) * current reliability
```

---

## 10. `src/security_framework/fusion/`

### `decision_fusion.py`

Compares four final security-decision approaches:

- Single Guard
- Equal Majority Voting
- Static Weighting
- Adaptive Trust-Weighted Fusion

The proposed approach gives more decision authority to monitors with higher current trust.

---

## 11. `src/security_framework/datasets/`

### `injecagent_adapter.py`

Converts the public **InjecAgent** indirect prompt-injection benchmark into my `SecurityEvent` format.

The original public benchmark is stored separately under `external/InjecAgent`.

This allows public attack cases to enter the same monitor pipeline as my controlled scenarios.

---

## 12. `data/`

Important data areas are:

```text
raw_scenarios/
    initial normal and compromised scenarios

behavior_baseline/
    synthetic normal application-agent behavior

public/injecagent/
    converted public prompt-injection cases

monitor_logs/
    monitor decision history

attestation/
    challenge results

processed/
    early processed/feature demo files

benchmark/reliability/
    train / validation / test reliability benchmark
```

The most important ML dataset for my research is the **monitor-reliability feature dataset**, not the raw prompt-injection data.

---

## 13. `models/`

Contains trained model files saved using joblib:

```text
logistic_regression.joblib
random_forest.joblib
xgboost.joblib
isolation_forest.joblib
```

These are trained monitor-reliability models.

---

## 14. `results/`

Contains current PP1 research results.

### `results/reliability_models/`

Contains:

- model metrics;
- test predictions;
- model comparison figure;
- summary.

### `results/trust/`

Contains:

- adaptive-trust trajectory CSV;
- trust trajectory figure.

---

## 15. `scripts/`

The scripts are simple entry points so I do not need to manually call Python classes.

Examples:

```text
run_policy_monitor.py
    test Policy Monitor

run_semantic_monitor.py
    test real Prompt Guard

run_behavior_monitor.py
    test Behavior Monitor

prepare_injecagent_dataset.py
    convert public benchmark

run_compromise_demo.py
    demonstrate compromised monitor behavior

run_challenge_demo.py
    demonstrate known-answer verification

build_reliability_features.py
    create feature dataset

generate_reliability_benchmark.py
    generate train/validation/test benchmark

train_reliability_models.py
    train and compare the four reliability models

run_trust_trajectory_demo.py
    show trust falling and recovering

run_fusion_demo.py
    compare final decision strategies
```

---

## 16. `tests/`

The tests check each research component separately.

They cover areas such as:

- event validation;
- scenario loading;
- monitor outputs;
- decision logging;
- public dataset conversion;
- controlled compromise;
- challenge verification;
- reliability features;
- reliability benchmark generation;
- reliability ML logic;
- adaptive trust;
- decision fusion.

The tests are there to make sure changes do not silently break the experiment pipeline.
