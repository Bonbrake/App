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
*Every item below is present in the shipped source and covered by `tests/qa_audit.py`.*
- Native Windows 11 app (CustomTkinter, dark glass UI, hover tooltips)
- Wraps the official ComfyUI 0.29.0 portable backend (runs on `http://127.0.0.1:8188`)
- Model presets with auto-applied optimal settings
- Native preview panel, drag-and-drop / browse image input, upscale options (2x/4x)
- Tabs: Text to Image · Image to Image · Upscale · Text to Video · Video to Video ·
  Video Refine & Upscale · Audio · Debug
- Background backend management (start / restart / monitor) + stray-process reaping
- Crash diagnostics: breadcrumbs, frame locals, thread dump, known-fix matching,
  one-click debug bundle (zip), log viewer
- Single-instance guard (a second launch raises the existing window instead of
  starting a second GUI + backend)

## Repository layout
| Path | Purpose |
|------|---------|
| `main.py` | Application entry point (has `if __name__ == "__main__"`) |
| `ComfyUI_App.py` | Primary application module (UI + controller logic) |
| `config.py` / `config.json` | Runtime settings, model definitions, paths |
| `backend.py` | Backend (ComfyUI server) lifecycle management |
| `glass.py` / `gallery.py` / `widgets.py` | UI helpers (acrylic background, gallery, custom widgets) |
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
fresh `dist\ComfyUI_Uncensored.exe`.

## Privacy & Security
This app makes **no network connections other than to your own local ComfyUI server.**

| Property | Status | Evidence |
|---|---|---|
| Network egress | Localhost only | Every HTTP/WebSocket call targets `http://127.0.0.1:8188` or `127.0.0.1:8199` (`config.py`, `comfyui_desktop/config.py`, `main.py`, `ComfyUI_App.py`) |
| Telemetry / analytics | None | No analytics SDK, no usage reporting, no crash upload — diagnostics stay on disk |
| Update checks | None | No external URL is contacted at any point |
| Server bind address | `127.0.0.1` | Backend is started without `--listen`, so ComfyUI binds loopback only |
| Admin elevation | Not requested | `app.manifest` declares `asInvoker` |
| Autostart / registry | None | No `Run` keys, no scheduled tasks, no services |
| Personal data in repo | None | Paths resolve via `expanduser`; no usernames are committed |

**Your data stays local:** prompts, generated images, and diagnostics are written only
to your own machine (see [Notes](#notes) for locations).

> ⚠️ **One user-controlled risk:** the *Custom Launch Args* setting is passed through to
> the ComfyUI backend. If you add `--listen 0.0.0.0` there, the server becomes reachable
> from your whole network. Don't do that on an untrusted network.

### Licensing
The wrapper in this repository is **MIT** licensed. The ComfyUI portable runtime it
launches is **GPL-3.0** and is *not* redistributed here — you supply it yourself, so the
two licenses stay independent.

## Known limitations
- **The EXE is unsigned.** Windows SmartScreen will show *"Windows protected your PC"*
  on first run. To launch it anyway: **More info → Run anyway**. Code-signing requires a
  paid certificate and is planned for a later release.
- The engine is **not bundled** (it's ~90 GB with models). `Setup.bat` places an existing
  local copy next to the EXE, or prints manual instructions if none is found.
- Requires an **NVIDIA GPU** for practical generation speed; VRAM limits which models
  and resolutions are usable.
- `tests/qa_audit.py` is a **static/structural** audit of the source. It does not
  generate images; end-to-end image quality still needs a human eyeball.

## Notes
- Output images default to `C:\Users\<you>\Pictures\ComfyUI_Generated\`.
- Logs: `C:\Users\<you>\Logs\ComfyUI_App.log`.
- Keyboard shortcuts: `Ctrl+E` generate · `Ctrl+O` open output · `Ctrl+R` restart backend · `F1` toggle tooltips.
