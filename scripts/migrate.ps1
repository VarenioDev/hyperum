$ErrorActionPreference = "Stop"

$container = "hyperum_postgres"
$dbUser    = "hyperum"
$dbName    = "hyperum"
$migrationsDir = Join-Path $PSScriptRoot "..\migrations"

Get-ChildItem "$migrationsDir\*.sql" | Sort-Object Name | ForEach-Object {
    Write-Host "Applying $($_.Name)..." -ForegroundColor Cyan
    Get-Content $_.FullName -Raw | docker exec -i $container psql -U $dbUser -d $dbName -v ON_ERROR_STOP=1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $($_.Name)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "All migrations applied." -ForegroundColor Green