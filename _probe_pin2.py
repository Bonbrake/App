"""Run the REAL _build_main with selected internals stubbed to find the
segfault contributor. Usage: _probe_pin2.py <stub>
"""
import os, sys, traceback
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
import customtkinter as ctk
import ComfyUI_App as A

stub = sys.argv[1]

if stub in ("no_ontab", "no_both"):
    A.ComfyUIApp._on_tab = lambda self, name=None: None
if stub in ("no_preview", "no_both"):
    A.ComfyUIApp._build_preview_pane = lambda self: None
if stub == "no_tooltips":
    A.ToolTip = lambda *a, **k: None
if stub == "no_segoverride":
    _orig = A.ComfyUIApp._build_main
if stub == "no_recent":
    A.ComfyUIApp._load_recent_into_preview = lambda self: None

root = ctk.CTk(); root.geometry("1280x1120")
app = A.ComfyUIApp.__new__(A.ComfyUIApp)
app.root = root
for n, kw in [("FONT_LOGO", dict(size=22, weight="bold")), ("FONT_LOGO_SUB", dict(size=13)),
              ("FONT_NORMAL", dict(size=12)), ("FONT_NORMAL_BOLD", dict(size=12, weight="bold")),
              ("FONT_SMALL", dict(size=11)), ("FONT_SMALL_BOLD", dict(size=11, weight="bold"))]:
    setattr(app, n, ctk.CTkFont(**kw))
app.FONT_MONO = ctk.CTkFont(family="Consolas", size=11)
app.vars = {}
app.current_tab = "txt2img"
app._active_view = "generate"
app.input_image_path = None
app._init_vars()

try:
    app._build_main()
except Exception:
    print("BUILD ERR:\n" + traceback.format_exc()[-600:])

root.update_idletasks(); root.update()
print("stub=%s built" % stub); sys.stdout.flush()
ctk.set_widget_scaling(1.1)
print("  returned"); sys.stdout.flush()
root.update_idletasks(); root.update()
print("  SURVIVED stub=%s" % stub); sys.stdout.flush()
root.destroy()
print("DONE-OK")
