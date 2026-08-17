"""Build + deploy the SHIPPING app (ComfyUI_App.py -> ComfyUI_Uncensored.exe).

Wraps build_exe.py's spec (ComfyUI_Uncensored.spec, onefile) and adds the
deploy-side steps: back up the previous good binary, install the freshly built
EXE next to the repo, and refresh the Desktop shortcut.

Paths are resolved relative to this file / the current user's profile, so the
script is portable across machines. Override the install location with the
COMFYUI_UNCENSORED_INSTALL_DIR environment variable.

Usage:  python build_glass.py
Exit codes: 0 ok | 2 no artifact | 3 artifact too small | 4 no interpreter | 5 deploy failed
"""
import ctypes
import datetime
import json
import os
import shutil
import subprocess
import sys

import PyInstaller  # fail fast if missing

# PyInstaller 6.21 isolated-subprocess discover_hook_directories() crash workaround
# (mirrors ComfyUI_Uncensored.spec / build_exe.py).
try:
    from PyInstaller.building import build_main as _bm

    def _discover_hook_directories_noop():
        return []

    _bm.discover_hook_directories = _discover_hook_directories_noop
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO_ROOT)

APP_NAME = "ComfyUI_Uncensored"
SPEC = os.path.join(REPO_ROOT, "%s.spec" % APP_NAME)
EXE_NAME = "%s.exe" % APP_NAME

# Where the shipping binary is installed. Env override wins unconditionally.
_env_install = os.environ.get("COMFYUI_UNCENSORED_INSTALL_DIR")
if _env_install:
    DEPLOY_DIR = os.path.normpath(os.path.expanduser(os.path.expandvars(_env_install)))
else:
    DEPLOY_DIR = REPO_ROOT
DEPLOY_EXE = os.path.join(DEPLOY_DIR, EXE_NAME)
ROLLBACK = os.path.join(REPO_ROOT, "_last_good_glass")
SHORTCUT = os.path.join(
    os.path.normpath(os.path.expanduser("~/Desktop")), "ComfyUI Uncensored.lnk"
)

# A valid frozen tkinter onefile build is ~120+ MB. Reject anything implausibly small.
MIN_EXE_BYTES = 80_000_000

# --- Emit build metadata so the running app can show a STABLE build identity. ---
BUILD_INFO = os.path.join(REPO_ROOT, "build_info.json")
try:
    build_meta = {
        "build": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "built_with": "PyInstaller %s" % getattr(PyInstaller, "__version__", "?"),
        "repo": "ComfyUI-Uncensored",
        "target": "%s (ComfyUI_App.py)" % APP_NAME,
    }
    with open(BUILD_INFO, "w") as _bf:
        json.dump(build_meta, _bf, indent=2)
    print("Wrote build metadata:", BUILD_INFO)
except OSError as e:
    print("WARN: could not write build metadata:", e)

# Build MUST use a Python 3.11 with PIL/numpy/customtkinter/tkinter/PyInstaller.
# Prefer the interpreter running this script; fall back to the on-disk Python311.
PY311 = os.path.normpath(
    os.path.expanduser(r"~/AppData/Local/Programs/Python/Python311/python.exe")
)


def _has_pyinstaller(py):
    if not py or not os.path.exists(py):
        return False
    try:
        subprocess.run(
            [py, "-c", "import PyInstaller"], capture_output=True, text=True, check=True
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


if _has_pyinstaller(sys.executable):
    BUILD_PY = sys.executable
elif _has_pyinstaller(PY311):
    BUILD_PY = PY311
else:
    BUILD_PY = None
if not BUILD_PY:
    print(
        "BUILD FAILED: no Python 3.11 with PyInstaller found (tried %s and %s)"
        % (sys.executable, PY311)
    )
    sys.exit(4)
print("Using build interpreter:", BUILD_PY)

if not os.path.exists(SPEC):
    print("BUILD FAILED: spec not found:", SPEC)
    sys.exit(2)

# Preserve the previous good binary so a failed build never strands the shortcut.
if os.path.isfile(DEPLOY_EXE):
    try:
        os.makedirs(ROLLBACK, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = os.path.join(ROLLBACK, "%s_%s.exe" % (APP_NAME, stamp))
        shutil.copy2(DEPLOY_EXE, bak)
        print("Preserved previous binary at", bak)
    except OSError as e:
        print("WARN: could not preserve previous binary:", e)

# Clean prior build artifacts so a stale bundle can never be mistaken for success.
for _d in ("build", "dist"):
    shutil.rmtree(os.path.join(REPO_ROOT, _d), ignore_errors=True)

result = subprocess.run(
    [BUILD_PY, "-m", "PyInstaller", SPEC, "--clean", "--noconfirm"],
    capture_output=True,
    text=True,
)
print("STDOUT:\n", result.stdout[-2000:])
print("STDERR:\n", result.stderr[-2000:])
print("Return code:", result.returncode)

src = os.path.join(REPO_ROOT, "dist", EXE_NAME)
if not os.path.isfile(src):
    print("BUILD FAILED: onefile binary not produced at", src)
    sys.exit(2)

sz = os.path.getsize(src)
print("Binary size bytes:", sz)
if sz < MIN_EXE_BYTES:
    print("BUILD FAILED: binary too small (%d B) - not a valid build" % sz)
    sys.exit(3)

print("BUILD OK: valid onefile binary (%d MB)" % (sz // 1_000_000))

# --- DEPLOY: install the freshly built binary as the shortcut target. ---
try:
    os.makedirs(DEPLOY_DIR, exist_ok=True)
    if os.path.normcase(os.path.abspath(src)) != os.path.normcase(
        os.path.abspath(DEPLOY_EXE)
    ):
        shutil.copy2(src, DEPLOY_EXE)
    print("DEPLOYED new build to:", DEPLOY_EXE)
except OSError as e:
    print("BUILD FAILED: could not deploy to", DEPLOY_EXE, "->", e)
    sys.exit(5)


def _create_shortcut(lnk_path, target_exe):
    """Create a Desktop .lnk pointing at target_exe (fallback if missing)."""
    ps = (
        "$ws = New-Object -ComObject WScript.Shell; "
        "$s = $ws.CreateShortcut('%s'); "
        "$s.TargetPath = '%s'; "
        "$s.WorkingDirectory = '%s'; "
        "$s.WindowStyle = 1; "
        "$s.Save()"
    ) % (lnk_path, target_exe, os.path.dirname(target_exe))
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True
    )


# --- Refresh Desktop shortcut (recreate if missing; keep existing if present). ---
try:
    if not os.path.exists(SHORTCUT):
        _create_shortcut(SHORTCUT, DEPLOY_EXE)
        print("CREATED Desktop shortcut:", SHORTCUT)
    else:
        print("Shortcut already exists:", SHORTCUT)
    # Flush Windows Shell icon cache so the new icon shows immediately.
    try:
        ctypes.windll.shell32.SHChangeNotify(0x8000000, 0x1000, None, None)
    except (AttributeError, OSError):
        pass
except OSError as e:
    print("WARN: shortcut refresh issue:", e)

print("DONE")
