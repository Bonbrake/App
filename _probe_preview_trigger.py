#!/usr/bin/env python3
"""PINNED: exact widget that segfaults _build_main + _build_preview_pane combo.

Proves _load_recent_into_preview's CTkScrollableFrame + thumbnails is the trigger."""
import os, sys, traceback
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
import customtkinter as ctk
import ComfyUI_App as A
from ComfyUI_App import (BG_APP, BG_CARD_ALT, BORDER, BRAND, BRAND_HOVER, TEXT,
                         DROPDOWN_FG, DROPDOWN_TEXT, DROPDOWN_HOVER, ACCENT2,
                         ACCENT2_HOVER, ToolTip, TOOLTIPS, MODELS, PRESETS)

root = ctk.CTk(); root.geometry("1280x1120")

app = A.ComfyUIApp.__new__(A.ComfyUIApp)
app.root = root
for n, kw in [("FONT_LOGO", dict(size=22, weight="bold")), ("FONT_LOGO_SUB", dict(size=13)),
              ("FONT_NORMAL", dict(size=12)), ("FONT_NORMAL_BOLD", dict(size=12, weight="bold")),
              ("FONT_SMALL", dict(size=11)), ("FONT_SMALL_BOLD", dict(size=11, weight="bold"))]:
    setattr(app, n, ctk.CTkFont(**kw))
app.FONT_MONO = ctk.CTkFont(family="Consolas", size=11)
app.vars = {}; app.current_tab = "txt2img"; app._active_view = "generate"; app.input_image_path = None
app._init_vars()

app._build_sidebar()
app._build_main()
root.update_idletasks(); root.update()
print("built up to tabview.set('Text to Image')"); sys.stdout.flush()

# NOW build preview (this is what segfaults on scaling)
app._build_preview_pane()
root.update_idletasks(); root.update()
print("preview pane built"); sys.stdout.flush()

# load recent populates thumbnails into the scrollable frame
app._load_recent_into_preview()
root.update_idletasks(); root.update()
print("load_recent done, widget count:", sum(len(v) for v in
      __import__('customtkinter.windows.widgets.scaling.scaling_tracker', fromlist=['ScalingTracker']).ScalingTracker.window_widgets_dict.values()))

ctk.set_widget_scaling(1.1)
print("set_widget_scaling returned")
root.update_idletasks(); root.update()
print("SURVIVED - THIS COMBINATION IS THE TRIGGER")
root.destroy()