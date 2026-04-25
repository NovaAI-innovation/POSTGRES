from __future__ import annotations

import uuid
from typing import Protocol

from app.memory.models import MemoryEntry


class MemoryRepository(Protocol):
    def create(self, entry: MemoryEntry) -> MemoryEntry:
        ...

    def get(self, memory_id: str, tenant_id: str) -> MemoryEntry | None:
        ...

    def list_by_tenant(self, tenant_id: str) -> list[MemoryEntry]:
        ...


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], MemoryEntry] = {}

    def create(self, entry: MemoryEntry) -> MemoryEntry:
        if not entry.id:
            entry.id = str(uuid.uuid4())
        self._store[(entry.tenant_id, entry.id)] = entry
        return entry

    def get(self, memory_id: str, tenant_id: str) -> MemoryEntry | None:
        return self._store.get((tenant_id, memory_id))

    def list_by_tenant(self, tenant_id: str) -> list[MemoryEntry]:
        return [entry for (stored_tenant, _), entry in self._store.items() if stored_tenant == tenant_id]
