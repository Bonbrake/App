# ComfyUI Uncensored - Setup Guide

## Quick Start
1. Double-click **"ComfyUI Uncensored"** on Desktop
2. Native app window opens → ComfyUI starts automatically in background
3. Pick model → Type prompt → Click **Generate**
4. Images save to `C:\Users\jakeb\Pictures\ComfyUI_Generated\`

## What You Get
- **3 Uncensored Models** (no safety filters, all content works):
  - **epiCRealism XL** - Photorealistic portraits (768×768, CFG 6.5, 35 steps)
  - **Juggernaut XL** - High quality general (1216×832, CFG 5.0, 35 steps)
  - **Pony Diffusion V6 XL** - Anime/stylized (832×1216, CFG 7.0, 25 steps)

- **Native Windows App** (no browser needed):
  - Dark professional theme
  - Hover tooltips with descriptions + recommended values
  - Auto-applied optimal settings per model
  - Upscale options (2x, 4x)
  - Drag & drop image support (browse button fallback)
  - Native preview panel
  - Error monitoring with logs in `C:\Users\jakeb\Logs\`

## Files
| File | Purpose |
|------|---------|
| `Desktop\ComfyUI Uncensored.lnk` | **Launch the app** |
| `C:\ComfyUI-Desktop\dist\ComfyUI_Uncensored.exe` | Native executable (35 MB) |
| `C:\ComfyUI-Desktop\ComfyUI_App.py` | Source code |
| `C:\ComfyUI-Desktop\ComfyUI_Error_Monitor.py` | Error monitoring script |
| `\ComfyUI-Desktop\ComfyUI_windows_portable\` | Official ComfyUI 0.29.0 portable |
| `\ComfyUI_windows\portable\ComfyUI\workflows\` | Pre-made workflow JSON files |

## Troubleshooting
- Check `C:\Users\jakeb\Logs\ComfyUI_App.log` for detailed logs
- Error files saved to `C:\Users\jakeb\Logs\ComfyUI_Error_*.json`
- Use "View Log" button in app to open logs
- "Restart" button restarts ComfyUI backend if stuck
- If ComfyUI fails to start, click "Restart Backend"

## Keyboard Shortcuts
- **Ctrl+E** - Generate image
- **Ctrl+O** - Open output folder
- **Ctrl+R** - Restart ComfyUI backend
- **F1** - Toggle tooltips