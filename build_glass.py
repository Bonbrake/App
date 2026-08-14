"""Build + deploy the SHIPPING glass app (main.py -> ComfyUIX.exe onedir).

This is the binary the maintainer actually launches (Desktop shortcut ComfyUIX.lnk points at
C:\ComfyUI-Desktop\ComfyUIX\ComfyUIX.exe). Rebuilds with the gallery-freeze fix and the
Debug sidebar view, then deploys onedir to C:\ComfyUI-Desktop\ComfyUIX, replacing the
running build only after a successful build (previous build is backed up first).

Usage:  python build_glass.py
"""
import subprocess, os, sys, shutil, json, datetime, struct, ctypes
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

DEPLOY_DIR = os.path.join(REPO_ROOT, "ComfyUIX")
ROLLBACK = os.path.join(REPO_ROOT, "_last_good_glass")
SHORTCUT = os.path.join(os.path.expanduser("~/Desktop"), "ComfyUIX.lnk")

# --- Emit build metadata so the running app can show a STABLE build identity. ---
BUILD_INFO = os.path.join(REPO_ROOT, "build_info.json")
try:
    build_meta = {
        "build": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "built_with": "PyInstaller %s" % getattr(PyInstaller, "__version__", "?"),
        "repo": os.path.basename(REPO_ROOT),
        "target": "ComfyUIX (main.py)",
    }
    with open(BUILD_INFO, "w") as _bf:
        json.dump(build_meta, _bf, indent=2)
    print("Wrote build metadata:", BUILD_INFO)
except Exception as e:
    print("WARN: could not write build metadata:", e)

# Build MUST use a Python 3.11 with PIL/numpy/customtkinter/tkinter/PyInstaller.
# The proven Aug-12 pipeline used the Hermes agent venv (sys.executable); prefer it,
# fall back to the on-disk Python311 install if the venv lacks PyInstaller.
PY311 = os.path.normpath(os.path.expanduser(r"~/AppData/Local/Programs/Python/Python311/python.exe"))
def _has_pyinstaller(py):
    try:
        subprocess.run([py, "-c", "import PyInstaller"], capture_output=True, text=True, check=True)
        return True
    except Exception:
        return False
if _has_pyinstaller(sys.executable):
    BUILD_PY = sys.executable
elif _has_pyinstaller(PY311):
    BUILD_PY = PY311
else:
    BUILD_PY = None
if not BUILD_PY:
    print("BUILD FAILED: no Python 3.11 with PyInstaller found (tried %s and %s)" % (sys.executable, PY311))
    sys.exit(4)
print("Using build interpreter:", BUILD_PY)

# Preserve the previous good deploy so a failed build never strands the shortcut.
if os.path.isdir(DEPLOY_DIR):
    try:
        os.makedirs(ROLLBACK, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = os.path.join(ROLLBACK, "ComfyUIX_%s" % stamp)
        shutil.copytree(DEPLOY_DIR, bak)
        print("Rolled previous deploy back to", bak)
    except Exception as e:
        print("WARN: could not preserve previous deploy:", e)

# Clean prior build artifacts so a stale bundle can never be mistaken for success.
subprocess.run(["rm", "-rf", "build", "dist"], shell=True)

result = subprocess.run(
    [BUILD_PY, "-m", "PyInstaller",
     os.path.join(REPO_ROOT, "ComfyUIX.spec"),
     "--clean", "--noconfirm"],
    capture_output=True, text=True,
)
print("STDOUT:\n", result.stdout[-2000:])
print("STDERR:\n", result.stderr[-2000:])
print("Return code:", result.returncode)

src = os.path.join(REPO_ROOT, "dist", "ComfyUIX")
if not os.path.isdir(src):
    print("BUILD FAILED: onedir bundle not produced at", src)
    sys.exit(2)

# A valid frozen tkinter onedir bundle is ~150+ MB. Reject anything implausibly small.
sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(src) for f in fs)
print("Bundle size bytes:", sz)
if sz < 80_000_000:
    print("BUILD FAILED: bundle too small (%d B) - not a valid build" % sz)
    sys.exit(3)

print("BUILD OK: valid onedir bundle (%d MB)" % (sz // 1_000_000))

# --- DEPLOY: replace the running onedir build (the maintainer's actual shortcut target). ---
try:
    if os.path.isdir(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR)
    shutil.copytree(src, DEPLOY_DIR)
    print("DEPLOYED new build to:", DEPLOY_DIR)
except Exception as e:
    print("BUILD FAILED: could not deploy to", DEPLOY_DIR, "->", e)
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
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)


# --- Refresh Desktop shortcut (recreate if missing; keep existing if present). ---
try:
    if not os.path.exists(SHORTCUT):
        _create_shortcut(SHORTCUT, os.path.join(DEPLOY_DIR, "ComfyUIX.exe"))
        print("CREATED Desktop shortcut:", SHORTCUT)
    else:
        print("Shortcut already exists:", SHORTCUT)
    # Flush Windows Shell icon cache so the new icon shows immediately.
    try:
        ctypes.windll.shell32.SHChangeNotify(0x8000000, 0x1000, None, None)
    except Exception:
        pass
except Exception as e:
    print("WARN: shortcut refresh issue:", e)

print("DONE")
