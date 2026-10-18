# Software-Level Security-Monitor Self-Attestation

Self-attestation here does not mean a monitor claims "I am trustworthy."

The framework gives the monitor controlled known-answer challenges and checks whether its decisions match independent expected answers.

Examples:
- known blocked resource -> BLOCK
- approved resource -> ALLOW
- known prompt injection -> BLOCK

`challenge_accuracy` later becomes one reliability feature.

The correct challenge answer is owned by the experiment controller and is not supplied to the monitor as an input.
