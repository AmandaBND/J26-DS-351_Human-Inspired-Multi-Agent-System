# Adaptive Self-Attesting Multi-Agent Security Framework

Individual research component of:

**Hierarchical Human-Inspired Multi-Agent Decision Support Framework for Enterprise Technology Service Operations**

Student: **B.N.D.A.L. Batagoda – IT23280274**

---

## Research Goal

This component investigates whether a multi-agent security system can remain reliable when one or more of its own security-monitoring agents become unreliable or compromised.

The proposed approach combines:

- behavioural monitoring;
- software-level self-attestation;
- adaptive trust estimation;
- trust-weighted security decisions;
- compromised-monitor isolation;
- human escalation.

---

## Research Pipeline

```text
Application Agent / Simulator
          v
    Security Event
          v

| Security Monitor Agents   |
          v
 Behavioural Evidence
          v
 Software Verification
          v
   Trust Estimation
          v
 Trust-Weighted Fusion
          v
Allow / Block / Review / Isolate

# Run
cd components\security
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\security_framework\main.py
pytest -v