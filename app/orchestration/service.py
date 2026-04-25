from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


TASK_STATUSES = {"pending", "running", "waiting_approval", "failed", "completed", "cancelled"}


@dataclass
class Task:
    task_id: str
    owner: str
    assigned_agent: str | None
    status: str
    priority: int
    deadline: str | None
    parent_task_id: str | None
    summary: str
    memory_group: str | None
    required_capabilities: list[str]
    required_tools: list[str]
    retries: int = 0
    max_retries: int = 2
    timeout_seconds: int = 120
    idempotency_key: str | None = None
    lock_key: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HandoffRecord:
    handoff_id: str
    task_id: str
    source_agent: str
    target_agent: str
    summary: str
    memory_ids: list[str]
    requested_output: str
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentProfile:
    agent_id: str
    capabilities: set[str]
    tools: set[str]
    groups: set[str]
    current_load: int = 0


class LockManager:
    def __init__(self) -> None:
        self._locks: dict[str, str] = {}

    def acquire(self, lock_key: str, holder: str) -> bool:
        if lock_key in self._locks and self._locks[lock_key] != holder:
            return False
        self._locks[lock_key] = holder
        return True

    def release(self, lock_key: str, holder: str) -> None:
        if self._locks.get(lock_key) == holder:
            del self._locks[lock_key]


class DeadLetterQueue:
    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def push(self, item: dict[str, Any]) -> None:
        self._items.append(item)

    def list_items(self) -> list[dict[str, Any]]:
        return list(self._items)


class AgentRouter:
    def __init__(self) -> None:
        self._agents: dict[str, AgentProfile] = {}

    def register_agent(self, agent_id: str, capabilities: set[str], tools: set[str], groups: set[str]) -> None:
        self._agents[agent_id] = AgentProfile(agent_id=agent_id, capabilities=capabilities, tools=tools, groups=groups)

    def route(self, required_capabilities: list[str], required_tools: list[str], memory_group: str | None) -> str | None:
        candidates: list[AgentProfile] = []
        for profile in self._agents.values():
            if not set(required_capabilities).issubset(profile.capabilities):
                continue
            if not set(required_tools).issubset(profile.tools):
                continue
            if memory_group and memory_group not in profile.groups:
                continue
            candidates.append(profile)
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.current_load)
        chosen = candidates[0]
        chosen.current_load += 1
        return chosen.agent_id

    def mark_complete(self, agent_id: str) -> None:
        profile = self._agents.get(agent_id)
        if profile and profile.current_load > 0:
            profile.current_load -= 1


class TaskQueue:
    def __init__(self, router: AgentRouter, lock_manager: LockManager, dead_letter: DeadLetterQueue) -> None:
        self._tasks: dict[str, Task] = {}
        self._idempotency: dict[str, str] = {}
        self._events: list[dict[str, Any]] = []
        self._handoffs: list[HandoffRecord] = []
        self._router = router
        self._locks = lock_manager
        self._dead_letter = dead_letter

    def create_task(
        self,
        *,
        owner: str,
        summary: str,
        priority: int = 50,
        deadline: str | None = None,
        parent_task_id: str | None = None,
        memory_group: str | None = None,
        required_capabilities: list[str] | None = None,
        required_tools: list[str] | None = None,
        idempotency_key: str | None = None,
        timeout_seconds: int = 120,
        lock_key: str | None = None,
    ) -> Task:
        if idempotency_key and idempotency_key in self._idempotency:
            return self._tasks[self._idempotency[idempotency_key]]
        assigned = self._router.route(required_capabilities or [], required_tools or [], memory_group)
        task = Task(
            task_id=str(uuid.uuid4()),
            owner=owner,
            assigned_agent=assigned,
            status="pending",
            priority=priority,
            deadline=deadline,
            parent_task_id=parent_task_id,
            summary=summary,
            memory_group=memory_group,
            required_capabilities=required_capabilities or [],
            required_tools=required_tools or [],
            timeout_seconds=timeout_seconds,
            idempotency_key=idempotency_key,
            lock_key=lock_key,
        )
        self._tasks[task.task_id] = task
        if idempotency_key:
            self._idempotency[idempotency_key] = task.task_id
        self._events.append({"event": "created", "task_id": task.task_id, "status": task.status})
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, patch: dict[str, Any]) -> Task | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        if "status" in patch and patch["status"] in TASK_STATUSES:
            task.status = patch["status"]
        if "priority" in patch:
            task.priority = int(patch["priority"])
        if "deadline" in patch:
            task.deadline = patch["deadline"]
        if "assigned_agent" in patch:
            task.assigned_agent = patch["assigned_agent"]
        task.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._events.append({"event": "updated", "task_id": task.task_id, "status": task.status})
        return task

    def cancel_task(self, task_id: str) -> Task | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = "cancelled"
        task.updated_at = datetime.now(tz=timezone.utc).isoformat()
        if task.assigned_agent:
            self._router.mark_complete(task.assigned_agent)
        if task.lock_key:
            self._locks.release(task.lock_key, task.task_id)
        self._events.append({"event": "cancelled", "task_id": task.task_id})
        return task

    def start_task(self, task_id: str) -> Task | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        if task.lock_key and not self._locks.acquire(task.lock_key, task.task_id):
            task.status = "waiting_approval"
            self._events.append({"event": "lock_wait", "task_id": task.task_id, "lock_key": task.lock_key})
            return task
        task.status = "running"
        task.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._events.append({"event": "started", "task_id": task.task_id})
        return task

    def complete_task(self, task_id: str) -> Task | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = "completed"
        task.updated_at = datetime.now(tz=timezone.utc).isoformat()
        if task.assigned_agent:
            self._router.mark_complete(task.assigned_agent)
        if task.lock_key:
            self._locks.release(task.lock_key, task.task_id)
        self._events.append({"event": "completed", "task_id": task.task_id})
        return task

    def fail_task(self, task_id: str, reason: str) -> Task | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.retries += 1
        if task.retries <= task.max_retries:
            task.status = "pending"
            self._events.append({"event": "retry", "task_id": task.task_id, "reason": reason, "retry": task.retries})
        else:
            task.status = "failed"
            self._dead_letter.push({"task_id": task.task_id, "reason": reason, "at": int(time.time())})
            self._events.append({"event": "dead_letter", "task_id": task.task_id, "reason": reason})
        task.updated_at = datetime.now(tz=timezone.utc).isoformat()
        return task

    def check_timeouts(self) -> list[str]:
        timed_out: list[str] = []
        now = datetime.now(tz=timezone.utc)
        for task in self._tasks.values():
            if task.status != "running":
                continue
            started = datetime.fromisoformat(task.updated_at.replace("Z", "+00:00"))
            if (now - started).total_seconds() > task.timeout_seconds:
                task.status = "failed"
                timed_out.append(task.task_id)
                self._dead_letter.push({"task_id": task.task_id, "reason": "timeout", "at": int(time.time())})
        return timed_out

    def handoff(
        self,
        *,
        task_id: str,
        source_agent: str,
        target_agent: str,
        summary: str,
        memory_ids: list[str],
        requested_output: str,
    ) -> HandoffRecord | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        record = HandoffRecord(
            handoff_id=str(uuid.uuid4()),
            task_id=task_id,
            source_agent=source_agent,
            target_agent=target_agent,
            summary=summary,
            memory_ids=memory_ids,
            requested_output=requested_output,
        )
        task.assigned_agent = target_agent
        task.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._handoffs.append(record)
        self._events.append({"event": "handoff", "task_id": task_id, "to": target_agent})
        return record

    def list_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def list_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def list_handoffs(self) -> list[HandoffRecord]:
        return list(self._handoffs)

    def snapshot(self) -> dict[str, Any]:
        return {
            "tasks": [task.to_dict() for task in self._tasks.values()],
            "events": self._events,
            "handoffs": [handoff.to_dict() for handoff in self._handoffs],
            "idempotency": self._idempotency,
        }

    def restore(self, payload: dict[str, Any]) -> None:
        self._tasks.clear()
        self._events = list(payload.get("events", []))
        self._handoffs = [HandoffRecord(**item) for item in payload.get("handoffs", [])]
        self._idempotency = dict(payload.get("idempotency", {}))
        for raw in payload.get("tasks", []):
            task = Task(**raw)
            self._tasks[task.task_id] = task

    def dumps(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=True)

    def loads(self, serialized: str) -> None:
        self.restore(json.loads(serialized))
