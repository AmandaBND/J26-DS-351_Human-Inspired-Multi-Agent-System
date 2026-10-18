# Monitor Decision Logging

The decision-history logger stores the evidence needed later to construct the security-monitor reliability dataset.

Controller-only labels:
- experimental_monitor_state
- experimental_behavior_mode

These may be stored for evaluation, but they must never be used as input features for the reliability model.

Generated raw logs should normally not be committed.
