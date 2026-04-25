#Requires -Version 5.1

[CmdletBinding()]
param(
    [ValidateSet("direct", "remote")]
    [string]$Mode = "direct",

    [ValidateSet("memory_event", "api_proxy")]
    [string]$Operation = "memory_event",

    [string]$TenantId = "Casey",

    [string]$EventJson,
    [string]$EventFile,

    [string]$Method = "POST",
    [string]$Path = "/memory/ingest",
    [string]$PayloadJson,
    [string]$PayloadFile,

    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$GatewayUrl = "http://127.0.0.1:8787",
    [string]$PolicyFile,
    [string]$AgentProfilesFile,

    [string]$AuthToken,
    [string]$ApiKey,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AgentId = "Agent-0"
if (-not $PolicyFile) {
    $PolicyFile = Join-Path $PSScriptRoot "..\policies\Agent-0.json"
}
if (-not $AgentProfilesFile) {
    $AgentProfilesFile = Join-Path $PSScriptRoot "..\policies\agent_profiles.json"
}
if (-not $AuthToken) {
    $AuthToken = $env:AGENT0_GATEWAY_TOKEN
}
if (-not $ApiKey) {
    $ApiKey = $env:AGENT0_GATEWAY_API_KEY
}

function Read-JsonObject {
    param(
        [string]$JsonText,
        [string]$JsonFile,
        [string]$ErrorContext
    )
    if ($JsonText) {
        return $JsonText | ConvertFrom-Json
    }
    if ($JsonFile) {
        if (-not (Test-Path -LiteralPath $JsonFile)) {
            throw "$ErrorContext file not found: $JsonFile"
        }
        return (Get-Content -LiteralPath $JsonFile -Raw) | ConvertFrom-Json
    }
    return $null
}

function Read-Policy {
    if (-not (Test-Path -LiteralPath $PolicyFile)) {
        throw "Policy file not found: $PolicyFile"
    }
    return (Get-Content -LiteralPath $PolicyFile -Raw) | ConvertFrom-Json
}

function Read-AgentProfile {
    if (-not (Test-Path -LiteralPath $AgentProfilesFile)) {
        throw "Agent profiles file not found: $AgentProfilesFile"
    }
    $profiles = (Get-Content -LiteralPath $AgentProfilesFile -Raw) | ConvertFrom-Json
    $agent = $profiles.agents.$AgentId
    if ($null -eq $agent) {
        throw "Agent profile not found for '$AgentId'"
    }
    return $agent
}

function Get-FieldValue {
    param(
        [object]$InputObject,
        [string]$Name,
        [object]$DefaultValue = $null
    )

    if ($null -eq $InputObject) {
        return $DefaultValue
    }

    $prop = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $prop) {
        return $DefaultValue
    }
    return $prop.Value
}

function Get-Rule {
    param(
        [object]$Policy,
        [string]$RuleName
    )

    foreach ($candidate in $Policy.rules.PSObject.Properties) {
        if ($candidate.Name -eq $RuleName) {
            return $candidate.Value
        }
    }
    return $null
}

function Get-EventClass {
    param(
        [object]$Policy,
        [object]$Event
    )

    $eventType = Get-FieldValue -InputObject $Event -Name "event_type" -DefaultValue $null
    if ($eventType) {
        $exact = Get-Rule -Policy $Policy -RuleName ([string]$eventType)
        if ($null -ne $exact) {
            return [string]$eventType
        }
    }

    $content = [string](Get-FieldValue -InputObject $Event -Name "content" -DefaultValue "")
    foreach ($rule in $Policy.rules.PSObject.Properties) {
        foreach ($pattern in $rule.Value.detect_patterns) {
            if ($content -match [string]$pattern) {
                return [string]$rule.Name
            }
        }
    }

    return [string]$Policy.default_rule
}

function Test-SensitiveContent {
    param(
        [object]$Policy,
        [string]$Content
    )

    foreach ($pattern in $Policy.sensitive_patterns) {
        if ($Content -match [string]$pattern) {
            return $true
        }
    }
    return $false
}

function Get-Confidence {
    param([object]$Event)
    $value = Get-FieldValue -InputObject $Event -Name "confidence" -DefaultValue $null
    if ($null -eq $value) {
        return 1.0
    }
    return [double]$value
}

function Should-PersistEvent {
    param(
        [object]$Policy,
        [object]$Rule,
        [object]$Event,
        [bool]$Sensitive
    )

    if ($Sensitive -and -not $Policy.sensitive_handling.persist_sensitive) {
        return $false
    }

    if (-not $Rule.enabled) {
        return $false
    }

    $confidence = Get-Confidence -Event $Event
    if ($confidence -lt [double]$Rule.min_confidence) {
        return $false
    }

    $scope = Get-FieldValue -InputObject $Event -Name "scope" -DefaultValue ""
    if ([string]$scope -eq "shared" -and -not $Policy.allow_shared_scope) {
        return $false
    }

    return $true
}

function New-DirectHeaders {
    param(
        [string]$RequestId,
        [string]$ActionId
    )

    $headers = @{
        "Content-Type" = "application/json"
        "X-Request-Id" = $RequestId
        "X-Action-Id"  = $ActionId
        "X-Actor"      = $AgentId
    }

    if ($AuthToken) {
        $headers["Authorization"] = "Bearer $AuthToken"
    } elseif ($ApiKey) {
        $headers["X-API-Key"] = $ApiKey
        $headers["X-Tenant-Id"] = $TenantId
        $headers["X-Agent-Id"] = $AgentId
    } else {
        throw "Direct mode requires -AuthToken or -ApiKey (or AGENT0_GATEWAY_TOKEN / AGENT0_GATEWAY_API_KEY env vars)."
    }

    return $headers
}

function Invoke-JsonApi {
    param(
        [string]$Url,
        [string]$HttpMethod,
        [object]$Payload,
        [hashtable]$Headers
    )

    $json = $Payload | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod -Method $HttpMethod -Uri $Url -Headers $Headers -Body $json
}

function Write-ActionLog {
    param(
        [string]$Stage,
        [string]$Status,
        [string]$Message,
        [string]$RequestId,
        [string]$ActionId,
        [hashtable]$Headers,
        [string]$EventClass
    )

    $logPayload = @{
        scope          = "isolated"
        owner_agent_id = $AgentId
        raw_content    = "action_log stage=$Stage status=$Status message=$Message"
        source_ref     = "gateway:$ActionId"
        metadata       = @{
            log_type    = "action_log"
            stage       = $Stage
            status      = $Status
            request_id  = $RequestId
            action_id   = $ActionId
            event_class = $EventClass
            actor       = $AgentId
            timestamp   = [DateTimeOffset]::UtcNow.ToString("o")
        }
    }

    $uri = $BaseUrl.TrimEnd("/") + "/memory/ingest"
    Invoke-JsonApi -Url $uri -HttpMethod "POST" -Payload $logPayload -Headers $Headers | Out-Null
}

function Test-PathAllowed {
    param(
        [object]$Profile,
        [string]$HttpMethod,
        [string]$ApiPath
    )

    $allowedMethods = @{}
    foreach ($m in $Profile.allowed_methods) {
        $allowedMethods[[string]$m.ToUpperInvariant()] = $true
    }

    $methodUpper = $HttpMethod.ToUpperInvariant()
    if ($allowedMethods.Count -gt 0 -and -not $allowedMethods.ContainsKey($methodUpper)) {
        return $false
    }

    foreach ($prefix in $Profile.allowed_path_prefixes) {
        if ($ApiPath.StartsWith([string]$prefix)) {
            return $true
        }
    }

    return $false
}

$event = Read-JsonObject -JsonText $EventJson -JsonFile $EventFile -ErrorContext "Event"
$payload = Read-JsonObject -JsonText $PayloadJson -JsonFile $PayloadFile -ErrorContext "Payload"

if ($Operation -eq "memory_event" -and $null -eq $event) {
    throw "memory_event requires -EventJson or -EventFile"
}

if ($Operation -eq "api_proxy" -and -not $Path.StartsWith("/")) {
    throw "api_proxy requires -Path starting with '/'"
}

$requestId = [guid]::NewGuid().ToString()
$actionId = [guid]::NewGuid().ToString()
$startedAt = Get-Date

$result = @{
    request_id = $requestId
    action_id = $actionId
    mode = $Mode
    operation = $Operation
    agent_id = $AgentId
    tenant_id = $TenantId
    dry_run = [bool]$DryRun
}

$hadError = $false
$errorMessage = ""
$headers = $null

try {
    if ($Mode -eq "remote") {
        $remoteBody = @{
            operation = $Operation
            agent_id = $AgentId
            tenant_id = $TenantId
            dry_run = [bool]$DryRun
        }
        if ($Operation -eq "memory_event") {
            $remoteBody["event"] = $event
        } else {
            $remoteBody["method"] = $Method.ToUpperInvariant()
            $remoteBody["path"] = $Path
            $remoteBody["payload"] = if ($null -eq $payload) { @{} } else { $payload }
        }

        $uri = $GatewayUrl.TrimEnd("/") + "/gateway/execute"
        $remoteResponse = Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body ($remoteBody | ConvertTo-Json -Depth 20 -Compress)
        $result.status = "ok"
        $result.gateway_response = $remoteResponse
    } else {
        $policy = Read-Policy
        $profile = Read-AgentProfile
        if (-not $DryRun) {`n            $headers = New-DirectHeaders -RequestId $requestId -ActionId $actionId`n        }

        $eventClass = if ($Operation -eq "memory_event") { Get-EventClass -Policy $policy -Event $event } else { "api_proxy" }

        if (-not $DryRun) {
            Write-ActionLog -Stage "start" -Status "running" -Message "received" -RequestId $requestId -ActionId $actionId -Headers $headers -EventClass $eventClass
        }

        if ($Operation -eq "memory_event") {
            $rule = Get-Rule -Policy $policy -RuleName $eventClass
            if ($null -eq $rule) {
                throw "No policy rule found for event class '$eventClass'"
            }

            $content = [string](Get-FieldValue -InputObject $event -Name "content" -DefaultValue "")
            $sensitive = Test-SensitiveContent -Policy $policy -Content $content
            $persist = Should-PersistEvent -Policy $policy -Rule $rule -Event $event -Sensitive $sensitive

            $result.event_class = $eventClass
            $result.sensitive = $sensitive
            $result.persist = $persist

            if ($persist) {
                $eventScope = Get-FieldValue -InputObject $event -Name "scope" -DefaultValue $null
                $scope = if ($eventScope) { [string]$eventScope } else { [string]$policy.default_scope }
                $sourceRef = Get-FieldValue -InputObject $event -Name "source_ref" -DefaultValue $null
                $directPayload = @{
                    scope          = $scope
                    owner_agent_id = $AgentId
                    raw_content    = $content
                    source_ref     = if ($sourceRef) { [string]$sourceRef } else { "event:$actionId" }
                    metadata       = @{
                        event_type  = $eventClass
                        confidence  = Get-Confidence -Event $event
                        request_id  = $requestId
                        action_id   = $actionId
                        actor       = $AgentId
                        policy_name = [string]$policy.policy_name
                        policy_ver  = [string]$policy.policy_version
                        tags        = @($rule.tags)
                        input_hash  = (
                            [System.BitConverter]::ToString(
                                [System.Security.Cryptography.SHA256]::Create().ComputeHash(
                                    [System.Text.Encoding]::UTF8.GetBytes($content)
                                )
                            ).Replace("-", "").ToLowerInvariant()
                        )
                    }
                }

                if ($sensitive -and $policy.sensitive_handling.mark_metadata_sensitive) {
                    $directPayload.metadata["sensitive"] = $true
                }
                $groupId = Get-FieldValue -InputObject $event -Name "group_id" -DefaultValue $null
                if ($groupId) {
                    $directPayload["group_id"] = [string]$groupId
                }

                if ($DryRun) {
                    $result.result = @{ status = "dry_run"; payload_preview = $directPayload }
                    $result.reason = "dry_run_would_persist"
                } else {
                    $uri = $BaseUrl.TrimEnd("/") + "/memory/ingest"
                    $apiResponse = Invoke-JsonApi -Url $uri -HttpMethod "POST" -Payload $directPayload -Headers $headers
                    $inserted = [bool](Get-FieldValue -InputObject $apiResponse -Name "inserted" -DefaultValue $false)
                    $result.reason = if ($inserted) { "persisted" } else { [string](Get-FieldValue -InputObject $apiResponse -Name "reason" -DefaultValue "not_inserted") }
                    $result.target_response = $apiResponse
                }
            } else {
                $result.reason = "skipped_by_policy"
                $result.result = @{ status = "skipped"; reason = "skipped_by_policy" }
            }
        } else {
            $methodUpper = $Method.ToUpperInvariant()
            if (-not (Test-PathAllowed -Profile $profile -HttpMethod $methodUpper -ApiPath $Path)) {
                throw "api_proxy path or method not allowed for ${AgentId}: $methodUpper $Path"
            }

            if ($DryRun) {
                $result.result = @{ status = "dry_run"; method = $methodUpper; path = $Path }
            } else {
                $proxyUri = $BaseUrl.TrimEnd("/") + $Path
                $proxyResponse = Invoke-JsonApi -Url $proxyUri -HttpMethod $methodUpper -Payload $(if ($null -eq $payload) { @{} } else { $payload }) -Headers $headers
                $result.target_response = $proxyResponse
            }
            $result.reason = if ($DryRun) { "api_proxy_dry_run" } else { "api_proxy_executed" }
        }

        $result.status = "ok"
    }
} catch {
    $hadError = $true
    $errorMessage = $_.Exception.Message
    $result.status = "error"
    $result.error = $errorMessage
} finally {
    if ($Mode -eq "direct" -and -not $DryRun -and $null -ne $headers) {
        try {
            $finalStatus = if ($hadError) { "failed" } else { "completed" }
            $finalMessage = if ($hadError) { "error" } elseif ($result.reason) { [string]$result.reason } else { "ok" }
            $eventClassFinal = if ($Operation -eq "memory_event" -and $result.event_class) { [string]$result.event_class } else { "api_proxy" }
            Write-ActionLog -Stage "end" -Status $finalStatus -Message $finalMessage -RequestId $requestId -ActionId $actionId -Headers $headers -EventClass $eventClassFinal
        } catch {
            if (-not $hadError) {
                $hadError = $true
                $errorMessage = $_.Exception.Message
                $result.status = "error"
                $result.error = $errorMessage
            }
        }
    }

    $result.duration_ms = [int]((Get-Date) - $startedAt).TotalMilliseconds
    $result | ConvertTo-Json -Depth 20
}

if ($hadError) {
    throw $errorMessage
}