from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    permissions_required: tuple[str, ...]
    timeout_seconds: int
    rate_limit_per_minute: int
    destructive: bool = False
    approval_category: str | None = None
    handler: ToolHandler | None = None


@dataclass
class ApprovalRecord:
    id: str
    tool_name: str
    requested_by: str
    reason: str
    status: str = "pending"
    approved_by: str | None = None


@dataclass
class ToolCallRecord:
    tool_name: str
    agent_id: str | None
    input_hash: str
    output_hash: str | None
    duration_ms: int
    status: str
    approval_id: str | None
    dry_run: bool
    error: str | None = None
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._tools)


class ToolApprovalStore:
    def __init__(self) -> None:
        self._records: dict[str, ApprovalRecord] = {}

    def request(self, tool_name: str, requested_by: str, reason: str) -> ApprovalRecord:
        record = ApprovalRecord(id=str(uuid.uuid4()), tool_name=tool_name, requested_by=requested_by, reason=reason)
        self._records[record.id] = record
        return record

    def get(self, approval_id: str) -> ApprovalRecord | None:
        return self._records.get(approval_id)

    def approve(self, approval_id: str, approved_by: str) -> ApprovalRecord | None:
        record = self._records.get(approval_id)
        if not record:
            return None
        record.status = "approved"
        record.approved_by = approved_by
        return record

    def reject(self, approval_id: str, approved_by: str) -> ApprovalRecord | None:
        record = self._records.get(approval_id)
        if not record:
            return None
        record.status = "rejected"
        record.approved_by = approved_by
        return record


class AgentToolAllowlistStore:
    def __init__(self) -> None:
        self._allowlists: dict[str, set[str]] = {}

    def set_allowlist(self, agent_id: str, tools: set[str]) -> None:
        self._allowlists[agent_id] = set(tools)

    def is_allowed(self, agent_id: str | None, tool_name: str) -> bool:
        if not agent_id:
            return False
        allowlist = self._allowlists.get(agent_id)
        if allowlist is None:
            return tool_name == "echo"
        return tool_name in allowlist


class ToolAuditLog:
    def __init__(self) -> None:
        self._records: list[ToolCallRecord] = []

    def append(self, record: ToolCallRecord) -> None:
        self._records.append(record)

    def list_recent(self, limit: int = 100) -> list[ToolCallRecord]:
        return self._records[-limit:]


class ToolRunner:
    def __init__(self, audit_log: ToolAuditLog, approvals: ToolApprovalStore) -> None:
        self._audit_log = audit_log
        self._approvals = approvals
        self._recent_calls: dict[tuple[str, str], list[float]] = {}

    def run(
        self,
        definition: ToolDefinition,
        payload: dict[str, Any],
        *,
        agent_id: str | None,
        dry_run: bool = False,
        approval_id: str | None = None,
        retries: int = 1,
    ) -> dict[str, Any]:
        started = time.monotonic()
        input_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        try:
            self._validate_input(definition, payload)
            self._check_rate_limit(definition, agent_id or "unknown")
            self._check_approval(definition, approval_id)
            if dry_run:
                output = {
                    "tool": definition.name,
                    "status": "dry_run",
                    "input_hash": input_hash,
                    "would_require_approval": bool(definition.destructive or definition.approval_category),
                }
                self._validate_output(definition, output)
                return self._record(
                    definition=definition,
                    agent_id=agent_id,
                    input_hash=input_hash,
                    output=output,
                    dry_run=True,
                    approval_id=approval_id,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )

            last_error: Exception | None = None
            for _ in range(max(1, retries)):
                try:
                    output = self._execute_with_timeout(definition, payload)
                    self._validate_output(definition, output)
                    return self._record(
                        definition=definition,
                        agent_id=agent_id,
                        input_hash=input_hash,
                        output=output,
                        dry_run=False,
                        approval_id=approval_id,
                        duration_ms=int((time.monotonic() - started) * 1000),
                    )
                except Exception as err:
                    last_error = err
            raise RuntimeError(str(last_error or "tool_execution_failed"))
        except Exception as err:
            duration = int((time.monotonic() - started) * 1000)
            self._audit_log.append(
                ToolCallRecord(
                    tool_name=definition.name,
                    agent_id=agent_id,
                    input_hash=input_hash,
                    output_hash=None,
                    duration_ms=duration,
                    status="error",
                    approval_id=approval_id,
                    dry_run=dry_run,
                    error=str(err),
                )
            )
            return {
                "tool": definition.name,
                "status": "error",
                "error": str(err),
                "input_hash": input_hash,
                "duration_ms": duration,
            }

    def _execute_with_timeout(self, definition: ToolDefinition, payload: dict[str, Any]) -> dict[str, Any]:
        start = time.monotonic()
        if definition.handler is None:
            output = {"tool": definition.name, "status": "ok", "echo": payload}
        else:
            output = definition.handler(payload)
        elapsed = time.monotonic() - start
        if elapsed > definition.timeout_seconds:
            raise RuntimeError("tool_timeout")
        return output

    def _validate_input(self, definition: ToolDefinition, payload: dict[str, Any]) -> None:
        for key, type_name in definition.input_schema.items():
            if key not in payload:
                raise RuntimeError(f"input_missing:{key}")
            if not _is_type(payload[key], type_name):
                raise RuntimeError(f"input_invalid_type:{key}")

    def _validate_output(self, definition: ToolDefinition, output: dict[str, Any]) -> None:
        if "status" not in output:
            raise RuntimeError("output_missing_status")
        for key, type_name in definition.output_schema.items():
            if key not in output:
                raise RuntimeError(f"output_missing:{key}")
            if not _is_type(output[key], type_name):
                raise RuntimeError(f"output_invalid_type:{key}")

    def _check_rate_limit(self, definition: ToolDefinition, agent_id: str) -> None:
        now = time.time()
        window_start = now - 60.0
        key = (agent_id, definition.name)
        calls = [ts for ts in self._recent_calls.get(key, []) if ts >= window_start]
        if len(calls) >= definition.rate_limit_per_minute:
            raise RuntimeError("tool_rate_limited")
        calls.append(now)
        self._recent_calls[key] = calls

    def _check_approval(self, definition: ToolDefinition, approval_id: str | None) -> None:
        requires_approval = bool(definition.destructive or definition.approval_category)
        if not requires_approval:
            return
        if not approval_id:
            raise RuntimeError("approval_required")
        record = self._approvals.get(approval_id)
        if not record or record.tool_name != definition.name or record.status != "approved":
            raise RuntimeError("approval_invalid")

    def _record(
        self,
        *,
        definition: ToolDefinition,
        agent_id: str | None,
        input_hash: str,
        output: dict[str, Any],
        duration_ms: int,
        dry_run: bool,
        approval_id: str | None,
    ) -> dict[str, Any]:
        output_hash = hashlib.sha256(json.dumps(output, sort_keys=True).encode("utf-8")).hexdigest()
        self._audit_log.append(
            ToolCallRecord(
                tool_name=definition.name,
                agent_id=agent_id,
                input_hash=input_hash,
                output_hash=output_hash,
                duration_ms=duration_ms,
                status=output.get("status", "ok"),
                approval_id=approval_id,
                dry_run=dry_run,
            )
        )
        output["input_hash"] = input_hash
        output["output_hash"] = output_hash
        output["duration_ms"] = duration_ms
        return output


def _is_type(value: Any, expected: str) -> bool:
    mapping = {
        "str": str,
        "int": int,
        "float": (float, int),
        "bool": bool,
        "dict": dict,
        "list": list,
    }
    t = mapping.get(expected)
    if t is None:
        return True
    return isinstance(value, t)
