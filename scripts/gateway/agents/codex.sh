#!/usr/bin/env bash
set -euo pipefail

AGENT_ID="Codex"
TENANT_ID="${TENANT_ID:-Casey}"
MODE="${MODE:-direct}"
OPERATION="${OPERATION:-memory_event}"
METHOD="${METHOD:-POST}"
PATH_ARG="${PATH_ARG:-/memory/ingest}"
EVENT_JSON="${EVENT_JSON:-}"
EVENT_FILE="${EVENT_FILE:-}"
PAYLOAD_JSON="${PAYLOAD_JSON:-}"
PAYLOAD_FILE="${PAYLOAD_FILE:-}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
GATEWAY_URL="${GATEWAY_URL:-https://agent-mesh-postgres.srv1300572.hstgr.cloud}"
POLICY_FILE="${POLICY_FILE:-$(cd "$(dirname "$0")/.." && pwd)/policies/Codex.json}"
AGENT_PROFILES_FILE="${AGENT_PROFILES_FILE:-$(cd "$(dirname "$0")/.." && pwd)/policies/agent_profiles.json}"
AUTH_TOKEN="${AUTH_TOKEN:-${CODEX_GATEWAY_TOKEN:-}}"
API_KEY="${API_KEY:-${CODEX_GATEWAY_API_KEY:-}}"
PROJECT_SCOPE_ID="${PROJECT_SCOPE_ID:-${CODEX_PROJECT_SCOPE_GROUP_ID:-project-codex}}"
DRY_RUN="${DRY_RUN:-false}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "python3 or python is required" >&2
    exit 1
  fi
fi

require_value() {
  if [[ $# -lt 2 || -z "${2:-}" ]]; then
    echo "Missing value for $1" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) require_value "$1" "${2:-}"; MODE="$2"; shift 2 ;;
    --operation) require_value "$1" "${2:-}"; OPERATION="$2"; shift 2 ;;
    --tenant-id) require_value "$1" "${2:-}"; TENANT_ID="$2"; shift 2 ;;
    --event-json) require_value "$1" "${2:-}"; EVENT_JSON="$2"; shift 2 ;;
    --event-file) require_value "$1" "${2:-}"; EVENT_FILE="$2"; shift 2 ;;
    --payload-json) require_value "$1" "${2:-}"; PAYLOAD_JSON="$2"; shift 2 ;;
    --payload-file) require_value "$1" "${2:-}"; PAYLOAD_FILE="$2"; shift 2 ;;
    --method) require_value "$1" "${2:-}"; METHOD="$2"; shift 2 ;;
    --path) require_value "$1" "${2:-}"; PATH_ARG="$2"; shift 2 ;;
    --base-url) require_value "$1" "${2:-}"; BASE_URL="$2"; shift 2 ;;
    --gateway-url) require_value "$1" "${2:-}"; GATEWAY_URL="$2"; shift 2 ;;
    --policy-file) require_value "$1" "${2:-}"; POLICY_FILE="$2"; shift 2 ;;
    --agent-profiles-file) require_value "$1" "${2:-}"; AGENT_PROFILES_FILE="$2"; shift 2 ;;
    --auth-token) require_value "$1" "${2:-}"; AUTH_TOKEN="$2"; shift 2 ;;
    --api-key) require_value "$1" "${2:-}"; API_KEY="$2"; shift 2 ;;
    --project-scope-id) require_value "$1" "${2:-}"; PROJECT_SCOPE_ID="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift 1 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ "$MODE" != "direct" && "$MODE" != "remote" ]]; then
  echo "--mode must be 'direct' or 'remote'" >&2
  exit 1
fi
if [[ "$OPERATION" != "memory_event" && "$OPERATION" != "api_proxy" ]]; then
  echo "--operation must be 'memory_event' or 'api_proxy'" >&2
  exit 1
fi
if [[ "$OPERATION" == "memory_event" && -z "$EVENT_JSON" && -z "$EVENT_FILE" ]]; then
  echo "memory_event requires --event-json or --event-file" >&2
  exit 1
fi
if [[ "$OPERATION" == "memory_event" && -n "$EVENT_JSON" && -n "$EVENT_FILE" ]]; then
  echo "Use only one of --event-json or --event-file" >&2
  exit 1
fi
if [[ "$OPERATION" == "api_proxy" && "${PATH_ARG:0:1}" != "/" ]]; then
  echo "api_proxy --path must start with '/'" >&2
  exit 1
fi

"$PYTHON_BIN" - "$AGENT_ID" "$TENANT_ID" "$MODE" "$OPERATION" "$METHOD" "$PATH_ARG" "$EVENT_JSON" "$EVENT_FILE" "$PAYLOAD_JSON" "$PAYLOAD_FILE" "$BASE_URL" "$GATEWAY_URL" "$POLICY_FILE" "$AGENT_PROFILES_FILE" "$AUTH_TOKEN" "$API_KEY" "$PROJECT_SCOPE_ID" "$DRY_RUN" <<'PY'
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

(
    agent_id,
    tenant_id,
    mode,
    operation,
    method,
    path_arg,
    event_json,
    event_file,
    payload_json,
    payload_file,
    base_url,
    gateway_url,
    policy_file,
    agent_profiles_file,
    auth_token,
    api_key,
    project_scope_id,
    dry_run_raw,
) = sys.argv[1:]

dry_run = str(dry_run_raw).lower() == "true"


def read_json_file(path: str):
    p = Path(path)
    if not p.is_file():
        raise RuntimeError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8-sig"))


def parse_optional(text: str, file_path: str):
    if text:
        return json.loads(text)
    if file_path:
        return read_json_file(file_path)
    return None


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


def make_direct_headers(request_id: str, action_id: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": request_id,
        "X-Action-Id": action_id,
        "X-Actor": agent_id,
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif api_key:
        headers["X-API-Key"] = api_key
        headers["X-Tenant-Id"] = tenant_id
        headers["X-Agent-Id"] = agent_id
    else:
        raise RuntimeError("Direct mode requires auth token or api key")
    return headers


def post_json(url: str, payload: dict, headers: dict, http_method: str = "POST"):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = Request(url=url, data=body, headers=headers, method=http_method.upper())
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error calling {url}: {exc}") from exc

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
            "actor": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    post_json(base_url.rstrip("/") + "/memory/ingest", log_payload, headers, "POST")


event = parse_optional(event_json, event_file)
payload = parse_optional(payload_json, payload_file)

if operation == "memory_event" and isinstance(event, dict):
    event_scope = str(get_field(event, "scope", "")).strip().lower()
    if not event_scope:
        event["scope"] = "scoped"
    if str(get_field(event, "scope", "")).lower() == "scoped" and not get_field(event, "group_id"):
        event["group_id"] = project_scope_id

request_id = str(uuid.uuid4())
action_id = str(uuid.uuid4())
started = time.time()

result = {
    "request_id": request_id,
    "action_id": action_id,
    "mode": mode,
    "operation": operation,
    "agent_id": agent_id,
    "tenant_id": tenant_id,
    "dry_run": dry_run,
}

error = None
headers = None

try:
    if mode == "remote":
        body = {
            "operation": operation,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "dry_run": dry_run,
        }
        if operation == "memory_event":
            if not isinstance(event, dict):
                raise RuntimeError("memory_event requires event object")
            body["event"] = event
        else:
            body["method"] = method.upper()
            body["path"] = path_arg
            body["payload"] = payload if isinstance(payload, dict) else {}

        gateway_resp = post_json(gateway_url.rstrip("/") + "/gateway/execute", body, {"Content-Type": "application/json"}, "POST")
        result["status"] = "ok"
        result["gateway_response"] = gateway_resp
    else:
        policy = read_json_file(policy_file)
        profiles = read_json_file(agent_profiles_file)
        profile = get_field(get_field(profiles, "agents", {}), agent_id)
        if not isinstance(profile, dict):
            raise RuntimeError(f"Agent profile not found for '{agent_id}'")

        headers = make_direct_headers(request_id, action_id) if not dry_run else None
        event_class = get_event_class(policy, event) if operation == "memory_event" else "api_proxy"

        if not dry_run:
            write_action_log("start", "running", "received", request_id, action_id, headers, event_class)

        if operation == "memory_event":
            if not isinstance(event, dict):
                raise RuntimeError("memory_event requires event object")
            rule = get_rule(policy, event_class)
            if rule is None:
                raise RuntimeError(f"No policy rule found for event class '{event_class}'")

            content = str(get_field(event, "content", ""))
            sensitive = test_sensitive(policy, content)
            persist = should_persist(policy, rule, event, sensitive)

            result["event_class"] = event_class
            result["sensitive"] = sensitive
            result["persist"] = persist

            if persist:
                event_scope = get_field(event, "scope")
                scope = str(event_scope) if event_scope else str(get_field(policy, "default_scope", "isolated"))
                source_ref = get_field(event, "source_ref")
                direct_payload = {
                    "scope": scope,
                    "owner_agent_id": agent_id,
                    "raw_content": content,
                    "source_ref": str(source_ref) if source_ref else f"event:{action_id}",
                    "metadata": {
                        "event_type": event_class,
                        "confidence": get_confidence(event),
                        "request_id": request_id,
                        "action_id": action_id,
                        "actor": agent_id,
                        "policy_name": str(get_field(policy, "policy_name", "")),
                        "policy_ver": str(get_field(policy, "policy_version", "")),
                        "tags": list(get_field(rule, "tags", [])),
                        "input_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    },
                }

                handling = get_field(policy, "sensitive_handling", {})
                if sensitive and bool(get_field(handling, "mark_metadata_sensitive", False)):
                    direct_payload["metadata"]["sensitive"] = True

                group_id = get_field(event, "group_id")
                if group_id:
                    direct_payload["group_id"] = str(group_id)

                if dry_run:
                    result["reason"] = "dry_run_would_persist"
                    result["result"] = {"status": "dry_run", "payload_preview": direct_payload}
                else:
                    api_resp = post_json(base_url.rstrip("/") + "/memory/ingest", direct_payload, headers, "POST")
                    inserted = bool(get_field(api_resp, "inserted", False))
                    result["reason"] = "persisted" if inserted else str(get_field(api_resp, "reason", "not_inserted"))
                    result["target_response"] = api_resp
            else:
                result["reason"] = "skipped_by_policy"
                result["result"] = {"status": "skipped", "reason": "skipped_by_policy"}

        else:
            method_up = method.upper()

            if dry_run:
                result["reason"] = "api_proxy_dry_run"
                result["result"] = {"status": "dry_run", "method": method_up, "path": path_arg}
            else:
                proxy_resp = post_json(base_url.rstrip("/") + path_arg, payload if isinstance(payload, dict) else {}, headers, method_up)
                result["reason"] = "api_proxy_executed"
                result["target_response"] = proxy_resp

        result["status"] = "ok"
except Exception as exc:
    result["status"] = "error"
    result["error"] = str(exc)
    error = exc
finally:
    result["duration_ms"] = int((time.time() - started) * 1000)
    if mode == "direct" and not dry_run and headers is not None:
        final_status = "failed" if error is not None else "completed"
        final_message = str(get_field(result, "reason", "error" if error is not None else "ok"))
        final_event_class = str(get_field(result, "event_class", "api_proxy"))
        try:
            write_action_log("end", final_status, final_message, request_id, action_id, headers, final_event_class)
        except Exception as log_exc:
            if error is None:
                result["status"] = "error"
                result["error"] = str(log_exc)
                error = log_exc

print(json.dumps(result, indent=2))
if error is not None:
    sys.exit(1)
PY
