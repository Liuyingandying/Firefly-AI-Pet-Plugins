# Firefly Voice Service - start only (no environment changes).
# Assumes setup.ps1 has been run at least once.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host "[start] ERROR: .venv not found. Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $root 'config.yaml'))) {
    Copy-Item (Join-Path $root 'config.example.yaml') (Join-Path $root 'config.yaml')
    Write-Host "[start] config.yaml created from config.example.yaml." -ForegroundColor Yellow
}

Write-Host "[start] Firefly Voice Service starting on 127.0.0.1:8300 (cold start 20-50s)..." -ForegroundColor Cyan
& $venvPython api\server.py
