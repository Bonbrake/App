# -*- mode: python ; coding: utf-8 -*-
import os

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
comfy_dir = os.path.join(REPO_ROOT, "ComfyUI_windows_portable")
icon_path = os.path.join(comfy_dir, "python_embeded", "Lib", "site-packages", "comfyui_frontend_package", "static", "assets", "favicon.ico")

a = Analysis(
    ['ComfyUI_App.py'],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=[(icon_path, 'static/assets')] if os.path.exists(icon_path) else [],
    hiddenimports=['PIL', 'PIL._tkinter_finder', 'PIL.ImageTk', 'win32mica', 'requests', 'ctypes', 'ctypes.wintypes',
                               'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.font',
                               'customtkinter', 'imageio', 'imageio.v2', 'imageio_ffmpeg', 'numpy', 'importlib.metadata',
                               'comfyui_desktop.glass', 'comfyui_desktop.orphan_reap', 'comfyui_desktop.config',
                               'comfyui_desktop.diagnostics'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ComfyUI_Uncensored',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon_path] if os.path.exists(icon_path) else [],
)
