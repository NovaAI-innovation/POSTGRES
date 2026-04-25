from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.auth.credentials import issue_agent_token
from app.config import Settings
from app.groups.service import GroupPermissions
from app.main import Application


def make_settings() -> Settings:
    return Settings(
        database_url="postgresql://test/test",
        embedding_model="all-MiniLM-L6-v2",
        auth_secret_current="test-secret",
        auth_secret_previous=None,
        internal_api_keys=("dev-api-key",),
        log_level="INFO",
        tool_timeout_seconds=30,
        app_env="development",
    )


def auth_headers(settings: Settings, tenant_id: str, agent_id: str, user_id: str | None = None) -> dict[str, str]:
    token = issue_agent_token(settings, tenant_id=tenant_id, agent_id=agent_id, user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


def test_orchestration_idempotency_and_locking_prevent_duplicates() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, "tenant-a", "agent-a")

    t1 = app.handle(
        "POST",
        "/tasks",
        headers=headers,
        body=json.dumps({"summary": "do x", "idempotency_key": "k1", "lock_key": "resource-A"}),
    )
    t2 = app.handle(
        "POST",
        "/tasks",
        headers=headers,
        body=json.dumps({"summary": "do x dup", "idempotency_key": "k1", "lock_key": "resource-A"}),
    )
    assert t1.status_code == 201
    assert t2.status_code == 201
    assert t1.body["task"]["task_id"] == t2.body["task"]["task_id"]

    tid = t1.body["task"]["task_id"]
    started = app.handle("POST", f"/tasks/{tid}/start", headers=headers, body=json.dumps({}))
    assert started.status_code == 200
    assert started.body["task"]["status"] == "running"

    other = app.handle(
        "POST",
        "/tasks",
        headers=headers,
        body=json.dumps({"summary": "do y", "idempotency_key": "k2", "lock_key": "resource-A"}),
    )
    other_id = other.body["task"]["task_id"]
    waiting = app.handle("POST", f"/tasks/{other_id}/start", headers=headers, body=json.dumps({}))
    assert waiting.body["task"]["status"] == "waiting_approval"


def test_orchestration_retry_dead_letter_and_handoff() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, "tenant-a", "agent-a")
    created = app.handle("POST", "/tasks", headers=headers, body=json.dumps({"summary": "unstable"}))
    tid = created.body["task"]["task_id"]

    for _ in range(3):
        app.handle("POST", f"/tasks/{tid}/fail", headers=headers, body=json.dumps({"reason": "boom"}))
    tasks = app.handle("GET", "/tasks", headers=headers)
    assert tasks.status_code == 200
    assert tasks.body["dead_letter"]

    stable = app.handle("POST", "/tasks", headers=headers, body=json.dumps({"summary": "handoff me"}))
    sid = stable.body["task"]["task_id"]
    handoff = app.handle(
        "POST",
        f"/tasks/{sid}/handoff",
        headers=headers,
        body=json.dumps(
            {
                "source_agent": "agent-a",
                "target_agent": "agent-b",
                "summary": "continue",
                "memory_ids": ["m1"],
                "requested_output": "final report",
            }
        ),
    )
    assert handoff.status_code == 200
    assert handoff.body["handoff"]["target_agent"] == "agent-b"


def test_lifecycle_decay_compaction_backup_restore_retention() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, "tenant-a", "agent-a")

    app.handle("POST", "/memory", headers=headers, body=json.dumps({"scope": "isolated", "content": "old message 1"}))
    app.handle("POST", "/memory", headers=headers, body=json.dumps({"scope": "isolated", "content": "old message 2"}))
    all_items = app.memory.list_by_tenant("tenant-a")
    for entry in all_items:
        entry.created_at = datetime.now(tz=timezone.utc) - timedelta(days=40)

    app.handle(
        "POST",
        "/lifecycle/retention",
        headers=headers,
        body=json.dumps({"message_days": 30, "sensitive_days": 7, "soft_delete_days": 1}),
    )
    report = app.handle("POST", "/lifecycle/maintenance", headers=headers, body=json.dumps({}))
    assert report.status_code == 200
    assert "compaction" in report.body["report"]

    backup = app.handle("POST", "/lifecycle/backup", headers=headers, body=json.dumps({"name": "test-backup.json"}))
    assert backup.status_code == 200
    assert "test-backup.json" in backup.body["all_backups"]

    restore = app.handle(
        "POST",
        "/lifecycle/restore",
        headers=headers,
        body=json.dumps({"file_name": "test-backup.json"}),
    )
    assert restore.status_code == 200
    assert restore.body["restored"]["tenant_id"] == "tenant-a"


def test_admin_rbac_emergency_controls_and_actions() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    user_headers = auth_headers(settings, "tenant-a", "agent-a", user_id="user-1")
    admin_headers = auth_headers(settings, "tenant-a", "agent-a", user_id="admin-ops")

    denied = app.handle("GET", "/admin/console", headers=user_headers, body=json.dumps({}))
    assert denied.status_code == 403

    allowed = app.handle("GET", "/admin/console", headers=admin_headers, body=json.dumps({}))
    assert allowed.status_code == 200
    assert "Operator Console" in allowed.body["html"]

    pause = app.handle("POST", "/admin/pause-agents", headers=admin_headers, body=json.dumps({}))
    assert pause.status_code == 200
    blocked = app.handle("POST", "/tasks", headers=user_headers, body=json.dumps({"summary": "x"}))
    assert blocked.status_code == 503
    app.handle("POST", "/admin/resume-agents", headers=admin_headers, body=json.dumps({}))

    app.groups.set_permissions("g1", "agent-a", GroupPermissions(can_read=True, can_write=True, can_admin=True))
    app.handle("POST", "/admin/block-shared-memory-writes", headers=admin_headers, body=json.dumps({}))
    blocked_shared = app.handle(
        "POST",
        "/memory",
        headers=user_headers,
        body=json.dumps({"scope": "shared", "group_id": "g1", "content": "share me"}),
    )
    assert blocked_shared.status_code == 403
    app.handle("POST", "/admin/unblock-shared-memory-writes", headers=admin_headers, body=json.dumps({}))

    disable_tool = app.handle(
        "POST",
        "/admin/disable-tool-class",
        headers=admin_headers,
        body=json.dumps({"category": "external_send"}),
    )
    assert disable_tool.status_code == 200
    app.tool_allowlists.set_allowlist("agent-a", {"external_send"})
    tool = app.handle(
        "POST",
        "/tools/external_send/run",
        headers=user_headers,
        body=json.dumps({"destination": "x", "payload": "y"}),
    )
    assert tool.status_code == 403
    assert tool.body["error"] == "tool_class_disabled"

    revoke = app.handle(
        "POST",
        "/admin/revoke-credentials",
        headers=admin_headers,
        body=json.dumps({"subject_id": "agent-a"}),
    )
    assert revoke.status_code == 200
    revoked = app.handle("GET", "/tools", headers=user_headers, body=json.dumps({}))
    assert revoked.status_code == 401


def test_admin_memory_controls_without_db_access() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    admin_headers = auth_headers(settings, "tenant-a", "agent-a", user_id="admin-ops")
    user_headers = auth_headers(settings, "tenant-a", "agent-a", user_id="user-1")

    created = app.handle("POST", "/memory", headers=user_headers, body=json.dumps({"scope": "isolated", "content": "raw secret"}))
    mid = created.body["memory"]["id"]

    deleted = app.handle("POST", f"/admin/memory/{mid}/delete", headers=admin_headers, body=json.dumps({}))
    assert deleted.status_code == 200
    assert deleted.body["memory"]["metadata"]["soft_deleted"] is True

    restored = app.handle("POST", f"/admin/memory/{mid}/restore", headers=admin_headers, body=json.dumps({}))
    assert restored.status_code == 200
    assert restored.body["memory"]["metadata"]["soft_deleted"] is False

    scored = app.handle(
        "POST",
        f"/admin/memory/{mid}/scores",
        headers=admin_headers,
        body=json.dumps({"importance": 99, "confidence": 0.99}),
    )
    assert scored.status_code == 200
    assert scored.body["memory"]["importance"] == 99
