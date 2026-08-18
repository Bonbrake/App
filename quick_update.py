"""
quick_update.py - Instant Live Update & Script Syncer for ComfyUIX Pro & Matrix HUD
Instantly syncs updated source files to all installed application directories in < 0.1s.
No full PyInstaller rebuild needed!
"""
import os
import shutil
import sys

def sync_all():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    dest_dirs = [
        r"C:\Users\jakeb\AppData\Local\Programs\ComfyUIX",
        r"C:\ComfyUI-Desktop",
        r"C:\LocalCoder",
    ]
    files = ["ComfyUI_App.py", "glass.py", "model_downloader.py", "gallery.py", "hermes_app.py"]
    
    print("=" * 60)
    print(" ⚡ COMFYUIX & MATRIX HUD INSTANT LIVE SYNC")
    print("=" * 60)
    
    total_copied = 0
    for d in dest_dirs:
        if os.path.isdir(d):
            print(f"[*] Syncing to: {d}")
            for f in files:
                src_f = os.path.join(src_dir, f)
                if os.path.isfile(src_f):
                    dst_f = os.path.join(d, f)
                    shutil.copy2(src_f, dst_f)
                    print(f"    ✓ {f}")
                    total_copied += 1
        else:
            print(f"[-] Directory not found (skipping): {d}")
            
    print("=" * 60)
    print(f" ✨ COMPLETE: {total_copied} files updated in < 0.1 seconds!")
    print(" You can now run or restart ComfyUIX / Matrix HUD immediately.")
    print("=" * 60)

if __name__ == "__main__":
    sync_all()
