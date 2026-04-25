from __future__ import annotations

from typing import Any

from app.identity.models import IdentityContext
from app.observability.logger import get_logger
from app.tools.service import ToolCallRecord


logger = get_logger("audit")


class AuditLogger:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def emit_auth_event(
        self,
        event: str,
        request_id: str,
        identity: IdentityContext | None = None,
        reason: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"event": event, "request_id": request_id}
        if identity:
            payload.update(
                {
                    "tenant_id": identity.tenant_id,
                    "agent_id": identity.agent_id,
                    "user_id": identity.user_id,
                    "service_client_id": identity.service_client_id,
                }
            )
        if reason:
            payload["reason"] = reason
        self._events.append(payload)
        logger.info("auth_audit", extra={"extra_payload": payload})

    def emit_policy_event(
        self,
        action: str,
        decision: str,
        reason: str,
        identity: IdentityContext,
        resource: str,
    ) -> None:
        payload = {
            "event": "policy_decision",
            "action": action,
            "decision": decision,
            "reason": reason,
            "resource": resource,
            "request_id": identity.request_id,
            "tenant_id": identity.tenant_id,
            "agent_id": identity.agent_id,
            "user_id": identity.user_id,
            "service_client_id": identity.service_client_id,
        }
        self._events.append(payload)
        logger.info("policy_decision", extra={"extra_payload": payload})

    def emit_tool_call(self, record: ToolCallRecord, request_id: str, tenant_id: str | None) -> None:
        payload = {
            "event": "tool_call",
            "request_id": request_id,
            "tenant_id": tenant_id,
            "agent_id": record.agent_id,
            "tool_name": record.tool_name,
            "input_hash": record.input_hash,
            "output_hash": record.output_hash,
            "duration_ms": record.duration_ms,
            "status": record.status,
            "approval_id": record.approval_id,
            "dry_run": record.dry_run,
            "error": record.error,
        }
        self._events.append(payload)
        logger.info("tool_call", extra={"extra_payload": payload})

    def emit_request_event(
        self,
        *,
        request_id: str,
        tenant_id: str | None,
        agent_id: str | None,
        trace_id: str,
        path: str,
        method: str,
        status_code: int,
        error: str | None = None,
    ) -> None:
        payload = {
            "event": "request",
            "request_id": request_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "trace_id": trace_id,
            "path": path,
            "method": method,
            "status_code": status_code,
            "error": error,
        }
        self._events.append(payload)
        logger.info("request", extra={"extra_payload": payload})

    def list_events(self, event_type: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        items = self._events
        if event_type:
            items = [e for e in items if e.get("event") == event_type]
        return items[-limit:]

    def emit_admin_action(
        self,
        *,
        request_id: str,
        tenant_id: str | None,
        actor: str | None,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "event": "admin_action",
            "request_id": request_id,
            "tenant_id": tenant_id,
            "actor": actor,
            "action": action,
            "payload": payload or {},
        }
        self._events.append(event)
        logger.info("admin_action", extra={"extra_payload": event})
