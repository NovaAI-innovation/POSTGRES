#!/usr/bin/env bash
set -euo pipefail

POLICY_FILE="${POLICY_FILE:-}"
AGENT_ID="${AGENT_ID:-}"
TENANT_ID="${TENANT_ID:-}"
EVENT_JSON="${EVENT_JSON:-}"
EVENT_FILE="${EVENT_FILE:-}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
API_KEY="${API_KEY:-}"
DRY_RUN="${DRY_RUN:-false}"

require_value() {
  if [[ $# -lt 2 || -z "${2:-}" ]]; then
    echo "Missing value for $1" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --policy-file) require_value "$1" "${2:-}"; POLICY_FILE="$2"; shift 2 ;;
    --agent-id) require_value "$1" "${2:-}"; AGENT_ID="$2"; shift 2 ;;
    --tenant-id) require_value "$1" "${2:-}"; TENANT_ID="$2"; shift 2 ;;
    --event-json) require_value "$1" "${2:-}"; EVENT_JSON="$2"; shift 2 ;;
    --event-file) require_value "$1" "${2:-}"; EVENT_FILE="$2"; shift 2 ;;
    --base-url) require_value "$1" "${2:-}"; BASE_URL="$2"; shift 2 ;;
    --auth-token) require_value "$1" "${2:-}"; AUTH_TOKEN="$2"; shift 2 ;;
    --api-key) require_value "$1" "${2:-}"; API_KEY="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift 1 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$POLICY_FILE" ]]; then
  echo "--policy-file is required" >&2
  exit 1
fi
if [[ -z "$AGENT_ID" ]]; then
  echo "--agent-id is required" >&2
  exit 1
fi
if [[ -z "$TENANT_ID" ]]; then
  echo "--tenant-id is required" >&2
  exit 1
fi
if [[ -z "$EVENT_JSON" && -z "$EVENT_FILE" ]]; then
  echo "One of --event-json or --event-file is required" >&2
  exit 1
fi
if [[ -n "$EVENT_JSON" && -n "$EVENT_FILE" ]]; then
  echo "Use only one of --event-json or --event-file" >&2
  exit 1
fi
if [[ -z "$AUTH_TOKEN" && -z "$API_KEY" ]]; then
  echo "Either --auth-token or --api-key is required" >&2
  exit 1
fi

python - "$POLICY_FILE" "$AGENT_ID" "$TENANT_ID" "$EVENT_JSON" "$EVENT_FILE" "$BASE_URL" "$AUTH_TOKEN" "$API_KEY" "$DRY_RUN" <<'PY'
import hashlib
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

policy_file, agent_id, tenant_id, event_json, event_file, base_url, auth_token, api_key, dry_run_raw = sys.argv[1:]
dry_run = str(dry_run_raw).lower() == "true"


def read_json_file(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8-sig"))


def get_field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def get_rule(policy_obj: dict, rule_name: str):
    return get_field(get_field(policy_obj, "rules", {}), rule_name)


def get_confidence(event_obj: dict) -> float:
    value = get_field(event_obj, "confidence", None)
    if value is None:
        return 1.0
    return float(value)


def get_event_class(policy_obj: dict, event_obj: dict) -> str:
    event_type = get_field(event_obj, "event_type")
    if event_type:
        exact = get_rule(policy_obj, str(event_type))
        if exact is not None:
            return str(event_type)

    content = str(get_field(event_obj, "content", ""))
    for name, rule in get_field(policy_obj, "rules", {}).items():
        for pattern in get_field(rule, "detect_patterns", []):
            if re.search(str(pattern), content):
                return str(name)

    default_rule = get_field(policy_obj, "default_rule")
    if not default_rule:
        raise RuntimeError("Policy missing default_rule")
    return str(default_rule)


def test_sensitive(policy_obj: dict, content: str) -> bool:
    for pattern in get_field(policy_obj, "sensitive_patterns", []):
        if re.search(str(pattern), content):
            return True
    return False


def should_persist(policy_obj: dict, rule: dict, event_obj: dict, sensitive: bool) -> bool:
    handling = get_field(policy_obj, "sensitive_handling", {})
    if sensitive and not bool(get_field(handling, "persist_sensitive", False)):
        return False

    if not bool(get_field(rule, "enabled", False)):
        return False

    confidence = get_confidence(event_obj)
    min_confidence = float(get_field(rule, "min_confidence", 0))
    if confidence < min_confidence:
        return False

    scope = str(get_field(event_obj, "scope", ""))
    if scope == "shared" and not bool(get_field(policy_obj, "allow_shared_scope", False)):
        return False

    return True


def make_headers(request_id: str, action_id: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": request_id,
        "X-Action-Id": action_id,
        "X-Actor": "claude-code",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif api_key:
        headers["X-API-Key"] = api_key
        headers["X-Tenant-Id"] = tenant_id
        headers["X-Agent-Id"] = agent_id
    else:
        raise RuntimeError("Either --auth-token or --api-key is required")
    return headers


def post_json(path: str, payload: dict, headers: dict):
    url = base_url.rstrip("/") + path
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = Request(url=url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error calling {path}: {exc}") from exc

    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_response": raw}


def write_action_log(stage: str, status: str, message: str, request_id: str, action_id: str, headers: dict, event_class: str):
    log_payload = {
        "scope": "isolated",
        "owner_agent_id": agent_id,
        "raw_content": f"action_log stage={stage} status={status} message={message}",
        "source_ref": f"gateway:{action_id}",
        "metadata": {
            "log_type": "action_log",
            "stage": stage,
            "status": status,
            "request_id": request_id,
            "action_id": action_id,
            "event_class": event_class,
            "actor": "claude-code",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    post_json("/memory/ingest", log_payload, headers)


policy = read_json_file(policy_file)
if event_json:
    event = json.loads(event_json)
else:
    event = read_json_file(event_file)

request_id = str(uuid.uuid4())
action_id = str(uuid.uuid4())
headers = make_headers(request_id, action_id)
event_class = get_event_class(policy, event)
rule = get_rule(policy, event_class)
if rule is None:
    raise RuntimeError(f"No policy rule found for event class '{event_class}'")

content = str(get_field(event, "content", ""))
sensitive = test_sensitive(policy, content)
persist = should_persist(policy, rule, event, sensitive)
started = time.time()

if not dry_run:
    write_action_log("start", "running", "event_received", request_id, action_id, headers, event_class)

result = {
    "request_id": request_id,
    "action_id": action_id,
    "agent_id": agent_id,
    "tenant_id": tenant_id,
    "event_class": event_class,
    "persisted": False,
    "sensitive": sensitive,
    "reason": "skipped_by_policy",
    "dry_run": dry_run,
}

error = None
try:
    if persist:
        event_scope = get_field(event, "scope")
        scope = str(event_scope) if event_scope else str(get_field(policy, "default_scope", "isolated"))
        source_ref = get_field(event, "source_ref")
        payload = {
            "scope": scope,
            "owner_agent_id": agent_id,
            "raw_content": content,
            "source_ref": str(source_ref) if source_ref else f"event:{action_id}",
            "metadata": {
                "event_type": event_class,
                "confidence": get_confidence(event),
                "request_id": request_id,
                "action_id": action_id,
                "actor": "claude-code",
                "policy_name": str(get_field(policy, "policy_name", "")),
                "policy_ver": str(get_field(policy, "policy_version", "")),
                "tags": list(get_field(rule, "tags", [])),
                "input_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            },
        }

        handling = get_field(policy, "sensitive_handling", {})
        if sensitive and bool(get_field(handling, "mark_metadata_sensitive", False)):
            payload["metadata"]["sensitive"] = True

        group_id = get_field(event, "group_id")
        if group_id:
            payload["group_id"] = str(group_id)

        if not dry_run:
            api_response = post_json("/memory/ingest", payload, headers)
            inserted = bool(get_field(api_response, "inserted", False))
            result["persisted"] = inserted
            result["reason"] = "persisted" if inserted else str(get_field(api_response, "reason", "not_inserted"))
            result["api_response"] = api_response
        else:
            result["persisted"] = True
            result["reason"] = "dry_run_would_persist"
            result["payload_preview"] = payload

    result["status"] = "ok"
except Exception as exc:
    result["status"] = "error"
    result["error"] = str(exc)
    error = exc
finally:
    result["duration_ms"] = int((time.time() - started) * 1000)
    if not dry_run:
        final_status = "completed" if result.get("status") == "ok" else "failed"
        final_message = str(result.get("reason") or "error")
        try:
            write_action_log("end", final_status, final_message, request_id, action_id, headers, event_class)
        except Exception as exc:
            if error is None:
                result["status"] = "error"
                result["error"] = str(exc)
                error = exc

print(json.dumps(result, indent=2))
if error is not None:
    sys.exit(1)
PY
