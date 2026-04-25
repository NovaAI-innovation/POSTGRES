# Migration Runbook

## Policy

- Forward-only SQL migrations.
- Migration command: `python -m app.db.migrate`.
- Validate in staging before production.

## Rollback Strategy

1. Pause agents using admin emergency control.
2. Restore most recent known-good backup (`POST /lifecycle/restore`).
3. Re-run smoke tests and eval gate.
4. Resume agents.

## Verification

- Run `python -m pytest -q`.
- Run `python -m app.eval.run`.
