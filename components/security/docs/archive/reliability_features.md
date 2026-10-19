# Security-Monitor Reliability Feature Dataset

One feature row currently represents one security monitor during one complete controlled experiment episode/window.

## Model input features

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

## Labels / metadata that are NOT model inputs

- episode_id
- monitor_id
- monitor_type
- decision_count
- challenge_count
- label_state
- compromised_label

`compromised_label` is controller-owned ground truth used only as the supervised target/evaluation label.

The current demo creates only a normal and a false-allow-compromised row to verify the pipeline. It is not the final ML training dataset.
