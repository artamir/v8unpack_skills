<#
.SYNOPSIS
    Удаляет проект из v8.projects.json и по умолчанию удаляет папки проекта.
.PARAMETER Project
    Имя проекта (ключ в секции projects).
.PARAMETER KeepFolders
    Если указан — не удалять папки src, build, temp, current проекта.
.PARAMETER Force
    Не запрашивать подтверждение.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Project,

    [switch]$KeepFolders,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
$JsonPath = Join-Path $RootDir "v8.projects.json"

if (-not (Test-Path $JsonPath)) {
    Write-Error "Файл v8.projects.json не найден: $JsonPath"
    exit 1
}

$json = Get-Content $JsonPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $json.projects.PSObject.Properties[$Project]) {
    Write-Error "Проект '$Project' не найден в v8.projects.json"
    exit 1
}

$proj = $json.projects.$Project

# По умолчанию удаляем папки проекта; отключается через -KeepFolders
$foldersToDelete = @()
if (-not $KeepFolders) {
    foreach ($key in @('src','build','temp','current')) {
        $rel = $proj.$key
        if ($rel) {
            $abs = Join-Path $RootDir $rel
            # Берём корень папки проекта (на 1 уровень выше current/<Name>/<Name>_ib -> current/<Name>)
            if ($key -eq 'current') {
                $abs = Split-Path -Parent $abs
            }
            $foldersToDelete += $abs
        }
    }
    # Убираем дубликаты
    $foldersToDelete = $foldersToDelete | Select-Object -Unique
}

# Подтверждение
if (-not $Force) {
    Write-Host ""
    Write-Host "Будет выполнено:" -ForegroundColor Yellow
    Write-Host "  - Удаление записи проекта '$Project' из v8.projects.json"
    if ($foldersToDelete.Count -gt 0) {
        Write-Host "  - Удаление папок:" -ForegroundColor Red
        foreach ($f in $foldersToDelete) {
            Write-Host "      $f" -ForegroundColor Red
        }
    } else {
        Write-Host "  - Папки проекта будут сохранены (-KeepFolders)" -ForegroundColor Gray
    }
    $confirm = Read-Host "Продолжить? (y/N)"
    if ($confirm -notmatch '^[Yy]$') {
        Write-Host "Отменено." -ForegroundColor Gray
        exit 0
    }
}

# Удалить папки
if ($foldersToDelete.Count -gt 0) {
    foreach ($f in $foldersToDelete) {
        if (Test-Path $f) {
            Remove-Item -Recurse -Force $f
            Write-Host "Удалена папка: $f" -ForegroundColor DarkYellow
        } else {
            Write-Host "Папка не существует (пропущено): $f" -ForegroundColor Gray
        }
    }
}

# Удалить запись из JSON
$json.projects.PSObject.Properties.Remove($Project)

# Сохранить JSON
$jsonOut = $json | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($JsonPath, $jsonOut, [System.Text.Encoding]::UTF8)

Write-Host ""
Write-Host "Проект '$Project' успешно удалён из v8.projects.json." -ForegroundColor Green
