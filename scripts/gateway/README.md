# Gateway

Central gateway model for remote multi-agent usage.

## Components

- `central_gateway.py`: HTTP service to run on VPS.
- `policies/*.json`: event policies and per-agent profiles.
- `core.ps1`: local direct mode script for PowerShell.
- `core.sh`: local direct mode script for bash/sh.
- `agents/*.ps1`: local direct mode wrappers.
- `.claude/scripts/claude_gateway.ps1` / `.claude/scripts/claude_gateway.sh`: Claude wrappers that call central gateway.
- `.codex/scripts/codex_gateway.ps1` / `.codex/scripts/codex_gateway.sh`: Codex wrappers that call central gateway.

## Central gateway start

```powershell
python .\scripts\gateway\central_gateway.py --host 0.0.0.0 --port 8787 --target-base-url http://127.0.0.1:8000
```

Environment overrides:

- `GATEWAY_BIND_HOST`
- `GATEWAY_BIND_PORT`
- `GATEWAY_TARGET_BASE_URL`
- `GATEWAY_AGENT_PROFILES`

## Required auth variables on the gateway host

At least one per agent profile:

- `CLAUDE_GATEWAY_TOKEN` or `CLAUDE_GATEWAY_API_KEY`
- `CODEX_GATEWAY_TOKEN` or `CODEX_GATEWAY_API_KEY`
- `AGENT0_GATEWAY_TOKEN` or `AGENT0_GATEWAY_API_KEY`

## Wrapper examples (remote mode)

Memory event via Claude wrapper:

```powershell
.\.claude\scripts\claude_gateway.ps1 -Operation memory_event -EventJson '{"content":"Task completed","confidence":0.91}' -GatewayUrl "http://your-vps:8787"
```

API proxy via Codex wrapper:

```powershell
.\.codex\scripts\codex_gateway.ps1 -Operation api_proxy -Method POST -Path "/tasks" -PayloadJson '{"summary":"integration task","idempotency_key":"k1"}' -GatewayUrl "http://your-vps:8787"
```

## Local direct mode via `core.sh`

```bash
sh ./scripts/gateway/core.sh \
  --policy-file ./scripts/gateway/policies/Claude.json \
  --agent-id Claude \
  --tenant-id Casey \
  --event-json '{"event_type":"task_outcome","content":"Migration completed","confidence":0.92,"scope":"isolated"}' \
  --base-url http://127.0.0.1:8000 \
  --auth-token "$CLAUDE_GATEWAY_TOKEN" \
  --dry-run
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

## Notes

- Every operation emits start/end action logs through `/memory/ingest`.
- Allowed methods and endpoint prefixes are controlled by `policies/agent_profiles.json`.
- Event-class persistence rules are controlled by each policy file (`Claude.json`, `Agent-0.json`, `Codex.json`).
