# ⚡ ComfyUIX Matrix Edition v5.0

> **The Ultimate Standalone Local AI Generation Workstation & Matrix HUD for Windows**

[![Release](https://img.shields.io/badge/release-v5.0.0--Matrix-00FF66.svg?style=for-the-badge&logo=matrix)](https://github.com/Bonbrake/ComfyUIX/releases)
[![QA Status](https://img.shields.io/badge/QA%20Tests-160%2B%20PASSED-00FF66.svg?style=for-the-badge)](https://github.com/Bonbrake/ComfyUIX)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0080FF.svg?style=for-the-badge&logo=windows)](https://github.com/Bonbrake/ComfyUIX)
[![CI Build](https://img.shields.io/badge/CI%20Build-Passing-00FF66.svg?style=for-the-badge&logo=githubactions)](https://github.com/Bonbrake/ComfyUIX/actions)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)

---

## 🌟 What is ComfyUIX?

**ComfyUIX** is a cutting-edge, zero-dependency desktop frontend and local AI workstation designed for generative image, video, audio, and PBR 3D material generation. It combines the raw power and modularity of ComfyUI backend graph workflows with a clean, responsive **Matrix Cyber Glass** user interface.

Accompanied by the **Matrix AI HUD** companion copilot, ComfyUIX delivers an all-in-one, frictionless powerhouse for digital artists, game developers, 3D texture artists, and AI creators.

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

## ⚔️ Why ComfyUIX? (Comparison Matrix)

| Feature | ComfyUIX Matrix | ComfyUI Web | StabilityMatrix | Fooocus | SwarmUI |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pure Desktop Executable** | ⚡ **Native (.exe)** | ❌ Browser tab | ⚠️ Electron wrapper | ⚠️ Browser UI | ⚠️ Browser UI |
| **Interactive Inpainting Canvas** | ✅ **Integrated** | ⚠️ Web canvas | ❌ None | ⚠️ Basic | ⚠️ Basic |
| **PBR 3D Texture Studio** | ✅ **5 Maps + 3x3 Wrap** | ❌ Manual nodes | ❌ None | ❌ None | ❌ None |
| **RFC 6455 Zero-Dep WebSocket** | ✅ **Native** | ⚠️ JS WebSocket | ⚠️ JS WebSocket | ❌ None | ⚠️ WebSockets |
| **Local LLM Copilot HUD** | ✅ **Matrix HUD** | ❌ None | ❌ None | ❌ None | ❌ None |
| **Process Tree Leak Reaper** | ✅ **Windows Job Object**| ❌ Orphan leaks | ⚠️ Variable | ❌ None | ❌ None |
| **1-Click Parameter Rehydration** | ✅ **Yes (PNG tEXt)** | ⚠️ Manual JSON | ❌ None | ❌ None | ⚠️ Partial |
| **1-Click Clipboard Image Export**| ✅ **Instant** | ❌ None | ❌ None | ❌ None | ❌ None |

---

## ✨ Key Features & Creative Studios

### 🎨 Creative Workflow Studios
- **Text to Image Studio**: High-precision prompt crafting, aspect ratio quick matrix (1:1, 16:9, 9:16, 4:3, 3:4, 21:9), LoRA stacking, custom VAE selection, and Hires Fix upscaling.
- **Image to Image & Inpainting**: Built-in interactive **Inpainting Canvas** with real-time brush scaling (4–100px), eraser mode, mask inversion, and direct workflow staging.
- **PBR Texture Studio**: Generates 5 game-ready physical material maps (Normal Map with Sobel unit tangent vectors, Roughness, Height/Displacement, Ambient Occlusion, and $3 \times 3$ Seamless Tiled wrap inspection).
- **AI Video Engine**: High-fidelity Text-to-Video, Video-to-Video, and video refine workflows (Wan 2.1, AnimateDiff, HunyuanVideo).
- **Audio Synthesis**: Multi-engine sound effect and speech synthesis (Bark TTS, AudioLDM, MusicGen).

### ⚡ Performance & Hardware Reliability
- **Zero-Dependency RFC 6455 WebSocket Client**: Real-time live latent preview streaming (binary JPEG frames) and step execution progress.
- **GPU Doctor & Smart VRAM Auto-Tuning**: Automatic detection of GPU VRAM, vendor optimization, and smart `--medvram`/`--lowvram` selection.
- **Multi-Monitor Bounds Protection**: Negative coordinate window restoration guarantees the app never opens off-screen.
- **Process Tree Reclamation**: Clean Windows Job Object integration ensures no orphan backend processes remain on exit.
- **Integrated Model Vault**: Hugging Face and CivitAI live browser with pre-flight disk space checks and companion `.preview.png` caching.

---

## ⌨️ Keyboard Shortcuts Reference

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>Enter</kbd> / <kbd>Ctrl</kbd> + <kbd>E</kbd> | **⚡ Generate** | Start AI generation in active studio tab |
| <kbd>Escape</kbd> | **🛑 Cancel / Interrupt** | Instantly abort running generation and clear queue |
| <kbd>Ctrl</kbd> + <kbd>R</kbd> | **⟳ Restart Server** | Soft restart ComfyUI backend subprocess |
| <kbd>Ctrl</kbd> + <kbd>O</kbd> | **📁 Open Output** | Open output media folder in Windows Explorer |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>C</kbd> | **📋 Copy Prompt** | Copy active positive prompt to OS clipboard |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>W</kbd> | **⇄ Swap Dimensions** | Swap Width and Height values (Landscape ⇄ Portrait) |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>V</kbd> | **⚡ Free VRAM** | Flush PyTorch CUDA cache and unload unused models |
| <kbd>F1</kbd> | **❓ Shortcuts HUD** | Display complete interactive keyboard shortcuts cheatsheet |
| <kbd>F5</kbd> | **🔄 Refresh Gallery** | Rescan output folder and refresh media vault thumbnails |
| <kbd>F12</kbd> / <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd> | **🖥️ Debug Console** | Focus live terminal logs and system diagnostics |
| <kbd>Ctrl</kbd> + <kbd>1</kbd> .. <kbd>8</kbd> | **📑 Switch Studio Tab** | Jump directly between Studio tabs (Txt2Img, Img2Img, Video, etc.) |

---

## 💻 Hardware Requirements

| Tier | GPU VRAM | Recommended Models & Resolution | Target Performance |
| :--- | :--- | :--- | :--- |
| **Minimum** | 4GB – 6GB | SD 1.5, LCM, 512×512, `--lowvram` | ~3–5s per image |
| **Recommended** | 8GB – 12GB | SDXL, Turbo, 1024×1024, `--medvram` | ~4–8s per image |
| **High-End Studio** | 16GB – 24GB+ | FLUX.1 Dev, Wan 2.1 Video, 4K Hires Fix | ~2–4s per image |

---

## 🚀 Quickstart

### Running from Source
```powershell
# 1. Clone the repository
git clone https://github.com/Bonbrake/ComfyUIX.git
cd ComfyUIX

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the desktop application
python ComfyUI_App.py
```

### Running Automated Test Suites
```powershell
# Run the Primary Functional QA Suite (53 Tests)
python qa_suite.py

# Run the Multi-Angle Deep Stress & Math Suite (160+ Assertions)
python multi_angle_debug.py
```

---

## 📋 Technical Specification & Master Architecture

For the complete technical breakdown, mathematical formulations (Sobel operators, normal mapping, gamma curves), and audit vectors, see [AUDIT_PLAN_AND_SPECIFICATION.md](AUDIT_PLAN_AND_SPECIFICATION.md).

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
