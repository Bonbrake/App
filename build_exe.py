import subprocess, os, sys, shutil
import PyInstaller  # fail fast if missing

os.chdir(r"C:\ComfyUI-Desktop")

EXE = r"C:\ComfyUI-Desktop\dist\ComfyUI_Uncensored.exe"
ROLLBACK = r"C:\ComfyUI-Desktop\_last_good\ComfyUI_Uncensored.exe"

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

# Build MUST use Python 3.11 (has PIL/numpy/customtkinter/imageio).
# Using sys.executable (Hermes venv) produces an 18MB broken stub that
# crashes on import at launch because the venv's Tcl/tkinter is broken.
PY311 = r"C:\Users\jakeb\AppData\Local\Programs\Python\Python311\python.exe"
if not os.path.exists(PY311):
    print("BUILD FAILED: Python 3.11 not found at %s" % PY311)
    sys.exit(4)
BUILD_PYTHON = PY311

result = subprocess.run(
    [BUILD_PYTHON, "-m", "PyInstaller",
     r"C:\ComfyUI-Desktop\ComfyUI_Uncensored.spec",
     "--clean", "--noconfirm"],
    capture_output=True, text=True,
)

print("STDOUT:\n", result.stdout[-2000:])
print("STDERR:\n", result.stderr[-2000:])
print("Return code:", result.returncode)

exe = r"C:\ComfyUI-Desktop\dist\ComfyUI_Uncensored.exe"
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
