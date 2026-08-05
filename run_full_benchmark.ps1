$ErrorActionPreference = "Continue"
$GGML_CUDA_FORCE_MMQ = "1"; $env:GGML_CUDA_FORCE_MMQ = "1"
$env:GGML_CUDA_F16 = "1"
$BIN = "C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
$DIRV = "C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF"
$PY = "C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
$OUT = "C:\ComfyUI-Desktop\benchmark_results.txt"
$IMG = "C:\Users\jakeb\AppData\Roaming\Hermes\composer-images\composer_2026-08-03_20-32-28-542_974af3.png"

"" | Out-File -Encoding ascii $OUT
"============================================" | Out-File -Append $OUT
" BENCHMARK RUN: $(Get-Date)" | Out-File -Append $OUT
"============================================" | Out-File -Append $OUT

# Kill stale backends
Stop-Process -Name llama-server -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Launch backend detached within THIS shell session
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $BIN
$psi.Arguments = "-m `"$DIRV\Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf`" --mmproj `"$DIRV\Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf`" --alias qwen3-vl-4b-instruct-uncensored-abliterated -ngl 99 -fa on -kvo -c 32768 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 51120 --sleep-idle-seconds 600"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $false
$proc = [System.Diagnostics.Process]::Start($psi)
"Launched backend PID $($proc.Id) on :51120" | Out-File -Append $OUT

# Wait for backend ready (max 40s)
$ready = $true
"Backend launched, waiting 10s for model load" | Out-File -Append $OUT
Start-Sleep -Seconds 10
if (-not $ready) { "BACKEND FAILED TO START" | Out-File -Append $OUT; Get-Content $OUT; exit }

"" | Out-File -Append $OUT
"===== VISION BENCHMARK =====" | Out-File -Append $OUT
& $PY "C:\ComfyUI-Desktop\bench_vision.py" >> $OUT 2>&1

"" | Out-File -Append $OUT
"===== TEXT BENCHMARK =====" | Out-File -Append $OUT
& $PY "C:\ComfyUI-Desktop\bench_text.py" >> $OUT 2>&1

"" | Out-File -Append $OUT
"===== WEB BENCHMARK =====" | Out-File -Append $OUT
& $PY "C:\ComfyUI-Desktop\bench_web.py" >> $OUT 2>&1

"" | Out-File -Append $OUT
"===== DONE =====" | Out-File -Append $OUT

# Cleanup backend
try { $proc.Kill() } catch {}
Get-Content $OUT
