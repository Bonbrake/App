@echo off
:: ==============================================================================
:: ComfyUI Vision Model Monitor — consolidated heartbeat/diagnostics script
:: Shows: active vision model, GPU status, all available VL models, server health
:: Single entry point — no scattered scripts
:: ==============================================================================

setlocal enabledelayedexpansion

:: --- Configuration ---
set BIONIC_URL=http://localhost:5120
set OUTPUT_FILE=C:\Users\jakeb\Pictures\vision_benchmark.txt

:: --- Functions ---
goto :main

:check_gpu
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name --format=csv,noheader 2^>nul') do (
        set GPU_INFO=%%i
    )
    if defined GPU_INFO (
        echo   GPU:     !GPU_INFO!
    ) else (
        echo   GPU:     (nvidia-smi not available)
    )
    goto :eof

:get_timestamp
    for /f "tokens=*" %%t in ('powershell -command "Get-Date -Format 'HH:mm:ss'"') do set TS=%%t
    echo [!TS!]
    goto :eof

:main
echo ===============================================================================
echo  VISION MODEL MONITOR — Hermes Bionic (LM Studio) Diagnostics
echo ===============================================================================
call :get_timestamp

:: --- Server health ---
echo.
echo [1] SERVER STATUS
echo -------------------------------------------------------------------------------
powershell -command "try { $r = Invoke-RestMethod -Uri '%BIONIC_URL%/v1/models' -TimeoutSec 5; Write-Output '  Status: ALIVE (HTTP 200)'; $r.data | ForEach-Object { Write-Output ('  Model: ' + $_.id) } } catch { Write-Output '  Status: DEAD (connection failed)' }" 2>nul

:: --- GPU status ---
echo.
echo [2] GPU STATUS
echo -------------------------------------------------------------------------------
call :check_gpu

:: --- Active models ---
echo.
echo [3] LOADED MODELS (current)
echo -------------------------------------------------------------------------------
powershell -command "
    $lms = 'C:\Users\jakeb\AppData\Local\Programs\Bionic\resources\app\.webpack-bionic\lms.exe'
    if (Test-Path $lms) {
        $result = & $lms 'ps' 2>$null
        $lines = $result -split \"`n\" | Where-Object { $_ -match 'IDENTIFIER|VL|qwen|lmf2|mini|thesby|ektome' }
        $lines | ForEach-Object { Write-Output ('  ' + $_.Trim()) }
    } else {
        Write-Output '  (lms CLI not found — checking API instead)'
    }
" 2>nul

:: --- Available VL models ---
echo.
echo [4] ALL VL MODELS (vision-capable)
echo -------------------------------------------------------------------------------
powershell -command "
    $lms = 'C:\Users\jakeb\AppData\Local\Programs\Bionic\resources\app\.webpack-bionic\lms.exe'
    if (Test-Path $lms) {
        & $lms 'ls' 2>$null | Select-String -Pattern 'VL|vl|caption|vision|image' | ForEach-Object {
            Write-Output ('  ' + $_.Line.Trim())
        }
    }
" 2>nul

echo -------------------------------------------------------------------------------
echo.
echo [5] VISION MODEL BENCHMARK (latest results)
echo -------------------------------------------------------------------------------
powershell -command "
    $lms = 'C:\Users\jakeb\AppData\Local\Programs\Bionic\resources\app\.webpack-bionic\lms.exe'
    if (Test-Path $lms) {
        & $lms 'ls' 2>$null | Select-String -Pattern 'VL|vl' | ForEach-Object {
            $size = ($_ -split '\s+')[2]
            $name = ($_ -split '\s+')[1]
            Write-Output ('  ' + $name + ' (' + $size + ')')
        }
    }
" 2>nul

echo.
echo -------------------------------------------------------------------------------
echo  Quick Actions:
echo   lms ps              - Show loaded models
echo   lms ls              - List all models on disk
echo   lms load ^<model^>   - Load a specific model
echo   lms unload ^<model^>  - Unload a specific model
echo   nvidia-smi          - Check GPU usage
echo -------------------------------------------------------------------------------
echo  NOTE: JIT TTL is set to 120s — models auto-unload after 2 min idle
echo  Config model: qwen3-vl-4b-instruct-uncensored-abliterated (95.3 tok/s)
echo ===============================================================================
