# Gateway

Single-wrapper gateway model: one full wrapper per agent.

## Canonical wrappers

- `scripts/gateway/agents/claude.ps1` / `scripts/gateway/agents/claude.sh`
- `scripts/gateway/agents/codex.ps1` / `scripts/gateway/agents/codex.sh`
- `scripts/gateway/agents/agent-zero.ps1` / `scripts/gateway/agents/agent-zero.sh`

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

## Usage examples

Direct memory event (Codex):

```powershell
.\scripts\gateway\agents\codex.ps1 -Mode direct -Operation memory_event -EventJson '{"event_type":"task_outcome","content":"Migration completed","confidence":0.92,"scope":"isolated"}' -BaseUrl http://127.0.0.1:8000
```

Remote API proxy (Claude):

```powershell
.\scripts\gateway\agents\claude.ps1 -Mode remote -Operation api_proxy -Method POST -Path "/tasks" -PayloadJson '{"summary":"integration task"}' -GatewayUrl "http://your-vps:8787"
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