# October 16 — Security Decision Fusion

The framework now compares four decision strategies:

1. Single Guard
2. Equal Majority Voting
3. Static Weighting
4. Adaptive Trust-Weighted Fusion

The proposed adaptive method uses each monitor's current reliability/trust as its decision authority.

Initial risk fusion:

`Final Risk = sum(T_i * q_i) / sum(T_i)`

where:
- `T_i` = current monitor trust
- `q_i` = event risk score produced by that monitor

The final risk is mapped to ALLOW / REVIEW / BLOCK using validation-tunable thresholds.

The demo intentionally creates a two-versus-one majority failure:
two low-trust compromised monitors vote ALLOW while one high-trust monitor strongly votes BLOCK.

This demo validates the mechanism only. Final research claims require the larger controlled experiments planned next.
