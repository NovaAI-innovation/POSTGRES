from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

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


def _dt_from_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _vector_to_pg(raw: list[float] | None) -> str | None:
    if not raw:
        return None
    return "[" + ",".join(f"{v:.8f}" for v in raw) + "]"


def _vector_from_pg(raw: Any) -> list[float] | None:
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


class SupabaseMemoryRepository:
    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self._base = supabase_url.rstrip("/")
        self._key = service_role_key

    def create(self, entry: MemoryEntry) -> MemoryEntry:
        tenant_uuid = _tenant_uuid(entry.tenant_id)
        self._ensure_tenant(tenant_uuid=tenant_uuid, tenant_name=entry.tenant_id)
        self._ensure_agent(tenant_uuid=tenant_uuid, agent_id=entry.owner_agent_id)

        row = {
            "id": entry.id,
            "tenant_id": tenant_uuid,
            "owner_agent_id": entry.owner_agent_id,
            "group_id": _group_uuid(entry.group_id),
            "scope": entry.scope,
            "entry_type": entry.entry_type,
            "content": entry.content,
            "content_hash": entry.content_hash,
            "importance": int(entry.importance),
            "confidence": float(entry.confidence),
            "valid_from": entry.valid_from.isoformat() if entry.valid_from else None,
            "valid_until": entry.valid_until.isoformat() if entry.valid_until else None,
            "tags": entry.tags,
            "source_ref": entry.source_ref,
            "metadata": entry.metadata or {},
            "embedding": _vector_to_pg(entry.embedding),
        }
        resp = self._request_json(
            "POST",
            "/rest/v1/memory_entries?select=*",
            payload=row,
            headers={"Prefer": "return=representation"},
        )
        if not isinstance(resp, list) or not resp:
            return entry
        return self._row_to_entry(resp[0], tenant_alias=entry.tenant_id)

    def get(self, memory_id: str, tenant_id: str) -> MemoryEntry | None:
        tenant_uuid = _tenant_uuid(tenant_id)
        q = urllib.parse.urlencode({"id": f"eq.{memory_id}", "tenant_id": f"eq.{tenant_uuid}", "select": "*"})
        resp = self._request_json("GET", f"/rest/v1/memory_entries?{q}")
        if not isinstance(resp, list) or not resp:
            return None
        return self._row_to_entry(resp[0], tenant_alias=tenant_id)

    def list_by_tenant(self, tenant_id: str) -> list[MemoryEntry]:
        tenant_uuid = _tenant_uuid(tenant_id)
        q = urllib.parse.urlencode({"tenant_id": f"eq.{tenant_uuid}", "select": "*", "order": "created_at.desc"})
        resp = self._request_json("GET", f"/rest/v1/memory_entries?{q}")
        if not isinstance(resp, list):
            return []
        return [self._row_to_entry(row, tenant_alias=tenant_id) for row in resp]

    def _ensure_tenant(self, tenant_uuid: str, tenant_name: str) -> None:
        payload = {"id": tenant_uuid, "name": tenant_name}
        self._request_json(
            "POST",
            "/rest/v1/tenants",
            payload=payload,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            query={"on_conflict": "id"},
        )

    def _ensure_agent(self, tenant_uuid: str, agent_id: str) -> None:
        payload = {"id": agent_id, "tenant_id": tenant_uuid, "name": agent_id, "override_mode": "none", "is_disabled": False}
        self._request_json(
            "POST",
            "/rest/v1/agents",
            payload=payload,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            query={"on_conflict": "id"},
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> Any:
        qs = ""
        if query:
            qs = ("&" if "?" in path else "?") + urllib.parse.urlencode(query)
        url = f"{self._base}{path}{qs}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req_headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url=url, data=body, method=method, headers=req_headers)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                if not raw.strip():
                    return {}
                return json.loads(raw)
        except (urllib.error.URLError, OSError):
            return self._request_via_powershell(method=method, url=url, payload=payload, headers=req_headers)

    def _row_to_entry(self, row: dict[str, Any], tenant_alias: str) -> MemoryEntry:
        created = _dt_from_iso(row.get("created_at")) or datetime.now(tz=timezone.utc)
        return MemoryEntry(
            id=str(row.get("id")),
            tenant_id=tenant_alias,
            owner_agent_id=str(row.get("owner_agent_id")),
            scope=str(row.get("scope")),
            content=str(row.get("content", "")),
            group_id=row.get("group_id"),
            entry_type=str(row.get("entry_type", "message")),
            tags=list(row.get("tags") or []),
            source_ref=row.get("source_ref"),
            embedding=_vector_from_pg(row.get("embedding")),
            content_hash=row.get("content_hash"),
            importance=int(row.get("importance", 50)),
            confidence=float(row.get("confidence", 0.5)),
            valid_from=_dt_from_iso(row.get("valid_from")),
            valid_until=_dt_from_iso(row.get("valid_until")),
            metadata=dict(row.get("metadata") or {}),
            created_at=created,
        )

    def _request_via_powershell(
        self, *, method: str, url: str, payload: dict[str, Any] | None, headers: dict[str, str]
    ) -> Any:
        payload_json = json.dumps(payload) if payload is not None else ""
        header_lines: list[str] = []
        for key, value in headers.items():
            escaped = str(value).replace("'", "''")
            header_lines.append(f"$h['{key}'] = '{escaped}'")
        headers_ps = "; ".join(header_lines)
        if payload is not None:
            body_escaped = payload_json.replace("'", "''")
            body_ps = f"$body = '{body_escaped}'"
        else:
            body_ps = "$body = $null"
        script = (
            "$ErrorActionPreference='Stop'; "
            "$h=@{}; "
            f"{headers_ps}; "
            f"{body_ps}; "
            "$args = @{Uri='" + url.replace("'", "''") + "'; Method='" + method + "'; Headers=$h; TimeoutSec=20; UseBasicParsing=$true}; "
            "if ($body -ne $null) { $args['Body']=$body }; "
            "$resp = Invoke-WebRequest @args; "
            "if ([string]::IsNullOrWhiteSpace($resp.Content)) { '{}' } else { $resp.Content }"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "powershell_request_failed")
        text = completed.stdout.strip()
        if not text:
            return {}
        return json.loads(text)
