@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
SET "GGML_CUDA_FORCE_MMQ=1"
SET "GGML_CUDA_F16=1"
SET "BIN=C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
SET "DIR9=C:\Users\jakeb\.lmstudio\models\HauhauCS\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive"
SET "PY=C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
SET "LOG=C:\Users\jakeb\.local\bin"
SET "OUT=C:\ComfyUI-Desktop\bench_9b_text.txt"

taskkill /F /IM llama-server.exe 2>nul
timeout /t 2 >nul

REM Start 9B on 51120
start "" /B "%BIN%" -m "%DIR9%\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf" --mmproj "%DIR9%\mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf" --alias qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf -ngl 99 -fa on -kvo -c 65536 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 51120 --sleep-idle-seconds 600 > "%LOG%\9b_51120.log" 2>&1

"" > %OUT%
echo 9B TEXT BENCHMARK > %OUT%
echo Started, waiting for load... >> %OUT%
timeout /t 12 >nul

echo. >> %OUT%
echo === TEXT/CODE (convex hull) === >> %OUT%
%PY% C:\ComfyUI-Desktop\bench_text.py --port 51120 --model qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf --max 500 >> %OUT% 2>&1

echo. >> %OUT%
echo === TEXT/CODE (quicksort) === >> %OUT%
%PY% C:\ComfyUI-Desktop\bench_text.py --port 51120 --model qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf --max 400 --task sort >> %OUT% 2>&1

echo. >> %OUT%
echo === DONE === >> %OUT%
type %OUT%
taskkill /F /IM llama-server.exe 2>nul
