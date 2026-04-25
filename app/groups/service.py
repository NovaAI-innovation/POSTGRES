from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroupPermissions:
    can_read: bool = False
    can_write: bool = False
    can_admin: bool = False


class GroupPermissionStore:
    def __init__(self) -> None:
        self._permissions: dict[tuple[str, str], GroupPermissions] = {}

    def set_permissions(self, group_id: str, agent_id: str, permissions: GroupPermissions) -> None:
        self._permissions[(group_id, agent_id)] = permissions

    def get_permissions(self, group_id: str | None, agent_id: str | None) -> GroupPermissions:
        if not group_id or not agent_id:
            return GroupPermissions()
        return self._permissions.get((group_id, agent_id), GroupPermissions())
