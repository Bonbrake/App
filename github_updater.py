"""
github_updater.py - Online GitHub Live Auto-Updater for ComfyUIX Pro & Matrix HUD
Checks for updates from official GitHub (Bonbrake/ComfyUIX) and applies
script patches or installer downloads in 1-click.
"""
import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.error
import threading

DEFAULT_REPOS = [
    {"name": "Bonbrake ComfyUIX (Official)", "repo": "Bonbrake/ComfyUIX", "branch": "main"},
]

TRACKED_SCRIPTS = [
    "config.py",
    "ComfyUI_App.py",
    "glass.py",
    "model_downloader.py",
    "gallery.py",
    "hermes_app.py",
    "github_updater.py",
    "qa_suite.py",
    "multi_angle_debug.py",
    "AUDIT_PLAN_AND_SPECIFICATION.md",
    "comfyui_desktop/__init__.py",
    "comfyui_desktop/ws_client.py",
    "comfyui_desktop/inpaint_canvas.py",
    "comfyui_desktop/gpu_doctor.py",
    "comfyui_desktop/browser_doctor.py",
    "comfyui_desktop/shortcut_manager.py",
    "comfyui_desktop/orphan_reap.py",
    "comfyui_desktop/backend_manager.py",
    "comfyui_desktop/diagnostics.py",
]

def get_local_build_info():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    info_path = os.path.join(repo_dir, "build_info.json")
    if os.path.isfile(info_path):
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"build": "v5.0.0-Matrix", "commit": "local", "last_check": 0}

def save_local_build_info(info):
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    info_path = os.path.join(repo_dir, "build_info.json")
    try:
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)
    except Exception:
        pass

def check_for_updates(repo="Bonbrake/ComfyUIX", branch="main"):
    """
    Check GitHub REST API for latest commits and releases.
    Returns dict with update status and metadata.
    """
    res = {
        "success": False,
        "has_update": False,
        "repo": repo,
        "branch": branch,
        "latest_sha": None,
        "latest_msg": None,
        "latest_date": None,
        "release_tag": None,
        "release_url": None,
        "error": None,
    }
    headers = {"User-Agent": "ComfyUIX-Updater/5.0.0"}
    
    # 1. Check latest commit on branch
    commit_url = f"https://api.github.com/repos/{repo}/commits/{branch}"
    try:
        req = urllib.request.Request(commit_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                sha = data.get("sha", "")[:7]
                msg = data.get("commit", {}).get("message", "").split("\n")[0]
                date = data.get("commit", {}).get("author", {}).get("date", "")
                res["latest_sha"] = sha
                res["latest_msg"] = msg
                res["latest_date"] = date
                res["success"] = True
                
                local_info = get_local_build_info()
                if local_info.get("commit") != sha and local_info.get("commit") != "local":
                    res["has_update"] = True
    except Exception as e:
        res["error"] = str(e)
        
    # 2. Check latest release tag
    release_url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(release_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                rel = json.loads(resp.read().decode("utf-8"))
                res["release_tag"] = rel.get("tag_name")
                res["release_name"] = rel.get("name")
                res["release_url"] = rel.get("html_url")
                for asset in rel.get("assets", []):
                    if asset.get("name", "").endswith(".exe"):
                        res["installer_url"] = asset.get("browser_download_url")
                        res["installer_size"] = asset.get("size")
    except Exception:
        pass
        
    return res

def apply_script_update(repo="Bonbrake/ComfyUIX", branch="main", progress_callback=None):
    """
    Download and apply raw Python script updates from GitHub into local application directories.
    """
    raw_base = f"https://raw.githubusercontent.com/{repo}/{branch}/"
    headers = {"User-Agent": "ComfyUIX-Updater/5.0.0"}
    
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dest_dirs = [src_dir]
    local_app_comfy = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "ComfyUIX")
    if os.path.isdir(local_app_comfy) and local_app_comfy not in dest_dirs:
        dest_dirs.append(local_app_comfy)
    
    updated_files = []
    total = len(TRACKED_SCRIPTS)
    
    for idx, fname in enumerate(TRACKED_SCRIPTS):
        if progress_callback:
            progress_callback(f"Downloading {fname} ({idx+1}/{total})...", (idx / total))
        file_url = raw_base + fname
        try:
            req = urllib.request.Request(file_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    content = resp.read()
                    # Write to workspace
                    local_path = os.path.join(src_dir, fname)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, "wb") as f:
                        f.write(content)
                    # Sync to destination directories
                    for d in dest_dirs:
                        if os.path.isdir(d):
                            target = os.path.join(d, fname)
                            os.makedirs(os.path.dirname(target), exist_ok=True)
                            with open(target, "wb") as f:
                                f.write(content)
                    updated_files.append(fname)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Warning: {fname} download failed: {e}", (idx / total))
                
    # Update local build info with current time & commit
    check_meta = check_for_updates(repo, branch)
    info = get_local_build_info()
    info["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if check_meta.get("latest_sha"):
        info["commit"] = check_meta["latest_sha"]
    save_local_build_info(info)
    
    if progress_callback:
        progress_callback(f"✅ Successfully updated {len(updated_files)} files live!", 1.0)
        
    return {
        "success": len(updated_files) > 0,
        "files_updated": updated_files,
        "commit": info.get("commit"),
    }

def restart_app_with_session(app_instance=None):
    """Snapshot current active workspace session and seamlessly restart the desktop app."""
    if app_instance and hasattr(app_instance, "_snapshot_session_state"):
        try:
            app_instance._snapshot_session_state()
        except Exception as e:
            pass
    
    # Launch new process
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ComfyUI_App.py")
    if os.path.isfile(main_script):
        import subprocess
        subprocess.Popen([sys.executable, main_script])
        if app_instance and hasattr(app_instance, "root") and app_instance.root:
            try:
                app_instance.root.after(100, app_instance._force_quit)
            except Exception:
                sys.exit(0)
        else:
            sys.exit(0)

if __name__ == "__main__":
    print("=" * 60)
    print(" 🌐 COMFYUIX ONLINE GITHUB UPDATER")
    print("=" * 60)
    print("[*] Checking for updates on Bonbrake/ComfyUIX...")
    up = check_for_updates()
    print("Result:", json.dumps(up, indent=2))
    if up.get("latest_sha"):
        print(f"Latest GitHub Commit: {up['latest_sha']} - {up['latest_msg']}")
        print("[*] Applying live update...")
        res = apply_script_update(progress_callback=lambda msg, pct: print(f"[{int(pct*100)}%] {msg}"))
        print("Update Result:", res)
    print("=" * 60)
