# Threat Model

## Adaptive Self-Attesting Multi-Agent Security Framework

## 1. Purpose

This threat model defines the security conditions that will be used to evaluate the proposed framework.

The research focuses particularly on a condition where a security-monitoring agent itself becomes unreliable or compromised.

The framework is evaluated in a controlled experimental environment and does not perform attacks against real organizational systems.

---

## 2. Protected System

The experimental system contains two main categories of agents.

### Application Agents

Application agents perform enterprise tasks such as:

- complaint analysis;
- employee-performance analysis;
- after-sales service analysis;
- other business decision-support tasks.

### Security Monitoring Agents

Security monitoring agents inspect security-relevant activities such as:

- user inputs;
- agent actions;
- tool requests;
- resource-access requests;
- generated outputs;
- behavioural patterns.

The central research problem is that a security monitor cannot always be permanently assumed to be trustworthy.

---

## 3. Assets to Protect

The experimental framework aims to protect:

- security decisions;
- enterprise resources;
- agent actions;
- external tool access;
- confidential-data access;
- security-monitor integrity;
- audit and event records.

---

## 4. Main Threat Categories

### T1 - Prompt Injection

An agent receives instructions intended to override or manipulate its expected behaviour.

### T2 - Malicious Instruction

An application or monitoring agent receives an intentionally unsafe task or instruction.

### T3 - Abnormal Tool Usage

An agent attempts to access a tool or resource outside the expected behaviour for the scenario.

### T4 - False Allow

A security monitor incorrectly allows an event that should be blocked.

### T5 - False Block

A security monitor incorrectly blocks legitimate behaviour.

### T6 - Security Monitor Compromise

A security-monitoring agent begins producing unreliable security decisions.

### T7 - Security Monitor Collusion

Two or more compromised security monitors intentionally produce coordinated incorrect decisions.

### T8 - Security Monitor Unavailability

A security monitor becomes unavailable or does not return a security decision.

---

## 5. Security-Monitor States

Each security monitor in the controlled experiment can have one of the following ground-truth states:

- NORMAL
- COMPROMISED
- UNAVAILABLE

The experiment controls this state.

Therefore, the real condition of each monitor is known during evaluation.

---

## 6. Event Ground Truth

Each experimental event will contain a known expected security decision.

Possible expected decisions are:

- ALLOW
- BLOCK
- REVIEW

The framework output can therefore be compared with ground truth.

Example:

Event:
A legitimate internal employee-performance record request.

Expected decision:
ALLOW

Example:

Event:
A malicious request attempting to override system instructions.

Expected decision:
BLOCK

---

## 7. Security Monitor Behaviour

A normal security monitor should generally produce decisions that agree with ground truth.

A compromised security monitor may deliberately or incorrectly:

- allow malicious events;
- block legitimate events;
- produce inconsistent decisions;
- disagree abnormally with reliable monitors;
- fail verification challenges;
- misuse tools;
- produce abnormal response patterns.

These behaviours will later be converted into measurable features.

---

## 8. Attacker Capabilities

Within the controlled experiment, the attacker may be able to:

- send malicious instructions;
- manipulate an application-agent request;
- compromise one or more simulated security monitors;
- cause a compromised monitor to make incorrect decisions;
- create coordinated decisions between compromised monitors.

---

## 9. Attacker Limitations

The attacker is not assumed to:

- modify the experimental ground-truth labels;
- modify the trusted experiment controller;
- rewrite historical experiment results;
- compromise the host operating system;
- compromise GitHub;
- compromise the researcher account.

These assumptions keep the experiment measurable and repeatable.

---

## 10. Trust Boundary

The experiment controller is treated as trusted because it defines:

- scenario configuration;
- ground truth;
- monitor state;
- expected decision;
- experiment result.

Security-monitor agents are not permanently trusted.

Their reliability must be estimated from observable evidence.

---

## 11. Research Focus

The main research question is not simply whether malicious application behaviour can be detected.

The important question is:

> Can the final security system remain reliable when one or more of the security monitors responsible for protection become unreliable or compromised?

---

## 12. PP1 Threat Scope

The first progress presentation will initially demonstrate:

- normal operation;
- false allow behaviour;
- false block behaviour;
- one compromised security monitor;
- multiple conflicting monitor decisions.

Additional collusion and advanced attack experiments may be introduced after the first prototype is stable.

---

## 13. Ethical and Safety Boundary

All attack behaviour used in this research is simulated inside a controlled experimental environment.

No attack scenarios will be executed against production systems belonging to Metropolitan Technologies or any third party.

No real credentials, secrets or confidential company data will be stored in the experimental scenario files.