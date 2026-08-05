"""
ComfyUI Uncensored v5.0 - Main Application Entry Point
Delegates execution to modular main.py while maintaining frozen PyInstaller build compatibility.
"""
import sys
import os

# Guarantee current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main, ComfyUIApp

if __name__ == "__main__":
    main()

    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ComfyUI_Uncensored',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon_path] if os.path.exists(icon_path) else [],
)

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

text\
        self._cancel_hide()
        self._hide_after_id = self.after(1200, self._do_hide)

    def _cancel_hide(self):
        if self._hide_after_id is not None:
            try:
                self.after_cancel(self._hide_after_id)
            except Exception:
                pass
            self._hide_after_id = None
6. **Purge** stale v3.0.0 error JSONs + remove orphan `launcher.c`.
7. **Re-run**: launch exe, confirm server bootstraps (status "Server online"), generate one txt2img, verify file lands in `Pictures\ComfyUI_Generated\`.

---

## BOTTOM LINE

You do **not** have a working app right now. The desktop shortcut points at a 128 KB non-executable stub. The v4.1 source is a credible rewrite (clean tkinter, proper DWM/Mica code, correct 64-bit drag-drop subclassing) but has **never been built or run**, and has 3 logic bugs + 1 dead subsystem that would bite on first use. None of the old crash/error artifacts are from this version.

I can execute the full remediation (rebuild + 4 bug fixes + verify a real generation) on your go-ahead. I will not declare it done until the exe is >50 MB AND a generated image actually appears in `Pictures\ComfyUI_Generated\`.

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
        sys.stderr.write("video support unavailable at import: %s\
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
# Input staging dir must be where ComfyUI's LoadImage reads from (its working dir + /input)
INPUT_DIR = os.path.join(COMFYUI_DIR, "input")
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
    "epiCRealism XL": {
        "value": "epicrealismXL_pure.safetensors",
        "w": 768, "h": 768, "steps": 35, "cfg": 6.5,
    },
    "Juggernaut XL": {
        "value": "juggernautXL_ragnarok.safetensors",
        "w": 1216, "h": 832, "steps": 35, "cfg": 5.0,
    },
    "Pony Diffusion V6 XL": {
        "value": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        "w": 832, "h": 1216, "steps": 25, "cfg": 7.0,
    },
}

PRESETS = {
    "Photoreal Portrait": {
        "model": "epiCRealism XL",
        "prompt": "photorealistic portrait of a woman, 85mm lens, shallow depth of field, "
                  "soft studio rim light, highly detailed skin texture, sharp focused eyes, "
                  "natural makeup, neutral blurred background, shot on Sony A7 IV, 8k uhd, "
                  "intricate details, volumetric lighting",
        "neg": "blurry, lowres, deformed, extra limbs, bad anatomy, watermark, text, "
               "cartoon, painting, illustration, oversaturated, jpeg artifacts, double chin",
        "steps": 35, "cfg": 6.5, "w": 768, "h": 768,
    },
    "Cinematic Wide": {
        "model": "Juggernaut XL",
        "prompt": "epic cinematic wide shot, dramatic volumetric lighting, atmospheric haze, "
                  "highly detailed environment, rule of thirds composition, anamorphic lens "
                  "flare, teal and orange cinematic color grade, photorealistic, 8k, "
                  "epic scale, film still",
        "neg": "blurry, lowres, deformed, watermark, text, oversaturated, flat lighting, "
               "amateur, cropping, extra limbs",
        "steps": 35, "cfg": 5.0, "w": 1216, "h": 832,
    },
    "Anime Character": {
        "model": "Pony Diffusion V6 XL",
        "prompt": "anime style character, vibrant cel shading, detailed flowing hair, "
                  "expressive detailed eyes, dynamic pose, clean linework, studio anime "
                  "background, high detail, masterpiece, best quality, intricate",
        "neg": "realistic, photo, photographic, 3d render, blurry, lowres, deformed, "
               "bad anatomy, watermark, text, extra limbs",
        "steps": 25, "cfg": 7.0, "w": 832, "h": 1216,
    },
    "Game Texture": {
        "model": "Pony Diffusion V6 XL",
        "prompt": "game texture, seamless tileable diffuse map, clean flat shading, "
                  "hand-painted cell-shaded style, consistent pixel density, UV-friendly, "
                  "no stretching, neutral lighting, game-ready asset, high detail",
        "neg": "realistic, photo, photographic, blurry, lowres, distorted seams, stretching, "
               "watermark, text, jpeg artifacts, noise",
        "format": "Game Texture (TGA)",
        "steps": 25, "cfg": 7.0, "w": 832, "h": 1216,
    },
}

SAMPLERS = ["dpmpp_2m", "dpmpp_sde", "euler", "euler_ancestral", "dpmpp_2m_sde", "ddim"]
SCHEDULERS = ["karras", "normal", "simple", "ddim_uniform", "beta"]
UPSCALE_MODELS = ["4x-UltraSharp.pth", "4x_NMKD-Siax_200k.pth", "ESRGAN_4x.pth"]
DEFAULT_NEG = "blurry, lowres, deformed, watermark, text"

# ---- Tooltips ----
TOOLTIPS = {
    "Prompt": ("Prompt",
        "The text that drives the image. Be specific and concrete.\
        "Structure: subject + appearance + setting + lighting + camera/lens + quality tags.\
        "Recommended: 'photorealistic portrait of a woman, 85mm lens, soft rim light, "
        "detailed skin, neutral background, 8k uhd'.\
        "Best used: lead with the subject; add style and mood words; avoid vague terms like 'nice'."),
    "Negative Prompt": ("Negative Prompt",
        "What to EXCLUDE. This is as important as the prompt.\
        "Recommended base: 'blurry, lowres, deformed, extra limbs, watermark, text, "
        "oversaturated, jpeg artifacts'.\
        "Best used: add model-specific exclusions (e.g. 'cartoon, painting' for photoreal; "
        "'realistic, photo' for anime). Tightens coherence fast."),
    "Width": ("Width",
        "Image width in pixels.\
        "Recommended: 768 (epiCRealism/Juggernaut square), 1216 (Juggernaut wide), 832 (Pony).\
        "Best used: match the model's trained resolution; off-native sizes cause distortion "
        "and doubled subjects. Pair with Height for the right aspect ratio."),
    "Height": ("Height",
        "Image height in pixels.\
        "Recommended: 768 (portrait), 1216 (Juggernaut wide), 832 (Pony tall).\
        "Best used: keep Width x Height near the model's native bucket (e.g. 832x1216 for Pony)."),
    "Steps": ("Steps",
        "Denoising passes — more = finer detail up to a point.\
        "Recommended: 30-35 (epiCRealism), 25 (Pony/fast), 40 (max quality).\
        "Best used: 30 is the SDXL sweet spot; beyond 40 rarely improves and just adds time. "
        "Lower steps = faster but softer."),
    "CFG": ("CFG Scale",
        "How strictly the image follows the prompt (1-10+).\
        "Recommended: 6.5 (epiCRealism), 5.0 (Juggernaut), 7.0-7.5 (Pony).\
        "Best used: too high = over-saturated/artifacting and rigid; too low = ignores prompt "
        "and drifts. 5-7 is the usable band for XL models."),
    "Seed": ("Seed",
        "Starting noise seed. 0 = new random each run.\
        "Recommended: lock a seed you like, then vary the prompt to iterate versions.\
        "Best used: same seed + changed prompt = controlled variation; great for refining a shot."),
    "Batch": ("Batch Size",
        "Images generated per click.\
        "Recommended: 1 on 8GB VRAM; 2-4 only if VRAM headroom allows.\
        "Best used: batch several variations, then pick the best in the Gallery."),
    "Sampler": ("Sampler",
        "The solver for each diffusion step.\
        "Recommended: dpmpp_2m (best all-rounder — fast, clean, SDXL-native).\
        "Best used: dpmpp_2m for realism/portraits; euler_ancestral for more creative variety; "
        "dpmpp_sde for moody renders."),
    "Scheduler": ("Scheduler",
        "Noise (sigma) schedule across steps.\
        "Recommended: karras (smoothest, most consistent for XL).\
        "Best used: karras for portraits/product; normal or simple also fine; beta for softer."),
    "Model": ("Model",
        "Checkpoint — each tuned for a style and native resolution.\
        "Recommended: epiCRealism XL (photoreal, 768), Juggernaut XL (cinematic, 1216x832), "
        "Pony Diffusion V6 XL (anime/stylized, 832x1216).\
        "Best used: pick by output goal; presets auto-set the matching size and steps."),
    "Preset": ("Preset",
        "One-click starter: sets model, size, steps, CFG and a strong prompt + negative.\
        "Recommended: Photoreal Portrait / Cinematic Wide / Anime Character / Game Texture.\
        "Best used: start from a preset, then tweak the prompt to taste — faster than blank."),
    "Generate": ("Generate",
        "Start generation (Ctrl+E). Click again to cancel mid-run.\
        "Recommended: set a clear prompt + model first; watch the VRAM % in the status bar.\
        "Best used: if VRAM hits critical, wait — the app warns before it risks a crash."),
    "Output Format": ("Output Format",
        "PNG = lossless, standard. Game Texture (TGA) = power-of-two for engine import.\
        "Recommended: PNG for normal art; TGA only when feeding UE5/Unity.\
        "Best used: TGA auto-pads to a power-of-two canvas for seamless textures."),
    "Denoise": ("Denoise",
        "img2img strength — how much to change the input.\
        "Recommended: 0.7 (strong restyle), 0.45-0.55 (keep composition), 0.3 (subtle refine).\
        "Best used: high to re-imagine, low to polish a good base while keeping its layout."),
    "Upscale Model": ("Upscale Model",
        "ESRGAN model for 2x/4x upscaling.\
        "Recommended: 4x-UltraSharp (crisp photos), 4x_NMKD-Siax (smooth/anime), ESRGAN_4x (general).\
        "Best used: UltraSharp for detail; NMKD-Siax for softer, cleaner line art."),
    "Input Image": ("Input Image",
        "Source image for img2img, or first frame of a video.\
        "Recommended: 512-1024px source; leave blank for txt2img.\
        "Best used: click 'Upload' (or drag-drop) then set Denoise to control change."),
}

# ---- Design System Tokens (High-Contrast Periwinkle / Slate Palette) ----
ctk.set_appearance_mode("system")
# Neutralize any OS-accent-colored widget borders app-wide by overriding the
# CTk theme border colors to the app's neutral slate token. This kills the
# stray orange outline that Windows 11 was drawing on dropdowns/buttons/frames.
try:
    _NEUTRAL = ("#2A2A3C", "#2A2A3C")  # BORDER token, both light/dark
    for _wname, _wcfg in ctk.ThemeManager.theme.items():
        if isinstance(_wcfg, dict) and "border_color" in _wcfg:
            try:
                _wcfg["border_color"] = list(_NEUTRAL)
            except Exception:
                pass
        if isinstance(_wcfg, dict) and "border_width" in _wcfg:
            try:
                # Keep Entry/ComboBox functionally outlined but neutral-colored;
                # zero out purely decorative frame/button borders.
                if _wname in ("CTkEntry", "CTkComboBox", "CTkTextbox"):
                    _wcfg["border_width"] = 1
                else:
                    _wcfg["border_width"] = 0
            except Exception:
                pass
except Exception:
    pass


BG_APP = ("#F1F5F9", "#0F0F12")
BG_SIDEBAR = ("#E2E8F0", "#14141A")          # LEFT SIDEBAR — stays black, DO NOT TOUCH
BG_CARD = ("#FFFFFF", "#1E1E2C")              # main panels — gradient tone (uniform)
BG_CARD_ALT = ("#F8FAFC", "#25253A")          # inner panels / fields — gradient tone
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

    @staticmethod
    def _get_event_target(widget):
        """Return the widget that actually receives mouse Enter/Leave events."""
        canvas = getattr(widget, "_canvas", None)
        return canvas if canvas is not None else widget

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
        target = self._get_event_target(self.widget)
        try:
            x = target.winfo_rootx() + 12
            y = target.winfo_rooty() + target.winfo_height() + 4
        except Exception:
            x = 40
            y = 40
        master = self.widget.winfo_toplevel()
        self.tipwindow = tw = ctk.CTkToplevel(master)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.wm_attributes("-topmost", True)
        tw.configure(fg_color=("gray95", "#1E1E28"))
        ctk.CTkLabel(tw, text=self.title, font=("Segoe UI", 10, "bold"),
                     text_color=TEXT).pack(padx=8, pady=(8, 2))
        ctk.CTkLabel(tw, text=self.description, font=("Segoe UI", 11),
                     text_color=TEXT_MUTED, wraplength=300).pack(padx=8, pady=(0, 8))
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

    def __init__(self, root):
        self.root = root
        self._running = True
        root.title("ComfyUI Uncensored")
        root.geometry("1280x1040")
        root.minsize(960, 680)
        mode = ctk.get_appearance_mode().lower()
        root.configure(bg="#F1F5F9" if mode == "light" else "#0F0F12")

        self.tooltips_enabled = ctk.StringVar(value="1")
        self.current_tab = "txt2img"
        self.vars = {}
        self.staged_image = None
        self.input_image_path = None
        self._init_drag_system()
        self.history = []
        self._load_history()
        self.backend = None
        self.backend_retries = 0
        self.last_prompt_id = None
        self.last_watch = time.time()
        self.current_pil = None
        self._hue = 0.0
        # Gallery selection state (Apple-style multi-select + delete)
        self._gallery_token = 0
        self._gallery_selected = set()   # set of file paths currently selected
        self._gallery_sel_mode = False   # True while in selection mode

        self._bg_label = None
        self._paint_background()
        root.bind("<Configure>", self._on_root_configure)

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
        self._poll_after_id = None
        self._cancel_requested = False
        self._last_tab_switch = 0
        self._last_model_switch = 0
        self._last_preset_switch = 0
        self._last_generate = 0

        self._init_vars()
        self._init_settings_vars()
        self._build_sidebar()
        self._build_main()

        self._build_status_bar()
        self._build_sidebar_buttons()

        root.bind("<Control-Return>", lambda e: self._start_generate())
        root.bind("<Shift-Return>", lambda e: self._start_generate())
        root.bind("<Control-e>", lambda e: self._start_generate())
        root.bind("<Control-E>", lambda e: self._start_generate())
        root.bind("<Control-o>", lambda e: self._open_dir(OUTPUT_DIR))
        root.bind("<F5>", lambda e: self._refresh_gallery_main())

        # Window Close Protocol
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Show window immediately, defer backend + gradient
        root.after(100, self._paint_header)
        root.after(5000, self._animate_gradient)
        root.after(15000, self._start_header_gradient)
        root.after(300, self._start_backend_threads)
                                  fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                  button_hover_color=BRAND_HOVER,
                                  dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT, dropdown_hover_color=DROPDOWN_HOVER)
        scale.set(getattr(self, "_current_scaling_val", "100%"))
        scale.grid(row=20, column=0, padx=14, pady=(4, 16), sticky="ew")
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

            def _refresh_children(parent):
                for child in parent.winfo_children():
                    if hasattr(child, "refresh_appearance"):
                        try:
                            child.refresh_appearance()
                        except Exception:
                            pass
                    _refresh_children(child)
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self.root, width=220, corner_radius=0, fg_color=BG_SIDEBAR)
        sb.grid(row=0, column=0, rowspan=4, sticky="nsew")
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(10, weight=1)  # spacer pushes status to bottom
        self.sidebar = sb
        # Brand
        ctk.CTkLabel(sb, text="ComfyUI", font=self.FONT_LOGO,
                     text_color=BRAND).grid(row=0, column=0, padx=20, pady=(22, 0), sticky="w")
        ctk.CTkLabel(sb, text="Uncensored", font=self.FONT_LOGO_SUB,
                     text_color=TEXT).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        # Primary navigation (clean, minimal)
        nav = [("Generate", self._focus_generate), ("Gallery", self._focus_gallery),
               ("Settings", self._focus_settings)]
        for i, (label, cmd) in enumerate(nav):
            b = ctk.CTkButton(sb, text=label, height=34, anchor="w", fg_color="transparent",
                              text_color=TEXT, hover_color=BG_CARD_ALT,
                              corner_radius=8, command=cmd, font=self.FONT_NORMAL_BOLD)
            b.grid(row=2 + i, column=0, padx=14, pady=6, sticky="ew")

        # Appearance (compact, dedicated — not a wall of params)
        ctk.CTkLabel(sb, text="Appearance", font=self.FONT_SMALL_BOLD,
                     text_color=TEXT_MUTED).grid(row=6, column=0, padx=20, pady=(14, 2), sticky="w")
        mode = ctk.CTkOptionMenu(sb, values=["Dark", "Light", "System"],
                                 command=self._set_appearance,
                                 fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                 button_hover_color=BRAND_HOVER,
                                 dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                 dropdown_hover_color=DROPDOWN_HOVER)
        mode.set(getattr(self, "_current_appearance_val", "System"))
        mode.grid(row=7, column=0, padx=14, pady=4, sticky="ew")
        scale = ctk.CTkOptionMenu(sb, values=["90%", "100%", "110%", "120%"],
                                  command=self._set_scaling,
                                  fg_color=BG_CARD_ALT, button_color=BORDER, text_color=TEXT,
                                  button_hover_color=BRAND_HOVER,
                                  dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                  dropdown_hover_color=DROPDOWN_HOVER)
        scale.set(getattr(self, "_current_scaling_val", "100%"))
        scale.grid(row=8, column=0, padx=14, pady=(4, 12), sticky="ew")

        # Status pill (bottom)
        self.status_label = ctk.CTkLabel(sb, text="Initializing...", height=30, corner_radius=8,
                                         fg_color=BG_CARD_ALT, text_color=TEXT,
                                         font=self.FONT_NORMAL, wraplength=1180,
                                         anchor="w")
        self.status_label.grid(row=11, column=0, padx=14, pady=(8, 14), sticky="ew")
                                  dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                                  dropdown_hover_color=DROPDOWN_HOVER)
        scale.set(getattr(self, "_current_scaling_val", "100%"))
        scale.grid(row=8, column=0, padx=14, pady=(4, 12), sticky="ew")

        # Status pill (bottom)
        self.status_label = ctk.CTkLabel(sb, text="Initializing...", height=30, corner_radius=8,
                                         fg_color=BG_CARD_ALT, text_color=TEXT,
                                         font=self.FONT_NORMAL, wraplength=1180,
                                         anchor="w")
        self.status_label.grid(row=11, column=0, padx=14, pady=(8, 14), sticky="ew")


    # ---- Safe pure-Tk internal drag (preview -> input box) ----
    def _init_drag_system(self):
        self._drag_targets = {}
        self._drag_pil = None
        self._drag_path = None
        self._drag_ghost = None
        self._drag_moved = False
        self._drag_start = None
            new_h = int(1120 * factor)
            min_w = int(900 * factor)
            min_h = int(640 * factor)
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.minsize(min_w, min_h)
                    self.root.update_idletasks()
                    x = self.root.winfo_x()
                    y = self.root.winfo_y()
                    if x >= 0 and y >= 0:
                        self.root.geometry(f"{new_w}x{new_h}+{x}+{y}")
        return None

    def _make_drag_source(self, widget, get_pil, get_path=None, on_click=None):
        def _press(e):
            self._drag_start = (e.x_root, e.y_root)
            self._drag_moved = False

        def _motion(e):
            if not self._drag_start:
                return
            dx = e.x_root - self._drag_start[0]
            dy = e.y_root - self._drag_start[1]
            if not self._drag_moved and (abs(dx) > 6 or abs(dy) > 6):
                pil = get_pil()
                if pil is None:
                    return
                self._drag_moved = True
                self._drag_pil = pil
                self._drag_path = get_path() if get_path else None
                g = tk.Toplevel(self.root)
                g.overrideredirect(True)
                g.attributes("-topmost", True)
                thumb = pil.copy()
                thumb.thumbnail((160, 160))
                tkimg = ImageTk.PhotoImage(thumb)
                lbl = tk.Label(g, image=tkimg, bg="#1E1E2C", relief="solid", bd=1)
                lbl.image = tkimg
                lbl.pack()
                self._drag_ghost = g
            if self._drag_moved and self._drag_ghost:
                self._drag_ghost.geometry("+%d+%d" % (e.x_root + 14, e.y_root + 14))

        def _release(e):
            moved = self._drag_moved
            ghost = self._drag_ghost
            pil = self._drag_pil
            path = self._drag_path
            self._drag_ghost = None
            self._drag_pil = None
            self._drag_path = None
            self._drag_moved = False
            self._drag_start = None
            if ghost:
                try:
                    ghost.destroy()
                except Exception:
                    pass
            if moved:
                tgt = self.root.winfo_containing(e.x_root, e.y_root)
                tgt = self._find_drop_target(tgt) if tgt else None
                if tgt:
                    cb = self._drag_targets.get(str(tgt.winfo_id()))
                    if cb:
                        cb(pil, path)
            elif on_click:
                on_click()

        widget.bind("<ButtonPress-1>", _press)
        widget.bind("<B1-Motion>", _motion)
        widget.bind("<ButtonRelease-1>", _release)

    def _stage_pil(self, pil, label, mode):
        try:
            if pil is None:
                return
            dst = os.path.join(INPUT_DIR, "drag_in.png")
            pil.save(dst)
            self.input_image_path = dst
            self._show_thumb(label, pil)
            self._set_status("%s input: dragged preview" % mode)
        except Exception as e:
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
            # Restore the active tab after rebuild (scaling change shouldn't lose it)
            if active_tab != "txt2img":
                try:
                    self.tabview.set(
                        "Text to Image" if active_tab == "txt2img" else
                        "Image to Image" if active_tab == "img2img" else "Upscale")
                except Exception:
                    pass
                self.current_tab = active_tab
            self._update_cursors_and_canvases()
        except Exception as e:
            logging.error("Rebuild UI error: %s", e)

    def _set_appearance(self, v):
        try:
            self._current_appearance_val = v
            mode_lower = str(v).lower()
            ctk.set_appearance_mode(mode_lower)
            self._update_cursors_and_canvases()
            if hasattr(self, '_bg_label') and self._bg_label:
                self._paint_background()
        except Exception as e:
            logging.error("Set appearance error: %s", e)

    def _set_scaling(self, v):
        try:
            factor = float(v.replace("%", "")) / 100.0
            self._current_scaling_val = v
            # Safely scale font sizes for clean proportional rendering
            self.FONT_BOLD = ctk.CTkFont(family="Segoe UI", size=max(9, int(13 * factor)), weight="bold")
            self.FONT_NORMAL = ctk.CTkFont(family="Segoe UI", size=max(8, int(11 * factor)))
            self.FONT_NORMAL_BOLD = ctk.CTkFont(family="Segoe UI", size=max(8, int(11 * factor)), weight="bold")
            self.FONT_SMALL = ctk.CTkFont(family="Segoe UI", size=max(7, int(10 * factor)))
            self.FONT_SMALL_BOLD = ctk.CTkFont(family="Segoe UI", size=max(7, int(10 * factor)), weight="bold")
            self.FONT_LOGO = ctk.CTkFont(family="Segoe UI", size=max(14, int(22 * factor)), weight="bold")
            self.FONT_LOGO_SUB = ctk.CTkFont(family="Segoe UI", size=max(9, int(13 * factor)), weight="bold")

            min_w = int(900 * factor)
            min_h = int(640 * factor)
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.minsize(min_w, min_h)
                except Exception:
                    pass
            self.root.after(50, self._deferred_rebuild_ui)
            self._set_status("UI Scaled to %s" % v)
        except Exception as e:
            logging.error("Set scaling error: %s", e)

    def _deferred_rebuild_ui(self):
        try:
            self._rebuild_ui()
            if hasattr(self, '_bg_label') and self._bg_label:
                self._paint_background()
        except Exception as e:
            logging.error("Deferred rebuild error: %s", e)

    def _focus_generate(self):
        import time
        try:
            logging.info("Focus generate clicked")
            if time.time() - self._last_tab_switch < 0.3:
                return
            self._last_tab_switch = time.time()
            if self.tabview.get() != "Text to Image":
                self.tabview.set("Text to Image")
            self.prompt_entry.focus()
            self._show_view("generate")
        except Exception as e:
            logging.error("Focus generate error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

    def _focus_gallery(self):
        import time
        try:
            logging.info("Focus gallery clicked")
            if time.time() - self._last_tab_switch < 0.3:
                return
            self._last_tab_switch = time.time()
            self._build_gallery_in_main()
            self._show_view("gallery")
        except Exception as e:
            logging.error("Focus gallery error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

        try:
            logging.info("Focus settings clicked")
            if time.time() - self._last_tab_switch < 0.3:
                return
            self._last_tab_switch = time.time()
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
        header.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(header, text="Generated Images", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        # selection count (shows "N selected" only in select mode)
        self._gallery_count = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=11),
                                            text_color=BRAND[1] if ctk.get_appearance_mode().lower() == "dark" else BRAND[0])
        self._gallery_count.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="w")
        # right-aligned action buttons (hidden until select mode)
        self._gallery_btn_select = ctk.CTkButton(header, text="Select", width=80, height=24,
                                                 command=self._gallery_enter_select,
                                                 fg_color=BG_CARD_ALT, hover_color=BORDER,
                                                 text_color=TEXT)
        self._gallery_btn_select.grid(row=0, column=3, padx=6, pady=8, sticky="e")
        self._gallery_btn_refresh = ctk.CTkButton(header, text="Refresh", width=80, height=24,
                                                  command=self._refresh_gallery_main, fg_color=ACCENT2,
                                                  hover_color=ACCENT2_HOVER, text_color="#FFFFFF")
        self._gallery_btn_refresh.grid(row=0, column=4, padx=6, pady=8, sticky="e")
        # --- selection-mode toolbar (hidden by default) ---
        self._gallery_selbar = ctk.CTkFrame(header, fg_color="transparent")
        self._gallery_selbar.grid(row=0, column=3, columnspan=2, padx=6, pady=8, sticky="e")
        self._gallery_selbar.grid_remove()
        self._gallery_btn_all = ctk.CTkButton(self._gallery_selbar, text="Select All", width=84, height=24,
                                              command=self._gallery_select_all,
                                              fg_color=BG_CARD_ALT, hover_color=BORDER, text_color=TEXT)
        self._gallery_btn_all.pack(side="left", padx=(0, 6))
        self._gallery_btn_del = ctk.CTkButton(self._gallery_selbar, text="Delete", width=84, height=24,
                                              command=self._gallery_delete_selected,
                                              fg_color=("#DC2626", "#EF4444"), hover_color=("#B91C1C", "#DC2626"),
                                              text_color="#FFFFFF")
        self._gallery_btn_del.pack(side="left", padx=(0, 6))
        self._gallery_btn_cancel = ctk.CTkButton(self._gallery_selbar, text="Cancel", width=80, height=24,
                                                 command=self._gallery_exit_select,
                                                 fg_color=BG_CARD_ALT, hover_color=BORDER, text_color=TEXT)
        self._gallery_btn_cancel.pack(side="left")

        self._gallery_frame_main = ctk.CTkScrollableFrame(self._gallery_main, fg_color=BG_CARD_ALT, corner_radius=8)
        self._gallery_frame_main.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._gallery_frame_main.grid_columnconfigure(0, weight=1)
        enable_auto_hide_scrollbar(self._gallery_frame_main)
        self._refresh_gallery_main()

    def _refresh_gallery_main(self):
            """Populate gallery with thumbnails from OUTPUT_DIR in main area.

            FIX: thumbnails are decoded + downscaled in a BACKGROUND thread so the
            full-resolution PNG/TGA decode never blocks the UI thread (was the
            'gallery lags my PC' bug). The 3-column grid is configured so thumbs
            actually lay out as a grid instead of collapsing to one column.
            """
            self._set_status("Gallery: refreshing...")
            print(f"[GALLERY DEBUG] _refresh_gallery_main called")
            if not hasattr(self, '_gallery_frame_main') or not self._gallery_frame_main.winfo_exists():
                print("[GALLERY DEBUG] _gallery_frame_main missing or gone")
                return
            for widget in self._gallery_frame_main.winfo_children():
                widget.destroy()
            for c in range(3):
                self._gallery_frame_main.grid_columnconfigure(c, weight=1, uniform="gcol")
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
                    except Exception as e:
                        print(f"[GALLERY DEBUG] thumbnail error for {fname}: {e}")
                        pass
                if getattr(self, "_gallery_token", 0) != token:
                    print("[GALLERY DEBUG] token invalidated, aborting")
                    return
                if not frame.winfo_exists():
                    print("[GALLERY DEBUG] frame gone")
                    return

                def place():
                    if not frame.winfo_exists() or getattr(self, "_gallery_token", 0) != token:
                        return
                    for idx, (fp, fname, im) in enumerate(thumbs):
                        try:
                            cell = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=8)
                            cell.grid(row=idx // cols, column=idx % cols,
                                      padx=6, pady=6, sticky="nsew")
                            photo = ImageTk.PhotoImage(im)
                            lbl = ctk.CTkLabel(cell, image=photo, text="",
                                               fg_color=BG_CARD, corner_radius=6,
                                               width=thumb[0], height=thumb[1])
                            lbl.image = photo
                            lbl.pack(fill="both", expand=True)
                            # double-click opens the full image
                            lbl.bind("<Double-Button-1>", lambda e, f=fp: os.startfile(f))
                            lbl.bind("<Enter>", lambda e, p=fname: self._set_status(p))
                            # single click toggles selection (Apple-style)
                            lbl.bind("<Button-1>", lambda e, f=fp: self._gallery_toggle(f))
                            # store refs so selection visuals can update without rebuild
                            cell._fp = fp
                            lbl._cell = cell
                            # selection check badge (top-left), hidden until selected
                            badge = ctk.CTkLabel(cell, text="✓", width=22, height=22,
                                                fg_color=BRAND, text_color="#FFFFFF",
                                                corner_radius=11, font=ctk.CTkFont(size=12, weight="bold"))
                            cell._badge = badge
                            # apply current selection visual state
                            self._gallery_style_cell(cell, fp in self._gallery_selected)
                        except Exception as e:
                            print(f"[GALLERY DEBUG] place error for {fp}: {e}")
                    try:
                        frame.update_idletasks()
                    except Exception as e:
                        print(f"[GALLERY DEBUG] update_idletasks error: {e}")

                self.root.after(0, place)

            threading.Thread(target=worker, daemon=True).start()

    def _gallery_style_cell(self, cell, selected):
        """Apply/remove the selection ring + check badge on a gallery cell."""
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
        except Exception as e:
            logging.error("Gallery style cell error: %s", e)

    def _gallery_toggle(self, fp):
        if not self._gallery_sel_mode:
            self._gallery_enter_select()
        if fp in self._gallery_selected:
            self._gallery_selected.discard(fp)
            self._set_status("Deselected %s" % os.path.basename(fp)[:36])
        else:
            self._gallery_selected.add(fp)
            self._set_status("Selected %s" % os.path.basename(fp)[:36])
        # update matching cells in all active gallery containers
        for container_name in ("_gallery_frame_main", "_gallery_frame", "thumb_frame"):
            container = getattr(self, container_name, None)
            if container and container.winfo_exists():
                for w in container.winfo_children():
                    if getattr(w, "_fp", None) == fp:
                        self._gallery_style_cell(w, fp in self._gallery_selected)
        self._gallery_update_selection_ui()

    def _gallery_enter_select(self):
        self._gallery_sel_mode = True
        if hasattr(self, "_gallery_btn_select") and self._gallery_btn_select.winfo_exists():
            self._gallery_btn_select.grid_remove()
        if hasattr(self, "_gallery_btn_refresh") and self._gallery_btn_refresh.winfo_exists():
            self._gallery_btn_refresh.grid_remove()
        if hasattr(self, "_gallery_selbar") and self._gallery_selbar.winfo_exists():
            self._gallery_selbar.grid()
        self._gallery_update_selection_ui()
        self._set_status("Select mode: click images to select, then Delete")
        self._gallery_selbar.grid_remove()
        self._gallery_btn_select.grid()
        self._gallery_btn_refresh.grid()
        self._gallery_count.configure(text="")
        # clear rings without a full rebuild
        for w in self._gallery_frame_main.winfo_children():
            if getattr(w, "_fp", None):
                self._gallery_style_cell(w, False)
        self._set_status("Selection cleared")

    def _gallery_select_all(self):
        try:
            items = [w._fp for w in self._gallery_frame_main.winfo_children() if getattr(w, "_fp", None)]
            self._gallery_selected.update(items)
            for w in self._gallery_frame_main.winfo_children():
                if getattr(w, "_fp", None):
                    self._gallery_style_cell(w, True)
            self._gallery_update_selection_ui()
            self._set_status("Selected all (%d)" % len(items))
        except Exception:
            pass

    def _gallery_update_selection_ui(self):
        n = len(self._gallery_selected)
        if self._gallery_sel_mode:
            self._gallery_count.configure(text="%d selected" % n)
            self._gallery_btn_del.configure(text="Delete%s" % ((" (%d)" % n) if n else ""))
            self._gallery_btn_del.configure(state="normal" if n else "disabled")

    def _gallery_delete_selected(self):
        if not self._gallery_selected:
            return
        n = len(self._gallery_selected)
        ok = messagebox.askyesno(
            "Delete %d image%s" % (n, "" if n == 1 else "s"),
            "Delete %d selected image%s?\
            (n, "" if n == 1 else "s", "" if n == 1 else "s"))
        if not ok:
                                                    " (%d failed)" % failed if failed else ""))
        self._gallery_exit_select()
        # Refresh whichever gallery is currently visible.
        if getattr(self, "_gallery_frame_main", None) and self._gallery_frame_main.winfo_exists() \
                and self._gallery_main.winfo_exists():
            self._refresh_gallery_main()
        if getattr(self, "_gallery_frame", None) and self._gallery_frame.winfo_exists():
            self._refresh_gallery()

                                                    " (%d failed)" % failed if failed else ""))
        self._gallery_exit_select()
        # Refresh whichever gallery is currently visible.
        if getattr(self, "_gallery_frame_main", None) and self._gallery_frame_main.winfo_exists() \
                and self._gallery_main.winfo_exists():
            self._refresh_gallery_main()
        if getattr(self, "_gallery_frame", None) and self._gallery_frame.winfo_exists():
            self._refresh_gallery()


    def _build_settings_in_main(self):
        """Build settings content in the main area."""
        if hasattr(self, "_settings_main") and self._settings_main and self._settings_main.winfo_exists():
            try:
                self._settings_main.destroy()
            except Exception:
                pass
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

        # Model dropdown: show display name + checkpoint filename so the user
        # can distinguish models at a glance. The _on_model handler maps back
        # to the mode-specific params.
        self.model_values = list(MODELS.keys())
        self.model_menu = ctk.CTkOptionMenu(toolbar, values=self.model_values, font=self.FONT_NORMAL,
                                            variable=self.model_var,
                                            fg_color=BG_CARD_ALT,
                                            button_color=BORDER,
                                            button_hover_color=BRAND_HOVER,
                                            text_color=TEXT,
                                            dropdown_fg_color=DROPDOWN_FG,
                                            dropdown_text_color=DROPDOWN_TEXT,
                                            dropdown_hover_color=DROPDOWN_HOVER,
                                            command=self._on_model, width=220)
        self.model_menu.grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.model_tooltip = ToolTip(self.model_menu, *TOOLTIPS["Model"])
        # Show the checkpoint filename in the tooltip subtitle
        self._update_model_tooltip()

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

        # Build ALL three tab contents eagerly so switching never shows a blank
        # panel. Lazy building via _tab_callbacks was unreliable (debounce/lock
        # could skip the first build, leaving the user staring at an empty tab).
        self._build_txt2img_tab()
        self._build_img2img_tab()
        self._build_upscale_tab()
        self._tab_built = {"Text to Image": True, "Image to Image": True,
                           "Upscale": True}

        # Set the initial tab without triggering debounce
        self.current_tab = "txt2img"
        self._last_tab_switch = 0
        self.txt2img_tab = self.tabview.tab("Text to Image")
        self.img2img_tab = self.tabview.tab("Image to Image")
        self.upscale_tab = self.tabview.tab("Upscale")

        # Preview window (right column of Generate view)
        self._build_preview_pane()

        # Header gradient image
        self._header_img = None
        self.header = ctk.CTkLabel(self.top, text="", height=56)
        self.header.grid(row=2, column=0, columnspan=1, padx=0, pady=(2, 0), sticky="nsew")

        # Bind tab changes via the proper CTkTabview command (fires AFTER the
        # internal tab switch, so the visible panel actually changes).
        self.tabview.configure(command=self._on_tab)
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
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self.prompt_entry = ctk.CTkTextbox(sf, height=60, font=ctk.CTkFont(size=10),
                                           fg_color=BG_CARD_ALT, text_color=TEXT)
        self.prompt_entry.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="nsew")
        self._apply_cursor_style(self.prompt_entry)
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
        swap_btn = ctk.CTkButton(sf, text="⇄ Swap Width & Height", font=self.FONT_SMALL_BOLD, height=24,
                                 fg_color=BG_CARD_ALT, hover_color=BRAND_HOVER, text_color=TEXT,
                                 command=self._swap_dimensions)
        swap_btn.grid(row=r, column=0, padx=10, pady=(2, 6), sticky="w")
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
            if getattr(self, '_tab_switch_lock', False):
                return
            if time.time() - getattr(self, '_last_tab_switch', 0) < 0.15:
                return
            self._tab_switch_lock = True
            self._last_tab_switch = time.time()
            try:
                if not name:
                    if hasattr(self, 'notebook') and self.notebook:
        t.grid_rowconfigure(0, weight=1)
        sf = ctk.CTkScrollableFrame(t, fg_color=BG_CARD, corner_radius=10)
        sf.grid(row=0, column=0, padx=16, pady=(8, 16), sticky="nsew")
        enable_auto_hide_scrollbar(sf)
        sf.grid_columnconfigure(0, weight=1)

        self.input_preview = ctk.CTkLabel(sf, text="No input selected", height=120,
                                          corner_radius=8, fg_color=BG_CARD_ALT,
                                          text_color=TEXT_MUTED)
        self.input_preview.grid(row=1, column=0, padx=10, pady=(6, 0), sticky="ew")
        self._make_drop_zone(sf, self.input_preview, self._stage_input)
        # Make the visible preview box itself clickable + a drag-drop target so
        # the user can click it to browse OR drop a dragged preview onto it.
        self.input_preview.bind("<Button-1>", lambda e: self._stage_input(
            filedialog.askopenfilename(title="Select Image",
                filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")]) or ""))
        self._register_drop_target(self.input_preview,
            lambda pil, path: self._stage_pil(pil, self.input_preview, "img2img"))

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
            fmt = self.vars.get(mode, {}).get("format")
            fmt_val = fmt.get() if fmt else "PNG"
            if fmt_val == "Game Texture (TGA)":
                self._convert_to_game_texture(out_path)
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

        self.input_preview = ctk.CTkLabel(sf, text="No input selected", height=120,
                                          corner_radius=8, fg_color=BG_CARD_ALT,
                                          text_color=TEXT_MUTED)
        self.input_preview.grid(row=1, column=0, padx=10, pady=(6, 0), sticky="ew")
        self._make_drop_zone(sf, self.input_preview, self._stage_input)
        # Make the visible preview box itself clickable + a drag-drop target so
        # the user can click it to browse OR drop a dragged preview onto it.
        self.input_preview.bind("<Button-1>", lambda e: self._stage_input(
            filedialog.askopenfilename(title="Select Image",
                filetypes=[("Image", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")]) or ""))
        self._register_drop_target(self.input_preview,
            lambda pil, path: self._stage_pil(pil, self.input_preview, "img2img"))

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
                used = int(pct * 100)
                # Update the VRAM readout in the status bar (main thread safe)
                try:
                    if hasattr(self, "status_vram") and self.status_vram.winfo_exists():
                        self.root.after(0, lambda v=used: self.status_vram.configure(
                            text="%d%% used" % v))
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
        self._render_settings_panel(sf)


    def _on_tab(self, name=None):

        import time
        try:
            if getattr(self, '_tab_switch_lock', False):
                return
            if time.time() - getattr(self, '_last_tab_switch', 0) < 0.15:
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
                # Normalize: if name is a CTkFrame (tab object), get its string name
                if not isinstance(name, str):
                    try:
                        name = str(name)
                    except Exception:
                        name = None
                tab_map = {
                    "Text to Image": "txt2img", "txt2img": "txt2img",
                    "Image to Image": "img2img", "img2img": "img2img",
                    "Upscale": "upscale", "upscale": "upscale"
                }
                self.current_tab = tab_map.get(str(name), "txt2img")
            finally:
                self._tab_switch_lock = False
        except Exception as e:
            self._tab_switch_lock = False
                                        "model": ["LastNode", 0], "positive": ["POS", 0],
                                        "negative": ["NEG", 0], "latent_image": ["EmptyLatent", 0]}},
                "POS": {"class_type": "CLIPTextEncode",
                        "inputs": {"text": prompt_text, "clip": ["LastNode", 1]}},
                "NEG": {"class_type": "CLIPTextEncode",
                        "inputs": {"text": neg_text, "clip": ["LastNode", 1]}},
                "VAEDecode": {"class_type": "VAEDecode",
                              "inputs": {"samples": ["KSampler", 0], "vae": ["LastNode", 2]}},
                "SaveImage": {"class_type": "SaveImage",
        started it manually) and connect to it instead of spawning a duplicate.
        Only one server instance should ever own port 8188.
        """
        try:
            r = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _fetch_server_model(self):
        """Query the live ComfyUI server for the currently-loaded checkpoint.

        ComfyUI exposes loaded models via /object_info/CheckpointLoaderSimple.
        We can't know exactly WHICH .safetensors is loaded from that, but we
        can confirm a model is loaded. The true source-of-truth is the app's
        own selection + symlink state, so we cross-check both.
        """
        try:
            r = requests.get(COMFYUI_URL + "/object_info/CheckpointLoaderSimple", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        return False

    def _start_backend(self):
        try:
            # ---- Single-server guard: detect an already-running ComfyUI ----
            # If something is already serving on 8188 (user launched ComfyUI
            # manually, or a previous app instance is alive), CONNECT to it
            # instead of spawning a duplicate process that will collide.
            if self._is_server_running():
                self._set_status("Connected to existing ComfyUI server")
                self.server_owned = False  # we did NOT start this server
                self.root.after(2000, self._refresh_model_status)
                self.root.after(3000, self._start_header_gradient)
                return
            self.server_owned = True
            # ---------------------------------------------------------------
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
                        self.root.after(2000, self._refresh_model_status)
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
                used = int(pct * 100)
                # Update the VRAM readout in the status bar (main thread safe)
                try:
                    if hasattr(self, "status_vram") and self.status_vram.winfo_exists():
                        self.root.after(0, lambda v=used: self.status_vram.configure(
                            text="%d%% used" % v))
                except Exception:
                    pass
                if pct > 0.95:
                    self._set_status("VRAM critical (%d%%) - wait for VRAM to clear" % used)
                    last_warned = pct
                elif pct > 0.85 and last_warned == 0:
                    self._set_status("Server online (VRAM %d%% used)" % used)
                    last_warned = pct
                elif pct < 0.80 and last_warned > 0:
                    last_warned = 0
            except Exception:
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
            return
        self._last_generate = time.time()
        self._generate_lock = True
        self._cancel_requested = False
        # Make Cancel reachable IMMEDIATELY (during build/model-load/POST) so the
        # user can abort a long synchronous phase instead of a dead disabled button.
        if hasattr(self, 'gen_btn') and self.gen_btn and self.gen_btn.winfo_exists():
            self.gen_btn.configure(text="Cancel", state="normal", command=self._cancel_generate)
        try:
            cfg = 6.5
        try:
            seed = int(m["seed"].get())
        except Exception:
            seed = 0
        try:
            batch = int(m["batch"].get())
        except Exception:
            batch = 1
        if seed == 0:
            seed = random.randint(1, 2**32 - 1)
            seed = random.randint(1, 2**32 - 1)
        batch = int(m["batch"].get())
        if mode == "img2img" and hasattr(self, "img2img_prompt_entry"):
            prompt_text = self.img2img_prompt_entry.get("1.0", "end").strip()
            neg_text = self.img2img_neg_entry.get("1.0", "end").strip()
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                wf, ckpt = self._build_workflow(target_mode)
                if not wf:
                    # No-input abort (img2img/upscale): status already set, release lock.
                    self._generate_lock = False
                    if hasattr(self, "gen_btn") and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                if not self._ensure_model_loaded(ckpt):
                    # Clear status already set by _ensure_model_loaded; re-enable button.
                    self._generate_lock = False
                    if hasattr(self, "gen_btn") and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self._set_status("Generating...")
                # ComfyUI 0.29 expects `prompt` as a JSON *object*, not a string.
                # Passing json.dumps(wf) makes it a str and every generation 500s
                # with "'str' object has no attribute 'items'". Send the dict.
                payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored\
                r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
                if r.status_code != 200:
                    # Extract the real node error from ComfyUI's 400/500 response
                    detail = ""
                    try:
                        body = r.json()
                        if "node_errors" in body:
                            for nid, nerr in body["node_errors"].items():
                                for e in nerr.get("errors", []):
                                    detail = e.get("details", "") or e.get("message", "")
                                    if detail: break
                        elif "error" in body and isinstance(body["error"], dict):
                            detail = body["error"].get("message", "")
                    except Exception:
                        detail = r.text[:120]
                    self._set_status("Queue failed: %s" % (detail[:80] or ("HTTP %d" % r.status_code)))
                    if hasattr(self, 'gen_btn') and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self.last_prompt_id = r.json().get("prompt_id")
                self._gen_mode = self.current_tab
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Cancel", command=self._cancel_generate)
                self._poll_attempts = 0
                self._poll_after_id = self.root.after(200, self._poll_history)
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
        """Stop a running generation. Posts /interrupt to ComfyUI, cancels the
        pending poll loop, and restores the Generate button. Guarded against a
        None prompt id (clicked during the synchronous build/POST phase)."""
        if not self.root or not self.root.winfo_exists():
            return
        self._cancel_requested = True
        # Cancel any pending poll tick so it can't fight the reset.
        if getattr(self, '_poll_after_id', None) is not None:
            try:
                self.root.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        if getattr(self, 'last_prompt_id', None):
            try:
        target = os.path.join(CKPT_DIR, model_name)
        source = os.path.join(ARCHIVE_DIR, model_name)
        # Already present and valid?
        if os.path.exists(target):
            return True
        # Need to (re)create the symlink.
        try:
            os.makedirs(CKPT_DIR, exist_ok=True)
            # Remove a stale/dangling link first.
            if os.path.islink(target):
                os.remove(target)
            os.symlink(source, target)
        except Exception as e:
            if os.path.exists(source):
                self._set_status("Model link error: %s" % str(e)[:40])
            else:
                self._set_status("Model file missing in archive: %s" % model_name)
            return False
        # Verify the link actually resolves (symlink privilege / path issues).
        if not os.path.exists(target):
            self._set_status("Model link broken: %s" % model_name)
            return False
        self._set_status("Model loaded: %s" % model_name[:20])
        return True

    def _cleanup_symlinks(self):
        """Remove model symlinks from checkpoints dir on exit."""
        try:
            if os.path.isdir(CKPT_DIR):
                for f in os.listdir(CKPT_DIR):
                    fp = os.path.join(CKPT_DIR, f)
            pass
        self._poll_after_id = self.root.after(500, self._poll_history)

    def _show_image(self, img_meta):
        mode = getattr(self, "_gen_mode", self.current_tab)
        try:
            fn = img_meta.get("filename")
            sub = img_meta.get("subfolder", "")
            url = COMFYUI_URL + "/view?filename=" + fn + "&subfolder=" + sub + "&type=output"
            r = requests.get(url, timeout=10)
        self._poll_after_id = self.root.after(500, self._poll_history)

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
                    if f.endswith(".safetensors") and os.path.islink(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
        except Exception:
            pass

    def _vram_critical(self, threshold=0.90):
        """Return True if VRAM usage exceeds threshold (best-effort; False on any error)."""
        """Symlink the selected model into models/checkpoints/ on-demand.

        Returns True if the checkpoint is reachable (real file or live link),
        False otherwise. Callers should abort the generate if this returns
        False so the user gets a clear reason instead of a bare HTTP 500.
        """
        if not model_name:
            self._set_status("No model selected")
            return False
        target = os.path.join(CKPT_DIR, model_name)
        source = os.path.join(ARCHIVE_DIR, model_name)
        # Already present and valid?
        if os.path.exists(target):
            return True
        # Need to (re)create the symlink.
        try:
            os.makedirs(CKPT_DIR, exist_ok=True)
            # Remove a stale/dangling link first.
            if os.path.islink(target):
                os.remove(target)
            os.symlink(source, target)
        except Exception as e:
            if os.path.exists(source):
                self._set_status("Model link error: %s" % str(e)[:40])
            else:
                self._set_status("Model file missing in archive: %s" % model_name)
            return False
        # Verify the link actually resolves (symlink privilege / path issues).
        if not os.path.exists(target):
            self._set_status("Model link broken: %s" % model_name)
            return False
            logging.info("Generate debounced")
            return
        if getattr(self, '_generate_lock', False):
            logging.info("Generate locked")
            return
        self._last_generate = time.time()
        self._generate_lock = True
        self._cancel_requested = False
        # Make Cancel reachable IMMEDIATELY (during build/model-load/POST) so the
                    if f.endswith(".safetensors") and os.path.islink(fp):
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
        except Exception:
            pass

    def _vram_critical(self, threshold=None):
        """Return True if VRAM usage exceeds threshold (best-effort; False on any error)."""
        try:
            val = self.vram_threshold_var.get() if hasattr(self, "vram_threshold_var") else "90%"
            if "Disabled" in val:
                return False
            if threshold is None:
                if "95%" in val: threshold = 0.95
                elif "85%" in val: threshold = 0.85
                elif "80%" in val: threshold = 0.80
                else: threshold = 0.90
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
                elif "80%" in val: threshold = 0.80
                else: threshold = 0.90
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
            used_pct = 1 - (free / total)
            if used_pct > threshold:
                # Smart VRAM Recovery: Automatically attempt /free to clear PyTorch cache
                try:
                    requests.post(COMFYUI_URL + "/free", json={"unload_models": True, "free_memory": True}, timeout=3)
                    time.sleep(0.5)
                    r2 = requests.get(COMFYUI_URL + "/system_stats", timeout=3)
                    if r2.status_code == 200 and r2.json().get("devices"):
                        d2 = r2.json()["devices"][0]
                        tot2 = d2.get("vram_total", 0) or 0
                        fr2 = d2.get("vram_free", 0) or 0
                        if tot2 > 0:
                            used_pct = 1 - (fr2 / tot2)
                except Exception:
                    pass
            return used_pct > threshold
        except Exception:
            return False

    def _start_generate(self, mode=None):
        import time
        logging.info("Generate button clicked")
        if mode and mode not in ("txt2img", "img2img", "upscale"):
            self._set_status("Error: unknown mode '%s'" % mode)
            return
        # Active VRAM guard: never OOM the host — defer when VRAM is critical.
        if self._vram_critical():
            self._set_status("VRAM limit exceeded - wait for VRAM to clear or adjust limit in Settings")
                # Cancel during the synchronous build phase must actually stop us
                # before we POST. Without this guard a cancel issued while the
                # workflow is being built still POSTs and starts an uncancelable
                # generation (the "Cancel doesn't work" bug).
                if getattr(self, "_cancel_requested", False):
                    self._generate_lock = False
                    if hasattr(self, "gen_btn") and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                wf, ckpt = self._build_workflow(target_mode)
                if not wf:
                    # No-input abort (img2img/upscale): status already set, release lock.
                    self._generate_lock = False
                    if hasattr(self, "gen_btn") and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                if not self._ensure_model_loaded(ckpt):
                    # Clear status already set by _ensure_model_loaded; re-enable button.
                    self._generate_lock = False
                    if hasattr(self, "gen_btn") and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self._set_status("Generating...")
                # ComfyUI 0.29 expects `prompt` as a JSON *object*, not a string.
                # Passing json.dumps(wf) makes it a str and every generation 500s
                # with "'str' object has no attribute 'items'". Send the dict.
                payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored\
                r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
                if r.status_code != 200:
                    # Extract the real node error from ComfyUI's 400/500 response
                    detail = ""
                    try:
                        body = r.json()
                        if "node_errors" in body:
                            for nid, nerr in body["node_errors"].items():
                                for e in nerr.get("errors", []):
                                    detail = e.get("details", "") or e.get("message", "")
                                    if detail: break
                        elif "error" in body and isinstance(body["error"], dict):
                            detail = body["error"].get("message", "")
                    except Exception:
                        detail = r.text[:120]
                    self._set_status("Queue failed: %s" % (detail[:80] or ("HTTP %d" % r.status_code)))
                    if hasattr(self, 'gen_btn') and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self.last_prompt_id = r.json().get("prompt_id")
                self._gen_mode = self.current_tab
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    return
                self._set_status("Generating...")
                # ComfyUI 0.29 expects `prompt` as a JSON *object*, not a string.
                # Passing json.dumps(wf) makes it a str and every generation 500s
                # with "'str' object has no attribute 'items'". Send the dict.
                payload = {"prompt": wf, "client_id": "hermes_comfyui_uncensored\
                r = requests.post(COMFYUI_URL + "/prompt", json=payload, timeout=10)
                if r.status_code != 200:
                    # Extract the real node error from ComfyUI's 400/500 response
                    detail = ""
                    try:
                        body = r.json()
                        if "node_errors" in body:
                            for nid, nerr in body["node_errors"].items():
                                for e in nerr.get("errors", []):
                                    detail = e.get("details", "") or e.get("message", "")
                                    if detail: break
                        elif "error" in body and isinstance(body["error"], dict):
                            detail = body["error"].get("message", "")
                    except Exception:
                        detail = r.text[:120]
                    self._set_status("Queue failed: %s" % (detail[:80] or ("HTTP %d" % r.status_code)))
                    if hasattr(self, 'gen_btn') and self.gen_btn:
                        self.gen_btn.configure(state="normal", text="Generate  (Ctrl+E)")
                    return
                self.last_prompt_id = r.json().get("prompt_id")
                self._gen_mode = self.current_tab
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Cancel", command=self._cancel_generate)
                self._poll_attempts = 0
                self._poll_after_id = self.root.after(200, self._poll_history)
            except Exception as e:
                logging.error("Generate error: %s", e)
                self._set_status("Generate error: %s" % str(e)[:40])
                if hasattr(self, 'gen_btn') and self.gen_btn:
                    self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal")
        except Exception as e:
            logging.error("Generate outer error: %s", e)
            self._set_status("Generate error: %s" % str(e)[:40])
            if hasattr(self, 'gen_btn') and self.gen_btn:
            self._set_status("Generate error: %s" % str(e)[:40])
            if hasattr(self, 'gen_btn') and self.gen_btn:
                self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal")
        finally:
            self._generate_lock = False

    def _cancel_generate(self):
        """Stop a running generation. Posts /interrupt to ComfyUI, cancels the
        pending poll loop, and restores the Generate button. Guarded against a
        None prompt id (clicked during the synchronous build/POST phase)."""
        if not self.root or not self.root.winfo_exists():
            return
        self._cancel_requested = True
        # Cancel any pending poll tick so it can't fight the reset.
        if getattr(self, '_poll_after_id', None) is not None:
            try:
                self.root.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        if getattr(self, 'last_prompt_id', None):
            try:
                requests.post(COMFYUI_URL + "/interrupt", timeout=5)
            except Exception:
                pass
        self._poll_attempts = 100
        self._gallery_exit_select()
        if hasattr(self, "progress_bar") and self.progress_bar and self.progress_bar.winfo_exists():
            self.progress_bar.set(0.0)
        if hasattr(self, "progress_label") and self.progress_label and self.progress_label.winfo_exists():
            self.progress_label.configure(text="Cancelled", text_color=TEXT_MUTED)
        if hasattr(self, 'gen_btn') and self.gen_btn.winfo_exists():
            self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
        self._generate_lock = False
        self._set_status("Cancelled")

    def _poll_history(self):
        """FIX: poll ComfyUI history with retries until done, error, or timeout."""
        if getattr(self, '_cancel_requested', False):
            self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
            return
        if self._poll_attempts > 150:
            self._set_status("Polling timed out")
            if hasattr(self, "progress_bar") and self.progress_bar and self.progress_bar.winfo_exists():
                self.progress_bar.set(0.0)
            if hasattr(self, "progress_label") and self.progress_label and self.progress_label.winfo_exists():
                self.progress_label.configure(text="Timed out", text_color=TEXT_MUTED)
            self.gen_btn.configure(text="Generate  (Ctrl+E)", state="normal", command=self._start_generate)
            return
        self._poll_attempts += 1
        pct = min(0.95, self._poll_attempts / 30.0)
        if hasattr(self, "progress_bar") and self.progress_bar and self.progress_bar.winfo_exists():
            self.progress_bar.set(pct)
        if hasattr(self, "progress_label") and self.progress_label and self.progress_label.winfo_exists():
            self.progress_label.configure(text="Generating... (%d%%)" % int(pct * 100), text_color=BRAND)
        try:
            r = requests.get(COMFYUI_URL + "/history", timeout=5)
            if r.status_code == 200:
                hist = r.json()
                for item_id, item in hist.items():
                    status = item.get("status", {})
                    if status.get("completed") and item_id == self.last_prompt_id:
                        outs = item.get("outputs", {})
                        found_img = False
                        for node_id, node_out in outs.items():
                            for img_data in node_out.get("images", []):



















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
            if hasattr(self, "progress_bar") and self.progress_bar and self.progress_bar.winfo_exists():
                self.progress_bar.set(1.0)
            if hasattr(self, "progress_label") and self.progress_label and self.progress_label.winfo_exists():
                self.progress_label.configure(text="Generation complete!", text_color="#A7F3D0")
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
                return
            # Show the FULL message (no destructive 33-char truncation that cut
            # off the end of longer status text). Cap only as a safety net.
            truncated = msg if len(msg) <= 200 else msg[:197] + "..."
            if level >= logging.WARNING:
                self.status_label.configure(text=truncated, text_color=("#FFAAAA", "#FFAAAA"))
            else:
                self.status_label.configure(text=truncated, text_color=TEXT)
        except Exception:
            pass

    def on_close(self):
        self._running = False
        # Only terminate the backend if we started it. If we detected and
        # connected to an externally-launched ComfyUI (e.g. the user ran the







































        mid.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mid, text="VRAM", font=self.FONT_SMALL_BOLD,
                     text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w")
        self.status_vram = ctk.CTkLabel(mid, text="—", font=self.FONT_NORMAL,
                                        text_color=TEXT)
        self.status_vram.grid(row=1, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(mid, text="Initializing...", font=self.FONT_NORMAL,
                                         text_color=TEXT)
        self.status_label.grid(row=2, column=0, sticky="w", pady=(4, 0))

        # Right: recent thumbnails strip  — unified to BG_CARD so it blends
        # seamlessly into the status bar instead of reading as a dark "back
        # square" block that distracts next to the Save History row above it.
        self.thumb_frame = ctk.CTkScrollableFrame(bar, fg_color=BG_CARD,
                                                 corner_radius=8, width=220)
        self.thumb_frame.grid(row=0, column=2, padx=10, pady=6, sticky="nsew")
        self.thumb_frame.grid_columnconfigure(0, weight=1)
        enable_auto_hide_scrollbar(self.thumb_frame)
        self._thumb_count = 0
        self._update_status_info()
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
        # Marshal the GUI write to the main thread. If we are already on the
        # main thread this still uses after(0) which is safe and cheap.
        self.root.after(0, self._set_status_gui, msg, level)

    def _set_status_gui(self, msg, level):
        pane.grid_columnconfigure(0, weight=1)
        pane.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(pane, text="Preview", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self.preview_big = ctk.CTkLabel(pane,
            text="No image yet.\
            height=360, corner_radius=8, fg_color=BG_CARD_ALT,
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=11), justify="center")
        self.preview_big.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")
        self.preview_big.grid_propagate(False)
        # Drag the generated result into the img2img / upscale input box.
        # Click (no drag) still opens the full image.
        self._make_drag_source(self.preview_big,
                               get_pil=lambda: getattr(self, "current_pil", None),
                               get_path=lambda: getattr(self, "current_pil_path", None),
                               on_click=self._open_last_preview)

            except Exception:
                pass
        self._cleanup_symlinks()
        self.root.destroy()

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self.root, height=100, fg_color=BG_CARD, corner_radius=10)
        bar.grid(row=3, column=1, padx=12, pady=(0, 12), sticky="nsew")
        bar.grid_columnconfigure(0, weight=1)   # model/last-output info
        bar.grid_columnconfigure(1, weight=1)   # VRAM / status
        bar.grid_columnconfigure(2, weight=0, minsize=220)  # recent thumbnails
        bar.grid_rowconfigure(0, weight=1)

        # Left: current model + last output path
        info = ctk.CTkFrame(bar, fg_color="transparent")
        info.grid(row=0, column=0, padx=10, pady=6, sticky="nsew")
        info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(info, text="Active Model", font=self.FONT_SMALL_BOLD,
                     text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w")
        self.status_model = ctk.CTkLabel(info, text="—", font=self.FONT_NORMAL,
                                         text_color=TEXT)
        self.status_model.grid(row=1, column=0, sticky="w")
        self.status_server_source = ctk.CTkLabel(info, text="—", font=self.FONT_SMALL,
                                                  text_color=TEXT_MUTED)
        self.status_server_source.grid(row=2, column=0, sticky="w", pady=(2, 0))
        ctk.CTkLabel(info, text="Last Output", font=self.FONT_SMALL_BOLD,
                     text_color=TEXT_MUTED).grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.status_last = ctk.CTkLabel(info, text="No images yet", font=self.FONT_NORMAL,
                                        text_color=TEXT_MUTED)
        self.status_last.grid(row=4, column=0, sticky="w")

        # Middle: VRAM + live status
        mid = ctk.CTkFrame(bar, fg_color="transparent")
        mid.grid(row=0, column=1, padx=10, pady=6, sticky="nsew")
        mid.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mid, text="VRAM", font=self.FONT_SMALL_BOLD,
                     text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w")
        self.status_vram = ctk.CTkLabel(mid, text="—", font=self.FONT_NORMAL,
                                        text_color=TEXT)
        self.status_vram.grid(row=1, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(mid, text="Initializing...", font=self.FONT_NORMAL,

















































            self._set_status("Log window error: %s" % str(e)[:30])

    def _save_history_simple(self):
        self._save_history(self.current_tab, "history_snapshot.json")
        self._set_status("History saved (%d entries)" % len(self.history))

    # ------------------------------------------------------------------
    def _update_model_tooltip(self):
        """Update the Model dropdown's hover-tooltip text to show the checkpoint
        filename for the selected model plus a summary of all models.

        FIX: previously this created a NEW ToolTip on every call and forced it
        open via .show(), which left a stuck floating window that never
        dismissed (the "window description" bug). We now update the text of the
        single existing hover tooltip (self.model_tooltip, bound at build time)
        and never force-show it. Any stray tooltip from an older build is

























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
            # Immediately update the active-model status bar display
            self._update_status_info()
            self._update_model_tooltip()
        except Exception as e:
            logging.error("Model change error: %s", e)
            self._set_status(f"Error: {str(e)[:30]}")

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
                    # Preset values take precedence over the model defaults.
                    m["width"].set(str(p.get("w", model["w"])))
                    m["height"].set(str(p.get("h", model["h"])))
                    m["steps"].set(str(p.get("steps", model["steps"])))
                    m["cfg"].set(str(p.get("cfg", model["cfg"])))
                self.prompt_entry.delete("1.0", "end")
                self.prompt_entry.insert("1.0", p["prompt"])
                self.neg_entry.delete("1.0", "end")
                fp = os.path.join(OUTPUT_DIR, f)
                try:
                    img = Image.open(fp).convert("RGB")
                    img.thumbnail((56, 56))
                    tkimg = ctk.CTkImage(light_image=img, dark_image=img, size=(56, 56))
                    lbl = ctk.CTkLabel(self.thumb_frame, text="", image=tkimg,
                                      corner_radius=4, fg_color=BG_CARD)
                    lbl._img = tkimg
                    lbl.bind("<Button-1>", lambda e, fp=fp: os.startfile(fp))
                    lbl.grid(row=0, column=self._thumb_count, padx=2, pady=2)
                    self._thumb_count += 1
                except Exception:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _start_header_gradient(self):
        """FIX: initialize hue and kick off the header gradient animation loop."""
        self._hue = 0.0
        self._animate_gradient()

    def _paint_background(self):
        """Paint a full-window gradient so there is never a black void / empty
        space. Uses a CTkImage label sized to the root, refreshed on resize."""
        try:
            w = max(2, self.root.winfo_width())
            h = max(2, self.root.winfo_height())
            self._bg_w, self._bg_h = w, h
            if mode == "light":
                solid = (240, 240, 250)
            else:
                solid = (24, 18, 38)  # #181226 deep obsidian purple
            img = ctk.CTkImage(light_image=Image.new("RGB", (w, h), solid),
                               dark_image=Image.new("RGB", (w, h), solid),
                               size=(w, h))
            if self._bg_label is None or not self._bg_label.winfo_exists():
                self._bg_label = ctk.CTkLabel(self.root, text="", image=img)
                self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self._bg_label.configure(image=img)
            self._bg_label.lower()  # keep it behind all content
        except Exception:
            pass

    def _on_root_configure(self, _e=None):
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            # Only repaint when the SIZE changes. Moving the window fires
            # <Configure> on every pixel of motion but the size is identical,
            # so we skip the expensive gradient repaint and avoid the lag.
            if getattr(self, '_bg_w', 0) == w and getattr(self, '_bg_h', 0) == h:
                return
            self._bg_w, self._bg_h = w, h
            if not hasattr(self, '_bg_job') or self._bg_job is None:
                self._bg_job = self.root.after(150, self._delayed_bg_paint)
        except Exception:
            pass

    def _delayed_bg_paint(self):
        try:
            self._bg_job = None
            self._paint_background()
        except Exception:
            pass

            w = max(10, self.root.winfo_width() - 220)
            h = 56
            c0 = (34, 34, 48)
            c1 = (58, 58, 80)
            grad = make_gradient(w, h, c0, c1, angle=90)
            photo = ctk.CTkImage(light_image=grad, dark_image=grad, size=(w, h))
            self._header_img = photo
            self.header.configure(image=photo)
        except Exception:
            pass
        # Intentionally do NOT reschedule — eliminates the perpetual repaint lag.

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
            if hasattr(self, "_last_output_file") and self._last_output_file and os.path.exists(self._last_output_file) and getattr(self, "current_pil", None) is not None:
                os.startfile(self._last_output_file)
            elif getattr(self, "current_pil", None) is not None and getattr(self, "current_pil_path", None) and os.path.exists(self.current_pil_path):
                os.startfile(self.current_pil_path)
            else:
                self._set_status("No generated preview yet — click Generate (Ctrl+E) to create an image")
        except Exception as e:
            logging.error("Open preview error: %s", e)

    # ------------------------------------------------------------------
    def _build_preview_pane(self):
        """Large preview window in the right column of the Generate view."""
        pane = ctk.CTkFrame(self.top, fg_color=BG_CARD, corner_radius=10)
        pane.grid(row=0, column=1, rowspan=3, padx=(12, 0), pady=(8, 16), sticky="nsew")
        pane.grid_columnconfigure(0, weight=1)
        pane.grid_rowconfigure(2, weight=1)

        # Header Title
        ctk.CTkLabel(pane, text="Preview", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")

        # Progress bar + status readout (real-time generation feedback)
        p_frame = ctk.CTkFrame(pane, fg_color="transparent")
        p_frame.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="ew")
        p_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(p_frame, height=8, fg_color=BG_CARD_ALT, progress_color=BRAND, corner_radius=4)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(2, 2))
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(p_frame, text="Ready", font=self.FONT_SMALL, text_color=TEXT_MUTED)
        self.progress_label.grid(row=1, column=0, sticky="w")

        # Big Preview Box
        self.preview_big = ctk.CTkLabel(pane,
            text="No image yet.\
            height=360, corner_radius=8, fg_color=BG_CARD_ALT,
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=11), justify="center")
        self.preview_big.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="nsew")
        self.preview_big.grid_propagate(False)

        self._make_drag_source(self.preview_big,
                               get_pil=lambda: getattr(self, "current_pil", None),
                               get_path=lambda: getattr(self, "current_pil_path", None),
                               on_click=self._open_last_preview)

        self._preview_thumb_count = 0
            # Immediately update the active-model status bar display
            self._update_status_info()
            self._update_model_tooltip()
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
                    # Preset values take precedence over the model defaults.
                    m["width"].set(str(p.get("w", model["w"])))
                    m["height"].set(str(p.get("h", model["h"])))
                    m["steps"].set(str(p.get("steps", model["steps"])))
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
            win.transient(self.root)
            win.attributes("-topmost", True)
            win.lift()  # ensure it's visible above the main window
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




































































































































































































































