"""
ComfyUI Uncensored v5.0 - Backend Lifecycle & REST/WebSocket Engine
Manages python_embeded.exe backend process, PID tracking, VRAM monitoring, and ComfyUI REST API client.
"""
import os
import sys
import time
import json
import logging
import requests
import subprocess
import threading
from config import COMFYUI_URL, COMFYUI_DIR, PYTHON_PATH, LOG_DIR

logger = logging.getLogger(__name__)

class BackendManager:
    """Manages the ComfyUI subprocess backend lifecycle with PID tracking and zero zombie processes."""
    def __init__(self, app_callback=None):
        self.process = None
        self.pid = None
        self.server_owned = False
        self.app_callback = app_callback

    def is_server_running(self):
        """Check if ComfyUI is already responding on port 8188."""
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
            self.process = subprocess.Popen(
                args, cwd=COMFYUI_DIR,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.pid = self.process.pid
            logger.info("Spawned ComfyUI backend process [PID: %d]", self.pid)

            # Wait for backend readiness (up to 120s)
            for i in range(120):
                time.sleep(1)
                if self.is_server_running():
                    return True, "Server online"
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

class ComfyClient:
    """REST API Client for ComfyUI Endpoints."""
    @staticmethod
    def post_prompt(workflow):
        payload = {"prompt": workflow, "client_id": "hermes_comfyui_uncensored"}
        r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
        return r

    @staticmethod
    def post_interrupt():
        try:
            return requests.post(COMFYUI_URL + "/interrupt", timeout=5)
        except Exception:
            return None

    @staticmethod
    def purge_vram():
        """Invoke ComfyUI /free endpoint to clear CUDA memory cache and unload idle models."""
        try:
            r = requests.post(COMFYUI_URL + "/free", json={"unload_models": True, "free_memory": True}, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def get_system_stats():
        try:
            r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    @staticmethod
    def get_history():
        try:
            r = requests.get(COMFYUI_URL + "/history", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

class VRAMWatchdog:
    """Monitors VRAM usage and performs smart automatic memory purging when critical."""
    def __init__(self, status_callback, get_threshold_func):
        self.status_callback = status_callback
        self.get_threshold_func = get_threshold_func
        self._running = True

    def is_critical(self, threshold=None):
        try:
            val = self.get_threshold_func() if self.get_threshold_func else "90%"
            if "Disabled" in val:
                return False
            if threshold is None:
                if "95%" in val: threshold = 0.95
                elif "85%" in val: threshold = 0.85
                elif "80%" in val: threshold = 0.80
                else: threshold = 0.90

            stats = ComfyClient.get_system_stats()
            if not stats or not stats.get("devices"):
                return False

            d = stats["devices"][0]
            total = d.get("vram_total", 0) or 0
            free = d.get("vram_free", 0) or 0
            if total <= 0:
                return False

            used_pct = 1 - (free / total)
            if used_pct > threshold:
                # Smart VRAM Recovery: Automatically attempt /free to clear PyTorch cache
                ComfyClient.purge_vram()
                time.sleep(0.5)
                stats2 = ComfyClient.get_system_stats()
                if stats2 and stats2.get("devices"):
                    d2 = stats2["devices"][0]
                    tot2 = d2.get("vram_total", 0) or 0
                    fr2 = d2.get("vram_free", 0) or 0
                    if tot2 > 0:
                        used_pct = 1 - (fr2 / tot2)
            return used_pct > threshold
        except Exception:
            return False

    def stop(self):
        self._running = False
