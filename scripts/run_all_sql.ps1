Get-ChildItem sql\*.sql | Sort-Object Name | ForEach-Object {
    & "$PSScriptRoot\run_sql.ps1" $_.FullName
}