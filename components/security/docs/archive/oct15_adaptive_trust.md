# October 15 — Adaptive Temporal Monitor Reliability

The ML classifier produces `P(compromised)` for a security-monitor observation.

The proposed trust layer converts this into a reliability signal and combines it with independent evidence:

- model reliability = `1 - P(compromised)`
- known-answer challenge accuracy
- deterministic policy integrity = `1 - policy_violation_rate`

The current PP1 raw reliability is a validation-tunable weighted combination of the available evidence.

Temporal update:

`T_t = alpha * T_(t-1) + (1 - alpha) * R_t`

This prevents one isolated error from instantly destroying trust while allowing sustained bad evidence to reduce authority.

A severe deterministic violation may immediately cap trust and isolate the monitor.

All current weights/thresholds are engineering defaults for PP1 and must be tuned/validated before final reporting.
