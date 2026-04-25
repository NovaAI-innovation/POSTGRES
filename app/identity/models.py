from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdentityContext:
    request_id: str
    principal: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    service_client_id: str | None = None
    is_authenticated: bool = False

    @property
    def subject_id(self) -> str | None:
        return self.agent_id or self.user_id or self.service_client_id
