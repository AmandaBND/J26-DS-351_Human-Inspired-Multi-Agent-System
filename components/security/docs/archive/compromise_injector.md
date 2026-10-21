# Controlled Security-Monitor Compromise

The compromise injector is a research experiment harness. It does not hack a real host/model.

Current modes:
- NORMAL
- FALSE_ALLOW
- FALSE_BLOCK
- SELECTIVE_FALSE_ALLOW
- INTERMITTENT_FLIP
- PROMPT_MANIPULATED
- UNAVAILABLE
- COLLUDING
- RECOVERED

`monitor_state` and `behavior_mode` are controller-owned ground truth. They are logged for evaluation but must never become reliability-model input features.

Compromised `MonitorResult` objects intentionally do not include the hidden state/mode labels in their metadata.
