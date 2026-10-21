# Experimental Data

This directory stores controlled research scenarios used by the Adaptive Self-Attesting Multi-Agent Security Framework.

## raw_scenarios

Contains manually defined or generated experimental scenarios.

Current dataset:

- normal_scenarios.json

All current scenarios are synthetic and contain no Metropolitan Technologies confidential information.

## processed

Contains structured outputs derived from the raw scenarios.

The processed files will later be used for:

- behavioural feature extraction;
- trust-model development;
- baseline experiments;
- security resilience evaluation.

## Important

Real organizational data must not be committed to this repository.

Any future Metropolitan data must be handled separately according to organizational approval, anonymization and ethical requirements.

## Compromised Security-Monitor Scenarios

`compromised_monitor_scenarios.json` contains controlled experiments in which the reliability of one or more security monitors is deliberately changed.

The current scenarios cover:

- false approval of malicious activity;
- false blocking of legitimate activity;
- conflicting security-monitor decisions;
- multiple compromised monitors;
- unavailable security monitors.

The monitor state and expected final security decision are known in advance so that later trust-estimation and decision-fusion methods can be evaluated against ground truth.