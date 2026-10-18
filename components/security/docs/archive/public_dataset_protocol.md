# Public Dataset Protocol

## First static benchmark: InjecAgent

The adapter preserves the full tool-response context as the security-monitor input.

Attack records are mapped to:

- EventType.TOOL_RESPONSE
- AttackType.PROMPT_INJECTION
- expected decision BLOCK

Preliminary benign tool-response contexts are created by removing the injection placeholder from the public user-case template.

These benign cases are useful for early false-positive checks, but they are not a complete production benign distribution.

## Provenance

Each preparation run records the exact Git commit of the locally cloned public source.

## AgentDojo

AgentDojo remains planned as a dynamic benchmark after the static ingestion path is stable.
