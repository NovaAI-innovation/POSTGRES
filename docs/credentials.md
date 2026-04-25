# Credential Issuance Process

## Signed service token

Use `app.auth.credentials.issue_service_token(settings, tenant_id, service_client_id)` to issue a short-lived signed token.

## Signed agent token

Use `app.auth.credentials.issue_agent_token(settings, tenant_id, agent_id, user_id=None)` to issue a short-lived signed token.

## Internal development API key

- Enabled only when `APP_ENV != production`.
- API keys are loaded from `INTERNAL_API_KEYS`.
- Requests must include `X-API-Key`, `X-Tenant-Id`, and `X-Agent-Id`.
