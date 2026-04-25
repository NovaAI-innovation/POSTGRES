param(
    [string]$DatabaseUrl = "",
    [string]$MigrationsDir = "app/db/migrations"
)

$ErrorActionPreference = "Stop"

function Load-DotEnv {
    param([string]$Path = ".env")
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $parts = $line -split "=", 2
        $k = $parts[0].Trim()
        $v = $parts[1].Trim().Trim('"')
        if ($k) { Set-Item -Path ("env:" + $k) -Value $v }
    }
}

Load-DotEnv

if (-not $DatabaseUrl) {
    $DatabaseUrl = $env:SUPABASE_DB_URL
}

if (-not $DatabaseUrl) {
    throw "Missing database URL. Pass -DatabaseUrl or set SUPABASE_DB_URL in .env (Postgres connection string)."
}

if (-not (Test-Path $MigrationsDir)) {
    throw "Migrations directory not found: $MigrationsDir"
}

$files = Get-ChildItem -Path $MigrationsDir -Filter *.sql | Sort-Object Name
if ($files.Count -eq 0) {
    throw "No SQL migrations found in $MigrationsDir"
}

Write-Host "Applying migrations to Supabase..."
foreach ($file in $files) {
    Write-Host " - $($file.Name)"
    & psql $DatabaseUrl -v ON_ERROR_STOP=1 -f $file.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Migration failed: $($file.Name)"
    }
}

Write-Host "Supabase migrations complete."
