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
    """High-Performance Authentic Matrix Digital Rain Canvas.

    Inspired by Project30Hub/Matrix-Digital-Rain, rendering cascading streams
    of glowing green Katakana, Latin glyphs, and digits with fade trails.
    """
    CHARS = list("ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-*/<>$#@%&")

    def __init__(self, master, font_size=14, fps=24, **kwargs):
        kwargs.setdefault("bg", "#000000")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        self.font_size = font_size
        self.fps = fps
        self.interval_ms = int(1000 / fps)
        self.running = False
        self._anim_job = None
        self.drops = []
        self._img_id = None
        self._photo = None
        self._pil_img = None
        self._draw = None
        self._last_canvas_size = None
        try:
            from PIL import ImageFont
            self._font = ImageFont.truetype("consola.ttf", self.font_size)
        except Exception:
            try:
                from PIL import ImageFont
                self._font = ImageFont.load_default()
            except Exception:
                self._font = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        if event is not None:
            new_size = (event.width, event.height)
            if self._last_canvas_size == new_size:
                return
            self._last_canvas_size = new_size
        w = max(50, self.winfo_width())
        h = max(50, self.winfo_height())
        cols = w // self.font_size + 1
        import random
        self.drops = [random.randint(-h // self.font_size, 0) for _ in range(cols)]
        try:
            from PIL import Image, ImageDraw, ImageTk
            self._pil_img = Image.new("RGB", (w, h), "#000000")
            self._draw = ImageDraw.Draw(self._pil_img)
            self._photo = ImageTk.PhotoImage(self._pil_img)
            self.delete("all")
            self._img_id = self.create_image(0, 0, image=self._photo, anchor="nw")
        except Exception:
            pass

    def _tick(self):
        if not self.running or self._draw is None:
            return
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        import random
        from PIL import Image, ImageDraw

        try:
            # Semi-transparent dark overlay (fading trail effect from Project30Hub/Matrix-Digital-Rain)
            fade = Image.new("RGBA", (w, h), (0, 0, 0, 28))
            self._pil_img.paste(Image.blend(self._pil_img.convert("RGBA"), fade, 0.16).convert("RGB"))
            self._draw = ImageDraw.Draw(self._pil_img)

            for i in range(len(self.drops)):
                char = random.choice(self.CHARS)
                x = i * self.font_size
                y = self.drops[i] * self.font_size

                # Bright glowing cyber green leading drop
                self._draw.text((x, y), char, font=self._font, fill=(0, 255, 102))

                # Reset to top randomly when passing bottom
                if y > h and random.random() > 0.975:
                    self.drops[i] = 0
                else:
                    self.drops[i] += 1

            self._photo.paste(self._pil_img)
        except Exception:
            pass

        if self.running:
            self._anim_job = self.after(self.interval_ms, self._tick)

    def start(self):
        if not self.running:
            self.running = True
            self._tick()

    def stop(self):
        self.running = False
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None


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


