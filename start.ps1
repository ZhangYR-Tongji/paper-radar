[CmdletBinding()]
param(
    [string]$EnvName = "paper-radar",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$SkipDbInit,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Write-Step {
    param([string]$Message)
    Write-Host "[paper-radar] $Message" -ForegroundColor Cyan
}

function Quote-ForPowerShell {
    param([string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Test-PortInUse {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Start-DevWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $quotedTitle = $Title -replace "'", "''"
    $quotedWorkingDirectory = Quote-ForPowerShell $WorkingDirectory

    $windowScript = @"
`$ErrorActionPreference = 'Stop'
`$Host.UI.RawUI.WindowTitle = '$quotedTitle'
Set-Location -LiteralPath $quotedWorkingDirectory
$Command
if (`$LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host "Command exited with code `$LASTEXITCODE." -ForegroundColor Red
}
"@

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $windowScript
    ) | Out-Null
}

if (-not (Test-Path -LiteralPath $BackendDir)) {
    throw "Backend directory not found: $BackendDir"
}

if (-not (Test-Path -LiteralPath $FrontendDir)) {
    throw "Frontend directory not found: $FrontendDir"
}

$conda = (Get-Command conda -ErrorAction Stop).Source
$condaQuoted = Quote-ForPowerShell $conda
$envNameQuoted = Quote-ForPowerShell $EnvName

Write-Step "Checking Conda environment '$EnvName'..."
$envListJson = & $conda env list --json
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read Conda environments."
}

$envList = $envListJson | ConvertFrom-Json
$envExists = $false
foreach ($envPath in $envList.envs) {
    if ((Split-Path -Leaf $envPath) -eq $EnvName) {
        $envExists = $true
        break
    }
}

if (-not $envExists) {
    throw "Conda environment '$EnvName' was not found. Run: conda env create -f environment.yml"
}

if (Test-PortInUse $BackendPort) {
    throw "Port $BackendPort is already in use. Stop the existing backend or pass -BackendPort <port>."
}

if (Test-PortInUse $FrontendPort) {
    throw "Port $FrontendPort is already in use. Stop the existing frontend or pass -FrontendPort <port>."
}

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    Write-Step "Installing frontend dependencies with npm install..."
    Push-Location $FrontendDir
    try {
        & $conda run -n $EnvName --no-capture-output npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

Write-Step "Starting backend on http://127.0.0.1:$BackendPort"
if ($SkipDbInit) {
    $backendCommand = @"
& $condaQuoted run -n $envNameQuoted --no-capture-output python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $BackendPort
"@
}
else {
    $backendCommand = @"
& $condaQuoted run -n $envNameQuoted --no-capture-output python -m app.cli
if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }
& $condaQuoted run -n $envNameQuoted --no-capture-output python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $BackendPort
"@
}
Start-DevWindow -Title "Paper Radar Backend" -WorkingDirectory $BackendDir -Command $backendCommand

Write-Step "Starting frontend on http://localhost:$FrontendPort"
$frontendCommand = @"
& $condaQuoted run -n $envNameQuoted --no-capture-output npm run dev -- -p $FrontendPort
"@
Start-DevWindow -Title "Paper Radar Frontend" -WorkingDirectory $FrontendDir -Command $frontendCommand

if (-not $NoBrowser) {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:$FrontendPort" | Out-Null
}

Write-Step "Done. Close the backend/frontend PowerShell windows to stop the project."
$global:LASTEXITCODE = 0
