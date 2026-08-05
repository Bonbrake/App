$ErrorActionPreference = "Continue"
$env:GGML_CUDA_FORCE_MMQ = "1"
$env:GGML_CUDA_F16 = "1"
$BIN = "C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
$DIR9 = "C:\Users\jakeb\.lmstudio\models\HauhauCS\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive"
$PY = "C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
$OUT = "C:\ComfyUI-Desktop\bench_9b_text.txt"

"" | Out-File -Encoding ascii $OUT
"9B TEXT BENCHMARK (Qwen3.5-9B-Uncensored)" | Out-File -Append $OUT

# kill stale
Stop-Process -Name llama-server -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $BIN
$psi.Arguments = "-m `"$DIR9\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`" --mmproj `"$DIR9\mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf`" --alias qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf -ngl 99 -fa on -kvo -c 65536 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 51120 --sleep-idle-seconds 600"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$p = [System.Diagnostics.Process]::Start($psi)
"Launched 9B PID $($p.Id) on :51120, waiting 20s" | Out-File -Append $OUT
Start-Sleep -Seconds 20
# dump server log if it exists
$logpath = "C:\ComfyUI-Desktop\9b_server.log"
try { $p.StandardOutput.ReadToEnd() | Out-File -Append $logpath; $p.StandardError.ReadToEnd() | Out-File -Append $logpath } catch {}

"" | Out-File -Append $OUT
"=== TEXT/CODE: convex hull ===" | Out-File -Append $OUT
& $PY "C:\ComfyUI-Desktop\bench_text.py" --port 51120 --model qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf --max 500 >> $OUT 2>&1

"" | Out-File -Append $OUT
"=== TEXT/CODE: quicksort ===" | Out-File -Append $OUT
& $PY "C:\ComfyUI-Desktop\bench_text.py" --port 51120 --model qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf --max 400 --task sort >> $OUT 2>&1

"" | Out-File -Append $OUT
"=== DONE ===" | Out-File -Append $OUT
try { $p.Kill() } catch {}
Get-Content $OUT
