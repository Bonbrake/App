"""Bisect WHICH build phase introduces the set_widget_scaling segfault.
Each stage runs in its own subprocess: exit 0 = safe, exit 139 = segfault.
Usage: _probe_bisect.py <stage>
"""
import os, sys, traceback
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
import customtkinter as ctk
import ComfyUI_App as A

A.ComfyUIApp._start_backend_threads = lambda self: None
A.ComfyUIApp._start_backend = lambda self: None
A.ComfyUIApp._start_vram_watch = lambda self: None
A.os.startfile = lambda p: None

stage = sys.argv[1]
root = ctk.CTk()
root.geometry("1280x1120")

# Build the object WITHOUT running __init__'s build sequence.
app = A.ComfyUIApp.__new__(A.ComfyUIApp)
app.root = root
app.FONT_LOGO = ctk.CTkFont(size=22, weight="bold")
app.FONT_LOGO_SUB = ctk.CTkFont(size=13)
app.FONT_NORMAL = ctk.CTkFont(size=12)
app.FONT_NORMAL_BOLD = ctk.CTkFont(size=12, weight="bold")
app.FONT_SMALL = ctk.CTkFont(size=11)
app.FONT_SMALL_BOLD = ctk.CTkFont(size=11, weight="bold")
app.FONT_MONO = ctk.CTkFont(family="Consolas", size=11)
app.vars = {}
app.current_tab = "txt2img"
app._active_view = "generate"
app.input_image_path = None
app._init_vars()
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)

built = []
try:
    if stage in ("sidebar", "main", "tabs", "preview", "sbbtn", "full"):
        app._build_sidebar(); built.append("sidebar")
    if stage in ("main", "tabs", "preview", "sbbtn", "full"):
        app._build_main(); built.append("main")
    if stage in ("tabs", "preview", "sbbtn", "full"):
        app._build_txt2img_tab(); built.append("txt2img")
        app._build_img2img_tab(); built.append("img2img")
        app._build_upscale_tab(); built.append("upscale")
    if stage in ("preview", "sbbtn", "full"):
        app._build_preview_pane(); built.append("preview")
    if stage in ("sbbtn", "full"):
        app._build_sidebar_buttons(); built.append("sidebar_buttons")
    if stage == "full":
        app._build_status_bar(); built.append("status_bar")
except Exception:
    print("BUILD ERROR at stage %s:\n%s" % (stage, traceback.format_exc()))

root.update_idletasks(); root.update()
print("stage=%-10s built=%s" % (stage, built))
sys.stdout.flush()

print("  calling set_widget_scaling(1.1)...")
sys.stdout.flush()
ctk.set_widget_scaling(1.1)
print("  call returned")
sys.stdout.flush()
root.update_idletasks(); root.update()
print("  SURVIVED stage=%s" % stage)
sys.stdout.flush()
root.destroy()
print("DONE-OK")
