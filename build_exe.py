import subprocess, os, sys, shutil, json
import PyInstaller  # fail fast if missing

# FIX: PyInstaller 6.21 isolation fix
try:
    from PyInstaller.building import build_main as _bm
    def _discover_hook_directories_noop():
        return []
    _bm.discover_hook_directories = _discover_hook_directories_noop
except Exception:
    pass

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO_ROOT)

EXE = os.path.join(REPO_ROOT, "dist", "ComfyUIX.exe")
ROLLBACK = os.path.join(REPO_ROOT, "_last_good", "ComfyUIX.exe")

# Preserve the previous good build
if os.path.exists(EXE):
    try:
        os.makedirs(os.path.dirname(ROLLBACK), exist_ok=True)
        shutil.copy2(EXE, ROLLBACK)
        print("Rolled previous EXE back to", ROLLBACK)
    except Exception as e:
        print("WARN: could not preserve previous EXE:", e)

# Clean prior build artifacts
subprocess.run(["rm", "-rf", "build", "dist"], shell=True)

# Build metadata
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

BUILD_PYTHON = sys.executable
for _cand in [sys.executable,
              os.path.normpath(os.path.expanduser(r"~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")),
              os.path.normpath(os.path.expanduser(r"~/AppData/Local/Programs/Python/Python311/python.exe"))]:
    if os.path.exists(_cand):
        try:
            res = subprocess.run([_cand, "-c", "import PyInstaller, av; print('OK')"], capture_output=True, text=True)
            if "OK" in res.stdout:
                BUILD_PYTHON = _cand
                break
        except Exception:
            pass

print("Using build Python:", BUILD_PYTHON)

result = subprocess.run(
    [BUILD_PYTHON, "-m", "PyInstaller",
     os.path.join(REPO_ROOT, "ComfyUI_Uncensored.spec"),
     "--clean", "--noconfirm"],
    capture_output=True, text=True,
)

print("STDOUT:\n", result.stdout[-2000:])
print("STDERR:\n", result.stderr[-2000:])
print("Return code:", result.returncode)

exe = os.path.join(REPO_ROOT, "dist", "ComfyUIX.exe")
if not os.path.exists(exe):
    print("BUILD FAILED: exe not produced")
    sys.exit(2)

sz = os.path.getsize(exe)
print("EXE size bytes:", sz)
if sz < 10_000_000:
    print("BUILD FAILED: exe too small (%d B) - not a valid bundle" % sz)
    sys.exit(3)

print("BUILD OK: valid bundle (%d MB)" % (sz // 1_000_000))

# --- BUILD OFFICIAL INNO SETUP INSTALLER ---
iscc_candidates = [
    os.path.normpath(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    shutil.which("ISCC.exe") or "",
]
iscc_exe = next((c for c in iscc_candidates if c and os.path.exists(c)), None)

installer_exe = os.path.join(REPO_ROOT, "dist", "ComfyUIX_Setup.exe")
iss_script = os.path.join(REPO_ROOT, "ComfyUIX_Setup.iss")

if iscc_exe and os.path.exists(iss_script):
    print(f"Building official Windows installer with {iscc_exe}...")
    res_iscc = subprocess.run([iscc_exe, iss_script], capture_output=True, text=True)
    if res_iscc.returncode == 0 and os.path.exists(installer_exe):
        inst_sz = os.path.getsize(installer_exe)
        print(f"INSTALLER BUILD OK: {installer_exe} ({inst_sz // 1_000_000} MB)")
    else:
        print("WARN: Installer build failed:\n", res_iscc.stderr or res_iscc.stdout)
else:
    print("NOTE: Inno Setup compiler ISCC.exe not found; skipped setup installer build.")

# --- DEPLOY: copy fresh ComfyUIX.exe build to target application directories ---
import win32com.client

installed_exe = os.path.normpath(os.path.expandvars(r"%LOCALAPPDATA%\Programs\ComfyUIX\ComfyUIX.exe"))
app_targets = [
    r"C:\ComfyUI-Desktop\ComfyUIX.exe",
    installed_exe,
]

for target_exe in app_targets:
    try:
        if os.path.exists(target_exe):
            bak = os.path.normpath(
                os.path.expanduser(r"~/Desktop/_exe_backup/ComfyUIX_%s.exe"
                                   % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
            os.makedirs(os.path.dirname(bak), exist_ok=True)
            shutil.copy2(target_exe, bak)
        os.makedirs(os.path.dirname(target_exe), exist_ok=True)
        shutil.copy2(exe, target_exe)
        print("DEPLOYED fresh build to application directory:", target_exe)
    except Exception as e:
        print("WARN: could not deploy to %s:" % target_exe, e)

# Clean up raw EXE on Desktop (we never want a raw exe sitting loose on Desktop)
desktop = os.path.normpath(os.path.expanduser("~/Desktop"))
desktop_raw_exe = os.path.join(desktop, "ComfyUIX.exe")
if os.path.exists(desktop_raw_exe):
    try:
        os.remove(desktop_raw_exe)
        print("CLEANED loose EXE from Desktop (Desktop only contains shortcut):", desktop_raw_exe)
    except Exception as e:
        print("WARN: could not remove loose EXE from Desktop:", e)

# Deploy Installer (.exe setup) to Desktop and old1/2polish for user testing & backup
if os.path.exists(installer_exe):
    installer_targets = [
        os.path.join(desktop, "ComfyUIX_Setup.exe"),
        os.path.join(desktop, "old1", "2polish", "ComfyUIX_Setup.exe"),
    ]
    for d_inst in installer_targets:
        try:
            os.makedirs(os.path.dirname(d_inst), exist_ok=True)
            shutil.copy2(installer_exe, d_inst)
            print("DEPLOYED official installer to:", d_inst)
        except Exception as e:
            print("WARN: could not copy installer to %s:" % d_inst, e)

# Create/update Desktop shortcut (ComfyUIX.lnk)
try:
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut_path = os.path.join(desktop, "ComfyUIX.lnk")
    shortcut = shell.CreateShortCut(shortcut_path)
    primary_exe = installed_exe if os.path.exists(installed_exe) else r"C:\ComfyUI-Desktop\ComfyUIX.exe"
    shortcut.Targetpath = primary_exe
    shortcut.WorkingDirectory = os.path.dirname(primary_exe)
    shortcut.IconLocation = os.path.join(REPO_ROOT, "assets", "app_icon.ico")
    shortcut.save()
    print("UPDATED Desktop shortcut:", shortcut_path)
except Exception as e:
    print("WARN: could not create Desktop shortcut:", e)


print("\n--- ALL TASKS COMPLETE ---")
