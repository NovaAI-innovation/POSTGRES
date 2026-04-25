#Requires -Version 5.1

[CmdletBinding()]
param(
    [string]$EventJson,
    [string]$EventFile,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$DryRun
)

$coreScript = Join-Path $PSScriptRoot "..\core.ps1"
$policyFile = Join-Path $PSScriptRoot "..\policies\Claude.json"

& $coreScript `
    -PolicyFile $policyFile `
    -AgentId "Claude" `
    -TenantId "Casey" `
    -BaseUrl $BaseUrl `
    -EventJson $EventJson `
    -EventFile $EventFile `
    -AuthToken $env:CLAUDE_GATEWAY_TOKEN `
    -ApiKey $env:CLAUDE_GATEWAY_API_KEY `
    -DryRun:$DryRun
