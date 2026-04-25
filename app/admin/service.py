from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.identity.models import IdentityContext


@dataclass
class EmergencyState:
    paused: bool = False
    block_shared_memory_writes: bool = False


class AdminAuthorizationError(Exception):
    pass


class AdminController:
    def __init__(self) -> None:
        self.emergency = EmergencyState()
        self.disabled_tool_classes: set[str] = set()
        self.revoked_subjects: set[str] = set()
        self.admin_events: list[dict[str, Any]] = []

    def ensure_admin(self, identity: IdentityContext) -> None:
        user_admin = bool(identity.user_id and identity.user_id.startswith("admin"))
        service_admin = identity.service_client_id in {"internal-api-key", "ops-service"}
        if not (user_admin or service_admin):
            raise AdminAuthorizationError("admin_role_required")

    def audit(self, identity: IdentityContext, action: str, payload: dict[str, Any] | None = None) -> None:
        self.admin_events.append(
            {
                "request_id": identity.request_id,
                "tenant_id": identity.tenant_id,
                "actor": identity.subject_id,
                "action": action,
                "payload": payload or {},
            }
        )

    def render_console_html(self) -> str:
        return """<!doctype html>
<html>
<head><title>Operator Console</title></head>
<body>
  <h1>Operator Console</h1>
  <ul>
    <li>Agents</li>
    <li>Groups</li>
    <li>Permissions</li>
    <li>Memory Search / Detail</li>
    <li>Tool Calls</li>
    <li>Tasks</li>
    <li>Approvals</li>
    <li>Audit Events</li>
  </ul>
</body>
</html>"""
