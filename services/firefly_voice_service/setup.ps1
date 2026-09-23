# Firefly Voice Service - one-shot environment setup (Windows).
# Creates a service-private venv, installs dependencies, prepares config,
# and checks model / ffmpeg prerequisites. Does NOT download models
# (license boundary, see models/README.md), does NOT touch system PATH.

param(
    # Torch build to install: cpu (default) | nvidia (CUDA 12.1 wheels) | amd (torch-directml)
    [ValidateSet('cpu', 'nvidia', 'amd')]
    [string]$Gpu = 'cpu',
    # Python executable to build the venv from (must be 3.10)
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Info($m)  { Write-Host "[setup] $m" -ForegroundColor Cyan }
function Warn($m)  { Write-Host "[setup] WARNING: $m" -ForegroundColor Yellow }
function Ok($m)    { Write-Host "[setup] OK: $m" -ForegroundColor Green }

# --- 1. Check Python -------------------------------------------------------
try {
    $ver = & $Python -c "import sys; print('%d.%d' % sys.version_info[:2])"
} catch {
    Write-Host "[setup] ERROR: python not found. Install Python 3.10 first." -ForegroundColor Red
    exit 1
}
if ($ver -notmatch '^3\.10') {
    Warn "Python $ver detected; this service is verified on 3.10 only (RVC engine snapshot). Continue at your own risk."
} else {
    Ok "Python $ver"
}

# --- 2. Create venv --------------------------------------------------------
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    Info "Existing .venv found, reusing it."
} else {
    Info "Creating .venv (service-private; never share with the Firefly host env)..."
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host "[setup] ERROR: venv creation failed" -ForegroundColor Red; exit 1 }
}

# --- 3. Install torch variant + requirements --------------------------------
Info "Installing torch ($Gpu build). This may take several minutes..."
switch ($Gpu) {
    'nvidia' {
        & $venvPython -m pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
    }
    'amd' {
        # DirectML path for AMD GPUs on Windows (fp32). torch-directml pins its
        # own compatible torch version; see https://learn.microsoft.com/en-us/windows/ai/directml/gpu-torch-directml
        & $venvPython -m pip install torch-directml
    }
    default {
        & $venvPython -m pip install torch==2.5.1 torchaudio==2.5.1
    }
}
if ($LASTEXITCODE -ne 0) { Write-Host "[setup] ERROR: torch install failed" -ForegroundColor Red; exit 1 }

Info "Installing requirements.txt..."
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "[setup] ERROR: requirements install failed" -ForegroundColor Red; exit 1 }
Ok "Dependencies installed."

# --- 4. Prepare config ------------------------------------------------------
if (-not (Test-Path (Join-Path $root 'config.yaml'))) {
    Copy-Item (Join-Path $root 'config.example.yaml') (Join-Path $root 'config.yaml')
    Ok "config.yaml created from config.example.yaml."
} else {
    Info "config.yaml already exists, left untouched."
}

# --- 5. Check models --------------------------------------------------------
$missing = @()
foreach ($f in @('models\firefly\firefly-chinese.pth', 'models\firefly\firefly-chinese_v2.index', 'models\rmvpe.pt', 'vendor\Retrieval-based-Voice-Conversion-WebUI-main\assets\hubert_base\pytorch_model.bin')) {
    if (-not (Test-Path (Join-Path $root $f))) { $missing += $f }
}
if ($missing.Count -gt 0) {
    Warn "Missing model files:"
    $missing | ForEach-Object { Warn "  $_" }
    Warn "Download them per models/README.md (weights are NOT in the git repo)."
} else {
    Ok "All model files present."
}

# --- 6. Check ffmpeg ---------------------------------------------------------
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($null -eq $ffmpeg) {
    Warn "ffmpeg not found on PATH. The RVC engine needs it for non-wav audio decoding."
    Warn "Install it (e.g. 'winget install Gyan.FFmpeg') and reopen the terminal; see README Troubleshooting."
} else {
    Ok "ffmpeg found: $($ffmpeg.Source)"
}

# --- 7. Next steps -----------------------------------------------------------
Write-Host ""
Info "Setup complete. Next steps:"
Write-Host "  1. Place models per models\README.md (if warned above)"
Write-Host "  2. Start the service:  powershell -ExecutionPolicy Bypass -File start.ps1"
Write-Host "  3. Wait 20-50s for model load, then check  http://127.0.0.1:8300/health"
