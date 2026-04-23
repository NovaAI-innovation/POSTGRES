#!/bin/bash
# reconcile.sh - Phase 6 Operations: Cleanup and Reconciliation

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

PSQL="${PSQL_PATH:-psql}"
export PGPASSWORD=$POSTGRES_PASSWORD
DB_FLAGS="-h $POSTGRES_HOST -U $POSTGRES_USERNAME -d $POSTGRES_DB"

echo "[$(date)] Starting reconciliation..."

# 1. Release stale leases
STALE_COUNT=$(echo | $PSQL $DB_FLAGS -n -t -c "
WITH stale AS (
  UPDATE shared.agent_leases 
  SET released_at = now() 
  WHERE released_at IS NULL AND expires_at < now()
  RETURNING 1
)
SELECT count(*) FROM stale;")

echo "Released ${STALE_COUNT:-0} stale leases."

# 2. Basic reconciliation
echo | $PSQL $DB_FLAGS -n -c "
INSERT INTO shared.events (project_id, event_type, scope_type, scope_key, idempotency_key, event_payload)
SELECT 
  project_id, 
  'reconciliation.task_cleanup', 
  'project', 
  'root', 
  'recon-' || task_id || '-' || now()::date,
  jsonb_build_object('task_id', task_id, 'note', 'Auto-archiving completed task')
FROM shared.tasks 
WHERE status = 'done' AND updated_at < now() - interval '7 days';"

echo "Reconciliation complete."
