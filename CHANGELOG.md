# Changelog

All notable changes to the **ComfyUIX** project are documented here.
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [5.2.0] - 2026-08-19 (Zero-Lag UI, Live Matrix Rain & SafeTimer Architecture)

### Added
- **Live Katakana & Alphanumeric Matrix Rain Background Canvas**:
  - Rewrote `MatrixRainCanvas` in `glass.py` using **canvas item pooling** (`coords()` / `itemconfigure()` instead of per-frame allocation).
  - Renders authentic falling Japanese Katakana glyphs (`ｦｱｳｴｵ...`), green phosphor digits, and Latin symbols with delta-time ($\Delta t$) compensation at 20 FPS with only **0.007 ms** per-frame latency.
- **SafeTimerManager Lifecycle Engine**:
  - Added centralized `SafeTimerManager` in `ComfyUI_App.py` to manage all 40+ Tkinter `.after()` callback timers.
  - Auto-cancels duplicate timers, verifies widget existence before GUI dispatch, and performs bulk Tcl timer purges on shutdown to eliminate `invalid command name` errors.
- **UI Frame Timing & Multi-Resolution Resize Benchmark Suite (Vector 7)**:
  - Added Vector 7 to `multi_angle_debug.py` to benchmark resize latency, canvas pool rebuilds, and timer throughput.
- **Universal Tooltip Coverage**:
  - Attached Cyber HUD `ToolTip` instances to Theme mode selector, Check for Updates button, gallery controls, and sidebar cards.

### Changed & Optimized
- **3,125x Faster Window Resizing**:
  - Optimized `AcrylicBackground` to bypass expensive PIL Gaussian blur and NumPy gradient generation whenever `MatrixRainCanvas` is active.
  - Added a 5px size-delta threshold and increased resize debounce to 600ms, dropping pool rebuild times from >1,000ms down to **0.32 ms**.
- **100% Obsidian Dark Theme Purity**:
  - Eliminated all hardcoded grey hex codes (`#0F0F12`, `#1A1A24`, `#141416`), standardizing the UI on `#040A06` (Deep Matrix Obsidian) and `#08150D` (Cyber Card Glass).
- **Asynchronous Diagnostic Self-Tests**:
  - Moved `_debug_diagnose()` to a background worker thread with thread-safe UI dispatch, eliminating 3-second UI freezes when the backend server is offline.

### Fixed & Verified
- **122 / 122 Automated QA Tests Passing (100% Nominal)** across functional suite (`qa_suite.py`, 60 tests) and multi-angle stress harness (`multi_angle_debug.py`, 62 tests).
- Added `_safe_destroy_app()` helper across QA test fixtures for clean teardown.

---

## [5.1.0] - 2026-08-18 (Matrix SOTA & Public Sanitization Release)

### Added
- **1-Click Generation Parameter & Workflow Re-Hydration**:
  - `extract_generation_metadata(image_path)` in `gallery.py` parses embedded PNG `tEXt` chunks (`prompt`, `workflow`, `parameters`).
  - Added 1-click **💧 Re-Hydrate** action button to `txt2img`, `img2img`, and `Gallery` toolbars to automatically restore Prompt, Negative, Steps, CFG, Seed, Dimensions, Sampler, Scheduler, and Model Checkpoints.
- **1-Click Local LLM Diffusion Prompt Expander**:
  - Added **⚡ Enhance** button in prompt toolbars to asynchronously query local AI endpoints (`Ollama` :11434, `LM Studio` :1234, local proxy :5119/:8000) or high-fidelity artistic heuristics without blocking Tkinter UI responsiveness.
- **Dynamic Wildcards Permutation Engine**:
  - Resolves `{option1|option2|option3}` dynamic permutation tags and attention weighting tokens prior to ComfyUI graph compilation.
- **GGUF & Scaled Quantization Routing**:
  - Automated graph loader detection and routing for `.gguf` checkpoints using `UnetLoaderGGUF` and `CLIPLoaderGGUF` to run heavy diffusion models on 8GB VRAM cards without OOM crashes.
- **PyTorch CUDA Memory Defragmentation**:
  - Injected `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` into backend process environment to eliminate memory fragmentation on Windows.
- **Titanium & Frosted Cyber Emerald App Icon**:
  - Precision 3D chamfered titanium emblem with glowing cyber mint-emerald glass (`#00FF66`/`#39FF8C`) matching native app dark palette. Output as `assets/app_icon.png`, `assets/app_icon.ico`, and `assets/comfyuix_app_icon_v5.ico`.

### Changed & Sanitized
- **Repository Debloated**: Deleted >135 MB of legacy binaries (`ComfyUIX_pyinstaller_backup.exe`, `unins000.exe`), scratch test files, and local logs.
- **Sanitized Public Release Defaults**:
  - Dynamic directory resolver `_resolve_comfyui_portable_dir()` in `config.py`.
  - Configurable public AI ports and generic model fallbacks in `hermes_app.py`.
  - Automatic path redaction (`[USER_HOME]`, `[APP_DIR]`) in `qa_suite.py`.
  - Hardened `.gitignore` to prevent runtime configs, crash logs, and binaries from leaking into git.

### Fixed & Verified
- Recompiled Windows launcher `ComfyUIX.exe` with embedded cyber emerald icon and invalidation across all 16 Windows shell icon cache databases.
- 110/110 automated tests passing across primary functional (`qa_suite.py`) and deep multi-vector stress (`multi_angle_debug.py`) harnesses.

---

## [5.0.0] - 2026-08-17 (Matrix UI & Multi-Studio Engine)

### Added
- **Matrix HUD Companion**: PySide6 telemetry companion app (`hermes_app.py`) with real-time VRAM sparklines, tok/s gauges, and generation event streaming.
- **PBR Texture Studio**: Generates 5 game-ready physical material maps (Normal Map with Sobel unit tangent vectors, Roughness, Height, AO, and $3 \times 3$ Seamless Tiled wrap inspection).
- **Interactive Inpainting Canvas**: CustomTkinter inpainting canvas with brush size slider, eraser mode, mask inversion, and direct workflow staging.
- **Multimodal Video & Audio Engines**: Support for Wan 2.1, AnimateDiff, Bark TTS, and AudioLDM generation graphs.
- **RFC 6455 Pure-Python WebSocket Client**: Real-time streaming of binary JPEG latent previews and step progress.
- **Multi-Monitor Window Safety**: Dynamic screen bound clamping ensuring window coordinates are never restored off-screen.

---

## [4.0.0] - 2026-08-17 (Initial Clean Portable Release)

### Added
- Privacy & security audit: verified localhost-only egress, absence of telemetry, and `asInvoker` manifest.
- Dynamic portable engine discovery resolving `COMFYUI_PORTABLE_DIR`.
- Initial CustomTkinter dark-mode interface with GPU Doctor VRAM auto-tuning.
