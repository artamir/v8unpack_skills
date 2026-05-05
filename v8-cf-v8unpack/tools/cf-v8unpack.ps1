param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectName,
    [string]$TargetPath,
    [string]$CfPath
)

$jsonPath = "e:/1CBases/NL/NL_v8unpack/v8.projects.json"
if (!(Test-Path $jsonPath)) {
    Write-Error "Not found v8.projects.json: $jsonPath"
    exit 1
}
$json = Get-Content $jsonPath -Raw | ConvertFrom-Json

if (-not $json.projects.$ProjectName) {
    Write-Error "Project '$ProjectName' not found in v8.projects.json"
    exit 1
}
$project = $json.projects.$ProjectName

$src = if ($TargetPath) { $TargetPath } else { $project.src }
$current = $project.current
$current_cf = $project.current_cf
if (-not $src) {
    Write-Error "src not found in project $ProjectName"
    exit 1
}

if (!(Test-Path $src)) {
    New-Item -ItemType Directory -Path $src -Force | Out-Null
}

# Ищем .cf файл сначала в current_cf, если есть, иначе в current
if ($CfPath) {
    if (!(Test-Path $CfPath)) {
        Write-Error "cf file not found: $CfPath"
        exit 1
    }
    $cf = Get-Item -Path $CfPath
} elseif ($current_cf -and (Test-Path $current_cf)) {
    $cf = Get-ChildItem -Path $current_cf -Filter *.cf -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
} else {
    $cf = Get-ChildItem -Path $current -Filter *.cf -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}
if (-not $cf) {
    Write-Error "No .cf file in $current_cf or $current"
    exit 1
}

$exe = $json.tools.v8unpack
if (-not $exe) {
    Write-Error "v8unpack.exe not found in tools"
    exit 1
}
if (!(Test-Path $exe)) {
    Write-Error "v8unpack.exe not found: $exe"
    exit 1
}

& $exe -E $($cf.FullName) $src
if ($LASTEXITCODE -ne 0) {
    Write-Error "cf unpack error"
    exit $LASTEXITCODE
}


