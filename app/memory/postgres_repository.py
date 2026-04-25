from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from app.memory.models import MemoryEntry


def _is_uuid(raw: str | None) -> bool:
    if not raw:
        return False
    try:
        uuid.UUID(str(raw))
        return True
    except ValueError:
        return False


def _tenant_uuid(tenant_id: str) -> str:
    if _is_uuid(tenant_id):
        return tenant_id
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tenant:{tenant_id}"))


def _group_uuid(group_id: str | None) -> str | None:
    if _is_uuid(group_id):
        return group_id
    return None


def _vector_to_pg(raw: list[float] | None) -> str | None:
    if not raw:
        return None
    return "[" + ",".join(f"{v:.8f}" for v in raw) + "]"


class PostgresMemoryRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def is_available(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except psycopg2.Error:
            return False

    def create(self, entry: MemoryEntry) -> MemoryEntry:
        tenant_uuid = _tenant_uuid(entry.tenant_id)
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                self._ensure_tenant(cur, tenant_uuid=tenant_uuid, tenant_name=entry.tenant_id)
                self._ensure_agent(cur, tenant_uuid=tenant_uuid, agent_id=entry.owner_agent_id)
                cur.execute(
                    """
                    INSERT INTO memory_entries (
                        id, tenant_id, owner_agent_id, group_id, scope, entry_type, content,
                        content_hash, importance, confidence, valid_from, valid_until,
                        tags, source_ref, metadata, embedding
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::vector
                    )
                    RETURNING *
                    """,
                    (
                        entry.id,
                        tenant_uuid,
                        entry.owner_agent_id,
                        _group_uuid(entry.group_id),
                        entry.scope,
                        entry.entry_type,
                        entry.content,
                        entry.content_hash,
                        int(entry.importance),
                        float(entry.confidence),
                        entry.valid_from,
                        entry.valid_until,
                        entry.tags,
                        entry.source_ref,
                        psycopg2.extras.Json(entry.metadata or {}),
                        _vector_to_pg(entry.embedding),
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                if row is None:
                    return entry
                return self._row_to_entry(row, tenant_alias=entry.tenant_id)

    def get(self, memory_id: str, tenant_id: str) -> MemoryEntry | None:
        tenant_uuid = _tenant_uuid(tenant_id)
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM memory_entries
                    WHERE id = %s AND tenant_id = %s
                    """,
                    (memory_id, tenant_uuid),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_entry(row, tenant_alias=tenant_id)

    def list_by_tenant(self, tenant_id: str) -> list[MemoryEntry]:
        tenant_uuid = _tenant_uuid(tenant_id)
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM memory_entries
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC
                    """,
                    (tenant_uuid,),
                )
                rows = cur.fetchall()
        return [self._row_to_entry(row, tenant_alias=tenant_id) for row in rows]

    def _ensure_tenant(self, cur: psycopg2.extensions.cursor, tenant_uuid: str, tenant_name: str) -> None:
        cur.execute(
            """
            INSERT INTO tenants (id, name)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name
            """,
            (tenant_uuid, tenant_name),
        )

    def _ensure_agent(self, cur: psycopg2.extensions.cursor, tenant_uuid: str, agent_id: str) -> None:
        cur.execute(
            """
            INSERT INTO agents (id, tenant_id, name, override_mode, is_disabled)
            VALUES (%s, %s, %s, 'none', false)
            ON CONFLICT (id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                name = EXCLUDED.name
            """,
            (agent_id, tenant_uuid, agent_id),
        )

    def _connect(self):
        return psycopg2.connect(self._database_url)

    def _row_to_entry(self, row: dict[str, Any], tenant_alias: str) -> MemoryEntry:
        created = row.get("created_at")
        if created is None:
            created = datetime.now(tz=timezone.utc)
        return MemoryEntry(
            id=str(row["id"]),
            tenant_id=tenant_alias,
            owner_agent_id=str(row["owner_agent_id"]),
            scope=str(row["scope"]),
            content=str(row.get("content", "")),
            group_id=(str(row["group_id"]) if row.get("group_id") is not None else None),
            entry_type=str(row.get("entry_type", "message")),
            tags=list(row.get("tags") or []),
            source_ref=row.get("source_ref"),
            embedding=self._vector_from_pg(row.get("embedding")),
            content_hash=row.get("content_hash"),
            importance=int(row.get("importance", 50)),
            confidence=float(row.get("confidence", 0.5)),
            valid_from=row.get("valid_from"),
            valid_until=row.get("valid_until"),
            metadata=dict(row.get("metadata") or {}),
            created_at=created,
        )

    def _vector_from_pg(self, raw: Any) -> list[float] | None:
        if raw is None:
            return None
        if isinstance(raw, list):
            return [float(v) for v in raw]
        if isinstance(raw, str):
            text = raw.strip()
            if text.startswith("[") and text.endswith("]"):
                body = text[1:-1].strip()
                if not body:
                    return []
                return [float(part.strip()) for part in body.split(",")]
        return None
