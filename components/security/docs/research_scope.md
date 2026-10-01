# Individual Research Scope

## Research Component

Adaptive Self-Attesting Multi-Agent Security Framework for Trustworthy Enterprise Agentic Systems

## Overall Research Project

Hierarchical Human-Inspired Multi-Agent Decision Support Framework for Enterprise Technology Service Operations

## Student

B.N.D.A.L. Batagoda  
IT23280274

---

## 1. Research Problem

LLM-based multi-agent systems may contain application agents that are monitored by security or guard agents.

Existing multi-agent security approaches can detect malicious prompts, abnormal agent behaviour, unsafe tool usage and compromised application agents.

However, a security agent itself may also become unreliable, manipulated or compromised.

If a compromised security agent continues to influence security decisions, it may:

- incorrectly allow malicious actions;
- incorrectly block legitimate actions;
- disagree abnormally with other security agents;
- provide misleading security assessments;
- reduce the reliability of the complete security framework.

Therefore, this research focuses on the trustworthiness of the security-monitoring agents themselves.

---

## 2. Main Research Question

Can software-level behavioural self-attestation and adaptive trust-weighted decision fusion maintain reliable security decisions when one or more security-monitoring agents in an LLM-based multi-agent system become unreliable or compromised?

---

## 3. Supporting Research Questions

### RQ1

Can behavioural and verification evidence be used to identify unreliable or compromised security-monitoring agents?

### RQ2

Can an adaptive trust score represent changes in the reliability of a security agent over time?

### RQ3

Does trust-weighted security decision fusion provide better resilience than a single-security-agent approach and equal-majority voting when security monitors become compromised?

### RQ4

How does the number of compromised security agents affect final security decision accuracy, attack success, false-positive rate and decision latency?

---

## 4. Research Hypothesis

### H1

Adaptive trust-weighted security decision-making will maintain higher final security-decision accuracy and lower attack success than single-security-agent and equal-majority-voting approaches when one or more security-monitoring agents become compromised.

### H0

Adaptive trust-weighted security decision-making will not provide a significant improvement over single-security-agent or equal-majority-voting approaches under compromised-security-agent conditions.

---

## 5. Proposed Research Contribution

The proposed research will investigate a security-monitoring architecture in which security agents are not permanently assumed to be trustworthy.

The framework will:

1. collect behavioural evidence from security agents;
2. perform software-level verification challenges;
3. estimate the reliability of each security agent;
4. maintain adaptive trust scores;
5. combine security decisions using trust-weighted aggregation;
6. reduce the influence of suspicious security agents;
7. isolate or escalate low-trust agents when necessary.

The research contribution is not simply the use of multiple security agents.

The main contribution being investigated is whether adaptive trust assessment and trust-weighted decision fusion can improve the resilience of a multi-agent security system when the security monitors themselves become unreliable.

---

## 6. Definition of Self-Attestation

In this research, self-attestation refers to software-level behavioural verification of a security agent.

It may use evidence such as:

- controlled security challenge results;
- previous decision correctness;
- disagreement patterns;
- false-allow behaviour;
- false-block behaviour;
- policy violations;
- abnormal tool usage;
- recent behavioural changes.

This research does not claim to implement hardware-based remote attestation or trusted-platform-module attestation.

---

## 7. Experimental Inputs

The controlled experimental environment will generate or record:

- security-agent identifier;
- application-agent identifier;
- security-event type;
- security-agent decision;
- expected/ground-truth decision;
- verification challenge result;
- disagreement with peer monitors;
- tool/resource activity;
- policy violations;
- response time;
- historical performance;
- compromised / normal label.

---

## 8. Initial Behavioural Features

The first experimental feature set will include:

- challenge_accuracy;
- disagreement_rate;
- false_allow_rate;
- false_block_rate;
- policy_violation_rate;
- abnormal_tool_rate;
- recent_accuracy;
- decision_flip_rate;
- response_latency;
- historical_reliability.

The exact final feature set may be refined after exploratory analysis.

---

## 9. Initial Baselines

The proposed method will initially be compared against:

### Baseline A — Single Security Agent

One security agent makes the final security decision.

### Baseline B — Equal Majority Voting

Multiple security agents vote, with every agent receiving equal decision authority.

### Proposed Method

Multiple security agents produce security assessments, while their influence is adjusted using dynamically estimated trust values.

---

## 10. Planned Evaluation Metrics

The research will initially evaluate:

- Precision;
- Recall;
- F1-score;
- False Positive Rate;
- False Negative Rate;
- Compromised Security-Agent Detection Rate;
- Final Security Decision Accuracy;
- Attack Success Rate;
- Decision Latency;
- Trust-score reliability;
- System resilience under increasing numbers of compromised monitors.

---

## 11. PP1 Scope

The Progress Presentation 1 demonstration will focus on the standalone individual component.

Integration with the Customer Complaint, Employee Performance and After-Sales Service components is intentionally excluded from the first experimental milestone.

By PP1, the expected research prototype should demonstrate:

- a controlled application-agent simulator;
- multiple security-monitor agents;
- normal and compromised monitor scenarios;
- security-event logging;
- software-level verification challenges;
- behavioural feature extraction;
- at least one initial trust-estimation model;
- single-agent and majority-voting baselines;
- an initial trust-weighted security decision mechanism;
- preliminary quantitative results.

---

## 12. Out of Scope for PP1

The following are not primary PP1 research goals:

- complete production UI;
- full integration with all other group components;
- production-ready SQL injection detection;
- production-ready PII detection;
- complete enterprise access-control implementation;
- deployment to Metropolitan production systems;
- full commercial platform development.

These functions may be added later as supporting system functionality.

---

## 13. Current Research Boundary

The central research question is:

> Can the security system remain reliable when the agents responsible for providing security decisions are themselves unreliable?

All implementation work should support the experimental investigation of this question.