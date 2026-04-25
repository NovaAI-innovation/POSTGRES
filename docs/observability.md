# Observability (Phase 7)

- Structured request/auth/policy/tool logs include request, tenant, agent, and trace IDs.
- Metrics store tracks request/tool/retrieval/embedding latency, error counters, and token usage gauges.
- Tracer records spans for request, retrieval, tool call, and DB operations.
- Dashboard template: `observability/dashboard.json`.
- Alert rules template: `observability/alerts.yml`.
- Endpoints:
  - `GET /observability/metrics`
  - `GET /observability/traces`
  - `GET /audit-events`
  - `GET /tool-calls`
  - `GET /policy-decisions`
