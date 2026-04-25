from __future__ import annotations

from dataclasses import dataclass

from app.agents.service import AgentOverrideStore
from app.groups.service import GroupPermissionStore
from app.identity.models import IdentityContext
from app.memory.models import MemoryEntry
from app.observability.audit import AuditLogger


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    def __init__(
        self,
        group_permissions: GroupPermissionStore,
        overrides: AgentOverrideStore,
        audit_logger: AuditLogger,
    ) -> None:
        self._groups = group_permissions
        self._overrides = overrides
        self._audit = audit_logger

    def _log(self, identity: IdentityContext, action: str, decision: PolicyDecision, resource: str) -> None:
        self._audit.emit_policy_event(
            action=action,
            decision="allow" if decision.allowed else "deny",
            reason=decision.reason,
            identity=identity,
            resource=resource,
        )

    def _override_check(self, identity: IdentityContext, action: str) -> PolicyDecision | None:
        override = self._overrides.get_override(identity.agent_id)
        if override == "blocked":
            return PolicyDecision(False, "agent_blocked")
        if override == "elevated":
            return PolicyDecision(True, "agent_elevated")
        if override == "read_only" and action in {"write_memory", "admin_group", "call_tool", "delegate"}:
            return PolicyDecision(False, "agent_read_only")
        return None

    def can_read_memory(self, identity: IdentityContext, memory: MemoryEntry) -> PolicyDecision:
        action = "read_memory"
        if not identity.is_authenticated:
            decision = PolicyDecision(False, "unauthenticated")
            self._log(identity, action, decision, memory.id)
            return decision
        override = self._override_check(identity, action)
        if override:
            self._log(identity, action, override, memory.id)
            return override
        if identity.tenant_id != memory.tenant_id:
            decision = PolicyDecision(False, "tenant_mismatch")
        elif memory.scope == "isolated":
            decision = PolicyDecision(identity.agent_id == memory.owner_agent_id, "isolated_owner_only")
        elif memory.scope in {"scoped", "shared"}:
            perms = self._groups.get_permissions(memory.group_id, identity.agent_id)
            decision = PolicyDecision(perms.can_read, "group_read_required")
        else:
            decision = PolicyDecision(False, "invalid_scope")
        self._log(identity, action, decision, memory.id)
        return decision

    def can_write_memory(
        self,
        identity: IdentityContext,
        scope: str,
        group_id: str | None,
        owner_agent_id: str,
    ) -> PolicyDecision:
        action = "write_memory"
        override = self._override_check(identity, action)
        if override:
            self._log(identity, action, override, f"scope:{scope}")
            return override
        if not identity.is_authenticated:
            decision = PolicyDecision(False, "unauthenticated")
        elif identity.tenant_id is None:
            decision = PolicyDecision(False, "missing_tenant")
        elif scope == "isolated":
            decision = PolicyDecision(identity.agent_id == owner_agent_id, "isolated_owner_only")
        elif scope in {"scoped", "shared"}:
            perms = self._groups.get_permissions(group_id, identity.agent_id)
            decision = PolicyDecision(perms.can_write, "group_write_required")
        else:
            decision = PolicyDecision(False, "deny_by_default")
        self._log(identity, action, decision, f"scope:{scope}")
        return decision

    def can_admin_group(self, identity: IdentityContext, group_id: str) -> PolicyDecision:
        action = "admin_group"
        override = self._override_check(identity, action)
        if override:
            self._log(identity, action, override, group_id)
            return override
        perms = self._groups.get_permissions(group_id, identity.agent_id)
        decision = PolicyDecision(perms.can_admin, "group_admin_required")
        self._log(identity, action, decision, group_id)
        return decision

    def can_call_tool(
        self, identity: IdentityContext, tool_name: str, allowed_tools: set[str] | None = None
    ) -> PolicyDecision:
        action = "call_tool"
        override = self._override_check(identity, action)
        if override:
            self._log(identity, action, override, tool_name)
            return override
        if allowed_tools is not None and tool_name not in allowed_tools:
            decision = PolicyDecision(False, "tool_not_allowed")
        else:
            decision = PolicyDecision(True, "tool_allowed")
        self._log(identity, action, decision, tool_name)
        return decision

    def can_delegate_to(
        self, identity: IdentityContext, target_agent_id: str, allowed_targets: set[str] | None = None
    ) -> PolicyDecision:
        action = "delegate"
        override = self._override_check(identity, action)
        if override:
            self._log(identity, action, override, target_agent_id)
            return override
        if allowed_targets is not None and target_agent_id not in allowed_targets:
            decision = PolicyDecision(False, "delegation_not_allowed")
        else:
            decision = PolicyDecision(True, "delegation_allowed")
        self._log(identity, action, decision, target_agent_id)
        return decision
