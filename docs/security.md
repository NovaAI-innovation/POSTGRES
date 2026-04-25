# Security Notes (Phases 0-2)

- Agents interact through the API only (`/memory`, `/tools`, `/health`).
- Agent tokens and API keys never include database credentials.
- Authentication middleware rejects unauthorized traffic before business logic.
- Secret values are scrubbed from logs by key name.
- Key rotation uses `AUTH_SECRET_CURRENT` and `AUTH_SECRET_PREVIOUS`.
