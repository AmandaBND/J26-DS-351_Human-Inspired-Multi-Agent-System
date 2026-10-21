# Security Monitor Architecture

## Purpose

Every security monitor receives the same `SecurityEvent` and returns a normalized `MonitorResult`.

## MonitorResult

```text
monitor_id
monitor_type
event_id
decision
risk_score
confidence
latency_ms
reason_codes
metadata
```

`risk_score` means the estimated risk of the event. It is **not** the monitor's own reliability/trust score.

## Implemented now

### Policy / Tool Monitor
- deterministic Python policy engine;
- allowed/blocked resources;
- allowed/blocked tools;
- REVIEW for unknown resource/tool requests;
- does not read `event.expected_decision` when deciding.

### Semantic / Prompt Monitor
- `meta-llama/Llama-Prompt-Guard-2-86M` via Hugging Face Transformers;
- BENIGN/MALICIOUS classification;
- normalized risk score;
- ALLOW / REVIEW / BLOCK using prototype thresholds;
- long input chunking when a tokenizer is available.

## Not implemented yet

- behavior/anomaly monitor;
- monitor decision history logger;
- compromise injector;
- challenge engine;
- monitor-reliability features/models;
- temporal adaptive trust;
- trust-weighted fusion.
