"""
ComfyUI Uncensored v5.0 - Backend Process Manager
Handles python_embeded.exe subprocess lifecycle, PID tracking, single-instance detection, and graceful termination.
"""
import os
import sys
import time
import logging
import requests
import subprocess
from comfyui_desktop.config import COMFYUI_URL, COMFYUI_DIR, PYTHON_PATH

logger = logging.getLogger(__name__)

class BackendManager:
    """Manages the ComfyUI subprocess backend lifecycle with PID tracking and zero zombie processes."""
    def __init__(self, app_callback=None):
        self.process = None
        self.pid = None
        self.server_owned = False
        self.app_callback = app_callback

    def is_server_running(self):
        """Check if ComfyUI is responding on port 8188."""
        try:
            r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def start(self):
        """Start the backend process or connect to an existing single instance."""
        if self.is_server_running():
            self.server_owned = False
            return True, "Connected to existing ComfyUI server"

        if not os.path.exists(PYTHON_PATH):
            return False, "Backend python missing"

        self.server_owned = True
        main_py = os.path.join(COMFYUI_DIR, "main.py")
        args = [
            PYTHON_PATH, main_py,
            "--windows-standalone-build", "--fast",
            "--disable-auto-launch"
        ]
        try:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            self.process = subprocess.Popen(
                args, cwd=COMFYUI_DIR,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            self.pid = self.process.pid
            logger.info("Spawned ComfyUI backend process [PID: %d]", self.pid)

            # Wait for backend readiness (up to 120s)
            for i in range(120):
                time.sleep(1)
                if self.is_server_running():
                    return True, "Server online"
                # PRESERVED_LEGACY: Return early if subprocess exited prematurely
                if self.process and self.process.poll() is not None:
                    code = self.process.poll()
                    return False, f"Server process exited with code {code}"
            return False, "Server start failed - click Restart Backend"
        except Exception as e:
            logger.error("Failed to launch backend subprocess: %s", e)
            return False, f"Backend launch error: {str(e)[:40]}"

    def stop(self):
        """Terminate the backend process cleanly if owned."""
        if self.server_owned and self.process:
            try:
                logger.info("Terminating ComfyUI backend process [PID: %s]", self.pid)
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
            self.pid = None
