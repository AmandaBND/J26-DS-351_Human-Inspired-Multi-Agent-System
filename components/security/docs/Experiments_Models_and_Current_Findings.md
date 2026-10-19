# 03 - My Experiments, Models and Current Findings

## How the Experiment Works

My experiment has two different things to evaluate.

### First: the application event

The three security monitors inspect a security-relevant event.

```text
Security Event
     |
     +--> Semantic Monitor
     |
     +--> Policy Monitor
     |
     `--> Behavior Monitor
```

Each monitor returns:

```text
ALLOW / REVIEW / BLOCK
risk score
confidence
latency
reason
```

### Second: the security monitor itself

I then observe whether each security monitor is behaving reliably.

```text
Monitor Decisions
      +
Challenge Results
      +
Verified / Policy Evidence
      |
      v
Reliability Features
      |
      v
Reliability Model
      |
      v
P(compromised)
```

This second part is the main Data Science part of my research.

---

## Data Used

I currently use three main data sources.

### 1. Controlled normal and compromised scenarios

These are small scenario files created to test the framework structure.

They include normal, compromised and unavailable monitor conditions.

### 2. InjecAgent public benchmark

I integrated the public InjecAgent dataset for indirect prompt-injection cases.

I convert the dataset into my standard `SecurityEvent` format.

This is mainly useful for realistic public security-event inputs.

### 3. Controlled monitor-reliability benchmark

For PP1, I created a reproducible synthetic benchmark specifically for the monitor-reliability experiment.

Current split:

| Split | Episodes | Decision records | Challenge records | Feature rows |
|---|---:|---:|---:|---:|
| Train | 80 | 5760 | 1440 | 240 |
| Validation | 24 | 1728 | 432 | 72 |
| Test | 32 | 2304 | 576 | 96 |

The split is done by complete experiment episodes. I do not randomly split rows from the same episode across train and test.

This dataset is controlled synthetic PP1 evidence. It is not production enterprise data.

---

## Reliability Features

For each monitor/episode I calculate:

| Feature | What it means |
|---|---|
| challenge_accuracy | How often known-answer challenges are answered correctly |
| verified_decision_accuracy | How often monitor decisions match known expected decisions |
| false_allow_rate | How often dangerous events are incorrectly allowed |
| false_block_rate | How often safe events are incorrectly blocked |
| disagreement_rate | How often the monitor disagrees with peer monitors |
| policy_violation_rate | How often decisions contradict independently verified policy |
| decision_flip_rate | How unstable decisions are under similar conditions |
| risk_score_drift | How much risk scoring changes across the episode |
| missing_response_rate | How often the monitor is unavailable |
| response_latency_zscore | How unusual the latest latency is compared with its earlier behavior |

Peer disagreement is only supporting evidence. It is not treated as ground truth.

---

## Reliability Models I Compared

### Logistic Regression

I use it as a simple and interpretable supervised baseline.

### Random Forest

I use it as a nonlinear tabular-data classifier.

### XGBoost

I use it as another strong supervised tabular-data model.

### Isolation Forest

I use it as a normal-only anomaly-detection baseline.

This comparison lets me study labelled supervised detection versus normal-only anomaly detection.

---

## Current Preliminary Model Results

The current repository contains these PP1 test results:

| Model | Precision | Recall | F1 | AUPRC | FPR |
|---|---:|---:|---:|---:|---:|
| Random Forest | 0.970 | 1.000 | **0.985** | **1.000** | 0.0156 |
| XGBoost | 0.970 | 1.000 | **0.985** | 0.999 | 0.0156 |
| Logistic Regression | 0.969 | 0.969 | 0.969 | 0.999 | 0.0156 |
| Isolation Forest | 0.939 | 0.969 | 0.954 | 0.995 | 0.0313 |

In the current controlled PP1 benchmark, **Random Forest is selected by the current F1/AUPRC rule**.

I should not present this as proof that Random Forest is universally the best model. These are preliminary results from a controlled synthetic benchmark.

The final research still needs broader experiments and stronger external validation.

---

## Adaptive Trust

The reliability model gives:

```text
P(compromised)
```

I convert it into:

```text
model reliability = 1 - P(compromised)
```

Then I combine it with independent evidence:

```text
model reliability
+ challenge accuracy
+ policy integrity
        |
        v
current reliability evidence
```

The current PP1 trust update is:

```text
T(t) = alpha * T(t-1) + (1-alpha) * R(t)
```

This means one single error does not immediately remove a monitor, but repeated bad evidence gradually reduces its trust.

---

## Current Trust-Trajectory Demonstration

The current demo has three phases.

### Normal phase

Trust rises from about:

```text
0.877 -> 0.924
```

and remains `ACTIVE`.

### Compromised phase

Trust falls:

```text
0.705
0.552
0.445
0.370
0.318
```

The status changes from:

```text
ACTIVE -> REDUCED -> REVIEW
```

### Recovery phase

When good evidence returns, trust increases:

```text
0.481
0.596
0.677
0.733
0.772
```

The status eventually returns to `ACTIVE`.

This demonstrates the temporal idea I want to study: trust can decrease after sustained bad behavior and recover when evidence improves.

---

## Final Security Decision Fusion

After estimating trust, I compare four ways of combining monitor decisions.

### Baseline 1 - Single Guard

One security monitor decides the result.

### Baseline 2 - Equal Majority Voting

All monitors have equal voting power.

### Baseline 3 - Static Weighting

Each monitor has a fixed weight.

### Proposed - Adaptive Trust-Weighted Fusion

Each monitor's current trust controls how much influence its risk score has.

Current formula:

```text
Final Risk = sum(trust_i * risk_i) / sum(trust_i)
```

Then final risk is converted into:

```text
ALLOW
REVIEW
BLOCK
```

The important experiment is a case where two compromised monitors give the same wrong answer.

Example:

```text
Semantic Monitor
ALLOW
trust = low

Policy Monitor
BLOCK
trust = high

Behavior Monitor
ALLOW
trust = low
```

Equal majority can choose ALLOW because it sees two votes against one.

Adaptive trust weighting can reduce the influence of the two low-trust monitors.

The current fusion code demonstrates this mechanism, but the larger comparative experiment is still required before making a final performance claim.

---

## What Is Complete Now

Current implemented research pipeline:

```text
Security Event Schema                 DONE
Three Security Monitors               DONE
Policy Monitor                        DONE
Prompt Guard Monitor                  DONE
Behavior Isolation Forest             DONE
Decision Logging                      DONE
InjecAgent Adapter                    DONE
Controlled Monitor Compromise         DONE
Known-Answer Challenges               DONE
Reliability Feature Extraction        DONE
Train / Validation / Test Benchmark   DONE
Logistic Regression                   DONE
Random Forest                         DONE
XGBoost                               DONE
Isolation Forest Reliability Baseline DONE
Adaptive Temporal Trust               DONE
Decision Fusion Strategies            DONE
```

---

## What Is Still Research Work

The current results are useful for PP1, but they are not the final thesis result.

The next important work is:

- run full system-level experiments with 0, 1 and 2 compromised monitors;
- evaluate collusion;
- evaluate intermittent compromise;
- measure detection delay;
- measure recovery delay;
- compare final decision accuracy across fusion baselines;
- measure attack success rate and false allow/false block rate;
- repeat experiments with multiple random seeds;
- perform ablation tests;
- test unseen compromise patterns;
- expand external/public benchmark validation;
- later integrate with the other group components.

---

## Current Limitations I Need to State Clearly

1. The main reliability benchmark is synthetic and controlled.
2. Current trust weights and thresholds are PP1 engineering values and are not yet proven optimal.
3. The current high ML scores may be partly because the controlled conditions are easier to separate than real-world compromise.
4. The Behavior Monitor's initial normal baseline is synthetic.
5. InjecAgent provides useful public prompt-injection events, but it is not the complete monitor-reliability dataset.
6. The system is currently a standalone research prototype and is not yet fully integrated with the group enterprise platform.

These limitations are important because they separate preliminary PP1 evidence from final research conclusions.
