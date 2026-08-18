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

# FIX (2026-08-12): Tcl/Tk init files are located at runtime via the on-disk
# Python311 install (see _ensure_tcl_tk_env() in ComfyUI_App.py, which FORCE-sets
# TCL_LIBRARY/TK_LIBRARY before `import tkinter`). We deliberately do NOT bundle
# _tcl_data/_tk_data: under PyInstaller's onefile bootloader the rthook points
# TCL_LIBRARY at a _MEI subdir that ends up empty on this machine, breaking
# tkinter init. Pointing at the always-present on-disk tcl is deterministic.

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

# FIX (2026-08-17): numpy 2.x imports several `numpy._core` submodules from
# inside its C extension (_multiarray_umath), so PyInstaller's static module
# graph cannot see them. numpy's bundled hook-numpy.py only declares
# `_dtype_ctypes` and `_multiarray_tests`, which left `numpy._core._exceptions`
# out of the PYZ. At runtime that raised
#   "Importing the numpy C-extensions failed ... No module named
#    numpy._core._exceptions"
# which the guarded `import imageio` in ComfyUI_App.py swallowed, silently
# disabling video support (HAS_VIDEO=False) in an otherwise "successful" build.
# Collect the whole `numpy._core` package instead of hand-picking names so a
# future numpy point release cannot reintroduce the same class of gap.
try:
    from PyInstaller.utils.hooks import collect_submodules
    _numpy_core_hidden = collect_submodules('numpy._core')
except Exception:
    # Never let a hook-API change break the build; fall back to the exact
    # module that was verified missing from the bundle.
    _numpy_core_hidden = ['numpy._core._exceptions']
# Guarantee the verified-missing module is present regardless of which path ran.
for _m in ('numpy._core._exceptions', 'numpy._core._dtype_ctypes', 'numpy.exceptions'):
    if _m not in _numpy_core_hidden:
        _numpy_core_hidden.append(_m)

a = Analysis(
    ['ComfyUI_App.py'],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=([(icon_path, 'static/assets')] if os.path.exists(icon_path) else []) + [(build_info_path, '.')],
    hiddenimports=[
        # Imaging / tkinter bridge
        'PIL', 'PIL._tkinter_finder', 'PIL.ImageTk',
        'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.font',
        'customtkinter', 'numpy', 'requests', 'ctypes', 'ctypes.wintypes', 'importlib.metadata',
        # Lazily imported feature deps (guarded try/except at the call site, so
        # the module graph cannot discover them statically).
        'imageio', 'imageio.v2', 'imageio_ffmpeg',
        'psutil',                                  # orphan_reap.reap_process_tree()
        'win32com', 'win32com.client', 'win32clipboard',   # SAPI TTS + clipboard copy
        # Top-level app modules imported lazily inside functions.
        'orphan_reap', 'glass',
        # comfyui_desktop package (real submodules only — verified against the
        # tracked tree; 'comfyui_desktop.glass'/'.orphan_reap' do NOT exist,
        # those are top-level modules and are listed above.)
        'comfyui_desktop', 'comfyui_desktop.config', 'comfyui_desktop.diagnostics',
        'comfyui_desktop.backend_manager', 'comfyui_desktop.gallery',
        'comfyui_desktop.main_window', 'comfyui_desktop.widgets',
        'comfyui_desktop.ws_client',
    ] + _numpy_core_hidden,
    # Feed the in-process hook dirs computed above. Passing [] here (the previous
    # behaviour) silently dropped the numpy/PIL binary hooks and produced the
    # broken ~63 MB bundle the comment above warns about.
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
