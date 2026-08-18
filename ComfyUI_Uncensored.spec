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

# FIX: Discover PyInstaller hook directories in-process
def _discover_hook_dirs_inproc():
    try:
        from PyInstaller.compat import importlib_metadata
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

from PyInstaller.utils.hooks import collect_all
hermes_path = os.path.join(REPO_ROOT, "hermes_app.py")
spec_datas = ([(icon_path, 'static/assets')] if os.path.exists(icon_path) else []) + [(build_info_path, '.')]
if os.path.exists(hermes_path):
    spec_datas.append((hermes_path, '.'))

spec_binaries = []
spec_hiddenimports = ['PIL', 'PIL._tkinter_finder', 'PIL.ImageTk', 'win32mica', 'requests', 'ctypes', 'ctypes.wintypes',
                       'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.font',
                       'customtkinter', 'imageio', 'imageio.v2', 'imageio_ffmpeg', 'numpy', 'importlib.metadata',
                       'glass', 'orphan_reap', 'gallery', 'config', 'backend', 'model_downloader', 'hermes_app',
                       'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'psutil', 'win32com', 'win32com.client',
                       'comfyui_desktop', 'comfyui_desktop.glass', 'comfyui_desktop.orphan_reap',
                       'comfyui_desktop.config', 'comfyui_desktop.diagnostics', 'comfyui_desktop.gallery',
                       'comfyui_desktop.backend_manager', 'comfyui_desktop.widgets', 'comfyui_desktop.ws_client']

for _pkg in ('customtkinter', 'imageio', 'imageio_ffmpeg', 'av', 'PIL', 'comfyui_desktop', 'requests', 'numpy', 'glass', 'onnxruntime', 'ctranslate2', 'scipy', 'sklearn', 'pydantic', 'rich', 'fastapi', 'uvicorn', 'cryptography', 'lxml', 'sounddevice', 'tokenizers', 'yaml', 'PySide6', 'psutil'):
    try:
        _d, _b, _h = collect_all(_pkg)
        spec_datas.extend(_d)
        spec_binaries.extend(_b)
        spec_hiddenimports.extend(_h)
    except Exception:
        pass

# Bundle Tcl/Tk data files for Tkinter & CustomTkinter (Fix PyInstaller pyi_rth__tkinter _tcl_data hook)
try:
    from PyInstaller.utils.hooks.tcl_tk import tcltk_info
    tcltk_info._load_tcl_tk_info()
    if getattr(tcltk_info, "data_files", None):
        spec_datas.extend([(src, os.path.dirname(dst)) for dst, src, _ in tcltk_info.data_files])
except Exception:
    pass

tcl_bases = [
    os.path.join(sys.base_prefix, 'tcl'),
    os.path.join(sys.prefix, 'tcl'),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", f"Python{sys.version_info.major}{sys.version_info.minor}", "tcl"),
    r'C:\Python311\tcl',
    r'C:\Python312\tcl',
]
tcl_root = next((b for b in tcl_bases if os.path.isdir(b)), None)
if tcl_root:
    t86 = os.path.join(tcl_root, 'tcl8.6')
    k86 = os.path.join(tcl_root, 'tk8.6')
    if os.path.isdir(t86):
        for root, dirs, files in os.walk(t86):
            for f in files:
                sf = os.path.join(root, f)
                rel = os.path.relpath(sf, t86)
                spec_datas.append((sf, os.path.join('_tcl_data', os.path.dirname(rel))))
                spec_datas.append((sf, os.path.join('tcl8.6', os.path.dirname(rel))))
                spec_datas.append((sf, os.path.join('lib', 'tcl8.6', os.path.dirname(rel))))
    if os.path.isdir(k86):
        for root, dirs, files in os.walk(k86):
            for f in files:
                sf = os.path.join(root, f)
                rel = os.path.relpath(sf, k86)
                spec_datas.append((sf, os.path.join('_tk_data', os.path.dirname(rel))))
                spec_datas.append((sf, os.path.join('tk8.6', os.path.dirname(rel))))
                spec_datas.append((sf, os.path.join('lib', 'tk8.6', os.path.dirname(rel))))
    for root, dirs, files in os.walk(tcl_root):
        for f in files:
            sf = os.path.join(root, f)
            rel = os.path.relpath(sf, tcl_root)
            spec_datas.append((sf, os.path.join('tcl', os.path.dirname(rel))))

import site
for _sp in site.getsitepackages():
    if os.path.exists(_sp):
        for _item in os.listdir(_sp):
            if _item.endswith(".libs"):
                _ldir = os.path.join(_sp, _item)
                if os.path.isdir(_ldir):
                    for _fname in os.listdir(_ldir):
                        _fp = os.path.join(_ldir, _fname)
                        if os.path.isfile(_fp):
                            spec_binaries.append((_fp, "."))
                            spec_binaries.append((_fp, _item))

a = Analysis(
    ['ComfyUI_App.py'],
    pathex=[REPO_ROOT],
    binaries=spec_binaries,
    datas=spec_datas,
    hiddenimports=spec_hiddenimports,
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
    name='ComfyUIX',
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
    icon=icon_path if os.path.exists(icon_path) else None,
)
