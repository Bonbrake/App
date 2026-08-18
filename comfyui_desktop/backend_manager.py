"""
ComfyUI Uncensored v5.0 - Backend Process Manager
Handles python_embeded.exe subprocess lifecycle, PID tracking, single-instance detection,
smart GPU auto-tuning, Windows Job Object kernel-level orphan protection, and graceful termination.
"""
import os
import sys
import time
import shutil
import logging
import requests
import subprocess
from comfyui_desktop.config import COMFYUI_URL, COMFYUI_DIR, PYTHON_PATH
from comfyui_desktop import gpu_doctor

try:
    from orphan_reap import WindowsJobObject, reap_process_tree, reap_if_orphan
except ImportError:
    try:
        from comfyui_desktop.orphan_reap import WindowsJobObject, reap_process_tree, reap_if_orphan
    except ImportError:
        WindowsJobObject = None
        reap_process_tree = None
        reap_if_orphan = None

logger = logging.getLogger(__name__)


def resolve_valid_python(preferred_path: str = None) -> str:
    """Find a usable Python interpreter for ComfyUI backend subprocess."""
    cands = [
        preferred_path,
        PYTHON_PATH,
        os.path.join(COMFYUI_DIR, "..", "python_embeded", "python.exe"),
        os.path.join(COMFYUI_DIR, "python_embeded", "python.exe"),
        r"C:\ComfyUI-Desktop\python_embeded\python.exe",
        os.path.normpath(os.path.expanduser(r"~/AppData/Local/Programs/Python/Python311/python.exe")),
        r"C:\Python311\python.exe",
        sys.executable,
        shutil.which("python.exe") or "",
        shutil.which("python") or "",
    ]
    for c in cands:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    return sys.executable if not getattr(sys, "frozen", False) else ""


class BackendManager:
    """Manages the ComfyUI subprocess backend lifecycle with PID tracking and zero zombie processes."""
    def __init__(self, app_callback=None):
        self.process = None
        self.pid = None
        self.server_owned = False
        self.app_callback = app_callback
        self.active_gpu_info = gpu_doctor.detect_gpu_hardware()
        self.job = WindowsJobObject() if WindowsJobObject else None

    def is_server_running(self):
        """Check if ComfyUI is responding on port 8188."""
        try:
            r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def start(self, extra_args: list = None):
        """Start the backend process with smart GPU auto-tuning or connect to an existing single instance."""
        # 1. Check if server is already running and responsive
        if self.is_server_running():
            self.server_owned = False
            return True, "Connected to existing ComfyUI server"

        # 2. Check for dead orphan process on port 8188 before spawning
        if reap_if_orphan:
            try:
                reaped = reap_if_orphan(port=8188)
                if reaped:
                    logger.info("Reaped stale orphan process on port 8188")
            except Exception as _e:
                logger.debug("Pre-flight orphan reap notice: %s", _e)

        py_bin = resolve_valid_python(PYTHON_PATH)
        if not py_bin or not os.path.isfile(py_bin):
            return False, "Backend Python interpreter not found"

        main_py = os.path.join(COMFYUI_DIR, "main.py")
        if not os.path.isfile(main_py):
            for cand_main in [
                os.path.join(os.path.dirname(COMFYUI_DIR), "ComfyUI", "main.py"),
                os.path.join(os.getcwd(), "ComfyUI", "main.py"),
                r"C:\ComfyUI-Desktop\ComfyUI\main.py",
            ]:
                if os.path.isfile(cand_main):
                    main_py = cand_main
                    break

        self.server_owned = True
        self.active_gpu_info = gpu_doctor.detect_gpu_hardware()
        
        # Build optimized arguments from GPU doctor
        recommended = list(self.active_gpu_info.get("recommended_args", ["--windows-standalone-build", "--fast", "--disable-auto-launch"]))
        
        args = [py_bin, main_py] + recommended
        if extra_args:
            for ea in extra_args:
                if ea not in args:
                    args.append(ea)

        try:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            if os.name == "nt":
                creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

            wdir = os.path.dirname(main_py) if os.path.isfile(main_py) else COMFYUI_DIR
            self.process = subprocess.Popen(
                args, cwd=wdir,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            self.pid = self.process.pid
            logger.info("Spawned ComfyUI backend process [PID: %d] with args %s", self.pid, args)

            # Assign to Windows Job Object for OS-kernel level lifecycle guarantee
            if self.job and self.pid:
                assigned = self.job.assign(self.pid)
                if assigned:
                    logger.info("Assigned PID %d to WindowsJobObject (KILL_ON_JOB_CLOSE enabled)", self.pid)

            # Wait for backend readiness (up to 120s)
            for i in range(120):
                time.sleep(1)
                if self.is_server_running():
                    return True, "Server online"
                if self.process and self.process.poll() is not None:
                    code = self.process.poll()
                    return False, f"Server process exited with code {code}"
            return False, "Server start timeout - click Restart Backend"
        except Exception as e:
            logger.error("Failed to launch backend subprocess: %s", e)
            return False, f"Backend launch error: {str(e)[:40]}"

    def stop(self):
        """Terminate the backend process cleanly if owned."""
        if self.server_owned and self.pid:
            try:
                logger.info("Terminating ComfyUI backend process [PID: %s]", self.pid)
                if reap_process_tree:
                    reap_process_tree(self.pid, timeout=2.0)
                elif self.process:
                    self.process.terminate()
                    self.process.wait(timeout=2)
            except Exception:
                try:
                    if self.process:
                        self.process.kill()
                except Exception:
                    pass
            self.process = None
            self.pid = None
