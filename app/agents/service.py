from __future__ import annotations


class AgentOverrideStore:
    def __init__(self) -> None:
        self._overrides: dict[str, str] = {}

    def set_override(self, agent_id: str, override: str) -> None:
        self._overrides[agent_id] = override

    def get_override(self, agent_id: str | None) -> str:
        if not agent_id:
            return "none"
        return self._overrides.get(agent_id, "none")
