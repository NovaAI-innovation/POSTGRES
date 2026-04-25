from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class GuardrailDecision:
    allow: bool
    reason: str
    escalation: str | None = None
    safe_fallback: str | None = None
    sensitive: bool = False


class InputScanner:
    _injection_markers = (
        "ignore previous instructions",
        "override system prompt",
        "act as root",
        "exfiltrate",
    )
    _secret_patterns = (
        r"sk-[A-Za-z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"(?i)password\s*[:=]\s*\S+",
        r"(?i)api[_-]?key\s*[:=]\s*\S+",
    )
    _pii_patterns = (
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b(?:\d[ -]*?){13,16}\b",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    )

    def scan(self, text: str) -> GuardrailDecision:
        lower = text.lower()
        if any(marker in lower for marker in self._injection_markers):
            return GuardrailDecision(False, "prompt_injection_detected", escalation="block")
        for pattern in self._secret_patterns:
            if re.search(pattern, text):
                return GuardrailDecision(False, "secret_detected", escalation="human_approval", sensitive=True)
        for pattern in self._pii_patterns:
            if re.search(pattern, text):
                return GuardrailDecision(True, "pii_detected", escalation="human_review_queue", sensitive=True)
        return GuardrailDecision(True, "clean")


class OutputValidator:
    _blocked_output_markers = ("internal policy dump", "developer message leak", "system prompt is")

    def validate(self, payload: dict[str, Any]) -> GuardrailDecision:
        if "status" not in payload:
            return GuardrailDecision(False, "invalid_output_schema", escalation="block")
        raw = str(payload).lower()
        if any(marker in raw for marker in self._blocked_output_markers):
            return GuardrailDecision(False, "sensitive_leak_detected", escalation="block")
        return GuardrailDecision(True, "valid_output")


class UntrustedOutputQuarantine:
    _instruction_patterns = (
        r"(?i)ignore (all|previous) instructions",
        r"(?i)run this command:",
        r"(?i)execute shell",
    )

    def quarantine(self, text: str) -> dict[str, Any]:
        stripped = text
        flagged = False
        for pattern in self._instruction_patterns:
            if re.search(pattern, stripped):
                flagged = True
                stripped = re.sub(pattern, "[quarantined-instruction]", stripped)
        return {"quarantined": flagged, "content": stripped}


class MemoryGuardrail:
    def __init__(self, scanner: InputScanner) -> None:
        self._scanner = scanner

    def evaluate_write(self, content: str, scope: str) -> GuardrailDecision:
        decision = self._scanner.scan(content)
        if not decision.allow and decision.reason == "secret_detected":
            if scope == "shared":
                return GuardrailDecision(
                    False,
                    "secret_blocked_for_shared_memory",
                    escalation="block",
                    safe_fallback="Store a redacted summary in isolated scope.",
                    sensitive=True,
                )
            return GuardrailDecision(
                True,
                "secret_allowed_mark_sensitive",
                escalation="human_review_queue",
                sensitive=True,
            )
        return decision

    def sensitive_expiry(self) -> datetime:
        return datetime.now(tz=timezone.utc) + timedelta(days=7)


class RedactionService:
    def redact(self, content: str) -> str:
        masked = re.sub(r"(?i)(password\s*[:=]\s*)\S+", r"\1[REDACTED]", content)
        masked = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)\S+", r"\1[REDACTED]", masked)
        masked = re.sub(r"sk-[A-Za-z0-9]{20,}", "[REDACTED_SECRET]", masked)
        masked = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", masked)
        return masked
