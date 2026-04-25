# Human Control Layer (Phase 12)

- Operator console endpoint: `GET /admin/console`.
- Admin actions:
  - disable agent / set read-only
  - delete/restore memory
  - adjust memory importance/confidence
  - approve/reject tool calls
  - inspect prompt context
- Audit trail:
  - admin actions logged via `admin_action` events
  - view at `GET /admin/audit-events`
- Role-based admin:
  - admin token requires `user_id` prefixed with `admin` or trusted service identity
- Emergency controls:
  - pause/resume agents
  - disable/enable tool class
  - revoke credentials
  - block/unblock shared-memory writes
