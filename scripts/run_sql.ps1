param(
    [Parameter(Mandatory=$true)]
    [string]$SqlFile
)

$fileName = Split-Path $SqlFile -Leaf
Write-Host ""
Write-Host "=== $fileName ===" -ForegroundColor Cyan
Write-Host ""

docker cp $SqlFile "hyperum_postgres:/tmp/$fileName"
docker exec -i hyperum_postgres psql -U hyperum -d hyperum -f "/tmp/$fileName"