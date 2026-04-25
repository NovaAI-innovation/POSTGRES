from __future__ import annotations

import secrets

from app.auth.tokens import issue_signed_token
from app.config import Settings


def issue_agent_token(settings: Settings, tenant_id: str, agent_id: str, user_id: str | None = None) -> str:
    claims = {"tenant_id": tenant_id, "agent_id": agent_id}
    if user_id:
        claims["user_id"] = user_id
    return issue_signed_token(claims, settings.auth_secret_current)


def issue_service_token(settings: Settings, tenant_id: str, service_client_id: str) -> str:
    claims = {"tenant_id": tenant_id, "service_client_id": service_client_id}
    return issue_signed_token(claims, settings.auth_secret_current)


def issue_internal_api_key() -> str:
    return secrets.token_urlsafe(32)
