from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth.credentials import issue_agent_token
from app.config import Settings


@dataclass
class Result:
    name: str
    status: int
    ok: bool
    details: str = ""


class HttpClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | str]:
        url = f"{self.base_url}{path}"
        body = None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url=url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
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


def expect(results: list[Result], name: str, status: int, expected: int | set[int], payload: Any) -> None:
    if isinstance(expected, set):
        ok = status in expected
        expected_str = ",".join(str(x) for x in sorted(expected))
    else:
        ok = status == expected
        expected_str = str(expected)
    details = ""
    if not ok:
        details = f"expected={expected_str} got={status} payload={payload}"
    results.append(Result(name=name, status=status, ok=ok, details=details))


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    settings = Settings.from_env()
    tenant_id = os.getenv("TEST_TENANT_ID", "tenant-a")
    agent_id = os.getenv("TEST_AGENT_ID", "agent-a")
    user_token = issue_agent_token(settings, tenant_id=tenant_id, agent_id=agent_id, user_id="user-1")
    admin_token = issue_agent_token(settings, tenant_id=tenant_id, agent_id=agent_id, user_id="admin-ops")

    anon = HttpClient(base_url)
    user = HttpClient(base_url, token=user_token)
    admin = HttpClient(base_url, token=admin_token)
    results: list[Result] = []

    status, payload = anon.request("GET", "/health")
    expect(results, "health", status, 200, payload)

    status, payload = user.request("GET", "/tools")
    expect(results, "tools_list", status, 200, payload)

    status, payload = user.request("POST", "/memory", {"scope": "isolated", "content": "integration note"})
    expect(results, "memory_create", status, 201, payload)
    memory_id = payload.get("memory", {}).get("id") if isinstance(payload, dict) else None

    if not memory_id:
        print(json.dumps([r.__dict__ for r in results], indent=2))
        return 1

    status, payload = user.request("GET", f"/memory/{memory_id}")
    expect(results, "memory_get", status, 200, payload)

    status, payload = user.request(
        "POST",
        "/memory/ingest",
        {"scope": "isolated", "raw_content": "User prefers concise summaries.", "source_ref": "int-msg-1"},
    )
    expect(results, "memory_ingest", status, 201, payload)

    status, payload = user.request("POST", "/memory/search", {"query": "concise summaries", "debug": True})
    expect(results, "memory_search", status, 200, payload)

    status, payload = user.request("POST", "/context/assemble", {"query": "concise summaries"})
    expect(results, "context_assemble", status, 200, payload)

    status, payload = user.request("POST", "/tools/echo/dry-run", {"value": 1})
    expect(results, "tool_echo_dry_run", status, 200, payload)

    status, payload = user.request("POST", "/tools/echo/run", {"value": 2})
    expect(results, "tool_echo_run", status, 200, payload)

    status, payload = user.request("POST", "/tools/external_send/run", {"destination": "x", "payload": "y"})
    expect(results, "tool_external_send_unapproved", status, 403, payload)

    status, payload = user.request("GET", "/tool-calls")
    expect(results, "tool_calls", status, 200, payload)

    status, payload = user.request("GET", "/audit-events")
    expect(results, "audit_events", status, 200, payload)

    status, payload = user.request("GET", "/policy-decisions")
    expect(results, "policy_decisions", status, 200, payload)

    status, payload = user.request("GET", "/observability/metrics")
    expect(results, "metrics", status, 200, payload)

    status, payload = user.request("GET", "/observability/traces")
    expect(results, "traces", status, 200, payload)

    status, payload = user.request("POST", "/eval/run", {})
    expect(results, "eval_run", status, 200, payload)

    status, payload = user.request("GET", "/eval/review-queue")
    expect(results, "eval_review_queue", status, 200, payload)

    status, payload = user.request("POST", "/tasks", {"summary": "integration task", "idempotency_key": "integration-k1"})
    expect(results, "task_create", status, 201, payload)
    task_id = payload.get("task", {}).get("task_id") if isinstance(payload, dict) else None

    if task_id:
        status, payload = user.request("GET", f"/tasks/{task_id}")
        expect(results, "task_get", status, 200, payload)
        status, payload = user.request("PATCH", f"/tasks/{task_id}", {"priority": 77})
        expect(results, "task_patch", status, 200, payload)
        status, payload = user.request("POST", f"/tasks/{task_id}/start", {})
        expect(results, "task_start", status, 200, payload)
        status, payload = user.request(
            "POST",
            f"/tasks/{task_id}/handoff",
            {
                "source_agent": "agent-a",
                "target_agent": "agent-b",
                "summary": "handoff",
                "memory_ids": [memory_id],
                "requested_output": "final",
            },
        )
        expect(results, "task_handoff", status, 200, payload)
        status, payload = user.request("POST", f"/tasks/{task_id}/complete", {})
        expect(results, "task_complete", status, 200, payload)

    status, payload = user.request("GET", "/tasks")
    expect(results, "task_list", status, 200, payload)

    status, payload = user.request("POST", "/lifecycle/retention", {"message_days": 30, "sensitive_days": 7, "soft_delete_days": 2})
    expect(results, "lifecycle_retention", status, 200, payload)
    status, payload = user.request("POST", "/lifecycle/maintenance", {})
    expect(results, "lifecycle_maintenance", status, 200, payload)
    status, payload = user.request("POST", "/lifecycle/backup", {"name": "integration-backup.json"})
    expect(results, "lifecycle_backup", status, 200, payload)
    status, payload = user.request("GET", "/lifecycle/backups")
    expect(results, "lifecycle_backups", status, 200, payload)
    status, payload = user.request("POST", "/lifecycle/restore", {"file_name": "integration-backup.json"})
    expect(results, "lifecycle_restore", status, 200, payload)

    status, payload = admin.request("GET", "/admin/console")
    expect(results, "admin_console", status, 200, payload)
    status, payload = admin.request("POST", f"/admin/memory/{memory_id}/scores", {"importance": 90, "confidence": 0.9})
    expect(results, "admin_adjust_scores", status, 200, payload)
    status, payload = admin.request("POST", f"/admin/memory/{memory_id}/delete", {})
    expect(results, "admin_memory_delete", status, 200, payload)
    status, payload = admin.request("POST", f"/admin/memory/{memory_id}/restore", {})
    expect(results, "admin_memory_restore", status, 200, payload)
    status, payload = admin.request("POST", f"/memory/{memory_id}/redact", {})
    expect(results, "memory_redact", status, 200, payload)
    status, payload = admin.request("POST", "/admin/prompt-context", {"query": "integration"})
    expect(results, "admin_prompt_context", status, 200, payload)
    status, payload = admin.request("POST", "/admin/pause-agents", {})
    expect(results, "admin_pause_agents", status, 200, payload)
    status, payload = user.request("POST", "/tasks", {"summary": "blocked task"})
    expect(results, "paused_blocks_tasks", status, 503, payload)
    status, payload = admin.request("POST", "/admin/resume-agents", {})
    expect(results, "admin_resume_agents", status, 200, payload)
    status, payload = admin.request("POST", "/admin/block-shared-memory-writes", {})
    expect(results, "admin_block_shared_writes", status, 200, payload)
    status, payload = admin.request("POST", "/admin/unblock-shared-memory-writes", {})
    expect(results, "admin_unblock_shared_writes", status, 200, payload)
    status, payload = admin.request("POST", "/admin/disable-tool-class", {"category": "external_send"})
    expect(results, "admin_disable_tool_class", status, 200, payload)
    status, payload = admin.request("POST", "/admin/enable-tool-class", {"category": "external_send"})
    expect(results, "admin_enable_tool_class", status, 200, payload)
    status, payload = admin.request("POST", "/admin/agents/agent-b/disable", {})
    expect(results, "admin_disable_agent", status, 200, payload)
    status, payload = admin.request("POST", "/admin/agents/agent-b/read-only", {})
    expect(results, "admin_agent_read_only", status, 200, payload)
    status, payload = admin.request("GET", "/admin/tasks")
    expect(results, "admin_tasks", status, 200, payload)
    status, payload = admin.request("GET", "/admin/tool-calls")
    expect(results, "admin_tool_calls", status, 200, payload)
    status, payload = admin.request("GET", "/admin/audit-events")
    expect(results, "admin_audit_events", status, 200, payload)
    status, payload = admin.request("GET", "/admin/approvals")
    expect(results, "admin_approvals", status, 200, payload)

    status, payload = admin.request("POST", "/admin/revoke-credentials", {"subject_id": "agent-a"})
    expect(results, "admin_revoke_credentials", status, 200, payload)
    status, payload = user.request("GET", "/tools")
    expect(results, "revoked_creds_blocked", status, 401, payload)

    print(json.dumps([r.__dict__ for r in results], indent=2))
    failures = [r for r in results if not r.ok]
    if failures:
        print(f"FAILED {len(failures)} checks", file=sys.stderr)
        return 1
    print(f"PASSED {len(results)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
