# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# PyInstaller is supposed to expose __file__ to the spec, but some 6.x builds
# exec the spec without it in the namespace. Fall back to sys.argv[0] so the
# spec resolves REPO_ROOT correctly either way.
try:
    _SPEC_PATH = __file__
except NameError:
    _SPEC_PATH = sys.argv[0]
REPO_ROOT = os.path.dirname(os.path.abspath(_SPEC_PATH))
comfy_dir = os.path.join(REPO_ROOT, "ComfyUI_windows_portable")
portable_icon = os.path.join(comfy_dir, "python_embeded", "Lib", "site-packages", "comfyui_frontend_package", "static", "assets", "favicon.ico")
# Prefer repo-vendored icon so the EXE always carries a valid icon even if the
# ComfyUI portable install is moved/cleaned (otherwise builds silently ship iconless).
icon_path = os.path.join(REPO_ROOT, "assets", "app_icon.ico")
if not os.path.exists(icon_path):
    icon_path = portable_icon
build_info_path = os.path.join(REPO_ROOT, "build_info.json")

# FIX (2026-08-09): PyInstaller 6.21's isolated subprocess crashes on
# discover_hook_directories() ("TypeError: arg 5 (closure) must be tuple" under
# this Python 3.11 build), so PyInstaller silently falls back to hookspath=[]
# and DROPS numpy/PIL/MKL binary hooks -> a broken ~63MB bundle missing ~70MB
# of deps. Recompute those exact hook directories IN-PROCESS via the
# `pyinstaller40` entry points (the same source discover_hook_directories
# uses, minus the broken isolation) and feed them as hookspath. This restores
# a complete ~133MB bundle deterministically.
def _discover_hook_dirs_inproc():
    try:
        from PyInstaller.compat import importlib_metadata
        from PyInstaller.depend.analysis import (
            HOOK_PRIORITY_CONTRIBUTED_HOOKS,
            HOOK_PRIORITY_UPSTREAM_HOOKS,
        )
        eps = importlib_metadata.entry_points(group="pyinstaller40", name="hook-dirs")
        eps = sorted(eps, key=lambda x: x.module.startswith("_pyinstaller_hooks_contrib"))
        dirs = []
        for ep in eps:
            try:
                for h in ep.load()():
                    dirs.append(h)
            except Exception:
                continue
        return dirs
    except Exception:
        return []

hook_dirs = _discover_hook_dirs_inproc()

a = Analysis(
    ['ComfyUI_App.py'],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=([(icon_path, 'static/assets')] if os.path.exists(icon_path) else []) + [(build_info_path, '.')],
    hiddenimports=['PIL', 'PIL._tkinter_finder', 'PIL.ImageTk', 'win32mica', 'requests', 'ctypes', 'ctypes.wintypes',
                               'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.font',
                               'customtkinter', 'imageio', 'imageio.v2', 'imageio_ffmpeg', 'numpy', 'importlib.metadata',
                               'comfyui_desktop.glass', 'comfyui_desktop.orphan_reap', 'comfyui_desktop.config',
                               'comfyui_desktop.diagnostics'],
    hookspath=hook_dirs,
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
