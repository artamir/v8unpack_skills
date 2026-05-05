param(
    [string]$ProjectName
)

## Новый путь: читаем v8.projects.json
$jsonPath = "e:/1CBases/NL/NL_v8unpack/v8.projects.json"
if (!(Test-Path $jsonPath)) {
    Write-Error "Не найден v8.projects.json: $jsonPath"
    exit 1
}
$json = Get-Content $jsonPath -Raw | ConvertFrom-Json

if (-not $json.projects.$ProjectName) {
    Write-Error "Проект '$ProjectName' не найден в v8.projects.json"
    exit 1
}
$project = $json.projects.$ProjectName
$current = $project.current
if (-not $current) {
    Write-Error "current не найден в проекте $ProjectName"
    exit 1
}
$db_user = $project.logins.default.db_user
$db_pwd = $project.logins.default.db_pwd
if (-not $db_user -or -not $db_pwd) {
    Write-Error "db_user или db_pwd не заданы в logins.default проекта $ProjectName"
    exit 1
}

$runner = Join-Path $PSScriptRoot "../../.tools/oscript/v8-runner.ps1"

# Запуск v8-runner.ps1 через powershell
$cmd = "powershell -ExecutionPolicy Bypass -File `"$runner`" designer --ibconnection '/F$current' --db-user '$db_user' --db-pwd '$db_pwd'"
Invoke-Expression $cmd
exit $LASTEXITCODE
