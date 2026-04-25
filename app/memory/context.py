from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ContextBudgets:
    memory_tokens: int
    tool_tokens: int
    history_tokens: int


class ContextAssembler:
    def assemble(
        self,
        memories: list[dict[str, Any]],
        budgets: ContextBudgets,
        tool_results: list[str] | None = None,
        history: list[str] | None = None,
    ) -> dict[str, Any]:
        deduped = self._compress(memories)
        grouped = self._group(deduped)
        resolved, conflicts = self._resolve_conflicts(grouped["project_facts"])
        grouped["project_facts"] = resolved

        memory_block = self._render_sections(grouped)
        memory_block = self._truncate_to_budget(memory_block, budgets.memory_tokens)
        tool_block = self._truncate_to_budget("\n".join(tool_results or []), budgets.tool_tokens)
        history_block = self._truncate_to_budget("\n".join(history or []), budgets.history_tokens)

        return {
            "memory_block": memory_block,
            "tool_block": tool_block,
            "history_block": history_block,
            "conflicts": conflicts,
            "budgets": {
                "memory_tokens": self._estimate_tokens(memory_block),
                "tool_tokens": self._estimate_tokens(tool_block),
                "history_tokens": self._estimate_tokens(history_block),
            },
        }

    def _group(self, memories: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped = {
            "preferences": [],
            "project_facts": [],
            "recent_events": [],
            "task_memories": [],
            "warnings_constraints": [],
        }
        for item in memories:
            tags = item.get("tags", [])
            entry_type = item.get("entry_type", "message")
            content_l = item.get("content", "").lower()
            if any("preference" in t for t in tags):
                grouped["preferences"].append(item)
            elif entry_type == "fact":
                grouped["project_facts"].append(item)
            elif entry_type == "episode":
                grouped["recent_events"].append(item)
            elif any("constraint" in t for t in tags) or any(k in content_l for k in ("must", "never", "cannot")):
                grouped["warnings_constraints"].append(item)
            else:
                grouped["task_memories"].append(item)
        return grouped

    def _compress(self, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compressed: dict[str, dict[str, Any]] = {}
        for item in memories:
            key = item.get("content_hash") or item.get("content")
            if key not in compressed:
                compressed[key] = dict(item)
                compressed[key]["source_refs"] = [item.get("source_label") or item.get("source_ref") or item.get("memory_id")]
                continue
            source = item.get("source_label") or item.get("source_ref") or item.get("memory_id")
            if source not in compressed[key]["source_refs"]:
                compressed[key]["source_refs"].append(source)
            compressed[key]["confidence"] = max(compressed[key].get("confidence", 0.0), item.get("confidence", 0.0))
        return list(compressed.values())

    def _resolve_conflicts(self, facts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        by_subject: dict[str, list[dict[str, Any]]] = {}
        for fact in facts:
            subject = self._subject_key(fact.get("content", ""))
            by_subject.setdefault(subject, []).append(fact)

        resolved: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        for subject, entries in by_subject.items():
            if len(entries) == 1:
                resolved.append(entries[0])
                continue
            ranked = sorted(
                entries,
                key=lambda e: (
                    self._parse_dt(e.get("valid_from")) or self._parse_dt(e.get("created_at")) or datetime.min,
                    e.get("confidence", 0.0),
                ),
                reverse=True,
            )
            top = ranked[0]
            tied = [e for e in ranked if (e.get("confidence", 0.0) == top.get("confidence", 0.0))]
            if len(tied) > 1:
                conflicts.append({"subject": subject, "entries": tied})
            resolved.append(top)
        return resolved, conflicts

    def _render_sections(self, grouped: dict[str, list[dict[str, Any]]]) -> str:
        order = [
            ("Preferences", grouped["preferences"]),
            ("Project Facts", grouped["project_facts"]),
            ("Recent Events", grouped["recent_events"]),
            ("Task Memories", grouped["task_memories"]),
            ("Warnings/Constraints", grouped["warnings_constraints"]),
        ]
        lines: list[str] = []
        for title, entries in order:
            if not entries:
                continue
            lines.append(f"{title}:")
            for entry in entries:
                refs = entry.get("source_refs") or [entry.get("source_label") or entry.get("memory_id")]
                ref_text = ",".join(str(r) for r in refs if r)
                lines.append(
                    f"- {entry.get('content')} [src:{ref_text}] [scope:{entry.get('scope')}] [conf:{entry.get('confidence', 0):.2f}]"
                )
        return "\n".join(lines).strip()

    def _truncate_to_budget(self, text: str, max_tokens: int) -> str:
        words = text.split()
        token_budget = max(0, max_tokens * 4)
        if len(words) <= token_budget:
            return text
        return " ".join(words[:token_budget])

    def _estimate_tokens(self, text: str) -> int:
        if not text.strip():
            return 0
        return max(1, len(text.split()) // 4)

    def _subject_key(self, content: str) -> str:
        if "=" in content:
            return content.split("=")[0].strip().lower()
        if ":" in content:
            return content.split(":")[0].strip().lower()
        return " ".join(content.lower().split()[:3])

    def _parse_dt(self, raw: Any) -> datetime | None:
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
