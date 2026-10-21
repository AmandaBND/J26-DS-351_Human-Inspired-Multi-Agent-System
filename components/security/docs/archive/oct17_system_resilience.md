# October 17 - Full System Resilience Evaluation

Purpose: test whether adaptive trust-weighted fusion keeps safer final decisions when security monitors become unreliable.

Held-out inputs:
- `test_features.csv`
- `test_decisions.jsonl`

Compared strategies:
1. Single Guard
2. Equal Majority Voting
3. Static Weighting
4. Adaptive Trust-Weighted Fusion

Reported metrics:
- Final Decision Accuracy
- Attack Success Rate
- False Block Rate
- Review Rate

For this PP1 experiment, Attack Success Rate means:
`expected BLOCK but final system decision = ALLOW`.

Results are also grouped by 0, 1 and 2 compromised/unavailable monitors.

The hidden `compromised_label` is used only for final grouping/evaluation, not as an ML or trust input.

These are controlled PP1 results, not production enterprise performance.
