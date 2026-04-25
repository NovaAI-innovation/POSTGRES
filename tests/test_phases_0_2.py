from __future__ import annotations

import json

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


def auth_headers(settings: Settings, tenant_id: str, agent_id: str) -> dict[str, str]:
    token = issue_agent_token(settings, tenant_id=tenant_id, agent_id=agent_id)
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_available_without_auth() -> None:
    app = Application(settings=make_settings())
    response = app.handle("GET", "/health", headers={})
    assert response.status_code == 200
    assert response.body["status"] == "ok"


def test_unauthorized_memory_write_rejected_before_logic() -> None:
    app = Application(settings=make_settings())
    response = app.handle("POST", "/memory", headers={}, body=json.dumps({"scope": "isolated", "content": "x"}))
    assert response.status_code == 401


def test_agent_can_create_and_read_isolated_memory() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")

    create = app.handle(
        "POST",
        "/memory",
        headers=headers,
        body=json.dumps({"scope": "isolated", "content": "isolated note"}),
    )
    assert create.status_code == 201
    memory_id = create.body["memory"]["id"]

    read = app.handle("GET", f"/memory/{memory_id}", headers=headers)
    assert read.status_code == 200
    assert read.body["memory"]["content"] == "isolated note"


def test_non_owner_cannot_read_isolated_memory() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    owner_headers = auth_headers(settings, tenant_id="tenant-a", agent_id="owner")
    other_headers = auth_headers(settings, tenant_id="tenant-a", agent_id="other")

    create = app.handle(
        "POST",
        "/memory",
        headers=owner_headers,
        body=json.dumps({"scope": "isolated", "content": "private"}),
    )
    memory_id = create.body["memory"]["id"]
    read = app.handle("GET", f"/memory/{memory_id}", headers=other_headers)
    assert read.status_code == 403


def test_scoped_memory_requires_group_read_permission() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    writer_headers = auth_headers(settings, tenant_id="tenant-a", agent_id="writer")
    reader_headers = auth_headers(settings, tenant_id="tenant-a", agent_id="reader")
    group_id = "group-1"

    app.groups.set_permissions(group_id, "writer", GroupPermissions(can_read=True, can_write=True, can_admin=True))
    app.groups.set_permissions(group_id, "reader", GroupPermissions(can_read=True, can_write=False, can_admin=False))

    create = app.handle(
        "POST",
        "/memory",
        headers=writer_headers,
        body=json.dumps({"scope": "scoped", "group_id": group_id, "content": "team note"}),
    )
    assert create.status_code == 201
    memory_id = create.body["memory"]["id"]

    read = app.handle("GET", f"/memory/{memory_id}", headers=reader_headers)
    assert read.status_code == 200


def test_shared_memory_write_denied_without_group_write_permission() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")

    app.groups.set_permissions("group-2", "agent-a", GroupPermissions(can_read=True, can_write=False, can_admin=False))
    response = app.handle(
        "POST",
        "/memory",
        headers=headers,
        body=json.dumps({"scope": "shared", "group_id": "group-2", "content": "shared note"}),
    )
    assert response.status_code == 403


def test_blocked_agent_override_is_enforced() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")
    app.agent_overrides.set_override("agent-a", "blocked")

    response = app.handle(
        "POST",
        "/memory",
        headers=headers,
        body=json.dumps({"scope": "isolated", "content": "should fail"}),
    )
    assert response.status_code == 403
    assert response.body["reason"] == "agent_blocked"


def test_read_only_agent_cannot_call_tool() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")
    app.agent_overrides.set_override("agent-a", "read_only")

    response = app.handle("POST", "/tools/echo/run", headers=headers, body=json.dumps({"value": 1}))
    assert response.status_code == 403
    assert response.body["reason"] == "agent_read_only"
