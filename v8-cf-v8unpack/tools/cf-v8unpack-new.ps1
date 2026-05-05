param(
    [string]$ProjectName
)

# Читаем v8.projects.json
$jsonPath = Join-Path $PSScriptRoot "../../../v8.projects.json"
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
$src = $project.src
$current = $project.current
if (-not $src) {
    Write-Error "src не найден в проекте $ProjectName"
    exit 1
}

# Ищем .cf файл в current
$cf = Get-ChildItem -Path $current -Filter *.cf -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $cf) {
    Write-Error "Не найден .cf файл в $current"
    exit 1
}

# Получаем путь к v8unpack.exe из tools
$exe = $json.tools.v8unpack
if (-not $exe) {
    Write-Error "v8unpack.exe не найден в секции tools v8.projects.json"
    exit 1
}
if (!(Test-Path $exe)) {
    Write-Error "Не найден v8unpack.exe: $exe"
    exit 1
}

& $exe -E $($cf.FullName) $src
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ошибка распаковки cf"
    exit $LASTEXITCODE
}

Write-Output ("Распаковка завершена: $($cf.FullName) -> $src")
