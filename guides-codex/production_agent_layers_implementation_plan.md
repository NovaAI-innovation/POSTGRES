# Production Agent Layers Implementation Plan

## Objective

Implement the production layers around the existing multi-agent memory database so agents can operate safely, observably, and reliably across isolated, scoped, and shared memory.

## Assumptions

- PostgreSQL is the primary memory store.
- pgvector is enabled with `VECTOR(384)` for local All-MiniLM-style embeddings.
- Agents access memory through an API, not by direct database writes.
- Production means multi-agent, multi-user, auditable, recoverable, and permissioned operation.

---

# Phase 0 — Baseline Foundation

## Goal

Get the memory schema running behind a minimal service boundary.

## Build

1. Apply the bootstrap SQL migration.
2. Create a backend service with these modules:
   - `agents`
   - `groups`
   - `memory`
   - `permissions`
   - `embeddings`
   - `tools`
   - `observability`
3. Expose only service APIs to agents.
4. Disable direct agent database access.
5. Add environment-based config:
   - database URL
   - embedding model name/path
   - auth secret/public key
   - log level
   - tool timeout defaults

## Outputs

- Running PostgreSQL memory database.
- Backend service connected to DB.
- Health check endpoint.
- Migration command.
- Basic create/read memory endpoint.

## Done Criteria

- A test agent can create and retrieve isolated memory through the API.
- No agent has direct DB credentials.

---

# Phase 1 — Identity & Auth Layer

## Goal

Ensure every request is tied to a known agent, user, tenant, or service identity.

## Build

1. Add identity model:
   - tenant ID
   - user ID
   - agent ID
   - service/client ID
2. Add API authentication:
   - JWT or signed service token
   - API key fallback only for internal/dev use
3. Add request context middleware:
   - authenticated principal
   - agent ID
   - tenant ID
   - request ID
4. Add secret handling:
   - secret manager integration
   - key rotation plan
   - no secrets in logs
5. Add auth audit events:
   - successful auth
   - failed auth
   - expired token
   - invalid agent identity

## Outputs

- Auth middleware.
- Identity context object.
- Agent/service credential issuance process.
- Auth audit logs.

## Done Criteria

- Every memory/tool request has a verified identity.
- Unauthorized requests are rejected before business logic.

---

# Phase 2 — Policy Enforcement Layer

## Goal

Centralize permission checks before memory reads/writes, tool calls, and agent delegation.

## Build

1. Create a policy engine module.
2. Define policy checks:
   - `can_read_memory(agent_id, memory_id)`
   - `can_write_memory(agent_id, scope)`
   - `can_admin_group(agent_id, group_id)`
   - `can_call_tool(agent_id, tool_name)`
   - `can_delegate_to(agent_id, target_agent_id)`
3. Enforce group permissions:
   - `can_read`
   - `can_write`
   - `can_admin`
4. Enforce overrides:
   - `blocked`
   - `read_only`
   - `elevated`
5. Add deny-by-default behavior.
6. Add policy decision logs:
   - allow/deny
   - reason
   - identity
   - resource

## Outputs

- Policy engine.
- Permission-checking middleware.
- Deny logs.
- Unit tests for isolated/scoped/shared memory visibility.

## Done Criteria

- All memory writes pass through policy checks.
- Blocked or read-only agents are enforced consistently.

---

# Phase 3 — Memory Ingestion Pipeline

## Goal

Turn raw agent/user/tool events into clean, searchable memory.

## Build

1. Create ingestion endpoint/job:
   - raw message/event input
   - source metadata
   - owning agent
   - target scope
2. Add normalization:
   - trim noise
   - remove duplicate boilerplate
   - preserve source reference
3. Add classification:
   - `fact`
   - `episode`
   - `message`
4. Add extraction:
   - facts from conversations
   - task outcomes
   - preferences
   - durable constraints
5. Add scoring:
   - importance `0-100`
   - confidence `0.00-1.00`
   - valid_from / valid_until
6. Add embedding generation:
   - local All-MiniLM-compatible model
   - exactly 384 dimensions
   - normalized embeddings if using cosine search
7. Add tagging:
   - project
   - user
   - domain
   - task type
8. Add deduplication:
   - exact content hash
   - near-duplicate vector threshold
   - source-ref uniqueness where applicable

## Outputs

- Ingestion worker.
- Embedding generator.
- Memory classifier.
- Importance/confidence scorer.
- Deduplication logic.

## Done Criteria

- Raw messages can be converted into structured memory entries.
- Duplicate memories are not repeatedly inserted.
- Embedding dimension is validated before insert.

---

# Phase 4 — Memory Retrieval Layer

## Goal

Retrieve the right memory, not just the nearest vector result.

## Build

1. Implement readable-memory retrieval using the DB helper function.
2. Add hybrid retrieval:
   - vector similarity
   - keyword/text search
   - recency
   - importance
   - confidence
   - scope priority
3. Add filters:
   - entry type
   - tag
   - domain
   - source_ref
   - valid time window
4. Add reranking:
   - semantic score
   - importance boost
   - recency decay
   - confidence boost
   - exact keyword match boost
5. Add deduplication after retrieval.
6. Add citation/source labeling.
7. Add retrieval debug mode for development.

## Outputs

- `retrieve_memory(agent_id, query, filters)` service.
- Hybrid score formula.
- Retrieval tests.
- Debug payload showing why memories were selected.

## Done Criteria

- Retrieval respects isolated/scoped/shared permissions.
- Old, low-confidence, irrelevant memories do not dominate context.

---

# Phase 5 — Context Assembly Layer

## Goal

Convert retrieved memory into prompt-ready context without blowing token budgets.

## Build

1. Add token budgeting:
   - max memory tokens
   - max tool result tokens
   - max conversation history tokens
2. Add context grouping:
   - user preferences
   - project facts
   - recent events
   - task-specific memories
   - warnings/constraints
3. Add compression:
   - summarize redundant memories
   - preserve source references
   - preserve uncertainty/confidence
4. Add conflict handling:
   - newest valid fact wins by default
   - higher confidence wins on same timestamp
   - surface conflicts when unresolved
5. Add final context format:
   - concise bullets
   - source IDs
   - scope labels
   - confidence where relevant

## Outputs

- Context assembler.
- Prompt memory block format.
- Conflict-resolution logic.
- Token-budget tests.

## Done Criteria

- Context fits inside configured token limits.
- Assembled context includes source labels and does not silently hide conflicts.

---

# Phase 6 — Tool Execution Sandbox

## Goal

Allow agents to use tools without uncontrolled side effects.

## Build

1. Create tool registry:
   - tool name
   - description
   - input schema
   - output schema
   - permissions required
   - timeout
   - rate limit
   - destructive/non-destructive flag
2. Add execution wrapper:
   - input validation
   - timeout
   - retry policy
   - structured output
   - error capture
3. Add approval gates:
   - destructive actions
   - external sends
   - payments/purchases
   - production deploys
   - data deletion
4. Add dry-run mode.
5. Add per-agent tool allowlists.
6. Log every tool call:
   - agent
   - input hash
   - output hash/summary
   - duration
   - status
   - approval info

## Outputs

- Tool registry.
- Tool runner.
- Approval flow.
- Dry-run support.
- Tool audit logs.

## Done Criteria

- Agents cannot call unapproved tools.
- Destructive tools require explicit approval or elevated policy.

---

# Phase 7 — Observability Layer

## Goal

Make agent behavior inspectable and debuggable.

## Build

1. Structured logs:
   - request ID
   - agent ID
   - tenant ID
   - memory IDs read/written
   - tool calls
   - policy decisions
2. Metrics:
   - request latency
   - tool latency
   - memory retrieval latency
   - embedding latency
   - token usage
   - cost estimate
   - error rates
3. Tracing:
   - agent request span
   - retrieval span
   - LLM call span
   - tool call span
   - DB span
4. Dashboards:
   - agent activity
   - failures
   - memory writes
   - retrieval quality
   - tool usage
5. Alerts:
   - elevated error rate
   - DB latency
   - embedding failures
   - unauthorized access attempts
   - tool timeout spikes

## Outputs

- Logging schema.
- Metrics dashboard.
- Distributed traces.
- Alert rules.

## Done Criteria

- A failed agent task can be traced from request to memory retrieval to tool execution.

---

# Phase 8 — Evaluation Layer

## Goal

Prevent prompt, memory, and tool regressions.

## Build

1. Create eval datasets:
   - memory recall tasks
   - permission boundary tests
   - tool-use tasks
   - refusal/safety tasks
   - multi-agent handoff tasks
2. Add automated scoring:
   - task success
   - memory relevance
   - hallucination rate
   - unauthorized access rate
   - tool correctness
3. Add regression suite:
   - run on prompt changes
   - run on retrieval changes
   - run on model changes
   - run on schema changes
4. Add golden traces for critical workflows.
5. Add human review queue for low-confidence outputs.

## Outputs

- Eval harness.
- Test datasets.
- Regression dashboard.
- Release gate thresholds.

## Done Criteria

- Prompt/model/retrieval changes cannot ship without passing core evals.

---

# Phase 9 — Safety & Guardrail Layer

## Goal

Reduce unsafe actions, data leakage, and prompt-injection risk.

## Build

1. Add input scanning:
   - prompt injection markers
   - secrets
   - PII
   - malicious tool instructions
2. Add output validation:
   - schema validation
   - blocked content checks
   - sensitive data leakage checks
3. Add tool-result quarantine:
   - treat retrieved web/doc/tool content as untrusted
   - strip or isolate embedded instructions
4. Add memory write guardrails:
   - do not store secrets by default
   - mark sensitive memory
   - require higher permission for shared memory writes
5. Add data retention rules:
   - delete/expire sensitive entries
   - redact on request
6. Add escalation paths:
   - human approval
   - block response
   - safe fallback

## Outputs

- Guardrail middleware.
- Injection detector.
- PII/secrets detector.
- Memory redaction flow.
- Quarantine rules for untrusted content.

## Done Criteria

- Tool output cannot directly override system/developer policy.
- Secrets and sensitive data are not written to shared memory by default.

---

# Phase 10 — Orchestration Layer

## Goal

Coordinate multi-agent work reliably.

## Build

1. Add task model:
   - task ID
   - owner
   - assigned agent
   - status
   - priority
   - deadline
   - parent task
2. Add queue:
   - pending
   - running
   - waiting approval
   - failed
   - completed
3. Add routing:
   - by agent capability
   - by tool access
   - by memory group
   - by current load
4. Add reliability controls:
   - retries
   - idempotency keys
   - cancellation
   - timeouts
   - dead-letter queue
5. Add handoffs:
   - source agent
   - target agent
   - task summary
   - relevant memory IDs
   - requested output
6. Add locking:
   - prevent duplicate execution
   - protect shared resources

## Outputs

- Task queue.
- Agent router.
- Handoff protocol.
- Retry/dead-letter handling.
- Idempotency layer.

## Done Criteria

- Multi-step tasks survive worker restarts and do not duplicate destructive actions.

---

# Phase 11 — Lifecycle Management

## Goal

Keep memory accurate, compact, and recoverable over time.

## Build

1. Add memory decay:
   - lower importance over time unless reinforced
   - preserve pinned/core facts
2. Add stale fact detection:
   - expired `valid_until`
   - contradiction detection
   - old source references
3. Add compaction:
   - summarize old messages into episodes
   - archive raw messages
   - keep facts current
4. Add backups:
   - daily database backups
   - point-in-time recovery
   - restore drills
5. Add migrations:
   - forward-only migration policy
   - rollback strategy for failed deploys
   - migration tests
6. Add retention:
   - per-tenant retention policy
   - sensitive data expiry
   - soft-delete cleanup schedule

## Outputs

- Memory maintenance jobs.
- Backup/restore process.
- Retention policy.
- Migration runbook.

## Done Criteria

- Old memory does not degrade retrieval quality.
- Database can be restored and verified from backup.

---

# Phase 12 — Human Control Layer

## Goal

Give operators visibility and control over agents and memory.

## Build

1. Admin UI pages:
   - agents
   - groups
   - permissions
   - memory search
   - memory detail
   - tool calls
   - tasks
   - approvals
   - audit events
2. Admin actions:
   - disable agent
   - mark read-only
   - delete/restore memory
   - adjust importance/confidence
   - approve/reject tool calls
   - inspect prompt context
3. Add audit trail for all admin actions.
4. Add role-based admin access.
5. Add emergency controls:
   - pause all agents
   - disable tool class
   - revoke credentials
   - block shared-memory writes

## Outputs

- Operator/admin console.
- Approval queue.
- Emergency stop controls.
- Audit event viewer.

## Done Criteria

- An operator can inspect, correct, disable, or roll back agent behavior without direct DB access.

---

# Recommended Build Order

## Milestone 1 — Secure Memory MVP

Implement:

1. Phase 0 — Baseline Foundation
2. Phase 1 — Identity & Auth
3. Phase 2 — Policy Enforcement
4. Phase 3 — Basic Memory Ingestion
5. Phase 4 — Basic Retrieval

Outcome: agents can safely write and retrieve memory through a permissioned API.

## Milestone 2 — Useful Agent Runtime

Implement:

1. Phase 5 — Context Assembly
2. Phase 6 — Tool Sandbox
3. Phase 7 — Observability

Outcome: agents can use memory and tools with logs, limits, and traceability.

## Milestone 3 — Production Hardening

Implement:

1. Phase 8 — Evaluation
2. Phase 9 — Safety/Guardrails
3. Phase 10 — Orchestration

Outcome: agents can perform multi-step tasks with regression checks and safety controls.

## Milestone 4 — Operations & Scale

Implement:

1. Phase 11 — Lifecycle Management
2. Phase 12 — Human Control

Outcome: the system is maintainable, recoverable, and operator-controlled.

---

# Initial API Surface

## Agents

- `POST /agents`
- `GET /agents/{agent_id}`
- `PATCH /agents/{agent_id}`
- `POST /agents/{agent_id}/disable`

## Groups

- `POST /groups`
- `POST /groups/{group_id}/members`
- `DELETE /groups/{group_id}/members/{agent_id}`
- `PATCH /groups/{group_id}/permissions/{agent_id}`

## Memory

- `POST /memory`
- `GET /memory/{uuid}`
- `GET /memory?agent_id=&scope=&tag=&entry_type=`
- `POST /memory/search`
- `PATCH /memory/{uuid}`
- `DELETE /memory/{uuid}`

## Tools

- `GET /tools`
- `POST /tools/{tool_name}/run`
- `POST /tools/{tool_name}/dry-run`
- `POST /tool-approvals/{approval_id}/approve`
- `POST /tool-approvals/{approval_id}/reject`

## Tasks

- `POST /tasks`
- `GET /tasks/{task_id}`
- `PATCH /tasks/{task_id}`
- `POST /tasks/{task_id}/cancel`
- `POST /tasks/{task_id}/handoff`

## Admin

- `GET /audit-events`
- `GET /tool-calls`
- `GET /policy-decisions`
- `POST /admin/pause-agents`
- `POST /admin/resume-agents`

---

# Minimum Data Additions Beyond Current Bootstrap

Add these tables after the memory MVP stabilizes:

1. `tenants`
2. `users`
3. `agent_credentials`
4. `policy_decisions`
5. `tool_registry`
6. `tool_calls`
7. `tool_approvals`
8. `tasks`
9. `task_events`
10. `agent_handoffs`
11. `audit_events`
12. `eval_runs`
13. `eval_cases`
14. `memory_ingestion_events`
15. `memory_compaction_jobs`

---

# Priority Checklist

## Build First

- Auth middleware
- Policy engine
- Memory ingestion
- Hybrid retrieval
- Context assembler
- Tool sandbox
- Structured logging

## Build Before Production Launch

- Evaluation suite
- Guardrails
- Audit events
- Admin controls
- Backup/restore
- Rate limits
- Approval gates

## Build After Launch

- Advanced orchestration
- Memory decay/compaction
- Rich admin UI
- Automated contradiction detection
- Per-agent performance tuning

