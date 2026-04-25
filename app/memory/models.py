from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


VALID_SCOPES = {"isolated", "scoped", "shared"}


@dataclass
class MemoryEntry:
    id: str
    tenant_id: str
    owner_agent_id: str
    scope: str
    content: str
    group_id: str | None = None
    entry_type: str = "message"
    tags: list[str] = field(default_factory=list)
    source_ref: str | None = None
    embedding: list[float] | None = None
    content_hash: str | None = None
    importance: int = 50
    confidence: float = 0.5
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def __post_init__(self) -> None:
        if self.scope not in VALID_SCOPES:
            raise ValueError(f"invalid scope: {self.scope}")

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["valid_from"] = self.valid_from.isoformat() if self.valid_from else None
        payload["valid_until"] = self.valid_until.isoformat() if self.valid_until else None
        return payload
