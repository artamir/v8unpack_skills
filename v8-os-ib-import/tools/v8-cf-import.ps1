param(
    [string]$ProjectName
)


# Читаем v8.projects.json (3 уровня вверх → workspace root)
$jsonPath = Join-Path $PSScriptRoot "../../../v8.projects.json"
if (!(Test-Path $jsonPath)) {
    Write-Error "Не найден v8.projects.json: $jsonPath"
    exit 1
}
$json = Get-Content $jsonPath -Raw | ConvertFrom-Json

# Поиск проекта включая подпроекты
function Find-V8Project { param($nodes, [string]$name)
    if ($nodes.$name) { return $nodes.$name }
    foreach ($p in $nodes.PSObject.Properties) { if ($p.Value.projects) { $r = Find-V8Project $p.Value.projects $name; if ($r) { return $r } } }
    return $null
}
$project = Find-V8Project $json.projects $ProjectName
if (-not $project) {
    Write-Error "Проект '$ProjectName' не найден в v8.projects.json"
    exit 1
}
$current = $project.current
$build = $project.build
$current_cf = $project.current_cf
if (-not $current) {
    Write-Error "current не найден в проекте $ProjectName"
    exit 1
}
if (-not $build) {
    Write-Error "build не найден в проекте $ProjectName"
    exit 1
}
if ($current_cf) {
    if (!(Test-Path $current_cf)) { New-Item -ItemType Directory -Path $current_cf | Out-Null }
    $cfFile = Join-Path $current_cf "$ProjectName.cf"
} else {
    $cfFile = Join-Path $build "$ProjectName.cf"
}
# Получаем логин по умолчанию
$db_user = $project.logins.default.db_user
$db_pwd = $project.logins.default.db_pwd
if (-not $db_user -or -not $db_pwd) {
    Write-Error "db_user или db_pwd не заданы в logins.default проекта $ProjectName"
    exit 1
}

# Формируем команду для v8-runner.ps1
$runner = Join-Path $PSScriptRoot "../../.tools/oscript/v8-runner.ps1"

# Запуск v8-runner.ps1 через powershell
$cmd = "powershell -ExecutionPolicy Bypass -File `"$runner`" load --ibconnection '/F$current' --src '$cfFile' --db-user '$db_user' --db-pwd '$db_pwd'"
Invoke-Expression $cmd
exit $LASTEXITCODE
