# ⚡ ComfyUIX Matrix Edition v5.0

> **The Ultimate Standalone Local AI Generation Suite & Matrix HUD for Windows**

[![Release](https://img.shields.io/badge/release-v5.0.0--Matrix-00FF66.svg?style=for-the-badge&logo=matrix)](https://github.com/Bonbrake/ComfyUIX)
[![QA Status](https://img.shields.io/badge/QA%20Tests-110%2F110%20PASSED-00FF66.svg?style=for-the-badge)](https://github.com/Bonbrake/ComfyUIX)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0080FF.svg?style=for-the-badge&logo=windows)](https://github.com/Bonbrake/ComfyUIX)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)

---

## 🌟 What is ComfyUIX?

**ComfyUIX** is a cutting-edge, zero-dependency desktop frontend for generative AI image, video, audio, and PBR 3D material generation. It combines the power of ComfyUI backend graph workflows with a streamlined, responsive **Matrix Dark Glass** user experience.

Accompanied by the **Matrix AI HUD** companion copilot, ComfyUIX delivers an all-in-one workstation for AI creators, game developers, 3D artists, and digital creators.

---

## ✨ Key Features

### 🎨 Creative Workflow Studios
- **Text to Image**: High-precision prompt engineering, LoRA stacking, custom VAE selection, and High-Resolution Fix (Hires Fix) latent upscaling.
- **Image to Image & Inpainting**: Built-in interactive **Inpainting Canvas** with brush size control, eraser mode, mask inversion, and direct workflow staging.
- **PBR Texture Studio**: Generates 5 game-ready physical material maps (Normal Map with Sobel tangent vectors, Roughness, Height/Displacement, Ambient Occlusion, and $3 \times 3$ Seamless Tiled wrap inspection).
- **AI Video Engine**: Support for Text-to-Video, Video-to-Video, and video refine workflows (Wan 2.1, AnimateDiff, HunyuanVideo).
- **Audio Synthesis**: Multi-engine sound and speech synthesis (Bark TTS, AudioLDM, MusicGen).

### ⚡ Performance & Hardware Engine
- **Zero-Dependency RFC 6455 WebSocket Client**: Real-time live latent preview streaming (binary JPEG frames) and step execution progress.
- **GPU Doctor & Smart VRAM Auto-Tuning**: Automatic detection of GPU VRAM, vendor optimization, and smart `--medvram`/`--lowvram` selection.
- **Multi-Monitor Bounds Protection**: Negative coordinate window restoration guarantees the app never opens off-screen.
- **Process Tree Reclamation**: Clean Windows Job Object integration ensures no orphan backend processes remain on exit.
- **Integrated Model Vault**: Hugging Face and CivitAI live browser with pre-flight disk space checks and companion `.preview.png` caching.

---

## 🚀 Quickstart

### Running from Source
```powershell
# 1. Clone the repository
git clone https://github.com/Bonbrake/ComfyUIX.git
cd ComfyUIX

# 2. Launch the desktop application
python ComfyUI_App.py
```

### Running Automated Test Suites
```powershell
# Run the Primary Functional QA Suite (53 Tests)
python qa_suite.py

# Run the Multi-Angle Deep Stress & Math Suite (57 Tests)
python scratch/multi_angle_debug.py
```

---

## 📋 Comprehensive Audit & Technical Spec

For the full detailed engineering audit, architectural diagrams, mathematical formulations, and verification breakdown, refer to [AUDIT_PLAN_AND_SPECIFICATION.md](AUDIT_PLAN_AND_SPECIFICATION.md).

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
