from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

from app.auth.credentials import issue_agent_token
from app.config import Settings
from app.embeddings.service import EmbeddingService
from app.groups.service import GroupPermissions
from app.main import Application
from app.memory.context import ContextAssembler, ContextBudgets
from app.memory.ingestion import MemoryIngestionWorker
from app.memory.repository import InMemoryMemoryRepository
from app.memory.service import MemoryService


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


def test_ingestion_converts_raw_event_to_structured_memory() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")

    response = app.handle(
        "POST",
        "/memory/ingest",
        headers=headers,
        body=json.dumps(
            {
                "scope": "isolated",
                "raw_content": "User prefers short answers. Sent from my iPhone",
                "source_ref": "msg-001",
                "metadata": {"project": "memory", "domain": "engineering", "task_type": "analysis"},
            }
        ),
    )
    assert response.status_code == 201
    assert response.body["inserted"] is True
    memory = response.body["memory"]
    assert memory["entry_type"] == "fact"
    assert "project:memory" in memory["tags"]
    assert "domain:engineering" in memory["tags"]
    assert len(memory["embedding"]) == 384
    vec = memory["embedding"]
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-3


def test_ingestion_deduplicates_by_hash_and_source_ref() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")

    first = app.handle(
        "POST",
        "/memory/ingest",
        headers=headers,
        body=json.dumps({"scope": "isolated", "raw_content": "Deploy completed successfully", "source_ref": "evt-1"}),
    )
    assert first.status_code == 201

    dup_hash = app.handle(
        "POST",
        "/memory/ingest",
        headers=headers,
        body=json.dumps({"scope": "isolated", "raw_content": "Deploy completed successfully", "source_ref": "evt-2"}),
    )
    assert dup_hash.body["inserted"] is False
    assert dup_hash.body["reason"] == "duplicate_content_hash"

    dup_ref = app.handle(
        "POST",
        "/memory/ingest",
        headers=headers,
        body=json.dumps({"scope": "isolated", "raw_content": "Different message", "source_ref": "evt-1"}),
    )
    assert dup_ref.body["inserted"] is False
    assert dup_ref.body["reason"] == "duplicate_source_ref"


def test_embedding_dimension_mismatch_is_detected() -> None:
    class BadEmbedding(EmbeddingService):
        def embed(self, text: str) -> list[float]:
            return [0.1] * 383

    memory = MemoryService(InMemoryMemoryRepository())
    worker = MemoryIngestionWorker(memory, BadEmbedding("bad"))
    result = worker.ingest(
        tenant_id="tenant-a",
        owner_agent_id="agent-a",
        scope="isolated",
        raw_content="some text",
    )
    assert result.inserted is False
    assert result.reason == "embedding_dimension_mismatch"


def test_retrieval_respects_scope_permissions() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    owner_headers = auth_headers(settings, tenant_id="tenant-a", agent_id="owner")
    reader_headers = auth_headers(settings, tenant_id="tenant-a", agent_id="reader")
    group_id = "group-9"
    app.groups.set_permissions(group_id, "owner", GroupPermissions(can_read=True, can_write=True, can_admin=True))
    app.groups.set_permissions(group_id, "reader", GroupPermissions(can_read=True, can_write=False, can_admin=False))

    iso = app.handle(
        "POST",
        "/memory/ingest",
        headers=owner_headers,
        body=json.dumps({"scope": "isolated", "raw_content": "private credential never share"}),
    )
    assert iso.status_code == 201
    scoped = app.handle(
        "POST",
        "/memory/ingest",
        headers=owner_headers,
        body=json.dumps({"scope": "scoped", "group_id": group_id, "raw_content": "team runbook location"}),
    )
    assert scoped.status_code == 201

    result = app.handle(
        "POST",
        "/memory/search",
        headers=reader_headers,
        body=json.dumps({"query": "runbook location", "debug": True}),
    )
    assert result.status_code == 200
    contents = [item["content"] for item in result.body["items"]]
    assert "team runbook location" in contents
    assert "private credential never share" not in contents


def test_retrieval_reranking_penalizes_old_low_confidence_items() -> None:
    settings = make_settings()
    app = Application(settings=settings)
    headers = auth_headers(settings, tenant_id="tenant-a", agent_id="agent-a")

    app.handle(
        "POST",
        "/memory",
        headers=headers,
        body=json.dumps(
            {
                "scope": "isolated",
                "content": "status page runbook is at docs/status",
                "importance": 85,
                "confidence": 0.95,
                "entry_type": "fact",
            }
        ),
    )
    old = app.handle(
        "POST",
        "/memory",
        headers=headers,
        body=json.dumps(
            {
                "scope": "isolated",
                "content": "legacy irrelevant note",
                "importance": 5,
                "confidence": 0.1,
                "entry_type": "message",
            }
        ),
    )
    old_id = old.body["memory"]["id"]
    entry = app.memory.get(old_id, "tenant-a")
    assert entry is not None
    entry.created_at = datetime.now(tz=timezone.utc) - timedelta(days=400)

    result = app.handle(
        "POST",
        "/memory/search",
        headers=headers,
        body=json.dumps({"query": "status page runbook", "debug": True}),
    )
    assert result.status_code == 200
    assert result.body["items"][0]["content"] == "status page runbook is at docs/status"


def test_context_assembler_enforces_token_budget_and_surfaces_conflicts() -> None:
    assembler = ContextAssembler()
    memories = [
        {
            "memory_id": "1",
            "content": "release_channel: beta",
            "scope": "shared",
            "entry_type": "fact",
            "confidence": 0.8,
            "source_label": "src-1",
            "created_at": "2026-04-20T00:00:00+00:00",
            "valid_from": "2026-04-20T00:00:00+00:00",
            "tags": ["project:app"],
        },
        {
            "memory_id": "2",
            "content": "release_channel: stable",
            "scope": "shared",
            "entry_type": "fact",
            "confidence": 0.8,
            "source_label": "src-2",
            "created_at": "2026-04-20T00:00:00+00:00",
            "valid_from": "2026-04-20T00:00:00+00:00",
            "tags": ["project:app"],
        },
    ]
    output = assembler.assemble(memories, ContextBudgets(memory_tokens=8, tool_tokens=4, history_tokens=4))
    assert output["budgets"]["memory_tokens"] <= 8
    assert output["conflicts"]
    assert "src:" in output["memory_block"]
    assert "scope:" in output["memory_block"]
