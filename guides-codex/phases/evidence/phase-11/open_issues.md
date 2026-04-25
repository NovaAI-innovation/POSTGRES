# Open Issues

1. Backups are JSON snapshots and not full PostgreSQL physical/PITR backups.
2. Lifecycle jobs are API-triggered and not yet on a scheduled worker/cron system.
3. Contradiction detection is heuristic and should be enhanced with richer semantic conflict logic.
