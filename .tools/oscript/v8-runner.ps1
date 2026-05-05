param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'

## Новый путь: читаем v8.projects.json
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..\..\..')
$jsonPath = Join-Path $repoRoot 'v8.projects.json'
$ovmPath = ''
if (Test-Path $jsonPath) {
    $json = Get-Content $jsonPath -Raw | ConvertFrom-Json
    $ovmPath = $json.tools.ovm
}
if (-not $ovmPath -or -not (Test-Path $ovmPath)) {
    Write-Error "[v8-runner.ps1] OVM не найден по пути: $ovmPath"
    exit 1
}

# Активируем ovm окружение
& $ovmPath use --install dev

# Проверяем наличие oscript
try {
    oscript -version | Out-Null
} catch {
    Write-Error "oscript не найден или не установлен в PATH"
    exit 1
}

# Запускаем vrunner с переданными аргументами
$cmd = @('vrunner') + $Args
Write-Host "[v8-runner.ps1] Запуск: $($cmd -join ' ')"
$proc = Start-Process -FilePath $cmd[0] -ArgumentList $cmd[1..($cmd.Count-1)] -Wait -NoNewWindow -PassThru
exit $proc.ExitCode
