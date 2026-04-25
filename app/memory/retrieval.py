from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.embeddings.service import EmbeddingService
from app.identity.models import IdentityContext
from app.memory.models import MemoryEntry
from app.memory.service import MemoryService
from app.permissions.policy_engine import PolicyEngine


@dataclass(frozen=True)
class RetrievalResult:
    items: list[dict[str, Any]]
    debug: dict[str, Any]


class MemoryRetrievalService:
    def __init__(self, memory_service: MemoryService, policy: PolicyEngine, embeddings: EmbeddingService) -> None:
        self._memory = memory_service
        self._policy = policy
        self._embeddings = embeddings

    def retrieve_memory(
        self,
        identity: IdentityContext,
        query: str,
        filters: dict[str, Any] | None = None,
        debug: bool = False,
        limit: int = 10,
    ) -> RetrievalResult:
        filters = filters or {}
        query_vector = self._normalize_vector(self._embeddings.embed(query))
        words = {w for w in query.lower().split() if w}
        now = datetime.now(tz=timezone.utc)

        scored: list[tuple[MemoryEntry, float, dict[str, float]]] = []
        for entry in self._memory.list_by_tenant(identity.tenant_id or ""):
            if not self._passes_filters(entry, filters, now):
                continue
            decision = self._policy.can_read_memory(identity, entry)
            if not decision.allowed:
                continue
            semantic = self._cosine_similarity(entry.embedding or [], query_vector)
            keyword = self._keyword_overlap(words, entry.content.lower().split())
            exact = 1.0 if query.lower() in entry.content.lower() else 0.0
            recency = self._recency_score(entry.created_at, now)
            importance = entry.importance / 100.0
            confidence = entry.confidence
            scope_priority = {"isolated": 1.0, "scoped": 0.85, "shared": 0.7}.get(entry.scope, 0.5)

            score = (
                semantic * 0.42
                + keyword * 0.18
                + recency * 0.12
                + importance * 0.14
                + confidence * 0.1
                + scope_priority * 0.04
                + exact * 0.08
            )
            scored.append(
                (
                    entry,
                    score,
                    {
                        "semantic": round(semantic, 4),
                        "keyword": round(keyword, 4),
                        "recency": round(recency, 4),
                        "importance": round(importance, 4),
                        "confidence": round(confidence, 4),
                        "scope_priority": round(scope_priority, 4),
                        "exact_match": round(exact, 4),
                        "hybrid_score": round(score, 4),
                    },
                )
            )

        scored.sort(key=lambda x: x[1], reverse=True)
        deduped: list[tuple[MemoryEntry, float, dict[str, float]]] = []
        seen_hash: set[str] = set()
        for row in scored:
            entry = row[0]
            if entry.content_hash and entry.content_hash in seen_hash:
                continue
            if entry.content_hash:
                seen_hash.add(entry.content_hash)
            deduped.append(row)
            if len(deduped) >= limit:
                break

        items: list[dict[str, Any]] = []
        for entry, score, components in deduped:
            payload = {
                "memory_id": entry.id,
                "content": entry.content,
                "scope": entry.scope,
                "entry_type": entry.entry_type,
                "tags": entry.tags,
                "source_ref": entry.source_ref,
                "content_hash": entry.content_hash,
                "confidence": entry.confidence,
                "importance": entry.importance,
                "source_label": entry.source_ref or f"memory:{entry.id}",
                "score": round(score, 4),
                "created_at": entry.created_at.isoformat(),
                "valid_from": entry.valid_from.isoformat() if entry.valid_from else None,
            }
            if debug:
                payload["debug"] = components
            items.append(payload)
        return RetrievalResult(
            items=items,
            debug={"query": query, "count": len(items), "filters": filters, "debug_mode": debug},
        )

    def _passes_filters(self, entry: MemoryEntry, filters: dict[str, Any], now: datetime) -> bool:
        if entry.metadata.get("soft_deleted") or entry.metadata.get("hard_deleted"):
            return False
        if filters.get("entry_type") and entry.entry_type != filters["entry_type"]:
            return False
        if filters.get("tag") and filters["tag"] not in entry.tags:
            return False
        if filters.get("domain") and f"domain:{filters['domain']}" not in entry.tags:
            return False
        if filters.get("source_ref") and entry.source_ref != filters["source_ref"]:
            return False
        if entry.valid_from and entry.valid_from > now:
            return False
        if entry.valid_until and entry.valid_until < now:
            return False
        return True

    def _keyword_overlap(self, query_words: set[str], content_words: list[str]) -> float:
        if not query_words:
            return 0.0
        matches = sum(1 for w in query_words if w in content_words)
        return matches / len(query_words)

    def _recency_score(self, created_at: datetime, now: datetime) -> float:
        age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
        return math.exp(-age_days / 30.0)

    def _normalize_vector(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
