$ErrorActionPreference = "Continue"
$env:GGML_CUDA_FORCE_MMQ = "1"
$env:GGML_CUDA_F16 = "1"
$BIN = "C:\Users\jakeb\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1\llama-server.exe"
$IMG = "C:\Users\jakeb\AppData\Roaming\Hermes\composer-images\composer_2026-08-03_20-32-28-542_974af3.png"
$OUT = "C:\ComfyUI-Desktop\bench_clean.txt"
$LOGDIR = "C:\Users\jakeb\.local\bin"
"" | Out-File -Encoding ascii $OUT

function RunBench($name, $dir, $gguf, $mmproj, $alias, $task) {
    "===== $name =====" | Out-File -Append $OUT
    "task: $task" | Out-File -Append $OUT
    $args2 = "-m `"$dir\$gguf`" --alias $alias -ngl 99 -fa on -kvo -c 32768 -ctk q4_0 -ctv q4_0 -t 16 -tb 16 -b 2048 -ub 512 --reasoning off --mlock --no-warmup --host 127.0.0.1 --port 51120 --sleep-idle-seconds 600"
    if ($mmproj -ne "") { $args2 = "--mmproj `"$dir\$mmproj`" " + $args2 }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $BIN
    $psi.Arguments = $args2
    $psi.UseShellExecute = $false
    $p = [System.Diagnostics.Process]::Start($psi)
    "  launched PID $($p.Id), waiting 16s for load" | Out-File -Append $OUT
    Start-Sleep -Seconds 16
    # verify
    $ok = $false
    try { $r = Invoke-RestMethod -Uri "http://localhost:51120/v1/models" -TimeoutSec 3 -ErrorAction SilentlyContinue; if ($r.data.Count -gt 0) { $ok = $true } } catch {}
    if (-not $ok) { "  SERVER FAILED TO LOAD - skipping" | Out-File -Append $OUT; try{$p.Kill()}catch{}; return }
    # run benchmark via python
    if ($task -eq "vision") {
        $py = "C:\ComfyUI-Desktop\bench_vision.py"
        $pargs = "--port 51120 --model $alias --max 200"
    } else {
        $py = "C:\ComfyUI-Desktop\bench_text.py"
        $pargs = "--port 51120 --model $alias --max 400 --task hull"
    }
    $res = & python $py $pargs.Split(" ") 2>&1
    $res | Out-File -Append $OUT
    "" | Out-File -Append $OUT
    try { $p.Kill() } catch {}
    Start-Sleep -Seconds 2
}

# 1. qwen3-vl-4b (vision)
RunBench "qwen3-vl-4b" "C:\Users\jakeb\.lmstudio\models\mradermacher\Qwen3-VL-4B-Instruct-Uncensored-abliterated-GGUF" "Qwen3-VL-4B-Instruct-Uncensored-abliterated.Q4_K_S.gguf" "Qwen3-VL-4B-Instruct-Uncensored-abliterated.mmproj-f16.gguf" "qwen3-vl-4b-instruct-uncensored-abliterated" "vision"

# 2. thesby 7b (vision)
RunBench "thesby-7b" "C:\Users\jakeb\.lmstudio\models\bartowski\thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-GGUF" "thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-Q4_K_S.gguf" "mmproj-thesby_Qwen2.5-VL-7B-NSFW-Caption-V3-f16.gguf" "thesby_qwen2.5-vl-7b-nsfw-caption-v3" "vision"

# 3. adi-4b (text)
RunBench "adi-4b" "C:\Users\jakeb\.lmstudio\models\AdvancedDataIntelligence\adi-qwen3.5-4b-glm5.2-general-GGUF" "adi-qwen3.5-4b-glm5.2-general-q4_k_m.gguf" "" "adi-qwen3.5-4b-glm5.2-general" "text"

# 4. qwen3.5-9b (text + vision)
RunBench "qwen3.5-9b-text" "C:\Users\jakeb\.lmstudio\models\HauhauCS\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive" "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf" "" "qwen3.5-9b-uncensored-hauhaucs-aggressive" "text"

"=== DONE ===" | Out-File -Append $OUT
Get-Content $OUT
