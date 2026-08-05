@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
SET "GGML_CUDA_FORCE_MMQ=1"
SET "GGML_CUDA_F16=1"
SET "BIN=C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
SET "DIRV=C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF"
SET "PY=C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
SET "OUT=C:\ComfyUI-Desktop\benchmark_results.txt"

echo ============================================ > "%OUT%"
echo  BENCHMARK RUN: %DATE% %TIME% >> "%OUT%"
echo ============================================ >> "%OUT%"

REM --- Kill any prior instance ---
taskkill /F /IM llama-server.exe 2>nul
timeout /t 2 >nul

REM --- Start server (detached so it lives during this script) ---
start "" "%BIN%" -m "%DIRV%\Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf" --mmproj "%DIRV%\Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf" --alias qwen3-vl-4b-instruct-uncensored-abliterated -ngl 99 -fa on -kvo -c 32768 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 5119 --sleep-idle-seconds 600 >> "%OUT%" 2>&1

REM --- Wait for server ready ---
set READY=0
for /L %%i in (1,1,30) do (
  curl -s http://localhost:5119/v1/models >nul 2>&1
  if !ERRORLEVEL!==0 (
    set READY=1
    echo [server ready after ~%%i sec] >> "%OUT%"
    goto :RUN
  )
  timeout /t 1 >nul
)
echo [SERVER FAILED TO START] >> "%OUT%"
type "%OUT%"
exit /b 1

:RUN
echo. >> "%OUT%"
echo ===== VISION BENCHMARK ===== >> "%OUT%"
"%PY%" "C:\ComfyUI-Desktop\bench_vision.py" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ===== TEXT BENCHMARK ===== >> "%OUT%"
"%PY%" "C:\ComfyUI-Desktop\bench_text.py" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ===== WEB BENCHMARK ===== >> "%OUT%"
"%PY%" "C:\ComfyUI-Desktop\bench_web.py" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ===== DONE ===== >> "%OUT%"

REM --- Cleanup ---
taskkill /F /IM llama-server.exe 2>nul
type "%OUT%"
