<#
.SYNOPSIS
    Добавляет новый проект 1С v7.7 в workspace.

.DESCRIPTION
    Скрипт:
      1. Создаёт структуру папок проекта:
           current\<Project>\<Project>_ib\   — база данных 1С (пользователь копирует сюда файлы)
           src\<Project>\cf\                 — распакованные метаданные (1cv7.md)
           src\<Project>\extforms\           — распакованные внешние отчёты и обработки
           temp\<Project>\                   — временные файлы
           build\<Project>\                  — результат сборки MD
      2. Добавляет секцию [project.<Project>] в v7.projects.ini.
    Если секция уже существует, выводит предупреждение и завершается без изменений.

.PARAMETER Project
    Имя проекта (латиница/кириллица, без пробелов).

.PARAMETER BaseDir
    Явный путь к папке базы данных 1С (где лежит 1cv7.md).
    Если задан — используется как есть, папка current\<Project>\ НЕ создаётся.
    Если не задан — создаётся current\<Project>\<Project>_ib\.

.PARAMETER Force
    Если указан — перезаписать секцию в INI, даже если она уже существует.

.EXAMPLE
    .\add-project.ps1 -Project AliniaArt2018

.EXAMPLE
    .\add-project.ps1 -Project AliniaArt2018 -BaseDir "E:\1CBases\AliniaArt2018\AliniaArt2018_ib"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [string] $Project,

    [Parameter(Position = 1)]
    [string] $BaseDir = "",

    [switch] $Force
)


Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# Корень workspace — папка, где лежит v8.projects.json
$repoRoot = Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent) -Parent
$jsonPath  = Join-Path $repoRoot 'v8.projects.json'

if (-not (Test-Path $jsonPath)) {
    Write-Error "Файл v8.projects.json не найден: $jsonPath"
    exit 2
}

# ─── Загрузка и проверка существования проекта ───────────────────────────────
$json = Get-Content $jsonPath -Raw | ConvertFrom-Json
if ($json.projects.$Project -and -not $Force) {
    Write-Warning "Проект '$Project' уже существует в v8.projects.json. Используйте -Force для перезаписи."
    exit 0
}

# ─── Разрешение путей ────────────────────────────────────────────────────────
$ibFolderName  = "${Project}_ib"
$defaultBaseDir = "current/$Project/$ibFolderName"
$resolvedBaseDir = if ($BaseDir) { $BaseDir } else { $defaultBaseDir }

$srcDir      = "src/$Project"
$srcCfDir    = "src/$Project/cf"
$extformsDir = "src/$Project/extforms"
$tempDir     = "temp/$Project"
$buildDir    = "build/$Project"
$currentDir  = $resolvedBaseDir
$currentCfDir = "current/$Project/cf"

# ─── Создание папок ─────────────────────────────────────────────────────────
$foldersToCreate = @(
    (Join-Path $repoRoot $srcCfDir),
    (Join-Path $repoRoot $extformsDir),
    (Join-Path $repoRoot $tempDir),
    (Join-Path $repoRoot $buildDir)
)

# BASE_DIR создаём только если это относительный путь внутри workspace
if (-not [System.IO.Path]::IsPathRooted($resolvedBaseDir)) {
    $foldersToCreate += Join-Path $repoRoot $resolvedBaseDir
}

foreach ($folder in $foldersToCreate) {
    if (-not (Test-Path $folder)) {
        New-Item -Path $folder -ItemType Directory -Force | Out-Null
        Write-Host "  [создана]  $folder"
    } else {
        Write-Host "  [уже есть] $folder"
    }
}

# ─── Добавление секции в JSON ────────────────────────────────────────────────
$json.projects.$Project = @{
    src = $srcDir
    build = $buildDir
    temp = $tempDir
    current = $currentDir
    current_cf = $currentCfDir
    logins = @{ default = @{ db_user = "Administrator"; db_pwd = "P@rol@321" } }
}

Set-Content -Path $jsonPath -Value ($json | ConvertTo-Json -Depth 10) -Encoding UTF8

Write-Host ""
Write-Host "Проект '$Project' добавлен в v8.projects.json"
Write-Host "  src        = $srcDir"
Write-Host "  build      = $buildDir"
Write-Host "  temp       = $tempDir"
Write-Host "  current    = $currentDir"
Write-Host "  current_cf = $currentCfDir"
Write-Host ""
if ($BaseDir -eq "") {
    $ibPath = Join-Path $repoRoot $defaultBaseDir
    Write-Warning "current = $defaultBaseDir — папка создана, но файлы базы 1С туда ещё не скопированы."
    Write-Host "Следующий шаг: скопируйте файлы базы 1С в:`n  $ibPath"
    Write-Host "Или при следующем запуске укажите -BaseDir <путь к существующей базе>"
}
    $ibPath = Join-Path $repoRoot $defaultBaseDir
