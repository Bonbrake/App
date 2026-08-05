"""Isolate the scaling-menu crash. Proves _rebuild_ui leaves the app in a
broken state (destroyed widgets still referenced)."""
import os, sys, traceback
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
import ComfyUI_App as A
import customtkinter as ctk

A.ComfyUIApp._start_backend_threads = lambda self: None
A.ComfyUIApp._start_backend = lambda self: None
A.ComfyUIApp._start_vram_watch = lambda self: None
A.os.startfile = lambda p: None

root = ctk.CTk(); root.geometry("1280x1120")
app = A.ComfyUIApp(root)
root.update_idletasks(); root.update()

def probe(tag):
    """Check whether the right-column views survived the rebuild."""
    for nm in ("_gallery_main", "_settings_main", "main", "sidebar", "tabview",
               "status_label", "preview_big", "gen_btn"):
        o = getattr(app, nm, None)
        if o is None:
            print("   %-16s = MISSING ATTR" % nm); continue
        try:
            print("   %-16s exists=%s mapped=%s" % (nm, o.winfo_exists(), o.winfo_ismapped()))
        except Exception as e:
            print("   %-16s DEAD (%s)" % (nm, type(e).__name__))

print("=== BEFORE scaling change ==="); probe("before")

print("\n=== calling _set_scaling('110%') ===")
try:
    app._set_scaling("110%")
    root.update_idletasks(); root.update()
    print("   returned without exception")
except Exception:
    print(traceback.format_exc())

print("\n=== AFTER scaling change ==="); probe("after")

print("\n=== now click Gallery nav (this is what the user would do) ===")
try:
    app._focus_gallery(); root.update_idletasks(); root.update()
    gm = getattr(app, "_gallery_main", None)
    print("   _gallery_main exists=%s mapped=%s" % (
        gm.winfo_exists() if gm is not None else "None",
        gm.winfo_ismapped() if gm is not None else "None"))
    print("   -> if mapped=False the right column is BLANK for the user")
except Exception:
    print(traceback.format_exc())

print("\n=== _update_cursors_and_canvases direct ===")
try:
    app._update_cursors_and_canvases(); print("   ok")
except Exception:
    print("   " + traceback.format_exc().strip().split("\n")[-1])

print("\n=== inspect _apply_cursor_style assumption ===")
import inspect
print(inspect.getsource(A.ComfyUIApp._apply_cursor_style))
print(inspect.getsource(A.ComfyUIApp._update_cursors_and_canvases))
root.destroy()
print("DONE-OK")
