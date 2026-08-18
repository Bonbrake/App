@echo off
SETLOCAL
SET "GGML_CUDA_FORCE_MMQ=1"
SET "GGML_CUDA_F16=1"
SET "BIN=C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
SET "DIRV=C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF"
SET "LOG=C:\Users\jakeb\.local\bin"
SET "PORT=5120"
IF NOT EXIST "%LOG%" mkdir "%LOG%"

echo ============================================================
echo  Local AI Server (Qwen3-VL-4B)  -  port %PORT%
echo ============================================================

:: Kill any stale binder on the port
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1
timeout /t 2 >nul

:launch
:: QoL: launch detached via PowerShell (reliable, survives parent exit)
powershell.exe -NoProfile -Command "Start-Process -FilePath '%BIN%' -ArgumentList '-m','%DIRV%\Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf','--mmproj','%DIRV%\Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf','--alias','qwen3-vl-4b-instruct-uncensored-abliterated','-ngl','99','-fa','on','-kvo','-c','32768','-ctk','q4_0','-ctv','q4_0','-t','16','-tb','16','-b','2048','-ub','512','--reasoning','off','--mlock','--no-warmup','--host','127.0.0.1','--port','%PORT%','--sleep-idle-seconds','180' -WindowStyle Minimized -RedirectStandardOutput '%LOG%\vl_%PORT%.log' -RedirectStandardError '%LOG%\vl_%PORT%_err.log'"
echo [%time%] Launched on :%PORT% (watchdog active)

:: QoL: self-healing heartbeat watchdog (restarts if server dies)
:watchdog
timeout /t 30 >nul
curl -s -m 4 http://127.0.0.1:%PORT%/v1/models >nul 2>&1
if errorlevel 1 (
  echo [%time%] SERVER DOWN - restarting...
  for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1
  taskkill /F /IM llama-server.exe >nul 2>&1
  timeout /t 2 >nul
  goto :launch
)
goto :watchdog
