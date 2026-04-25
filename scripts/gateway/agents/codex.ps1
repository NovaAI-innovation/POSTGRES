#Requires -Version 5.1

[CmdletBinding()]
param(
    [string]$EventJson,
    [string]$EventFile,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$DryRun
)

$coreScript = Join-Path $PSScriptRoot "..\core.ps1"
$policyFile = Join-Path $PSScriptRoot "..\policies\Codex.json"

& $coreScript `
    -PolicyFile $policyFile `
    -AgentId "Codex" `
    -TenantId "Casey" `
    -BaseUrl $BaseUrl `
    -EventJson $EventJson `
    -EventFile $EventFile `
    -AuthToken $env:CODEX_GATEWAY_TOKEN `
    -ApiKey $env:CODEX_GATEWAY_API_KEY `
    -DryRun:$DryRun
