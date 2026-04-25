# Tool Sandbox (Phase 6)

- Tool registry now includes input/output schema, permissions, timeout, rate limit, destructive flag, and approval category.
- Tool runner enforces schema validation, timeout, retry, rate limit, and structured error capture.
- Destructive tools require approval IDs (`/tool-approvals/{id}/approve|reject`).
- Dry-run supported via `POST /tools/{tool}/dry-run`.
- Per-agent allowlists are enforced before policy checks.
- Tool call audit log captures hashes, duration, status, dry-run, and approval linkage.
