[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingPlainTextForPassword', '', Justification = 'Local development Docker bootstrap script; no production secret handling.')]
param(
    [string]$ContainerName = "agent-memory-postgres",
    [string]$Image = "pgvector/pgvector:pg16",
    [string]$DbUser = "postgres",
    [string]$DbPassword = "postgres",
    [string]$DbName = "agent_memory",
    [int]$HostPort = 5432,
    [switch]$Recreate,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Output "==> $Message"
}

function Invoke-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($DockerArgs -join ' ')"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$migrationsDir = Join-Path $repoRoot "app\db\migrations"

if (-not (Test-Path $migrationsDir)) {
    throw "Migrations directory not found: $migrationsDir"
}

$existing = [string](& docker ps -a --filter "name=^${ContainerName}$" --format "{{.Names}}" | Select-Object -First 1)
if ($LASTEXITCODE -ne 0) {
    throw "Docker command failed: docker ps -a --filter name=^${ContainerName}$ --format {{.Names}}"
}
if ($null -eq $existing) {
    $existing = ""
} else {
    $existing = $existing.Trim()
}
if ($existing -eq $ContainerName -and $Recreate) {
    Write-Step "Removing existing container '$ContainerName' (--Recreate set)"
    Invoke-Docker @("rm", "-f", $ContainerName)
    $existing = ""
}

if ($existing -eq $ContainerName) {
    $running = [string](& docker ps --filter "name=^${ContainerName}$" --format "{{.Names}}" | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker ps --filter name=^${ContainerName}$ --format {{.Names}}"
    }
    if ($null -eq $running) {
        $running = ""
    } else {
        $running = $running.Trim()
    }
    if ($running -ne $ContainerName) {
        Write-Step "Starting existing container '$ContainerName'"
        Invoke-Docker @("start", $ContainerName)
    } else {
        Write-Step "Container '$ContainerName' already running"
    }
} else {
    Write-Step "Creating PostgreSQL container '$ContainerName' from image '$Image'"
    $mount = "${repoRoot}:/workspace"
    Invoke-Docker @(
        "run", "-d",
        "--name", $ContainerName,
        "-e", "POSTGRES_USER=$DbUser",
        "-e", "POSTGRES_PASSWORD=$DbPassword",
        "-e", "POSTGRES_DB=$DbName",
        "-p", "${HostPort}:5432",
        "-v", $mount,
        $Image
    )
}

Write-Step "Waiting for PostgreSQL readiness"
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    & docker exec $ContainerName pg_isready -U $DbUser -d $DbName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw "PostgreSQL did not become ready in time."
}

$migrationFiles = Get-ChildItem -Path $migrationsDir -Filter "*.sql" | Sort-Object Name
if ($migrationFiles.Count -eq 0) {
    throw "No migration files found in $migrationsDir"
}

Write-Step "Applying migrations"
foreach ($file in $migrationFiles) {
    $containerPath = "/workspace/app/db/migrations/$($file.Name)"
    Write-Output "  - $($file.Name)"
    & docker exec $ContainerName psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -f $containerPath | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Migration failed: $($file.Name)"
    }
}

$databaseUrl = "postgresql://${DbUser}:${DbPassword}@localhost:${HostPort}/${DbName}"
Write-Step "Migrations complete"
Write-Output "DATABASE_URL=$databaseUrl"
Write-Output "Container: $ContainerName"

if ($RunTests) {
    Write-Step "Running test suite"
    Push-Location $repoRoot
    try {
        & python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Tests failed."
        }
    } finally {
        Pop-Location
    }
}
