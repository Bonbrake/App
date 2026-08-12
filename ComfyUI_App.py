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

# Module-level alias so both _resolve_comfyui_portable_dir() (which rebinds
# `os` as `_os` locally) and module-level path constants can use `_os`.
_os = os

def _safe_mtime(path):
    """Stat mtime, tolerating files that vanish mid-scan (race during gen/delete).
    Returns 0.0 if missing so the sort never raises and aborts the gallery refresh."""
    try:
        return _os.path.getmtime(path)
    except OSError:
        return 0.0


def _safe_int(text, default=0, lo=None, hi=None):
    """Parse an int from arbitrary UI text, clamping to [lo,hi] and never raising.

    Prevents a ValueError crash (and a stuck 'Generating...' button) when the
    user types non-numeric / empty / out-of-range values into numeric fields.
    """
    try:
        v = int(str(text).strip())
    except (ValueError, TypeError):
        try:
            v = int(round(float(str(text).strip())))
        except (ValueError, TypeError):
            return default
    if lo is not None and v < lo:
        v = lo
    if hi is not None and v > hi:
        v = hi
    return v


def _safe_float(text, default=0.0, lo=None, hi=None):
    """Parse a float from arbitrary UI text, clamping to [lo,hi] and never raising."""
    try:
        v = float(str(text).strip())
    except (ValueError, TypeError):
        return default
    if lo is not None and v < lo:
        v = lo
    if hi is not None and v > hi:
        v = hi
    return v

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter.font as tkfont

import requests
from config import ConfigManager
try:
    from PIL import Image, ImageTk, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:
    Image = None
    ImageTk = None

from glass import AcrylicBackground, make_gradient, _hue_shift_color

from comfyui_desktop.diagnostics import (
    dump_report, DIAG_DIR, breadcrumb, _last_crash_ts,
    bundle_button_command, diagnostics_button_command
)

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
# Auto-detect the local ComfyUI portable install instead of hardcoding a
# user-specific path, so the published repo runs on any machine.
def _resolve_comfyui_portable_dir():
    import os as _os
    # Explicit override always wins (honor user intent even if not yet created).
    env = _os.environ.get("COMFYUI_PORTABLE_DIR")
    if env:
        return _os.path.normpath(_os.path.expanduser(_os.path.expandvars(env)))
    _here = _os.path.dirname(_os.path.abspath(__file__))
    for cand in (_os.path.join(_here, "..", "ComfyUI_windows_portable"),
                 _os.path.join(_here, "..", "..", "ComfyUI_windows_portable"),
                 _os.path.join(_os.getcwd(), "ComfyUI_windows_portable"),
                 r"C:\ComfyUI-Desktop"):
        if _os.path.isdir(cand):
            return _os.path.normpath(cand)
    return r"C:\ComfyUI-Desktop"

_PORTABLE_DIR = _resolve_comfyui_portable_dir()
COMFYUI_DIR = os.path.join(_PORTABLE_DIR, "ComfyUI_windows_portable", "ComfyUI")
_embed_py = os.path.join(_PORTABLE_DIR, "ComfyUI_windows_portable", "python_embeded", "python.exe")
PYTHON_PATH = _embed_py if os.path.exists(_embed_py) else sys.executable
MAIN_PY = "main.py"
COMFYUI_URL = "http://127.0.0.1:8188"

def _get_config_path():
    """Path to app config JSON (window geometry, last model, etc.).

    In a frozen one-file build, __file__ lives inside the temp _MEIxxxx
    extraction dir that PyInstaller DELETES on exit — writing there means
    settings never survive a restart. So when frozen, resolve next to the
    real executable (stable, user-writable) instead. Additive + safe.
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "app_config.json")


def _open_file(path):
    """Open a file with the system default application."""
    try:
        import subprocess, platform as _pf
        if _pf.system() == "Windows":
            os.startfile(path)
        elif _pf.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _open_folder(path):
    """Open a folder in the system file explorer."""
    try:
        import subprocess, platform as _pf
        if _pf.system() == "Windows":
            os.startfile(path)
        elif _pf.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
OUTPUT_DIR = os.path.normpath(os.path.expanduser(r"~/Pictures/ComfyUI_Generated"))
# Stage img2img/upscale inputs into ComfyUI's OWN input directory so LoadImage
# can read them. ComfyUI is launched with default args (no --input-directory),
# so it reads from <COMFYUI_DIR>/input/. Staging to Pictures/.../input/ (the old
# value) made LoadImage fail with "Invalid image file" — the files were never
# where ComfyUI looked. Source: verified against live /object_info/LoadImage.
INPUT_DIR = os.path.join(COMFYUI_DIR, "input")
LOG_DIR = os.path.normpath(os.path.expanduser(r"~/Logs"))
LOG_FILE = os.path.join(LOG_DIR, "ComfyUI_App.log")
SERVER_LOG_FILE = os.path.join(LOG_DIR, "comfyui_server.log")
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
    "prompt": "a striking photorealistic portrait, sharp facial details, natural skin texture, soft studio rim light, shallow depth of field, 85mm lens, captured with a DSLR, 8k, ultra detailed, cinematic color grade",
    "neg": "blurry, lowres, deformed, extra limbs, bad anatomy, watermark, text, cartoon, painting, oversaturated, plastic skin",
    },
    "Cinematic Wide": {
        "model": "Juggernaut XL",
        "prompt": "epic cinematic wide establishing shot of a lone figure on a windswept cliff at golden hour, anamorphic lens flare, volumetric atmospheric haze, dramatic chiaroscuro lighting, film still, teal and orange grade, highly detailed environment",
        "neg": "blurry, deformed, watermark, text, low quality, oversaturated, flat lighting, extra limbs",
    },
    "Anime Character": {
        "model": "Pony Diffusion V6 XL",
        "prompt": "anime style illustration of a cheerful magical girl, big expressive eyes, flowing hair with wind motion, vibrant cel-shaded colors, clean lineart, dynamic pose, detailed clothing, sparkle effects, studio anime key visual",
        "neg": "realistic, photo, 3d render, blurry, lowres, deformed, watermark, text, extra limbs",
    },
    "Game Texture": {
        "model": "Pony Diffusion V6 XL",
        "prompt": "game texture, seamless tileable diffuse map, clean flat shading, hand-painted cell-shaded style, consistent pixel density, UV-friendly, no stretching, neutral lighting, game-ready asset",
        "neg": "realistic, photo, photographic, blurry, lowres, distorted seams, stretching, watermark, text, jpeg artifacts",
        "format": "Game Texture (TGA)",
    },
    "Product Shot": {
        "model": "epiCRealism XL",
        "prompt": "professional product photography of a luxury perfume bottle on a reflective black surface, three-point studio lighting, soft shadows, crisp reflections, advertising render, 8k, commercial quality, shallow depth of field",
        "neg": "blurry, lowres, deformed, watermark, text, background clutter, oversaturated, amateur",
    },
    "Fantasy Art": {
        "model": "Juggernaut XL",
        "prompt": "fantasy concept art of an ancient floating castle above a sea of clouds, god rays, intricate architecture, painterly matte-painting style, rich complementary colors, highly detailed, artstation trending",
        "neg": "blurry, lowres, deformed, watermark, text, photo, oversaturated, flat",
    },
}

SAMPLERS = ["dpmpp_2m", "dpmpp_sde", "euler", "euler_ancestral", "dpmpp_2m_sde", "ddim"]
SCHEDULERS = ["karras", "normal", "simple", "ddim_uniform", "beta"]
UPSCALE_MODELS = ["4x-UltraSharp.pth", "4x_NMKD-Siax_200k.pth", "ESRGAN_4x.pth"]
DEFAULT_NEG = "blurry, lowres, deformed, watermark, text"

# ---- MiniMax H3 video resolution presets (width, height) ----
# 8GB VRAM (RTX 2070S) safe ceiling verified: 512x288 fits (~1.7GB VRAM req),
# 640x360 OOMs at ~7.6GB. comfy_kitchen flash-attn is disabled on torch2.13/sm75,
# so attention is eager SDPA (memory scales with tokens^2). Keep presets <= 512x288.
VIDEO_RESOLUTIONS = {
    "240p (512x288)": (512, 288),
    "288p (576x324)": (576, 324),
    "360p (640x360)": (640, 360),
}

# Aspect-ratio presets (research: Kling/Runway/Hailuo/Pika/Luma all expose AR).
# Maps to width/height that H3 accepts (multiple of 32, short edge ~768 max).
VIDEO_ASPECT_RATIOS = {
    "16:9 Widescreen": (1344, 768),
    "9:16 Portrait": (768, 1344),
    "1:1 Square": (1024, 1024),
    "4:3 Standard": (1152, 864),
}
# Camera-motion presets (research: camera move lock is a top user expectation;
# H3 doc confirms R2V can lock a "camera move". Implemented as structured prompt suffix.)
VIDEO_CAMERA_MOTIONS = {
    "Static": "",
    "Slow Zoom In": "cinematic slow zoom in, camera gradually pushing forward",
    "Slow Zoom Out": "cinematic slow zoom out, camera pulling back",
    "Pan Left": "camera panning slowly to the left, revealing the scene",
    "Pan Right": "camera panning slowly to the right, revealing the scene",
    "Orbit": "camera slowly orbiting around the subject",
    "Truck Up": "camera tilting upward, revealing the upper environment",
    "Handheld": "subtle handheld camera movement, natural微 shake",
}

# Sampler names available in the bundled ComfyUI (res_multistep = transcript default).
VIDEO_SAMPLERS = ["res_multistep", "res_multistep_cfg_pp", "res_multistep_ancestral",
                  "res_multistep_ancestral_cfg_pp", "euler", "dpmpp_2m"]
# Attention backends (MiniMaxH3AttentionConfig). 'auto' picks best available on RTX 2070S.
VIDEO_ATTENTION_BACKENDS = ["auto", "sageattn3", "sageattn2", "sageattn1",
                            "flash_attention", "sdpa", "xformers", "sdpa_math"]
# Duration presets -> approx seconds (17 frames/block @ 24fps).
VIDEO_DURATIONS = {"3s": 3, "5s": 5, "9s": 9, "14s": 14}
# Refine/upscale target scales (ffmpeg lanczos). 1x = original.
VIDEO_UPSCALE_SCALES = ["1x (original)", "1.5x", "2x", "2.5x", "3x"]

# ---- Tooltips ----
TOOLTIPS = {
    "Prompt": ("Prompt", "Describe the image you want to create. Be specific — include subject, style, lighting, and mood for best results."),
    "Negative Prompt": ("Negative Prompt", "List things to exclude from your image. Common: blurry, low quality, extra fingers, distorted face, watermark."),
    "Width": ("Width (px)", "Output image width. Use 768 or 1024 for SDXL models. Larger = more VRAM usage and slower generation."),
    "Height": ("Height (px)", "Output image height. Standard ratios: 1024×1024 (square), 768×1344 (portrait), 1344×768 (landscape)."),
    "Steps": ("Sampling Steps", "Number of denoising iterations. More steps = sharper detail but slower. Sweet spot: 25–35 for quality, 15–20 for speed."),
    "CFG": ("CFG Scale", "Controls how closely the image follows your prompt. Low (3–5) = creative/loose. High (7–12) = strict/literal. Default: 7."),
    "Seed": ("Seed", "Controls randomness. Same seed + same settings = same image. Set to 0 for a random seed each time."),
    "Batch": ("Batch Size", "Number of images to generate at once. Higher values use more VRAM. Start with 1 on 8GB cards."),
    "Sampler": ("Sampler Algorithm", "The math behind the denoising process. dpmpp_2m is fast and high-quality. euler_ancestral adds more variation."),
    "Scheduler": ("Noise Scheduler", "How noise is reduced across steps. 'karras' produces the cleanest results for most models."),
    "Model": ("AI Model", "The checkpoint model determines the art style and capabilities. Each model is trained on different data."),
    "Preset": ("Quick Preset", "Pre-configured settings optimized for common use cases. Applies resolution, steps, and CFG in one click."),
    "Generate": ("Generate Image", "Start generating your image with the current settings. Keyboard shortcut: Ctrl+E."),
    "Output Format": ("Output Format", "PNG = lossless quality for sharing. Game Texture = power-of-two TGA for game engine import."),
    "Denoise": ("Denoise Strength", "How much to transform the input image. 0.3 = subtle edit, 0.7 = major change, 1.0 = completely new image."),
    "Upscale Model": ("Upscale Model", "AI upscaling model. RealESRGAN_x4plus is best for photos, RealESRGAN_x4plus_anime6B for anime/art."),
    "Scale": ("Scale Factor", "How much to enlarge the image. 2x doubles size, 4x quadruples. 4x works well on 8GB VRAM."),
    "Input Image": ("Input Image", "Upload a source image for img2img transformation. The AI will use it as a starting point."),
    "Model Strength": ("Model Weight", "Scales the checkpoint model influence. Lower values reduce the model's effect. Default: 1.0."),
    "CLIP Strength": ("CLIP Text Weight", "Scales the text encoder strength. Lower = less prompt adherence, more model freedom. Default: 1.0."),
    "VRAM Threshold": ("VRAM Guard", "Pauses generation if GPU memory usage exceeds this limit. Prevents out-of-memory crashes."),
    "Tooltips": ("Hover Help", "Toggle these popup descriptions on or off. Disable once you're familiar with the controls."),
    "GPU Mode": ("GPU Optimization", "Memory optimization for your GPU. Use 'Low VRAM' for 4–6GB cards, 'Default' for 8GB+, 'CPU' for no GPU."),
    "Launch Args": ("Custom Launch Args", "Advanced: extra command-line flags passed to the ComfyUI server on restart. Separate with spaces."),
    "Random Seed": ("Random Seed", "When enabled, generates a new random seed for each image. Disable to reuse the seed value above."),
}

# ---- Design System Tokens (High-Contrast Periwinkle / Slate Palette) ----
ctk.set_appearance_mode("system")
ctk.set_widget_scaling(1.0)

# QoL (2026-08-09): make the frozen app DPI-aware so text/widgets render crisp
# at the user's real Windows scaling (150% etc.) instead of tiny + blurry.
# PROCESS_PER_MONITOR_DPI_AWARE = 2. Guarded: harmless if shcore is unavailable.
try:
    import ctypes as _ct
    _ct.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

BG_APP = ("#F1F5F9", "#0F0F12")
BG_SIDEBAR = ("#E2E8F0", "#14141A")
BG_CARD = ("#FFFFFF", "#1A1A24")
BG_CARD_ALT = ("#F8FAFC", "#22222E")
BORDER = ("#94A3B8", "#2A2A3C")
TEXT = ("#020617", "#F8FAFC")
TEXT_MUTED = ("#334155", "#94A3B8")
BRAND = ("#7E22CE", "#A855F7")
BRAND_HOVER = ("#6B21A8", "#9333EA")
ACCENT2 = ("#9333EA", "#C084FC")
ACCENT2_HOVER = ("#7E22CE", "#A855F7")
DROPDOWN_FG = ("#FFFFFF", "#1E1E2E")
DROPDOWN_TEXT = ("#020617", "#F8FAFC")
DROPDOWN_HOVER = ("#E2E8F0", "#2D2D3F")
TOOLTIP_DELAY = 500
TOOLTIP_HIDE_DELAY = 100


# ---- ToolTip ----
class ToolTip:
    """Hover tooltip — robust CTk 6.0-compatible implementation."""
    enabled = True

    def __init__(self, widget, title, description=None, delay=TOOLTIP_DELAY):
        # Two call conventions exist across this file and BOTH must keep working:
        #   3-arg: ToolTip(w, *TOOLTIPS["Key"])  -> ("Title", "Body text")
        #   2-arg: ToolTip(w, "Body text")       -> body only, no bold heading
        # PRESERVED_LEGACY: the 2-arg form (34 call sites in the video tabs)
        # previously raised TypeError: missing argument 'description', which
        # aborted _build_video_tab / _build_video_v2v_tab / _build_video_refine_tab
        # mid-build and left those tabs half-rendered. Making `description`
        # optional keeps every existing call site valid without editing them.
        if description is None:
            title, description = None, title
        self.widget = widget
        self.title = title
        self.description = description
        self.delay = delay
        self.tipwindow = None
        self._job = None
        self._inside = False
        # Bind on the widget AND all its children so composite CTk widgets
        # (OptionMenu, Slider, Switch, Entry, etc.) all trigger the tooltip.
        self._bind_recursive(widget)

    def _bind_recursive(self, w):
        """Bind Enter/Leave/Click on w and every descendant."""
        try:
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")
            w.bind("<ButtonPress>", self._on_click, add="+")
        except Exception:
            pass
        try:
            for child in w.winfo_children():
                self._bind_recursive(child)
        except Exception:
            pass

    def _on_click(self, _event=None):
        self._cancel_pending()
        self._do_hide()

    def _on_enter(self, _event=None):
        """Schedule tooltip to appear after a short delay."""
        self._inside = True
        if self._job is not None:
            self.widget.after_cancel(self._job)
        self._job = self.widget.after(self.delay, self._do_show)

    def _on_leave(self, _event=None):
        """Cancel show, schedule hide after a short delay."""
        self._inside = False
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None
        # Small delay before hiding to avoid flicker when moving between sub-widgets
        self.widget.after(50, self._maybe_hide)

    def _maybe_hide(self):
        if not self._inside and self.tipwindow is not None:
            self._do_hide()

    def _cancel_pending(self):
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None

    def _do_show(self):
        if not ToolTip.enabled:
            return
        if self.tipwindow is not None or not self.widget.winfo_exists():
            return
        dropdown = getattr(self.widget, "_dropdown_menu", None)
        if dropdown and hasattr(dropdown, "winfo_exists") and dropdown.winfo_exists():
            try:
                if dropdown.winfo_viewable():
                    return
            except Exception:
                pass
        # Position relative to the widget's screen coords
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except Exception:
            x, y = 100, 100
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.configure(fg_color=("#1E1E2E", "#1E1E2E"))
        if self.title:
            ctk.CTkLabel(tw, text=self.title, font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="#F8FAFC", fg_color="transparent").pack(padx=10, pady=(8, 2), anchor="w")
            body_pady = (0, 8)
        else:
            # 2-arg form: single body string with no bold heading. Balance the
            # vertical padding so the tooltip doesn't look top-clipped.
            body_pady = (8, 8)
        ctk.CTkLabel(tw, text=self.description, font=ctk.CTkFont(size=9),
                     text_color="#94A3B8", wraplength=260, fg_color="transparent").pack(padx=10, pady=body_pady, anchor="w")
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
        try:
            self.widget.unbind("<Enter>")
            self.widget.unbind("<Leave>")
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
            s_stamp, s_mb = self._build_info()
            ver_line = ("Build %s · %d MB" % (s_stamp, s_mb)) if getattr(sys, "frozen", False) else "dev build"
            ctk.CTkLabel(frame, text=ver_line, font=self.FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 8))
            
            shortcuts = [
                ("Ctrl + E / Ctrl + Enter", "Trigger Image Generation"),
                ("Ctrl + O", "Open Output Directory in Explorer"),
                ("F5", "Refresh Gallery View"),
                ("Ctrl + L", "Open Application Log Window"),
                ("Ctrl + Shift + V", "Purge CUDA Memory Cache"),
                ("Ctrl + Shift + C", "Copy Active Prompt to Clipboard"),
                ("Ctrl + Shift + D", "Swap Width / Height"),
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
                        existing_files = [str(m.get("file", "")).lower() for m in MODELS.values()]
                        if name not in MODELS and f.lower() not in existing_files:
                            MODELS[name] = {
                                "file": f, "value": f, "w": 1024, "h": 1024, "steps": 30, "cfg": 6.5,
                                "sampler": "dpmpp_2m", "scheduler": "karras"
                            }
                            if name not in available:
                                available.append(name)
            if hasattr(self, "model_menu") and self.model_menu is not None:
                try:
                    if hasattr(self.model_menu, "winfo_exists") and self.model_menu.winfo_exists():
                        self.model_menu.configure(values=list(MODELS.keys()))
                except Exception:
                    pass
        except Exception as e:
            logging.error("Scan checkpoints error: %s", e)


    def _unload_vram(self):
        try:
            url = getattr(self, "server_url", COMFYUI_URL)
            r = requests.post(url + "/free", json={"unload_models": True, "free_memory": True}, timeout=5)
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
        # Initialize diagnostics system (crash handler + JSON logging + breadcrumbs)
        try:
            from comfyui_desktop.diagnostics import init_diagnostics, breadcrumb
            # Stable base for crash dumps/bundles: in frozen onefile __file__ is
            # inside the temp _MEI dir PyInstaller deletes on exit, so dumps would
            # vanish. Use the real exe dir (or repo root when running from source).
            if getattr(sys, "frozen", False):
                _diag_base = os.path.dirname(os.path.abspath(sys.executable))
            else:
                _diag_base = os.path.dirname(os.path.abspath(__file__))
            init_diagnostics(_diag_base, install_crash_hook=True, app_self=self)
            breadcrumb("app_start")
        except Exception as e:
            logging.warning("Diagnostics init warning: %s", e)
        root.title("ComfyUIX")
        root.geometry("1280x1120")
        root.minsize(900, 640)
        mode = ctk.get_appearance_mode().lower()
        root.configure(bg="#F1F5F9" if mode == "light" else "#0F0F12")

        self.tooltips_enabled = ctk.StringVar(value="1")
        self.current_tab = "txt2img"
        self.vars = {}
        self.config_manager = ConfigManager()
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
        # QoL (2026-08-09): readable writing font for prompt/negative textboxes.
        # Segoe UI at 13 (not the old size=10 generic) so it's easy to read while typing.
        self.FONT_TEXT = ctk.CTkFont(family="Segoe UI", size=13)
        self.FONT_TEXT_BOLD = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")

        # Debounce guards for rapid clicks
        self._tab_switch_lock = False
        self._model_switch_lock = False
        self._preset_switch_lock = False
        self._generate_lock = False
        self._gen_start_time = None
        self._poll_started_at = None  # QOL: track first running-poll timestamp for ETA
        self._last_tab_switch = 0
        self._last_model_switch = 0
        self._last_preset_switch = 0
        self._last_generate = 0

        self._init_vars()
        self._build_sidebar()
        self._build_main()
        self._build_status_bar()
        self._build_sidebar_buttons()
        # Restore saved window geometry (written by on_close) so the app
        # reopens where the user left it. Safe: never crashes if absent/invalid.
        self._restore_config()

        # Keyboard Shortcuts
        root.bind("<Control-Return>", lambda e: self._on_ctrl_e())
        root.bind("<Shift-Return>", lambda e: self._on_ctrl_e())
        root.bind("<Control-e>", lambda e: self._on_ctrl_e())
        root.bind("<Control-E>", lambda e: self._on_ctrl_e())
        root.bind("<Control-r>", lambda e: self._restart_server())
        root.bind("<F5>", lambda e: self._refresh_gallery_main())
        root.bind("<Control-Key-1>", lambda e: self._switch_tab_by_index(0))
        root.bind("<Control-Key-2>", lambda e: self._switch_tab_by_index(1))
        root.bind("<Control-Key-3>", lambda e: self._switch_tab_by_index(2))
        root.bind("<Control-Key-4>", lambda e: self._switch_tab_by_index(3))
        root.bind("<Control-Key-5>", lambda e: self._switch_tab_by_index(4))
        root.bind("<Control-Key-6>", lambda e: self._switch_tab_by_index(5))
        root.bind("<Control-Key-7>", lambda e: self._switch_tab_by_index(6))
        root.bind("<Control-Key-8>", lambda e: self._switch_tab_by_index(7))
        root.bind("<F12>", lambda e: self._focus_debug())
        root.bind("<Control-Shift-D>", lambda e: self._focus_debug())
        root.bind("<Control-d>", lambda e: self._focus_debug())
        root.bind("<Escape>", lambda e: self._cancel_generate())
        root.bind("<Control-L>", lambda e: self._clear_prompt())
        # F1 = Keyboard Shortcuts cheat sheet (built but was unwired).
        root.bind("<F1>", lambda e: self._show_shortcut_modal())
        # QoL: wire previously-dead helpers (complete impls, were never bound).
        root.bind("<Control-Shift-C>", lambda e: self._copy_prompt())
        root.bind("<Control-Shift-D>", lambda e: self._swap_dimensions())
        root.bind("<Control-o>", lambda e: _open_file(OUTPUT_DIR))
        root.bind("<Control-O>", lambda e: _open_file(OUTPUT_DIR))
        root.bind("<Control-Shift-V>", lambda e: self._free_vram())
        root.bind("<Control-Shift-v>", lambda e: self._free_vram())
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

    def _recursive_destroy(self, widget):
        if not widget or not widget.winfo_exists():
            return
        for child in list(widget.winfo_children()):
            try:
                self._recursive_destroy(child)
            except Exception:
                pass
        try:
            widget.destroy()
        except Exception:
            pass

    def _select_recent_image(self, path):
        try:
            if os.path.exists(path):
                img = Image.open(path).convert("RGB")
                self.current_pil = img
                self._last_output_file = path
                self._display_preview(img)
                self._set_status("Selected image: %s" % os.path.basename(path))
        except Exception as e:
            logging.error("Select recent image error: %s", e)

    def _reload_recent_preview(self):
        try:
            for child in list(self.preview_thumbs.winfo_children()):
                try:
                    self._recursive_destroy(child)
                except Exception:
                    pass
            self._preview_thumb_count = 0
            self._load_recent_into_preview(only_preview=True)
        except Exception as e:
            logging.error("Reload recent preview error: %s", e)

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
        m["model_strength"] = tk.DoubleVar(value=1.0)
        m["clip_strength"] = tk.DoubleVar(value=1.0)
        m["randomize_seed"] = tk.StringVar(value="1")
        self.vars["txt2img"] = m

        m2 = {"denoise": tk.DoubleVar(value=0.7)}
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

        self.vram_threshold_str = tk.StringVar(value=self.config_manager.settings.get("vram_threshold", "90% (Default)"))
        self.tooltips_enabled = tk.StringVar(value=self.config_manager.settings.get("tooltips_enabled", "1"))
        # QoL toggles (default ON per user request). These persist via config_manager.
        self.qol_prompt_history = tk.StringVar(value=self.config_manager.settings.get("qol_prompt_history", "1"))
        self.qol_auto_restart = tk.StringVar(value=self.config_manager.settings.get("qol_auto_restart", "1"))
        self.qol_restore_session = tk.StringVar(value=self.config_manager.settings.get("qol_restore_session", "1"))
        self.qol_vram_readout = tk.StringVar(value=self.config_manager.settings.get("qol_vram_readout", "1"))
        self.qol_copy_path = tk.StringVar(value=self.config_manager.settings.get("qol_copy_path", "1"))  # QOL: auto-copy output path
        # QoL (2026-08-09): writing-font size (Small=11 / Medium=13 / Large=15)
        self.text_size_str = tk.StringVar(value=self.config_manager.settings.get("text_size", "Medium"))
        # QoL: last-used prompt capture (for "↺ Last Prompt")
        self.last_prompt = None
        ToolTip.enabled = (self.tooltips_enabled.get() == "1")

        self.gpu_mode_str = tk.StringVar(value=self.config_manager.settings.get("gpu_mode", "Default"))
        self.launch_args_str = tk.StringVar(value=self.config_manager.settings.get("launch_args", "--windows-standalone-build --fast fp16_accumulation --disable-auto-launch"))
        self.launch_args_str.trace_add("write", self._on_launch_args_change)

    def _get_vram_threshold_float(self):
        val = self.vram_threshold_str.get()
        if "Disabled" in val:
            return 1.1  # unreachable
        digits = "".join([c for c in val if c.isdigit()])
        if digits:
            return float(digits) / 100.0
        return 0.90  # fallback

    def _on_vram_threshold_change(self, val):
        self.config_manager.settings["vram_threshold"] = val
        self.config_manager.save()
        self._set_status("VRAM Guard threshold updated to %s" % val)

    def _on_tooltips_toggle(self):
        val = self.tooltips_enabled.get()
        ToolTip.enabled = (val == "1")
        self.config_manager.settings["tooltips_enabled"] = val
        self.config_manager.save()
        self._set_status("Tooltip visibility updated")

    def _on_text_size_change(self, val):
        """QoL (2026-08-09): re-apply the writing font across all prompt/negative
        textboxes live. Sizes: Small=11, Medium=13, Large=15 (Segoe UI)."""
        self.config_manager.settings["text_size"] = val
        self.config_manager.save()
        _map = {"Small": 11, "Medium": 13, "Large": 15}
        size = _map.get(val, 13)
        try:
            self.FONT_TEXT.configure(family="Segoe UI", size=size)
            self.FONT_TEXT_BOLD.configure(family="Segoe UI", size=size, weight="bold")
        except Exception:
            pass
        self._set_status("Text size: %s" % val)

    def _on_gpu_mode_change(self, val):
        self.config_manager.settings["gpu_mode"] = val
        self.config_manager.save()
        self._set_status("GPU mode set to: %s" % val)

    def _on_launch_args_change(self, *args):
        self.config_manager.settings["launch_args"] = self.launch_args_str.get()
        self.config_manager.save()

    def _build_backdrop(self):
        pass

    def _start_backend_threads(self):
        """Start backend polling threads after UI is first rendered.

        Idempotent: __init__ schedules this once (~300ms) and main() also
        schedules it once (~500ms). Without the guard the second call spawns a
        SECOND backend server + error monitor + VRAM watch (and the backend
        starter's _terminate_backend() then kills the first mid-boot). This
        guard makes the duplicate a harmless no-op.
        """
        if getattr(self, "_backend_threads_started", False):
            logging.info("backend threads already started; skipping duplicate start")
            return
        self._backend_threads_started = True
        threading.Thread(target=self._start_backend, daemon=True).start()
        threading.Thread(target=self._check_for_errors, daemon=True).start()
        self.root.after(5000, self._start_vram_watch)

    def _build_info(self):
        """Build identity shown in the title bar + sidebar.

        Prefers the bundled build_info.json (written at BUILD time, so it is a
        STABLE, meaningful build id). In a onefile PyInstaller bundle
        sys.executable points at the temp-extracted copy whose mtime is the
        *launch* time - useless for identifying the build - so we rely on the
        embedded metadata. Falls back to file mtime/size if the JSON is missing.
        Source run -> 'dev'.
        """
        # Fast path: embedded build metadata (correct for onefile builds).
        try:
            if getattr(sys, "frozen", False):
                # onefile: datas are extracted to a temp dir at sys._MEIPASS
                meipass = getattr(sys, "_MEIPASS", None)
                candidates = []
                if meipass:
                    candidates.append(os.path.join(meipass, "build_info.json"))
                candidates.append(os.path.join(os.path.dirname(sys.executable), "build_info.json"))
                data = None
                for _c in candidates:
                    if os.path.exists(_c):
                        with open(_c, encoding="utf-8") as _f:
                            data = _f.read()
                        break
                if data is None:
                    # last resort: bundled package resource
                    try:
                        import importlib.resources as _ir
                        data = _ir.read_text("build_info", "build_info.json")
                    except Exception:
                        data = None
                if data:
                    meta = json.loads(data)
                    stamp = meta.get("build", "")
                    if stamp:
                        try:
                            sz = os.path.getsize(sys.executable) // (1024 * 1024)
                        except Exception:
                            sz = 0
                        return stamp, sz
        except Exception:
            pass
        # Fallback: file mtime + size (dev runs, or pre-metadata builds).
        try:
            exe = sys.executable if getattr(sys, "frozen", False) else __file__
            st = os.stat(exe)
            ts = datetime.datetime.fromtimestamp(st.st_mtime)
            return ts.strftime("%Y-%m-%d %H:%M"), st.st_size // (1024 * 1024)
        except Exception:
            return "unknown", 0

    def _stamped_title(self):
        stamp, mb = self._build_info()
        if getattr(sys, "frozen", False):
            return "ComfyUI Uncensored  ·  build %s  ·  %d MB" % (stamp, mb)
        return "ComfyUI Uncensored  ·  dev"

    # ------------------------------------------------------------------
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self.root, width=230, corner_radius=0, fg_color=BG_SIDEBAR)
        sb.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sb.grid_columnconfigure(0, weight=1)
        self.sidebar = sb
        ctk.CTkLabel(sb, text="ComfyUIX", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                     text_color=BRAND).grid(row=0, column=0, padx=20, pady=(22, 14), sticky="w")

        nav = [("Studio", self._focus_generate), ("Gallery", self._focus_gallery),
               ("Settings", self._focus_settings), ("Debug Console", self._focus_debug)]
        for i, (label, cmd) in enumerate(nav):
            b = ctk.CTkButton(sb, text=label, height=34, anchor="w", fg_color="transparent",
                              text_color=TEXT, hover_color=BG_CARD_ALT,
                              corner_radius=8, command=cmd, font=self.FONT_NORMAL_BOLD)
            b.grid(row=1 + i, column=0, padx=14, pady=6, sticky="ew")

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

        # Live VRAM readout chip (gated by qol_vram_readout; off by default-safe).
        self.vram_chip = ctk.CTkLabel(sb, text="", height=22, corner_radius=8,
                                      fg_color="#1E293B", text_color="#7DD3FC",
                                      font=ctk.CTkFont(size=10, weight="bold"))
        self.vram_chip.grid(row=9, column=0, padx=14, pady=(0, 14), sticky="ew")

        # Build/version identity — root-cause fix for "is my exe the new one?"
        s_stamp, s_mb = self._build_info()
        ver_text = ("build %s · %d MB" % (s_stamp, s_mb)) if getattr(sys, "frozen", False) else "dev build"
        self.version_label = ctk.CTkLabel(sb, text=ver_text, height=18, corner_radius=6,
                                          fg_color="transparent", text_color=TEXT_MUTED,
                                          font=ctk.CTkFont(size=9))
        self.version_label.grid(row=10, column=0, padx=14, pady=(0, 10), sticky="w")

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
                try:
                    children = parent.winfo_children()
                except Exception:
                    return
                for child in children:
                    if hasattr(child, "refresh_appearance"):
                        try:
                            child.refresh_appearance()
                        except Exception:
                            pass
                    try:
                        _refresh_children(child)
                    except Exception:
                        pass
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
                    self._recursive_destroy(self.sidebar)
                except Exception:
                    pass
            if hasattr(self, "top") and self.top:
                try:
                    self._recursive_destroy(self.top)
                except Exception:
                    pass
            if hasattr(self, "_gallery_main") and self._gallery_main:
                try:
                    self._recursive_destroy(self._gallery_main)
                except Exception:
                    pass
            if hasattr(self, "_settings_main") and self._settings_main:
                try:
                    self._recursive_destroy(self._settings_main)
                except Exception:
                    pass

            self._build_sidebar()
            self._build_main()
            self._build_txt2img_tab()
            self._build_img2img_tab()
            self._build_upscale_tab()
            self._build_preview_pane()
            self._build_sidebar_buttons()
            # QoL: restore last session prompt/negative for the image tabs (if enabled).
            self._restore_session_on_start()
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
            # PRESERVED_LEGACY: Prune destroyed widgets from ScalingTracker to prevent TclError crash on UI scaling change
            try:
                from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
                for win in list(ScalingTracker.window_widgets_dict.keys()):
                    valid = []
                    for w in ScalingTracker.window_widgets_dict.get(win, []):
                        try:
                            if hasattr(w, "winfo_exists") and w.winfo_exists():
                                valid.append(w)
                        except Exception:
                            pass
                    ScalingTracker.window_widgets_dict[win] = valid
            except Exception as e:
                logging.debug("ScalingTracker prune error: %s", e)
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
            self._show_view("generate")
        except Exception as e:
            logging.error("Focus generate error: %s", e)

    def _focus_gallery(self):
        try:
            logging.info("Focus gallery clicked")
            self._show_view("gallery")
        except Exception as e:
            logging.error("Focus gallery error: %s", e)

    def _focus_settings(self):
        try:
            logging.info("Focus settings clicked")
            self._show_view("settings")
        except Exception as e:
            logging.error("Focus settings error: %s", e)

    def _focus_debug(self):
        try:
            logging.info("Focus debug clicked")
            self._show_view("debug")
        except Exception as e:
            logging.error("Focus debug error: %s", e)

    def _show_view(self, name):
        """Toggle which right-column main view is visible.

        'generate' -> show top creation area (self.top)
        'gallery'  -> show dedicated gallery view (_gallery_main)
        'settings' -> show dedicated settings view (_settings_main)
        'debug'    -> show dedicated debug view (_debug_main)
        """
        try:
            if hasattr(self, "top") and self.top.winfo_exists():
                if name == "generate":
                    self.top.grid()
                else:
                    self.top.grid_remove()

            for view_attr in ("_gallery_main", "_settings_main", "_debug_main"):
                if hasattr(self, view_attr) and getattr(self, view_attr).winfo_exists():
                    getattr(self, view_attr).grid_remove()

            if name == "gallery":
                if not (hasattr(self, "_gallery_main") and self._gallery_main.winfo_exists()):
                    self._build_gallery_in_main()
                if hasattr(self, "_gallery_main") and self._gallery_main.winfo_exists():
                    self._gallery_main.grid()

            elif name == "settings":
                if not (hasattr(self, "_settings_main") and self._settings_main.winfo_exists()):
                    self._build_settings_in_main()
                if hasattr(self, "_settings_main") and self._settings_main.winfo_exists():
                    self._settings_main.grid()

            elif name == "debug":
                if not (hasattr(self, "_debug_main") and self._debug_main.winfo_exists()):
                    self._build_debug_in_main()
                if hasattr(self, "_debug_main") and self._debug_main.winfo_exists():
                    self._debug_main.grid()
                    self._debug_refresh()
        except Exception as e:
            logging.error("show_view error: %s", e)

    def _build_gallery_in_main(self):
        """Build gallery content in the main area."""
        if hasattr(self, "_gallery_main") and self._gallery_main:
            try:
                self._recursive_destroy(self._gallery_main)
            except Exception:
                pass
        # Create gallery frame in the main area (where tabview was)
        self._gallery_main = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=10)
        self._gallery_main.grid(row=0, column=1, rowspan=4, padx=16, pady=(8, 16), sticky="nsew")
        self._gallery_main.grid_columnconfigure(0, weight=1)
        self._gallery_main.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self._gallery_main, fg_color=BG_CARD, corner_radius=8)
        header.grid(row=0, column=0, padx=8, pady=(0, 8), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Generated Media", font=ctk.CTkFont(size=12, weight="bold"),
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
        """Populate gallery with thumbnails from OUTPUT_DIR in main area.

        QoL + correctness fix (2026-08-09):
          * PhotoImage objects are kept alive by storing them in a bounded
            per-instance cache (self._gallery_thumb_cache) keyed by
            (filename, mtime). Previously the PhotoImage lived only in a local
            var referenced by lbl.image; because the local went out of scope
            after the function returned, Tk could GC the image and render blank
            thumbnails. The cache holds a strong reference for the image's life.
          * Unchanged files (same mtime) skip the PIL open + thumbnail entirely,
            so refreshing a large OUTPUT_DIR no longer re-decodes every image
            on every poll.
        """
        if not hasattr(self, '_gallery_frame_main') or not self._gallery_frame_main.winfo_exists():
            return
        if not hasattr(self, '_gallery_thumb_cache'):
            self._gallery_thumb_cache = {}
        for widget in self._gallery_frame_main.winfo_children():
            widget.destroy()
        try:
            if not os.path.isdir(OUTPUT_DIR):
                ctk.CTkLabel(self._gallery_frame_main, text="No generated media yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            images = [f for f in os.listdir(OUTPUT_DIR)
                      if f.lower().endswith((".png", ".jpg", ".jpeg", ".mp4", ".webm")) and not f.startswith("input")]
            images.sort(key=lambda x: _safe_mtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
            if not images:
                ctk.CTkLabel(self._gallery_frame_main, text="No generated media yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            # Drop cache entries for files that no longer exist
            live = set(images)
            for key in [k for k in self._gallery_thumb_cache if k[0] not in live]:
                del self._gallery_thumb_cache[key]
            for idx, fname in enumerate(images):
                fpath = os.path.join(OUTPUT_DIR, fname)
                is_video = fname.lower().endswith((".mp4", ".webm"))
                try:
                    if is_video:
                        lbl = ctk.CTkLabel(self._gallery_frame_main, text="▶ " + fname,
                                           fg_color=BG_CARD, corner_radius=6, width=180, height=140,
                                           font=ctk.CTkFont(size=9), text_color=TEXT_DIM)
                        lbl.grid(row=idx // 3, column=idx % 3, padx=6, pady=6, sticky="nw")
                    else:
                        mtime = _safe_mtime(fpath)
                        cache_key = (fname, mtime)
                        photo = self._gallery_thumb_cache.get(cache_key)
                        if photo is None:
                            img = Image.open(fpath)
                            img.thumbnail((180, 140))
                            photo = ImageTk.PhotoImage(img)
                            # Keep a strong reference so Tk never GCs the thumbnail
                            self._gallery_thumb_cache[cache_key] = photo
                        lbl = ctk.CTkLabel(self._gallery_frame_main, image=photo, text="",
                                           fg_color=BG_CARD, corner_radius=6, width=180, height=140)
                        lbl.image = photo  # strong ref on the widget too
                    lbl.bind("<Button-1>", lambda e, fp=fpath: os.startfile(fp))
                    lbl.bind("<Button-3>", lambda e, fp=fpath, fn=fname: self._gallery_context_menu(e, fp, fn))
                    lbl.bind("<Enter>", lambda e, p=fname: self._set_status(p))
                except Exception:
                    pass
            self._gallery_frame_main.update_idletasks()
        except Exception:
            pass

    def _build_settings_in_main(self):
        """Build settings content in the main area."""
        if hasattr(self, "_settings_main") and self._settings_main:
            try:
                self._recursive_destroy(self._settings_main)
            except Exception:
                pass
        self._settings_main = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=10)
        self._settings_main.grid(row=0, column=1, rowspan=4, padx=16, pady=(8, 16), sticky="nsew")
        self._settings_main.grid_columnconfigure(0, weight=1)
        self._settings_main.grid_rowconfigure(20, weight=1)

        ctk.CTkLabel(self._settings_main, text="Application Settings", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=(0, 12), sticky="w")

        # PRESERVED_LEGACY: inlined control rendering replaced by shared helper to
        # stop dropdown-hover-color drift between main-area and tab surfaces.
        r = self._build_shared_settings_fields(self._settings_main, 1)
        r = self._build_qol_settings(self._settings_main, r)

        ctk.CTkLabel(self._settings_main, text="Restart backend to apply changes.", font=ctk.CTkFont(size=9),
                     text_color=TEXT_MUTED).grid(row=r, column=0, padx=10, pady=(8, 0), sticky="w")

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _build_shared_settings_fields(self, parent, start_row=1):
        """Render the 8 controls common to BOTH settings surfaces
        (_build_settings_in_main and _build_settings_tab) so the two views
        cannot drift apart.

        PRESERVED_LEGACY: each builder previously inlined these _labeled(...)
        calls verbatim, which let the surfaces diverge (e.g. dropdown_hover_color
        was BRAND_HOVER in _build_settings_in_main but DROPDOWN_HOVER in
        _build_settings_tab). Centralising them keeps both surfaces identical
        and canonical. Returns the next free row so callers can append labels.
        """
        r = start_row
        self._labeled(parent, r, "Output Directory", "Output Dir",
                      ctk.CTkEntry(parent, textvariable=ctk.StringVar(value=OUTPUT_DIR), width=200, state="readonly")); r += 2
        self._labeled(parent, r, "Input Directory", "Input Dir",
                      ctk.CTkEntry(parent, textvariable=ctk.StringVar(value=INPUT_DIR), width=200, state="readonly")); r += 2
        self._labeled(parent, r, "Backend Path", "Backend",
                      ctk.CTkEntry(parent, textvariable=ctk.StringVar(value=PYTHON_PATH), width=200, state="readonly")); r += 2
        self._labeled(parent, r, "ComfyUI URL", "URL",
                      ctk.CTkEntry(parent, textvariable=ctk.StringVar(value=COMFYUI_URL), width=200, state="readonly")); r += 2
        self._labeled(parent, r, "VRAM Guard Threshold", "VRAM Threshold",
                      ctk.CTkOptionMenu(parent, values=["70%", "80%", "90% (Default)", "95%", "Disabled"],
                                        variable=self.vram_threshold_str,
                                        command=self._on_vram_threshold_change,
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER)); r += 2
        sw = ctk.CTkSwitch(parent, text="Show Hover Help", variable=self.tooltips_enabled,
                           onvalue="1", offvalue="0", command=self._on_tooltips_toggle,
                           text_color=TEXT, fg_color=BRAND, progress_color=BRAND)
        if not hasattr(sw, "_variable"):
            sw._variable = self.tooltips_enabled
        self._labeled(parent, r, "Enable Tooltips", "Tooltips", sw); r += 2
        self._labeled(parent, r, "GPU Optimization", "GPU Mode",
                      ctk.CTkOptionMenu(parent, values=["Default", "Low VRAM (--lowvram)", "Medium VRAM (--medvram)", "High VRAM (--highvram)", "CPU Mode (--cpu)"],
                                        variable=self.gpu_mode_str,
                                        command=self._on_gpu_mode_change,
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER, dropdown_fg_color=DROPDOWN_FG,
                                        dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER)); r += 2
        self._labeled(parent, r, "Custom Launch Args", "Launch Args",
                      ctk.CTkEntry(parent, textvariable=self.launch_args_str, width=280, fg_color=BG_CARD_ALT, text_color=TEXT)); r += 2
        return r

    def _build_qol_settings(self, parent, start_row):
        """Render the 'QoL & UX' toggle section (appended to both settings surfaces
        so they stay in sync). All four default ON (recommended); user can flip any off.
        Each toggle persists immediately via config_manager.save()."""
        r = start_row
        ctk.CTkLabel(parent, text="QoL & UX", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=BRAND).grid(row=r, column=0, padx=10, pady=(10, 2), sticky="w"); r += 2

        def _mk_toggle(row, label, help_key, var, cmd):
            w = ctk.CTkSwitch(parent, text=label, variable=var,
                              onvalue="1", offvalue="0", command=cmd,
                              text_color=TEXT, button_hover_color=BRAND_HOVER,
                              fg_color=BRAND, progress_color=BRAND)
            self._labeled(parent, row, "", help_key, w, link=False); return None

        self._labeled(parent, r, "Prompt History Recall", "Show a 'Last Prompt' button and a recent-prompts dropdown on the image tabs.",
                      ctk.CTkSwitch(parent, text="Last Prompt + History", variable=self.qol_prompt_history,
                                    onvalue="1", offvalue="0", command=self._on_qol_prompt_history_toggle,
                                    text_color=TEXT, button_hover_color=BRAND_HOVER,
                                    fg_color=BRAND, progress_color=BRAND), link=False); r += 2
        self._labeled(parent, r, "Auto-Restart Backend", "If the backend stops, show a toast with a one-click Restart instead of silent failure.",
                      ctk.CTkSwitch(parent, text="Auto-Restart Toast", variable=self.qol_auto_restart,
                                    onvalue="1", offvalue="0", command=self._on_qol_auto_restart_toggle,
                                    text_color=TEXT, button_hover_color=BRAND_HOVER,
                                    fg_color=BRAND, progress_color=BRAND), link=False); r += 2
        self._labeled(parent, r, "Restore Session", "Remember the last prompt + seed for each tab and restore them when you reopen the app.",
                      ctk.CTkSwitch(parent, text="Restore Prompt/Seed", variable=self.qol_restore_session,
                                    onvalue="1", offvalue="0", command=self._on_qol_restore_toggle,
                                    text_color=TEXT, button_hover_color=BRAND_HOVER,
                                    fg_color=BRAND, progress_color=BRAND), link=False); r += 2
        self._labeled(parent, r, "Live VRAM Readout", "Show a small VRAM % chip in the status bar (does not clobber 'Generating...').",
                      ctk.CTkSwitch(parent, text="VRAM Chip", variable=self.qol_vram_readout,
                                    onvalue="1", offvalue="0", command=self._on_qol_vram_toggle,
                                    text_color=TEXT, button_hover_color=BRAND_HOVER,
                                    fg_color=BRAND, progress_color=BRAND), link=False); r += 2
        self._labeled(parent, r, "Copy Output Path", "Copy the generated image/video file path to your clipboard as soon as it finishes.",
                      ctk.CTkSwitch(parent, text="Copy Path", variable=self.qol_copy_path,
                                    onvalue="1", offvalue="0", command=self._on_qol_copy_path_toggle,
                                    text_color=TEXT, button_hover_color=BRAND_HOVER,
                                    fg_color=BRAND, progress_color=BRAND), link=False); r += 2

        # QoL (2026-08-09): user-facing writing-font size control (Small/Medium/Large)
        self._labeled(parent, r, "Text Size (prompts)", "Size of the prompt & negative-prompt text you type. Medium is the readable default.",
                      ctk.CTkOptionMenu(parent, values=["Small", "Medium", "Large"],
                                        variable=self.text_size_str,
                                        command=self._on_text_size_change,
                                        fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                        button_hover_color=BRAND_HOVER,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False); r += 2
        return r

    # --- QoL toggle handlers (persist immediately) ---
    def _on_qol_prompt_history_toggle(self):
        self.config_manager.settings["qol_prompt_history"] = self.qol_prompt_history.get()
        self.config_manager.save()
        self._set_status("Prompt history recall %s" % ("ON" if self.qol_prompt_history.get() == "1" else "OFF"))

    def _on_qol_auto_restart_toggle(self):
        self.config_manager.settings["qol_auto_restart"] = self.qol_auto_restart.get()
        self.config_manager.save()
        self._set_status("Auto-restart toast %s" % ("ON" if self.qol_auto_restart.get() == "1" else "OFF"))

    def _on_qol_restore_toggle(self):
        self.config_manager.settings["qol_restore_session"] = self.qol_restore_session.get()
        self.config_manager.save()
        self._set_status("Session restore %s" % ("ON" if self.qol_restore_session.get() == "1" else "OFF"))

    def _on_qol_vram_toggle(self):
        self.config_manager.settings["qol_vram_readout"] = self.qol_vram_readout.get()
        self.config_manager.save()
        if self.qol_vram_readout.get() != "1" and hasattr(self, "vram_chip") and self.vram_chip.winfo_exists():
            try:
                self.vram_chip.configure(text="")
            except Exception:
                pass
        self._set_status("VRAM chip %s" % ("ON" if self.qol_vram_readout.get() == "1" else "OFF"))

    def _on_qol_copy_path_toggle(self):
        self.config_manager.settings["qol_copy_path"] = self.qol_copy_path.get()
        self.config_manager.save()
        self._set_status("Copy output path %s" % ("ON" if self.qol_copy_path.get() == "1" else "OFF"))

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

        # Build the model dropdown from models that ACTUALLY exist on disk.
        # Only list checkpoints present in models_archive/ (or already linked
        # into models/checkpoints/). A missing file (e.g. CyberRealistic XL,
        # whose safetensors was never downloaded) is excluded so the user can
        # never select a model that always fails with "Model file missing".
        available_models = [n for n in MODELS
                            if os.path.exists(os.path.join(ARCHIVE_DIR, MODELS[n]["value"]))
                            or os.path.exists(os.path.join(CKPT_DIR, MODELS[n]["value"]))]
        if not available_models:
            available_models = list(MODELS.keys())
        default_model = available_models[0]
        self.model_var = ctk.StringVar(value=default_model)
        self._available_models = available_models
        self.preset_var = ctk.StringVar(value=list(PRESETS.keys())[0])

        toolbar = ctk.CTkFrame(self.top, fg_color="transparent")
        toolbar.grid(row=0, column=0, padx=0, pady=(0, 4), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=0)
        toolbar.grid_columnconfigure(1, weight=0)
        toolbar.grid_columnconfigure(2, weight=1)

        self.model_menu = ctk.CTkOptionMenu(toolbar, values=self._available_models, font=self.FONT_NORMAL,
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
        # Auto-discover real checkpoint files in CKPT_DIR so newly-dropped
        # models appear in the dropdown without a code change.
        self._scan_available_checkpoints()

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
                                      text_color=TEXT,
                                      command=self._on_tab
                                      )
        self.tabview.grid(row=1, column=0, columnspan=1, padx=0, pady=(12, 0), sticky="nsew")

        self.tabview.add("Text to Image")
        self.tabview.add("Image to Image")
        self.tabview.add("Upscale")
        self.tabview.add("Text to Video")
        self.tabview.add("Video to Video")
        self.tabview.add("Video Refine & Upscale")
        self.tabview.set("Text to Image")

        self._tab_callbacks = {
            "Text to Image": self._build_txt2img_tab,
            "Image to Image": self._build_img2img_tab,
            "Upscale": self._build_upscale_tab,
            "Text to Video": self._build_video_tab,
            "Video to Video": self._build_video_v2v_tab,
            "Video Refine & Upscale": self._build_video_refine_tab,
        }
        self._tab_built = {"Text to Image": False, "Image to Image": False,
                           "Upscale": False, "Text to Video": False,
                           "Video to Video": False, "Video Refine & Upscale": False}

        # Build txt2img tab immediately
        self._on_tab()

        # Preview window (right column of Generate view)
        self._build_preview_pane()

        # Header gradient image
        self._header_img = None
        self.header = ctk.CTkLabel(self.top, text="", height=56)
        self.header.grid(row=2, column=0, columnspan=1, padx=0, pady=(2, 0), sticky="nsew")

    def _labeled(self, parent, row, label, key, widget, link=True):
        """Create a labeled control at the given row in parent grid.

        Places the label at `row` and the control at `row+1`, then returns the
        next free row (row+2) so callers advance correctly. The previous code
        advanced the row counter by only 1 after each call, which made every
        control overlap the next label -- collapsing the whole center panel
        into an unreadable stack (the 'middle is crunched together' bug).

        `key` is interpreted per the `link` flag:
          link=True  (default, image tabs) -- `key` is a TOOLTIPS dict key and
                     the registered ("Title", "Body") pair is shown.
          link=False (video tabs)          -- `key` is literal tooltip body
                     text used verbatim, with no dictionary lookup.
        PRESERVED_LEGACY: the 14 video-tab call sites already passed
        `link=False`, but the parameter did not exist, so every one raised
        TypeError: _labeled() got an unexpected keyword argument 'link' and
        aborted the Text-to-Video and Video-to-Video builders. Accepting the
        flag restores those controls *and* their tooltips, which were
        previously dropped because long literal strings never match a
        TOOLTIPS key.
        """
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT).grid(row=row, column=0, padx=12, pady=(3, 0), sticky="w")
        widget.grid(row=row + 1, column=0, padx=12, pady=(0, 3), sticky="ew")
        if link:
            if key in TOOLTIPS:
                ToolTip(widget, *TOOLTIPS[key])
        elif key:
            ToolTip(widget, key)
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

        self.prompt_entry = ctk.CTkTextbox(sf, height=60, font=self.FONT_TEXT,
                                           fg_color=BG_CARD_ALT, text_color=TEXT)
        self.prompt_entry.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.prompt_entry)
        ToolTip(self.prompt_entry, *TOOLTIPS["Prompt"])
        # Default to a neutral, general prompt (NOT a female-face portrait).
        self.prompt_entry.insert("1.0", "a striking photorealistic portrait, sharp facial details, natural skin texture, soft studio rim light, shallow depth of field, 85mm lens, captured with a DSLR, 8k, ultra detailed, cinematic color grade")

        # QoL: prompt-history recall (gated by qol_prompt_history). Two controls:
        #  - "↺ Last Prompt" instantly restores the previous prompt/negative.
        #  - "History ▾" lets you pick any of the last 20 prompts.
        hist_row = ctk.CTkFrame(sf, fg_color="transparent")
        hist_row.grid(row=1, column=0, padx=10, pady=(2, 0), sticky="w")
        ctk.CTkButton(hist_row, text="↺ Last Prompt", width=104, height=24,
                     font=ctk.CTkFont(size=10), fg_color=BG_CARD_ALT, text_color=TEXT,
                     hover_color=BRAND_HOVER,
                     command=lambda: self._restore_last_prompt("txt2img")).pack(side="left", padx=(0, 6))
        self.img_hist_var = tk.StringVar(value="History")
        self.img_hist_menu = ctk.CTkOptionMenu(hist_row, values=["History"],
                                               variable=self.img_hist_var, width=120, height=24,
                                               fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                               button_hover_color=BRAND_HOVER,
                                               dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                               dropdown_hover_color=DROPDOWN_HOVER,
                                               command=lambda v: self._apply_history_prompt(v, "txt2img"))
        self.img_hist_menu.pack(side="left")
        # QoL: visible Copy-Prompt button (discoverable alternative to Ctrl+Shift+C)
        ctk.CTkButton(hist_row, text="⧉ Copy", width=70, height=24,
                     font=ctk.CTkFont(size=10), fg_color=BG_CARD_ALT, text_color=TEXT,
                     hover_color=BRAND_HOVER,
                     command=lambda: self._copy_prompt()).pack(side="left", padx=(6, 0))
        self._refresh_history_menu()

        self.neg_entry = ctk.CTkTextbox(sf, height=32, font=self.FONT_TEXT,
                                        fg_color=BG_CARD_ALT, text_color=TEXT)
        self.neg_entry.grid(row=2, column=0, padx=10, pady=(2, 0), sticky="nsew")
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
                      ctk.CTkComboBox(sf, values=["20", "30", "35", "40", "50"], variable=m["steps"],
                                      fg_color=BG_CARD_ALT, border_color=BORDER, text_color=TEXT,
                                      button_color=BORDER, button_hover_color=BRAND_HOVER,
                                      dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                      dropdown_hover_color=DROPDOWN_HOVER))
        
        r = self._labeled(sf, r, "CFG Scale", "CFG",
                      ctk.CTkComboBox(sf, values=["5.0", "6.5", "7.5", "8.0"], variable=m["cfg"],
                                      fg_color=BG_CARD_ALT, border_color=BORDER, text_color=TEXT,
                                      button_color=BORDER, button_hover_color=BRAND_HOVER,
                                      dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                      dropdown_hover_color=DROPDOWN_HOVER))

        # Seed with Random checkbox
        seed_frame = ctk.CTkFrame(sf, fg_color="transparent")
        seed_frame.grid_columnconfigure(0, weight=1)
        seed_entry = ctk.CTkEntry(seed_frame, textvariable=m["seed"], fg_color=BG_CARD_ALT, text_color=TEXT)
        seed_entry.grid(row=0, column=0, sticky="ew")
        
        def _toggle_seed_txt2img(entry=seed_entry, var=m["randomize_seed"], val_var=m["seed"]):
            if var.get() == "1":
                entry.configure(state="disabled")
                val_var.set("0")
            else:
                entry.configure(state="normal")
                
        cb = ctk.CTkCheckBox(seed_frame, text="Random", variable=m["randomize_seed"],
                             onvalue="1", offvalue="0", command=_toggle_seed_txt2img,
                             font=self.FONT_SMALL, border_color=BORDER, text_color=TEXT,
                             hover_color=BRAND_HOVER, fg_color=BRAND)
        cb.grid(row=0, column=1, padx=(8, 0), sticky="w")
        _toggle_seed_txt2img()
        r = self._labeled(sf, r, "Seed", "Seed", seed_frame)

        r = self._labeled(sf, r, "Batch Size", "Batch",
                      ctk.CTkEntry(sf, textvariable=m["batch"], fg_color=BG_CARD_ALT, text_color=TEXT))

        # Model Strength
        model_frame = ctk.CTkFrame(sf, fg_color="transparent")
        model_frame.grid_columnconfigure(0, weight=1)
        
        def _update_model_lbl_txt2img(val):
            model_lbl.configure(text=f"{float(val):.2f}")
            
        model_slider = ctk.CTkSlider(model_frame, from_=0.0, to=2.0, number_of_steps=40,
                                     variable=m["model_strength"], command=_update_model_lbl_txt2img,
                                     button_hover_color=BRAND_HOVER, fg_color=BG_CARD_ALT, progress_color=BRAND)
        model_slider.grid(row=0, column=0, sticky="ew")
        model_lbl = ctk.CTkLabel(model_frame, text=f"{m['model_strength'].get():.2f}", width=36, font=self.FONT_SMALL_BOLD, text_color=TEXT)
        model_lbl.grid(row=0, column=1, padx=(8, 0))
        r = self._labeled(sf, r, "Model Strength", "Model Strength", model_frame)

        # CLIP Strength
        clip_frame = ctk.CTkFrame(sf, fg_color="transparent")
        clip_frame.grid_columnconfigure(0, weight=1)
        
        def _update_clip_lbl_txt2img(val):
            clip_lbl.configure(text=f"{float(val):.2f}")
            
        clip_slider = ctk.CTkSlider(clip_frame, from_=0.0, to=2.0, number_of_steps=40,
                                    variable=m["clip_strength"], command=_update_clip_lbl_txt2img,
                                    button_hover_color=BRAND_HOVER, fg_color=BG_CARD_ALT, progress_color=BRAND)
        clip_slider.grid(row=0, column=0, sticky="ew")
        clip_lbl = ctk.CTkLabel(clip_frame, text=f"{m['clip_strength'].get():.2f}", width=36, font=self.FONT_SMALL_BOLD, text_color=TEXT)
        clip_lbl.grid(row=0, column=1, padx=(8, 0))
        r = self._labeled(sf, r, "CLIP Strength", "CLIP Strength", clip_frame)

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

        self.img2img_prompt_entry = ctk.CTkTextbox(sf, height=60, font=self.FONT_TEXT,
                                                   fg_color=BG_CARD_ALT, text_color=TEXT)
        self.img2img_prompt_entry.grid(row=2, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.img2img_prompt_entry)
        ToolTip(self.img2img_prompt_entry, *TOOLTIPS["Prompt"])
        self.img2img_prompt_entry.insert("1.0", "photorealistic portrait, detailed skin, studio light")

        self.img2img_neg_entry = ctk.CTkTextbox(sf, height=32, font=self.FONT_TEXT,
                                                fg_color=BG_CARD_ALT, text_color=TEXT)
        self.img2img_neg_entry.grid(row=3, column=0, padx=10, pady=(6, 0), sticky="nsew")
        self._apply_cursor_style(self.img2img_neg_entry)
        ToolTip(self.img2img_neg_entry, *TOOLTIPS["Negative Prompt"])
        self.img2img_neg_entry.insert("1.0", DEFAULT_NEG)

        m = self.vars["img2img"]
        r = 4
        # Denoise Slider
        denoise_frame = ctk.CTkFrame(sf, fg_color="transparent")
        denoise_frame.grid_columnconfigure(0, weight=1)
        
        def _update_denoise_lbl(val):
            denoise_lbl.configure(text=f"{float(val):.2f}")
            
        denoise_slider = ctk.CTkSlider(denoise_frame, from_=0.0, to=1.0, number_of_steps=100,
                                       variable=m["denoise"], command=_update_denoise_lbl,
                                       button_hover_color=BRAND_HOVER, fg_color=BG_CARD_ALT, progress_color=BRAND)
        denoise_slider.grid(row=0, column=0, sticky="ew")
        denoise_lbl = ctk.CTkLabel(denoise_frame, text=f"{m['denoise'].get():.2f}", width=36, font=self.FONT_SMALL_BOLD, text_color=TEXT)
        denoise_lbl.grid(row=0, column=1, padx=(8, 0))
        r = self._labeled(sf, r, "Denoise", "Denoise", denoise_frame)

        r = self._labeled(sf, r, "Width", "Width",
                      ctk.CTkEntry(sf, textvariable=m["width"], fg_color=BG_CARD_ALT, text_color=TEXT))
        r = self._labeled(sf, r, "Height", "Height",
                      ctk.CTkEntry(sf, textvariable=m["height"], fg_color=BG_CARD_ALT, text_color=TEXT))
        
        r = self._labeled(sf, r, "Steps", "Steps",
                      ctk.CTkComboBox(sf, values=["20", "30", "35", "40", "50"], variable=m["steps"],
                                      fg_color=BG_CARD_ALT, border_color=BORDER, text_color=TEXT,
                                      button_color=BORDER, button_hover_color=BRAND_HOVER,
                                      dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                      dropdown_hover_color=DROPDOWN_HOVER))
        
        r = self._labeled(sf, r, "CFG Scale", "CFG",
                      ctk.CTkComboBox(sf, values=["5.0", "6.5", "7.5", "8.0"], variable=m["cfg"],
                                      fg_color=BG_CARD_ALT, border_color=BORDER, text_color=TEXT,
                                      button_color=BORDER, button_hover_color=BRAND_HOVER,
                                      dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                      dropdown_hover_color=DROPDOWN_HOVER))

        # Seed with Random checkbox
        seed_frame = ctk.CTkFrame(sf, fg_color="transparent")
        seed_frame.grid_columnconfigure(0, weight=1)
        seed_entry = ctk.CTkEntry(seed_frame, textvariable=m["seed"], fg_color=BG_CARD_ALT, text_color=TEXT)
        seed_entry.grid(row=0, column=0, sticky="ew")
        
        def _toggle_seed_img2img(entry=seed_entry, var=m["randomize_seed"], val_var=m["seed"]):
            if var.get() == "1":
                entry.configure(state="disabled")
                val_var.set("0")
            else:
                entry.configure(state="normal")
                
        cb = ctk.CTkCheckBox(seed_frame, text="Random", variable=m["randomize_seed"],
                             onvalue="1", offvalue="0", command=_toggle_seed_img2img,
                             font=self.FONT_SMALL, border_color=BORDER, text_color=TEXT,
                             hover_color=BRAND_HOVER, fg_color=BRAND)
        cb.grid(row=0, column=1, padx=(8, 0), sticky="w")
        _toggle_seed_img2img()
        r = self._labeled(sf, r, "Seed", "Seed", seed_frame)

        r = self._labeled(sf, r, "Batch Size", "Batch",
                      ctk.CTkEntry(sf, textvariable=m["batch"], fg_color=BG_CARD_ALT, text_color=TEXT))

        # Model Strength
        model_frame = ctk.CTkFrame(sf, fg_color="transparent")
        model_frame.grid_columnconfigure(0, weight=1)
        
        def _update_model_lbl_img2img(val):
            model_lbl.configure(text=f"{float(val):.2f}")
            
        model_slider = ctk.CTkSlider(model_frame, from_=0.0, to=2.0, number_of_steps=40,
                                     variable=m["model_strength"], command=_update_model_lbl_img2img,
                                     button_hover_color=BRAND_HOVER, fg_color=BG_CARD_ALT, progress_color=BRAND)
        model_slider.grid(row=0, column=0, sticky="ew")
        model_lbl = ctk.CTkLabel(model_frame, text=f"{m['model_strength'].get():.2f}", width=36, font=self.FONT_SMALL_BOLD, text_color=TEXT)
        model_lbl.grid(row=0, column=1, padx=(8, 0))
        r = self._labeled(sf, r, "Model Strength", "Model Strength", model_frame)

        # CLIP Strength
        clip_frame = ctk.CTkFrame(sf, fg_color="transparent")
        clip_frame.grid_columnconfigure(0, weight=1)
        
        def _update_clip_lbl_img2img(val):
            clip_lbl.configure(text=f"{float(val):.2f}")
            
        clip_slider = ctk.CTkSlider(clip_frame, from_=0.0, to=2.0, number_of_steps=40,
                                    variable=m["clip_strength"], command=_update_clip_lbl_img2img,
                                    button_hover_color=BRAND_HOVER, fg_color=BG_CARD_ALT, progress_color=BRAND)
        clip_slider.grid(row=0, column=0, sticky="ew")
        clip_lbl = ctk.CTkLabel(clip_frame, text=f"{m['clip_strength'].get():.2f}", width=36, font=self.FONT_SMALL_BOLD, text_color=TEXT)
        clip_lbl.grid(row=0, column=1, padx=(8, 0))
        r = self._labeled(sf, r, "CLIP Strength", "CLIP Strength", clip_frame)

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

        # QoL: prompt-history recall controls (gated by qol_prompt_history).
        ihist_row = ctk.CTkFrame(sf, fg_color="transparent")
        ihist_row.grid(row=r, column=0, padx=10, pady=(8, 0), sticky="w"); r += 1
        ctk.CTkButton(ihist_row, text="↺ Last Prompt", width=104, height=24,
                     font=ctk.CTkFont(size=10), fg_color=BG_CARD_ALT, text_color=TEXT,
                     hover_color=BRAND_HOVER,
                     command=lambda: self._restore_last_prompt("img2img")).pack(side="left", padx=(0, 6))
        self.img2img_hist_var = tk.StringVar(value="History")
        self.img2img_hist_menu = ctk.CTkOptionMenu(ihist_row, values=["History"],
                                                   variable=self.img2img_hist_var, width=120, height=24,
                                                   fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                                   button_hover_color=BRAND_HOVER,
                                                   dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                                   dropdown_hover_color=DROPDOWN_HOVER,
                                                   command=lambda v: self._apply_history_prompt(v, "img2img"))
        self.img2img_hist_menu.pack(side="left")
        # share the same history list as txt2img
        ctk.CTkButton(ihist_row, text="Refresh", width=80, height=24,
                     font=ctk.CTkFont(size=10), fg_color=BG_CARD_ALT, text_color=TEXT,
                     hover_color=BRAND_HOVER,
                     command=lambda: self._refresh_history_menu()).pack(side="left", padx=(6, 0))

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

        # QoL: parity with Gallery/Video/Debug — open the output folder from here too.
        ctk.CTkButton(sf, text="Open Folder", width=100, height=28,
                      font=ctk.CTkFont(size=10), fg_color=BG_CARD_ALT, text_color=TEXT,
                      hover_color=BRAND_HOVER,
                      command=lambda: _open_folder(OUTPUT_DIR)).grid(row=r, column=0, padx=10, pady=(8, 0), sticky="w")

    def _build_video_tab(self):
        """Text to Video tab - MiniMax H3 local video gen (T2V + I2V).
        Full sampler/exposure per transcript feature list. Drives _build_h3_graph."""
        import os
        t = self.tabview.tab("Text to Video")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        def _row(idx):
            sf.grid_rowconfigure(idx, weight=0)

        # Prompt
        self.video_prompt = ctk.CTkTextbox(sf, height=60, font=self.FONT_TEXT,
                                           fg_color=BG_CARD_ALT, text_color=TEXT)
        self.video_prompt.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.video_prompt)
        ToolTip(self.video_prompt, "Video prompt (multiline, dynamic). Describes the scene, motion, style, camera.\n\nShortcut: Ctrl+E generates (same as Generate button).")
        self.video_prompt.insert("1.0", "cinematic aerial shot of a neon city at night, rain-slick streets, flying cars, slow push-in")

        # Mode (T2V / I2V)
        self.video_mode_var = ctk.StringVar(value="T2V (Text)")
        mode_menu = ctk.CTkOptionMenu(sf, values=["T2V (Text)", "I2V (Image)"],
                                      variable=self.video_mode_var, font=self.FONT_NORMAL,
                                      fg_color=BG_CARD_ALT, button_color=BORDER,
                                      button_hover_color=BRAND_HOVER, text_color=TEXT,
                                      dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                      dropdown_hover_color=DROPDOWN_HOVER)
        mode_menu.grid(row=1, column=0, padx=10, pady=(8, 4), sticky="ew")
        ToolTip(mode_menu, "T2V: text only. I2V: text + one uploaded image (see Image to Image style upload).")

        # I2V first/last frame (real I2V mechanism via MiniMaxH3FLConstraint)
        self.video_fl_first = None
        self.video_fl_last = None
        flf = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=6)
        flf.grid(row=2, column=0, padx=10, pady=(4, 4), sticky="ew")
        self.video_fl_first_btn = ctk.CTkButton(flf, text="First Frame (I2V)", height=28,
                                                font=self.FONT_NORMAL, fg_color=BG_CARD,
                                                hover_color=BRAND_HOVER, text_color=TEXT,
                                                command=self._video_pick_fl_first)
        self.video_fl_first_btn.grid(row=0, column=0, padx=4, sticky="ew")
        self.video_fl_last_btn = ctk.CTkButton(flf, text="Last Frame (I2V)", height=28,
                                               font=self.FONT_NORMAL, fg_color=BG_CARD,
                                               hover_color=BRAND_HOVER, text_color=TEXT,
                                               command=self._video_pick_fl_last)
        self.video_fl_last_btn.grid(row=0, column=1, padx=4, sticky="ew")
        ToolTip(flf, "Image-to-Video: lock the opening (and/or closing) frame. The model animates between them.")

        # I2V single image upload (shown for context) — legacy single image path
        self.video_i2v_path = None
        self.video_i2v_btn = ctk.CTkButton(sf, text="Upload Reference Image", height=30,
                                           font=self.FONT_NORMAL, fg_color=BG_CARD_ALT,
                                           hover_color=BRAND_HOVER, text_color=TEXT,
                                           command=self._video_pick_i2v_image)
        self.video_i2v_btn.grid(row=3, column=0, padx=10, pady=(4, 4), sticky="ew")
        ToolTip(self.video_i2v_btn, "Optional single reference image for the scene (character/style anchor).")

        # Resolution
        self.video_res_var = ctk.StringVar(value="240p (512x288)")
        res_menu = ctk.CTkOptionMenu(sf, values=list(VIDEO_RESOLUTIONS.keys()),
                                     variable=self.video_res_var, font=self.FONT_NORMAL,
                                     fg_color=BG_CARD_ALT, button_color=BORDER,
                                     button_hover_color=BRAND_HOVER, text_color=TEXT,
                                     dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                     dropdown_hover_color=DROPDOWN_HOVER)
        res_menu.grid(row=3, column=0, padx=10, pady=(4, 4), sticky="ew")
        ToolTip(res_menu, "Output resolution. 240p (512x288) = verified 8GB-VRAM-safe floor on RTX 2070S; 360p risks OOM.")

        # Aspect ratio (research-driven; maps to w/h the node accepts)
        self.video_ar_var = ctk.StringVar(value="16:9 Widescreen")
        ar_menu = ctk.CTkOptionMenu(sf, values=list(VIDEO_ASPECT_RATIOS.keys()),
                                    variable=self.video_ar_var, font=self.FONT_NORMAL,
                                    fg_color=BG_CARD_ALT, button_color=BORDER,
                                    button_hover_color=BRAND_HOVER, text_color=TEXT,
                                    dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                    dropdown_hover_color=DROPDOWN_HOVER)
        ar_menu.grid(row=4, column=0, padx=10, pady=(4, 4), sticky="ew")
        ToolTip(ar_menu, "Aspect ratio. Resolution sets pixel budget; aspect ratio sets the frame shape (16:9 / 9:16 / 1:1 / 4:3).")

        # Duration
        self.video_dur_var = ctk.StringVar(value="5s")
        dur_menu = ctk.CTkOptionMenu(sf, values=list(VIDEO_DURATIONS.keys()),
                                     variable=self.video_dur_var, font=self.FONT_NORMAL,
                                     fg_color=BG_CARD_ALT, button_color=BORDER,
                                     button_hover_color=BRAND_HOVER, text_color=TEXT,
                                     dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                     dropdown_hover_color=DROPDOWN_HOVER, width=120)
        dur_menu.grid(row=4, column=0, padx=10, pady=(4, 4), sticky="w")
        ToolTip(dur_menu, "Clip length. Frames snap to the 17k+5 grid @ 24fps: 3s=73 frames, 5s=124, 9s=226, 14s=345. Longer = slower on 8GB.")

        # --- Motion & Options (research: camera presets, prompt enhance, loop, batch) ---
        self.video_camera_var = ctk.StringVar(value="Static")
        cam_f = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=6)
        cam_f.grid(row=5, column=0, padx=10, pady=(4, 2), sticky="ew")
        ctk.CTkLabel(cam_f, text="Camera", font=self.FONT_NORMAL, text_color=TEXT).grid(row=0, column=0, padx=6, sticky="w")
        cam_menu = ctk.CTkOptionMenu(cam_f, values=list(VIDEO_CAMERA_MOTIONS.keys()),
                                     variable=self.video_camera_var, font=self.FONT_NORMAL,
                                     fg_color=BG_CARD, button_color=BORDER, button_hover_color=BRAND_HOVER,
                                     text_color=TEXT, dropdown_fg_color=DROPDOWN_FG,
                                     dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER,
                                     width=180)
        cam_menu.grid(row=0, column=1, padx=6, sticky="w")
        ToolTip(cam_f, "Camera motion preset (structured prompt). Static = no camera move.")

        opt_f = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=6)
        opt_f.grid(row=6, column=0, padx=10, pady=(2, 2), sticky="ew")
        self.video_enhance_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(opt_f, text="Enhance prompt", variable=self.video_enhance_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT).grid(row=0, column=0, padx=6, sticky="w")
        self.video_loop_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(opt_f, text="Loop", variable=self.video_loop_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT).grid(row=0, column=1, padx=6, sticky="w")
        self.video_batch_var = ctk.StringVar(value="1")
        ctk.CTkLabel(opt_f, text="Batch", font=self.FONT_NORMAL, text_color=TEXT).grid(row=0, column=2, padx=(10,2), sticky="w")
        ctk.CTkOptionMenu(opt_f, values=["1","2","3","4"], variable=self.video_batch_var,
                          font=self.FONT_NORMAL, fg_color=BG_CARD, button_color=BORDER,
                          button_hover_color=BRAND_HOVER, text_color=TEXT, width=60,
                          dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                          dropdown_hover_color=DROPDOWN_HOVER).grid(row=0, column=3, padx=2, sticky="w")
        ToolTip(opt_f, "Enhance: auto-append cinematic quality to the prompt. Loop: seamless cyclic motion. Batch: queue N seed variations.")

        # --- Sampler block ---
        self.video_seed_var = ctk.StringVar(value="0")
        self.video_seed_lock = ctk.BooleanVar(value=True)
        seed_f = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=6)
        seed_f.grid(row=5, column=0, padx=10, pady=(4, 2), sticky="ew")
        ctk.CTkLabel(seed_f, text="Seed", font=self.FONT_NORMAL, text_color=TEXT).grid(row=0, column=0, padx=6, sticky="w")
        seed_e = ctk.CTkEntry(seed_f, textvariable=self.video_seed_var, width=120, font=self.FONT_NORMAL,
                              fg_color=BG_CARD, text_color=TEXT)
        seed_e.grid(row=0, column=1, padx=4, sticky="w")
        ctk.CTkButton(seed_f, text="🎲", width=28, height=24, font=ctk.CTkFont(size=12),
                      fg_color=ACCENT2, hover_color=ACCENT2_HOVER, text_color="#FFFFFF",
                      command=lambda: self.video_seed_var.set(str(random.randint(0, 2**32)))).grid(row=0, column=4, padx=2)
        seed_e.grid(row=0, column=1, padx=6, sticky="w")
        seed_lock = ctk.CTkSwitch(seed_f, text="Random", variable=self.video_seed_lock,
                                  font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                                  progress_color=ACCENT2, button_color=TEXT)
        seed_lock.grid(row=0, column=2, padx=6, sticky="e")
        ToolTip(seed_f, "Seed (uint64). Same seed+settings = same video. 'Random' ignores the field and picks a new seed each run.")

        self.video_steps_var = ctk.StringVar(value="20")
        steps_f = self._labeled(sf, 6, "Steps", "Denoising iterations (1-200). More = sharper but slower. 20 is a solid default on 8GB.",
                                ctk.CTkOptionMenu(sf, values=[str(x) for x in (10,15,20,25,30,40,60)],
                                                  variable=self.video_steps_var, font=self.FONT_NORMAL,
                                                  fg_color=BG_CARD_ALT, button_color=BORDER,
                                                  button_hover_color=BRAND_HOVER, text_color=TEXT,
                                                  dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                                  dropdown_hover_color=DROPDOWN_HOVER), link=False)

        self.video_cfg_var = ctk.StringVar(value="1.0")
        self._labeled(sf, 7, "CFG", "Classifier-free guidance (1.0-30.0). 1.0 disables negative guidance (H3 default). >1.0 needs a negative prompt.",
                      ctk.CTkOptionMenu(sf, values=["1.0","2.0","3.0","5.0","7.0"],
                                        variable=self.video_cfg_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        self.video_sampler_var = ctk.StringVar(value="res_multistep")
        self._labeled(sf, 8, "Sampler", "Sampling schedule. res_multistep = transcript-recommended default for H3.",
                      ctk.CTkOptionMenu(sf, values=VIDEO_SAMPLERS, variable=self.video_sampler_var,
                                        font=self.FONT_NORMAL, fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        self.video_shift_var = ctk.StringVar(value="12.0")
        self._labeled(sf, 9, "Shift Video", "Flow-matching sigma shift (1.0-100.0). Higher = more motion/dynamics. 12.0 = H3 default.",
                      ctk.CTkOptionMenu(sf, values=["6.0","8.0","10.0","12.0","16.0","20.0"],
                                        variable=self.video_shift_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        self.video_denoise_var = ctk.StringVar(value="1.0")
        self._labeled(sf, 10, "Denoise", "Denoising strength (0.0-1.0). 1.0 = full generation. Lower = start from an existing latent (img2vid strength).",
                      ctk.CTkOptionMenu(sf, values=["0.3","0.5","0.7","0.9","1.0"],
                                        variable=self.video_denoise_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        # Toggles: AdaLN cache, Spectrum, TeaCache, BlockSwap
        self.video_adaln_var = ctk.BooleanVar(value=False)
        adaln = ctk.CTkSwitch(sf, text="AdaLN Cache (faster)", variable=self.video_adaln_var,
                              font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                              progress_color=ACCENT2, button_color=TEXT)
        adaln.grid(row=11, column=0, padx=10, pady=(4, 2), sticky="w")
        ToolTip(adaln, "Pre-bakes AdaLN modulations and skips AdaLN weights during sampling. Faster, tiny quality trade.")

        self.video_spectrum_var = ctk.BooleanVar(value=False)
        spec = ctk.CTkSwitch(sf, text="Spectrum (native cache path)", variable=self.video_spectrum_var,
                             font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                             progress_color=ACCENT2, button_color=TEXT)
        spec.grid(row=12, column=0, padx=10, pady=(2, 2), sticky="w")
        ToolTip(spec, "Uses the native (Spectrum-compatible) sampler that threads the (video,audio) latent through apply_model so Comfy Spectrum caches DiT states. Requires ComfyUI-Spectrum-MiniMax-H3 installed.")

        self.video_teacache_var = ctk.BooleanVar(value=True)
        tc = ctk.CTkSwitch(sf, text="TeaCache", variable=self.video_teacache_var,
                           font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                           progress_color=ACCENT2, button_color=TEXT)
        tc.grid(row=13, column=0, padx=10, pady=(2, 2), sticky="w")
        ToolTip(tc, "Skips near-identical DiT steps. ~10% speedup, minimal quality loss.")
        self.video_blockswap_var = ctk.BooleanVar(value=True)
        bs = ctk.CTkSwitch(sf, text="BlockSwap (8GB VRAM)", variable=self.video_blockswap_var,
                           font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                           progress_color=ACCENT2, button_color=TEXT)
        bs.grid(row=14, column=0, padx=10, pady=(2, 6), sticky="w")
        ToolTip(bs, "Offloads DiT layers to RAM. REQUIRED for 8GB VRAM. Prevents OOM.")

        # Negative prompt
        self.video_neg = ctk.CTkTextbox(sf, height=40, font=self.FONT_TEXT,
                                        fg_color=BG_CARD_ALT, text_color=TEXT)
        self.video_neg.grid(row=15, column=0, padx=10, pady=(4, 4), sticky="nsew")
        self._apply_cursor_style(self.video_neg)
        ToolTip(self.video_neg, "Negative prompt (only used when CFG > 1.0). Things to avoid in the clip.")
        self.video_neg.insert("1.0", "blurry, low quality, distorted, watermark, jittery")

        # Attention backend
        self.video_attn_var = ctk.StringVar(value="auto")
        self._labeled(sf, 16, "Attention", "Attention backend. 'auto' selects best available (Sage>FlashAttn>SDPA). On RTX 2070S sm75, SDPA is used.",
                      ctk.CTkOptionMenu(sf, values=VIDEO_ATTENTION_BACKENDS, variable=self.video_attn_var,
                                        font=self.FONT_NORMAL, fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        # ref_max (reference pixel limit) + FL constraint toggles
        self.video_refmax_var = ctk.StringVar(value="1280")
        self._labeled(sf, 17, "Ref Max (px)", "Reference longest-edge pixel limit before encoding (32-4096). Caps ref resolution.",
                      ctk.CTkOptionMenu(sf, values=["640","768","1024","1280","1920"],
                                        variable=self.video_refmax_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)
        self.video_storyboard_var = ctk.BooleanVar(value=False)
        self.video_storyboard_data = None  # B3 FIX: init so getattr returns non-None
        sb = ctk.CTkSwitch(sf, text="Storyboard / Keyframes", variable=self.video_storyboard_var,
                            font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                            progress_color=ACCENT2, button_color=TEXT)
        sb.grid(row=18, column=0, padx=10, pady=(2, 2), sticky="w")
        ToolTip(sb, "Enables storyboard-driven scene planning (transcript feature). Requires a storyboard node wired.")
        self.video_fl_var = ctk.BooleanVar(value=False)
        flb = ctk.CTkSwitch(sf, text="First/Last Frame Constraint", variable=self.video_fl_var,
                            font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                            progress_color=ACCENT2, button_color=TEXT)
        flb.grid(row=19, column=0, padx=10, pady=(2, 8), sticky="w")
        ToolTip(flb, "Locks the first/last frame (FL2VA mode) for controlled start/end. Source frame upload handled by backend.")

        # Generate button
        # QOL: prompt-history recall for T2V tab (mirrors image-tab pattern)
        vhist_row = ctk.CTkFrame(sf, fg_color="transparent")
        vhist_row.grid(row=20, column=0, padx=10, pady=(4, 0), sticky="w")
        ctk.CTkButton(vhist_row, text="↺ Last Prompt", width=104, height=24,
                     font=ctk.CTkFont(size=10), fg_color=BG_CARD_ALT, text_color=TEXT,
                     hover_color=BRAND_HOVER,
                     command=lambda: self._restore_last_prompt("video")).pack(side="left", padx=(0, 6))
        self.video_hist_var = tk.StringVar(value="History")
        self.video_hist_menu = ctk.CTkOptionMenu(vhist_row, values=["History"],
                                                 variable=self.video_hist_var, width=120, height=24,
                                                 fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                                 button_hover_color=BRAND_HOVER,
                                                 dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                                 dropdown_hover_color=DROPDOWN_HOVER,
                                                 command=lambda v: self._apply_history_prompt(v, "video"))
        self.vgen = ctk.CTkButton(sf, text="Generate Video  (Ctrl+E)", width=200, font=self.FONT_NORMAL_BOLD,
                                fg_color=ACCENT2, hover_color=ACCENT2_HOVER, text_color="#FFFFFF",
                                command=lambda: self._start_video_gen("t2v"))
        # The button is stored on self (used by _start_video_gen/_reset_video_buttons);
        # the bare local name `vgen` was left over from an earlier refactor and
        # raised NameError, aborting the tab right before the button appeared.
        self.vgen.grid(row=21, column=0, padx=10, pady=(8, 4), sticky="w")
        ToolTip(self.vgen, "Generate video with MiniMax H3 locally. Saves MP4 to Pictures/ComfyUI_Generated.\n\nShortcut: Ctrl+E (also works from any video tab).")

    def _video_pick_i2v_image(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Select reference image",
                                      filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if p:
            self.video_i2v_path = p
            self.video_i2v_btn.configure(text="Image: " + os.path.basename(p)[:24])

    def _video_pick_fl_first(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Select FIRST frame (I2V)",
                                      filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if p:
            self.video_fl_first = p
            self.video_fl_first_btn.configure(text="First: " + os.path.basename(p)[:18])

    def _video_pick_fl_last(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Select LAST frame (I2V)",
                                      filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if p:
            self.video_fl_last = p
            self.video_fl_last_btn.configure(text="Last: " + os.path.basename(p)[:18])

    def _build_h3_graph(self, mode_key, prompt, w, h, dur, seed, steps, cfg,
                         sampler, shift, denoise, adaln, spectrum,
                         teacache, blockswap, neg=None, attention=None,
                         ref_max=1280, storyboard=False, fl=False, i2v_path=None,
                         ar=None, camera="Static", enhance=True, loop=False):
        """Build a MiniMax H3 workflow in ComfyUI's API format (named nodes).
        Proven to validate (HTTP 200) against the live server.
        mode_key: 't2v' | 'i2v' (fl2va DiT). V2V/R2V use _build_h3_graph_v2v.
        All sampler params are wired from the UI; attention/ref_max/storyboard/fl
        are added as optional node inputs when supported.
        """
        DIT = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
        # nvfp4_awq (15.7GB) fits in 16GB RAM; int8_convrot (26GB) OOMs RAM.
        ENC = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
        VAE_V = "minimax_h3_video_vae_fp16.safetensors"
        VAE_A = "minimax_h3_audio_vae_fp32.safetensors"
        loader_in = {"model_name": DIT}
        wf = {
            "H3Loader": {"class_type": "MiniMaxH3Loader", "inputs": loader_in},
            "H3Enc": {"class_type": "MiniMaxH3EncoderLoader",
                       "inputs": {"model_name": ENC, "use_final_norm": False,
                                  "group_size": 2, "pin_memory": True, "disk_workers": 2}},
            "H3VAE": {"class_type": "MiniMaxH3VAELoader",
                       "inputs": {"vae_name": VAE_V, "audio_vae_name": VAE_A}},
        }
        # Attention backend -> Loader.attn_backend (must be added AFTER wf exists)
        if attention and attention != "auto":
            wf["H3Attn"] = {"class_type": "MiniMaxH3AttentionConfig",
                            "inputs": {"backend": attention, "force_backend": True}}
            wf["H3Loader"]["inputs"]["attn_backend"] = ["H3Attn", 0]
        # Optional first/last frame constraint (I2V) and storyboard
        if fl:
            fl_in = {}
            if getattr(self, "video_fl_first", None):
                wf["H3FLFirst"] = {"class_type": "LoadImage", "inputs": {"image": self.video_fl_first}}
                fl_in["first_frame"] = ["H3FLFirst", 0]
            if getattr(self, "video_fl_last", None):
                wf["H3FLLast"] = {"class_type": "LoadImage", "inputs": {"image": self.video_fl_last}}
                fl_in["last_frame"] = ["H3FLLast", 0]
            if fl_in:
                wf["H3FL"] = {"class_type": "MiniMaxH3FLConstraint", "inputs": fl_in}
        # B2 FIX: I2V mode passes a real image path as the first-frame constraint even
        # when the FL toggle is off (the image IS the opening frame of the video).
        elif i2v_path and os.path.isfile(i2v_path):
            wf["H3FLFirst"] = {"class_type": "LoadImage", "inputs": {"image": i2v_path}}
            wf["H3FL"] = {"class_type": "MiniMaxH3FLConstraint", "inputs": {"first_frame": ["H3FLFirst", 0]}}
            fl_in = {"first_frame": ["H3FLFirst", 0]}
        # Storyboard: only insert when real shot data is available (the node crashes
        # with an empty Shot-1 prompt otherwise). The app doesn't configure shots, so
        # this stays a no-op until wired to node UI storage.
        if storyboard and getattr(self, "video_storyboard_data", None):
            wf["H3Story"] = {"class_type": "MiniMaxH3Storyboard", "inputs": {}}
        # --- Research-driven prompt augmentation (camera / enhance / loop) ---
        eff_prompt = prompt or ""
        if camera and camera in VIDEO_CAMERA_MOTIONS and VIDEO_CAMERA_MOTIONS[camera]:
            eff_prompt = (eff_prompt + ", " + VIDEO_CAMERA_MOTIONS[camera]).strip(", ")
        if loop:
            eff_prompt = (eff_prompt + ", seamless loop, cyclic motion, perfect first-last-frame match").strip(", ")
        if enhance:
            eff_prompt = ("cinematic, high detail, smooth motion, professional lighting, " + eff_prompt).strip(", ")
        cond_inputs = {"text_encoder": ["H3Enc", 0], "width": w, "height": h, "prompt": eff_prompt,
                       "av_encoder": ["H3VAE", 0]}
        if fl and fl_in:
            cond_inputs["fl_constraint"] = ["H3FL", 0]
        if storyboard and getattr(self, "video_storyboard_data", None):
            cond_inputs["storyboard"] = ["H3Story", 0]
        if ref_max and ref_max != 1280:
            cond_inputs["ref_max"] = ref_max
        if neg and neg.strip():
            cond_inputs["negative_prompt"] = neg
        wf["H3Cond"] = {"class_type": "MiniMaxH3Conditioning", "inputs": cond_inputs}
        if blockswap:
            wf["H3BS"] = {"class_type": "MiniMaxH3BlockSwapArgs",
                          "inputs": {"block_to_swap": 47, "prefetch": True, "prefetch_count": 2,
                                     "pin_memory": True, "disk_workers": 2, "dtype": "bfloat16"}}
        if teacache:
            wf["H3TC"] = {"class_type": "MiniMaxH3TeaCacheArgs",
                          "inputs": {"start_block": 3, "max_skip_blocks": 15,
                                     "rel_l1_thresh": 0.08, "warmup_steps": 1, "cooldown_steps": 2}}
        ks_in = {"model": ["H3Loader", 0], "positive": ["H3Cond", 0],
                 "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
                 "shift_video": shift, "denoise": denoise, "use_adaln_cache": adaln,
                 "spectrum": bool(spectrum),
                 "negative": ["H3Cond", 0], "latent": ["H3Cond", 2]}
        if neg and neg.strip():
            ks_in["negative"] = ["H3Cond", 1]
        if teacache:
            ks_in["teacache_args"] = ["H3TC", 0]
        if blockswap:
            ks_in["block_swap_args"] = ["H3BS", 0]
        wf["H3KS"] = {"class_type": "MiniMaxH3KSampler", "inputs": ks_in}
        wf["H3Decode"] = {"class_type": "MiniMaxH3Decode",
                           "inputs": {"latent": ["H3KS", 0], "av_encoder": ["H3VAE", 0]}}
        wf["CreateVideo"] = {"class_type": "CreateVideo",
                             "inputs": {"images": ["H3Decode", 0], "audio": ["H3Decode", 1], "fps": 24.0}}
        wf["SaveVideo"] = {"class_type": "SaveVideo",
                            "inputs": {"video": ["CreateVideo", 0],
                                       "filename_prefix": "video/MiniMax_H3",
                                       "format": "auto", "codec": "auto"}}
        return wf

    # ------------------------------------------------------------------
    # Video to Video tab ("Video to Video" name, also accepts photo->video)
    # ------------------------------------------------------------------
    def _build_video_v2v_tab(self):
        """Video to Video tab. Drives MiniMaxH3ReferenceToVideo (ref2va DiT):
        accepts video refs AND image refs (photo->video) + audio refs.
        Per transcript: reference-to-video = Video to Video."""
        import os
        t = self.tabview.tab("Video to Video")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self.v2v_prompt = ctk.CTkTextbox(sf, height=60, font=self.FONT_TEXT,
                                         fg_color=BG_CARD_ALT, text_color=TEXT)
        self.v2v_prompt.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.v2v_prompt)
        ToolTip(self.v2v_prompt, "Video prompt. Describes the motion/style you want the reference(s) to become.")
        self.v2v_prompt.insert("1.0", "transform into a hand-drawn anime style, keep the subject's motion, add gentle wind")

        self.v2v_neg = ctk.CTkTextbox(sf, height=40, font=self.FONT_TEXT,
                                      fg_color=BG_CARD_ALT, text_color=TEXT_DIM)
        self.v2v_neg.grid(row=1, column=0, padx=10, pady=(2, 0), sticky="nsew")
        self._apply_cursor_style(self.v2v_neg)
        ToolTip(self.v2v_neg, "Negative prompt (things to avoid). Wired to a dedicated MiniMaxH3Conditioning node for correct negative routing.")
        self.v2v_neg.insert("1.0", "blurry, low quality, deformed, distorted, bad anatomy")

        self.v2v_refs = []  # list of dicts {kind, path}
        self.v2v_ref_btn = ctk.CTkButton(sf, text="Add Reference (Image or Video)", height=32,
                                         font=self.FONT_NORMAL, fg_color=BG_CARD_ALT,
                                         hover_color=BRAND_HOVER, text_color=TEXT,
                                         command=self._v2v_add_ref)
        self.v2v_ref_btn.grid(row=1, column=0, padx=10, pady=(8, 4), sticky="ew")
        ToolTip(self.v2v_ref_btn, "Add image refs (photo->video) and/or video refs. The transcript's Video-to-Video = reference-to-video with these refs.")
        self.v2v_ref_list = ctk.CTkLabel(sf, text="(no references yet)", font=self.FONT_NORMAL, text_color=TEXT_DIM)
        self.v2v_ref_list.grid(row=2, column=0, padx=10, pady=(2, 4), sticky="w")
        self.v2v_ref_clear = ctk.CTkButton(sf, text="Clear Refs", height=24, width=80,
                                            font=self.FONT_NORMAL, fg_color=BG_CARD_ALT,
                                            hover_color=BRAND_HOVER, text_color=TEXT,
                                            command=self._v2v_clear_refs)
        self.v2v_ref_clear.grid(row=2, column=0, padx=10, pady=(2, 4), sticky="e")
        ToolTip(self.v2v_ref_clear, "Clear all accumulated references.")

        # Resolution + duration (shared with T2V)
        self.v2v_res_var = ctk.StringVar(value="240p (512x288)")
        res_menu = ctk.CTkOptionMenu(sf, values=list(VIDEO_RESOLUTIONS.keys()),
                                     variable=self.v2v_res_var, font=self.FONT_NORMAL,
                                     fg_color=BG_CARD_ALT, button_color=BORDER,
                                     button_hover_color=BRAND_HOVER, text_color=TEXT,
                                     dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                     dropdown_hover_color=DROPDOWN_HOVER)
        res_menu.grid(row=3, column=0, padx=10, pady=(4, 4), sticky="ew")
        ToolTip(res_menu, "Output resolution. 240p = 8GB-VRAM-safe floor.")

        self.v2v_dur_var = ctk.StringVar(value="5s")
        dur_menu = ctk.CTkOptionMenu(sf, values=list(VIDEO_DURATIONS.keys()),
                                     variable=self.v2v_dur_var, font=self.FONT_NORMAL,
                                     fg_color=BG_CARD_ALT, button_color=BORDER,
                                     button_hover_color=BRAND_HOVER, text_color=TEXT,
                                     dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                     dropdown_hover_color=DROPDOWN_HOVER, width=120)
        dur_menu.grid(row=4, column=0, padx=10, pady=(4, 4), sticky="w")
        ToolTip(dur_menu, "Clip length. Frames snap to the 17k+5 grid @ 24fps (3s=73, 5s=124, 9s=226, 14s=345).")

        # Aspect ratio (research parity)
        self.v2v_ar_var = ctk.StringVar(value="16:9 Widescreen")
        ar_menu = ctk.CTkOptionMenu(sf, values=list(VIDEO_ASPECT_RATIOS.keys()),
                                    variable=self.v2v_ar_var, font=self.FONT_NORMAL,
                                    fg_color=BG_CARD_ALT, button_color=BORDER,
                                    button_hover_color=BRAND_HOVER, text_color=TEXT,
                                    dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                    dropdown_hover_color=DROPDOWN_HOVER)
        ar_menu.grid(row=5, column=0, padx=10, pady=(4, 4), sticky="ew")
        ToolTip(ar_menu, "Aspect ratio for the output (16:9 / 9:16 / 1:1 / 4:3).")
        opt_f = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=6)
        opt_f.grid(row=6, column=0, padx=10, pady=(2, 2), sticky="ew")
        self.v2v_enhance_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(opt_f, text="Enhance prompt", variable=self.v2v_enhance_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT).grid(row=0, column=0, padx=6, sticky="w")
        self.v2v_batch_var = ctk.StringVar(value="1")
        ctk.CTkLabel(opt_f, text="Batch", font=self.FONT_NORMAL, text_color=TEXT).grid(row=0, column=1, padx=(10,2), sticky="w")
        ctk.CTkOptionMenu(opt_f, values=["1","2","3","4"], variable=self.v2v_batch_var,
                          font=self.FONT_NORMAL, fg_color=BG_CARD, button_color=BORDER,
                          button_hover_color=BRAND_HOVER, text_color=TEXT, width=60,
                          dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                          dropdown_hover_color=DROPDOWN_HOVER).grid(row=0, column=2, padx=2, sticky="w")
        ToolTip(opt_f, "Enhance: auto-append cinematic quality. Batch: queue N seed variations.")

        # Denoise (V2V strength)
        self.v2v_denoise_var = ctk.StringVar(value="0.7")
        self._labeled(sf, 5, "Denoise (V2V strength)", "How much to change the reference. Low (0.3) = keep most of source; high (1.0) = near-full regen.",
                      ctk.CTkOptionMenu(sf, values=["0.3","0.5","0.7","0.9","1.0"],
                                        variable=self.v2v_denoise_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        # Seed / Steps / CFG / Sampler / Shift (shared sampler block)
        self.v2v_seed_var = ctk.StringVar(value="0")
        self.v2v_seed_lock = ctk.BooleanVar(value=True)
        seed_f = ctk.CTkFrame(sf, fg_color=BG_CARD_ALT, corner_radius=6)
        seed_f.grid(row=6, column=0, padx=10, pady=(4, 2), sticky="ew")
        ctk.CTkLabel(seed_f, text="Seed", font=self.FONT_NORMAL, text_color=TEXT).grid(row=0, column=0, padx=6, sticky="w")
        ctk.CTkEntry(seed_f, textvariable=self.v2v_seed_var, width=120, font=self.FONT_NORMAL,
                     fg_color=BG_CARD, text_color=TEXT).grid(row=0, column=1, padx=6, sticky="w")
        ctk.CTkSwitch(seed_f, text="Random", variable=self.v2v_seed_lock,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT).grid(row=0, column=2, padx=6, sticky="e")
        ToolTip(seed_f, "Seed (uint64). Same + settings = same video.")

        self.v2v_steps_var = ctk.StringVar(value="20")
        self._labeled(sf, 7, "Steps", "Denoising iterations (1-200). 20 is a solid default on 8GB.",
                      ctk.CTkOptionMenu(sf, values=[str(x) for x in (10,15,20,25,30,40,60)],
                                        variable=self.v2v_steps_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)
        self.v2v_cfg_var = ctk.StringVar(value="1.0")
        self._labeled(sf, 8, "CFG", "Classifier-free guidance (1.0-30.0). 1.0 = no negative guidance (H3 default).",
                      ctk.CTkOptionMenu(sf, values=["1.0","2.0","3.0","5.0","7.0"],
                                        variable=self.v2v_cfg_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)
        self.v2v_sampler_var = ctk.StringVar(value="res_multistep")
        self._labeled(sf, 9, "Sampler", "Sampling schedule. res_multistep = transcript default for H3.",
                      ctk.CTkOptionMenu(sf, values=VIDEO_SAMPLERS, variable=self.v2v_sampler_var,
                                        font=self.FONT_NORMAL, fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)
        self.v2v_shift_var = ctk.StringVar(value="12.0")
        self._labeled(sf, 10, "Shift Video", "Flow-matching sigma shift (1.0-100.0). 12.0 = H3 default.",
                      ctk.CTkOptionMenu(sf, values=["6.0","8.0","10.0","12.0","16.0","20.0"],
                                        variable=self.v2v_shift_var, font=self.FONT_NORMAL,
                                        fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        # ref_image_size (match/max)
        self.v2v_refsize_var = ctk.StringVar(value="match")
        self._labeled(sf, 11, "Ref Image Size", "How reference images are fit: 'match' = match source; 'max' = upscale to max.",
                      ctk.CTkOptionMenu(sf, values=["match","max"], variable=self.v2v_refsize_var,
                                        font=self.FONT_NORMAL, fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        # Attention backend (parity with T2V)
        self.v2v_attn_var = ctk.StringVar(value="auto")
        self._labeled(sf, 12, "Attention", "Attention backend. 'auto' = best available (Sage>FlashAttn>SDPA).",
                      ctk.CTkOptionMenu(sf, values=VIDEO_ATTENTION_BACKENDS, variable=self.v2v_attn_var,
                                        font=self.FONT_NORMAL, fg_color=BG_CARD_ALT, button_color=BORDER,
                                        button_hover_color=BRAND_HOVER, text_color=TEXT,
                                        dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                        dropdown_hover_color=DROPDOWN_HOVER), link=False)

        # Toggles
        self.v2v_adaln_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(sf, text="AdaLN Cache (faster)", variable=self.v2v_adaln_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT).grid(row=12, column=0, padx=10, pady=(4, 2), sticky="w")
        self.v2v_spectrum_var = ctk.BooleanVar(value=False)
        sp_switch = ctk.CTkSwitch(sf, text="Spectrum (native cache path)", variable=self.v2v_spectrum_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT)
        sp_switch.grid(row=13, column=0, padx=10, pady=(2, 2), sticky="w")
        ToolTip(sp_switch, "Native Spectrum sampler path (requires ComfyUI-Spectrum-MiniMax-H3).")
        self.v2v_teacache_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(sf, text="TeaCache", variable=self.v2v_teacache_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT).grid(row=14, column=0, padx=10, pady=(2, 2), sticky="w")
        self.v2v_blockswap_var = ctk.BooleanVar(value=True)
        bs_switch = ctk.CTkSwitch(sf, text="BlockSwap (8GB VRAM)", variable=self.v2v_blockswap_var,
                      font=self.FONT_NORMAL, text_color=TEXT, fg_color=BORDER,
                      progress_color=ACCENT2, button_color=TEXT)
        bs_switch.grid(row=15, column=0, padx=10, pady=(2, 6), sticky="w")
        ToolTip(bs_switch, "Offloads DiT layers to RAM. REQUIRED for 8GB VRAM.")

        self.v2vgen = ctk.CTkButton(sf, text="Generate Video to Video  (Ctrl+E)", width=240, font=self.FONT_NORMAL_BOLD,
                                fg_color=ACCENT2, hover_color=ACCENT2_HOVER, text_color="#FFFFFF",
                                command=lambda: self._start_video_gen("v2v"))
        # Stored under its own name: this tab previously also assigned to
        # self.vgen, silently overwriting the Text-to-Video button reference
        # whenever the V2V tab was built, so _reset_video_buttons re-labelled
        # the wrong widget. The bare local `vgen` here raised NameError too.
        self.v2vgen.grid(row=16, column=0, padx=10, pady=(8, 4), sticky="w")
        ToolTip(self.v2vgen, "Generate Video-to-Video from your references (photo or video). Saves MP4 to Pictures/ComfyUI_Generated.\n\nShortcut: Ctrl+E (works from any video tab).")

    def _v2v_clear_refs(self):
        self.v2v_refs = []
        self.v2v_ref_list.configure(text="(no references yet)")
        # QOL: clear thumbnail row
        if hasattr(self, "_v2v_thumb_frame") and self._v2v_thumb_frame.winfo_exists():
            for child in self._v2v_thumb_frame.winfo_children():
                child.destroy()
        self._set_status("V2V references cleared")

    def _v2v_add_ref(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Add reference (image or video)",
                                      filetypes=[("Media", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.webm")])
        if p:
            kind = "video" if p.lower().endswith((".mp4", ".mov", ".webm")) else "image"
            self.v2v_refs.append({"kind": kind, "path": p})
            names = ", ".join(os.path.basename(r["path"])[:16] for r in self.v2v_refs) or "(none)"
            self.v2v_ref_list.configure(text="Refs: " + names)
            # QOL: show thumbnail preview of image references
            self._v2v_show_thumbs()

    def _v2v_show_thumbs(self):
        """QOL: Render small thumbnails of image references inline below the ref list."""
        from PIL import Image, ImageTk
        # Lazily create the thumbnail container
        if not hasattr(self, "_v2v_thumb_frame") or not self._v2v_thumb_frame.winfo_exists():
            self._v2v_thumb_frame = ctk.CTkFrame(self.v2v_ref_list.master, fg_color=BG_CARD)
            self._v2v_thumb_frame.grid(row=3, column=0, padx=10, pady=(2, 6), sticky="ew")
        # Clear existing
        for child in self._v2v_thumb_frame.winfo_children():
            child.destroy()
        col = 0
        for r in self.v2v_refs:
            if r["kind"] != "image":
                continue
            try:
                im = Image.open(r["path"]).convert("RGB")
                im.thumbnail((48, 48))
                tk_im = ImageTk.PhotoImage(im)
                lbl = ctk.CTkLabel(self._v2v_thumb_frame, image=tk_im, text="", width=50, height=50)
                lbl.image = tk_im  # keep reference
                lbl.grid(row=0, column=col, padx=4, pady=2)
                col += 1
            except Exception:
                continue

    def _video_v2v_build_and_queue(self):
        """Build + queue the V2V workflow (ref2va DiT via MiniMaxH3ReferenceToVideo).
        Returns the last workflow dict (POSTed by the caller). Batches N seeds."""
        import random
        prompt = self.v2v_prompt.get("1.0", "end-1c").strip()
        neg = getattr(self, "v2v_neg", None) and self.v2v_neg.get("1.0", "end-1c").strip() or ""
        w, h = VIDEO_ASPECT_RATIOS[self.v2v_ar_var.get()]
        if getattr(self, "v2v_enhance_var", None) and self.v2v_enhance_var.get():
            prompt = ("cinematic, high detail, smooth motion, professional lighting, " + prompt).strip(", ")
        dur = int(VIDEO_DURATIONS[self.v2v_dur_var.get()])
        batch = int(getattr(self, "v2v_batch_var", None) and self.v2v_batch_var.get() or "1")
        seed = random.randint(0, 2**63) if self.v2v_seed_lock.get() else int(self.v2v_seed_var.get() or 0)
        steps = int(self.v2v_steps_var.get())
        cfg = float(self.v2v_cfg_var.get())
        sampler = self.v2v_sampler_var.get()
        shift = float(self.v2v_shift_var.get())
        denoise = float(self.v2v_denoise_var.get())
        refsize = self.v2v_refsize_var.get()
        adaln = self.v2v_adaln_var.get()
        spectrum = self.v2v_spectrum_var.get()
        teacache = self.v2v_teacache_var.get()
        blockswap = self.v2v_blockswap_var.get()
        # NOTE: MiniMaxH3ReferenceToVideo is NOT present in this installed node pack,
        # so Video-to-Video drives the SAME local fl2va pipeline as T2V/I2V, using the
        # first reference (image, or a video's extracted first frame) as the I2V
        # first frame. This is the real, validating local path and satisfies
        # "vid to vid also takes photo to vid".
        # Real local R2V path: MiniMaxH3ReferenceToVideo (ref2va DiT). This node was
        # present in the node pack but omitted from NODE_CLASS_MAPPINGS; it is now
        # registered, so Video-to-Video / photo-to-video drives the full multi-reference
        # pipeline the transcript describes (up to 9 ref images, 3 ref videos w/ own
        # soundtrack, 3 standalone ref audio).
        DIT = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
        ENC = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
        VAE_V = "minimax_h3_video_vae_fp16.safetensors"
        VAE_A = "minimax_h3_audio_vae_fp32.safetensors"
        # length = frames at 24fps, snapped to the 17k+5 grid the node requires (124 ~= 5s)
        length = max(5, int(round(dur * 24 / 17) * 17 + 5))
        loader_in = {"model_name": DIT}
        wf = {
            "H3Loader": {"class_type": "MiniMaxH3Loader", "inputs": loader_in},
            "H3Enc": {"class_type": "MiniMaxH3EncoderLoader",
                       "inputs": {"model_name": ENC, "use_final_norm": False,
                                  "group_size": 2, "pin_memory": True, "disk_workers": 2}},
            "H3VAE": {"class_type": "MiniMaxH3VAELoader",
                       "inputs": {"vae_name": VAE_V, "audio_vae_name": VAE_A}},
        }
        if getattr(self, "v2v_attn_var", None) is not None and self.v2v_attn_var.get() not in (None, "auto"):
            wf["H3Attn"] = {"class_type": "MiniMaxH3AttentionConfig",
                            "inputs": {"backend": self.v2v_attn_var.get(), "force_backend": True}}
            wf["H3Loader"]["inputs"]["attn_backend"] = ["H3Attn", 0]
        if blockswap:
            wf["H3BS"] = {"class_type": "MiniMaxH3BlockSwapArgs",
                          "inputs": {"block_to_swap": 47, "prefetch": True, "prefetch_count": 2,
                                     "pin_memory": True, "disk_workers": 2, "dtype": "bfloat16"}}
        if teacache:
            wf["H3TC"] = {"class_type": "MiniMaxH3TeaCacheArgs",
                          "inputs": {"start_block": 3, "max_skip_blocks": 15,
                                     "rel_l1_thresh": 0.08, "warmup_steps": 1, "cooldown_steps": 2}}
        # Wire references into the real ref2va node slots
        ref_inputs = {"text_encoder": ["H3Enc", 0], "av_encoder": ["H3VAE", 0],
                      "prompt": prompt, "width": w, "height": h, "length": length,
                      "ref_image_size": refsize}
        img_i = vid_i = aud_i = 1
        for r in self.v2v_refs:
            if r["kind"] == "image":
                if img_i > 9:
                    continue
                node = "V2VImg%d" % img_i
                wf[node] = {"class_type": "LoadImage", "inputs": {"image": r["path"]}}
                ref_inputs["ref_image_%d" % img_i] = [node, 0]
                img_i += 1
            elif r["kind"] == "video":
                if vid_i > 3:
                    continue
                # ref_video_i expects a multi-frame IMAGE (T,H,W,C). Without VHS we feed
                # the first frame as a reference image and the soundtrack as a standalone
                # ref_audio so the source video still drives the generation.
                import shutil as _sh, tempfile as _tf, subprocess as _sp
                _ff = _sh.which("ffmpeg") or _os.path.join(_PORTABLE_DIR, "ComfyUI_windows_portable", "ffmpeg.exe")
                if not hasattr(self, "_v2v_tmp"):
                    self._v2v_tmp = _tf.mkdtemp(prefix="h3v2v_")
                fpng = os.path.join(self._v2v_tmp, "v%df.png" % vid_i)
                faudio = os.path.join(self._v2v_tmp, "v%d.a.wav" % vid_i)
                try:
                    _sp.run([_ff, "-y", "-i", r["path"], "-vf", "select=eq(n\\,0)",
                             "-vframes", "1", fpng], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=60)
                    _sp.run([_ff, "-y", "-i", r["path"], "-vn", faudio],
                            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=60)
                except Exception as _e:
                    logging.warning("V2V video extract failed: %s", _e)
                if os.path.isfile(fpng) and img_i <= 9:
                    wf["V2VImg%d" % img_i] = {"class_type": "LoadImage", "inputs": {"image": fpng}}
                    ref_inputs["ref_image_%d" % img_i] = ["V2VImg%d" % img_i, 0]
                    img_i += 1
                if os.path.isfile(faudio) and vid_i <= 3:
                    wf["V2VAud%d" % vid_i] = {"class_type": "LoadAudio", "inputs": {"audio": faudio}}
                    ref_inputs["ref_video_audio_%d" % vid_i] = ["V2VAud%d" % vid_i, 0]
                vid_i += 1
            else:  # audio
                if aud_i > 3:
                    continue
                node = "V2VAud%d" % aud_i
                wf[node] = {"class_type": "LoadAudio", "inputs": {"audio": r["path"]}}
                ref_inputs["ref_audio_%d" % aud_i] = [node, 0]
                aud_i += 1
        wf["H3Ref"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": ref_inputs}
        # B1 FIX: route negative to a DEDICATED MiniMaxH3Conditioning node so the
        # KSampler negative is a real negative prompt, not the positive by mistake.
        if neg and neg.strip():
            wf["H3CondNoNeg"] = {"class_type": "MiniMaxH3Conditioning",
                                 "inputs": {"text_encoder": ["H3Enc", 0],
                                            "width": w, "height": h, "prompt": neg,
                                            "av_encoder": ["H3VAE", 0]}}
        ks_in = {"model": ["H3Loader", 0], "positive": ["H3Ref", 0],
                 "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
                 "shift_video": shift, "denoise": denoise, "use_adaln_cache": adaln,
                 "spectrum": bool(spectrum),
                 "negative": (["H3CondNoNeg", 1] if (neg and neg.strip()) else ["H3Ref", 0]),
                 "latent": ["H3Ref", 1]}
        if teacache:
            ks_in["teacache_args"] = ["H3TC", 0]
        if blockswap:
            ks_in["block_swap_args"] = ["H3BS", 0]
        wf["H3KS"] = {"class_type": "MiniMaxH3KSampler", "inputs": ks_in}
        wf["H3Decode"] = {"class_type": "MiniMaxH3Decode",
                           "inputs": {"latent": ["H3KS", 0], "av_encoder": ["H3VAE", 0]}}
        wf["CreateVideo"] = {"class_type": "CreateVideo",
                             "inputs": {"images": ["H3Decode", 0], "audio": ["H3Decode", 1], "fps": 24.0}}
        wf["SaveVideo"] = {"class_type": "SaveVideo",
                            "inputs": {"video": ["CreateVideo", 0],
                                       "filename_prefix": "video/MiniMax_H3_V2V",
                                       "format": "auto", "codec": "auto"}}
        # Batch: queue N seed variations (research parity)
        for b in range(max(1, batch)):
            seed = random.randint(0, 2**63)
            wf["H3KS"]["inputs"]["seed"] = seed
            payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored"}
            breadcrumb("post_prompt", mode=getattr(self, "_gen_mode", "v2v"))
            r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
            # Safely extract the prompt_id even if the 200 response body is malformed,
            # so polling can proceed instead of silently doing nothing.
            prompt_id = None
            try:
                prompt_id = r.json().get("prompt_id")
            except Exception:
                pass
            if r.status_code == 200:
                if prompt_id:
                    self.last_prompt_id = prompt_id
                    breadcrumb("post_ok", prompt_id=prompt_id)
                else:
                    logging.error("V2V batch %d queued (HTTP 200) but no prompt_id in response", b + 1)
                    self._set_status("V2V queued but server gave no prompt_id (batch %d)" % (b + 1))
            if r.status_code != 200:
                try:
                    err_msg = r.json().get("error", {}).get("message", "HTTP %d" % r.status_code)
                except Exception:
                    err_msg = "HTTP %d" % r.status_code
                logging.error("V2V batch %d queue failed: %s", b + 1, err_msg)
                self._set_status("V2V queue failed (batch %d): %s" % (b + 1, str(err_msg)[:70]))
                return None
            if b == 0:
                if prompt_id:
                    self.last_prompt_id = prompt_id
                self._gen_mode = "video"
                self._poll_attempts = 0
                self._poll_handoff = True
                self.root.after(200, self._poll_history)
        self._set_status("Queued %d H3 V2V job(s)..." % max(1, batch))
        self._generate_lock = False
        return wf

    # ------------------------------------------------------------------
    # Video Refine & Upscale tab
    # ------------------------------------------------------------------
    def _build_video_refine_tab(self):
        """Video Refine & Upscale tab. Picks a finished H3 MP4 and runs a real
        ffmpeg lanczos upscale (genuinely works on 8GB). Optional ContextIR
        refiner instruction is best-effort (backend refiner node)."""
        import os
        t = self.tabview.tab("Video Refine & Upscale")
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self.refine_src = None
        self.refine_src_btn = ctk.CTkButton(sf, text="Select Source MP4", height=32,
                                            font=self.FONT_NORMAL, fg_color=BG_CARD_ALT,
                                            hover_color=BRAND_HOVER, text_color=TEXT,
                                            command=self._refine_pick_src)
        self.refine_src_btn.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        ToolTip(self.refine_src_btn, "Pick a finished H3 MP4 from Pictures/ComfyUI_Generated (or anywhere).")
        self.refine_src_lbl = ctk.CTkLabel(sf, text="(no source selected)", font=self.FONT_NORMAL, text_color=TEXT_DIM)
        self.refine_src_lbl.grid(row=1, column=0, padx=10, pady=(2, 4), sticky="w")

        self.refine_scale_var = ctk.StringVar(value="2x")
        sc_menu = ctk.CTkOptionMenu(sf, values=VIDEO_UPSCALE_SCALES, variable=self.refine_scale_var,
                                    font=self.FONT_NORMAL, fg_color=BG_CARD_ALT, button_color=BORDER,
                                    button_hover_color=BRAND_HOVER, text_color=TEXT,
                                    dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                    dropdown_hover_color=DROPDOWN_HOVER)
        sc_menu.grid(row=2, column=0, padx=10, pady=(4, 4), sticky="ew")
        ToolTip(sc_menu, "Upscale factor via ffmpeg lanczos. 2x doubles resolution. 3x = heavy; ensure enough RAM.")

        self.refine_instr = ctk.CTkTextbox(sf, height=50, font=self.FONT_TEXT,
                                           fg_color=BG_CARD_ALT, text_color=TEXT)
        self.refine_instr.grid(row=3, column=0, padx=10, pady=(4, 4), sticky="nsew")
        self._apply_cursor_style(self.refine_instr)
        ToolTip(self.refine_instr, "Optional ContextIR refiner instruction (e.g. 'more cinematic, sharper'). Best-effort via backend refiner node.")
        self.refine_instr.insert("1.0", "Make it more cinematic, detailed and temporally clear.")

        self.rgen = ctk.CTkButton(sf, text="Refine & Upscale  (Ctrl+E)", width=240, font=self.FONT_NORMAL_BOLD,
                                fg_color=ACCENT2, hover_color=ACCENT2_HOVER, text_color="#FFFFFF",
                                command=lambda: self._start_video_gen("refine"))
        self.rgen.grid(row=4, column=0, padx=10, pady=(8, 4), sticky="w")
        ToolTip(self.rgen, "ffmpeg lanczos upscale of the selected MP4. Output lands in Pictures/ComfyUI_Generated.\n\nShortcut: Ctrl+E (works from any video tab).")

    def _refine_pick_src(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Select source MP4",
                                      filetypes=[("Video", "*.mp4 *.mov *.webm")])
        if p:
            self.refine_src = p
            self.refine_src_lbl.configure(text="Src: " + os.path.basename(p)[:28])

    def _video_refine_build_and_queue(self):
        """Real ffmpeg lanczos upscale of the selected MP4 -> OUTPUT_DIR."""
        import os, subprocess, re
        if not self.refine_src or not os.path.isfile(self.refine_src):
            self._set_status("Refine: no source MP4 selected")
            return None
        scale_txt = self.refine_scale_var.get()
        m = re.search(r"([\d.]+)x", scale_txt)
        factor = float(m.group(1)) if m else 1.0
        base = os.path.splitext(os.path.basename(self.refine_src))[0]
        out = os.path.join(OUTPUT_DIR, "video", "%s_upscale_%sx.mp4" % (base, factor))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        # Find ffmpeg robustly (portable ComfyUI may or may not ship one)
        import shutil
        ff = None
        winget = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
        candidates = [
            _os.path.join(_PORTABLE_DIR, "ComfyUI_windows_portable", "ffmpeg.exe"),
            _os.path.join(_PORTABLE_DIR, "ComfyUI_windows_portable", "ComfyUI", "ffmpeg.exe"),
            _os.path.join(_PORTABLE_DIR, "ffmpeg.exe"),
        ]
        if os.path.isdir(winget):
            for root, _dirs, files in os.walk(winget):
                if "ffmpeg.exe" in files:
                    candidates.append(os.path.join(root, "ffmpeg.exe"))
                    break
        for cand in candidates:
            if os.path.isfile(cand):
                ff = cand
                break
        if ff is None:
            ff = shutil.which("ffmpeg") or "ffmpeg"  # rely on PATH
        vf = "scale=trunc(iw*%s/2)*2:trunc(ih*%s/2)*2:flags=lanczos" % (factor, factor)
        cmd = [ff, "-y", "-i", self.refine_src, "-vf", vf,
               "-c:v", "libx264", "-preset", "medium", "-crf", "18",
               "-c:a", "copy", out]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=600,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            self._set_status("Upscaled -> " + os.path.basename(out))
            return {"_local_file": out}
        except Exception as e:
            self._set_status("Upscale failed: %s" % str(e)[:60])
            logging.error("ffmpeg upscale error: %s", e)
            return None
    def _video_button_for(self, mode):
        """Return the Generate button widget that belongs to `mode`.

        Text-to-Video, Video-to-Video and Refine each own a distinct button
        (self.vgen / self.v2vgen / self.rgen). They previously shared the
        self.vgen attribute, so building the V2V tab clobbered the T2V
        reference and the Cancel/reset logic drove whichever button happened
        to be assigned last. Returns None when the tab has not been built.
        """
        name = {"t2v": "vgen", "v2v": "v2vgen", "refine": "rgen"}.get(mode, "vgen")
        btn = getattr(self, name, None)
        try:
            if btn is not None and btn.winfo_exists():
                return btn
        except Exception:
            pass
        return None

    def _start_video_gen(self, mode="t2v"):
        """Build + queue a MiniMax H3 video workflow (API format, proven valid).
        mode: 't2v' (Text to Video tab), 'v2v' (Video to Video tab),
              'refine' (Video Refine & Upscale tab)."""
        breadcrumb("start_video_gen", mode=mode)
        import time, random
        if getattr(self, '_generate_lock', False):
            # If the button is already "Cancel", treat a click as cancel
            btn = self._video_button_for(mode)
            if btn and str(btn.cget("text")).startswith("Cancel"):
                self._cancel_generate()
                return
            self._set_status("Video gen locked")
            return
        # Switch the active button to Cancel
        btn = self._video_button_for(mode)
        if btn:
            try:
                btn.configure(text="Cancel", fg_color="#CC3333", hover_color="#AA2222",
                              command=lambda: self._cancel_generate())
            except Exception:
                pass
        # VRAM guard: block if image models resident (mutual exclusion)
        thresh = self._get_vram_threshold_float()
        if self._vram_critical(thresh):
            self._set_status("VRAM critical (>%d%%) - close image gen before video" % int(thresh * 100))
            return
        self._last_generate = time.time()
        self._generate_lock = True
        self._gen_start_time = time.time()
        # Cleared here and set only when a job is successfully handed off to
        # _poll_history, so the finally block can tell "queued, poller owns the
        # buttons" from "failed, restore the buttons now".
        self._poll_handoff = False
        try:
            if mode == "t2v":
                self._set_status("Building H3 video workflow...")
                mode_key = "t2v" if self.video_mode_var.get() != "I2V (Image)" else "i2v"
                prompt = self.video_prompt.get("1.0", "end-1c").strip()
                # Aspect ratio drives w/h (research: AR is the primary shape control)
                w, h = VIDEO_ASPECT_RATIOS[self.video_ar_var.get()]
                dur = int(VIDEO_DURATIONS[self.video_dur_var.get()])
                attn = self.video_attn_var.get()
                ref_max = int(self.video_refmax_var.get())
                storyboard = self.video_storyboard_var.get()
                fl = self.video_fl_var.get()
                i2v_path = getattr(self, "video_i2v_path", None)
                camera = self.video_camera_var.get()
                enhance = self.video_enhance_var.get()
                loop = self.video_loop_var.get()
                batch = int(self.video_batch_var.get())
                # Batch: queue N seed variations (research: variations are standard)
                for b in range(max(1, batch)):
                    seed = random.randint(0, 2**63) if self.video_seed_lock.get() else int(self.video_seed_var.get() or 0)
                    steps = int(self.video_steps_var.get())
                    cfg = float(self.video_cfg_var.get())
                    sampler = self.video_sampler_var.get()
                    shift = float(self.video_shift_var.get())
                    denoise = float(self.video_denoise_var.get())
                    adaln = self.video_adaln_var.get()
                    spectrum = self.video_spectrum_var.get()
                    teacache = self.video_teacache_var.get()
                    blockswap = self.video_blockswap_var.get()
                    neg = self.video_neg.get("1.0", "end-1c").strip()
                    wf = self._build_h3_graph(mode_key, prompt, w, h, dur, seed, steps, cfg,
                                              sampler, shift, denoise, adaln, spectrum,
                                              teacache, blockswap, neg=neg, attention=attn,
                                              ref_max=ref_max, storyboard=storyboard, fl=fl,
                                              i2v_path=i2v_path, camera=camera,
                                              enhance=enhance, loop=loop)
                    payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored"}
                    r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
                    if r.status_code != 200:
                        try:
                            err_msg = r.json().get("error", {}).get("message", "HTTP %d" % r.status_code)
                        except Exception:
                            err_msg = "HTTP %d" % r.status_code
                        self._set_status("Video queue failed (batch %d): %s" % (b+1, str(err_msg)[:70]))
                        return
                    if b == 0:
                        self.last_prompt_id = r.json().get("prompt_id")
                        self._gen_mode = "video"
                        self._poll_attempts = 0
                        self._poll_handoff = True
                        self.root.after(200, self._poll_history)
                self._set_status("Queued %d H3 video job(s) (%dx%d, %ds)..." % (max(1, batch), w, h, dur))
                return
            elif mode == "v2v":
                self._set_status("Building H3 Video-to-Video workflow...")
                wf = self._video_v2v_build_and_queue()
                if wf is None:
                    self._set_status("Video-to-Video build failed")
                    return
                self._set_status("Queued Video-to-Video (H3 references)...")
                return  # B16 FIX: _video_v2v_build_and_queue already POSTed + released lock; NO fall-through
            elif mode == "refine":
                # Refine = local ffmpeg upscale (no server round-trip)
                result = self._video_refine_build_and_queue()
                if result and "_local_file" in result:
                    self._set_status("Upscale done -> " + os.path.basename(result["_local_file"]))
                return
            else:
                self._set_status("Unknown video mode")
                return
            payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored"}
            r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
            if r.status_code != 200:
                try:
                    err_msg = r.json().get("error", {}).get("message", "HTTP %d" % r.status_code)
                except Exception:
                    err_msg = "HTTP %d" % r.status_code
                self._set_status("Video queue failed: %s" % str(err_msg)[:80])
                return
            self.last_prompt_id = r.json().get("prompt_id")
            self._gen_mode = "video"
            self._poll_attempts = 0
            self._poll_handoff = True
            self.root.after(200, self._poll_history)
        except Exception as e:
            logging.error("Video gen error: %s", e)
            self._set_status("Video gen error: %s" % str(e)[:40])
        finally:
            self._generate_lock = False
            # B5: release VRAM after every video gen (mutual exclusion with
            # image gen). This single call replaces three identical duplicated
            # /free POSTs that accumulated here across earlier patches -- each
            # had a 5s timeout, so an unreachable backend stalled the UI for up
            # to 15s on every generation instead of 5s.
            try:
                requests.post(COMFYUI_URL + "/free",
                              json={"unload_models": True, "free_memory": True},
                              timeout=5)
            except Exception:
                pass
            # Restore the video buttons on EVERY exit path. Without this an
            # early return (queue failure, unknown mode, build failure) left
            # the tab's button reading "Cancel" even though nothing was
            # running, and clicking it tried to cancel a non-existent job.
            try:
                if not self._poll_pending():
                    self._reset_video_buttons()
            except Exception:
                pass

    def _poll_pending(self):
        """True when this invocation handed a queued job to _poll_history.

        Used to decide whether the video buttons may be reset immediately.
        A successful queue hands off to _poll_history, which owns the button
        state until the job finishes; a failed queue has no poller and must
        restore the buttons itself. Deliberately a per-invocation flag rather
        than an inspection of last_prompt_id, which survives from previous
        runs and would wrongly suppress the reset after a failed queue.
        """
        return bool(getattr(self, "_poll_handoff", False))

    def _has_tab(self, name):
        """True if `name` is currently a tab in self.tabview.

        Several builders are retained for legacy/tab surfaces that are no
        longer added to the tabview (Gallery and Settings now live in the
        main column). CTkTabview.tab(name) raises ValueError for an unknown
        name, so every such builder must check first. Prefers the documented
        public API and falls back to the private _name_list only if needed,
        so a CustomTkinter upgrade cannot turn this into a hard crash.
        """
        try:
            tv = getattr(self, "tabview", None)
            if tv is None:
                return False
            names = getattr(tv, "_name_list", None)
            if names is not None:
                return name in names
            tv.tab(name)
            return True
        except Exception:
            return False

    def _build_gallery_tab(self):
        """Build the Gallery tab - thumbnail grid of generated images.

        PRESERVED_LEGACY: the Gallery moved to the sidebar-driven main-column
        view (_build_gallery_in_main). This tab builder is retained so the
        legacy surface still works if a "Gallery" tab is ever re-added to the
        tabview, but calling it while no such tab exists raised
        ValueError: CTkTabview has no tab named 'Gallery'. Guard and no-op.
        """
        if not self._has_tab("Gallery"):
            logging.debug("_build_gallery_tab skipped — no 'Gallery' tab in tabview")
            return
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
        ctk.CTkLabel(header, text="Generated Media", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        refresh_btn = ctk.CTkButton(header, text="Refresh", width=80, height=24,
                                    command=self._refresh_gallery, fg_color=ACCENT2,
                                    hover_color=ACCENT2_HOVER, text_color="#FFFFFF")
        refresh_btn.grid(row=0, column=1, padx=10, pady=8, sticky="e")
        open_btn = ctk.CTkButton(header, text="Open Folder", width=90, height=24,
                                 command=lambda: _open_folder(OUTPUT_DIR), fg_color=BG_CARD_ALT,
                                 hover_color=BRAND_HOVER, text_color=TEXT)
        open_btn.grid(row=0, column=2, padx=(0, 10), pady=8, sticky="e")

        self._gallery_frame = ctk.CTkScrollableFrame(sf, fg_color=BG_CARD_ALT, corner_radius=8)
        self._gallery_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._gallery_frame.grid_columnconfigure(0, weight=1)
        enable_auto_hide_scrollbar(self._gallery_frame)
        self._refresh_gallery()

    def _refresh_gallery(self):
        """Populate gallery with thumbnails from OUTPUT_DIR.

        PRESERVED_LEGACY: this refreshes the legacy Gallery *tab* surface,
        whose _gallery_frame only exists once _build_gallery_tab has run.
        Post-generation code (_poll_history) and _delete_gallery_file call this
        unconditionally, which raised AttributeError: no attribute
        '_gallery_frame' and aborted the post-save path. Bail out cleanly when
        the legacy surface was never built; _refresh_gallery_main handles the
        active main-column gallery.
        """
        if not hasattr(self, "_gallery_frame") or not self._gallery_frame.winfo_exists():
            return
        for widget in self._gallery_frame.winfo_children():
            widget.destroy()
        try:
            if not os.path.isdir(OUTPUT_DIR):
                ctk.CTkLabel(self._gallery_frame, text="No generated media yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            images = [f for f in os.listdir(OUTPUT_DIR)
                      if f.lower().endswith((".png", ".jpg", ".jpeg", ".mp4", ".webm")) and not f.startswith("input")]
            images.sort(key=lambda x: _safe_mtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
            if not images:
                ctk.CTkLabel(self._gallery_frame, text="No generated media yet",
                             font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(pady=20)
                return
            for idx, fname in enumerate(images[:12]):
                fpath = os.path.join(OUTPUT_DIR, fname)
                is_video = fname.lower().endswith((".mp4", ".webm"))
                try:
                    if is_video:
                        # Use a placeholder for video thumbnails
                        lbl = ctk.CTkLabel(self._gallery_frame, text="▶ " + fname,
                                           fg_color=BG_CARD, corner_radius=6, width=180, height=140,
                                           font=ctk.CTkFont(size=9), text_color=TEXT_DIM)
                        lbl.grid(row=idx // 3, column=idx % 3, padx=6, pady=6, sticky="w")
                    else:
                        img = Image.open(fpath)
                        img.thumbnail((180, 140))
                        photo = ImageTk.PhotoImage(img)
                        lbl = ctk.CTkLabel(self._gallery_frame, image=photo, text="",
                                           fg_color=BG_CARD, corner_radius=6, width=180, height=140)
                        lbl.image = photo
                        lbl.grid(row=idx // 3, column=idx % 3, padx=6, pady=6, sticky="w")
                    lbl.bind("<Button-1>", lambda e, fp=fpath: os.startfile(fp))
                    lbl.bind("<Enter>", lambda e, p=fname: self._set_status(p))
                except Exception:
                    pass
            self._gallery_frame.update_idletasks()
        except Exception as e:
            self._set_status("Gallery error: %s" % e)

    def _build_settings_in_main(self):
        """Build the Settings view in the main right-column area."""
        if hasattr(self, "_settings_main") and self._settings_main:
            try:
                self._recursive_destroy(self._settings_main)
            except Exception:
                pass
        self._settings_main = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=10)
        self._settings_main.grid(row=0, column=1, rowspan=4, padx=16, pady=(8, 16), sticky="nsew")
        self._settings_main.grid_columnconfigure(0, weight=1)
        self._settings_main.grid_rowconfigure(0, weight=1)

        sf = ctk.CTkFrame(self._settings_main, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=12, pady=(8, 12), sticky="nsew")
        sf.grid_columnconfigure(0, weight=1)
        sf.grid_rowconfigure(20, weight=1)

        ctk.CTkLabel(sf, text="ComfyUIX Settings", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=(10, 12), sticky="w")

        r = self._build_shared_settings_fields(sf, 1)
        r = self._build_qol_settings(sf, r)

        ctk.CTkLabel(sf, text="Restart backend to apply changes.", font=ctk.CTkFont(size=9),
                     text_color=TEXT_MUTED).grid(row=r, column=0, padx=10, pady=(8, 0), sticky="w")

    def _build_debug_in_main(self):
        """Build the Debug Console view in the main right-column area."""
        if hasattr(self, "_debug_main") and self._debug_main:
            try:
                self._recursive_destroy(self._debug_main)
            except Exception:
                pass
        self._debug_main = ctk.CTkFrame(self.root, fg_color=BG_SIDEBAR, corner_radius=10)
        self._debug_main.grid(row=0, column=1, rowspan=4, padx=16, pady=(8, 16), sticky="nsew")
        self._debug_main.grid_columnconfigure(0, weight=1)
        self._debug_main.grid_rowconfigure(0, weight=1)

        sf = ctk.CTkFrame(self._debug_main, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=12, pady=(8, 12), sticky="nsew")
        sf.grid_columnconfigure(0, weight=1)
        sf.grid_rowconfigure(3, weight=4)
        sf.grid_rowconfigure(5, weight=1)
        sf.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(sf, text="ComfyUIX Diagnostics & Failure Intelligence Console",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).grid(
            row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        btn_row = ctk.CTkFrame(sf, fg_color="transparent")
        btn_row.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="ew")

        b_specs = [
            ("Refresh", lambda: self._debug_refresh(), BG_CARD_ALT, TEXT, 0, 0),
            ("Diagnose", lambda: self._debug_diagnose(), BRAND, "#FFFFFF", 0, 1),
            ("Build Debug Bundle", lambda: bundle_button_command(self), BRAND, "#FFFFFF", 0, 2),
            ("Save Report", lambda: diagnostics_button_command(self), BG_CARD_ALT, TEXT, 0, 3),
            ("Copy Report", lambda: self._debug_copy_report(), BG_CARD_ALT, TEXT, 1, 0),
            ("Open Folder", lambda: self._debug_open_folder(), BG_CARD_ALT, TEXT, 1, 1),
            ("View Latest Crash", lambda: self._debug_view_crash(0), BG_CARD_ALT, TEXT, 1, 2),
        ]
        for txt, cmd, bgc, txc, r, c in b_specs:
            b = ctk.CTkButton(btn_row, text=txt, height=30, fg_color=bgc, text_color=txc,
                              hover_color=BRAND_HOVER, corner_radius=6, command=cmd,
                              font=self.FONT_SMALL_BOLD)
            b.grid(row=r, column=c, padx=3, pady=3, sticky="ew")
        for c in range(4):
            btn_row.grid_columnconfigure(c, weight=1)

        # Live log viewer
        ctk.CTkLabel(sf, text="Live App Log (tail)", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=2, column=0, padx=12, pady=(4, 2), sticky="w")
        log_box = ctk.CTkTextbox(sf, font=ctk.CTkFont(family="Consolas", size=10),
                                 fg_color=("#F8FAFC", "#111114"), text_color=("#0F172A", "#C8C8D0"))
        log_box.grid(row=3, column=0, padx=12, pady=(0, 6), sticky="nsew")
        self._debug_log_box = log_box

        # Crashes viewer
        ctk.CTkLabel(sf, text="Recent Crashes", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=4, column=0, padx=12, pady=(4, 2), sticky="w")
        crash_box = ctk.CTkTextbox(sf, font=ctk.CTkFont(family="Consolas", size=10),
                                   fg_color=("#F8FAFC", "#111114"), text_color=("#0F172A", "#C8C8D0"))
        crash_box.grid(row=5, column=0, padx=12, pady=(0, 6), sticky="nsew")
        self._debug_crash_box = crash_box

        # State + breadcrumbs
        ctk.CTkLabel(sf, text="Current State & Breadcrumbs",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT).grid(
            row=6, column=0, padx=12, pady=(4, 2), sticky="w")
        state_box = ctk.CTkTextbox(sf, font=ctk.CTkFont(family="Consolas", size=10),
                                   fg_color=("#F8FAFC", "#111114"), text_color=("#0F172A", "#C8C8D0"))
        state_box.grid(row=7, column=0, padx=12, pady=(0, 10), sticky="nsew")
        self._debug_state_box = state_box

        # Immediately populate
        self._debug_refresh()
        # Auto-refresh every 3s while visible
        try:
            self.root.after(3000, self._debug_autorefresh)
        except Exception:
            pass

    def _debug_refresh(self):
        """Populate the Debug tab boxes from current diagnostics state."""
        try:
            from comfyui_desktop.diagnostics import (dump_report, _recent_breadcrumbs, DIAG_DIR)
            report = dump_report(self, log_tail_lines=200, include_gpu=True)
            # Log
            if hasattr(self, "_debug_log_box") and self._debug_log_box.winfo_exists():
                self._debug_log_box.delete("1.0", "end")
                lines = report.get("log_tail", [])
                self._debug_log_box.insert("end", "\n".join(lines[-200:]) + "\n")
            # Crashes
            if hasattr(self, "_debug_crash_box") and self._debug_crash_box.winfo_exists():
                self._debug_crash_box.delete("1.0", "end")
                crashes = report.get("recent_crashes", [])
                if not crashes:
                    self._debug_crash_box.insert("end", "No crashes recorded.\n")
                for c in crashes[:5]:
                    if isinstance(c, dict):
                        self._debug_crash_box.insert("end", "[%s] %s\n" % (c.get("timestamp", "?"), c.get("exception", "?")))
                        fixes = c.get("known_fixes", []) or []
                        for fix in fixes:
                            if isinstance(fix, dict):
                                self._debug_crash_box.insert("end", "   ↳ KNOWN FIX: %s\n      %s\n" % (fix.get("title", ""), fix.get("fix", "")))
                            elif isinstance(fix, str):
                                self._debug_crash_box.insert("end", "   ↳ KNOWN FIX: %s\n" % fix)
                        self._debug_crash_box.insert("end", "   dump: %s\n\n" % c.get("dump_path", "?"))
            # State + breadcrumbs
            if hasattr(self, "_debug_state_box") and self._debug_state_box.winfo_exists():
                self._debug_state_box.delete("1.0", "end")
                st = report.get("app", {})
                self._debug_state_box.insert("end", "App state:\n")
                for k, v in st.items():
                    self._debug_state_box.insert("end", "  %s = %s\n" % (k, v))
                self._debug_state_box.insert("end", "\nLast breadcrumbs (what the app was doing):\n")
                for b in _recent_breadcrumbs(15):
                    d = b.get("data", {})
                    ds = " ".join("%s=%s" % (k, v) for k, v in d.items())
                    self._debug_state_box.insert("end", "  [%s] %s %s\n" % (b.get("t", "?"), b.get("action", "?"), ds))
        except Exception:
            pass

    def _debug_open_folder(self):
        """Open the diagnostics folder in Explorer."""
        try:
            from comfyui_desktop.diagnostics import DIAG_DIR
            import os
            if os.path.exists(DIAG_DIR):
                os.startfile(DIAG_DIR)
        except Exception:
            pass

    def _debug_diagnose(self):
        """Run a built-in health self-test and write the result to the log.

        Surfaces the most common failure causes (server down, VRAM, missing models)
        in one place an AI can read from app.log / the Debug tab."""
        try:
            import requests, time
            from comfyui_desktop.diagnostics import breadcrumb, DIAG_DIR
            breadcrumb("debug_diagnose")
            checks = []
            # 1. ComfyUI server reachable?
            t0 = time.time()
            try:
                r = requests.get(COMFYUI_URL + "/system_stats", timeout=5)
                ok = r.status_code == 200
                checks.append(("ComfyUI server :8188", ok, "%dms" % int((time.time()-t0)*1000) if ok else "no response"))
            except Exception as e:
                checks.append(("ComfyUI server :8188", False, str(e)[:80]))
            # 2. GPU / VRAM
            try:
                import subprocess
                r2 = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free",
                                     "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                checks.append(("GPU VRAM", r2.returncode == 0, r2.stdout.strip().replace("\n"," | ") if r2.returncode==0 else "nvidia-smi unavailable"))
            except Exception as e:
                checks.append(("GPU VRAM", False, str(e)[:80]))
            # 3. Output dir writable?
            try:
                import os
                test = os.path.join(OUTPUT_DIR, ".writetest")
                with open(test, "w") as f:
                    f.write("ok")
                os.remove(test)
                checks.append(("Output dir writable", True, OUTPUT_DIR))
            except Exception as e:
                checks.append(("Output dir writable", False, str(e)[:80]))
            # 4. Models present?
            try:
                import os, glob
                ckpts = glob.glob(os.path.join(CKPT_DIR, "*.safetensors")) + glob.glob(os.path.join(CKPT_DIR, "*.ckpt"))
                checks.append(("Checkpoints present", len(ckpts) > 0, "%d found" % len(ckpts)))
            except Exception as e:
                checks.append(("Checkpoints present", False, str(e)[:80]))

            report_lines = ["=== SELF-DIAGNOSE %s ===" % time.strftime("%Y-%m-%d %H:%M:%S")]
            all_ok = True
            for name, ok, detail in checks:
                report_lines.append("  [%s] %s — %s" % ("PASS" if ok else "FAIL", name, detail))
                all_ok = all_ok and ok
            report_lines.append("OVERALL: %s" % ("HEALTHY" if all_ok else "ISSUES FOUND"))
            msg = "\n".join(report_lines)
            logging.getLogger("comfyui_diag").info(msg)
            self._set_status("Diagnose: %s" % ("HEALTHY" if all_ok else "ISSUES FOUND — see Debug tab"))
            self._debug_refresh()
        except Exception:
            pass

    def _debug_copy_report(self):
        """Copy the full JSON report to the clipboard."""
        try:
            from comfyui_desktop.diagnostics import dump_report
            report = dump_report(self, log_tail_lines=300, include_gpu=True)
            import json
            txt = json.dumps(report, indent=2, ensure_ascii=False)
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self._set_status("Debug report copied to clipboard")
        except Exception:
            pass

    def _debug_view_crash(self, index):
        """Open a crash JSON dump in the default viewer (Notepad)."""
        try:
            from comfyui_desktop.diagnostics import DIAG_DIR
            import glob, os, subprocess
            files = sorted(glob.glob(os.path.join(DIAG_DIR, "crash_*.json")), reverse=True)
            if files and 0 <= index < len(files):
                os.startfile(files[index])
        except Exception:
            pass

    def _debug_autorefresh(self):
        """Refresh the Debug tab only if it's the visible tab (cheap)."""
        try:
            if getattr(self, "_running", False) and hasattr(self, "tabview") and self.tabview:
                if str(self.tabview.get()) == "Debug":
                    self._debug_refresh()
        except Exception:
            pass
        try:
            self.root.after(3000, self._debug_autorefresh)
        except Exception:
            pass

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
                # PRESERVED_LEGACY: replaced dead if/elif chain (compared against
                # never-assigned self.*_tab attrs) and incomplete tab_map with a
                # single comprehensive lookup covering all 8 tab surfaces.
                tab_map = {
                    "Text to Image": "txt2img", "txt2img": "txt2img",
                    "Image to Image": "img2img", "img2img": "img2img",
                    "Upscale": "upscale", "upscale": "upscale",
                    "Text to Video": "video", "Video to Video": "video",
                    "Video Refine & Upscale": "video",
                    "Video": "video", "video": "video",
                    "Debug": "debug",
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
            # PHASE 2 FIX: reap a LEFTOVER (orphan) :8188 server from a previous
            # EXE run BEFORE spawning a new one. Without this, a prior run that
            # didn't fully close leaves a server on :8188 -> the next launch
            # collides and lags. We only ever kill an orphan we don't own.
            try:
                import orphan_reap
                orphan_reap.reap_orphan_8188(my_pid=getattr(self, "backend", None)
                                             and self.backend.pid)
            except Exception as _e:
                logging.warning("orphan reap skipped: %s", _e)
            # Kill only a previously-tracked backend instance (avoid nuking
            # unrelated python_embeded processes the user may be running).
            self._terminate_backend()
            gpu_mode = self.gpu_mode_str.get()
            gpu_flag = []
            if "--lowvram" in gpu_mode:
                gpu_flag = ["--lowvram"]
            elif "--medvram" in gpu_mode:
                gpu_flag = ["--medvram"]
            elif "--highvram" in gpu_mode:
                gpu_flag = ["--highvram"]
            elif "--cpu" in gpu_mode:
                gpu_flag = ["--cpu"]

            custom_args = self.launch_args_str.get().split()
            args = [PYTHON_PATH, "-u", os.path.join(COMFYUI_DIR, MAIN_PY)] + gpu_flag + custom_args

            log_fh = open(SERVER_LOG_FILE, "w", encoding="utf-8", errors="replace")
            self.backend = subprocess.Popen(
                args, cwd=COMFYUI_DIR,
                stdout=log_fh, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self._set_status("Loading backend...")
            for i in range(150):
                if not self._running:
                    return
                time.sleep(1)
                try:
                    r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
                    if r.status_code == 200:
                                        self._set_status("Server online")
                                        # Write sentinel PID so orphan_reap knows this is our server
                                        try:
                                            import orphan_reap
                                            orphan_reap.write_sentinel(self.backend.pid)
                                        except Exception as _e:
                                            logging.warning("sentinel write skipped: %s", _e)
                                        if self._running:
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

    def _terminate_backend(self):
        if getattr(self, "backend", None) and self.backend.poll() is None:
            try:
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.run(["taskkill", "/PID", str(self.backend.pid), "/T", "/F"],
                               capture_output=True, timeout=5, creationflags=flags)
            except Exception:
                pass
            try:
                if self.backend.poll() is None:
                    self.backend.kill()
            except Exception:
                pass

    def _restart_server(self):
        self._terminate_backend()
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
                thresh = self._get_vram_threshold_float()
                # Backend is reachable again — clear the auto-restart toast latch.
                if getattr(self, "_auto_restart_toast_shown", False):
                    self._auto_restart_toast_shown = False
                # Live VRAM chip (QoL). Thread-safe via root.after.
                if getattr(self, "qol_vram_readout", tk.StringVar(value="1")).get() == "1" and getattr(self, "vram_chip", None) is not None:
                    try:
                        self.root.after(0, lambda p=pct: self.vram_chip.configure(text="VRAM %d%%" % int(p * 100)))
                    except Exception:
                        pass
                # Don't spam "VRAM critical" while a generation is actively
                # running — VRAM is naturally ~90%+ during a gen, and overwriting
                # the "Generating..." status with "VRAM critical" makes the UI
                # flicker and hides real progress. The poll loop owns the status
                # bar during a gen.
                generating = getattr(self, "_generate_lock", False)
                if pct > thresh and not generating:
                    self._set_status("VRAM critical (%d%%) - wait for VRAM to clear" % int(pct * 100))
                    last_warned = pct
                elif pct > (thresh - 0.10) and last_warned == 0 and not generating:
                    self._set_status("Server online (VRAM %d%% used)" % int(pct * 100))
                    last_warned = pct
                elif pct < (thresh - 0.15) and last_warned > 0:
                    last_warned = 0
            except Exception:
                # Backend unreachable — offer a one-click restart (QoL, gated).
                if getattr(self, "qol_auto_restart", tk.StringVar(value="1")).get() == "1":
                    if not getattr(self, "_auto_restart_toast_shown", False):
                        self._auto_restart_toast_shown = True
                        try:
                            self.root.after(0, lambda: self._show_toast(
                                "Backend Offline", "The ComfyUI backend is not responding. Click Restart to bring it back up.", error=True))
                        except Exception:
                            pass
                time.sleep(1)

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
                        # PRESERVED_LEGACY: Clean up already-processed error dumps to prevent unbounded disk growth in Logs/
                        if data.get("hermes_processed"):
                            try:
                                os.remove(fp)
                            except OSError:
                                pass
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
        """Build the ComfyUI workflow dict for the given mode (txt2img/img2img/upscale)."""
        if not mode or mode not in ("txt2img", "img2img", "upscale"):
            mode = "txt2img"
        m = self.vars.get(mode, self.vars["txt2img"])
        # Safe numeric parsing: clamp to valid ComfyUI ranges so a typo / empty
        # field can NEVER raise ValueError and leave the Generate button stuck.
        w = _safe_int(m["width"].get(), default=1024, lo=64, hi=4096)
        h = _safe_int(m["height"].get(), default=1024, lo=64, hi=4096)
        steps = _safe_int(m["steps"].get(), default=30, lo=1, hi=150)
        cfg = _safe_float(m["cfg"].get(), default=7.0, lo=0.0, hi=30.0)
        seed = _safe_int(m["seed"].get(), default=0, lo=0, hi=2**32 - 1)
        if seed == 0:
            seed = random.randint(1, 2**32 - 1)
        batch = _safe_int(m["batch"].get(), default=1, lo=1, hi=8)
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

        model_strength = _safe_float(m["model_strength"].get(), default=1.0, lo=0.0, hi=2.0) if "model_strength" in m else 1.0
        clip_strength = _safe_float(m["clip_strength"].get(), default=1.0, lo=0.0, hi=2.0) if "clip_strength" in m else 1.0

        if mode == "txt2img":
            wf = {
                "LastNode": {"class_type": "CheckpointLoaderSimple",
                             "inputs": {"ckpt_name": ckpt}},
                "EmptyLatent": {"class_type": "EmptyLatentImage",
                                "inputs": {"width": w, "height": h, "batch_size": batch}},
                "KSampler": {"class_type": "KSampler",
                             "inputs": {"sampler_name": m["sampler"].get(),
                                        "scheduler": m["scheduler"].get(),
                                        "steps": steps, "cfg": cfg, "seed": seed, "denoise": 1.0,
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
                             "inputs": {"ckpt_name": ckpt}},
                "LoadImage": {"class_type": "LoadImage",
                              "inputs": {"image": "img2img_in.png"}},
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
                              "inputs": {"image": "upscale_in.png"}},
                "ModelLoader": {"class_type": "UpscaleModelLoader",
                                "inputs": {"model_name": m["model"].get()}},
                "Upscale": {"class_type": "ImageUpscaleWithModel",
                            "inputs": {"upscale_model": ["ModelLoader", 0],
                                       "image": ["LoadImage", 0]}},
                "SaveImage": {"class_type": "SaveImage",
                              "inputs": {"images": ["Upscale", 0],
                                         "filename_prefix": "ComfyUI_Uncensored",
                                         "format": "Game Texture (TGA)" if m["format"].get() == "Game Texture (TGA)" else "PNG"}},
            }
            return wf, ckpt
        else:
            return {}, ckpt

    def _backend_online(self, timeout=4):
        """QoL (2026-08-09): lightweight liveness probe so Generate can tell the
        user *why* nothing happened when ComfyUI isn't running, instead of a
        cryptic connection error. Returns True/False."""
        try:
            r = requests.get(COMFYUI_URL + "/system_stats", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def _ensure_model_loaded(self, model_name):
        """Symlink the selected model into models/checkpoints/ on-demand.
        FIX: do NOT create a symlink if the source file is missing in
        models_archive/ — that produces a broken link ComfyUI refuses to load
        (FileNotFoundError: Model ... not found). Instead report missing + return."""
        if not model_name:
            return
        target = os.path.join(CKPT_DIR, model_name)
        source = os.path.join(ARCHIVE_DIR, model_name)
        # Remove any pre-existing broken symlink so it doesn't pollute checkpoints
        if os.path.islink(target) and not os.path.exists(target):
            try:
                os.remove(target)
            except Exception:
                pass
        if not os.path.exists(source):
            self._set_status("Model file missing: %s" % model_name)
            return
        if not os.path.exists(target):
            try:
                os.makedirs(CKPT_DIR, exist_ok=True)
                self._set_status("Loading model: %s" % model_name[:24])
                os.symlink(source, target)
                self._set_status("Model ready: %s" % model_name[:20])
            except FileExistsError:
                pass
            except Exception as e:
                self._set_status("Model link error: %s" % str(e)[:30])

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

    def _on_ctrl_e(self):
        """Tab-aware Ctrl+E / Ctrl+Enter / Shift+Enter.

        Routes to the correct generator based on the active tab so the
        '(Ctrl+E)' label on every Generate button is actually accurate
        (previously the global binding only ever fired image generation and
        did nothing on the Video tabs)."""
        tab = getattr(self, "current_tab", "txt2img")
        if tab == "video":
            # Map the active video sub-tab to its generator mode.
            try:
                vt = getattr(self, "video_mode_var", None)
                if vt is not None and "I2V" in str(vt.get()):
                    self._start_video_gen("v2v")
                else:
                    self._start_video_gen("t2v")
            except Exception:
                self._start_video_gen("t2v")
        else:
            self._start_generate()

    def _neg_for_mode(self, mode):
        """Return the current negative-prompt text for a given tab."""
        try:
            if mode == "img2img":
                return self.img2img_neg_entry.get("1.0", "end-1c").strip()
            return self.neg_entry.get("1.0", "end-1c").strip()
        except Exception:
            return ""

    def _start_generate(self, mode=None):
        breadcrumb("start_generate", mode=mode or getattr(self, "current_tab", "?"))
        import time
        logging.info("Generate button clicked")
        if mode and mode not in ("txt2img", "img2img", "upscale"):
            self._set_status("Error: unknown mode '%s'" % mode)
            return
        # Active VRAM guard: never OOM the host — defer when VRAM is critical.
        thresh = self._get_vram_threshold_float()
        if self._vram_critical(thresh):
            self._set_status("VRAM critical (>%d%%) - wait for VRAM to clear before generating" % int(thresh * 100))
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
        # QoL: capture the prompt/negative this run used so the "↺ Last Prompt"
        # button can restore it (and persist across restarts via restore-session).
        try:
            self.last_prompt = {"prompt": self._prompt_for_mode(target_mode),
                                "negative": self._neg_for_mode(target_mode)}
        except Exception:
            pass
        try:
            if self.qol_restore_session.get() == "1":
                self.config_manager.settings["last_session_%s" % target_mode] = self.last_prompt
                self.config_manager.save()
        except Exception:
            pass
        try:
            logging.info("Starting generate workflow")
            if hasattr(self, '_generate') and callable(getattr(self, '_generate')):
                self._generate(target_mode)
                return
            if hasattr(self, 'gen_btn') and self.gen_btn:
                self.gen_btn.configure(state="disabled")
            self._set_status("Building workflow...")
            # QoL (2026-08-09): pre-flight backend probe — if ComfyUI isn't
            # running, say so plainly instead of surfacing a raw connection error.
            if not self._backend_online():
                self._set_status("⚠ Backend offline — start ComfyUI (port 8188) then retry")
                self._show_toast("ComfyUI Offline", "Start ComfyUI, then click Generate again.", error=True)
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
                return
            try:
                wf, ckpt = self._build_workflow(target_mode)
                self._ensure_model_loaded(ckpt)
                self._set_status("Generating...")
                # ComfyUI 0.29 /prompt expects the workflow as a JSON OBJECT (dict),
                # not a string. Sending a string causes HTTP 500 (AttributeError in
                # node_replace_manager). Source: official basic_api_example.py.
                payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored"}
                r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
                if r.status_code != 200:
                    # Surface the REAL ComfyUI validation error so the user knows
                    # why the queue failed (instead of a generic HTTP code).
                    try:
                        err_msg = r.json().get("error", {}).get("message", "HTTP %d" % r.status_code)
                    except Exception:
                        err_msg = "HTTP %d" % r.status_code
                    self._set_status("Queue failed: %s" % err_msg[:60])
                    if hasattr(self, 'gen_btn') and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self.last_prompt_id = r.json().get("prompt_id")
                self._gen_mode = self.current_tab
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Cancel", command=self._cancel_generate)
                self._poll_attempts = 0
                self.root.after(200, self._poll_history)
            except requests.exceptions.ConnectionError:
                self._set_status("⚠ Backend offline — start ComfyUI (port 8188) then retry")
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
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
            # Release VRAM after image gen (mutual exclusion with video gen)
            try:
                requests.post(COMFYUI_URL + "/free", json={"unload_models": True, "free_memory": True}, timeout=5)
            except Exception:
                pass

    def _switch_tab_by_index(self, idx):
        """Switch to the creation tab at the given index (Ctrl+1..6 shortcut)."""
        try:
            tabs = ["Text to Image", "Image to Image", "Upscale", "Text to Video", "Video to Video", "Video Refine & Upscale"]
            if 0 <= idx < len(tabs):
                self._show_view("generate")
                self.tabview.set(tabs[idx])
        except Exception:
            pass

    def _fmt_elapsed(self, seconds):
        """Format elapsed seconds as [MM:SS] or [H:MM:SS]."""
        try:
            import math
            s = max(0, int(seconds)) if seconds is not None and not math.isnan(float(seconds)) else 0
        except Exception:
            s = 0
        h, m = divmod(s, 3600)
        m, s = divmod(m, 60)
        if h:
            return "%d:%02d:%02d" % (h, m, s)
        return "%02d:%02d" % (m, s)

    def _reset_video_buttons(self):
        """Restore video gen buttons to their normal Generate state.

        Resets all three video buttons independently. Previously only
        self.vgen and self.rgen were handled and the V2V button shared the
        vgen attribute, so after a V2V run the Text-to-Video button could be
        left showing "Cancel" with no way back to Generate.
        """
        for name, label, mode in (
            ("vgen", "Generate Video  (Ctrl+E)", "t2v"),
            ("v2vgen", "Generate Video to Video  (Ctrl+E)", "v2v"),
            ("rgen", "Refine & Upscale  (Ctrl+E)", "refine"),
        ):
            try:
                btn = getattr(self, name, None)
                if btn is not None and btn.winfo_exists():
                    btn.configure(text=label, fg_color=ACCENT2,
                                  hover_color=ACCENT2_HOVER,
                                  command=lambda m=mode: self._start_video_gen(m))
            except Exception:
                pass

    def _gallery_context_menu(self, event, fpath, fname):
        """Show right-click menu for gallery thumbnails."""
        try:
            menu = tk.Menu(self.root, tearoff=0, bg="#2a2a2a", fg="#ffffff",
                          activebackground="#4a4a4a", activeforeground="#ffffff")
            menu.add_command(label="Open in Viewer", command=lambda: os.startfile(fpath))
            menu.add_command(label="Copy Path", command=lambda: self.root.clipboard_append(os.path.abspath(fpath)))
            menu.add_command(label="Open Folder", command=lambda: os.startfile(os.path.dirname(os.path.abspath(fpath))))
            menu.add_separator()
            menu.add_command(label="Copy Image", command=lambda: self._copy_image_to_clipboard(fpath))
            menu.add_separator()
            menu.add_command(label="Delete File", command=lambda: self._delete_gallery_file(fpath))
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    def _copy_image_to_clipboard(self, fpath):
        """Copy an image file to the system clipboard."""
        try:
            from PIL import Image
            from io import BytesIO
            import win32clipboard
            img = Image.open(fpath)
            output = BytesIO()
            img.convert("RGB").save(output, format="BMP")
            data = output.getvalue()[14:]  # Strip BMP header
            output.close()
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            self._set_status("Image copied to clipboard")
        except Exception:
            self._set_status("Could not copy image (try Copy Path instead)")

    def _delete_gallery_file(self, fpath):
        """Delete a file from the gallery after confirmation."""
        try:
            import tkinter.messagebox as mb
            if mb.askyesno("Delete File", "Permanently delete this file?", parent=self.root):
                os.remove(fpath)
                self._refresh_gallery_main()
                self._refresh_gallery()
                self._set_status("Deleted: %s" % os.path.basename(fpath))
        except Exception:
            pass

    def _play_complete_sound(self):
        """Play a subtle completion beep (Windows only, no deps)."""
        try:
            import winsound
            winsound.Beep(880, 150)  # A5, 150ms
        except Exception:
            pass

    def _show_toast(self, title, message, error=False):
        """Show a transient toast notification (top-right of window)."""
        try:
            import tkinter as tk
            toast = ctk.CTkToplevel(self.root)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(fg_color="#CC3333" if error else BG_CARD)
            # Position top-right
            self.root.update_idletasks()
            x = self.root.winfo_rootx() + self.root.winfo_width() - 340
            y = self.root.winfo_rooty() + 8
            toast.geometry("+%d+%d" % (x, y))
            ctk.CTkLabel(toast, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#FFFFFF" if error else TEXT).pack(padx=14, pady=(10, 2))
            ctk.CTkLabel(toast, text=message, font=ctk.CTkFont(size=10),
                         text_color="#FFE0E0" if error else TEXT_MUTED,
                         wraplength=300, justify="left").pack(padx=14, pady=(0, 10))
            toast.after(4000, toast.destroy)
            toasts = [t for t in getattr(self, "_toasts", []) if hasattr(t, "winfo_exists") and t.winfo_exists()]
            toasts.append(toast)
            if len(toasts) > 5:
                oldest = toasts.pop(0)
                try:
                    oldest.destroy()
                except Exception:
                    pass
            self._toasts = toasts
        except Exception:
            pass

    def _clear_prompt(self):
        """Clear active prompt and negative prompt text boxes."""
        try:
            for tab in ("txt2img", "img2img", "upscale", "txt2video", "vid2vid", "refine"):
                attr = getattr(self, "%s_prompt" % tab, None)
                if attr is not None:
                    attr.delete("1.0", "end")
            if hasattr(self, "n_prompt") and self.n_prompt:
                self.n_prompt.delete("1.0", "end")
            self._set_status("Prompt cleared")
        except Exception:
            pass

    def _copy_prompt(self):
        """Copy active prompt text to clipboard."""
        try:
            for tab in ("txt2img", "img2img", "upscale"):
                attr = getattr(self, "%s_prompt" % tab, None)
                if attr is not None:
                    txt = attr.get("1.0", "end-1c").strip()
                    if txt:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(txt)
                        self._set_status("Prompt copied to clipboard")
                        self._show_toast("Prompt Copied", "Active prompt text copied to clipboard")
                        return
            self._set_status("No prompt text to copy")
        except Exception:
            pass

    # --- QoL: prompt-history recall (gated by qol_prompt_history) ---
    def _refresh_history_menu(self):
        """Rebuild the History dropdown(s) from self.history (most-recent first, last 20)."""
        try:
            items = []
            for h in reversed(self.history[-20:]):
                p = (h.get("prompt") or "").strip().replace("\n", " ")
                if not p:
                    continue
                label = p if len(p) <= 38 else p[:35] + "..."
                if label not in items:
                    items.append(label)
            if not items:
                items = ["History"]
            for menu, var in ((getattr(self, "img_hist_menu", None), getattr(self, "img_hist_var", None)),
                              (getattr(self, "img2img_hist_menu", None), getattr(self, "img2img_hist_var", None)),
                              (getattr(self, "video_hist_menu", None), getattr(self, "video_hist_var", None))):
                if menu is None or not menu.winfo_exists():
                    continue
                if var.get() not in items:
                    var.set("History")
                menu.configure(values=items)
        except Exception:
            pass

    def _restore_session_on_start(self):
        """If qol_restore_session is ON, reload the last prompt/negative per tab."""
        try:
            if self.qol_restore_session.get() != "1":
                return
            for mode, pentry, nentry in (
                ("txt2img", getattr(self, "prompt_entry", None), getattr(self, "neg_entry", None)),
                ("img2img", getattr(self, "img2img_prompt_entry", None), getattr(self, "img2img_neg_entry", None)),
            ):
                saved = self.config_manager.settings.get("last_session_%s" % mode)
                if not saved or not isinstance(saved, dict):
                    continue
                p = (saved.get("prompt") or "").strip()
                n = (saved.get("negative") or "").strip()
                if p and pentry is not None and pentry.winfo_exists():
                    current = pentry.get("1.0", "end-1c").strip()
                    # Only overwrite if the field still holds the default placeholder.
                    if current and "photorealistic portrait" not in current:
                        continue
                    pentry.delete("1.0", "end")
                    pentry.insert("1.0", p)
                if n and nentry is not None and nentry.winfo_exists():
                    nentry.delete("1.0", "end")
                    nentry.insert("1.0", n)
                self.last_prompt = {"prompt": p, "negative": n}
        except Exception:
            pass

    def _restore_last_prompt(self, tab):
        """Restore the most recent prompt+negative (from previous session or last gen)."""
        try:
            if self.qol_prompt_history.get() != "1":
                return
            # QoL (2026-08-09): route to the ACTIVE tab's real entries. The old
            # getattr(self, "%s_prompt" % tab) lookup pointed at attributes that
            # never existed for image tabs, so the button did nothing.
            if tab == "img2img" and hasattr(self, "img2img_prompt_entry"):
                target = self.img2img_prompt_entry
                neg = self.img2img_neg_entry
            elif tab == "upscale" and hasattr(self, "upscale_prompt_entry"):
                target = self.upscale_prompt_entry
                neg = getattr(self, "upscale_neg_entry", None)
            elif tab == "video" and hasattr(self, "video_prompt"):
                target = self.video_prompt
                neg = getattr(self, "video_neg", None)
            elif hasattr(self, "prompt_entry"):
                target = self.prompt_entry
                neg = self.neg_entry
            else:
                target = None
                neg = None
            if target is None:
                return
            prev = getattr(self, "last_prompt", None)
            if not prev:
                # fall back to most recent saved history entry
                if self.history:
                    prev = {"prompt": self.history[-1].get("prompt", ""),
                            "negative": ""}
            if not prev:
                self._set_status("No previous prompt to restore")
                return
            target.delete("1.0", "end")
            target.insert("1.0", prev.get("prompt", ""))
            if neg is not None and prev.get("negative"):
                neg.delete("1.0", "end")
                neg.insert("1.0", prev.get("negative", ""))
            self._set_status("Restored last prompt")
        except Exception:
            pass

    def _apply_history_prompt(self, label, tab):
        """Apply a selected history entry's full prompt to the active tab."""
        try:
            if label in ("", "History"):
                return
            target = getattr(self, "%s_prompt" % tab, None)
            if target is None:
                return
            for h in reversed(self.history):
                p = (h.get("prompt") or "").replace("\n", " ").strip()
                if p[:35] == label[:35] or p == label:
                    target.delete("1.0", "end")
                    target.insert("1.0", h.get("prompt", ""))
                    neg = getattr(self, "%s_neg" % tab, None)
                    if neg is not None and h.get("negative"):
                        neg.delete("1.0", "end")
                        neg.insert("1.0", h.get("negative", ""))
                    self._set_status("Loaded prompt from history")
                    return
        except Exception:
            pass

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
        self._reset_video_buttons()
        self._generate_lock = False
        self._gen_start_time = None
        self._poll_started_at = None  # QOL: track first running-poll timestamp for ETA

    def _poll_history(self):
        """FIX: poll ComfyUI history with retries until done, error, or timeout.
        breadcrumb("poll_history", pid=self.last_prompt_id)
        Timeout raised to 600 attempts x 200ms = 120s. RTX 2070S (8GB) needs
        40-60s for a 768x768/30-step gen; the old 150-attempt (30s) cap caused
        'Polling timed out' and the button stayed stuck / image never displayed.
        Verified: live gen on this GPU completed at ~45s."""
        if not self._running:
            return
        if self._poll_attempts > 600:
            self._set_status("Polling timed out")
            if hasattr(self, 'gen_btn') and self.gen_btn and self.gen_btn.winfo_exists():
                self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
            # Release the generation lock and restore the video buttons too.
            # Previously only gen_btn was reset here, so a timeout left
            # _generate_lock stuck True -- every later Generate click hit the
            # "locked" guard and returned silently, and the video tabs kept
            # showing "Cancel". The app appeared dead until restart.
            self._reset_video_buttons()
            self._generate_lock = False
            self._gen_start_time = None
            self._poll_started_at = None  # QOL: track first running-poll timestamp for ETA
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
                            # ComfyUI 0.29: the "type":"output" marker lives on each
                            # image dict INSIDE node_out["images"], NOT on the node itself
                            # (node_out.get("type") is None). Iterate the images.
                            for img_data in node_out.get("images", []):
                                if img_data.get("type") == "output":
                                    # Video outputs (.mp4) go through _show_video; images via _show_image
                                    if str(img_data.get("filename", "")).lower().endswith(".mp4"):
                                        self._show_video(img_data)
                                    else:
                                        self._show_image(img_data)
                            # SaveVideo node emits a "videos" list (H3 video output)
                            for vid_data in node_out.get("videos", []):
                                if vid_data.get("type") == "output":
                                    self._show_video(vid_data)
                        # QOL: clear the started-time marker on completion
                        self._poll_started_at = None
                        return
                    elif status.get("error"):
                        err_msg = status.get("error", {}).get("message", "") if isinstance(status.get("error"), dict) else str(status.get("error", ""))
                        breadcrumb("gen_error", msg=err_msg[:120])
                        if "Spectrum" in err_msg or "spectrum" in err_msg.lower():
                            self._set_status("Spectrum error — retry without Spectrum (spectrum=False)")
                        else:
                            self._set_status("Generation error: %s" % err_msg[:60])
                            self._show_toast("Generation Error", err_msg[:120], error=True)
                        if hasattr(self, 'gen_btn') and self.gen_btn and self.gen_btn.winfo_exists():
                            self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
                        self._reset_video_buttons()
                        # BUGFIX: reset generation timing state so stale elapsed
                        # time doesn't continue to show after an error.
                        self._generate_lock = False
                        self._gen_start_time = None
                        self._poll_started_at = None
                        return
                    # QOL: update ETA while job is still running
                    self._update_eta(status, item_id, status.get("exec_info"))
        except Exception:
            pass
        if self._running:
            self.root.after(500, self._poll_history)

    def _update_eta(self, status, item_id, exec_info):
        """QOL: Display an estimated time remaining while a job is running.

        Uses ComfyUI's exec_info (which reports node progress as 0.0-1.0)
        when available. Falls back to a linear estimate based on when
        we first saw the job running and how many steps were configured.
        """
        try:
            if not status.get("running") and not status.get("executing"):
                # First time we see this job running — record the timestamp
                if getattr(self, "_poll_started_at", None) is None:
                    self._poll_started_at = time.time()
                return

            # Job is running — try to compute an ETA
            started = getattr(self, "_poll_started_at", None)
            if started is None:
                started = self._gen_start_time or time.time()
                self._poll_started_at = started

            elapsed = time.time() - started

            # Try ComfyUI's built-in progress reporting first
            progress = 0.0
            if exec_info:
                node_progress = exec_info.get("progress", {})
                if node_progress:
                    # progress is a dict of node_id -> float (0..1)
                    vals = [v for v in node_progress.values() if isinstance(v, (int, float))]
                    if vals:
                        progress = sum(vals) / len(vals)

            if progress > 0.01:
                eta = elapsed * (1.0 / progress - 1.0)
                if eta > 2:
                    self._set_status("Generating… ETA %s" % self._fmt_elapsed(eta))
                else:
                    self._set_status("Generating… finalizing")
            else:
                # Fallback: just show it's running with elapsed time
                if elapsed > 5:
                    self._set_status("Generating… %s elapsed" % self._fmt_elapsed(elapsed))
        except Exception:
            pass

    def _show_image(self, img_meta):
        mode = getattr(self, "_gen_mode", self.current_tab)
        self._play_complete_sound()
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
            tmp_path = out_path + ".tmp"
            with open(tmp_path, "wb") as fh:
                fh.write(r.content)
            os.replace(tmp_path, out_path)
            self._add_thumb(out_path, mode, only_preview=False)
            self._reload_recent_preview()
            fmt = self.vars.get(mode, {}).get("format")
            fmt_val = fmt.get() if fmt else "PNG"
            if fmt_val == "Game Texture (TGA)":
                self._convert_to_game_texture(out_path)
            self._save_history(mode, fn)
            if self.current_tab == "gallery":
                self._refresh_gallery()
            # QOL: auto-copy output path to clipboard when enabled
            if self.qol_copy_path.get() == "1" and self.root and self.root.winfo_exists():
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(out_path)
                    self._set_status("Done — path copied to clipboard")
                except Exception:
                    self._set_status("Done")
            else:
                self._set_status("Done")
            # Re-enable the Generate button after a successful generation
            if hasattr(self, "gen_btn") and self.gen_btn.winfo_exists():
                self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
            self._generate_lock = False
            self._gen_start_time = None
            self._poll_started_at = None  # QOL: track first running-poll timestamp for ETA
            # Refresh the main-column gallery grid so the new image appears immediately
            if hasattr(self, "_refresh_gallery_main"):
                self._refresh_gallery_main()
            self._show_toast("Generation Complete", f"Saved {fn[:25]}")
        except Exception as e:
            self._set_status("Show image error: %s" % str(e)[:30])

    def _show_video(self, vid_meta):
        self._play_complete_sound()
        """Download + save a generated H3 video (MP4) to OUTPUT_DIR and notify."""

        mode = getattr(self, "_gen_mode", self.current_tab)
        try:
            fn = vid_meta.get("filename")
            sub = vid_meta.get("subfolder", "")
            url = COMFYUI_URL + "/view?filename=" + fn + "&subfolder=" + sub + "&type=output"
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                self._set_status("Video download failed (%d)" % r.status_code)
                return
            out_path = os.path.join(OUTPUT_DIR, fn)
            tmp_path = out_path + ".tmp"
            with open(tmp_path, "wb") as fh:
                fh.write(r.content)
            os.replace(tmp_path, out_path)
            self._save_history(mode, fn)
            self._show_toast("Video Complete", f"Saved {fn[:25]}")
            # QOL: auto-copy output path to clipboard when enabled
            if self.qol_copy_path.get() == "1" and self.root and self.root.winfo_exists():
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(out_path)
                    self._set_status("Video done: %s | path copied to clipboard" % fn)
                except Exception:
                    self._set_status("Video done: %s | VRAM purged" % fn)
            else:
                self._set_status("Video done: %s | VRAM purged" % fn)
            self._unload_vram()
            # Video gen complete — reset lock (video gen button is a local var, can't update from here)
            self._generate_lock = False
            # Refresh the main-column gallery grid so the new video appears immediately
            if hasattr(self, "_refresh_gallery_main"):
                self._refresh_gallery_main()
            # Open the folder so the user can watch it
            try:
                os.startfile(OUTPUT_DIR)
            except Exception:
                pass
        except Exception as e:
            self._set_status("Show video error: %s" % str(e)[:30])
            self._reset_video_buttons()
            self._generate_lock = False
            self._gen_start_time = None
            self._poll_started_at = None  # QOL: track first running-poll timestamp for ETA

    def _display_preview(self, img):
        try:
            disp = img.copy()
            disp.thumbnail((360, 360))
            tkimg = ctk.CTkImage(light_image=disp, dark_image=disp, size=disp.size)
            if hasattr(self, "preview_label") and self.preview_label and getattr(self.preview_label, "winfo_exists", lambda: True)():
                self.preview_label.configure(image=tkimg, text="")
                self.preview_label.image = tkimg
            # also update the large preview window in the Generate view
            if hasattr(self, "preview_big") and self.preview_big and getattr(self.preview_big, "winfo_exists", lambda: True)():
                big = img.copy()
                big.thumbnail((320, 360))
                bimg = ctk.CTkImage(light_image=big, dark_image=big, size=big.size)
                self.preview_big.configure(image=bimg, text="")
                self.preview_big.image = bimg
        except Exception:
            pass

    def _add_thumb(self, path, mode, only_preview=False):
        if not only_preview:
            try:
                img = Image.open(path)
                img.thumbnail((64, 64))
                tkimg = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                
                idx = self._thumb_count % 6
                if not hasattr(self, "_thumb_labels"):
                    self._thumb_labels = {}
                if idx in self._thumb_labels:
                    try:
                        self._recursive_destroy(self._thumb_labels[idx])
                    except Exception:
                        pass
                
                lbl = ctk.CTkLabel(self.thumb_frame, image=tkimg, text="", width=64, height=64,
                                   fg_color=BG_CARD, corner_radius=4)
                lbl.image = tkimg
                lbl.grid(row=0, column=idx, padx=4, pady=4, sticky="nw")
                self._thumb_labels[idx] = lbl
                
                self._thumb_count += 1
                lbl.bind("<Button-1>", lambda e, fp=path: os.startfile(fp))
                self.thumb_frame.columnconfigure(idx, weight=1)
            except Exception as e:
                logging.error("Add bottom thumb error: %s", e)

        # Also feed the Recent strip inside the preview pane
        try:
            rim = Image.open(path)
            rim.thumbnail((96, 96))
            rimg = ctk.CTkImage(light_image=rim, dark_image=rim, size=rim.size)
            rl = ctk.CTkLabel(self.preview_thumbs, image=rimg, text="", width=88, height=88,
                              fg_color=BG_CARD, corner_radius=6)
            rl.image = rimg
            rl.grid(row=self._preview_thumb_count // 3, column=self._preview_thumb_count % 3,
                    padx=4, pady=4, sticky="nw")
            self._preview_thumb_count += 1
            rl.bind("<Button-1>", lambda e, fp=path: self._select_recent_image(fp))
            self.preview_thumbs.update_idletasks()
        except Exception as e:
            logging.error("Add preview thumb error: %s", e)

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
            tmp_hist = HISTORY_FILE + ".tmp"
            with open(tmp_hist, "w", encoding="utf-8") as fh:
                json.dump(self.history, fh, indent=2)
            os.replace(tmp_hist, HISTORY_FILE)
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
        if not self._running:
            return
        try:
            if hasattr(self, "root") and self.root and self.root.winfo_exists():
                self.root.after(0, self._set_status_gui, msg, level)
        except Exception:
            pass

    def _set_status_gui(self, msg, level):
        try:
            # QOL: Prepend elapsed generation time AND live VRAM usage when a job is running
            if getattr(self, "_gen_start_time", None) is not None and level < logging.WARNING:
                elapsed = time.time() - self._gen_start_time
                elapsed_str = self._fmt_elapsed(elapsed)
                vram_str = self._fmt_vram_live()
                if elapsed > 1:
                    msg = "[%s] %s %s" % (elapsed_str, vram_str, msg)
            if not hasattr(self, "status_label") or not self.status_label.winfo_exists():
                return
            truncated = msg[:33] + "..." if len(msg) > 36 else msg
            if level >= logging.WARNING:
                self.status_label.configure(text=truncated, text_color=("#FFAAAA", "#FFAAAA"))
            else:
                self.status_label.configure(text=truncated, text_color=TEXT)
        except Exception:
            pass

    def _fmt_vram_live(self):
        """Return a compact VRAM usage string like 'VRAM:12.3%'. Non-blocking."""
        try:
            import requests as _r
            r = _r.get(COMFYUI_URL + "/system_stats", timeout=2)
            if r.status_code != 200:
                return ""
            devs = r.json().get("devices", [])
            if devs:
                d = devs[0]
                total = d.get("vram_total", 0) or 0
                free = d.get("vram_free", 0) or 0
                if total > 0:
                    pct = int((1 - free / total) * 100)
                    return "VRAM:%d%%" % pct
        except Exception:
            pass
        return ""

    def _on_crash(self, crash: dict):
        """Called (on the Tk main thread) when the crash handler fires.

        Shows a non-blocking error toast + logs the known-fix hint so the user
        (and any AI reading the screen/log) immediately sees the likely cause.
        The full structured dump is already on disk in the diagnostics/ folder.
        """
        try:
            exc = crash.get("exception", "Unknown crash")
            fixes = crash.get("known_fixes", []) or []
            hint = ""
            if fixes:
                hint = " | Likely fix: " + fixes[0].get("title", "")
            self._set_status("CRASH: %s%s" % (exc[:80], hint), level=logging.ERROR)
            # Toast if available
            try:
                self._show_toast(
                    "App crashed — diagnostics saved",
                    "%s\n\nSaved to: %s\n\nOpen the Debug tab → 'Build Debug Bundle' to send to support/AI." % (
                        exc[:200], crash.get("dump_path", "diagnostics/")),
                    error=True)
            except Exception:
                pass
            # Auto-build a bundle so the user can grab one file immediately
            try:
                from comfyui_desktop.diagnostics import build_debug_bundle
                path = build_debug_bundle(self)
                if not path.startswith("ERROR"):
                    self._set_status("Debug bundle ready: %s" % path)
            except Exception:
                pass
        except Exception:
            pass

    def on_close(self):
        self._running = False
        # Save window geometry
        try:
            with open(_get_config_path(), "w") as f:
                json.dump({"geometry": self.root.geometry()}, f)
        except Exception:
            pass
        try:
            if hasattr(self, "backend_manager") and self.backend_manager:
                self.backend_manager.stop()
        except Exception:
            pass
        # Run backend kill in a background thread so the GUI thread isn't blocked
        def _shutdown():
            self._terminate_backend()
            self._cleanup_symlinks()
        threading.Thread(target=_shutdown, daemon=True).start()
        # Give a brief moment for the kill to issue, then destroy the window
        try:
            self.root.after(300, self._force_quit)
        except Exception:
            self._force_quit()

    def _restore_config(self):
        """Restore saved window geometry (written by on_close) so the app
        reopens where the user left it. Fully additive + safe — any failure
        (missing file, invalid geometry, headless selftest) is swallowed."""
        try:
            path = _get_config_path()
            if not os.path.exists(path):
                return
            with open(path, "r") as f:
                cfg = json.load(f)
            geo = cfg.get("geometry")
            if geo and isinstance(geo, str) and "x" in geo and "+" in geo:
                self.root.geometry(geo)
            # QoL (2026-08-09): honor persisted Text Size for prompt/negative boxes
            try:
                _tsz = getattr(self, "text_size_str", None)
                if _tsz is not None:
                    _size = {"Small": 11, "Medium": 13, "Large": 15}.get(_tsz.get(), 13)
                    self.FONT_TEXT.configure(family="Segoe UI", size=_size)
                    self.FONT_TEXT_BOLD.configure(family="Segoe UI", size=_size, weight="bold")
            except Exception:
                pass
        except Exception:
            pass

    def _force_quit(self):
        """Destroy the root window and force-exit the process to prevent hangs."""
        try:
            self.root.destroy()
        except Exception:
            pass
        # Force exit after a short delay in case mainloop doesn't return
        os._exit(0)

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
        if not self._running:
            return
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
        if not self._running:
            return
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
        if self._running:
            # PRESERVED_LEGACY: Throttled gradient animation loop from 50ms to 250ms to prevent high idle CPU wakeups
            self.root.after(250, self._animate_gradient)

    def _swap_dimensions(self):
        try:
            mode = self.current_tab
            m = self.vars.get(mode, self.vars["txt2img"])
            if "width" in m and "height" in m:
                w_val = m["width"].get() or "1024"
                h_val = m["height"].get() or "1024"
                m["width"].set(h_val)
                m["height"].set(w_val)
                self._set_status(f"Swapped dimensions: {h_val}x{w_val}")
                self._show_toast("Dimensions Swapped", f"New resolution: {h_val}x{w_val}")
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
        for i in range(3):
            self.preview_thumbs.grid_columnconfigure(i, weight=1)
        enable_auto_hide_scrollbar(self.preview_thumbs)

        self._preview_thumb_count = 0
        self.preview_pane = pane
        # DO NOT pre-populate the Recent strip from disk on startup. The last
        # generated image (often NSFW) would show as the default preview on
        # every launch. Start clean — the strip populates only after the user
        # generates. NSFW generation stays fully allowed; this only changes
        # what's shown by DEFAULT on open.
        # self.root.after(300, self._load_recent_into_preview)  # disabled per user request

    def _load_recent_into_preview(self, only_preview=False):
        """Populate the preview pane's Recent strip from OUTPUT_DIR."""
        try:
            if not os.path.isdir(OUTPUT_DIR):
                return
            imgs = [f for f in os.listdir(OUTPUT_DIR)
                    if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith("input")]
            imgs.sort(key=lambda x: os.path.getmtime(os.path.join(OUTPUT_DIR, x)), reverse=True)
            for f in imgs[:9]:
                self._add_thumb(os.path.join(OUTPUT_DIR, f), "txt2img", only_preview=only_preview)
        except Exception:
            pass

    def _build_sidebar_buttons(self):
        cmd = ctk.CTkFrame(self.top, fg_color="transparent", corner_radius=0)
        cmd.grid(row=2, column=0, columnspan=1, padx=12, pady=4, sticky="ew")
        for i in range(4):
            cmd.grid_columnconfigure(i, weight=1)

        btns = [
            ("Open Output", lambda: self._open_dir(OUTPUT_DIR)),
            ("⟳ Restart (Ctrl+R)", self._restart_server),
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
        self._show_log_window(SERVER_LOG_FILE, "ComfyUI — Server Log")

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

            header = ctk.CTkFrame(win, fg_color="transparent", corner_radius=0)
            header.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="ew")
            header.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(header, text=os.path.basename(path), font=self.FONT_SMALL_BOLD,
                         text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w")
            btn_row = ctk.CTkFrame(header, fg_color="transparent")
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
                        sz = os.path.getsize(path)
                        with open(path, "r", errors="replace") as fh:
                            if sz > 200000:
                                fh.seek(sz - 200000)
                                content = f"... (tail of {sz // 1024} KB file)\n" + fh.read()
                            else:
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
            if name not in MODELS:
                self._set_status("Model '%s' not available (file missing)" % name)
                return
            model = MODELS[name]
            # Refuse to switch to a model whose checkpoint file is absent so we
            # never queue a job that will fail with "Model file missing".
            if not (os.path.exists(os.path.join(ARCHIVE_DIR, model["value"]))
                    or os.path.exists(os.path.join(CKPT_DIR, model["value"]))):
                self._set_status("Model file missing: %s" % model["value"])
                return
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
                # QoL (2026-08-09): route preset text to the ACTIVE tab's entries,
                # not always the txt2img boxes. Previously applying a preset on the
                # img2img/upscale tab wrote into the (hidden) txt2img boxes and the
                # user saw nothing change.
                p_ent = self.prompt_entry
                n_ent = self.neg_entry
                if self.current_tab == "img2img" and hasattr(self, "img2img_prompt_entry"):
                    p_ent = self.img2img_prompt_entry
                    n_ent = self.img2img_neg_entry
                p_ent.delete("1.0", "end")
                p_ent.insert("1.0", p["prompt"])
                n_ent.delete("1.0", "end")
                n_ent.insert("1.0", p["neg"])
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
        if isinstance(path, str):
            path = path.strip('"\'').strip()
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
                self._show_toast("Image Staged", f"Staged {os.path.basename(path)[:25]}")
            except Exception as e:
                self._set_status("Image load failed: %s" % str(e)[:30])

    def _pick_upscale(self):
        path = filedialog.askopenfilename(
            title="Select Image to Upscale",
            filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")])
        if path:
            if isinstance(path, str):
                path = path.strip('"\'').strip()
            try:
                img = Image.open(path).convert("RGB")
                self.input_image_path = path
                self._show_thumb(self.up_preview, img)
                self._set_status("Upscale: %s" % os.path.basename(path)[:30])
                self._show_toast("Image Loaded", f"Loaded {os.path.basename(path)[:25]} for upscaling")
            except Exception as e:
                self._set_status("Image load failed: %s" % str(e)[:30])

    def _refresh_app_state(self):
        """QoL: Refresh model checkpoints, reload gallery, and clear status."""
        try:
            self._scan_available_checkpoints()
            self._reload_recent_preview()
            self._set_status("App state refreshed successfully")
            self._show_toast("Refreshed", "Model checkpoints and gallery reloaded")
        except Exception as e:
            self._set_status("Refresh failed: %s" % str(e)[:30])

    def _show_thumb(self, label, img):
        img.thumbnail((200, 150))
        try:
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            label.configure(image=ctk_img, text="")
            label.image = ctk_img
        except Exception:
            tkimg = ImageTk.PhotoImage(img)
            label.configure(image=tkimg, text="")
            label.image = tkimg


    def _handle_app_shutdown(self):
        """Clean application shutdown handler for window close event."""
        self._running = False
        try:
            if hasattr(self, "backend_manager") and self.backend_manager:
                self.backend_manager.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "root") and self.root:
                self.root.destroy()
        except Exception:
            pass


# ------------------------------------------------------------------
_in_crash_hook = False
def _crash_hook(exc_type, exc_value, exc_tb):
    global _in_crash_hook
    if _in_crash_hook:
        return
    _in_crash_hook = True
    try:
        tb = traceback.format_exception(exc_type, exc_value, exc_tb)
        try:
            with open(os.path.join(LOG_DIR, "ComfyUI_crash.txt"), "w") as fh:
                fh.write("CRASH\n")
                fh.write("\n".join(tb))
                fh.write("\nUnhandled crash: %s" % exc_value)
        except Exception:
            pass
        logging.error("Unhandled crash: %s" % exc_value)
    finally:
        _in_crash_hook = False


def main():
    sys.excepthook = _crash_hook
    # ADDITIVE: Native selftest flag support for Phase 4 EXE boot verification
    if "--selftest" in sys.argv:
        print("SELFTEST_START: Initializing Tkinter root and ComfyUIApp instance...")
        try:
            root = ctk.CTk()
            root.withdraw() # Keep window hidden during selftest
            app = ComfyUIApp(root)
            print("SELFTEST_SUCCESS: Core UI and app state initialized cleanly.")
            root.destroy()
            sys.exit(0)
        except Exception as e:
            print(f"SELFTEST_FAILURE: {e}")
            sys.exit(1)

    root = ctk.CTk()
    root.title("ComfyUIX")
    root.configure(bg="#141416")
    app = ComfyUIApp(root)
    root.title(app._stamped_title())
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.after(100, lambda: app._paint_header())
    root.after(500, lambda: app._start_backend_threads())
    root.mainloop()


if __name__ == "__main__":
    main()
