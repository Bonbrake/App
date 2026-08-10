import subprocess, os, sys, shutil, json
import PyInstaller  # fail fast if missing

# FIX (2026-08-09): PyInstaller 6.21's isolated subprocess crashes on
# discover_hook_directories() with "TypeError: arg 5 (closure) must be tuple"
# (the function is a closure and the _child.py marshal path mangles it under
# Python 3.11.15). The spec uses hookspath=[] + explicit hiddenimports, so the
# custom-hook scan is a no-op anyway. Replace it with a plain module-level
# (non-closure) function to bypass the broken isolation. Build-only; no effect
# on the frozen app.
try:
    from PyInstaller.building import build_main as _bm
    def _discover_hook_directories_noop():
        return []
    _bm.discover_hook_directories = _discover_hook_directories_noop
except Exception:
    pass

# Repo root = directory containing this script (no hardcoded machine path),
# so the build works from any checkout location.
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO_ROOT)

EXE = os.path.join(REPO_ROOT, "dist", "ComfyUI_Uncensored.exe")
ROLLBACK = os.path.join(REPO_ROOT, "_last_good", "ComfyUI_Uncensored.exe")

# Preserve the previous good build so a failed build never strands the shortcut.
# NOTE: must live OUTSIDE dist/ because we rm -rf dist right after.
if os.path.exists(EXE):
    try:
        os.makedirs(os.path.dirname(ROLLBACK), exist_ok=True)
        shutil.copy2(EXE, ROLLBACK)
        print("Rolled previous EXE back to", ROLLBACK)
    except Exception as e:
        print("WARN: could not preserve previous EXE:", e)

# Clean prior build artifacts so a stale bundle can never be mistaken for success.
subprocess.run(["rm", "-rf", "build", "dist"], shell=True)

# --- Emit build-time metadata so the running app can show a STABLE, meaningful
# build identity (root-cause fix for "my exe isn't the new one").
# In a onefile build sys.executable points at the temp-extracted copy, whose
# mtime is the launch time — useless for identifying the build. We capture the
# real build timestamp/size HERE and bundle it via the spec's datas.
import datetime
BUILD_INFO = os.path.join(REPO_ROOT, "build_info.json")
try:
    build_meta = {
        "build": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "built_with": "PyInstaller %s" % getattr(PyInstaller, "__version__", "?"),
        "repo": os.path.basename(REPO_ROOT),
    }
    with open(BUILD_INFO, "w") as _bf:
        json.dump(build_meta, _bf, indent=2)
    print("Wrote build metadata:", BUILD_INFO)
except Exception as e:
    print("WARN: could not write build metadata:", e)

# Build MUST use Python 3.11 (has PIL/numpy/customtkinter/imageio).
# Using sys.executable (Hermes venv) produces an 18MB broken stub that
# crashes on import at launch because the venv's Tcl/tkinter is broken.
PY311 = os.path.normpath(os.path.expanduser(r"~/AppData/Local/Programs/Python/Python311/python.exe"))
if not os.path.exists(PY311):
    # PRESERVED_LEGACY: Dynamic fallback to 'py -3.11' launcher if default path differs
    try:
        py_path = subprocess.check_output(["py", "-3.11", "-c", "import sys; print(sys.executable)"], text=True).strip()
        if os.path.exists(py_path):
            PY311 = py_path
    except Exception:
        pass

if not os.path.exists(PY311):
    print("BUILD FAILED: Python 3.11 not found at %s" % PY311)
    sys.exit(4)
BUILD_PYTHON = PY311

result = subprocess.run(
    [BUILD_PYTHON, "-m", "PyInstaller",
     os.path.join(REPO_ROOT, "ComfyUI_Uncensored.spec"),
     "--clean", "--noconfirm"],
    capture_output=True, text=True,
)

print("STDOUT:\n", result.stdout[-2000:])
print("STDERR:\n", result.stderr[-2000:])
print("Return code:", result.returncode)

exe = os.path.join(REPO_ROOT, "dist", "ComfyUI_Uncensored.exe")
if not os.path.exists(exe):
    print("BUILD FAILED: exe not produced")
    sys.exit(2)

sz = os.path.getsize(exe)
print("EXE size bytes:", sz)
# A valid frozen tkinter bundle is ~35 MB. The broken stub we replaced was
# 131 KB with no bootloader. Reject anything under 10 MB as a non-bundle.
if sz < 10_000_000:
    print("BUILD FAILED: exe too small (%d B) - not a valid bundle" % sz)
    sys.exit(3)

print("BUILD OK: valid bundle (%d MB)" % (sz // 1_000_000))

# --- DEPLOY: copy the fresh build to the Desktop shortcut target so the user
# actually runs the new exe (root-cause fix for "my exe isn't the new one").
# Additive only: preserves the previous Desktop exe as a dated backup first.
import datetime
DESKTOP = os.path.normpath(os.path.expanduser(r"~/Desktop/ComfyUI_Uncensored.exe"))
DESKTOP_BACKUP = os.path.normpath(
    os.path.expanduser(r"~/Desktop/_exe_backup/ComfyUI_Uncensored_%s.exe"
                       % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
if os.path.exists(DESKTOP):
    try:
        os.makedirs(os.path.dirname(DESKTOP_BACKUP), exist_ok=True)
        shutil.copy2(DESKTOP, DESKTOP_BACKUP)
        print("Backed up previous Desktop exe to", DESKTOP_BACKUP)
    except Exception as e:
        print("WARN: could not back up previous Desktop exe:", e)
try:
    shutil.copy2(exe, DESKTOP)
    print("DEPLOYED new build to Desktop:", DESKTOP)
except Exception as e:
    print("WARN: could not deploy to Desktop (is the exe running?):", e)
