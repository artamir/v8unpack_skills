param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    [string]$SourcePath,
    [string]$CfPath
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
$src = if ($SourcePath) { $SourcePath } else { $project.src }
$build = $project.build
if (-not $src) {
    Write-Error "src не найден в проекте $ProjectName"
    exit 1
}
if (-not $CfPath -and -not $build) {
    Write-Error "build не найден в проекте $ProjectName"
    exit 1
}
# Имя cf-файла для сборки
$cf = if ($CfPath) { $CfPath } else { Join-Path $build "$ProjectName.cf" }
$cfDir = Split-Path -Parent $cf
if ($cfDir -and !(Test-Path $cfDir)) {
    New-Item -ItemType Directory -Path $cfDir -Force | Out-Null
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

& $exe -B $src $cf
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ошибка сборки cf"
    exit $LASTEXITCODE
}
Write-Output "Сборка завершена: $src -> $cf"
