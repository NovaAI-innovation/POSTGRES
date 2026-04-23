#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [string]$Action,
    [string]$Matcher = ""
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

function Write-HookLog([string]$Message) {
    Write-Host "[agent-state-hook] $Message"
}

function EscSql([string]$Value) {
    if ($null -eq $Value) { return '' }
    return $Value.Replace("'", "''")
}

function Load-DotEnv {
    if (-not (Test-Path ".env")) { return }
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^(?<key>[^#\s=]+)=(?<value>.*)$') {
            $key = $Matches['key'].Trim()
            $value = $Matches['value'].Trim().Trim('"').Trim("'")
            Set-Item -Path "Env:$key" -Value $value
        }
    }
}

function Get-DbFlags {
    if ([string]::IsNullOrWhiteSpace($env:POSTGRES_HOST) -or
        [string]::IsNullOrWhiteSpace($env:POSTGRES_USERNAME) -or
        [string]::IsNullOrWhiteSpace($env:POSTGRES_DB) -or
        [string]::IsNullOrWhiteSpace($env:POSTGRES_PASSWORD)) {
        return $null
    }

    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    return @('-h', $env:POSTGRES_HOST, '-U', $env:POSTGRES_USERNAME, '-d', $env:POSTGRES_DB)
}

function Invoke-Psql([string]$Sql, [string[]]$DbFlags) {
    '' | psql @DbFlags -n --pset=pager=off -c $Sql | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "psql exited with code $LASTEXITCODE"
    }
}

function Invoke-PsqlScalar([string]$Sql, [string[]]$DbFlags) {
    $result = '' | psql @DbFlags -n -t -A --pset=pager=off -c $Sql
    if ($LASTEXITCODE -ne 0) {
        throw "psql exited with code $LASTEXITCODE"
    }
    return ($result | Select-Object -First 1).Trim()
}

function Read-HookPayload {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    try {
        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Normalize-ScopeKey([string]$PathValue, [string]$RepoRootPath) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return "unknown" }

    $candidate = $PathValue
    if (-not [System.IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path $RepoRootPath $candidate
    }

    try {
        $full = [System.IO.Path]::GetFullPath($candidate)
    } catch {
        return $PathValue.Replace('\', '/')
    }

    if ($full.StartsWith($RepoRootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $full.Substring($RepoRootPath.Length).TrimStart('\', '/')
        if ([string]::IsNullOrWhiteSpace($relative)) { return "root" }
        return $relative.Replace('\', '/')
    }

    return $full.Replace('\', '/')
}

function Get-ToolName($Payload) {
    if ($null -eq $Payload) { return "" }
    if ($Payload.PSObject.Properties.Name -contains 'tool_name') { return [string]$Payload.tool_name }
    return ""
}

function Get-FileScopeKey($Payload, [string]$RepoRootPath) {
    if ($null -eq $Payload) { return "unknown" }

    $toolInput = $null
    if ($Payload.PSObject.Properties.Name -contains 'tool_input') {
        $toolInput = $Payload.tool_input
    }

    if ($null -eq $toolInput) { return "unknown" }

    foreach ($field in @('file_path', 'path', 'target_file')) {
        if ($toolInput.PSObject.Properties.Name -contains $field) {
            $value = [string]$toolInput.$field
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return (Normalize-ScopeKey -PathValue $value -RepoRootPath $RepoRootPath)
            }
        }
    }

    return "unknown"
}

function Get-IdempotencySuffix($Payload) {
    if ($null -eq $Payload) { return (Get-Date -Format "yyyyMMddHHmmss") }
    foreach ($field in @('tool_use_id', 'request_id', 'session_id', 'transcript_path')) {
        if ($Payload.PSObject.Properties.Name -contains $field) {
            $value = [string]$Payload.$field
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return ($value -replace '[^a-zA-Z0-9._-]', '-')
            }
        }
    }
    return (Get-Date -Format "yyyyMMddHHmmss")
}

function Ensure-StateDir([string]$RepoRootPath) {
    $stateDir = Join-Path $RepoRootPath ".claude\state"
    if (-not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    }
    return $stateDir
}

function Read-ActiveLeases([string]$LeaseFilePath) {
    if (-not (Test-Path $LeaseFilePath)) { return @{} }
    $raw = Get-Content -Raw $LeaseFilePath
    if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
    try {
        $obj = $raw | ConvertFrom-Json -AsHashtable
        if ($null -eq $obj) { return @{} }
        return $obj
    } catch {
        return @{}
    }
}

function Write-ActiveLeases([string]$LeaseFilePath, [hashtable]$Leases) {
    $Leases | ConvertTo-Json -Depth 6 | Set-Content -Path $LeaseFilePath -Encoding UTF8
}

Load-DotEnv
$dbFlags = Get-DbFlags

if ($null -eq $dbFlags) {
    Write-HookLog "Skipping '$Action' (missing database environment variables)."
    exit 0
}

$agentKey = if (-not [string]::IsNullOrWhiteSpace($env:AGENT_KEY)) { $env:AGENT_KEY } else { "openai-codex" }
$projectId = if (-not [string]::IsNullOrWhiteSpace($env:PROJECT_ID)) { [int]$env:PROJECT_ID } else { 1 }
$payload = Read-HookPayload
$toolName = Get-ToolName $payload
$scopeKey = Get-FileScopeKey -Payload $payload -RepoRootPath $RepoRoot
$suffix = Get-IdempotencySuffix $payload

$stateDir = Ensure-StateDir -RepoRootPath $RepoRoot
$leaseFile = Join-Path $stateDir "active-leases.json"
$leases = Read-ActiveLeases -LeaseFilePath $leaseFile

try {
    switch ($Action) {
        "SessionStart" {
            & "$RepoRoot\powershell\agent-state.ps1" pull | Out-Null
            & "$RepoRoot\powershell\agent-state.ps1" tasks | Out-Null
            # Phase 5 Step 3: read agent's own extension row
            $extSql = "SELECT workspace_root, cwd, active_branch, active_task_key, last_seen_event_id FROM ext.$(($agentKey -replace '-','_'))_state WHERE project_id = $projectId AND agent_id = (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)') LIMIT 1;"
            try { Invoke-PsqlScalar -Sql $extSql -DbFlags $dbFlags | Out-Null } catch {}
            Write-HookLog "Session synchronized from shared state."
        }
        "UserPromptSubmit" {
            & "$RepoRoot\powershell\agent-state.ps1" pull | Out-Null
            Write-HookLog "Prompt sync completed."
        }
        "PreToolUse" {
            if ($Matcher -eq "write-tools" -and $scopeKey -ne "unknown") {
                if (-not $leases.ContainsKey($scopeKey)) {
                    $sql = "SELECT api.claim_lease($projectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)'), 'file', '$(EscSql $scopeKey)', 'hook-pretooluse:$($toolName)', 1800);"
                    $token = Invoke-PsqlScalar -Sql $sql -DbFlags $dbFlags
                    if (-not [string]::IsNullOrWhiteSpace($token)) {
                        $leases[$scopeKey] = @{
                            token = $token
                            claimed_at = (Get-Date).ToString("o")
                            tool = $toolName
                        }
                        Write-ActiveLeases -LeaseFilePath $leaseFile -Leases $leases
                        Write-HookLog "Lease claimed for '$scopeKey'."
                    }
                }
            }
        }
        "PostToolUse" {
            if ($Matcher -eq "write-tools") {
                $idempotencyKey = "hook-write-$($suffix)-$((EscSql $scopeKey) -replace '[^a-zA-Z0-9._/-]','-')"
                $sql = @"
WITH ev AS (
  SELECT api.append_event(
    $projectId,
    (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)'),
    'tool.write.completed',
    'file',
    '$(EscSql $scopeKey)',
    '$(EscSql $idempotencyKey)',
    jsonb_build_object(
      'tool_name', '$(EscSql $toolName)',
      'matcher', '$(EscSql $Matcher)',
      'scope_key', '$(EscSql $scopeKey)'
    )
  ) AS event_id
)
SELECT api.upsert_core_state(
  $projectId,
  (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)'),
  'file',
  '$(EscSql $scopeKey)',
  'last_write',
  jsonb_build_object(
    'tool_name', '$(EscSql $toolName)',
    'hook', 'PostToolUse',
    'updated_at', now()::text
  ),
  NULL,
  (SELECT event_id FROM ev),
  1.0
);
"@
                Invoke-Psql -Sql $sql -DbFlags $dbFlags

                # Phase 5 Step 7: upsert agent's own extension row
                $cwdVal = (Get-Location).Path.Replace('\','/').Replace("'","''")
                $branchVal = try { (git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch { "" }
                $lastEventSql = "SELECT COALESCE(MAX(event_id),0) FROM shared.events WHERE project_id = $projectId;"
                $lastEventId = try { Invoke-PsqlScalar -Sql $lastEventSql -DbFlags $dbFlags } catch { "0" }
                $extUpsertSql = "SELECT api.upsert_agent_runtime_state('$(EscSql $agentKey)', $projectId, '$(EscSql $RepoRoot.Replace('\','/'))','$(EscSql $cwdVal)','$(EscSql $branchVal)','$(EscSql $scopeKey)','{}'::jsonb,'{}'::jsonb,'[]'::jsonb,NULL,$lastEventId);"
                Invoke-Psql -Sql $extUpsertSql -DbFlags $dbFlags
                Write-HookLog "Deterministic write event+state persisted for '$scopeKey'."
            }
        }
        "Notification" {
            $idempotencyKey = "hook-notification-$suffix"
            $sql = "SELECT api.append_event($projectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)'), 'agent.notification', 'project', 'root', '$(EscSql $idempotencyKey)', jsonb_build_object('source','hook'));"
            Invoke-Psql -Sql $sql -DbFlags $dbFlags
            Write-HookLog "Notification event appended."
        }
        "Stop" {
            # Phase 5 Step 7: final ext state upsert before releasing leases
            $cwdVal = (Get-Location).Path.Replace('\','/').Replace("'","''")
            $branchVal = try { (git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch { "" }
            $lastEventSql = "SELECT COALESCE(MAX(event_id),0) FROM shared.events WHERE project_id = $projectId;"
            $lastEventId = try { Invoke-PsqlScalar -Sql $lastEventSql -DbFlags $dbFlags } catch { "0" }
            $extUpsertSql = "SELECT api.upsert_agent_runtime_state('$(EscSql $agentKey)', $projectId, '$(EscSql $RepoRoot.Replace('\','/'))','$(EscSql $cwdVal)','$(EscSql $branchVal)',NULL,'{}'::jsonb,'{}'::jsonb,'[]'::jsonb,NULL,$lastEventId);"
            try { Invoke-Psql -Sql $extUpsertSql -DbFlags $dbFlags } catch {}

            foreach ($scope in @($leases.Keys)) {
                $token = [string]$leases[$scope].token
                if (-not [string]::IsNullOrWhiteSpace($token)) {
                    $sql = "SELECT api.release_lease($projectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)'), 'file', '$(EscSql $scope)', '$(EscSql $token)'::uuid);"
                    Invoke-Psql -Sql $sql -DbFlags $dbFlags
                }
            }
            @{} | ConvertTo-Json | Set-Content -Path $leaseFile -Encoding UTF8
            & "$RepoRoot\powershell\reconcile.ps1" | Out-Null
            Write-HookLog "Leases released and reconciliation executed."
        }
        "SubagentStop" {
            # Phase 5 Step 7: final ext state upsert before releasing leases
            $cwdVal = (Get-Location).Path.Replace('\','/').Replace("'","''")
            $branchVal = try { (git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch { "" }
            $lastEventSql = "SELECT COALESCE(MAX(event_id),0) FROM shared.events WHERE project_id = $projectId;"
            $lastEventId = try { Invoke-PsqlScalar -Sql $lastEventSql -DbFlags $dbFlags } catch { "0" }
            $extUpsertSql = "SELECT api.upsert_agent_runtime_state('$(EscSql $agentKey)', $projectId, '$(EscSql $RepoRoot.Replace('\','/'))','$(EscSql $cwdVal)','$(EscSql $branchVal)',NULL,'{}'::jsonb,'{}'::jsonb,'[]'::jsonb,NULL,$lastEventId);"
            try { Invoke-Psql -Sql $extUpsertSql -DbFlags $dbFlags } catch {}

            foreach ($scope in @($leases.Keys)) {
                $token = [string]$leases[$scope].token
                if (-not [string]::IsNullOrWhiteSpace($token)) {
                    $sql = "SELECT api.release_lease($projectId, (SELECT agent_id FROM core.agents WHERE agent_key='$(EscSql $agentKey)'), 'file', '$(EscSql $scope)', '$(EscSql $token)'::uuid);"
                    Invoke-Psql -Sql $sql -DbFlags $dbFlags
                }
            }
            @{} | ConvertTo-Json | Set-Content -Path $leaseFile -Encoding UTF8
            Write-HookLog "Subagent leases released."
        }
        default {
            Write-HookLog "No-op for action '$Action'."
        }
    }
} catch {
    Write-HookLog "Non-blocking hook error for '$Action': $($_.Exception.Message)"
}

exit 0
