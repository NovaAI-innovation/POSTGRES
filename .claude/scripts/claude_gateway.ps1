#Requires -Version 5.1

[CmdletBinding()]
param(
    [ValidateSet("memory_event", "api_proxy")]
    [string]$Operation = "memory_event",
    [string]$EventJson,
    [string]$EventFile,
    [string]$Method = "POST",
    [string]$Path = "/memory/ingest",
    [string]$PayloadJson,
    [string]$PayloadFile,
    [string]$GatewayUrl = "http://127.0.0.1:8787",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-JsonObject {
    param(
        [string]$JsonText,
        [string]$JsonFile
    )
    if ($JsonText) {
        return $JsonText | ConvertFrom-Json -Depth 20
    }
    if ($JsonFile) {
        if (-not (Test-Path -LiteralPath $JsonFile)) {
            throw "JSON file not found: $JsonFile"
        }
        return (Get-Content -LiteralPath $JsonFile -Raw) | ConvertFrom-Json -Depth 20
    }
    return $null
}

$event = Read-JsonObject -JsonText $EventJson -JsonFile $EventFile
$payload = Read-JsonObject -JsonText $PayloadJson -JsonFile $PayloadFile

$body = @{
    operation = $Operation
    agent_id = "Claude"
    tenant_id = "Casey"
    dry_run = [bool]$DryRun
}

if ($Operation -eq "memory_event") {
    if ($null -eq $event) {
        throw "memory_event requires -EventJson or -EventFile"
    }
    $body["event"] = $event
} else {
    $body["method"] = $Method.ToUpperInvariant()
    $body["path"] = $Path
    $body["payload"] = if ($null -eq $payload) { @{} } else { $payload }
}

$uri = $GatewayUrl.TrimEnd("/") + "/gateway/execute"
$json = $body | ConvertTo-Json -Depth 20 -Compress
Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body $json | ConvertTo-Json -Depth 20
