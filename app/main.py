from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass
from typing import Any

from app.admin.service import AdminAuthorizationError, AdminController
from app.agents.service import AgentOverrideStore
from app.auth.middleware import AuthError, AuthMiddleware
from app.config import Settings
from app.embeddings.service import EmbeddingService
from app.eval.harness import EvalHarness, HumanReviewQueue
from app.groups.service import GroupPermissionStore
from app.lifecycle.service import BackupManager, LifecycleManager, TenantRetentionPolicy
from app.memory.context import ContextAssembler, ContextBudgets
from app.memory.ingestion import MemoryIngestionWorker
from app.memory.repository import MemoryRepository
from app.memory.repository_factory import build_memory_repository
from app.memory.retrieval import MemoryRetrievalService
from app.memory.service import MemoryService
from app.observability.audit import AuditLogger
from app.observability.logger import configure_logging
from app.observability.metrics import MetricsStore
from app.observability.tracing import Trace, Tracer
from app.orchestration.service import AgentRouter, DeadLetterQueue, LockManager, TaskQueue
from app.permissions.policy_engine import PolicyEngine
from app.safety.guardrails import (
    InputScanner,
    MemoryGuardrail,
    OutputValidator,
    RedactionService,
    UntrustedOutputQuarantine,
)
from app.tools.service import (
    AgentToolAllowlistStore,
    ToolApprovalStore,
    ToolDefinition,
    ToolRegistry,
    ToolRunner,
    ToolAuditLog,
)


@dataclass(frozen=True)
class Response:
    status_code: int
    body: dict[str, Any]


class Application:
    def __init__(
        self,
        settings: Settings | None = None,
        memory_repository: MemoryRepository | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        configure_logging(self.settings.log_level)

        self.audit = AuditLogger()
        self.metrics = MetricsStore()
        self.tracer = Tracer()
        self.review_queue = HumanReviewQueue()
        self.admin = AdminController()

        self.auth = AuthMiddleware(self.settings, self.audit)
        self.groups = GroupPermissionStore()
        self.agent_overrides = AgentOverrideStore()
        self.policy = PolicyEngine(self.groups, self.agent_overrides, self.audit)
        self.memory = MemoryService(memory_repository or build_memory_repository(self.settings))
        self.embeddings = EmbeddingService(self.settings.embedding_model)
        self.ingestion = MemoryIngestionWorker(self.memory, self.embeddings)
        self.retrieval = MemoryRetrievalService(self.memory, self.policy, self.embeddings)
        self.context_assembler = ContextAssembler()

        self.input_scanner = InputScanner()
        self.memory_guardrail = MemoryGuardrail(self.input_scanner)
        self.output_validator = OutputValidator()
        self.redaction = RedactionService()
        self.quarantine = UntrustedOutputQuarantine()

        self.tools = ToolRegistry()
        self.tool_approvals = ToolApprovalStore()
        self.tool_audit = ToolAuditLog()
        self.tool_allowlists = AgentToolAllowlistStore()
        self.tool_runner = ToolRunner(self.tool_audit, self.tool_approvals)

        self.router = AgentRouter()
        self.lock_manager = LockManager()
        self.dead_letter = DeadLetterQueue()
        self.tasks = TaskQueue(self.router, self.lock_manager, self.dead_letter)

        self.backup_manager = BackupManager(pathlib.Path.cwd() / "backups")
        self.lifecycle = LifecycleManager(self.memory, self.backup_manager)
        self.eval_harness = EvalHarness(self, pathlib.Path.cwd() / "eval" / "datasets")

        self._register_default_tools()
        self._register_default_agents()

    def _register_default_tools(self) -> None:
        self.tools.register(
            ToolDefinition(
                name="echo",
                description="Return payload as echo.",
                input_schema={"value": "int"},
                output_schema={"status": "str", "tool": "str"},
                permissions_required=("tool:echo",),
                timeout_seconds=self.settings.tool_timeout_seconds,
                rate_limit_per_minute=120,
                destructive=False,
                handler=lambda payload: {"status": "ok", "tool": "echo", "echo": payload["value"]},
            )
        )
        self.tools.register(
            ToolDefinition(
                name="external_send",
                description="Send content externally.",
                input_schema={"destination": "str", "payload": "str"},
                output_schema={"status": "str", "tool": "str"},
                permissions_required=("tool:external_send",),
                timeout_seconds=self.settings.tool_timeout_seconds,
                rate_limit_per_minute=10,
                destructive=True,
                approval_category="external_send",
                handler=lambda payload: {"status": "ok", "tool": "external_send"},
            )
        )
        self.tools.register(
            ToolDefinition(
                name="delete_memory",
                description="Delete memory item.",
                input_schema={"memory_id": "str"},
                output_schema={"status": "str", "tool": "str"},
                permissions_required=("tool:delete_memory",),
                timeout_seconds=self.settings.tool_timeout_seconds,
                rate_limit_per_minute=5,
                destructive=True,
                approval_category="deletion",
                handler=lambda payload: {"status": "ok", "tool": "delete_memory"},
            )
        )

    def _register_default_agents(self) -> None:
        self.router.register_agent("agent-a", {"general", "memory"}, {"echo"}, {"group-1", "group-9"})
        self.router.register_agent("agent-b", {"general", "tooling"}, {"echo", "external_send"}, {"group-9"})

    def handle(self, method: str, path: str, headers: dict[str, str], body: str | None = None) -> Response:
        req_start = time.monotonic()
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        request_id = self.auth.request_id(normalized_headers)
        trace = self.tracer.start_trace(request_id)
        request_span = self.tracer.start_span(trace, "agent_request", {"method": method, "path": path})

        if method == "GET" and path == "/health":
            self.tracer.end_span(request_span, {"status": 200})
            return Response(200, {"status": "ok"})

        try:
            identity = self.auth.authenticate(normalized_headers)
        except AuthError as exc:
            self._log_request_error(request_id, trace.trace_id, path, method, exc.status_code, exc.message)
            self.tracer.end_span(request_span, {"status": exc.status_code, "error": exc.message})
            return Response(exc.status_code, {"error": exc.message, "meta": {"request_id": request_id, "trace_id": trace.trace_id}})

        if identity.subject_id in self.admin.revoked_subjects:
            self._log_request_error(identity.request_id, trace.trace_id, path, method, 401, "credentials_revoked")
            self.tracer.end_span(request_span, {"status": 401, "error": "credentials_revoked"})
            return Response(401, {"error": "credentials_revoked"})

        try:
            response = self._handle_authed(method, path, identity, body, trace)
        except Exception as exc:
            self._log_request_error(identity.request_id, trace.trace_id, path, method, 503, f"backend_unavailable:{exc}")
            self.tracer.end_span(request_span, {"status": 503, "error": "backend_unavailable"})
            return Response(
                503,
                {
                    "error": "backend_unavailable",
                    "reason": str(exc),
                    "meta": {"request_id": identity.request_id, "trace_id": trace.trace_id},
                },
            )
        elapsed_ms = (time.monotonic() - req_start) * 1000
        self.metrics.observe_ms("request_latency_ms", elapsed_ms, {"path": path, "method": method})
        if response.status_code >= 400:
            self.metrics.inc("request_errors")

        self.audit.emit_request_event(
            request_id=identity.request_id,
            tenant_id=identity.tenant_id,
            agent_id=identity.agent_id,
            trace_id=trace.trace_id,
            path=path,
            method=method,
            status_code=response.status_code,
            error=response.body.get("error"),
        )
        self.tracer.end_span(request_span, {"status": response.status_code})

        if "meta" not in response.body:
            response.body["meta"] = {}
        response.body["meta"]["trace_id"] = trace.trace_id
        response.body["meta"]["request_id"] = identity.request_id
        return response

    def _log_request_error(self, request_id: str, trace_id: str, path: str, method: str, status: int, error: str) -> None:
        self.metrics.inc("request_errors")
        self.audit.emit_request_event(
            request_id=request_id,
            tenant_id=None,
            agent_id=None,
            trace_id=trace_id,
            path=path,
            method=method,
            status_code=status,
            error=error,
        )

    def _handle_authed(self, method: str, path: str, identity, body: str | None, trace: Trace) -> Response:
        if method == "GET" and path == "/tools":
            return Response(200, {"tools": self.tools.list_names()})

        if method == "GET" and path == "/tool-calls":
            return Response(200, {"tool_calls": [r.__dict__ for r in self.tool_audit.list_recent(100)]})

        if method == "GET" and path == "/audit-events":
            events = self.audit.list_events(limit=300) + self.admin.admin_events
            return Response(200, {"events": events[-300:]})

        if method == "GET" and path == "/policy-decisions":
            return Response(200, {"policy_decisions": self.audit.list_events(event_type="policy_decision", limit=200)})

        if method == "GET" and path == "/observability/metrics":
            return Response(200, {"metrics": self.metrics.snapshot()})

        if method == "GET" and path == "/observability/traces":
            return Response(200, {"traces": self.tracer.list_traces()})

        if method == "GET" and path == "/eval/review-queue":
            return Response(200, {"queue": self.review_queue.list_items()})

        if method == "POST" and path == "/eval/run":
            summary = self.eval_harness.run()
            thresholds = _load_release_thresholds(pathlib.Path.cwd() / "eval" / "release_gates.json")
            gate = self.eval_harness.release_gate(summary, thresholds)
            return Response(200, {"summary": summary, "release_gate": gate})

        if method == "POST" and path == "/memory":
            return self._handle_memory_create(identity, body, trace)

        if method == "POST" and path == "/memory/ingest":
            return self._handle_memory_ingest(identity, body, trace)

        if method == "GET" and path.startswith("/memory/"):
            memory_id = path.removeprefix("/memory/")
            entry = self.memory.get(memory_id, tenant_id=identity.tenant_id or "")
            if not entry:
                return Response(404, {"error": "not_found"})
            decision = self.policy.can_read_memory(identity, entry)
            if not decision.allowed:
                return Response(403, {"error": "forbidden", "reason": decision.reason})
            return Response(200, {"memory": entry.to_dict()})

        if method == "POST" and path.startswith("/memory/") and path.endswith("/redact"):
            memory_id = path.removeprefix("/memory/").removesuffix("/redact").strip("/")
            entry = self.memory.get(memory_id, tenant_id=identity.tenant_id or "")
            if not entry:
                return Response(404, {"error": "not_found"})
            entry.content = self.redaction.redact(entry.content)
            entry.metadata["redacted"] = True
            return Response(200, {"memory": entry.to_dict()})

        if method == "POST" and path.startswith("/tools/") and (path.endswith("/run") or path.endswith("/dry-run")):
            dry_run = path.endswith("/dry-run")
            tool_name = path.removeprefix("/tools/").removesuffix("/run").removesuffix("/dry-run").strip("/")
            return self._handle_tool_call(identity, tool_name, body, dry_run=dry_run, trace=trace)

        if method == "POST" and path.startswith("/tool-approvals/") and path.endswith("/approve"):
            approval_id = path.removeprefix("/tool-approvals/").removesuffix("/approve").strip("/")
            record = self.tool_approvals.approve(approval_id, approved_by=identity.subject_id or "unknown")
            if not record:
                return Response(404, {"error": "not_found"})
            return Response(200, {"approval": record.__dict__})

        if method == "POST" and path.startswith("/tool-approvals/") and path.endswith("/reject"):
            approval_id = path.removeprefix("/tool-approvals/").removesuffix("/reject").strip("/")
            record = self.tool_approvals.reject(approval_id, approved_by=identity.subject_id or "unknown")
            if not record:
                return Response(404, {"error": "not_found"})
            return Response(200, {"approval": record.__dict__})

        if method == "POST" and path == "/memory/search":
            payload = _parse_json(body)
            query = payload.get("query")
            if not isinstance(query, str) or not query.strip():
                return Response(400, {"error": "query is required"})
            retrieval_span = self.tracer.start_span(trace, "retrieval")
            result = self.retrieval.retrieve_memory(
                identity=identity,
                query=query,
                filters=payload.get("filters", {}),
                debug=bool(payload.get("debug", False)),
                limit=int(payload.get("limit", 10)),
            )
            self.tracer.end_span(retrieval_span, {"count": len(result.items)})
            self.metrics.observe_ms("retrieval_latency_ms", 1.0)
            return Response(200, {"items": result.items, "debug": result.debug})

        if method == "POST" and path == "/context/assemble":
            payload = _parse_json(body)
            query = payload.get("query", "")
            retrieval = self.retrieval.retrieve_memory(
                identity=identity,
                query=query,
                filters=payload.get("filters", {}),
                debug=bool(payload.get("debug", False)),
                limit=int(payload.get("limit", 20)),
            )
            budgets_payload = payload.get("budgets", {})
            budgets = ContextBudgets(
                memory_tokens=int(budgets_payload.get("memory_tokens", 512)),
                tool_tokens=int(budgets_payload.get("tool_tokens", 256)),
                history_tokens=int(budgets_payload.get("history_tokens", 512)),
            )
            context = self.context_assembler.assemble(
                memories=retrieval.items,
                budgets=budgets,
                tool_results=payload.get("tool_results", []),
                history=payload.get("history", []),
            )
            for item in retrieval.items:
                if float(item.get("confidence", 1.0)) < 0.4:
                    self.review_queue.enqueue({"type": "low_confidence_retrieval", "memory_id": item.get("memory_id")})
            self.metrics.set_gauge("token_usage_memory", context["budgets"]["memory_tokens"])
            return Response(200, {"context": context, "retrieval_debug": retrieval.debug})

        if path.startswith("/tasks"):
            return self._handle_tasks(method, path, identity, body)

        if path.startswith("/lifecycle"):
            return self._handle_lifecycle(method, path, identity, body)

        if path.startswith("/admin"):
            return self._handle_admin(method, path, identity, body)

        return Response(404, {"error": "not_found"})

    def _handle_tasks(self, method: str, path: str, identity, body: str | None) -> Response:
        payload = _parse_json(body)
        if method == "POST" and path == "/tasks":
            if self.admin.emergency.paused:
                return Response(503, {"error": "agents_paused"})
            task = self.tasks.create_task(
                owner=identity.subject_id or "unknown",
                summary=payload.get("summary", ""),
                priority=int(payload.get("priority", 50)),
                deadline=payload.get("deadline"),
                parent_task_id=payload.get("parent_task_id"),
                memory_group=payload.get("memory_group"),
                required_capabilities=payload.get("required_capabilities", []),
                required_tools=payload.get("required_tools", []),
                idempotency_key=payload.get("idempotency_key"),
                timeout_seconds=int(payload.get("timeout_seconds", 120)),
                lock_key=payload.get("lock_key"),
            )
            return Response(201, {"task": task.to_dict()})

        if method == "GET" and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/")
            task = self.tasks.get_task(task_id)
            if not task:
                return Response(404, {"error": "not_found"})
            return Response(200, {"task": task.to_dict(), "events": self.tasks.list_events()[-20:]})

        if method == "PATCH" and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/")
            task = self.tasks.update_task(task_id, payload)
            if not task:
                return Response(404, {"error": "not_found"})
            return Response(200, {"task": task.to_dict()})

        if method == "POST" and path.endswith("/cancel") and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/").removesuffix("/cancel").strip("/")
            task = self.tasks.cancel_task(task_id)
            if not task:
                return Response(404, {"error": "not_found"})
            return Response(200, {"task": task.to_dict()})

        if method == "POST" and path.endswith("/handoff") and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/").removesuffix("/handoff").strip("/")
            record = self.tasks.handoff(
                task_id=task_id,
                source_agent=payload.get("source_agent", identity.agent_id or "unknown"),
                target_agent=payload.get("target_agent", ""),
                summary=payload.get("summary", ""),
                memory_ids=payload.get("memory_ids", []),
                requested_output=payload.get("requested_output", ""),
            )
            if not record:
                return Response(404, {"error": "not_found"})
            return Response(200, {"handoff": record.to_dict()})

        if method == "POST" and path.endswith("/start") and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/").removesuffix("/start").strip("/")
            task = self.tasks.start_task(task_id)
            if not task:
                return Response(404, {"error": "not_found"})
            return Response(200, {"task": task.to_dict()})

        if method == "POST" and path.endswith("/complete") and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/").removesuffix("/complete").strip("/")
            task = self.tasks.complete_task(task_id)
            if not task:
                return Response(404, {"error": "not_found"})
            return Response(200, {"task": task.to_dict()})

        if method == "POST" and path.endswith("/fail") and path.startswith("/tasks/"):
            task_id = path.removeprefix("/tasks/").removesuffix("/fail").strip("/")
            task = self.tasks.fail_task(task_id, payload.get("reason", "unknown"))
            if not task:
                return Response(404, {"error": "not_found"})
            return Response(200, {"task": task.to_dict(), "dead_letter": self.dead_letter.list_items()})

        if method == "GET" and path == "/tasks":
            return Response(
                200,
                {
                    "tasks": [task.to_dict() for task in self.tasks.list_tasks()],
                    "dead_letter": self.dead_letter.list_items(),
                    "handoffs": [h.to_dict() for h in self.tasks.list_handoffs()],
                },
            )
        return Response(404, {"error": "not_found"})

    def _handle_lifecycle(self, method: str, path: str, identity, body: str | None) -> Response:
        payload = _parse_json(body)
        tenant_id = identity.tenant_id or ""
        if method == "POST" and path == "/lifecycle/retention":
            policy = TenantRetentionPolicy(
                tenant_id=tenant_id,
                message_days=int(payload.get("message_days", 90)),
                sensitive_days=int(payload.get("sensitive_days", 7)),
                soft_delete_days=int(payload.get("soft_delete_days", 30)),
            )
            self.lifecycle.set_retention_policy(policy)
            return Response(200, {"policy": policy.__dict__})

        if method == "POST" and path == "/lifecycle/maintenance":
            report = self.lifecycle.run_maintenance(tenant_id)
            return Response(200, {"report": report})

        if method == "POST" and path == "/lifecycle/backup":
            backup_name = self.lifecycle.backup(tenant_id, name=payload.get("name"))
            return Response(200, {"backup": backup_name, "all_backups": self.lifecycle.list_backups()})

        if method == "POST" and path == "/lifecycle/restore":
            file_name = payload.get("file_name")
            if not isinstance(file_name, str) or not file_name:
                return Response(400, {"error": "file_name is required"})
            restored = self.lifecycle.restore(file_name)
            return Response(200, {"restored": restored})

        if method == "GET" and path == "/lifecycle/backups":
            return Response(200, {"backups": self.lifecycle.list_backups()})

        return Response(404, {"error": "not_found"})

    def _handle_admin(self, method: str, path: str, identity, body: str | None) -> Response:
        payload = _parse_json(body)
        try:
            self.admin.ensure_admin(identity)
        except AdminAuthorizationError as exc:
            return Response(403, {"error": str(exc)})

        if method == "GET" and path == "/admin/console":
            self._audit_admin(identity, "view_console")
            return Response(200, {"html": self.admin.render_console_html()})

        if method == "POST" and path == "/admin/pause-agents":
            self.admin.emergency.paused = True
            self._audit_admin(identity, "pause_agents")
            return Response(200, {"paused": True})

        if method == "POST" and path == "/admin/resume-agents":
            self.admin.emergency.paused = False
            self._audit_admin(identity, "resume_agents")
            return Response(200, {"paused": False})

        if method == "POST" and path == "/admin/block-shared-memory-writes":
            self.admin.emergency.block_shared_memory_writes = True
            self._audit_admin(identity, "block_shared_memory_writes")
            return Response(200, {"block_shared_memory_writes": True})

        if method == "POST" and path == "/admin/unblock-shared-memory-writes":
            self.admin.emergency.block_shared_memory_writes = False
            self._audit_admin(identity, "unblock_shared_memory_writes")
            return Response(200, {"block_shared_memory_writes": False})

        if method == "POST" and path == "/admin/disable-tool-class":
            category = payload.get("category")
            if not category:
                return Response(400, {"error": "category is required"})
            self.admin.disabled_tool_classes.add(category)
            self._audit_admin(identity, "disable_tool_class", {"category": category})
            return Response(200, {"disabled_tool_classes": sorted(self.admin.disabled_tool_classes)})

        if method == "POST" and path == "/admin/enable-tool-class":
            category = payload.get("category")
            if category in self.admin.disabled_tool_classes:
                self.admin.disabled_tool_classes.remove(category)
            self._audit_admin(identity, "enable_tool_class", {"category": category})
            return Response(200, {"disabled_tool_classes": sorted(self.admin.disabled_tool_classes)})

        if method == "POST" and path == "/admin/revoke-credentials":
            subject_id = payload.get("subject_id")
            if not subject_id:
                return Response(400, {"error": "subject_id is required"})
            self.admin.revoked_subjects.add(subject_id)
            self._audit_admin(identity, "revoke_credentials", {"subject_id": subject_id})
            return Response(200, {"revoked_subjects": sorted(self.admin.revoked_subjects)})

        if method == "POST" and path.startswith("/admin/agents/") and path.endswith("/disable"):
            agent_id = path.removeprefix("/admin/agents/").removesuffix("/disable").strip("/")
            self.agent_overrides.set_override(agent_id, "blocked")
            self._audit_admin(identity, "disable_agent", {"agent_id": agent_id})
            return Response(200, {"agent_id": agent_id, "override": "blocked"})

        if method == "POST" and path.startswith("/admin/agents/") and path.endswith("/read-only"):
            agent_id = path.removeprefix("/admin/agents/").removesuffix("/read-only").strip("/")
            self.agent_overrides.set_override(agent_id, "read_only")
            self._audit_admin(identity, "set_agent_read_only", {"agent_id": agent_id})
            return Response(200, {"agent_id": agent_id, "override": "read_only"})

        if method == "POST" and path.startswith("/admin/memory/") and path.endswith("/delete"):
            memory_id = path.removeprefix("/admin/memory/").removesuffix("/delete").strip("/")
            entry = self.memory.get(memory_id, identity.tenant_id or "")
            if not entry:
                return Response(404, {"error": "not_found"})
            entry.metadata["soft_deleted"] = True
            self._audit_admin(identity, "delete_memory", {"memory_id": memory_id})
            return Response(200, {"memory": entry.to_dict()})

        if method == "POST" and path.startswith("/admin/memory/") and path.endswith("/restore"):
            memory_id = path.removeprefix("/admin/memory/").removesuffix("/restore").strip("/")
            entry = self.memory.get(memory_id, identity.tenant_id or "")
            if not entry:
                return Response(404, {"error": "not_found"})
            entry.metadata["soft_deleted"] = False
            entry.metadata["hard_deleted"] = False
            self._audit_admin(identity, "restore_memory", {"memory_id": memory_id})
            return Response(200, {"memory": entry.to_dict()})

        if method == "POST" and path.startswith("/admin/memory/") and path.endswith("/scores"):
            memory_id = path.removeprefix("/admin/memory/").removesuffix("/scores").strip("/")
            entry = self.memory.get(memory_id, identity.tenant_id or "")
            if not entry:
                return Response(404, {"error": "not_found"})
            if "importance" in payload:
                entry.importance = int(payload["importance"])
            if "confidence" in payload:
                entry.confidence = float(payload["confidence"])
            self._audit_admin(identity, "adjust_scores", {"memory_id": memory_id})
            return Response(200, {"memory": entry.to_dict()})

        if method == "GET" and path == "/admin/memory/search":
            query = payload.get("query", "")
            result = self.retrieval.retrieve_memory(identity, query=query, filters=payload.get("filters", {}), debug=True, limit=50)
            self._audit_admin(identity, "memory_search", {"query": query})
            return Response(200, {"items": result.items, "debug": result.debug})

        if method == "GET" and path.startswith("/admin/memory/"):
            memory_id = path.removeprefix("/admin/memory/")
            entry = self.memory.get(memory_id, identity.tenant_id or "")
            if not entry:
                return Response(404, {"error": "not_found"})
            self._audit_admin(identity, "memory_detail", {"memory_id": memory_id})
            return Response(200, {"memory": entry.to_dict()})

        if method == "GET" and path == "/admin/tasks":
            self._audit_admin(identity, "view_tasks")
            return Response(200, {"tasks": [t.to_dict() for t in self.tasks.list_tasks()], "dead_letter": self.dead_letter.list_items()})

        if method == "GET" and path == "/admin/tool-calls":
            self._audit_admin(identity, "view_tool_calls")
            return Response(200, {"tool_calls": [r.__dict__ for r in self.tool_audit.list_recent(200)]})

        if method == "GET" and path == "/admin/approvals":
            pending = []
            for approval_id in payload.get("approval_ids", []):
                record = self.tool_approvals.get(approval_id)
                if record:
                    pending.append(record.__dict__)
            self._audit_admin(identity, "view_approvals")
            return Response(200, {"approvals": pending})

        if method == "GET" and path == "/admin/audit-events":
            self._audit_admin(identity, "view_admin_audit")
            return Response(200, {"admin_events": self.admin.admin_events[-200:]})

        if method == "POST" and path == "/admin/prompt-context":
            query = payload.get("query", "")
            retrieval = self.retrieval.retrieve_memory(identity, query=query, filters=payload.get("filters", {}), debug=True, limit=20)
            context = self.context_assembler.assemble(
                memories=retrieval.items,
                budgets=ContextBudgets(memory_tokens=256, tool_tokens=128, history_tokens=256),
                tool_results=[],
                history=[],
            )
            self._audit_admin(identity, "inspect_prompt_context", {"query": query})
            return Response(200, {"context": context, "retrieval_debug": retrieval.debug})

        return Response(404, {"error": "not_found"})

    def _audit_admin(self, identity, action: str, payload: dict[str, Any] | None = None) -> None:
        self.admin.audit(identity, action, payload)
        self.audit.emit_admin_action(
            request_id=identity.request_id,
            tenant_id=identity.tenant_id,
            actor=identity.subject_id,
            action=action,
            payload=payload,
        )

    def _handle_memory_create(self, identity, body: str | None, trace: Trace) -> Response:
        if self.admin.emergency.paused:
            return Response(503, {"error": "agents_paused"})
        payload = _parse_json(body)
        owner_agent_id = payload.get("owner_agent_id") or identity.agent_id
        scope = payload.get("scope", "isolated")
        if scope == "shared" and self.admin.emergency.block_shared_memory_writes:
            return Response(403, {"error": "shared_memory_writes_blocked"})
        group_id = payload.get("group_id")
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            return Response(400, {"error": "content is required"})
        if not isinstance(owner_agent_id, str) or not owner_agent_id:
            return Response(400, {"error": "owner_agent_id is required"})

        decision = self.policy.can_write_memory(identity, scope=scope, group_id=group_id, owner_agent_id=owner_agent_id)
        if not decision.allowed:
            return Response(403, {"error": "forbidden", "reason": decision.reason})

        guard = self.memory_guardrail.evaluate_write(content, scope)
        if not guard.allow:
            if guard.escalation == "human_approval":
                self.review_queue.enqueue({"type": "memory_write", "reason": guard.reason, "content": self.redaction.redact(content)})
            return Response(403, {"error": "guardrail_block", "reason": guard.reason, "fallback": guard.safe_fallback})

        if scope == "shared":
            admin = self.policy.can_admin_group(identity, group_id or "")
            if not admin.allowed:
                return Response(403, {"error": "forbidden", "reason": "shared_write_requires_admin"})

        db_span = self.tracer.start_span(trace, "db", {"op": "memory_create"})
        embedding_start = time.monotonic()
        embedding = self.embeddings.embed(content)
        self.metrics.observe_ms("embedding_latency_ms", (time.monotonic() - embedding_start) * 1000)
        if not self.embeddings.validate(embedding):
            self.metrics.inc("embedding_errors")
            self.tracer.end_span(db_span, {"status": "error"})
            return Response(500, {"error": "embedding_dimension_mismatch"})
        valid_until = _parse_dt(payload.get("valid_until"))
        metadata = payload.get("metadata", {})
        if guard.sensitive:
            metadata["sensitive"] = True
            if not valid_until:
                valid_until = self.memory_guardrail.sensitive_expiry()
        entry = self.memory.create(
            tenant_id=identity.tenant_id or "",
            owner_agent_id=owner_agent_id,
            scope=scope,
            content=content,
            group_id=group_id,
            entry_type=payload.get("entry_type", "message"),
            tags=payload.get("tags", []),
            source_ref=payload.get("source_ref"),
            embedding=embedding,
            content_hash=payload.get("content_hash"),
            importance=int(payload.get("importance", 50)),
            confidence=float(payload.get("confidence", 0.5)),
            valid_from=_parse_dt(payload.get("valid_from")),
            valid_until=valid_until,
            metadata=metadata,
        )
        self.metrics.inc("memory_writes")
        self.tracer.end_span(db_span, {"status": "ok", "memory_id": entry.id})
        return Response(201, {"memory": entry.to_dict()})

    def _handle_memory_ingest(self, identity, body: str | None, trace: Trace) -> Response:
        if self.admin.emergency.paused:
            return Response(503, {"error": "agents_paused"})
        payload = _parse_json(body)
        owner_agent_id = payload.get("owner_agent_id") or identity.agent_id
        scope = payload.get("scope", "isolated")
        if scope == "shared" and self.admin.emergency.block_shared_memory_writes:
            return Response(403, {"error": "shared_memory_writes_blocked"})
        group_id = payload.get("group_id")
        raw_content = payload.get("raw_content") or payload.get("content")
        if not isinstance(raw_content, str) or not raw_content.strip():
            return Response(400, {"error": "raw_content is required"})
        decision = self.policy.can_write_memory(identity, scope=scope, group_id=group_id, owner_agent_id=owner_agent_id)
        if not decision.allowed:
            return Response(403, {"error": "forbidden", "reason": decision.reason})

        guard = self.memory_guardrail.evaluate_write(raw_content, scope)
        if not guard.allow:
            return Response(403, {"error": "guardrail_block", "reason": guard.reason, "fallback": guard.safe_fallback})

        ingest_span = self.tracer.start_span(trace, "db", {"op": "ingestion"})
        result = self.ingestion.ingest(
            tenant_id=identity.tenant_id or "",
            owner_agent_id=owner_agent_id,
            scope=scope,
            raw_content=raw_content,
            source_ref=payload.get("source_ref"),
            group_id=group_id,
            metadata=payload.get("metadata", {}),
        )
        self.tracer.end_span(ingest_span, {"inserted": result.inserted, "reason": result.reason})
        status = 201 if result.inserted else 200
        return Response(
            status,
            {
                "inserted": result.inserted,
                "reason": result.reason,
                "debug": result.debug,
                "memory": result.memory.to_dict() if result.memory else None,
            },
        )

    def _handle_tool_call(self, identity, tool_name: str, body: str | None, dry_run: bool, trace: Trace) -> Response:
        if self.admin.emergency.paused:
            return Response(503, {"error": "agents_paused"})
        definition = self.tools.get(tool_name)
        if not definition:
            return Response(404, {"error": "tool_not_found"})

        if definition.approval_category and definition.approval_category in self.admin.disabled_tool_classes:
            return Response(403, {"error": "tool_class_disabled", "category": definition.approval_category})

        if not self.tool_allowlists.is_allowed(identity.agent_id, tool_name):
            return Response(403, {"error": "forbidden", "reason": "tool_not_allowlisted"})

        decision = self.policy.can_call_tool(identity, tool_name, allowed_tools=set(self.tools.list_names()))
        if not decision.allowed:
            return Response(403, {"error": "forbidden", "reason": decision.reason})

        payload = _parse_json(body)
        approval_id = payload.get("approval_id")
        if definition.destructive and not approval_id:
            requested = self.tool_approvals.request(
                tool_name=tool_name,
                requested_by=identity.subject_id or "unknown",
                reason=f"{definition.approval_category or 'destructive'} requires approval",
            )
            return Response(202, {"approval_required": True, "approval_id": requested.id})

        scanned = self.input_scanner.scan(json.dumps(payload))
        if not scanned.allow:
            return Response(403, {"error": "guardrail_block", "reason": scanned.reason})

        tool_span = self.tracer.start_span(trace, "tool_call", {"tool": tool_name, "dry_run": dry_run})
        result = self.tool_runner.run(
            definition,
            payload,
            agent_id=identity.agent_id,
            dry_run=dry_run,
            approval_id=approval_id,
            retries=2,
        )
        self.tracer.end_span(tool_span, {"status": result.get("status")})

        validation = self.output_validator.validate(result)
        if not validation.allow:
            return Response(500, {"error": "guardrail_output_block", "reason": validation.reason})
        quarantined = self.quarantine.quarantine(json.dumps(result))
        if quarantined["quarantined"]:
            result["quarantined"] = True
            result["quarantined_content"] = quarantined["content"]

        self.metrics.observe_ms("tool_latency_ms", float(result.get("duration_ms", 0)), {"tool": tool_name})
        if result.get("status") == "error":
            self.metrics.inc("tool_errors")
            if result.get("error") == "tool_timeout":
                self.metrics.inc("tool_timeouts")

        recent = self.tool_audit.list_recent(1)
        if recent:
            self.audit.emit_tool_call(recent[0], identity.request_id, identity.tenant_id)

        return Response(200, {"result": result})


def _parse_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_dt(raw: Any):
    from datetime import datetime

    if not raw:
        return None
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _load_release_thresholds(path: pathlib.Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {k: float(v) for k, v in parsed.items()}
