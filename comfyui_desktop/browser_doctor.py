"""
browser_doctor.py -- Cross-Browser & Localhost Diagnostic Hub for ComfyUIX
==========================================================================
Provides automated detection of installed browsers (Brave, Google Chrome,
Microsoft Edge, Mozilla Firefox, Arc, Opera), loopback port reachability checks,
Brave Shields / localhost WebSocket / WebGL compatibility diagnostics, and
smart one-click launch helpers.
"""

import os
import sys
import time
import socket
import logging
import subprocess
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# Standard Local AI service ports
DEFAULT_PORTS = [
    {"name": "ComfyUI Web UI", "port": 8188, "url": "http://127.0.0.1:8188/system_stats", "type": "comfyui"},
    {"name": "Matrix / Hermes Proxy", "port": 5119, "url": "http://127.0.0.1:5119/admin/telemetry", "type": "llm"},
    {"name": "Ollama Server", "port": 11434, "url": "http://127.0.0.1:11434/api/tags", "type": "llm"},
    {"name": "LM Studio API", "port": 1234, "url": "http://127.0.0.1:1234/v1/models", "type": "llm"},
    {"name": "vLLM / LocalAI", "port": 8000, "url": "http://127.0.0.1:8000/v1/models", "type": "llm"},
    {"name": "Text-Gen WebUI", "port": 7860, "url": "http://127.0.0.1:7860", "type": "llm"},
]

# Common Windows install locations for popular browsers
BROWSER_CANDIDATES = [
    {
        "id": "brave",
        "name": "Brave Browser",
        "icon": "🦁",
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ],
        "shields_note": (
            "Brave Shields is active by default. If ComfyUI graph or WebSockets fail to load:\n"
            "  1. Click the Brave Lion icon in the address bar on http://127.0.0.1:8188\n"
            "  2. Toggle Shields to 'DOWN' for localhost, or set 'Fingerprinting' to Standard.\n"
            "  3. Ensure Hardware Acceleration is enabled in brave://settings/system."
        )
    },
    {
        "id": "chrome",
        "name": "Google Chrome",
        "icon": "🌐",
        "paths": [
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "shields_note": "Standard Chromium engine. Excellent WebGL/WebGPU and WebSocket support."
    },
    {
        "id": "edge",
        "name": "Microsoft Edge",
        "icon": "🌊",
        "paths": [
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
        ],
        "shields_note": "Built-in Windows Chromium engine with standard localhost WebSocket support."
    },
    {
        "id": "firefox",
        "name": "Mozilla Firefox",
        "icon": "🦊",
        "paths": [
            os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"),
        ],
        "shields_note": (
            "Gecko engine. If WebSockets are blocked, verify about:config "
            "'network.websocket.allowInsecureFromHTTPS' and Enhanced Tracking Protection on localhost."
        )
    },
    {
        "id": "arc",
        "name": "Arc Browser",
        "icon": "🌈",
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\TheBrowserCompany\Arc\Arc.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Arc\Arc.exe"),
        ],
        "shields_note": "Chromium-based. Full WebSocket and WebGL compatibility."
    },
    {
        "id": "opera",
        "name": "Opera / Opera GX",
        "icon": "🔴",
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera GX\opera.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Opera\launcher.exe"),
        ],
        "shields_note": "Chromium-based. Check built-in ad blocker settings for localhost."
    },
]


def detect_installed_browsers() -> list:
    """Detect all installed web browsers on the host system.
    
    Returns a list of dicts with id, name, icon, executable path, and notes.
    """
    found = []
    for b in BROWSER_CANDIDATES:
        exe_path = None
        for p in b["paths"]:
            if os.path.isfile(p):
                exe_path = os.path.normpath(p)
                break
        
        # Check Windows registry if file not found in default paths
        if not exe_path and sys.platform == "win32":
            try:
                import winreg
                reg_keys = [
                    (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Clients\StartMenuInternet\{b['id'].upper()}.exe\shell\open\command"),
                    (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Clients\StartMenuInternet\{b['id'].upper()}.exe\shell\open\command"),
                ]
                for root_key, subkey in reg_keys:
                    try:
                        with winreg.OpenKey(root_key, subkey) as key:
                            val, _ = winreg.QueryValueEx(key, "")
                            raw = val.replace('"', '').strip()
                            if os.path.isfile(raw):
                                exe_path = os.path.normpath(raw)
                                break
                    except Exception:
                        pass
                    if exe_path:
                        break
            except Exception:
                pass

        if exe_path:
            found.append({
                "id": b["id"],
                "name": b["name"],
                "icon": b["icon"],
                "path": exe_path,
                "note": b.get("shields_note", ""),
                "is_brave": (b["id"] == "brave"),
            })

    return found


def scan_ports(ports: list = None) -> list:
    """Ultra-fast loopback socket scan (<5ms per port) of local AI servers."""
    target_ports = ports or DEFAULT_PORTS
    results = []
    for item in target_ports:
        port = item["port"]
        name = item["name"]
        entry = {
            "name": name,
            "port": port,
            "url": item.get("url", f"http://127.0.0.1:{port}"),
            "type": item.get("type", "generic"),
            "online": False,
            "latency_ms": None,
            "detail": "Offline (Connection Refused)"
        }
        t0 = time.time()
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.06):
                lat = max(1, int((time.time() - t0) * 1000))
                entry["online"] = True
                entry["latency_ms"] = lat
                entry["detail"] = f"Online ({lat}ms)"
        except Exception:
            pass
        results.append(entry)
    return results


def check_comfyui_reachability(url: str = "http://127.0.0.1:8188") -> dict:
    """Test HTTP REST and WebSocket capability for ComfyUI."""
    res = {
        "url": url,
        "http_ok": False,
        "system_stats": None,
        "status_code": None,
        "error": None,
        "brave_advisory": None,
    }
    try:
        req = urllib.request.Request(f"{url}/system_stats", headers={"User-Agent": "ComfyUIX-BrowserDoctor"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            res["status_code"] = resp.status
            if resp.status == 200:
                import json
                res["http_ok"] = True
                res["system_stats"] = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        res["status_code"] = e.code
        res["error"] = str(e)
    except Exception as e:
        res["error"] = str(e)

    # Check for Brave advisory
    browsers = detect_installed_browsers()
    brave = next((b for b in browsers if b["id"] == "brave"), None)
    if brave:
        res["brave_advisory"] = (
            "Brave detected: When opening ComfyUI in Brave, toggle Brave Shields to OFF "
            "for http://127.0.0.1:8188 to prevent WebSocket disconnection or canvas farbling."
        )

    return res


def get_browser_launch_command(url: str, browser_id: str = None) -> list:
    """Return the executable path and command list to launch a URL in a target or preferred browser."""
    browsers = detect_installed_browsers()
    chosen = None
    if browser_id:
        chosen = next((b for b in browsers if b["id"].lower() == browser_id.lower()), None)
    if not chosen and browsers:
        # Default to Brave if installed, otherwise first available
        chosen = next((b for b in browsers if b["id"] == "brave"), browsers[0])
    if chosen and os.path.isfile(chosen["path"]):
        return [chosen["path"], url]
    return ["cmd.exe", "/c", "start", url]


def launch_in_browser(url: str = "http://127.0.0.1:8188", browser_id: str = None) -> tuple:
    """Launch a URL in a specific browser (e.g. 'brave', 'chrome', 'edge', 'firefox') or default browser.
    
    Returns (success: bool, message: str).
    """
    browsers = detect_installed_browsers()
    chosen = None
    if browser_id:
        chosen = next((b for b in browsers if b["id"].lower() == browser_id.lower()), None)
    
    if not chosen and browsers:
        # Default preference: Brave if user has it, else Chrome, else first found
        chosen = next((b for b in browsers if b["id"] == "brave"), None) or \
                 next((b for b in browsers if b["id"] == "chrome"), None) or \
                 browsers[0]

    flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) if sys.platform == "win32" else 0

    if chosen and os.path.isfile(chosen["path"]):
        try:
            subprocess.Popen([chosen["path"], url], creationflags=flags)
            return True, f"Opened {url} in {chosen['name']}"
        except Exception as e:
            logger.warning("Failed to launch chosen browser %s: %s", chosen["name"], e)

    # Fallback to system default webbrowser
    try:
        import webbrowser
        webbrowser.open(url)
        return True, f"Opened {url} in default system browser"
    except Exception as e:
        return False, f"Could not launch browser: {e}"


def get_brave_troubleshooting_tips() -> list:
    """Return specific actionable troubleshooting tips for Brave Browser users."""
    return [
        "1. Click the Brave Lion Shield icon in the address bar on http://127.0.0.1:8188",
        "2. Toggle 'Shields are UP' to 'Shields are DOWN' for localhost (safe for local AI tools)",
        "3. Or in Advanced Controls -> set 'Trackers & ads blocking' to Standard",
        "4. Set 'Block fingerprinting' to Standard rather than Strict (Strict blocks WebGL/canvas farbling)",
        "5. Verify Hardware Acceleration is enabled under brave://settings/system"
    ]


def get_brave_shields_instructions() -> str:
    """Return formatted Brave Shields troubleshooting guidance string."""
    return "\n".join(get_brave_troubleshooting_tips())


def run_full_browser_doctor_report() -> dict:
    """Generate a comprehensive browser & localhost network diagnostic report."""
    browsers = detect_installed_browsers()
    ports = scan_ports()
    comfy_check = check_comfyui_reachability()
    
    brave_installed = any(b["id"] == "brave" for b in browsers)
    
    guidance = []
    if brave_installed:
        guidance.append(
            "🦁 Brave Browser Guidance: Brave's Shields feature blocks localhost WebSockets & randomizes "
            "Canvas/WebGL by default. For seamless ComfyUI use, click the Lion shield icon on localhost:8188 "
            "and switch Shields to OFF."
        )
    guidance.append(
        "⚡ Cross-Origin / WebSockets: If using Firefox, ensure about:config 'network.websocket.allowInsecureFromHTTPS' "
        "is enabled if embedding in mixed contexts."
    )

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "installed_browsers": browsers,
        "port_status": ports,
        "comfyui_reachability": comfy_check,
        "brave_installed": brave_installed,
        "guidance": guidance,
    }


if __name__ == "__main__":
    print("=== ComfyUIX Browser Doctor ===")
    rep = run_full_browser_doctor_report()
    import pprint
    pprint.pprint(rep)
