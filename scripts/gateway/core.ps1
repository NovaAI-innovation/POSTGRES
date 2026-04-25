#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PolicyFile,

    [Parameter(Mandatory = $true)]
    [string]$AgentId,

    [Parameter(Mandatory = $true)]
    [string]$TenantId,

    [string]$EventJson,
    [string]$EventFile,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AuthToken,
    [string]$ApiKey,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-EventPayload {
    if ($EventJson) {
        return $EventJson | ConvertFrom-Json -Depth 20
    }
    if ($EventFile) {
        if (-not (Test-Path -LiteralPath $EventFile)) {
            throw "Event file not found: $EventFile"
        }
        return (Get-Content -LiteralPath $EventFile -Raw) | ConvertFrom-Json -Depth 20
    }
    throw "One of -EventJson or -EventFile is required."
}

function Read-Policy {
    if (-not (Test-Path -LiteralPath $PolicyFile)) {
        throw "Policy file not found: $PolicyFile"
    }
    return (Get-Content -LiteralPath $PolicyFile -Raw) | ConvertFrom-Json -Depth 20
}

function New-Headers {
    param(
        [string]$RequestId,
        [string]$ActionId
    )

    $headers = @{
        "Content-Type" = "application/json"
        "X-Request-Id" = $RequestId
        "X-Action-Id"  = $ActionId
        "X-Actor"      = "claude-code"
    }

    if ($AuthToken) {
        $headers["Authorization"] = "Bearer $AuthToken"
    } elseif ($ApiKey) {
        $headers["X-API-Key"] = $ApiKey
        $headers["X-Tenant-Id"] = $TenantId
        $headers["X-Agent-Id"] = $AgentId
    } else {
        throw "Either -AuthToken or -ApiKey must be provided."
    }

    return $headers
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

function Invoke-GatewayCall {
    param(
        [string]$Path,
        [object]$Payload,
        [hashtable]$Headers
    )

    $uri = $BaseUrl.TrimEnd("/") + $Path
    $body = $Payload | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod -Method Post -Uri $uri -Headers $Headers -Body $body
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
            actor       = "claude-code"
            timestamp   = [DateTimeOffset]::UtcNow.ToString("o")
        }
    }

    Invoke-GatewayCall -Path "/memory/ingest" -Payload $logPayload -Headers $Headers | Out-Null
}

$policy = Read-Policy
$event = Read-EventPayload

$requestId = [guid]::NewGuid().ToString()
$actionId = [guid]::NewGuid().ToString()
$headers = New-Headers -RequestId $requestId -ActionId $actionId

$eventClass = Get-EventClass -Policy $policy -Event $event
$rule = Get-Rule -Policy $policy -RuleName $eventClass
if ($null -eq $rule) {
    throw "No policy rule found for event class '$eventClass'"
}

$content = [string](Get-FieldValue -InputObject $event -Name "content" -DefaultValue "")
$sensitive = Test-SensitiveContent -Policy $policy -Content $content
$persist = Should-PersistEvent -Policy $policy -Rule $rule -Event $event -Sensitive $sensitive
$startedAt = Get-Date

if (-not $DryRun) {
    Write-ActionLog -Stage "start" -Status "running" -Message "event_received" -RequestId $requestId -ActionId $actionId -Headers $headers -EventClass $eventClass
}

$result = @{
    request_id   = $requestId
    action_id    = $actionId
    agent_id     = $AgentId
    tenant_id    = $TenantId
    event_class  = $eventClass
    persisted    = $false
    sensitive    = $sensitive
    reason       = "skipped_by_policy"
    dry_run      = [bool]$DryRun
}

try {
    if ($persist) {
        $eventScope = Get-FieldValue -InputObject $event -Name "scope" -DefaultValue $null
        $scope = if ($eventScope) { [string]$eventScope } else { [string]$policy.default_scope }
        $sourceRef = Get-FieldValue -InputObject $event -Name "source_ref" -DefaultValue $null
        $payload = @{
            scope          = $scope
            owner_agent_id = $AgentId
            raw_content    = $content
            source_ref     = if ($sourceRef) { [string]$sourceRef } else { "event:$actionId" }
            metadata       = @{
                event_type   = $eventClass
                confidence   = Get-Confidence -Event $event
                request_id   = $requestId
                action_id    = $actionId
                actor        = "claude-code"
                policy_name  = [string]$policy.policy_name
                policy_ver   = [string]$policy.policy_version
                tags         = @($rule.tags)
                input_hash   = (
                    [System.BitConverter]::ToString(
                        [System.Security.Cryptography.SHA256]::Create().ComputeHash(
                            [System.Text.Encoding]::UTF8.GetBytes(($content))
                        )
                    ).Replace("-", "").ToLowerInvariant()
                )
            }
        }

        if ($sensitive -and $policy.sensitive_handling.mark_metadata_sensitive) {
            $payload.metadata["sensitive"] = $true
        }
        $groupId = Get-FieldValue -InputObject $event -Name "group_id" -DefaultValue $null
        if ($groupId) {
            $payload["group_id"] = [string]$groupId
        }

        if (-not $DryRun) {
            $apiResponse = Invoke-GatewayCall -Path "/memory/ingest" -Payload $payload -Headers $headers
            $result.persisted = [bool]$apiResponse.inserted
            $result.reason = if ($apiResponse.inserted) { "persisted" } else { [string]$apiResponse.reason }
            $result.api_response = $apiResponse
        } else {
            $result.persisted = $true
            $result.reason = "dry_run_would_persist"
            $result.payload_preview = $payload
        }
    }

    $result.status = "ok"
} catch {
    $result.status = "error"
    $result.error = $_.Exception.Message
    throw
} finally {
    $durationMs = [int]((Get-Date) - $startedAt).TotalMilliseconds
    $result.duration_ms = $durationMs

    if (-not $DryRun) {
        $finalStatus = if ($result.status -eq "ok") { "completed" } else { "failed" }
        $finalMessage = if ($result.reason) { [string]$result.reason } else { "error" }
        Write-ActionLog -Stage "end" -Status $finalStatus -Message $finalMessage -RequestId $requestId -ActionId $actionId -Headers $headers -EventClass $eventClass
    }

    $result | ConvertTo-Json -Depth 20
}
