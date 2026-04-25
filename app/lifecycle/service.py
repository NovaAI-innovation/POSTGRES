from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.memory.models import MemoryEntry
from app.memory.service import MemoryService


@dataclass
class TenantRetentionPolicy:
    tenant_id: str
    message_days: int = 90
    sensitive_days: int = 7
    soft_delete_days: int = 30


class BackupManager:
    def __init__(self, backup_dir: pathlib.Path) -> None:
        self._backup_dir = backup_dir
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, payload: dict[str, Any], name: str | None = None) -> pathlib.Path:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_name = name or f"backup-{timestamp}.json"
        path = self._backup_dir / file_name
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def restore_backup(self, file_name: str) -> dict[str, Any]:
        path = self._backup_dir / file_name
        return json.loads(path.read_text(encoding="utf-8"))

    def list_backups(self) -> list[str]:
        return sorted([p.name for p in self._backup_dir.glob("*.json")])


class LifecycleManager:
    def __init__(self, memory_service: MemoryService, backup_manager: BackupManager) -> None:
        self._memory = memory_service
        self._backups = backup_manager
        self._retention: dict[str, TenantRetentionPolicy] = {}
        self._archives: dict[str, list[dict[str, Any]]] = {}

    def set_retention_policy(self, policy: TenantRetentionPolicy) -> None:
        self._retention[policy.tenant_id] = policy

    def get_retention_policy(self, tenant_id: str) -> TenantRetentionPolicy:
        return self._retention.get(tenant_id, TenantRetentionPolicy(tenant_id=tenant_id))

    def apply_decay(self, tenant_id: str) -> int:
        changed = 0
        for entry in self._memory.list_by_tenant(tenant_id):
            if "pinned" in entry.tags or "core_fact" in entry.tags:
                continue
            reinforced = bool(entry.metadata.get("reinforced", False))
            decay = 1 if reinforced else 3
            next_importance = max(0, entry.importance - decay)
            if next_importance != entry.importance:
                entry.importance = next_importance
                changed += 1
        return changed

    def detect_stale(self, tenant_id: str) -> dict[str, list[str]]:
        now = datetime.now(tz=timezone.utc)
        stale_expired: list[str] = []
        stale_old_source: list[str] = []
        contradictions: list[str] = []

        facts_by_subject: dict[str, list[MemoryEntry]] = {}
        for entry in self._memory.list_by_tenant(tenant_id):
            if entry.valid_until and entry.valid_until < now:
                stale_expired.append(entry.id)
            if entry.source_ref and entry.created_at < now - timedelta(days=180):
                stale_old_source.append(entry.id)
            if entry.entry_type == "fact":
                subject = _subject_key(entry.content)
                facts_by_subject.setdefault(subject, []).append(entry)

        for subject, entries in facts_by_subject.items():
            distinct = {e.content.strip().lower() for e in entries}
            if len(distinct) > 1:
                contradictions.append(subject)

        return {
            "expired": stale_expired,
            "old_source": stale_old_source,
            "contradictions": contradictions,
        }

    def compact(self, tenant_id: str) -> dict[str, Any]:
        now = datetime.now(tz=timezone.utc)
        old_messages = [
            entry
            for entry in self._memory.list_by_tenant(tenant_id)
            if entry.entry_type == "message" and entry.created_at < now - timedelta(days=30)
        ]
        if not old_messages:
            return {"compacted": 0, "summary_id": None}

        summary_content = " | ".join(m.content for m in old_messages[:20])
        episode = self._memory.create(
            tenant_id=tenant_id,
            owner_agent_id=old_messages[0].owner_agent_id,
            scope=old_messages[0].scope,
            group_id=old_messages[0].group_id,
            content=f"Compacted episode: {summary_content}",
            entry_type="episode",
            tags=["compacted"],
            importance=60,
            confidence=0.8,
            metadata={"compaction_sources": [m.id for m in old_messages]},
        )
        archive = self._archives.setdefault(tenant_id, [])
        for message in old_messages:
            archive.append({"id": message.id, "content": message.content, "archived_at": now.isoformat()})
            message.metadata["soft_deleted"] = True
        return {"compacted": len(old_messages), "summary_id": episode.id}

    def cleanup_soft_deleted(self, tenant_id: str) -> int:
        policy = self.get_retention_policy(tenant_id)
        now = datetime.now(tz=timezone.utc)
        removed = 0
        for entry in self._memory.list_by_tenant(tenant_id):
            if not entry.metadata.get("soft_deleted"):
                continue
            age_days = (now - entry.created_at).days
            if age_days >= policy.soft_delete_days:
                entry.metadata["hard_deleted"] = True
                removed += 1
        return removed

    def enforce_retention(self, tenant_id: str) -> dict[str, int]:
        policy = self.get_retention_policy(tenant_id)
        now = datetime.now(tz=timezone.utc)
        messages_expired = 0
        sensitive_expired = 0
        for entry in self._memory.list_by_tenant(tenant_id):
            if entry.entry_type == "message" and entry.created_at < now - timedelta(days=policy.message_days):
                entry.metadata["soft_deleted"] = True
                messages_expired += 1
            if entry.metadata.get("sensitive") and entry.created_at < now - timedelta(days=policy.sensitive_days):
                entry.metadata["soft_deleted"] = True
                sensitive_expired += 1
        cleaned = self.cleanup_soft_deleted(tenant_id)
        return {
            "messages_expired": messages_expired,
            "sensitive_expired": sensitive_expired,
            "hard_deleted": cleaned,
        }

    def run_maintenance(self, tenant_id: str) -> dict[str, Any]:
        decay = self.apply_decay(tenant_id)
        stale = self.detect_stale(tenant_id)
        compacted = self.compact(tenant_id)
        retention = self.enforce_retention(tenant_id)
        return {"decayed": decay, "stale": stale, "compaction": compacted, "retention": retention}

    def snapshot(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "memory": [m.to_dict() for m in self._memory.list_by_tenant(tenant_id)],
            "retention_policy": self.get_retention_policy(tenant_id).__dict__,
            "archives": self._archives.get(tenant_id, []),
        }

    def backup(self, tenant_id: str, name: str | None = None) -> str:
        path = self._backups.create_backup(self.snapshot(tenant_id), name=name)
        return path.name

    def restore(self, file_name: str) -> dict[str, Any]:
        return self._backups.restore_backup(file_name)

    def list_backups(self) -> list[str]:
        return self._backups.list_backups()


def _subject_key(content: str) -> str:
    if ":" in content:
        return content.split(":")[0].strip().lower()
    if "=" in content:
        return content.split("=")[0].strip().lower()
    return " ".join(content.split()[:3]).lower()
