# Safety Guardrails (Phase 9)

- Input scanning detects prompt injection markers, secrets, and PII.
- Output validation enforces schema and blocks policy/system leakage markers.
- Untrusted tool output is quarantined and instruction fragments are stripped.
- Memory write guardrails:
  - block secrets in shared memory by default
  - mark sensitive content and apply short expiry
  - shared writes require stronger permissions (group admin check)
- Redaction flow endpoint: `POST /memory/{id}/redact`.
- Escalation actions: block, human approval, human review queue, safe fallback hints.
