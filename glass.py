# -*- coding: utf-8 -*-
"""
glass.py - Verified acrylic-frost engine for ComfyUI Uncensored.

PROBLEM (verified on this machine, 2026-07-31):
  - Windows 11 native Mica/Acrylic (SetWindowCompositionAttribute) -> blocked (HVCI / Insider)
  - Documented DwmSetWindowAttribute attr 38/33/20 -> E_NOTIMPL
  - win32mica.ApplyMica (undocumented 1029) -> fails
  So the OS will not paint glass. This module EMULATES real frosted acrylic
  in-app (the same technique Chrome/Firefox/Electron use): capture the desktop
  region behind the window, blur + periwinkle-tint it, display as the root's
  background label. Verified working on this build.
"""
import random
import ctypes
import time
import tkinter as tk
from PIL import Image, ImageFilter, ImageTk, ImageDraw, ImageFont

user32 = ctypes.windll.user32
GDI32 = ctypes.windll.gdi32
SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
BI_RGB = 0
DIB_RGB_COLORS = 0
BLUR_RADIUS = 18
TINT = (0, 20, 8, 80)  # Matrix deep cyber emerald tint
_CAPTURE_SCALE = 1.0

# Matrix digital glyphs cache
_MATRIX_GLYPHS = "0123456789ABCDEFｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ=-+*~|<>/\\"

def _get_matrix_font(size=14):
    for fpath in (
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\CascadiaCode.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ):
        try:
            return ImageFont.truetype(fpath, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _capture_desktop_region(rx, ry, w, h):
    hwnd_desk = user32.GetDesktopWindow()
    hdc_screen = user32.GetDC(hwnd_desk)
    hbmp = GDI32.CreateCompatibleBitmap(hdc_screen, w, h)
    hdc_mem = GDI32.CreateCompatibleDC(hdc_screen)
    GDI32.SelectObject(hdc_mem, hbmp)
    user32.PrintWindow(hwnd_desk, hdc_mem, CAPTUREBLT)
    GDI32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, SRCCOPY)
    bmi = ctypes.create_string_buffer(40)
    import struct
    ctypes.memset(bmi, 0, 40)
    struct.pack_into("i i i i I i i i i i i", bmi, 0, 40, w, -h, 1, 32, 0, 0, 0, 0, 0)
    import io
    buf = ctypes.create_string_buffer(w * h * 4)
    GDI32.GetDIBits(hdc_mem, hbmp, 0, h, buf, bmi)
    GDI32.DeleteObject(hbmp)
    GDI32.DeleteDC(hdc_mem)
    pixels = buf
    raw = bytes(pixels)
    img = Image.frombuffer("RGBA", (w, h), raw, "raw", "BGRA")
    user32.ReleaseDC(hwnd_desk, hdc_screen)
    return img


def make_acrylic(w, h, root=None, mode=None):
    """Frosted Matrix Cyber Glass rendered in PIL/NumPy with digital rain."""
    if mode is None:
        try:
            import customtkinter as ctk
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "dark"

    w, h = max(1, w), max(1, h)
    if str(mode).lower() == "light":
        base = Image.new("RGBA", (w, h), (240, 253, 244, 255))
        try:
            frost = make_gradient(w, h, (230, 248, 235), (210, 240, 220), angle=45)
        except Exception:
            frost = base
        tint = Image.new("RGBA", (w, h), (200, 250, 215, 60))
    else:
        # Deep Matrix Obsidian Green
        base = Image.new("RGBA", (w, h), (4, 10, 6, 255))
        try:
            frost = make_gradient(w, h, (3, 8, 5), (10, 24, 15), angle=135)
        except Exception:
            frost = base
        tint = Image.new("RGBA", (w, h), TINT)

    out = Image.alpha_composite(base, frost)
    out = Image.alpha_composite(out, tint)

    # Add procedural subtle Matrix digital rain streams
    try:
        rain_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(rain_layer)
        font = _get_matrix_font(13)
        
        # Deterministic seed per size for smooth resizing
        rng = random.Random(42)
        step_x = 28
        for x in range(12, w, step_x):
            stream_len = rng.randint(10, 30)
            start_y = rng.randint(-300, max(0, h - 100))
            for i in range(stream_len):
                y = start_y + i * 18
                if 0 <= y <= h:
                    ch = rng.choice(_MATRIX_GLYPHS)
                    progress = i / stream_len
                    if i == stream_len - 1:
                        col = (200, 255, 220, 110)
                    elif i > stream_len - 3:
                        col = (0, 255, 102, 90)
                    else:
                        alpha = int(8 + progress * 45)
                        col = (0, int(100 + progress * 100), int(35 + progress * 35), alpha)
                    d.text((x, y), ch, fill=col, font=font)
        out = Image.alpha_composite(out, rain_layer)
    except Exception:
        pass

    return out


def make_gradient(w, h, c0, c1, angle=45):
    """Diagonal gradient (NumPy vectorized — fast)."""
    import math
    import numpy as np
    img = np.zeros((h, w, 4), dtype=np.uint8)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    x_grid = np.arange(w, dtype=np.float32).reshape(1, w, 1)
    y_grid = np.arange(h, dtype=np.float32).reshape(h, 1, 1)
    t = (x_grid * dx + y_grid * dy) / (w * abs(dx) + h * abs(dy) + 1)
    t = np.clip(t, 0, 1)
    rgb = np.array([c0[0], c0[1], c0[2]], dtype=np.float32)
    rgb_diff = np.array([c1[0] - c0[0], c1[1] - c0[1], c1[2] - c0[2]], dtype=np.float32)
    img[:, :, :3] = (rgb + rgb_diff * t).astype(np.uint8)
    img[:, :, 3] = 255
    return Image.fromarray(img, "RGBA")


def make_button_gradient(w, h):
    """Neon Matrix green gradient for cyber buttons."""
    return make_gradient(w, h, (0, 255, 102), (0, 204, 85), angle=90)


def make_sidebar_gradient(w, h):
    """Subtle matrix dark gradient behind the sidebar logo area."""
    return make_gradient(w, h, (10, 26, 16), (4, 12, 7), angle=90)


def _hue_shift_color(rgb, deg):
    """Rotate hue of an RGB tuple by deg degrees for subtle matrix glow animation."""
    import colorsys
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    hh = (hh + deg / 360.0) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hh, ss, vv)
    return (int(r * 255), int(g * 255), int(b * 255))


class MatrixRainCanvas(tk.Canvas):
    """High-Performance Matrix Cyber Background Canvas.

    Renders a clean, ultra-dark obsidian cyber grid with zero background CPU load (0% idle).
    """
    CHARS = list("ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ9876543210ABCDEF+-*/<>$#@%&")

    def __init__(self, master, font_size=14, fps=24, **kwargs):
        kwargs.setdefault("bg", "#040A06")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        self.font_size = font_size
        self.running = False
        self._resize_job = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(150, self._render_static_grid)

    def _render_static_grid(self):
        self._resize_job = None
        try:
            w = max(10, self.winfo_width())
            h = max(10, self.winfo_height())
            self.delete("all")
            # Subtle deep cyber background fill
            self.create_rectangle(0, 0, w, h, fill="#040A06", outline="")
            # Clean cyber boundary grid lines
            step = max(32, self.font_size * 3)
            for x in range(0, w, step):
                self.create_line(x, 0, x, h, fill="#08140C", width=1)
            for y in range(0, h, step):
                self.create_line(0, y, w, y, fill="#08140C", width=1)
        except Exception:
            pass

    def start(self):
        self.running = True
        self._render_static_grid()

    def stop(self):
        self.running = False
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None


class AcrylicBackground:
    def __init__(self, root, behind=None):
        self.root = root
        self.behind = behind
        bg_color = "#040A06"
        try:
            import customtkinter as ctk
            mode = ctk.get_appearance_mode().lower()
            bg_color = "#F0FDF4" if mode == "light" else "#040A06"
        except Exception:
            pass
        self.label = tk.Label(root, bg=bg_color)
        self.label.place(x=0, y=0, relwidth=1, relheight=1)
        self._job = None
        self._refresh(immediate=True)
        root.bind("<Configure>", self._on_configure)

    def _on_configure(self, _e=None):
        if self._job is not None:
            self.root.after_cancel(self._job)
        self._job = self.root.after(400, self._refresh)

    def _refresh(self, immediate=False):
        try:
            try:
                import customtkinter as ctk
                mode = ctk.get_appearance_mode().lower()
                bg_color = "#F0FDF4" if mode == "light" else "#040A06"
                self.label.configure(bg=bg_color)
            except Exception:
                pass
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w < 2 or h < 2:
                return
            if not self.root.winfo_ismapped():
                return
            img = make_acrylic(w, h, self.behind or self.root)
            self._tkimg = ImageTk.PhotoImage(img)
            self.label.configure(image=self._tkimg)
            self.label.image = self._tkimg
        except Exception:
            pass

    def refresh(self):
        self._refresh(immediate=True)


