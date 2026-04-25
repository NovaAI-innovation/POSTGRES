from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.memory.models import MemoryEntry
from app.memory.repository import MemoryRepository


class MemoryService:
    def __init__(self, repository: MemoryRepository) -> None:
        self._repository = repository

    def create(
        self,
        tenant_id: str,
        owner_agent_id: str,
        scope: str,
        content: str,
        group_id: str | None = None,
        entry_type: str = "message",
        tags: list[str] | None = None,
        source_ref: str | None = None,
        embedding: list[float] | None = None,
        content_hash: str | None = None,
        importance: int = 50,
        confidence: float = 0.5,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            owner_agent_id=owner_agent_id,
            scope=scope,
            group_id=group_id,
            content=content,
            entry_type=entry_type,
            tags=tags or [],
            source_ref=source_ref,
            embedding=embedding,
            content_hash=content_hash,
            importance=importance,
            confidence=confidence,
            valid_from=valid_from,
            valid_until=valid_until,
            metadata=metadata or {},
        )
        return self._repository.create(entry)

    def get(self, memory_id: str, tenant_id: str) -> MemoryEntry | None:
        return self._repository.get(memory_id, tenant_id)

    def list_by_tenant(self, tenant_id: str) -> list[MemoryEntry]:
        return self._repository.list_by_tenant(tenant_id)
