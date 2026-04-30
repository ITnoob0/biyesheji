param(
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [string]$FrontendHost = "127.0.0.1",
    [int]$FrontendPort = 5173,
    [switch]$SkipBackendPreflight,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Test-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)

    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-PortInUse {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1)
    } catch {
        return $false
    }
}

function New-WindowCommand {
    param(
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$WindowTitle,
        [Parameter(Mandatory = $true)][string[]]$Commands
    )

    $escapedWorkingDirectory = $WorkingDirectory.Replace("'", "''")
    $allCommands = @(
        "Set-Location -LiteralPath '$escapedWorkingDirectory'"
        "`$Host.UI.RawUI.WindowTitle = '$WindowTitle'"
    ) + $Commands

    return ($allCommands -join "; ")
}

function Start-WindowProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Command
    )

    if ($DryRun) {
        Write-Host "[DryRun] $Label command:"
        Write-Host $Command
        Write-Host ""
        return
    }

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $Command
    ) | Out-Null

    Write-Host "[OK] $Label window started."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

if (-not (Test-Path -LiteralPath $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}

if (-not (Test-CommandExists "python")) {
    throw "python command was not found. Please install Python or add it to PATH."
}

if (-not (Test-CommandExists "npm")) {
    throw "npm command was not found. Please install Node.js or add it to PATH."
}

$backendCommand = New-WindowCommand -WorkingDirectory $backendDir -WindowTitle "BiShe Backend" -Commands @(
    "Write-Host 'Backend directory: $backendDir' -ForegroundColor Cyan"
    "Write-Host 'Backend URL: http://$BackendHost`:$BackendPort' -ForegroundColor Cyan"
    $(if ($SkipBackendPreflight) {
        "Write-Host 'Skipping backend preflight.' -ForegroundColor Yellow"
    } else {
        "python .\scripts\startup_preflight.py; if (`$LASTEXITCODE -ne 0) { Write-Host 'Backend preflight failed. Press Enter to close.' -ForegroundColor Red; Read-Host | Out-Null; exit `$LASTEXITCODE }"
    })
    "python .\manage.py runserver ${BackendHost}:${BackendPort}"
)

$frontendCommand = New-WindowCommand -WorkingDirectory $frontendDir -WindowTitle "BiShe Frontend" -Commands @(
    "Write-Host 'Frontend directory: $frontendDir' -ForegroundColor Green"
    "Write-Host 'Frontend URL: http://$FrontendHost`:$FrontendPort' -ForegroundColor Green"
    "npm run dev -- --host $FrontendHost --port $FrontendPort"
)

$startedAny = $false

if (Test-PortInUse -Port $BackendPort) {
    Write-Warning "Backend port $BackendPort is already in use, so the backend window was not started."
} else {
    Start-WindowProcess -Label "Backend" -Command $backendCommand
    $startedAny = $true
}

if (Test-PortInUse -Port $FrontendPort) {
    Write-Warning "Frontend port $FrontendPort is already in use, so the frontend window was not started."
} else {
    Start-WindowProcess -Label "Frontend" -Command $frontendCommand
    $startedAny = $true
}

if (-not $startedAny) {
    Write-Warning "No new service windows were started."
    exit 1
}

if ($DryRun) {
    Write-Host "[DryRun] No processes were started."
    exit 0
}

Write-Host "Development services are launching in separate windows."
Write-Host "Frontend: http://$FrontendHost`:$FrontendPort"
Write-Host "Backend:  http://$BackendHost`:$BackendPort"
