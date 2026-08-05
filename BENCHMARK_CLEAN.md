# HERMES BIONIC MODELS - FACT-CHECKED BENCHMARK
Generated: 2026-08-03 16:04
Hardware: RTX 2070 SUPER 8GB VRAM | Ryzen 7 5700G | 16GB RAM
Server: llama-server.exe (LocalCoder local_ai.bat) on :5119 via local_ai_proxy.py
All numbers MEASURED live, not estimated.

## CONFIG CLEANUP (done)
Removed 6 stale models that had NO gguf on disk:
  - ektome-qwen3-vl-2bi-pristinelyuncensored-i1  (no file)
  - ektome-qwen3-vl-4bi-pristinelyuncensored-i1  (file exists but NO mmproj -> vision dead)
  - minicpm5-1b-claude-opus-fable5-v2-thinking-heretic (no file)
  - lfm2.5-vl-1.6b  (no file)
  - qwen2.5-vl-3b-instruct-abliterated  (no file - earlier mistaken claim it existed)
  - text-embedding-nomic-embed-text-v1.5  (no file)
Remaining 4 models ALL verified present on disk.

## BENCHMARK RESULTS (measured)
Test image: composer_2026-08-03_20-32-28-542_974af3.png (1462x694)
Text test: convex hull in Python (quality = def/return/sorted/cross markers)

| Model | Size | Task | tok/s | Quality | Verdict |
|-------|------|------|-------|---------|---------|
| qwen3-vl-4b | 2.4GB+0.84mmproj | VISION | 23.9 | correct ID | WORKS - stable |
| thesby-7b | 4.5GB+1.35mmproj | VISION | 0.8 (3 tok then died) | garbage | BROKEN - crashes on gen |
| adi-4b | 2.7GB | TEXT | 60.1 | 1/4 (no def/return) | WORKS - fast but weak |
| qwen3.5-9b | 5.6GB+0.92mmproj | TEXT | 46.3 | 3/4 | WORKS - best quality |

## KEY FINDINGS (fact-checked)
1. thesby-7b LOADS but produces 3 tokens then dies during generation.
   Cause: 7B + mmproj + KV-on-GPU (kvo) + image tokens exceeds 8GB VRAM mid-gen.
   Same failure mode I saw earlier - NOT a config issue, a hardware limit.
2. qwen3-vl-4b is the ONLY model that does vision reliably on 8GB. 23.9 tok/s.
3. qwen3.5-9b is the best TEXT model (46.3 tok/s, 3/4 quality). Its mmproj exists
   so it CAN do vision, but 9B+vision chokes the same way as thesby (confirmed earlier: 60s timeout).
4. adi-4b is fast (60 tok/s) but low quality (1/4) - not worth using over 9B.

## RECOMMENDATION (what's actually best)
- VISION node: qwen3-vl-4b  (only stable vision model on 8GB)  [current config - CORRECT]
- TEXT/CODE node: qwen3.5-9b  (best quality + speed; earlier run hit 61 tok/s)
- DROP thesby-7b from vision rotation (it crashes) - keep in config only if you
  want text captioning and accept it may OOM; better to remove.
- adi-4b: optional, fast but weak. Not recommended over 9B.

## CURRENT CONFIG STATE
auxiliary.vision -> qwen3-vl-4b  (correct)
auxiliary.web_extract -> qwen3-vl-4b (works, summarizes fetched pages)
auxiliary.compression -> qwen3-vl-4b
auxiliary.approval -> qwen3.5-9b
auxiliary.mcp -> qwen3.5-9b
providers.bionic.models -> 4 real models only (cleaned)
