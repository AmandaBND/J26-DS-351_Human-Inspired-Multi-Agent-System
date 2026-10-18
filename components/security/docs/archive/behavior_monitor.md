# Behavior / Anomaly Monitor

The Behavior Monitor evaluates the **application agent**, not the security monitors.

Current model: `sklearn.ensemble.IsolationForest`.

Current PP1 baseline is explicitly synthetic and reproducible. It is only an engineering baseline, not final enterprise ground truth.

Current features per 10-action observation window:

- tool_call_frequency
- restricted_resource_attempts
- failed_authorization_count
- external_api_calls
- database_query_count
- sensitive_resource_attempts

The later Monitor Reliability Model is a different component that will analyze the behavior/history of the security monitors themselves.
