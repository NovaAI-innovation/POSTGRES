# Orchestration Layer (Phase 10)

- Task queue states: `pending`, `running`, `waiting_approval`, `failed`, `completed`, `cancelled`.
- Routing uses capability, tool access, memory group, and current load.
- Reliability controls:
  - idempotency key dedupe
  - retries and dead-letter queue
  - cancellation
  - timeout checks
  - lock manager for duplicate execution protection
- Handoff protocol captures source/target, summary, memory IDs, requested output.
- Endpoints:
  - `POST /tasks`
  - `GET /tasks`
  - `GET /tasks/{task_id}`
  - `PATCH /tasks/{task_id}`
  - `POST /tasks/{task_id}/cancel`
  - `POST /tasks/{task_id}/handoff`
