# Gateway

Single-wrapper gateway model: one full wrapper per agent.

## Canonical wrappers

- `scripts/gateway/agents/claude.sh`
- `scripts/gateway/agents/codex.sh`
- `scripts/gateway/agents/agent-zero.sh`

Each wrapper supports both modes:

- `direct`: policy evaluation + direct API calls to target service.
- `remote`: calls central gateway `POST /gateway/execute`.

## Central gateway

```powershell
python .\scripts\gateway\central_gateway.py --host 0.0.0.0 --port 8787 --target-base-url http://127.0.0.1:8000
```

Environment overrides:

- `GATEWAY_BIND_HOST`
- `GATEWAY_BIND_PORT`
- `GATEWAY_TARGET_BASE_URL`
- `GATEWAY_AGENT_PROFILES`

## Required auth variables (direct mode)

At least one per agent:

- `CLAUDE_GATEWAY_TOKEN` or `CLAUDE_GATEWAY_API_KEY`
- `CODEX_GATEWAY_TOKEN` or `CODEX_GATEWAY_API_KEY`
- `AGENT0_GATEWAY_TOKEN` or `AGENT0_GATEWAY_API_KEY`

## Codex project scope

- Codex defaults to `scoped` memory writes.
- Default project group id is `project-codex`.
- Override via env `CODEX_PROJECT_SCOPE_GROUP_ID` or wrapper arg `--project-scope-id`.

## Usage examples

Direct memory event (Codex):

```bash
sh ./scripts/gateway/agents/codex.sh \
  --mode direct \
  --operation memory_event \
  --event-json '{"event_type":"task_outcome","content":"Migration completed","confidence":0.92}' \
  --project-scope-id "project-codex" \
  --base-url "http://127.0.0.1:8000"
```

Remote API proxy (Claude):

```bash
sh ./scripts/gateway/agents/claude.sh \
  --mode remote \
  --operation api_proxy \
  --method POST \
  --path "/tasks" \
  --payload-json '{"summary":"integration task"}' \
  --gateway-url "http://your-vps:8787"
```

## `POST /gateway/execute` payload

`memory_event`:

```json
{
  "operation": "memory_event",
  "agent_id": "Claude",
  "tenant_id": "Casey",
  "event": {
    "event_type": "task_outcome",
    "content": "Migration completed",
    "confidence": 0.92,
    "scope": "isolated"
  }
}
```

`api_proxy`:

```json
{
  "operation": "api_proxy",
  "agent_id": "Codex",
  "tenant_id": "Casey",
  "method": "POST",
  "path": "/tasks",
  "payload": {
    "summary": "integration task"
  }
}
```
