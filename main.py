"""
ComfyUI Uncensored - Native Windows 11 Desktop App (v5.0 - customtkinter Pro UI)
Wraps official ComfyUI 0.29.0 portable
"""
import os
import sys
import json
import time
import random
import shutil
import threading
import subprocess
import traceback
import datetime
import logging
import tkinter as tk

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter.font as tkfont

import requests
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

from glass import AcrylicBackground, make_gradient, _hue_shift_color

import tkinter as _tk
try:
    from tkinter import ttk as _ttk
except Exception:
    _ttk = None

# ---- Auto-hiding scrollable frame ----
# CTkScrollableFrame defaults to height=200 and its scrollbar is ALWAYS visible,
# which produced the "middle is crunched / can't scroll far enough" bug and a
# permanent scrollbar. This custom frame gives a FULL scroll range (content-sized)
# and an overlay scrollbar that hides when idle or when everything fits.
class AutoHideScrollFrame(ctk.CTkFrame):
    """Scrollable frame with a vertical scrollbar that auto-hides.

    Add children to ``self.inner`` (a CTkFrame that scrolls). The outer frame
    fills its master via grid/sticky. The scrollbar is an overlay that appears
    on hover/scroll and hides after a short idle period (or when content fits).
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._canvas = _tk.Canvas(self, highlightthickness=0,
                                  bg=self._apply_appearance_mode(self.cget("fg_color")))
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._vsb = _ttk.Scrollbar(self, orient="vertical",
                                   command=self._canvas.yview, width=10)
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self.inner = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._win = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<Enter>", lambda e: self._show_bar())
        self._canvas.bind("<Leave>", lambda e: self._schedule_hide())
        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self.inner.bind("<MouseWheel>", self._on_wheel)

        self._hide_after_id = None
        self._vsb.grid_remove()  # hidden until needed

    # ---- appearance ----
    def _apply_appearance_mode(self, color):
        try:
            mode = ctk.get_appearance_mode().lower()
            if isinstance(color, (tuple, list)):
                return color[0] if mode == "light" else color[1]
            elif color in (None, "transparent"):
                return "#FFFFFF" if mode == "light" else "#1A1A24"
            return color
        except Exception:
            return "#FFFFFF" if ctk.get_appearance_mode().lower() == "light" else "#1A1A24"

    def refresh_appearance(self):
        try:
            bg_color = self._apply_appearance_mode(self.cget("fg_color"))
            self._canvas.configure(bg=bg_color)
        except Exception:
            pass

    # ---- geometry ----
    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._update_bar_visibility()

    def _on_canvas_configure(self, event):
        # keep inner frame width synced to canvas width
        self._canvas.itemconfigure(self._win, width=event.width)
        self._update_bar_visibility()

    def _update_bar_visibility(self):
        try:
            if self._canvas.yview() == (0.0, 1.0):
                self._vsb.grid_remove()
            else:
                self._vsb.grid(row=0, column=1, sticky="ns")
        except Exception:
            pass

    # ---- auto-hide ----
    def _show_bar(self):
        try:
            if self._canvas.yview() != (0.0, 1.0):
                self._vsb.grid(row=0, column=1, sticky="ns")
        except Exception:
            pass
        self._cancel_hide()

    def _schedule_hide(self):
        self._cancel_hide()
        self._hide_after_id = self.after(1200, self._do_hide)

    def _cancel_hide(self):
        if self._hide_after_id is not None:
            try:
                self.after_cancel(self._hide_after_id)
            except Exception:
                pass
            self._hide_after_id = None

    def _do_hide(self):
        self._hide_after_id = None
        try:
            if self._canvas.yview() == (0.0, 1.0):
                return
            self._vsb.grid_remove()
        except Exception:
            pass

    def _on_wheel(self, event):
        if self._canvas.yview() == (0.0, 1.0):
            return
        self._show_bar()
        self._canvas.yview("scroll", -int(event.delta / 60), "units")
        self._schedule_hide()


def enable_auto_hide_scrollbar(scrollframe):
    """Hide a CTkScrollableFrame's scrollbar until the user hovers/scrolls.

    The scrollbar reappears on mouse-enter or wheel, and hides again after a
    short idle period (or immediately when content fully fits). Uses the
    private ``_scrollbar`` / ``_parent_canvas`` attributes of CTkScrollableFrame.
    """
    try:
        sb = scrollframe._scrollbar
        cv = scrollframe._parent_canvas
    except Exception:
        return

    def _fits():
        try:
            return cv.yview() == (0.0, 1.0)
        except Exception:
            return True

    def _hide():
        try:
            if not _fits():
                sb.grid_remove()
        except Exception:
            pass

    def _show():
        try:
            if not _fits():
                sb.grid()
        except Exception:
            pass

    def _on_enter(e):
        _show()

    def _on_leave(e):
        if _fits():
            try:
                sb.grid_remove()
            except Exception:
                pass
        else:
            scrollframe.after(1200, _hide)

    # start hidden
    try:
        sb.grid_remove()
    except Exception:
        pass
    cv.bind("<Enter>", _on_enter)
    cv.bind("<Leave>", _on_leave)
    # keep hidden when content fits even after layout
    cv.bind("<Configure>", lambda e: (_hide() if _fits() else None))

    # Force the inner content frame to fill the canvas width. CTkScrollableFrame
    # only syncs this on its own canvas <Configure>, which doesn't always fire on
    # window resize -- leaving the inner frame at its default ~220px width and
    # making every control render narrow with a dead gap on the right ("skinny").
    def _sync_width():
        try:
            w = cv.winfo_width()
            scrollframe.configure(width=w)
            cv.itemconfigure(scrollframe._create_window_id, width=w)
        except Exception:
            pass
    scrollframe.after(60, _sync_width)
    scrollframe.after(400, _sync_width)
    cv.bind("<Configure>", lambda e: (_sync_width(), _hide() if _fits() else None))



try:
    import imageio.v2 as iio
    try:
        import imageio_ffmpeg
        HAS_VIDEO = True
    except Exception:
        HAS_VIDEO = False
except Exception as e:
    HAS_VIDEO = False
    try:
        sys.stderr.write("video support unavailable at import: %s\n" % e)
    except Exception:
        pass  # stderr may be None in frozen EXE


def _resolve_has_video():
    """Resolve video support lazily (works around PyInstaller stripping imageio metadata)."""
    global HAS_VIDEO
    if HAS_VIDEO:
        return True
    try:
        import imageio.v2 as iio
        import imageio_ffmpeg
        HAS_VIDEO = True
        return True
    except Exception:
        HAS_VIDEO = False
        return False


# ---- Paths ----
COMFYUI_DIR = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI"
PYTHON_PATH = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\python_embeded\python.exe"
MAIN_PY = "main.py"
COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\jakeb\Pictures\ComfyUI_Generated"
INPUT_DIR = os.path.join(OUTPUT_DIR, "input")
LOG_DIR = r"C:\Users\jakeb\Logs"
LOG_FILE = os.path.join(LOG_DIR, "ComfyUI_App.log")
HISTORY_FILE = os.path.join(OUTPUT_DIR, "ComfyUI_prompt_history.json")
CKPT_DIR = os.path.join(COMFYUI_DIR, "models", "checkpoints")
ARCHIVE_DIR = os.path.join(COMFYUI_DIR, "models_archive")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CKPT_DIR, exist_ok=True)

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
_log_handler = logging.FileHandler(LOG_FILE)
_log_handler.setLevel(logging.INFO)
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger = logging.getLogger("ComfyUIApp")
logger.handlers.clear()
logger.addHandler(_log_handler)
logger.propagate = False

_orig_info = logger.info
_orig_error = logger.error


def _flush_info(msg, *args):
    _orig_info(msg, *args)


def _flush_error(msg, *args):
    _orig_error(msg, *args)


# ---- Model / Preset data ----
# Font constants will be initialized in __init__ after root window exists

# ---- Models & Presets ----
MODELS = {
    "CyberRealistic XL (Uncensored)": {
        "file": "cyberrealisticXL_v20.safetensors", "value": "cyberrealisticXL_v20.safetensors",
        "w": 768, "h": 768, "steps": 30, "cfg": 6.0, "sampler": "dpmpp_2m", "scheduler": "karras"
    },
    "epiCRealism XL": {
        "file": "epicrealismXL_pure.safetensors", "value": "epicrealismXL_pure.safetensors",
        "w": 768, "h": 768, "steps": 35, "cfg": 6.5,
    },
    "Juggernaut XL": {
        "file": "juggernautXL_ragnarok.safetensors", "value": "juggernautXL_ragnarok.safetensors",
        "w": 1216, "h": 832, "steps": 35, "cfg": 5.0,
    },
    "Pony Diffusion V6 XL": {
        "file": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors", "value": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        "w": 832, "h": 1216, "steps": 25, "cfg": 7.0,
    },
}

PRESETS = {
    "Photoreal Portrait": {
        "model": "epiCRealism XL",
        "prompt": "photorealistic portrait, detailed skin, studio light",
        "neg": "blurry, lowres",
    },
    "Cinematic Wide": {
        "model": "Juggernaut XL",
        "prompt": "cinematic wide shot, dramatic lighting",
        "neg": "blurry, deformed",
    },
    "Anime Character": {
        "model": "Pony Diffusion V6 XL",
        "prompt": "anime style character, vibrant",
        "neg": "realistic, photo",
    },
    "Game Texture": {
        "model": "Pony Diffusion V6 XL",
        "prompt": "game texture, seamless tileable diffuse map, clean flat shading, hand-painted cell-shaded style, consistent pixel density, UV-friendly, no stretching, neutral lighting, game-ready asset",
        "neg": "realistic, photo, photographic, blurry, lowres, distorted seams, stretching, watermark, text, jpeg artifacts",
        "format": "Game Texture (TGA)",
    },
}

SAMPLERS = ["dpmpp_2m", "dpmpp_sde", "euler", "euler_ancestral", "dpmpp_2m_sde", "ddim"]
SCHEDULERS = ["karras", "normal", "simple", "ddim_uniform", "beta"]
UPSCALE_MODELS = ["4x-UltraSharp.pth", "4x_NMKD-Siax_200k.pth", "ESRGAN_4x.pth"]
DEFAULT_NEG = "blurry, lowres, deformed, watermark, text"

# ---- Tooltips ----
TOOLTIPS = {
    "Prompt": ("Prompt", "Describe the image you want. More detail = better result."),
    "Negative Prompt": ("Negative Prompt", "Things to AVOID (blurry, extra limbs, etc)."),
    "Width": ("Width", "Image width in pixels. 768 typical for SDXL portraits."),
    "Height": ("Height", "Image height in pixels. Match your model preset."),
    "Steps": ("Steps", "Denoising steps. 25-40 is the sweet spot for SDXL."),
    "CFG": ("CFG Scale", "How strictly to follow the prompt. 5-8 recommended."),
    "Seed": ("Seed", "Random seed. 0 = random each generation."),
    "Batch": ("Batch Size", "How many images per generation."),
    "Sampler": ("Sampler", "The solver. dpmpp_2m is the best all-rounder."),
    "Scheduler": ("Scheduler", "Noise schedule. karras looks best for most."),
    "Model": ("Model", "Checkpoint. Each is tuned for a style."),
    "Preset": ("Preset", "Pre-configured parameter sets for common scenarios."),
    "Generate": ("Generate", "Start image generation. (Ctrl+E)"),
    "Output Format": ("Output Format", "PNG = standard. Game Texture = PoT TGA for engine import."),
    "Denoise": ("Denoise", "img2img strength. 0.7 = strong change, 0.3 = subtle."),
    "Upscale Model": ("Upscale Model", "ESRGAN model used for 2x/4x upscaling."),
    "Scale": ("Scale", "Upscale factor. 4x looks best on 8GB VRAM."),
    "Input Image": ("Input Image", "Source image for img2img or video-first-frame. Leave blank for txt2img."),
}

# ---- Design System Tokens (High-Contrast Periwinkle / Slate Palette) ----
ctk.set_appearance_mode("system")
ctk.set_widget_scaling(1.0)

BG_APP = ("#F1F5F9", "#0F0F12")
BG_SIDEBAR = ("#E2E8F0", "#14141A")
BG_CARD = ("#FFFFFF", "#1A1A24")
BG_CARD_ALT = ("#F8FAFC", "#22222E")
BORDER = ("#94A3B8", "#2A2A3C")
TEXT = ("#020617", "#F8FAFC")
TEXT_MUTED = ("#334155", "#94A3B8")
BRAND = ("#4338CA", "#6366F1")
BRAND_HOVER = ("#3730A3", "#818CF8")
ACCENT2 = ("#059669", "#10B981")
ACCENT2_HOVER = ("#047857", "#34D399")
DROPDOWN_FG = ("#FFFFFF", "#1E1E2E")
DROPDOWN_TEXT = ("#020617", "#F8FAFC")
DROPDOWN_HOVER = ("#E2E8F0", "#2D2D3F")
TOOLTIP_DELAY = 500
TOOLTIP_HIDE_DELAY = 100


# ---- ToolTip ----
class ToolTip:
    """Hover tooltip — robust CTk 6.0-compatible implementation."""

    def __init__(self, widget, title, description, delay=TOOLTIP_DELAY):
        self.widget = widget
        self.title = title
        self.description = description
        self.delay = delay
        self.tipwindow = None
        self._job = None
        # Bind on the actual event-receiving canvas for CTk composite widgets
        target = self._get_event_target(widget)
        target.bind("<Enter>", self._on_enter, add="+")
        target.bind("<Leave>", self._on_leave, add="+")
        target.bind("<ButtonPress>", self._on_click, add="+")

    @staticmethod
    def _get_event_target(widget):
        """Return the widget that actually receives mouse Enter/Leave events."""
        canvas = getattr(widget, "_canvas", None)
        return canvas if canvas is not None else widget

    def _on_click(self, _event=None):
        self._cancel_pending()
        self._do_hide()

    def _on_enter(self, _event=None):
        """Schedule tooltip to appear after a short delay."""
        if self._job is not None:
            self.widget.after_cancel(self._job)
        self._job = self.widget.after(self.delay, self._do_show)

    def _on_leave(self, _event=None):
        """Cancel show, schedule hide after a short delay."""
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None
        if self.tipwindow is not None:
            self._do_hide()

    def _cancel_pending(self):
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None

    def _do_show(self):
        if self.tipwindow is not None or not self.widget.winfo_exists():
            return
        dropdown = getattr(self.widget, "_dropdown_menu", None)
        if dropdown and hasattr(dropdown, "winfo_exists") and dropdown.winfo_exists():
            try:
                if dropdown.winfo_viewable():
                    return
            except Exception:
                pass
        x, y = self._get_event_target(self.widget).bbox("insert")[0:2]
        x += self._get_event_target(self.widget).winfo_rootx() + 16
        y += self._get_event_target(self.widget).winfo_rooty() + 16
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        ctk.CTkLabel(tw, text=self.title, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT).pack(padx=8, pady=(8, 2))
        ctk.CTkLabel(tw, text=self.description, font=ctk.CTkFont(size=9),
                     text_color=TEXT_MUTED, wraplength=240).pack(padx=8, pady=(0, 8))
        tw.update_idletasks()

    def _do_hide(self):
        if self.tipwindow is not None:
            try:
                self.tipwindow.destroy()
            except Exception:
                pass
            self.tipwindow = None

    def show(self, event=None):
        self._on_enter(event)

    def hide(self, event=None):
        self._on_leave(event)

    def destroy(self):
        self._cancel_pending()
        self._do_hide()
        canvas = self._get_event_target(self.widget)
        try:
            canvas.unbind("<Enter>")
            canvas.unbind("<Leave>")
        except Exception:
            pass


# === ComfyUIApp class ===
class ComfyUIApp:

    def _show_shortcut_modal(self, event=None):
        try:
            win = ctk.CTkToplevel(self.root)
            win.title("Keyboard Shortcuts Cheat Sheet")
            win.geometry("520x400")
            win.resizable(False, False)
            win.attributes("-topmost", True)
            
            frame = ctk.CTkFrame(win, fg_color=BG_CARD, corner_radius=10)
            frame.pack(fill="both", expand=True, padx=16, pady=16)
            
            ctk.CTkLabel(frame, text="Keyboard Shortcuts", font=self.FONT_LOGO_SUB, text_color=TEXT).pack(pady=(12, 16))
            
            shortcuts = [
                ("Ctrl + E / Ctrl + Enter", "Trigger Image Generation"),
                ("Ctrl + O", "Open Output Directory in Explorer"),
                ("F5", "Refresh Gallery View"),
                ("Ctrl + L", "Open Application Log Window"),
                ("Ctrl + Shift + V", "Purge CUDA Memory Cache"),
                ("F1", "Show Shortcuts Cheat Sheet")
            ]
            
            for key, desc in shortcuts:
                row = ctk.CTkFrame(frame, fg_color=BG_CARD_ALT, corner_radius=6)
                row.pack(fill="x", padx=12, pady=4)
                ctk.CTkLabel(row, text=key, font=self.FONT_SMALL_BOLD, text_color=BRAND, width=140, anchor="w").pack(side="left", padx=12, pady=6)
                ctk.CTkLabel(row, text=desc, font=self.FONT_SMALL, text_color=TEXT_MUTED, anchor="w").pack(side="left", padx=4, pady=6)
                
            ctk.CTkButton(frame, text="Close", width=100, font=self.FONT_SMALL, command=win.destroy).pack(pady=16)
        except Exception as e:
            logging.error("Shortcut modal error: %s", e)


    def _add_style_tag(self, tag):
        try:
            curr = self.prompt_entry.get("1.0", "end-1c").strip()
            if curr:
                new_text = curr + ", " + tag
            else:
                new_text = tag
            self.prompt_entry.delete("1.0", "end")
            self.prompt_entry.insert("1.0", new_text)
            self._set_status(f"Added style tag: {tag}")
        except Exception as e:
            logging.error("Style tag error: %s", e)


    def _scan_available_checkpoints(self):
        """Dynamic Checkpoint Scanner: Auto-populates any .safetensors files in models/checkpoints."""
        try:
            available = list(MODELS.keys())
            if os.path.exists(CKPT_DIR):
                for f in os.listdir(CKPT_DIR):
                    if f.endswith(".safetensors") or f.endswith(".ckpt"):
                        name = os.path.splitext(f)[0]
                        if name not in MODELS and f not in [m.get("file") for m in MODELS.values()]:
                            MODELS[name] = {
                                "file": f, "w": 1024, "h": 1024, "steps": 30, "cfg": 6.5,
                                "sampler": "dpmpp_2m", "scheduler": "karras"
                            }
                            if name not in available:
                                available.append(name)
            if hasattr(self, "model_menu"):
                self.model_menu.configure(values=list(MODELS.keys()))
        except Exception as e:
            logging.error("Scan checkpoints error: %s", e)


    def _unload_vram(self):
        try:
            r = requests.post(COMFYUI_URL + "/free", json={"unload_models": True, "free_memory": True}, timeout=5)
            if r.status_code == 200:
                self._set_status("VRAM purged successfully — memory freed!")
                return True
        except Exception: pass
        self._set_status("VRAM purge completed")
        return False


    def _gallery_style_cell(self, cell, selected):
        try:
            if selected:
                cell.configure(border_width=3, border_color=BRAND)
                if getattr(cell, "_badge", None):
                    cell._badge.place(relx=0.0, rely=0.0, x=6, y=6, anchor="nw")
                    cell._badge.lift()
            else:
                cell.configure(border_width=0)
                if getattr(cell, "_badge", None):
                    cell._badge.place_forget()
        except Exception: pass

    def _gallery_toggle(self, fp):
        if not getattr(self, "_gallery_sel_mode", False): self._gallery_enter_select()
        if fp in self._gallery_selected: self._gallery_selected.discard(fp)
        else: self._gallery_selected.add(fp)
        for container_name in ("_gallery_frame_main", "thumb_frame"):
            c = getattr(self, container_name, None)
            if c and hasattr(c, "inner") and c.inner.winfo_exists():
                for w in c.inner.winfo_children():
                    if getattr(w, "_fp", None) == fp:
                        self._gallery_style_cell(w, fp in self._gallery_selected)

    def _gallery_enter_select(self):
        self._gallery_sel_mode = True
        if hasattr(self, "_gallery_btn_select"): self._gallery_btn_select.grid_remove()
        if hasattr(self, "_gallery_btn_refresh"): self._gallery_btn_refresh.grid_remove()
        if hasattr(self, "_gallery_selbar"): self._gallery_selbar.grid()

    def _gallery_exit_select(self):
        self._gallery_sel_mode = False
        if hasattr(self, "_gallery_selected"): self._gallery_selected.clear()
        if hasattr(self, "_gallery_selbar"): self._gallery_selbar.grid_remove()
        if hasattr(self, "_gallery_btn_select"): self._gallery_btn_select.grid()
        if hasattr(self, "_gallery_btn_refresh"): self._gallery_btn_refresh.grid()

    def _gallery_select_all(self):
        try:
            items = [w._fp for w in self._gallery_frame_main.inner.winfo_children() if getattr(w, "_fp", None)]
            self._gallery_selected.update(items)
            for w in self._gallery_frame_main.inner.winfo_children():
                if getattr(w, "_fp", None): self._gallery_style_cell(w, True)
        except Exception: pass

    def _gallery_delete_selected(self):
        if not getattr(self, "_gallery_selected", None): return
        n = len(self._gallery_selected)
        if messagebox.askyesno("Delete Images", f"Delete {n} selected image(s) from disk?"):
            for fp in list(self._gallery_selected):
                try:
                    if os.path.exists(fp): os.remove(fp)
                except Exception: pass
            self._gallery_exit_select()
            if hasattr(self, "_refresh_gallery_main"): self._refresh_gallery_main()


    def _init_drag_system(self):
        self._drag_targets = {}
        self._drag_pil = None
        self._drag_path = None
        self._drag_ghost = None

    def _register_drop_target(self, widget, callback):
        self._drag_targets[widget] = callback

    def _make_drag_source(self, widget, get_pil, get_path, on_click=None):
        def _on_press(event):
            widget._drag_start = (event.x, event.y)
            widget._drag_moved = False

        def _on_motion(event):
            if not getattr(widget, "_drag_start", None): return
            dx = abs(event.x - widget._drag_start[0])
            dy = abs(event.y - widget._drag_start[1])
            if (dx > 6 or dy > 6) and not widget._drag_moved:
                widget._drag_moved = True
                pil_img = get_pil()
                img_path = get_path()
                if pil_img or img_path:
                    self._drag_pil = pil_img
                    self._drag_path = img_path
                    self._create_drag_ghost(event, pil_img)

        def _on_release(event):
            if self._drag_ghost:
                self._destroy_drag_ghost()
                drop_w = self.root.winfo_containing(event.x_root, event.y_root)
                curr = drop_w
                cb = None
                while curr:
                    if curr in self._drag_targets:
                        cb = self._drag_targets[curr]
                        break
                    curr = getattr(curr, "master", None)
                if cb and (self._drag_pil or self._drag_path):
                    cb(self._drag_pil, self._drag_path)
            elif not getattr(widget, "_drag_moved", False) and on_click:
                on_click()
            widget._drag_start = None
            widget._drag_moved = False
            self._drag_pil = None
            self._drag_path = None

        widget.bind("<ButtonPress-1>", _on_press)
        widget.bind("<B1-Motion>", _on_motion)
        widget.bind("<ButtonRelease-1>", _on_release)

    def _create_drag_ghost(self, event, pil_img):
        try:
            self._destroy_drag_ghost()
            ghost = ctk.CTkToplevel(self.root)
            ghost.overrideredirect(True)
            ghost.attributes("-alpha", 0.7)
            ghost.attributes("-topmost", True)
            if pil_img:
                t_img = pil_img.copy()
                t_img.thumbnail((90, 90))
                ctk_img = ctk.CTkImage(light_image=t_img, dark_image=t_img, size=t_img.size)
                lbl = ctk.CTkLabel(ghost, image=ctk_img, text="")
                lbl._img = ctk_img
                lbl.pack()
            else:
                lbl = ctk.CTkLabel(ghost, text="[Image]", fg_color=BRAND, text_color="#FFFFFF", corner_radius=6)
                lbl.pack()
            ghost.geometry("+%d+%d" % (event.x_root + 14, event.y_root + 14))
            self._drag_ghost = ghost
        except Exception: pass

    def _destroy_drag_ghost(self):
        if self._drag_ghost:
            try: self._drag_ghost.destroy()
            except Exception: pass
            self._drag_ghost = None

    def __init__(self, root):
        self.root = root
        self._running = True
        root.title("ComfyUI Uncensored")
        root.geometry("1280x1120")
        root.minsize(900, 640)
        mode = ctk.get_appearance_mode().lower()
        root.configure(bg="#F1F5F9" if mode == "light" else "#0F0F12")

        self.tooltips_enabled = ctk.StringVar(value="1")
        self.current_tab = "txt2img"
        self.vars = {}
        self.staged_image = None
        self.input_image_path = None
        self.history = []
        self._load_history()
        self.backend = None
        self.backend_retries = 0
        self.last_prompt_id = None
        self.last_watch = time.time()
        self.current_pil = None
        self._hue = 0.0

        self.glass = AcrylicBackground(root)
        self.acrylic = self.glass

        # Initialize font constants after root exists
        self.FONT_BOLD = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.FONT_NORMAL = ctk.CTkFont(family="Segoe UI", size=11)
        self.FONT_NORMAL_BOLD = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        self.FONT_SMALL = ctk.CTkFont(family="Segoe UI", size=10)
        self.FONT_SMALL_BOLD = ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        self.FONT_LOGO = ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        self.FONT_LOGO_SUB = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")

        # Debounce guards for rapid clicks
        self._tab_switch_lock = False
        self._model_switch_lock = False
        self._preset_switch_lock = False
        self._generate_lock = False
        self._last_tab_switch = 0
        self._last_model_switch = 0
        self._last_preset_switch = 0
        self._last_generate = 0

        self._init_vars()
        self._build_sidebar()
        self._build_main()
        self._build_status_bar()
        self._build_sidebar_buttons()

        # Keyboard Shortcuts
        root.bind("<Control-Return>", lambda e: self._start_generate())
        root.bind("<Shift-Return>", lambda e: self._start_generate())
        root.bind("<Control-e>", lambda e: self._start_generate())
        root.bind("<Control-E>", lambda e: self._start_generate())
        root.bind("<Control-r>", lambda e: self._restart_server())
        root.bind("<F5>", lambda e: self._refresh_gallery_main())

        # Window Close Protocol
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Show window immediately, defer backend + gradient
        root.after(100, self._paint_header)
        root.after(5000, self._animate_gradient)
        root.after(15000, self._start_header_gradient)
        root.after(300, self._start_backend_threads)

    def _post_build(self):
        """Called after window is first shown — starts deferred animations/captures."""
        pass  # Now handled by after() calls in __init__

    def _init_vars(self):
        m = {}
        m["width"] = tk.StringVar(value="768")
        m["height"] = tk.StringVar(value="768")
        m["steps"] = tk.StringVar(value="30")
        m["cfg"] = tk.StringVar(value="6.5")
        m["seed"] = tk.StringVar(value="0")
        m["batch"] = tk.StringVar(value="1")
        m["sampler"] = tk.StringVar(value="dpmpp_2m")
        m["scheduler"] = tk.StringVar(value="karras")
        m["format"] = tk.StringVar(value="PNG")
        self.vars["txt2img"] = m

        m2 = {"denoise": tk.StringVar(value="0.7")}
        m2.update(m)
        self.vars["img2img"] = m2

        m3 = {
            "width": tk.StringVar(value="512"),
            "height": tk.StringVar(value="512"),
            "steps": tk.StringVar(value="0"),
            "cfg": tk.StringVar(value="0"),
            "seed": tk.StringVar(value="0"),
            "batch": tk.StringVar(value="1"),
            "sampler": tk.StringVar(value="dpmpp_2m"),
            "scheduler": tk.StringVar(value="karras"),
            "model": tk.StringVar(value=UPSCALE_MODELS[0]),
            "scale": tk.StringVar(value="4"),
            "format": tk.StringVar(value="PNG"),
        }
        self.vars["upscale"] = m3

    def _build_backdrop(self):
        pass

    def _start_backend_threads(self):
        """Start backend polling threads after UI is first rendered."""
        threading.Thread(target=self._start_backend, daemon=True).start()
        threading.Thread(target=self._check_for_errors, daemon=True).start()
        self.root.after(5000, self._start_vram_watch)

    # ------------------------------------------------------------------
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self.root, width=230, corner_radius=0, fg_color=BG_SIDEBAR)
        sb.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sb.grid_columnconfigure(0, weight=1)
        self.sidebar = sb
        ctk.CTkLabel(sb, text="ComfyUI", font=self.FONT_LOGO,
                     text_color=BRAND).grid(row=0, column=0, padx=20, pady=(22, 0), sticky="w")
        ctk.CTkLabel(sb, text="Uncensored", font=self.FONT_LOGO_SUB,
                     text_color=TEXT).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        nav = [("Generate", self._focus_generate), ("Gallery", self._focus_gallery),
               ("Settings", self._focus_settings)]
        for i, (label, cmd) in enumerate(nav):
            b = ctk.CTkButton(sb, text=label, height=34, anchor="w", fg_color="transparent",
                              text_color=TEXT, hover_color=BG_CARD_ALT,
                              corner_radius=8, command=cmd, font=self.FONT_NORMAL_BOLD)
            b.grid(row=2 + i, column=0, padx=14, pady=6, sticky="ew")

        # ---- Appearance ----
        ctk.CTkLabel(sb, text="Appearance", font=self.FONT_NORMAL_BOLD,
                     text_color=TEXT).grid(row=5, column=0, padx=20, pady=(20, 2), sticky="w")
        mode = ctk.CTkOptionMenu(sb, values=["Dark", "Light", "System"],
                                 command=self._set_appearance,
                                 fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                 button_hover_color=BRAND_HOVER,
                                 dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER)
        mode.set(getattr(self, "_current_appearance_val", "System"))
        mode.grid(row=6, column=0, padx=14, pady=4, sticky="ew")
        scale = ctk.CTkOptionMenu(sb, values=["90%", "100%", "110%", "120%"],
                                  command=self._set_scaling,
                                  fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                  button_hover_color=BRAND_HOVER,
                                  dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER)
        scale.set(getattr(self, "_current_scaling_val", "100%"))
        scale.grid(row=7, column=0, padx=14, pady=(4, 16), sticky="ew")

        # Status pill
        self.status_label = ctk.CTkLabel(sb, text="Initializing...", height=30, corner_radius=8,
                                         fg_color=BG_CARD_ALT, text_color=TEXT,
                                         font=self.FONT_NORMAL)
        self.status_label.grid(row=8, column=0, padx=14, pady=(20, 14), sticky="ew")

    def _apply_cursor_style(self, widget):
        try:
            mode = ctk.get_appearance_mode().lower()
            cursor_color = "#020617" if mode == "light" else "#F8FAFC"
            select_bg = "#4338CA"
            select_fg = "#FFFFFF"
            if hasattr(widget, "_textbox"):
                widget._textbox.configure(insertbackground=cursor_color, selectbackground=select_bg, selectforeground=select_fg, insertwidth=2)
            elif hasattr(widget, "_entry"):
                widget._entry.configure(insertbackground=cursor_color, selectbackground=select_bg, selectforeground=select_fg, insertwidth=2)
        except Exception:
            pass

    def _update_cursors_and_canvases(self):
        try:
            mode = ctk.get_appearance_mode().lower()
            bg_color = "#F1F5F9" if mode == "light" else "#0F0F12"
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.configure(bg=bg_color)
                except Exception:
                    pass

            for attr in ("prompt_entry", "neg_entry", "img2img_prompt_entry", "img2img_neg_entry"):
                if hasattr(self, attr):
                    self._apply_cursor_style(getattr(self, attr))

            def _refresh_children(parent):
                for child in parent.winfo_children():
                    if hasattr(child, "refresh_appearance"):
                        try:
                            child.refresh_appearance()
                        except Exception:
                            pass
                    _refresh_children(child)
            if hasattr(self, 'root') and self.root:
                _refresh_children(self.root)
        except Exception as e:
            logging.error("Update cursors error: %s", e)

    def _rebuild_ui(self):
        try:
            active_tab = getattr(self, "current_tab", "txt2img")
            active_view = getattr(self, "_active_view", "generate")

            if hasattr(self, "sidebar") and self.sidebar:
                try:
                    self.sidebar.destroy()
                except Exception:
                    pass
            if hasattr(self, "top") and self.top:
                try:
                    self.top.destroy()
                except Exception:
                    pass
            if hasattr(self, "_gallery_main") and self._gallery_main:
                try:
                    self._gallery_main.destroy()
                except Exception:
                    pass
            if hasattr(self, "_settings_main") and self._settings_main:
                try:
                    self._settings_main.destroy()
                except Exception:
                    pass

            self._build_sidebar()
            self._build_main()
            self._build_txt2img_tab()
            self._build_img2img_tab()
            self._build_upscale_tab()
            self._build_preview_pane()
            self._build_sidebar_buttons()
            self._show_view(active_view)
            self._update_cursors_and_canvases()
        except Exception as e:
            logging.error("Rebuild UI error: %s", e)

    def _set_appearance(self, v):
        try:
            self._current_appearance_val = v
            mode_lower = str(v).lower()
            ctk.set_appearance_mode(mode_lower)
            self._update_cursors_and_canvases()
            if hasattr(self, 'glass') and self.glass:
                self.glass.refresh()
        except Exception as e:
            logging.error("Set appearance error: %s", e)

    def _set_scaling(self, v):
        try:
            factor = float(v.replace("%", "")) / 100.0
            self._current_scaling_val = v
            ctk.set_widget_scaling(factor)
            self._set_status("UI Scaled to %s" % v)
        except Exception as e:
            logging.error("Set scaling error: %s", e)

    def _deferred_rebuild_ui(self):
        try:
            self._rebuild_ui()
            if hasattr(self, 'glass') and self.glass:
                self.glass.refresh()
        except Exception as e:
            logging.error("Deferred rebuild error: %s", e)

    def _focus_generate(self):
        try:
            logging.info("Focus generate clicked")
            if hasattr(self, "tabview") and self.tabview.get() != "Text to Image":
                self.tabview.set("Text to Image")
            if hasattr(self, "prompt_entry"):
                self.prompt_entry.focus()
            self._show_view("generate")
        except Exception as e:
            logging.error("Focus generate error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

    def _focus_gallery(self):
        try:
            logging.info("Focus gallery clicked")
            self._build_gallery_in_main()
            self._show_view("gallery")
        except Exception as e:
            logging.error("Focus gallery error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

    def _focus_settings(self):
        try:
            logging.info("Focus settings clicked")
            self._build_settings_in_main()
            self._show_view("settings")
        except Exception as e:
            logging.error("Focus settings error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

    def _show_view(self, name):
        """Toggle which right-column view is visible.

        'generate'  -> show the params + preview pane (self.top)
        'gallery'   -> show _gallery_main
        'settings'  -> show _settings_main
        """
        try:
            if name == "generate":
                self.top.grid()
                for f in ("_gallery_main", "_settings_main"):
                    if hasattr(self, f) and getattr(self, f).winfo_exists():
                        getattr(self, f).grid_remove()
            else:
                self.top.grid_remove()
                target = "_gallery_main" if name == "gallery" else "_settings_main"
                if not (hasattr(self, target) and getattr(self, target).winfo_exists()):
                    # Frame was destroyed by a UI rebuild (e.g. scaling change) — recreate it
                    if name == "gallery":
                        self._build_gallery_in_main()
                    else:
                        self._build_settings_in_main()
                if hasattr(self, target) and getattr(self, target).winfo_exists():
                    getattr(self, target).grid()
        except Exception as e:
            logging.error("show_view error: %s", e)

    def _build_gallery_in_main(self):
        """Build gallery content in the main area."""
        # Create gallery frame in the main area (where tabview was)
        self._gallery_main = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=10)
        self._gallery_main.grid(row=0, column=1, rowspan=4, padx=16, pady=(8, 16), sticky="nsew")
        self._gallery_main.grid_columnconfigure(0, weight=1)
        self._gallery_main.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self._gallery_main, fg_color=BG_CARD, corner_radius=8)
        header.grid(row=0, column=0, padx=8, pady=(0, 8), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Generated Images", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        refresh_btn = ctk.CTkButton(header, text="Refresh", width=80, height=24,
                                    command=self._refresh_gallery_main, fg_color=ACCENT2,
                                    hover_color=ACCENT2_HOVER, text_color="#FFFFFF")
        refresh_btn.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        self._gallery_frame_main = ctk.CTkScrollableFrame(self._gallery_main, fg_color=BG_CARD_ALT, corner_radius=8)
        self._gallery_frame_main.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._gallery_frame_main.grid_columnconfigure(0, weight=1)
        enable_auto_hide_scrollbar(self._gallery_frame_main)
        self._refresh_gallery_main()

    def _refresh_gallery_main(self):
        """Populate gallery with thumbnails from OUTPUT_DIR in main area."""
        if not hasattr(self, '_gallery_frame_main') or not self._gallery_frame_main.winfo_exists():
            return
        for widget in self._gallery_frame_main.winfo_children():
            widget.destroy()
        try:
            if not os.path.isdir(OUTPUT_DIR):
                ctk.CTkLabel(self._gallery_frame_main, text="No generated images yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            images = [f for f in os.listdir(OUTPUT_DIR)
                      if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith("input")]
            images.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
            if not images:
                ctk.CTkLabel(self._gallery_frame_main, text="No generated images yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            for idx, fname in enumerate(images[:12]):
                fpath = os.path.join(OUTPUT_DIR, fname)
                try:
                    img = Image.open(fpath)
                    img.thumbnail((180, 140))
                    photo = ImageTk.PhotoImage(img)
                    lbl = ctk.CTkLabel(self._gallery_frame_main, image=photo, text="",
                                       fg_color=BG_CARD, corner_radius=6, width=180, height=140)
                    lbl.image = photo
                    lbl.grid(row=idx // 3, column=idx % 3, padx=6, pady=6, sticky="nw")
                    lbl.bind("<Button-1>", lambda e, fp=fpath: os.startfile(fp))
                    lbl.bind("<Enter>", lambda e, p=fname: self._set_status(p))
                except Exception:
                    pass
            self._gallery_frame_main.update_idletasks()
        except Exception:
            pass

    def _build_settings_in_main(self):
        """Build settings content in the main area."""
        self._settings_main = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=10)
        self._settings_main.grid(row=0, column=1, rowspan=4, padx=16, pady=(8, 16), sticky="nsew")
        self._settings_main.grid_columnconfigure(0, weight=1)
        self._settings_main.grid_rowconfigure(20, weight=1)

        ctk.CTkLabel(self._settings_main, text="Application Settings", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=(0, 12), sticky="w")

        r = 1
        self._labeled(self._settings_main, r, "Output Directory", "Output Dir",
                      ctk.CTkEntry(self._settings_main, textvariable=ctk.StringVar(value=OUTPUT_DIR), width=200, state="readonly")); r += 2
        self._labeled(self._settings_main, r, "Input Directory", "Input Dir",
                      ctk.CTkEntry(self._settings_main, textvariable=ctk.StringVar(value=INPUT_DIR), width=200, state="readonly")); r += 2
        self._labeled(self._settings_main, r, "Backend Path", "Backend",
                      ctk.CTkEntry(self._settings_main, textvariable=ctk.StringVar(value=PYTHON_PATH), width=200, state="readonly")); r += 2
        self._labeled(self._settings_main, r, "ComfyUI URL", "URL",
                      ctk.CTkEntry(self._settings_main, textvariable=ctk.StringVar(value=COMFYUI_URL), width=200, state="readonly")); r += 2
        ctk.CTkLabel(self._settings_main, text="Restart backend to apply changes.", font=ctk.CTkFont(size=9),
                     text_color=TEXT_MUTED).grid(row=r, column=0, padx=10, pady=(8, 0), sticky="w")

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _build_main(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # NOTE: No global click filter. A bind_all("<Button-1>") returning "break"
        # silently swallows every left-click from CTk widgets and makes the app
        # feel dead. Debounce is handled per-handler only (see _on_tab, _on_model, etc.).

        self.top = ctk.CTkFrame(self.root, fg_color=BG_APP, corner_radius=0)
        self.top.grid(row=0, column=1, padx=16, pady=12, sticky="nsew")
        self.top.grid_columnconfigure(0, weight=1)   # params column
        self.top.grid_columnconfigure(1, weight=0, minsize=340)  # preview column (fixed)
        self.top.grid_rowconfigure(1, weight=1)  # tabview expands; action bar sits below at row 2

        self.model_var = ctk.StringVar(value=list(MODELS.keys())[0])
        self.preset_var = ctk.StringVar(value=list(PRESETS.keys())[0])

        toolbar = ctk.CTkFrame(self.top, fg_color="transparent")
        toolbar.grid(row=0, column=0, padx=0, pady=(0, 4), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=0)
        toolbar.grid_columnconfigure(1, weight=0)
        toolbar.grid_columnconfigure(2, weight=1)

        self.model_menu = ctk.CTkOptionMenu(toolbar, values=list(MODELS.keys()), font=self.FONT_NORMAL,
                                            variable=self.model_var,
                                            fg_color=BG_CARD_ALT,
                                            button_color=BORDER,
                                            button_hover_color=BRAND_HOVER,
                                            text_color=TEXT,
                                            dropdown_fg_color=DROPDOWN_FG,
                                            dropdown_text_color=DROPDOWN_TEXT,
                                            dropdown_hover_color=DROPDOWN_HOVER,
                                            command=self._on_model, width=160)
        self.model_menu.grid(row=0, column=0, padx=(0, 6), sticky="w")
        ToolTip(self.model_menu, *TOOLTIPS["Model"])

        self.preset_menu = ctk.CTkOptionMenu(toolbar, values=list(PRESETS.keys()), font=self.FONT_NORMAL,
                                             variable=self.preset_var,
                                             fg_color=BG_CARD_ALT,
                                             button_color=BORDER,
                                             button_hover_color=BRAND_HOVER,
                                             text_color=TEXT,
                                             dropdown_fg_color=DROPDOWN_FG,
                                             dropdown_text_color=DROPDOWN_TEXT,
                                             dropdown_hover_color=DROPDOWN_HOVER,
                                             command=self._on_preset, width=160)
        self.preset_menu.grid(row=0, column=1, padx=6, sticky="w")
        ToolTip(self.preset_menu, *TOOLTIPS["Preset"])

        self.gen_btn = ctk.CTkButton(toolbar, text="Generate  (Ctrl+E)", width=130, font=self.FONT_NORMAL_BOLD,
                                     fg_color=ACCENT2, hover_color=ACCENT2_HOVER,
                                     text_color="#FFFFFF",
                                     command=self._start_generate)
        self.gen_btn.grid(row=0, column=2, padx=(8, 0), sticky="e")
        ToolTip(self.gen_btn, *TOOLTIPS["Generate"])

        # Tabview
        self.tabview = ctk.CTkTabview(self.top, fg_color="transparent",
                                      segmented_button_fg_color=BG_CARD_ALT,
                                      segmented_button_selected_color=BRAND,
                                      segmented_button_selected_hover_color=BRAND_HOVER,
                                      text_color=TEXT
                                      )
        self.tabview.grid(row=1, column=0, columnspan=1, padx=0, pady=(12, 0), sticky="nsew")

        self.tabview.add("Text to Image")
        self.tabview.add("Image to Image")
        self.tabview.add("Upscale")
        self.tabview.set("Text to Image")

        self._tab_callbacks = {
            "Text to Image": self._build_txt2img_tab,
            "Image to Image": self._build_img2img_tab,
            "Upscale": self._build_upscale_tab,
        }
        self._tab_built = {"Text to Image": False, "Image to Image": False,
                           "Upscale": False}

        # Build txt2img tab immediately
        self._on_tab()

        # Preview window (right column of Generate view)
        self._build_preview_pane()

        # Header gradient image
        self._header_img = None
        self.header = ctk.CTkLabel(self.top, text="", height=56)
        self.header.grid(row=2, column=0, columnspan=1, padx=0, pady=(2, 0), sticky="nsew")

        # Bind tab changes
        self.tabview._segmented_button.configure(command=self._on_tab)
    def _labeled(self, parent, row, label, key, widget):
        """Create a labeled control at the given row in parent grid.

        Places the label at `row` and the control at `row+1`, then returns the
        next free row (row+2) so callers advance correctly. The previous code
        advanced the row counter by only 1 after each call, which made every
        control overlap the next label -- collapsing the whole center panel
        into an unreadable stack (the 'middle is crunched together' bug).
        """
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT).grid(row=row, column=0, padx=12, pady=(3, 0), sticky="w")
        widget.grid(row=row + 1, column=0, padx=12, pady=(0, 3), sticky="ew")
        if key in TOOLTIPS:
            ToolTip(widget, *TOOLTIPS[key])
        return row + 2

    # ------------------------------------------------------------------
    def _build_txt2img_tab(self):
        t = self.tabview.tab("Text to Image")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self.prompt_entry = ctk.CTkTextbox(sf, height=60, font=ctk.CTkFont(size=10),
                                           fg_color=BG_CARD_ALT, text_color=TEXT)
        self.prompt_entry.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.prompt_entry)
        ToolTip(self.prompt_entry, *TOOLTIPS["Prompt"])
        self.prompt_entry.insert("1.0", "photorealistic portrait, detailed skin, studio light")

        self.neg_entry = ctk.CTkTextbox(sf, height=32, font=ctk.CTkFont(size=10),
                                        fg_color=BG_CARD_ALT, text_color=TEXT)
        self.neg_entry.grid(row=1, column=0, padx=10, pady=(6, 0), sticky="nsew")
        self._apply_cursor_style(self.neg_entry)
        ToolTip(self.neg_entry, *TOOLTIPS["Negative Prompt"])
        self.neg_entry.insert("1.0", DEFAULT_NEG)

        m = self.vars["txt2img"]
        r = 2
        r = self._labeled(sf, r, "Width", "Width",
                      ctk.CTkEntry(sf, textvariable=m["width"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Height", "Height",
                      ctk.CTkEntry(sf, textvariable=m["height"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Steps", "Steps",
                      ctk.CTkOptionMenu(sf, values=["20", "30", "35", "40", "50"], variable=m["steps"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "CFG Scale", "CFG",
                      ctk.CTkOptionMenu(sf, values=["5.0", "6.5", "7.5", "8.0"], variable=m["cfg"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Seed", "Seed",
                      ctk.CTkEntry(sf, textvariable=m["seed"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Batch Size", "Batch",
                      ctk.CTkEntry(sf, textvariable=m["batch"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Sampler", "Sampler",
                      ctk.CTkOptionMenu(sf, values=SAMPLERS, variable=m["sampler"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Scheduler", "Scheduler",
                      ctk.CTkOptionMenu(sf, values=SCHEDULERS, variable=m["scheduler"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Output Format", "Output Format",
                      ctk.CTkOptionMenu(sf, values=["PNG", "Game Texture (TGA)"], variable=m["format"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))

    # ------------------------------------------------------------------
    def _build_img2img_tab(self):
        t = self.tabview.tab("Image to Image")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self._upload_btn = ctk.CTkButton(sf, text="Upload Image or Video", height=36,
                                         corner_radius=16, fg_color=ACCENT2,
                                         hover_color=ACCENT2_HOVER, text_color="#FFFFFF",
                                         command=self._pick_input)
        self._upload_btn.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        ToolTip(self._upload_btn, *TOOLTIPS["Input Image"])

        self.input_preview = ctk.CTkLabel(sf, text="No input selected", height=120,
                                          corner_radius=8, fg_color=BG_CARD_ALT,
                                          text_color=TEXT_MUTED)
        self.input_preview.grid(row=1, column=0, padx=10, pady=(6, 0), sticky="ew")

        self.img2img_prompt_entry = ctk.CTkTextbox(sf, height=60, font=ctk.CTkFont(size=10),
                                                   fg_color=BG_CARD_ALT, text_color=TEXT)
        self.img2img_prompt_entry.grid(row=2, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.img2img_prompt_entry)
        ToolTip(self.img2img_prompt_entry, *TOOLTIPS["Prompt"])
        self.img2img_prompt_entry.insert("1.0", "photorealistic portrait, detailed skin, studio light")

        self.img2img_neg_entry = ctk.CTkTextbox(sf, height=32, font=ctk.CTkFont(size=10),
                                                fg_color=BG_CARD_ALT, text_color=TEXT)
        self.img2img_neg_entry.grid(row=3, column=0, padx=10, pady=(6, 0), sticky="nsew")
        self._apply_cursor_style(self.img2img_neg_entry)
        ToolTip(self.img2img_neg_entry, *TOOLTIPS["Negative Prompt"])
        self.img2img_neg_entry.insert("1.0", DEFAULT_NEG)

        m = self.vars["img2img"]
        r = 4
        r = self._labeled(sf, r, "Denoise", "Denoise",
                      ctk.CTkEntry(sf, textvariable=m["denoise"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Width", "Width",
                      ctk.CTkEntry(sf, textvariable=m["width"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Height", "Height",
                      ctk.CTkEntry(sf, textvariable=m["height"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Steps", "Steps",
                      ctk.CTkOptionMenu(sf, values=["20", "30", "35", "40", "50"], variable=m["steps"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "CFG Scale", "CFG",
                      ctk.CTkOptionMenu(sf, values=["5.0", "6.5", "7.5", "8.0"], variable=m["cfg"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Seed", "Seed",
                      ctk.CTkEntry(sf, textvariable=m["seed"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Batch Size", "Batch",
                      ctk.CTkEntry(sf, textvariable=m["batch"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Sampler", "Sampler",
                      ctk.CTkOptionMenu(sf, values=SAMPLERS, variable=m["sampler"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Scheduler", "Scheduler",
                      ctk.CTkOptionMenu(sf, values=SCHEDULERS, variable=m["scheduler"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Output Format", "Output Format",
                      ctk.CTkOptionMenu(sf, values=["PNG", "Game Texture (TGA)"], variable=m["format"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))

    def _build_upscale_tab(self):
        t = self.tabview.tab("Upscale")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self._up_scale_btn = ctk.CTkButton(sf, text="Select Image to Upscale", height=36,
                                           corner_radius=16, fg_color=ACCENT2,
                                           hover_color=ACCENT2_HOVER, text_color="#FFFFFF",
                                           command=self._pick_upscale)
        self._up_scale_btn.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        ToolTip(self._up_scale_btn, *TOOLTIPS["Upscale Model"])

        self.up_preview = ctk.CTkLabel(sf, text="No image selected", height=150, corner_radius=8,
                                       fg_color=BG_CARD_ALT, text_color=TEXT_MUTED)
        self.up_preview.grid(row=1, column=0, padx=10, pady=(6, 0), sticky="ew")

        m = self.vars["upscale"]
        r = 2
        r = self._labeled(sf, r, "Upscale Model", "Upscale Model",
                      ctk.CTkOptionMenu(sf, values=UPSCALE_MODELS, variable=m["model"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))
        r = self._labeled(sf, r, "Scale", "Scale",
                      ctk.CTkEntry(sf, textvariable=m["scale"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Output Format", "Output Format",
                      ctk.CTkOptionMenu(sf, values=["PNG", "Game Texture (TGA)"], variable=m["format"],
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER))

    def _build_gallery_tab(self):
        """Build the Gallery tab - thumbnail grid of generated images."""
        t = self.tabview.tab("Gallery")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        sf.grid_columnconfigure(0, weight=1)
        sf.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=8)
        header.grid(row=0, column=0, padx=8, pady=(0, 8), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Generated Images", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        refresh_btn = ctk.CTkButton(header, text="Refresh", width=80, height=24,
                                    command=self._refresh_gallery, fg_color=ACCENT2,
                                    hover_color=ACCENT2_HOVER, text_color="#FFFFFF")
        refresh_btn.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        self._gallery_frame = ctk.CTkScrollableFrame(sf, fg_color=BG_CARD_ALT, corner_radius=8)
        self._gallery_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._gallery_frame.grid_columnconfigure(0, weight=1)
        enable_auto_hide_scrollbar(self._gallery_frame)
        self._refresh_gallery()

    def _refresh_gallery(self):
        """Populate gallery with thumbnails from OUTPUT_DIR."""
        for widget in self._gallery_frame.winfo_children():
            widget.destroy()
        try:
            if not os.path.isdir(OUTPUT_DIR):
                ctk.CTkLabel(self._gallery_frame, text="No generated images yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            images = [f for f in os.listdir(OUTPUT_DIR)
                      if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith("input")]
            images.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
            if not images:
                ctk.CTkLabel(self._gallery_frame, text="No generated images yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            for idx, fname in enumerate(images[:12]):
                fpath = os.path.join(OUTPUT_DIR, fname)
                try:
                    img = Image.open(fpath)
                    img.thumbnail((180, 140))
                    photo = ImageTk.PhotoImage(img)
                    lbl = ctk.CTkLabel(self._gallery_frame, image=photo, text="",
                                       fg_color=BG_CARD, corner_radius=6, width=180, height=140)
                    lbl.image = photo
                    lbl.grid(row=idx // 3, column=0, padx=6, pady=6, sticky="w")
                    lbl.bind("<Button-1>", lambda e, fp=fpath: os.startfile(fp))
                    lbl.bind("<Enter>", lambda e, p=fname: self._set_status(p))
                except Exception:
                    pass
            self._gallery_frame.update_idletasks()
        except Exception as e:
            self._set_status("Gallery error: %s" % e)

    def _build_settings_tab(self):
        """Build the Settings tab - app configuration."""
        t = self.tabview.tab("Settings")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        sf.grid_columnconfigure(0, weight=1)
        sf.grid_rowconfigure(20, weight=1)

        ctk.CTkLabel(sf, text="Application Settings", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=(0, 12), sticky="w")

        r = 1
        self._labeled(sf, r, "Output Directory", "Output Dir",
                      ctk.CTkEntry(sf, textvariable=ctk.StringVar(value=OUTPUT_DIR), width=200, state="readonly")); r += 2
        self._labeled(sf, r, "Input Directory", "Input Dir",
                      ctk.CTkEntry(sf, textvariable=ctk.StringVar(value=INPUT_DIR), width=200, state="readonly")); r += 2
        self._labeled(sf, r, "Backend Path", "Backend",
                      ctk.CTkEntry(sf, textvariable=ctk.StringVar(value=PYTHON_PATH), width=200, state="readonly")); r += 2
        self._labeled(sf, r, "ComfyUI URL", "URL",
                      ctk.CTkEntry(sf, textvariable=ctk.StringVar(value=COMFYUI_URL), width=200, state="readonly")); r += 2
        ctk.CTkLabel(sf, text="Restart backend to apply changes.", font=ctk.CTkFont(size=9),
                     text_color=TEXT_MUTED).grid(row=r, column=0, padx=10, pady=(8, 0), sticky="w")

    def _on_tab(self, name=None):
        import time
        try:
            if getattr(self, '_tab_switch_lock', False):
                return
            if time.time() - getattr(self, '_last_tab_switch', 0) < 0.3:
                return
            self._tab_switch_lock = True
            self._last_tab_switch = time.time()
            try:
                if not name:
                    if hasattr(self, 'notebook') and self.notebook:
                        try:
                            name = self.notebook.select()
                        except Exception:
                            name = None
                    if not name and hasattr(self, 'tabview') and self.tabview:
                        try:
                            name = self.tabview.get()
                        except Exception:
                            name = None
                if str(name) == str(getattr(self, 'img2img_tab', None)):
                    self.current_tab = "img2img"
                elif str(name) == str(getattr(self, 'upscale_tab', None)):
                    self.current_tab = "upscale"
                elif str(name) == str(getattr(self, 'txt2img_tab', None)):
                    self.current_tab = "txt2img"
                else:
                    tab_map = {
                        "Text to Image": "txt2img", "txt2img": "txt2img",
                        "Image to Image": "img2img", "img2img": "img2img",
                        "Upscale": "upscale", "upscale": "upscale"
                    }
                    self.current_tab = tab_map.get(str(name), "txt2img")
                if name in getattr(self, '_tab_callbacks', {}) and not getattr(self, '_tab_built', {}).get(name, False):
                    self._tab_callbacks[name]()
                    self._tab_built[name] = True
            finally:
                self._tab_switch_lock = False
        except Exception as e:
            self._set_status(f"Error: {str(e)[:30]}")

    # ------------------------------------------------------------------
    # Backend lifecycle
    # ------------------------------------------------------------------
    def _start_backend(self):
        try:
            if not os.path.exists(PYTHON_PATH):
                self._set_status("Backend python missing")
                return
            # Kill only a previously-tracked backend instance (avoid nuking
            # unrelated python_embeded processes the user may be running).
            if getattr(self, "backend", None) and self.backend.poll() is None:
                try:
                    self.backend.terminate()
                except Exception:
                    pass
            args = [PYTHON_PATH, os.path.join(COMFYUI_DIR, MAIN_PY),
                    "--windows-standalone-build", "--fast", "fp16_accumulation",
                    "--disable-auto-launch"]
            self.backend = subprocess.Popen(
                args, cwd=COMFYUI_DIR,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self._set_status("Loading backend...")
            for i in range(150):
                time.sleep(1)
                try:
                    r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
                    if r.status_code == 200:
                        self._set_status("Server online")
                        self.root.after(3000, self._start_header_gradient)
                        return
                except Exception:
                    if i % 10 == 0:
                        self._set_status("Loading backend... (%ds)" % (i + 1))
            self._set_status("Server start failed - click Restart Backend")
        except Exception as e:
            self._set_status("Backend launch error: %s" % e)

    def _start_vram_watch(self):
        """Wrapper to start VRAM watchdog in a thread (deferred until backend ready)."""
        threading.Thread(target=self._vram_watch, daemon=True).start()

    def _restart_server(self):
        if self.backend and self.backend.poll() is None:
            try:
                self.backend.terminate()
            except Exception:
                pass
        self._set_status("Restarting backend...")
        threading.Thread(target=self._start_backend, daemon=True).start()

    def _vram_watch(self):
        """Monitor VRAM usage and warn when critical."""
        last_warned = 0
        while self._running:
            time.sleep(5)
            try:
                r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
                if r.status_code != 200:
                    continue
                devs = r.json().get("devices", [])
                if not devs:
                    continue
                d = devs[0]
                total = d.get("vram_total", 1)
                free = d.get("vram_free", 0)
                if total <= 0:
                    continue
                pct = 1 - (free / total)
                if pct > 0.95:
                    self._set_status("VRAM critical (%d%%) - wait for VRAM to clear" % int(pct * 100))
                    last_warned = pct
                elif pct > 0.85 and last_warned == 0:
                    self._set_status("Server online (VRAM %d%% used)" % int(pct * 100))
                    last_warned = pct
                elif pct < 0.80 and last_warned > 0:
                    last_warned = 0
            except Exception:
                pass

    def _check_for_errors(self):
        while self._running:
            time.sleep(2)
            try:
                for f in os.listdir(LOG_DIR):
                    if f.startswith("ComfyUI_Error_") and f.endswith(".json"):
                        fp = os.path.join(LOG_DIR, f)
                        try:
                            with open(fp) as fh:
                                data = json.load(fh)
                        except Exception:
                            continue
                        if data.get("hermes_processed"):
                            continue
                        msg = data.get("error", "Unknown backend error")
                        self._set_status("Error: %s" % msg[:40])
                        data["hermes_processed"] = True
                        try:
                            with open(fp, "w") as fh:
                                json.dump(data, fh)
                        except Exception:
                            pass
            except Exception as e:
                self._set_status("Monitor error: %s" % e)
            time.sleep(2)

    # ------------------------------------------------------------------
    # Workflow / Generation
    # ------------------------------------------------------------------
    def _build_workflow(self, mode):
        """Select an input image (or video frame) on the Image to Image tab"""
        m = self.vars.get(mode, self.vars["txt2img"])
        w = int(m["width"].get())
        h = int(m["height"].get())
        steps = int(m["steps"].get())
        cfg = float(m["cfg"].get())
        seed = int(m["seed"].get())
        if seed == 0:
            seed = random.randint(1, 2**32 - 1)
        batch = int(m["batch"].get())
        if mode == "img2img" and hasattr(self, "img2img_prompt_entry"):
            prompt_text = self.img2img_prompt_entry.get("1.0", "end").strip()
            neg_text = self.img2img_neg_entry.get("1.0", "end").strip()
        elif hasattr(self, "prompt_entry"):
            prompt_text = self.prompt_entry.get("1.0", "end").strip()
            neg_text = self.neg_entry.get("1.0", "end").strip()
        else:
            prompt_text = m.get("prompt", tk.StringVar()).get()
            neg_text = m.get("neg", tk.StringVar()).get()
        model_name = MODELS[self.model_var.get()]["value"]
        ckpt = model_name

        if mode == "txt2img":
            wf = {
                "LastNode": {"class_type": "CheckpointLoaderSimple",
                             "inputs": {"ckpt_name": ckpt, "model_strength": 1.0, "clip_strength": 1.0}},
                "EmptyLatent": {"class_type": "EmptyLatentImage",
                                "inputs": {"width": w, "height": h, "batch_size": batch}},
                "KSampler": {"class_type": "KSampler",
                             "inputs": {"sampler_name": m["sampler"].get(),
                                        "scheduler": m["scheduler"].get(),
                                        "steps": steps, "cfg": cfg, "seed": seed,
                                        "model": ["LastNode", 0], "positive": ["POS", 0],
                                        "negative": ["NEG", 0], "latent_image": ["EmptyLatent", 0]}},
                "POS": {"class_type": "CLIPTextEncode",
                        "inputs": {"text": prompt_text, "clip": ["LastNode", 1]}},
                "NEG": {"class_type": "CLIPTextEncode",
                        "inputs": {"text": neg_text, "clip": ["LastNode", 1]}},
                "VAEDecode": {"class_type": "VAEDecode",
                              "inputs": {"samples": ["KSampler", 0], "vae": ["LastNode", 2]}},
                "SaveImage": {"class_type": "SaveImage",
                              "inputs": {"images": ["VAEDecode", 0],
                                         "filename_prefix": "ComfyUI_Uncensored",
                                         "format": "Game Texture (TGA)" if m["format"].get() == "Game Texture (TGA)" else "PNG"}},
            }
            return wf, ckpt
        elif mode == "img2img":
            if not self.input_image_path:
                self._set_status("Select an input image first")
                wf, _ = self._build_workflow("txt2img")
                return wf, ckpt
            # Stage the input into ComfyUI's input dir so LoadImage can read it
            img = Image.open(self.input_image_path).convert("RGB")
            staged = os.path.join(INPUT_DIR, "img2img_in.png")
            img.save(staged)
            denoise = float(self.vars["img2img"].get("denoise", tk.StringVar(value="0.7")).get()) if "denoise" in self.vars["img2img"] else 0.7
            wf = {
                "LastNode": {"class_type": "CheckpointLoaderSimple",
                             "inputs": {"ckpt_name": ckpt, "model_strength": 1.0, "clip_strength": 1.0}},
                "LoadImage": {"class_type": "LoadImage",
                              "inputs": {"image": os.path.join("input", "img2img_in.png")}},
                "VAEEncode": {"class_type": "VAEEncode",
                              "inputs": {"pixels": ["LoadImage", 0], "vae": ["LastNode", 2]}},
                "KSampler": {"class_type": "KSampler",
                             "inputs": {"sampler_name": m["sampler"].get(),
                                        "scheduler": m["scheduler"].get(),
                                        "steps": steps, "cfg": cfg, "seed": seed,
                                        "denoise": denoise,
                                        "model": ["LastNode", 0], "positive": ["POS", 0],
                                        "negative": ["NEG", 0], "latent_image": ["VAEEncode", 0]}},
                "POS": {"class_type": "CLIPTextEncode",
                        "inputs": {"text": prompt_text, "clip": ["LastNode", 1]}},
                "NEG": {"class_type": "CLIPTextEncode",
                        "inputs": {"text": neg_text, "clip": ["LastNode", 1]}},
                "VAEDecode": {"class_type": "VAEDecode",
                              "inputs": {"samples": ["KSampler", 0], "vae": ["LastNode", 2]}},
                "SaveImage": {"class_type": "SaveImage",
                              "inputs": {"images": ["VAEDecode", 0],
                                         "filename_prefix": "ComfyUI_Uncensored",
                                         "format": "Game Texture (TGA)" if m["format"].get() == "Game Texture (TGA)" else "PNG"}},
            }
            return wf, ckpt
        elif mode == "upscale":
            if not self.input_image_path:
                self._set_status("Select an image on the Upscale tab")
                wf, _ = self._build_workflow("txt2img")
                return wf, ckpt
            img = Image.open(self.input_image_path).convert("RGB")
            img.save(os.path.join(INPUT_DIR, "upscale_in.png"))
            wf = {
                "LoadImage": {"class_type": "LoadImage",
                              "inputs": {"image": os.path.join("input", "upscale_in.png")}},
                "ModelLoader": {"class_type": "UpscaleModelLoader",
                                "inputs": {"model_name": m["model"].get()}},
                "Upscale": {"class_type": "ImageUpscaleWithModel",
                            "inputs": {"upscale_model": ["ModelLoader", 0],
                                       "image": ["LoadImage", 0],
                                       "width": w, "height": h}},
                "SaveImage": {"class_type": "SaveImage",
                              "inputs": {"images": ["Upscale", 0],
                                         "filename_prefix": "ComfyUI_Uncensored",
                                         "format": "Game Texture (TGA)" if m["format"].get() == "Game Texture (TGA)" else "PNG"}},
            }
            return wf, ckpt
        else:
            return {}, ckpt

    def _ensure_model_loaded(self, model_name):
        """Symlink the selected model into models/checkpoints/ on-demand."""
        if not model_name:
            return
        target = os.path.join(CKPT_DIR, model_name)
        source = os.path.join(ARCHIVE_DIR, model_name)
        if not os.path.exists(target) or (os.path.islink(target) and not os.path.exists(target)):
            try:
                os.makedirs(CKPT_DIR, exist_ok=True)
                os.symlink(source, target)
                self._set_status("Model loaded: %s" % model_name[:20])
            except FileExistsError:
                pass
            except Exception as e:
                if os.path.exists(source):
                    self._set_status("Model link error: %s" % str(e)[:30])
                else:
                    self._set_status("Model file missing: %s" % model_name)

    def _cleanup_symlinks(self):
        """Remove model symlinks from checkpoints dir on exit."""
        try:
            if os.path.isdir(CKPT_DIR):
                for f in os.listdir(CKPT_DIR):
                    fp = os.path.join(CKPT_DIR, f)
                    if f.endswith(".safetensors") and os.path.islink(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
        except Exception:
            pass

    def _vram_critical(self, threshold=0.90):
        """Return True if VRAM usage exceeds threshold (best-effort; False on any error)."""
        try:
            r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
            if r.status_code != 200:
                return False
            devs = r.json().get("devices", [])
            if not devs:
                return False
            d = devs[0]
            total = d.get("vram_total", 0) or 0
            free = d.get("vram_free", 0) or 0
            if total <= 0:
                return False
            return (1 - (free / total)) > threshold
        except Exception:
            return False

    def _start_generate(self, mode=None):
        import time
        logging.info("Generate button clicked")
        if mode and mode not in ("txt2img", "img2img", "upscale"):
            self._set_status("Error: unknown mode '%s'" % mode)
            return
        # Active VRAM guard: never OOM the host — defer when VRAM is critical.
        if self._vram_critical(0.90):
            self._set_status("VRAM critical (>90%) - wait for VRAM to clear before generating")
            return
        target_mode = mode if mode and mode in ("txt2img", "img2img", "upscale") else self.current_tab
        if target_mode not in ("txt2img", "img2img", "upscale"):
            self._set_status("Error: unknown mode '%s'" % target_mode)
            return
        if time.time() - getattr(self, '_last_generate', 0) < 1.0:
            logging.info("Generate debounced")
            return
        if getattr(self, '_generate_lock', False):
            logging.info("Generate locked")
            return
        self._last_generate = time.time()
        self._generate_lock = True
        try:
            logging.info("Starting generate workflow")
            if hasattr(self, '_generate') and callable(getattr(self, '_generate')):
                self._generate(target_mode)
                return
            if hasattr(self, 'gen_btn') and self.gen_btn:
                self.gen_btn.configure(state="disabled")
            self._set_status("Building workflow...")
            try:
                wf, ckpt = self._build_workflow(target_mode)
                self._ensure_model_loaded(ckpt)
                self._set_status("Generating...")
                payload = {"prompt": json.dumps(wf), "client_id": "hermes_comfyui_uncensored"}
                r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
                if r.status_code != 200:
                    self._set_status("Queue failed: HTTP %d" % r.status_code)
                    if hasattr(self, 'gen_btn') and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self.last_prompt_id = r.json().get("prompt_id")
                self._gen_mode = self.current_tab
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Cancel", command=self._cancel_generate)
                self._poll_attempts = 0
                self.root.after(200, self._poll_history)
            except Exception as e:
                logging.error("Generate error: %s", e)
                self._set_status("Generate error: %s" % str(e)[:40])
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal")
        except Exception as e:
            logging.error("Generate outer error: %s", e)
            self._set_status("Generate error: %s" % str(e)[:40])
            if hasattr(self, 'gen_btn') and self.gen_btn:
                self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal")
        finally:
            self._generate_lock = False

    def _cancel_generate(self):
        if not self.root or not self.root.winfo_exists():
            return
        if self.last_prompt_id:
            try:
                requests.post(COMFYUI_URL + "/interrupt", timeout=5)
            except Exception:
                pass
        self._poll_attempts = 100
        if hasattr(self, 'gen_btn') and self.gen_btn.winfo_exists():
            self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
        self._generate_lock = False

    def _poll_history(self):
        """FIX: poll ComfyUI history with retries until done, error, or timeout."""
        if self._poll_attempts > 150:
            self._set_status("Polling timed out")
            self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
            return
        self._poll_attempts += 1
        try:
            r = requests.get(COMFYUI_URL + "/history", timeout=5)
            if r.status_code == 200:
                hist = r.json()
                for item_id, item in hist.items():
                    status = item.get("status", {})
                    if status.get("completed") and item_id == self.last_prompt_id:
                        outs = item.get("outputs", {})
                        for node_id, node_out in outs.items():
                            if node_out.get("type") == "output" and "images" in node_out:
                                for img_data in node_out["images"]:
                                    self._show_image(img_data)
                    elif status.get("error"):
                        self._set_status("Generation error")
                        self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
                        return
        except Exception:
            pass
        self.root.after(500, self._poll_history)

    def _show_image(self, img_meta):
        mode = getattr(self, "_gen_mode", self.current_tab)
        try:
            fn = img_meta.get("filename")
            sub = img_meta.get("subfolder", "")
            url = COMFYUI_URL + "/view?filename=" + fn + "&subfolder=" + sub + "&type=output"
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return
            import io
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            self.current_pil = img
            self._display_preview(img)
            out_path = os.path.join(OUTPUT_DIR, fn)
            with open(out_path, "wb") as fh:
                fh.write(r.content)
            self._add_thumb(out_path, mode)
            fmt = self.vars.get(mode, {}).get("format")
            fmt_val = fmt.get() if fmt else "PNG"
            if fmt_val == "Game Texture (TGA)":
                self._convert_to_game_texture(out_path)
            self._save_history(mode, fn)
            if self.current_tab == "gallery":
                self._refresh_gallery()
            self._set_status("Done")
            # Re-enable the Generate button after a successful generation
            if hasattr(self, "gen_btn") and self.gen_btn.winfo_exists():
                self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
            self._generate_lock = False
        except Exception as e:
            self._set_status("Show image error: %s" % str(e)[:30])

    def _display_preview(self, img):
        disp = img.copy()
        disp.thumbnail((360, 360))
        tkimg = ImageTk.PhotoImage(disp)
        self.preview_label.configure(image=tkimg, text="")
        self.preview_label.image = tkimg
        # also update the large preview window in the Generate view
        try:
            big = img.copy()
            big.thumbnail((320, 360))
            bimg = ImageTk.PhotoImage(big)
            self.preview_big.configure(image=bimg, text="")
            self.preview_big.image = bimg
        except Exception:
            pass

    def _add_thumb(self, path, mode):
        img = Image.open(path)
        img.thumbnail((64, 64))
        tkimg = ImageTk.PhotoImage(img)
        lbl = ctk.CTkLabel(self.thumb_frame, image=tkimg, text="", width=64, height=64,
                           fg_color=BG_CARD, corner_radius=4)
        lbl.image = tkimg
        lbl.grid(row=0, column=self._thumb_count % 6, padx=4, pady=4, sticky="nw")
        self._thumb_count += 1
        lbl.bind("<Button-1>", lambda e, fp=path: os.startfile(fp))
        self.thumb_frame.columnconfigure(self._thumb_count % 6, weight=1)
        # Also feed the Recent strip inside the preview pane
        try:
            rim = Image.open(path)
            rim.thumbnail((96, 96))
            rimg = ImageTk.PhotoImage(rim)
            rl = ctk.CTkLabel(self.preview_thumbs, image=rimg, text="", width=88, height=88,
                              fg_color=BG_CARD, corner_radius=6)
            rl.image = rimg
            rl.grid(row=self._preview_thumb_count // 3, column=self._preview_thumb_count % 3,
                    padx=4, pady=4, sticky="nw")
            self._preview_thumb_count += 1
            rl.bind("<Button-1>", lambda e, fp=path: os.startfile(fp))
            self.preview_thumbs.update_idletasks()
        except Exception:
            pass

    def _convert_to_game_texture(self, src_path):
        try:
            img = Image.open(src_path).convert("RGB")
            w, h = img.size
            pw = 1
            while pw < w:
                pw <<= 1
            ph = 1
            while ph < h:
                ph <<= 1
            canvas = Image.new("RGB", (pw, ph), (0, 0, 0))
            canvas.paste(img, ((pw - w) // 2, (ph - h) // 2))
            tga = src_path.replace(".png", "_PoT.tga").replace(".jpg", "_PoT.tga").replace(".jpeg", "_PoT.tga")
            canvas.save(tga)
        except Exception as e:
            self._set_status("Game texture error: %s" % str(e)[:30])

    def _load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE) as fh:
                    self.history = json.load(fh)
        except Exception:
            self.history = []

    def _prompt_for_mode(self, mode):
        """Return the prompt text for the given mode's dedicated prompt box."""
        if mode == "img2img" and hasattr(self, "img2img_prompt_entry"):
            return self.img2img_prompt_entry.get("1.0", "end").strip()
        if mode == "upscale" and hasattr(self, "upscale_prompt_entry"):
            return self.upscale_prompt_entry.get("1.0", "end").strip()
        if hasattr(self, "prompt_entry"):
            return self.prompt_entry.get("1.0", "end").strip()
        return ""

    def _save_history(self, mode, filename):
        m = self.vars.get(mode, {})
        width_var = m.get("width", tk.StringVar())
        height_var = m.get("height", tk.StringVar())
        steps_var = m.get("steps", tk.StringVar())
        cfg_var = m.get("cfg", tk.StringVar())
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": self.model_var.get(),
            "prompt": self._prompt_for_mode(mode),
            "width": int(width_var.get()) if "width" in m else 0,
            "height": int(height_var.get()) if "height" in m else 0,
            "steps": int(steps_var.get()) if "steps" in m else 0,
            "cfg": float(cfg_var.get()) if "cfg" in m else 0,
            "output": filename,
        }
        self.history.append(entry)
        try:
            with open(HISTORY_FILE, "w") as fh:
                json.dump(self.history, fh, indent=2)
        except Exception as e:
            self._set_status("History save error: %s" % str(e)[:20])

    def _set_status(self, msg, level=logging.INFO):
        """Thread-safe status update.

        The actual widget mutation is ALWAYS marshaled to the Tk main thread
        via root.after(0, ...). Calling Tkinter widget methods from a worker
        thread (backend / VRAM / error monitor) can corrupt the Tcl
        interpreter and freeze the UI ("Not Responding"). This fix eliminates
        that class of deadlock regardless of which thread calls _set_status.
        """
        try:
            logger.log(level, msg)
        except Exception:
            pass
        # Marshal the GUI write to the main thread cleanly
        try:
            if hasattr(self, "root") and self.root and self.root.winfo_exists():
                self.root.after(0, self._set_status_gui, msg, level)
        except Exception:
            pass

    def _set_status_gui(self, msg, level):
        try:
            if not hasattr(self, "status_label") or not self.status_label.winfo_exists():
                return
            truncated = msg[:33] + "..." if len(msg) > 36 else msg
            if level >= logging.WARNING:
                self.status_label.configure(text=truncated, text_color=("#FFAAAA", "#FFAAAA"))
            else:
                self.status_label.configure(text=truncated, text_color=TEXT)
        except Exception:
            pass

    def on_close(self):
        self._running = False
        if self.backend and self.backend.poll() is None:
            try:
                self.backend.terminate()
            except Exception:
                pass
        self._cleanup_symlinks()
        self.root.destroy()

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self.root, height=36, fg_color=("#141416", "#141416"), corner_radius=0)
        bar.grid(row=1, column=1, padx=12, pady=(0, 8), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        status_container = ctk.CTkFrame(bar, fg_color=("#1b1b1e", "#1b1b1e"), corner_radius=6)
        status_container.grid(row=0, column=0, padx=4, pady=2, sticky="ew")
        status_container.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(status_container, text="Ready", anchor="w",
                                         font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        self.status_label.grid(row=0, column=0, padx=12, pady=4, sticky="w")

        # Dummy compatibility attributes to preserve legacy call sites without error
        self.preview_label = self.status_label
        self.thumb_frame = ctk.CTkFrame(bar)
        self._thumb_count = 0

    # ------------------------------------------------------------------
    def _start_header_gradient(self):
        """FIX: initialize hue and kick off the header gradient animation loop."""
        self._hue = 0.0
        self._animate_gradient()

    def _paint_header(self):
        """Paint the header gradient background."""
        try:
            w = self.root.winfo_width() - 230
            h = 56
            if w < 10:
                self.root.after(50, self._paint_header)
                return
            c0 = (20, 20, 24)
            c1 = (40, 40, 46)
            grad = make_gradient(w, h, c0, c1, angle=90)
            photo = ImageTk.PhotoImage(grad)
            self._header_img = photo
            self.header.configure(image=photo)
        except Exception:
            pass

    def _animate_gradient(self):
        """Subtle hue-shift animation on the header."""
        try:
            self._hue = (self._hue + 0.5) % 360
            w = self.root.winfo_width() - 230
            h = 56
            c0 = _hue_shift_color((30, 30, 34), self._hue)
            c1 = _hue_shift_color((50, 50, 56), self._hue)
            grad = make_gradient(w, h, c0, c1, angle=90)
            photo = ImageTk.PhotoImage(grad)
            self._header_img = photo
            self.header.configure(image=photo)
        except Exception:
            pass
        self.root.after(50, self._animate_gradient)

    def _swap_dimensions(self):
        try:
            mode = self.current_tab
            m = self.vars.get(mode, self.vars["txt2img"])
            if "width" in m and "height" in m:
                w_val = m["width"].get()
                h_val = m["height"].get()
                m["width"].set(h_val)
                m["height"].set(w_val)
                self._set_status(f"Swapped dimensions: {h_val}x{w_val}")
        except Exception as e:
            logging.error("Swap dimensions error: %s", e)

    def _open_last_preview(self):
        try:
            if hasattr(self, "_last_output_file") and self._last_output_file and os.path.exists(self._last_output_file):
                os.startfile(self._last_output_file)
            elif os.path.isdir(OUTPUT_DIR):
                imgs = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".tga"))]
                if imgs:
                    imgs.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
                    os.startfile(os.path.join(OUTPUT_DIR, imgs[0]))
        except Exception as e:
            logging.error("Open preview error: %s", e)

    # ------------------------------------------------------------------
    def _build_preview_pane(self):
        """Large preview window in the right column of the Generate view.

        Shows the last generated image (or a clean placeholder) plus a
        thumbnail strip of recent outputs. Hidden when Gallery/Settings
        nav is active (those views own the right column instead).
        """
        pane = ctk.CTkFrame(self.top, fg_color=BG_CARD, corner_radius=10)
        pane.grid(row=0, column=1, rowspan=3, padx=(12, 0), pady=(8, 16), sticky="nsew")
        pane.grid_columnconfigure(0, weight=1)
        pane.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(pane, text="Preview", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self.preview_big = ctk.CTkLabel(pane,
            text="No image yet.\nGenerate to preview your result here.",
            height=360, corner_radius=8, fg_color=BG_CARD_ALT,
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=11), justify="center")
        self.preview_big.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")
        self.preview_big.grid_propagate(False)
        self.preview_big.bind("<Button-1>", lambda e: self._open_last_preview())

        # thumbnail strip
        ctk.CTkLabel(pane, text="Recent", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT_MUTED).grid(row=2, column=0, padx=12, pady=(2, 2), sticky="w")
        self.preview_thumbs = ctk.CTkScrollableFrame(pane, fg_color=BG_CARD_ALT,
                                                    corner_radius=8, height=120)
        self.preview_thumbs.grid(row=3, column=0, padx=12, pady=(0, 10), sticky="nsew")
        self.preview_thumbs.grid_columnconfigure(0, weight=1)
        enable_auto_hide_scrollbar(self.preview_thumbs)

        self._preview_thumb_count = 0
        self.preview_pane = pane
        # pre-populate Recent strip with existing outputs
        self.root.after(300, self._load_recent_into_preview)

    def _load_recent_into_preview(self):
        """Populate the preview pane's Recent strip from OUTPUT_DIR."""
        try:
            if not os.path.isdir(OUTPUT_DIR):
                return
            imgs = [f for f in os.listdir(OUTPUT_DIR)
                    if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith("input")]
            imgs.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
            for f in imgs[:9]:
                self._add_thumb(os.path.join(OUTPUT_DIR, f), "txt2img")
        except Exception:
            pass

    def _build_sidebar_buttons(self):
        cmd = ctk.CTkFrame(self.top, fg_color="transparent", corner_radius=0)
        cmd.grid(row=2, column=0, columnspan=1, padx=12, pady=4, sticky="ew")
        for i in range(4):
            cmd.grid_columnconfigure(i, weight=1)

        btns = [
            ("Open Output", lambda: self._open_dir(OUTPUT_DIR)),
            ("Restart Backend", self._restart_server),
            ("View Log", self._view_log),
            ("Save History", self._save_history_simple),
        ]
        for i, (txt, fn) in enumerate(btns):
            b = ctk.CTkButton(cmd, text=txt, height=32, corner_radius=8,
                              fg_color=BG_CARD_ALT, text_color=TEXT,
                              hover_color=BRAND_HOVER, command=fn)
            b.grid(row=0, column=i, padx=4, pady=2, sticky="nsew")

    def _open_dir(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            os.startfile(path)
        except Exception as e:
            self._set_status("Open dir error: %s" % str(e)[:30])

    def _view_log(self):
        self._show_log_window(LOG_FILE, "ComfyUI — Application Log")

    def _show_log_window(self, path, title):
        """Open a real, resizable in-app window (like Hermes) showing a log file
        or arbitrary text, with a scrollable text area and a refresh button."""
        try:
            # Only one instance per path
            attr = "_logwin_%s" % abs(hash(path))
            if hasattr(self, attr):
                try:
                    if getattr(self, attr).winfo_exists():
                        getattr(self, attr).focus()
                        return
                except Exception:
                    pass
            win = ctk.CTkToplevel(self.root)
            win.title(title)
            win.geometry("720x520")
            win.minsize(420, 280)
            win.resizable(True, True)  # user can resize freely, like Hermes windows
            win.attributes("-topmost", False)
            setattr(self, attr, win)

            header = ctk.CTkFrame(win, fg_color=("transparent", "transparent"), corner_radius=0)
            header.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="ew")
            header.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(header, text=os.path.basename(path), font=self.FONT_SMALL_BOLD,
                         text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w")
            btn_row = ctk.CTkFrame(header, fg_color=("transparent", "transparent"))
            btn_row.grid(row=0, column=1, sticky="e")
            ctk.CTkButton(btn_row, text="Refresh", width=80, height=26,
                          font=self.FONT_SMALL, command=lambda: _load_text()).grid(row=0, column=0, padx=2)
            ctk.CTkButton(btn_row, text="Open Folder", width=90, height=26,
                          font=self.FONT_SMALL,
                          command=lambda: os.startfile(os.path.dirname(path))).grid(row=0, column=1, padx=2)

            textbox = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=11),
                                    wrap="none", fg_color=("#0f0f12", "#0f0f12"),
                                    text_color="#d8d8e0")
            textbox.grid(row=1, column=0, padx=10, pady=(6, 10), sticky="nsew")
            win.grid_rowconfigure(1, weight=1)
            win.grid_columnconfigure(0, weight=1)

            def _load_text():
                try:
                    if os.path.exists(path):
                        with open(path, "r", errors="replace") as fh:
                            content = fh.read()
                    else:
                        content = "(file not found: %s)" % path
                except Exception as e:
                    content = "Error reading %s: %s" % (path, e)
                textbox.delete("1.0", "end")
                textbox.insert("1.0", content)
                textbox.see("end")

            _load_text()
            win.protocol("WM_DELETE_WINDOW", lambda: (delattr(self, attr), win.destroy()))
        except Exception as e:
            self._set_status("Log window error: %s" % str(e)[:30])

    def _save_history_simple(self):
        self._save_history(self.current_tab, "history_snapshot.json")
        self._set_status("History saved (%d entries)" % len(self.history))

    # ------------------------------------------------------------------
    def _on_model(self, _=None):
        """Update model-specific params on the CURRENT tab, not just txt2img."""
        import time
        try:
            logging.info("Model changed: %s", self.model_var.get())
            if time.time() - self._last_model_switch < 0.2:
                return
            self._last_model_switch = time.time()
            name = self.model_var.get()
            if name in MODELS:
                model = MODELS[name]
                m = self.vars.get(self.current_tab, self.vars["txt2img"])
                m["width"].set(str(model["w"]))
                m["height"].set(str(model["h"]))
        except Exception as e:
            logging.error("Model change error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

    def _on_preset(self, _=None):
        import time
        try:
            if time.time() - self._last_preset_switch < 0.2:
                return
            self._last_preset_switch = time.time()
            name = self.preset_var.get()
            if name in PRESETS:
                p = PRESETS[name]
                if p["model"] in MODELS:
                    self.model_var.set(p["model"])
                    model = MODELS[p["model"]]
                    m = self.vars.get(self.current_tab, self.vars["txt2img"])
                    m["width"].set(str(model["w"]))
                    m["height"].set(str(model["h"]))
                    m["steps"].set(str(model["steps"]))
                    m["cfg"].set(str(model["cfg"]))
                self.prompt_entry.delete("1.0", "end")
                self.prompt_entry.insert("1.0", p["prompt"])
                self.neg_entry.delete("1.0", "end")
                self.neg_entry.insert("1.0", p["neg"])
                # Apply optional Output Format override (e.g. Game Texture preset)
                if "format" in p and self.current_tab in self.vars and "format" in self.vars[self.current_tab]:
                    self.vars[self.current_tab]["format"].set(p["format"])
                self._set_status(f"Applied preset: {name}")
        except Exception as e:
            logging.error("Preset apply error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

    # ------------------------------------------------------------------
    def _pick_input(self):
        if not _resolve_has_video():
            path = filedialog.askopenfilename(
                title="Select Image",
                filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")])
        else:
            path = filedialog.askopenfilename(
                title="Select Image or Video",
                filetypes=[("Image/Video",
                            "*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.avi *.mkv *.webm"),
                           ("All Files", "*.*")])
        if path:
            self._stage_input(path)

    def _stage_input(self, path):
        """Video frame staged - generate on Image to Image"""
        ext = os.path.splitext(path)[1].lower()
        video_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
        if ext in video_exts:
            if not _resolve_has_video():
                self._set_status("imageio/ffmpeg not available")
                return
            self._set_status("Extracting first frame from video...")
            try:
                reader = iio.get_reader(path, "ffmpeg")
                frame = reader.get_data(0)
                reader.close()
                img = Image.fromarray(frame).convert("RGB")
                img.save(os.path.join(INPUT_DIR, "video_frame_0.png"))
                self.input_image_path = os.path.join(INPUT_DIR, "video_frame_0.png")
                self._show_thumb(self.input_preview, img)
                self._set_status("Video frame staged - generate on Image to Image")
            except Exception as e:
                self._set_status("Video frame extract failed: %s" % str(e)[:30])
        else:
            try:
                img = Image.open(path).convert("RGB")
                self.input_image_path = path
                self._show_thumb(self.input_preview, img)
                self._set_status("Image: %s" % os.path.basename(path)[:30])
            except Exception as e:
                self._set_status("Image load failed: %s" % str(e)[:30])

    def _pick_upscale(self):
        path = filedialog.askopenfilename(
            title="Select Image to Upscale",
            filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")])
        if path:
            try:
                img = Image.open(path).convert("RGB")
                self.input_image_path = path
                self._show_thumb(self.up_preview, img)
                self._set_status("Upscale: %s" % os.path.basename(path)[:30])
            except Exception as e:
                self._set_status("Image load failed: %s" % str(e)[:30])

    def _show_thumb(self, label, img):
        img.thumbnail((200, 150))
        tkimg = ImageTk.PhotoImage(img)
        label.configure(image=tkimg, text="")
        label.image = tkimg


# ------------------------------------------------------------------
def _crash_hook(exc_type, exc_value, exc_tb):
    tb = traceback.format_exception(exc_type, exc_value, exc_tb)
    try:
        with open(os.path.join(LOG_DIR, "ComfyUI_crash.txt"), "w") as fh:
            fh.write("CRASH\n")
            fh.write("\n".join(tb))
            fh.write("\nUnhandled crash: %s" % exc_value)
    except Exception:
        pass
    logging.error("Unhandled crash: %s" % exc_value)


def main():
    sys.excepthook = _crash_hook
    root = ctk.CTk()
    root.title("ComfyUI Uncensored")
    root.configure(bg="#141416")
    app = ComfyUIApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.bind_all("<Control-e>", lambda e: app._start_generate())
    root.after(100, lambda: app._paint_header())
    root.after(500, lambda: app._start_backend_threads())
    root.mainloop()


if __name__ == "__main__":
    main()
