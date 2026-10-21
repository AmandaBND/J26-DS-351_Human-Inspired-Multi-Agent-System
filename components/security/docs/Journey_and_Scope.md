## October 19 implementation update

The active Semantic/Prompt Monitor has been replaced by a Prompt-Aware Data Minimization and Least-Privilege Enforcement Monitor. Its internal monitor ID remains `semantic-monitor` to keep earlier experiment records usable. The original Prompt Guard work and earlier results are preserved as historical PP1 evidence; they are not results for this replacement. The Policy and Behavior Monitors, reliability-feature extraction, ML training, attestation, and trust-weighted fusion remain part of the component. Adaptive trust now uses the minimum available independent reliability signal rather than manually assigned evidence weights. The optional LLM column selector is not used by the default local baseline.

---

# 01 - My Research Journey and Research Scope

## Research Component

**Adaptive Self-Attesting Multi-Agent Security Framework for Trustworthy Enterprise Agentic Systems**

This is my individual component of the group research project:

**Hierarchical Human-Inspired Multi-Agent Decision Support Framework for Enterprise Technology Service Operations**

My main research problem is not only detecting attacks against application agents. I am studying what happens when the **security monitors themselves become unreliable or compromised**.

The main question I am trying to answer is:

> Can a multi-agent security system still make reliable security decisions when one or more of its own security monitors become unreliable?

---

## How My Research Idea Developed

At the beginning, my idea was mainly a security layer for enterprise AI agents. It included prompt checking, policy checking, anomaly detection, logging and output security.

After the proposal feedback and literature review, I understood that only building these security functions would look more like a product than a research contribution.

The research was then narrowed to the reliability of the security monitors themselves.

My current idea is:

```text
Application / Enterprise Agent
            |
            v
      Security Event
            |
     -------------------
     |        |        |
     v        v        v
 Semantic   Policy   Behavior
 Monitor    Monitor  Monitor
     |        |        |
     -------------------
            |
            v
      Monitor Decisions
            |
            v
   Monitor Behavior History
            |
      ----------------
      |              |
      v              v
Known-Answer      Policy /
Challenges        Verified Evidence
      |              |
      ----------------
            |
            v
   Reliability Features
            |
            v
 Reliability ML Models
            |
            v
    Adaptive Trust
            |
            v
 Trust-Weighted Fusion
            |
            v
 ALLOW / REVIEW / BLOCK
```

The three security monitors are used to protect the application-agent layer. My main research contribution starts after their decisions are collected, because I then evaluate whether the **security monitors can still be trusted**.

---

## Main Security Monitors I Developed

### 1. Semantic / Prompt Monitor

I use **Meta Llama Prompt Guard 2 86M** through Hugging Face Transformers and PyTorch.

Its purpose is to inspect text and identify prompt-injection or malicious-prompt behavior.

It returns a common result containing:

- ALLOW / REVIEW / BLOCK;
- risk score;
- confidence;
- latency;
- reason code.

I successfully tested the real Prompt Guard model with a malicious prompt.

### 2. Policy / Tool Monitor

This monitor is written using normal Python rules.

It checks whether an application agent is allowed to access a resource or use a tool.

Example:

```text
Customer Complaint Agent
        |
        v
full_customer_database
        |
        v
BLOCK
```

I use a JSON policy file for allowed and blocked resources/tools.

This monitor does not need an LLM because the policy is deterministic.

### 3. Behavior / Anomaly Monitor

This monitor uses **Isolation Forest** from scikit-learn.

It checks abnormal behavior of the **application agent**, such as:

- unusually high tool-call frequency;
- restricted-resource attempts;
- failed authorization attempts;
- external API calls;
- high database-query activity;
- sensitive-resource attempts.

The initial behavior baseline is synthetic and is only used as an engineering baseline for PP1.

---

## Controlled Security-Monitor Compromise

To evaluate monitor reliability, I created controlled experiments where a security monitor can behave in different known conditions.

Current experiment modes are:

- NORMAL
- FALSE_ALLOW
- FALSE_BLOCK
- SELECTIVE_FALSE_ALLOW
- INTERMITTENT_FLIP
- PROMPT_MANIPULATED
- UNAVAILABLE
- COLLUDING
- RECOVERED

This is not real hacking. The experiment controller deliberately changes monitor behavior so I have known ground truth.

The hidden monitor state is used only for evaluation and is not given to the reliability model as an input.

---

## What Self-Attestation Means in My Research

Self-attestation does not mean the monitor says:

> “I am trustworthy.”

I use software-level behavioral verification.

For example, I give a monitor a known-answer challenge:

```text
Known challenge:
Request credential_store

Correct security decision:
BLOCK
```

If the monitor returns ALLOW, it fails the challenge.

From several challenges I can calculate values such as:

```text
challenge_accuracy = correct challenges / total challenges
```

This gives independent evidence about monitor reliability.

---

## My Research Contribution

The main research contribution I am currently testing is:

> Use independent behavioral verification evidence to estimate the reliability of dedicated security monitors over time, and dynamically reduce the decision authority of monitors that become unreliable or compromised.

The contribution is not simply:

- using multiple agents;
- using dynamic trust;
- using weighted voting;
- using a security agent.

Those ideas already exist in previous research.

My focus is the combination of:

```text
Security-monitor behavior
        +
Known-answer verification
        +
Reliability modelling
        +
Temporal trust
        +
Adaptive decision authority
```

---

## Current Research Boundary

This project is currently a controlled research prototype.

It is not a production SOC or a complete enterprise cybersecurity product.

For PP1 I am mainly evaluating:

- security-monitor behavior;
- controlled monitor compromise;
- independent verification;
- reliability features;
- reliability models;
- adaptive trust;
- security decision fusion.

Full enterprise integration is later work.
