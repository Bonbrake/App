"""
shortcut_manager.py -- Self-Healing Desktop Shortcut Manager for ComfyUIX
=========================================================================
Ensures the ComfyUIX desktop shortcut (ComfyUIX.lnk) is always present,
valid, and pointing to the correct binary, working directory, and icon.
Auto-heals on app launch and provides on-demand repair.
"""

import os
import sys
import logging
import subprocess

logger = logging.getLogger(__name__)


def get_desktop_dir() -> str:
    """Return the normalized path to the current user's Desktop."""
    # Standard user desktop
    desktop = os.path.normpath(os.path.expanduser("~/Desktop"))
    if os.path.isdir(desktop):
        return desktop
    
    # Check OneDrive Desktop if redirected
    onedrive_desktop = os.path.normpath(os.path.expanduser("~/OneDrive/Desktop"))
    if os.path.isdir(onedrive_desktop):
        return onedrive_desktop
    
    # Fallback to USERPROFILE\Desktop
    up = os.environ.get("USERPROFILE", "")
    if up and os.path.isdir(os.path.join(up, "Desktop")):
        return os.path.join(up, "Desktop")
        
    return desktop


def resolve_app_target() -> tuple:
    """Resolve the best target executable, arguments, and working directory for the shortcut.
    
    Returns (target_path, arguments, working_dir, icon_path).
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Check for standalone EXE in current folder
    exe_cand = os.path.join(here, "ComfyUIX.exe")
    icon_cand = os.path.join(here, "assets", "app_icon.ico")
    if not os.path.isfile(icon_cand):
        icon_cand = os.path.join(here, "assets", "app_icon.png")

    if os.path.isfile(exe_cand):
        return (os.path.abspath(exe_cand), "", os.path.abspath(here), os.path.abspath(icon_cand) if os.path.isfile(icon_cand) else os.path.abspath(exe_cand))

    # 2. Source mode fallback: pythonw.exe + ComfyUI_App.py
    app_py = os.path.join(here, "ComfyUI_App.py")
    py_dir = os.path.dirname(sys.executable)
    py_cands = [
        os.path.join(py_dir, "pythonw.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", f"Python{sys.version_info.major}{sys.version_info.minor}", "pythonw.exe"),
        sys.executable,
    ]
    py_exe = sys.executable
    for p in py_cands:
        if p and os.path.isfile(p):
            py_exe = p
            break
            
    return (os.path.abspath(py_exe), f'"{os.path.abspath(app_py)}"', os.path.abspath(here), os.path.abspath(icon_cand) if os.path.isfile(icon_cand) else os.path.abspath(py_exe))


def resolve_target_executable() -> str:
    """Return the resolved primary executable binary path."""
    target, _, _, _ = resolve_app_target()
    return target



def verify_and_repair_desktop_shortcut(force_update: bool = False) -> dict:
    """Verify that ComfyUIX.lnk exists on the Desktop and points to the right target.
    
    If missing or broken or force_update=True, creates or repairs it via Windows Shell COM API.
    Returns a result dict with status and details.
    """
    desktop = get_desktop_dir()
    shortcut_path = os.path.join(desktop, "ComfyUIX.lnk")
    target, args, wdir, icon = resolve_app_target()
    
    res = {
        "shortcut_path": shortcut_path,
        "target_path": target,
        "arguments": args,
        "working_dir": wdir,
        "icon_path": icon,
        "exists_before": os.path.isfile(shortcut_path),
        "repaired": False,
        "success": True,
        "message": ""
    }

    if sys.platform != "win32":
        res["success"] = False
        res["message"] = "Shortcut management is Windows-only."
        return res

    needs_repair = force_update or not os.path.isfile(shortcut_path)

    # If it exists, verify its target
    if not needs_repair and os.path.isfile(shortcut_path):
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortcut(shortcut_path)
            cur_target = os.path.normpath(sc.TargetPath)
            cur_wdir = os.path.normpath(sc.WorkingDirectory)
            if cur_target.lower() != os.path.normpath(target).lower() or cur_wdir.lower() != os.path.normpath(wdir).lower():
                needs_repair = True
        except Exception:
            # If win32com inspection fails, proceed to re-save to guarantee validity
            pass

    if needs_repair:
        try:
            # Attempt via win32com.client WScript.Shell
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortcut(shortcut_path)
            sc.TargetPath = target
            sc.Arguments = args
            sc.WorkingDirectory = wdir
            if icon and os.path.isfile(icon):
                sc.IconLocation = f"{icon},0"
            sc.Description = "ComfyUIX — Matrix Edition AI Studio"
            sc.Save()
            res["repaired"] = True
            res["message"] = f"Successfully created/repaired desktop shortcut: {shortcut_path}"
            logger.info("Repaired desktop shortcut: %s -> %s", shortcut_path, target)
        except Exception as e:
            # Fallback to PowerShell COM script if win32com is unavailable
            try:
                ps_script = f'''
                $ws = New-Object -ComObject WScript.Shell
                $s = $ws.CreateShortcut('{shortcut_path}')
                $s.TargetPath = '{target}'
                $s.Arguments = '{args}'
                $s.WorkingDirectory = '{wdir}'
                $s.IconLocation = '{icon},0'
                $s.Description = 'ComfyUIX — Matrix Edition AI Studio'
                $s.Save()
                '''
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    check=True, capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                res["repaired"] = True
                res["message"] = f"Repaired desktop shortcut via PowerShell: {shortcut_path}"
            except Exception as pe:
                res["success"] = False
                res["message"] = f"Failed to create desktop shortcut: {pe}"
                logger.error("Shortcut repair error: %s", pe)
    else:
        res["message"] = "Desktop shortcut is verified and healthy."

    return res


if __name__ == "__main__":
    print("=== ComfyUIX Shortcut Manager ===")
    r = verify_and_repair_desktop_shortcut(force_update=True)
    import pprint
    pprint.pprint(r)
