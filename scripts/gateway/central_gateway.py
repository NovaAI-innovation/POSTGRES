from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[2]
GATEWAY_DIR = pathlib.Path(__file__).resolve().parent
POLICY_DIR = GATEWAY_DIR / "policies"
DEFAULT_AGENT_PROFILES = POLICY_DIR / "agent_profiles.json"


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _json_loads(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_event(policy: dict[str, Any], event: dict[str, Any]) -> str:
    rules: dict[str, Any] = policy.get("rules", {})
    explicit = event.get("event_type")
    if isinstance(explicit, str) and explicit in rules:
        return explicit

    content = str(event.get("content", ""))
    for rule_name, rule in rules.items():
        patterns = rule.get("detect_patterns", [])
        for pattern in patterns:
            if re.search(str(pattern), content):
                return str(rule_name)
    return str(policy.get("default_rule", "message"))


def is_sensitive(policy: dict[str, Any], content: str) -> bool:
    for pattern in policy.get("sensitive_patterns", []):
        if re.search(str(pattern), content):
            return True
    return False


def should_persist_event(
    policy: dict[str, Any],
    event: dict[str, Any],
) -> tuple[bool, str, str, bool]:
    event_class = classify_event(policy, event)
    rules: dict[str, Any] = policy.get("rules", {})
    rule = rules.get(event_class)
    if not isinstance(rule, dict):
        return False, "missing_rule", event_class, False

    content = str(event.get("content", ""))
    sensitive = is_sensitive(policy, content)
    if sensitive and not bool(policy.get("sensitive_handling", {}).get("persist_sensitive", False)):
        return False, "sensitive_blocked", event_class, True

    if not bool(rule.get("enabled", False)):
        return False, "rule_disabled", event_class, sensitive

    confidence = float(event.get("confidence", 1.0))
    if confidence < float(rule.get("min_confidence", 1.0)):
        return False, "low_confidence", event_class, sensitive

    if str(event.get("scope", "")).lower() == "shared" and not bool(policy.get("allow_shared_scope", False)):
        return False, "shared_scope_blocked", event_class, sensitive

    return True, "persisted", event_class, sensitive


def path_allowed(profile: dict[str, Any], method: str, path: str) -> bool:
    method_up = method.upper()
    allowed_methods = {m.upper() for m in profile.get("allowed_methods", [])}
    if allowed_methods and method_up not in allowed_methods:
        return False

    allowed_prefixes = profile.get("allowed_path_prefixes", [])
    if not allowed_prefixes:
        return False
    return any(path.startswith(str(prefix)) for prefix in allowed_prefixes)


@dataclass(frozen=True)
class GatewayConfig:
    target_base_url: str
    bind_host: str
    bind_port: int
    agent_profiles_path: pathlib.Path

    @staticmethod
    def from_env(args: argparse.Namespace) -> "GatewayConfig":
        return GatewayConfig(
            target_base_url=os.getenv("GATEWAY_TARGET_BASE_URL", args.target_base_url).rstrip("/"),
            bind_host=os.getenv("GATEWAY_BIND_HOST", args.host),
            bind_port=int(os.getenv("GATEWAY_BIND_PORT", str(args.port))),
            agent_profiles_path=pathlib.Path(os.getenv("GATEWAY_AGENT_PROFILES", str(args.agent_profiles))).resolve(),
        )


class CentralGateway:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.agent_profiles = self._load_agent_profiles()

    def _load_agent_profiles(self) -> dict[str, Any]:
        parsed = _load_json(self.config.agent_profiles_path)
        profiles = parsed.get("agents")
        if not isinstance(profiles, dict):
            return {}
        return profiles

    def _profile(self, agent_id: str) -> dict[str, Any] | None:
        profile = self.agent_profiles.get(agent_id)
        return profile if isinstance(profile, dict) else None

    def _policy_for(self, profile: dict[str, Any]) -> dict[str, Any]:
        policy_rel = profile.get("policy_file")
        if not isinstance(policy_rel, str) or not policy_rel:
            raise RuntimeError("profile_missing_policy_file")
        policy_path = (POLICY_DIR / policy_rel).resolve()
        if POLICY_DIR.resolve() not in policy_path.parents:
            raise RuntimeError("policy_path_not_allowed")
        return _load_json(policy_path)

    def _build_target_headers(
        self,
        *,
        profile: dict[str, Any],
        tenant_id: str,
        agent_id: str,
        request_id: str,
        action_id: str,
    ) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
            "X-Action-Id": action_id,
            "X-Actor": agent_id,
        }
        token_env = str(profile.get("auth_token_env", ""))
        api_key_env = str(profile.get("api_key_env", ""))
        token = os.getenv(token_env) if token_env else None
        api_key = os.getenv(api_key_env) if api_key_env else None

        if token:
            headers["Authorization"] = f"Bearer {token}"
            return headers
        if api_key:
            headers["X-API-Key"] = api_key
            headers["X-Tenant-Id"] = tenant_id
            headers["X-Agent-Id"] = agent_id
            return headers
        raise RuntimeError("missing_upstream_auth")

    def _call_target(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> tuple[int, dict[str, Any] | str]:
        url = f"{self.config.target_base_url}{path}"
        body = _json_dumps(payload or {})
        req = urllib.request.Request(url=url, data=body, method=method.upper(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = raw
                return resp.status, parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            return exc.code, parsed

    def _log_action(
        self,
        *,
        stage: str,
        status: str,
        message: str,
        agent_id: str,
        tenant_id: str,
        event_class: str,
        request_id: str,
        action_id: str,
        headers: dict[str, str],
        operation: str,
    ) -> None:
        payload = {
            "scope": "isolated",
            "owner_agent_id": agent_id,
            "raw_content": f"action_log stage={stage} status={status} message={message}",
            "source_ref": f"gateway:{action_id}",
            "metadata": {
                "log_type": "action_log",
                "stage": stage,
                "status": status,
                "message": message,
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "request_id": request_id,
                "action_id": action_id,
                "event_class": event_class,
                "operation": operation,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }
        self._call_target(method="POST", path="/memory/ingest", payload=payload, headers=headers)

    def execute(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        request_id = str(uuid.uuid4())
        action_id = str(uuid.uuid4())
        started = time.monotonic()

        agent_id = str(body.get("agent_id", ""))
        tenant_id = str(body.get("tenant_id", ""))
        operation = str(body.get("operation", "memory_event"))
        dry_run = bool(body.get("dry_run", False))

        if not agent_id or not tenant_id:
            return 400, {"error": "agent_id and tenant_id are required"}
        profile = self._profile(agent_id)
        if not profile:
            return 403, {"error": "agent_profile_not_found", "agent_id": agent_id}

        expected_tenant = str(profile.get("tenant_id", ""))
        if expected_tenant and tenant_id != expected_tenant:
            return 403, {"error": "tenant_mismatch", "expected_tenant": expected_tenant}

        try:
            target_headers = self._build_target_headers(
                profile=profile,
                tenant_id=tenant_id,
                agent_id=agent_id,
                request_id=request_id,
                action_id=action_id,
            )
        except RuntimeError as exc:
            return 500, {"error": str(exc), "agent_id": agent_id}

        event_class = "operation"
        if not dry_run:
            self._log_action(
                stage="start",
                status="running",
                message="received",
                agent_id=agent_id,
                tenant_id=tenant_id,
                event_class=event_class,
                request_id=request_id,
                action_id=action_id,
                headers=target_headers,
                operation=operation,
            )

        response: dict[str, Any] = {
            "request_id": request_id,
            "action_id": action_id,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "operation": operation,
            "dry_run": dry_run,
        }

        try:
            if operation == "memory_event":
                policy = self._policy_for(profile)
                event = body.get("event")
                if not isinstance(event, dict):
                    return 400, {"error": "event object is required for memory_event"}
                persist, reason, event_class, sensitive = should_persist_event(policy, event)
                response["event_class"] = event_class
                response["sensitive"] = sensitive
                response["persist"] = persist
                response["reason"] = reason

                if persist:
                    rule = policy["rules"][event_class]
                    content = str(event.get("content", ""))
                    payload = {
                        "scope": str(event.get("scope", policy.get("default_scope", "isolated"))),
                        "owner_agent_id": agent_id,
                        "raw_content": content,
                        "source_ref": str(event.get("source_ref", f"event:{action_id}")),
                        "metadata": {
                            "event_type": event_class,
                            "confidence": float(event.get("confidence", 1.0)),
                            "request_id": request_id,
                            "action_id": action_id,
                            "policy_name": str(policy.get("policy_name", "")),
                            "policy_ver": str(policy.get("policy_version", "")),
                            "tags": rule.get("tags", []),
                            "input_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        },
                    }
                    if "group_id" in event:
                        payload["group_id"] = str(event["group_id"])
                    if sensitive and bool(policy.get("sensitive_handling", {}).get("mark_metadata_sensitive", False)):
                        payload["metadata"]["sensitive"] = True

                    if dry_run:
                        response["result"] = {"status": "dry_run", "payload_preview": payload}
                    else:
                        status, target_resp = self._call_target(
                            method="POST",
                            path="/memory/ingest",
                            payload=payload,
                            headers=target_headers,
                        )
                        response["target_status"] = status
                        response["target_response"] = target_resp
                else:
                    response["result"] = {"status": "skipped", "reason": reason}

            elif operation == "api_proxy":
                method = str(body.get("method", "POST")).upper()
                path = str(body.get("path", ""))
                payload = body.get("payload")
                if not path.startswith("/"):
                    return 400, {"error": "path must start with '/'"}
                if not path_allowed(profile, method=method, path=path):
                    return 403, {"error": "path_not_allowed", "path": path, "method": method}
                if payload is not None and not isinstance(payload, dict):
                    return 400, {"error": "payload must be an object"}

                if dry_run:
                    response["result"] = {"status": "dry_run", "method": method, "path": path}
                else:
                    status, target_resp = self._call_target(
                        method=method,
                        path=path,
                        payload=payload if isinstance(payload, dict) else {},
                        headers=target_headers,
                    )
                    response["target_status"] = status
                    response["target_response"] = target_resp
            else:
                return 400, {"error": "unsupported_operation", "operation": operation}

            response["status"] = "ok"
            return 200, response
        except Exception as exc:  # noqa: BLE001
            response["status"] = "error"
            response["error"] = str(exc)
            return 500, response
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            if not dry_run:
                final_status = response.get("status", "error")
                message = str(response.get("reason", final_status))
                self._log_action(
                    stage="end",
                    status=final_status,
                    message=message,
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    event_class=event_class,
                    request_id=request_id,
                    action_id=action_id,
                    headers=target_headers,
                    operation=operation,
                )
            response["duration_ms"] = duration_ms


class Handler(BaseHTTPRequestHandler):
    gateway: CentralGateway

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_dumps(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok"})
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/gateway/execute":
            self._send(404, {"error": "not_found"})
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        body = _json_loads(raw)
        status, response = self.gateway.execute(body)
        self._send(status, response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Central gateway for agent wrappers")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--target-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--agent-profiles", default=str(DEFAULT_AGENT_PROFILES))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GatewayConfig.from_env(args)
    gateway = CentralGateway(config)

    class BoundHandler(Handler):
        pass

    BoundHandler.gateway = gateway
    server = HTTPServer((config.bind_host, config.bind_port), BoundHandler)
    print(f"Central gateway listening on http://{config.bind_host}:{config.bind_port}")
    print(f"Target API base URL: {config.target_base_url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
