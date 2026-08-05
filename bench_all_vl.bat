@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
SET "GGML_CUDA_FORCE_MMQ=1"
SET "GGML_CUDA_F16=1"
SET "BIN=C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
SET "PY=C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
SET "LOG=C:\Users\jakeb\.local\bin"
SET "OUT=C:\ComfyUI-Desktop\bench_all_vl.txt"
SET "IMG=C:\Users\jakeb\AppData\Roaming\Hermes\composer-images\composer_2026-08-03_20-32-28-542_974af3.png"

taskkill /F /IM llama-server.exe 2>nul
timeout /t 2 >nul

"" > %OUT%
echo ALL VISION-CAPABLE MODELS — BENCHMARK > %OUT%
echo Image: %IMG% >> %OUT%
echo. >> %OUT%

CALL :runmodel "qwen3-vl-4b" "C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF" "Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf" "Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf" "qwen3-vl-4b-instruct-uncensored-abliterated"

CALL :runmodel "thesby-7b" "C:\Users\jakeb\.lmstudio\models\bartowski\thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-GGUF" "thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-Q4_K_S.gguf" "mmproj-thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-f16.gguf" "thesby-qwen2.5-vl-7b"

CALL :runmodel "qwen3.5-9b-vision" "C:\Users\jakeb\.lmstudio\models\HauhauCS\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive" "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf" "mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf" "qwen3.5-9b-vision"

echo. >> %OUT%
echo === DONE — VISION MODELS === >> %OUT%
type %OUT%
taskkill /F /IM llama-server.exe 2>nul
GOTO :eof

:runmodel
SET "NAME=%~1"
SET "DIR=%~2"
SET "GGUF=%~3"
SET "MMPROJ=%~4"
SET "ALIAS=%~5"
echo. >> %OUT%
echo ===== %NAME% ===== >> %OUT%
IF NOT EXIST "%DIR%\%GGUF%" (
  echo SKIPPED: %GGUF% missing >> %OUT%
  GOTO :eof
)
taskkill /F /IM llama-server.exe 2>nul
timeout /t 2 >nul
start "" /B "%BIN%" -m "%DIR%\%GGUF%" --mmproj "%DIR%\%MMPROJ%" --alias %ALIAS% -ngl 99 -fa on -kvo -c 32768 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 51120 --sleep-idle-seconds 600 > "%LOG%\%NAME%_51120.log" 2>&1
echo Loading %NAME% ... >> %OUT%
timeout /t 14 >nul
%PY% C:\ComfyUI-Desktop\bench_vision.py --port 51120 --model %ALIAS% --max 300 >> %OUT% 2>&1
GOTO :eof
