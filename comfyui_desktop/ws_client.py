"""
ComfyUI Uncensored v5.0 - WebSocket Progress Listener & REST ComfyClient
Handles real-time node execution progress and VRAM memory watchdog.
"""
import time
import json
import logging
import requests
import threading
from comfyui_desktop.config import COMFYUI_URL, COMFYUI_WS_URL

logger = logging.getLogger(__name__)

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
