#Requires -Version 5.1
# agent-state.ps1 - PowerShell for Phase 5 State Management

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
# Use explicit flags so psql processes -c as an option, not a positional arg
$DbFlags = @('-h', $env:POSTGRES_HOST, '-U', $env:POSTGRES_USERNAME, '-d', $env:POSTGRES_DB)
$ProjectId = 1

function Invoke-Psql($Command) {
    '' | psql @DbFlags -n --pset=pager=off -c $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Error "psql exited with code $LASTEXITCODE"
    }
}

# Escape single quotes for SQL string literals
function EscSql($s) { if ($null -eq $s) { '' } else { $s.Replace("'", "''") } }

switch ($args[0]) {
    "pull" {
        Write-Host "--- PROJECT STATE ---" -ForegroundColor Cyan
        Invoke-Psql "SELECT scope_type, scope_key, state_key, value_json FROM shared.core_state WHERE project_id = $ProjectId;"
    }
    "tasks" {
        Write-Host "--- OPEN TASKS ---" -ForegroundColor Cyan
        Invoke-Psql "SELECT title, status, priority, assigned_agent_id FROM shared.tasks WHERE project_id = $ProjectId AND status != 'done' ORDER BY updated_at DESC;"
    }
    "lease-claim" {
        # Usage: .\agent-state.ps1 lease-claim [scope] [key] [agent_key] [reason] [ttl]
        $ttl = if ($null -ne $args[5] -and $args[5] -ne '') { $args[5] } else { 900 }
        Invoke-Psql "SELECT api.claim_lease($ProjectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $args[3])'), '$(EscSql $args[1])', '$(EscSql $args[2])', '$(EscSql $args[4])', $ttl);"
    }
    "lease-release" {
        # Usage: .\agent-state.ps1 lease-release [scope] [key] [agent_key] [token]
        Invoke-Psql "SELECT api.release_lease($ProjectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $args[3])'), '$(EscSql $args[1])', '$(EscSql $args[2])', '$(EscSql $args[4])'::uuid);"
    }
    "event" {
        # Usage: .\agent-state.ps1 event [agent_key] [type] [scope] [scope_key] [idemp_key] [payload_json]
        Invoke-Psql "SELECT api.append_event($ProjectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $args[1])'), '$(EscSql $args[2])', '$(EscSql $args[3])', '$(EscSql $args[4])', '$(EscSql $args[5])', '$(EscSql $args[6])'::jsonb);"
    }
    "state" {
        # Usage: .\agent-state.ps1 state [agent_key] [scope] [scope_key] [state_key] [value_json] [event_id]
        Invoke-Psql "SELECT api.upsert_core_state($ProjectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $args[1])'), '$(EscSql $args[2])', '$(EscSql $args[3])', '$(EscSql $args[4])', '$(EscSql $args[5])'::jsonb, NULL, $($args[6]));"
    }
    "handoff" {
        # Usage: .\agent-state.ps1 handoff [from_agent] [to_agent] [subject] [payload_json]
        Invoke-Psql "INSERT INTO shared.handoffs (project_id, from_agent_id, to_agent_id, subject, payload) VALUES ($ProjectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $args[1])'), (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $args[2])'), '$(EscSql $args[3])', '$(EscSql $args[4])'::jsonb);"
    }
    "summary" {
        Invoke-Psql "SELECT * FROM api.project_summary WHERE project_id = $ProjectId;"
    }
    default {
        Write-Host "Usage: .\agent-state.ps1 {pull|tasks|lease-claim|lease-release|event|state|handoff|summary}" -ForegroundColor Yellow
    }
}
