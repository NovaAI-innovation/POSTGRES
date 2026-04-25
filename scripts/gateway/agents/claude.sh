#!/usr/bin/env bash
set -euo pipefail

AGENT_ID="Claude"
TENANT_ID="${TENANT_ID:-Casey}"
GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8787}"
OPERATION="${OPERATION:-memory_event}"
METHOD="${METHOD:-POST}"
PATH_ARG="${PATH_ARG:-/memory/ingest}"
EVENT_JSON="${EVENT_JSON:-}"
PAYLOAD_JSON="${PAYLOAD_JSON:-{}}"
DRY_RUN="${DRY_RUN:-false}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --operation) OPERATION="$2"; shift 2 ;;
    --event-json) EVENT_JSON="$2"; shift 2 ;;
    --payload-json) PAYLOAD_JSON="$2"; shift 2 ;;
    --method) METHOD="$2"; shift 2 ;;
    --path) PATH_ARG="$2"; shift 2 ;;
    --gateway-url) GATEWAY_URL="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift 1 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

python - "$AGENT_ID" "$TENANT_ID" "$GATEWAY_URL" "$OPERATION" "$METHOD" "$PATH_ARG" "$EVENT_JSON" "$PAYLOAD_JSON" "$DRY_RUN" <<'PY'
import json
import sys
import urllib.request

agent_id, tenant_id, gateway_url, operation, method, path_arg, event_json, payload_json, dry_run_raw = sys.argv[1:]
dry_run = dry_run_raw.lower() == "true"

body = {
    "operation": operation,
    "agent_id": agent_id,
    "tenant_id": tenant_id,
    "dry_run": dry_run,
}

if operation == "memory_event":
    if not event_json:
        raise SystemExit("memory_event requires --event-json")
    body["event"] = json.loads(event_json)
elif operation == "api_proxy":
    body["method"] = method.upper()
    body["path"] = path_arg
    body["payload"] = json.loads(payload_json) if payload_json else {}
else:
    raise SystemExit(f"unsupported operation: {operation}")

req = urllib.request.Request(
    url=gateway_url.rstrip("/") + "/gateway/execute",
    data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    raw = resp.read().decode("utf-8")
    try:
        parsed = json.loads(raw)
        print(json.dumps(parsed, indent=2))
    except Exception:
        print(raw)
PY
