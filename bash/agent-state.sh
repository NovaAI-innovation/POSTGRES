#!/bin/bash
# agent-state.sh - CLI for Phase 5 State Management
# Automatically loads credentials from .env

# Load .env variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Use PSQL_PATH from .env if defined, otherwise default to 'psql'
PSQL="${PSQL_PATH:-psql}"
PROJECT_ID=1
PAGER_OFF="-P pager=off"

# Set PGPASSWORD for psql
export PGPASSWORD=$POSTGRES_PASSWORD

# Shared connection flags
DB_FLAGS="-h $POSTGRES_HOST -U $POSTGRES_USERNAME -d $POSTGRES_DB"

case $1 in
  "pull")
    echo "--- PROJECT STATE ---"
    echo | $PSQL $DB_FLAGS -n $PAGER_OFF -c "SELECT scope_type, scope_key, state_key, value_json FROM shared.core_state WHERE project_id = $PROJECT_ID;"
    ;;
  
  "tasks")
    echo "--- OPEN TASKS ---"
    echo | $PSQL $DB_FLAGS -n $PAGER_OFF -c "SELECT title, status, priority, assigned_agent_id FROM shared.tasks WHERE project_id = $PROJECT_ID AND status != 'done' ORDER BY updated_at DESC;"
    ;;

  "lease-claim")
    echo | $PSQL $DB_FLAGS -n -t -c "SELECT api.claim_lease($PROJECT_ID, (SELECT agent_id FROM core.agents WHERE agent_key='$4'), '$2', '$3', '$5', ${6:-900});"
    ;;

  "lease-release")
    echo | $PSQL $DB_FLAGS -n -c "SELECT api.release_lease($PROJECT_ID, (SELECT agent_id FROM core.agents WHERE agent_key='$4'), '$2', '$3', '$5'::uuid);"
    ;;

  "event")
    echo | $PSQL $DB_FLAGS -n -c "SELECT api.append_event($PROJECT_ID, (SELECT agent_id FROM core.agents WHERE agent_key='$2'), '$3', '$4', '$5', '$6', '$7'::jsonb);"
    ;;

  "state")
    echo | $PSQL $DB_FLAGS -n -c "SELECT api.upsert_core_state($PROJECT_ID, (SELECT agent_id FROM core.agents WHERE agent_key='$2'), '$3', '$4', '$5', '$6'::jsonb, NULL, $7);"
    ;;

  "handoff")
    echo | $PSQL $DB_FLAGS -n -c "INSERT INTO shared.handoffs (project_id, from_agent_id, to_agent_id, subject, payload) VALUES ($PROJECT_ID, (SELECT agent_id FROM core.agents WHERE agent_key='$2'), (SELECT agent_id FROM core.agents WHERE agent_key='$3'), '$4', '$5'::jsonb);"
    ;;

  "summary")
    echo | $PSQL $DB_FLAGS -n $PAGER_OFF -c "SELECT * FROM api.project_summary WHERE project_id = $PROJECT_ID;"
    ;;

  *)
    echo "Usage: $0 {pull|tasks|lease-claim|lease-release|event|state|handoff|summary}"
    exit 1
    ;;
esac
