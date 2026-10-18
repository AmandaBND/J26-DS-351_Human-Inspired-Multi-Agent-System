# October 18 - Ablation, Recovery and PP1 Evidence

## Evidence ablation

The adaptive system is re-run with:
- full evidence;
- model probability only;
- no challenge evidence;
- no policy-integrity evidence.

This tests whether the self-attestation evidence contributes useful information.

## Dynamic experiment

Sequence:

`NORMAL -> COMPROMISED -> RECOVERY`

The selected supervised reliability model produces `P(compromised)` from representative held-out feature rows. The adaptive-trust estimator updates the monitor trust over observation windows.

Metrics:
- detection delay;
- recovery delay;
- minimum trust;
- final trust.

Detection occurs when the monitor first leaves `ACTIVE`.
Recovery occurs when it first returns to `ACTIVE`.

## PP1 summary

The final summary combines:
- ML model comparison;
- system fusion comparison;
- performance by 0/1/2 compromised monitors;
- ablation;
- dynamic detection/recovery.

All results remain preliminary controlled PP1 evidence.
