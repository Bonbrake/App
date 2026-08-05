$ErrorActionPreference = "Continue"
$env:GGML_CUDA_FORCE_MMQ = "1"
$env:GGML_CUDA_F16 = "1"
$BIN = "C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
$PY = "C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
$IMG = "C:\Users\jakeb\AppData\Roaming\Hermes\composer-images\composer_2026-08-03_20-32-28-542_974af3.png"
$OUT = "C:\ComfyUI-Desktop\bench_all_vl.txt"

"" | Out-File -Encoding ascii $OUT
"ALL VISION-CAPABLE MODELS - BENCHMARK" | Out-File -Append $OUT
"Image: $IMG" | Out-File -Append $OUT

function RunModel($name, $dir, $gguf, $mmproj, $alias) {
    "" | Out-File -Append $OUT
    "===== $name =====" | Out-File -Append $OUT
    if (-not (Test-Path "$dir\$gguf")) { "SKIPPED: $gguf missing" | Out-File -Append $OUT; return }
    Stop-Process -Name llama-server -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $BIN
    $psi.Arguments = "-m `"$dir\$gguf`" --mmproj `"$dir\$mmproj`" --alias $alias -ngl 99 -fa on -kvo -c 32768 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 51120 --sleep-idle-seconds 600"
    $psi.UseShellExecute = $false
    $p = [System.Diagnostics.Process]::Start($psi)
    "Loading $name (PID $($p.Id)), waiting 14s" | Out-File -Append $OUT
    Start-Sleep -Seconds 14
    & $PY "C:\ComfyUI-Desktop\bench_vision.py" --port 51120 --model $alias --max 300 >> $OUT 2>&1
    try { $p.Kill() } catch {}
}

RunModel "qwen3-vl-4b" "C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF" "Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf" "Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf" "qwen3-vl-4b-instruct-uncensored-abliterated"
RunModel "thesby-7b" "C:\Users\jakeb\.lmstudio\models\bartowski\thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-GGUF" "thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-Q4_K_S.gguf" "mmproj-thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-f16.gguf" "thesby-qwen2.5-vl-7b"
RunModel "qwen3.5-9b-vision" "C:\Users\jakeb\.lmstudio\models\HauhauCS\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive" "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf" "mmproj-Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-BF16.gguf" "qwen3.5-9b-vision"

"" | Out-File -Append $OUT
"=== DONE - VISION MODELS ===" | Out-File -Append $OUT
Get-Content $OUT
