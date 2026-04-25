from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.auth.tokens import validate_signed_token
from app.config import Settings
from app.identity.models import IdentityContext
from app.observability.audit import AuditLogger


@dataclass(frozen=True)
class AuthError(Exception):
    status_code: int
    message: str


class AuthMiddleware:
    def __init__(self, settings: Settings, audit: AuditLogger) -> None:
        self._settings = settings
        self._audit = audit

    def request_id(self, headers: dict[str, str]) -> str:
        return headers.get("x-request-id") or str(uuid.uuid4())

    def authenticate(self, headers: dict[str, str]) -> IdentityContext:
        request_id = self.request_id(headers)
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            secrets = [self._settings.auth_secret_current]
            if self._settings.auth_secret_previous:
                secrets.append(self._settings.auth_secret_previous)
            result = validate_signed_token(token, secrets)
            if not result.ok or not result.payload:
                reason = result.error or "invalid_token"
                event = "expired_token" if reason == "expired_token" else "invalid_identity"
                self._audit.emit_auth_event(event=event, request_id=request_id, reason=reason)
                raise AuthError(status_code=401, message="Unauthorized")
            payload = result.payload
            tenant_id = payload.get("tenant_id")
            if not isinstance(tenant_id, str) or not tenant_id:
                self._audit.emit_auth_event(
                    event="invalid_identity", request_id=request_id, reason="missing_tenant"
                )
                raise AuthError(status_code=401, message="Unauthorized")
            identity = IdentityContext(
                request_id=request_id,
                principal="token",
                tenant_id=tenant_id,
                user_id=payload.get("user_id"),
                agent_id=payload.get("agent_id"),
                service_client_id=payload.get("service_client_id"),
                is_authenticated=True,
            )
            if not identity.subject_id:
                self._audit.emit_auth_event(
                    event="invalid_identity", request_id=request_id, reason="missing_subject"
                )
                raise AuthError(status_code=401, message="Unauthorized")
            self._audit.emit_auth_event(event="auth_success", request_id=request_id, identity=identity)
            return identity

        api_key = headers.get("x-api-key")
        if api_key and self._settings.allow_dev_api_key and api_key in self._settings.internal_api_keys:
            identity = IdentityContext(
                request_id=request_id,
                principal="api_key",
                tenant_id=headers.get("x-tenant-id"),
                agent_id=headers.get("x-agent-id"),
                service_client_id="internal-api-key",
                is_authenticated=True,
            )
            if not identity.tenant_id or not identity.subject_id:
                self._audit.emit_auth_event(
                    event="invalid_identity", request_id=request_id, reason="api_key_missing_identity"
                )
                raise AuthError(status_code=401, message="Unauthorized")
            self._audit.emit_auth_event(event="auth_success", request_id=request_id, identity=identity)
            return identity

        self._audit.emit_auth_event(event="auth_failure", request_id=request_id, reason="missing_credentials")
        raise AuthError(status_code=401, message="Unauthorized")
