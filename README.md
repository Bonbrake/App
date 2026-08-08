# ComfyUI Uncensored (Windows Desktop App)

A native **Windows 11** desktop wrapper for [ComfyUI](https://github.com/comfyanonymous/ComfyUI),
built with **Python 3.11 + CustomTkinter**. It launches the ComfyUI backend in the
background and gives you a dark, glass-themed GUI for prompting, model selection, and
image generation — no browser required.

> **This repository contains application source code only.** AI model weights, the
> ComfyUI portable runtime, generated images, and build artifacts are intentionally
> **excluded** (see `.gitignore`). See [Setup](#setup) to obtain the runtime pieces.

---

## Features
- Native Windows 11 app (CustomTkinter, dark glass UI, hover tooltips)
- Wraps the official ComfyUI 0.29.0 portable backend (runs on `http://127.0.0.1:8188`)
- Model presets with auto-applied optimal settings
- Native preview panel, drag-and-drop / browse image input, upscale options (2x/4x)
- Background backend management (start / restart / monitor)
- Crash diagnostics + log viewer

## Repository layout
| Path | Purpose |
|------|---------|
| `main.py` | Application entry point (has `if __name__ == "__main__"`) |
| `ComfyUI_App.py` | Primary application module (UI + controller logic) |
| `config.py` / `config.json` | Runtime settings, model definitions, paths |
| `backend.py` | Backend (ComfyUI server) lifecycle management |
| `glass.py` / `gallery.py` / `widgets.py` | UI helpers (acrylic background, gallery, custom widgets) |
| `ComfyUI_Error_Monitor.py` | Error monitoring / log capture |
| `orphan_reap.py` | Stray backend-process cleanup |
| `comfyui_desktop/` | UI subpackage (windows, diagnostics, ws client, backend manager) |
| `build_exe.py` / `ComfyUI_Uncensored.spec` / `app.manifest` | PyInstaller build → `dist/ComfyUI_Uncensored.exe` |

## Requirements
- Windows 10/11
- Python **3.11** (the build requires `C:\Users\<you>\AppData\Local\Programs\Python\Python311\python.exe`)
- ComfyUI 0.29.0 **portable** placed at `ComfyUI_windows_portable\ComfyUI` (excluded from git)
- Uncensored checkpoints in `ComfyUI_windows_portable\ComfyUI\models\checkpoints` (excluded)
- Python packages: `customtkinter`, `requests`, `Pillow`, `imageio` (+ `imageio-ffmpeg`), `pywin32`, `PyInstaller` (build only)

## Run from source
```bat
py -3.11 main.py
```
The app will start the ComfyUI backend on `127.0.0.1:8188` automatically.

## Build a standalone EXE
```bat
py -3.11 build_exe.py
```
This preserves the previous good EXE to `_last_good\` (rollback safety) and writes a
fresh `dist\ComfyUI_Uncensored.exe`. A successful bundle is ~35 MB.

## Notes
- Output images default to `C:\Users\<you>\Pictures\ComfyUI_Generated\`.
- Logs: `C:\Users\<you>\Logs\ComfyUI_App.log`.
- Keyboard shortcuts: `Ctrl+E` generate · `Ctrl+O` open output · `Ctrl+R` restart backend · `F1` toggle tooltips.
