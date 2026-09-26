param(
    [switch]$SkipWorker,
    [string]$RvcRoot = "",
    [string]$Python = "",
    [string]$Model = "",
    [string]$Index = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Build = Join-Path $Root "build"
$Dist = Join-Path $Root "dist"
$ValidatorBuild = Join-Path $Build "v3vs"
$Validator = Join-Path $ValidatorBuild "bin\Release\validator.exe"

& (Join-Path $PSScriptRoot "build.ps1")

cmake -S $Root -B $Build -G "Visual Studio 17 2022" -A x64 -DRVC_BUILD_SMOKE_TEST=ON
if ($LASTEXITCODE -ne 0) {
    throw "CMake configuration failed with exit code $LASTEXITCODE"
}
cmake --build $Build --config Release --target rvc-vst2-smoke rvc-worker-smoke --parallel
if ($LASTEXITCODE -ne 0) {
    throw "Smoke-test build failed with exit code $LASTEXITCODE"
}

& (Join-Path $Build "Release\rvc-vst2-smoke.exe") (Join-Path $Dist "RVC Realtime.dll")
if ($LASTEXITCODE -ne 0) {
    throw "VST2 smoke test failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $Validator)) {
    $Sdk = Join-Path $Root "third_party\iPlug2\Dependencies\IPlug\VST3_SDK"
    # Several validator source names exceed legacy MSBuild path limits when the
    # repository is cloned deeply. A stable TEMP junction keeps compiler paths short.
    $ValidatorSdk = Join-Path ([System.IO.Path]::GetTempPath()) "RVCRealtimeVST-vst3sdk-58f8da7"
    if (-not (Test-Path -LiteralPath $ValidatorSdk)) {
        New-Item -ItemType Junction -Path $ValidatorSdk -Target $Sdk | Out-Null
    }
    if (-not (Test-Path -LiteralPath (Join-Path $ValidatorSdk "CMakeLists.txt") -PathType Leaf)) {
        throw "Short VST3 SDK path is invalid: $ValidatorSdk"
    }
    cmake -S $ValidatorSdk -B $ValidatorBuild -G "Visual Studio 17 2022" -A x64 `
        -DSMTG_ENABLE_VST3_PLUGIN_EXAMPLES=OFF `
        -DSMTG_ENABLE_VST3_HOSTING_EXAMPLES=ON `
        -DSMTG_ENABLE_VSTGUI_SUPPORT=OFF
    if ($LASTEXITCODE -ne 0) {
        throw "VST3 validator configuration failed with exit code $LASTEXITCODE"
    }
    cmake --build $ValidatorBuild --config Release --target validator --parallel
    if ($LASTEXITCODE -ne 0) {
        throw "VST3 validator build failed with exit code $LASTEXITCODE"
    }
}

& $Validator (Join-Path $Dist "RVCRealtime.vst3")
if ($LASTEXITCODE -ne 0) {
    throw "VST3 validator failed with exit code $LASTEXITCODE"
}

if (-not $SkipWorker) {
    if ([string]::IsNullOrWhiteSpace($RvcRoot) -or [string]::IsNullOrWhiteSpace($Model)) {
        throw "Specify -RvcRoot and -Model for the CUDA worker test, or use -SkipWorker."
    }
    if ([string]::IsNullOrWhiteSpace($Python)) {
        $Python = Join-Path $RvcRoot "runtime\python.exe"
    }
    foreach ($RequiredPath in @($RvcRoot, $Python, $Model)) {
        if (-not (Test-Path -LiteralPath $RequiredPath)) {
            throw "Required worker test path does not exist: $RequiredPath"
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($Index) -and -not (Test-Path -LiteralPath $Index -PathType Leaf)) {
        throw "Index path does not exist: $Index"
    }
    $WorkerArgs = @($RvcRoot, $Python, $Model)
    if (-not [string]::IsNullOrWhiteSpace($Index)) {
        $WorkerArgs += $Index
    }
    & (Join-Path $Build "Release\rvc-worker-smoke.exe") @WorkerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Worker smoke test failed with exit code $LASTEXITCODE"
    }
}

if ($SkipWorker) {
    Write-Host "VST2 and VST3 format tests passed; CUDA worker test skipped."
} else {
    Write-Host "All VST2, VST3, and CUDA worker tests passed."
}
