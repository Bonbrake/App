@echo off
SETLOCAL
SET "GGML_CUDA_FORCE_MMQ=1"
SET "GGML_CUDA_F16=1"
SET "BIN=C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
SET "DIRV=C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF"
SET "LOG=C:\Users\jakeb\.local\bin"
IF NOT EXIST "%LOG%" mkdir "%LOG%"
taskkill /F /IM llama-server.exe 2>nul
timeout /t 2 >nul
start "" /B "%BIN%" -m "%DIRV%\Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf" --mmproj "%DIRV%\Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf" --alias qwen3-vl-4b-instruct-uncensored-abliterated -ngl 99 -fa on -kvo -c 32768 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 5119 --sleep-idle-seconds 180 > "%LOG%\vl_5119.log" 2>&1
echo Launched detached on :5119
