# ComfyUIX Matrix Edition v5.0 — Master Specification, Architecture & Deep Gap Roadmap

[![Version](https://img.shields.io/badge/version-5.0.0--Matrix-00FF66.svg)](https://github.com/Bonbrake/ComfyUIX)
[![QA Status](https://img.shields.io/badge/QA%20Tests-146%2F146%20PASSED-00FF66.svg)](https://github.com/Bonbrake/ComfyUIX)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue.svg)](https://github.com/Bonbrake/ComfyUIX)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 1. Executive Summary & Architecture

**ComfyUIX Matrix Edition v5.0** is a standalone, high-performance desktop interface and local AI orchestration suite for generative image, video, audio, and PBR 3D material workflows. Designed as a zero-hassle application for Windows, it bridges complex node-based diffusion graphs with an ultra-sleek, cyberpunk Matrix dark glass user experience.

```
+-----------------------------------------------------------------------------------+
|                           ComfyUIX Matrix Edition v5.0                             |
+-----------------------------------------------------------------------------------+
|  [ Desktop GUI (CustomTkinter) ]  <--->  [ Native RFC 6455 WebSocket Client ]      |
|  * Text to Image (LoRA + VAE)            * Real-time JPEG Latent Previewer         |
|  * Image to Image (Inpaint Canvas)       * Step Progress & Node State Tracker      |
|  * PBR Texture Studio (Sobel + Wrap)     * Pure Python (Zero 3rd-Party Libs)      |
|  * AI Video & Audio Engines                                                       |
|                                                                                   |
|  [ Matrix AI HUD Companion ]      <--->  [ Multi-GPU Doctor & Auto-Tuner ]        |
|  * Local LLM Copilot (PySide6)           * VRAM Telemetry & Smart Medvram Tuning   |
|  * Synchronized IPC & System Tray        * Windows Job Object Tree Reclamation    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Master 12-Dimension Gap Analysis ("Where Most People Don't Look")

This exhaustive matrix identifies non-obvious, high-impact architectural and creative gaps across the generative AI desktop ecosystem:

| # | Dimension | Current State | The Deep Gap | Recommended Architecture Solution |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Adaptive Graph Compilation** | Fixed JSON DAG dictionary | SOTA models (FLUX.1, SD 3.5, Wan 2.1) require completely different node topologies (`DualCLIPLoader`, `EmptySD3LatentImage`, 16-channel latents). | Dynamic Graph Builder querying `/object_info` at startup with architecture auto-detection. |
| **2** | **Modern Quantization** | Full precision FP16 safetensors | 8GB VRAM cards (RTX 2070/3060/4060) crash with CUDA OOM on FLUX or Wan 2.1. | Native GGUF (`UnetLoaderGGUF`) & FP8/NF4 (`bitsandbytes`) integration with precision selectors. |
| **3** | **Multi-LoRA Stacking** | Single LoRA dropdown | Professional creators stack 3–5 LoRAs simultaneously (Character + Style + Clothing + Detailer). | Dynamic LoRA Stacker interface with independent UNet/CLIP weights and auto-trigger insertion. |
| **4** | **Parameter Re-Hydration** | Gallery displays thumbnails only | ComfyUI embeds full generation DAGs in PNG `tEXt` chunks; ComfyUIX doesn't extract them. | 1-Click PNG metadata reader restoring full Prompt, Seed, Model, Steps, CFG, and Samplers to UI. |
| **5** | **LLM Prompt Expansion** | HUD runs in isolated window | Users must manually copy-paste prompt enhancements between windows. | 1-Click "⚡ Enhance Prompt" button querying local LLM (Ollama/LM Studio/Proxy) directly in GUI. |
| **6** | **ControlNet Guidance** | Unconditional generation | No native OpenPose, DepthAnything V2, Canny, or Tile guidance controls in the GUI. | Multi-ControlNet Studio with integrated preprocessors and strength sliders. |
| **7** | **Semantic Auto-Masking** | Manual brush painting only | Inpainting complex clothing/objects by hand is tedious and imprecise. | Segment Anything 2 (SAM 2) text-prompt auto-segmentation (`"sunglasses"`, `"red jacket"`). |
| **8** | **Automated Face Detailer** | Manual crop-and-inpaint | Far portraits generate distorted eyes/hands without dedicated face restoration passes. | Automated YOLOv8-face / SEGS bounding-box detection, hires inpaint, and alpha blendback. |
| **9** | **Hyperparameter Grid (XY)** | Single generation sweeps | No way to compare CFG vs Steps or Sampler vs Scheduler across a 2D matrix. | XY Plot & Grid Search Generator producing side-by-side comparative matrices. |
| **10** | **Temporal Video Synthesis** | Basic frame/fps sliders | Video outputs suffer from low framerates (16 FPS) and temporal flickering. | Integrated RIFE/FILM frame interpolation (to 60 FPS) and AnimateDiff Camera Motion LoRAs. |
| **11** | **Memory Spillover & Defrag** | Physical VRAM monitoring | Windows silently pages VRAM overflow into System RAM, causing a 10×–20× slowdown. | PyTorch CUDA `expandable_segments` defrag + Shared GPU Memory allocation detection alert. |
| **12** | **Safe Mode & Node Isolation** | Standard subprocess launch | Broken third-party custom nodes prevent ComfyUI from booting with cryptic import errors. | Safe Mode boot switch (`--disable-all-custom-nodes`) and malicious pickle `.pt`/`.ckpt` scanner. |

---

## 3. Core Architectural Modules

### 3.1. PBR Texture Studio (`gallery.py`)
Generates 5 synchronized physical material channels from any 2D albedo texture:
1. **Tangent-Space Normal Map**: Computes Sobel spatial image gradients along $X$ and $Y$ axes:
   $$\nabla I_x = \text{Sobel}_x(I), \quad \nabla I_y = \text{Sobel}_y(I)$$
   Normal vectors are normalized to unit magnitude and packed into standard RGB normal color space:
   $$N = \frac{[\nabla I_x \cdot s, \; -\nabla I_y \cdot s, \; 1.0]}{\sqrt{(\nabla I_x \cdot s)^2 + (\nabla I_y \cdot s)^2 + 1.0}}, \quad \text{RGB} = \frac{N + 1}{2} \times 255$$
2. **Roughness Map**: Inverted specular response with gamma power curve ($R = (1.0 - I)^{0.8}$).
3. **Displacement / Height Map**: Normalized 8-bit luminance elevation data.
4. **Ambient Occlusion (AO)**: Cavity shading approximation with dynamic contrast clamping.
5. **$3 \times 3$ Seamless Wrap Tiling**: Real-time seam inspection matrix.

### 3.2. Interactive Inpainting Canvas (`comfyui_desktop/inpaint_canvas.py`)
- Real-time brush painting with dynamic diameter slider ($4\text{px} \dots 100\text{px}$).
- Eraser mode with visual indicator.
- Single-click mask inversion ($M_{\text{inv}} = 255 - M$).
- Seamless staging into ComfyUI `INPUT_DIR` and automatic workflow wiring.

### 3.3. Zero-Dependency RFC 6455 WebSocket Client (`comfyui_desktop/ws_client.py`)
- Fully compliant with RFC 6455 Section 5.1 (client-to-server masking key application).
- Handles text frames (Opcode `0x1`) for live progress JSON payloads (`val`, `max`, `node`).
- Decodes binary frames (Opcode `0x2`) by stripping 8-byte event headers and piping raw JPEG data into PIL image buffers.
- Automatic reconnection watchdog with exponential backoff.

### 3.4. Dynamic Path & Portability Engine (`config.py` & `comfyui_desktop/config.py`)
- Dynamic base directory resolution via `COMFYUI_PORTABLE_DIR`, relative repo anchors, and standard system paths.
- Zero machine-specific hardcoded paths across all modules.

---

## 4. Verification & Testing Methodology

The codebase is validated against **146 automated test assertions**:
1. **Primary Functional QA Suite** (`qa_suite.py`): 58 / 58 PASSED (100%)
2. **Deep Multi-Vector Stress Suite** (`multi_angle_debug.py`): 88 / 88 PASSED (100%)
Total: **146 / 146 PASSED (100% Pass Rate)**

---

## 5. Running Locally & Building

```powershell
# Run the application from source
python ComfyUI_App.py

# Run the automated QA verification suites
python qa_suite.py
python multi_angle_debug.py

# Build standalone distribution
pyinstaller --clean -y ComfyUI_Uncensored.spec
```
