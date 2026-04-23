#Requires -Version 5.1
# reconcile.ps1 - Phase 6 Operations: Cleanup and Reconciliation

if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^(?<key>[^#\s=]+)=(?<value>.*)$') {
            $key = $Matches['key'].Trim()
            $value = $Matches['value'].Trim().Trim('"').Trim("'")
            Set-Item -Path "Env:$key" -Value $value
        }
    }
}

$env:PGPASSWORD = $env:POSTGRES_PASSWORD
$DbFlags = @('-h', $env:POSTGRES_HOST, '-U', $env:POSTGRES_USERNAME, '-d', $env:POSTGRES_DB)

Write-Host "[$(Get-Date)] Starting reconciliation..." -ForegroundColor Cyan

# 1. Release stale leases
$StaleCount = '' | psql @DbFlags -n -t --pset=pager=off -c "
WITH stale AS (
  UPDATE shared.agent_leases
  SET released_at = now()
  WHERE released_at IS NULL AND expires_at < now()
  RETURNING 1
)
SELECT count(*) FROM stale;"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to release stale leases (psql exit $LASTEXITCODE)"
    exit 1
}

Write-Host "Released $($StaleCount.Trim()) stale leases." -ForegroundColor Green

# 2. Archive completed tasks — idempotent: ON CONFLICT skips duplicate idempotency keys on re-runs
$AgentKey = if (-not [string]::IsNullOrWhiteSpace($env:AGENT_KEY)) { $env:AGENT_KEY } else { "openai-codex" }
'' | psql @DbFlags -n --pset=pager=off -c "
INSERT INTO shared.events (project_id, agent_id, event_type, scope_type, scope_key, idempotency_key, event_payload)
SELECT
  project_id,
  (SELECT agent_id FROM core.agents WHERE agent_key = '$AgentKey' LIMIT 1),
  'reconciliation.task_cleanup',
  'project',
  'root',
  'recon-' || task_id || '-' || now()::date,
  jsonb_build_object('task_id', task_id, 'note', 'Auto-archiving completed task')
FROM shared.tasks
WHERE status = 'done' AND updated_at < now() - interval '7 days'
ON CONFLICT (project_id, idempotency_key) DO NOTHING;"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to run reconciliation cleanup (psql exit $LASTEXITCODE)"
    exit 1
}

Write-Host "Reconciliation complete." -ForegroundColor Cyan
