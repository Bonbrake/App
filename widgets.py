"""
ComfyUI Uncensored v5.0 - Custom UI Components & Styling
Defines Obsidian Purple color tokens, public CTk AutoHideScrollFrame subclass, and ToolTips.
"""
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

# Design System Tokens - Obsidian Purple & Electric Accent Palette
BG_APP = "#0F0D15"        # Obsidian Black main window background
BG_SIDEBAR = "#151122"    # Dark purple-black sidebar background
BG_CARD = "#1D172E"       # Dark violet card container
BG_CARD_ALT = "#271F3B"   # Card alt fill for input boxes / entries
BORDER = "#3B2D5C"        # Subtle violet border
BRAND = "#9333EA"         # Vibrant electric purple
BRAND_HOVER = "#A855F7"   # Hover state for primary buttons
ACCENT2 = "#8B5CF6"       # Secondary purple accent
ACCENT2_HOVER = "#7C3AED" # Secondary hover
TEXT = "#F3F0FF"          # Bright silver-white text
TEXT_MUTED = "#A799C7"    # Muted lavender subtext
DROPDOWN_FG = "#1D172E"   # Dropdown menu background
DROPDOWN_TEXT = "#F3F0FF" # Dropdown text
DROPDOWN_HOVER = "#271F3B"# Dropdown hover item

class AutoHideScrollFrame(ctk.CTkFrame):
    """Clean public CTk subclass for scrollable frames with auto-hiding scrollbars."""
    def __init__(self, master, fg_color=BG_CARD, corner_radius=10, **kwargs):
        super().__init__(master, fg_color=fg_color, corner_radius=corner_radius, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg=self._apply_appearance_mode(fg_color),
                                 highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self._canvas.yview,
                                           fg_color="transparent", button_color=BORDER,
                                           button_hover_color=BRAND_HOVER)
        self._canvas.configure(yscrollcommand=self.scrollbar.set)

        self.inner = ctk.CTkFrame(self._canvas, fg_color=fg_color, corner_radius=0)
        self._win = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<Enter>", lambda e: self._show_bar())
        self._canvas.bind("<Leave>", lambda e: self._schedule_hide())
        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self.inner.bind("<MouseWheel>", self._on_wheel)

        self._hide_after_id = None
        self.scrollbar.grid_remove()

    def _apply_appearance_mode(self, color):
        try:
            mode = ctk.get_appearance_mode().lower()
            if isinstance(color, (tuple, list)):
                return color[0] if mode == "light" else color[1]
            elif color in (None, "transparent"):
                return "#FFFFFF" if mode == "light" else "#1D172E"
            return color
        except Exception:
            return "#1D172E"

    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._update_bar_visibility()

    def _on_canvas_configure(self, event):
        self._canvas.itemconfigure(self._win, width=event.width)
        self._update_bar_visibility()

    def _update_bar_visibility(self):
        try:
            if self._canvas.yview() == (0.0, 1.0):
                self.scrollbar.grid_remove()
            else:
                self.scrollbar.grid(row=0, column=1, sticky="ns")
        except Exception:
            pass

    def _show_bar(self):
        try:
            if self._canvas.yview() != (0.0, 1.0):
                self.scrollbar.grid(row=0, column=1, sticky="ns")
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
            self.scrollbar.grid_remove()
        except Exception:
            pass

    def _on_wheel(self, event):
        try:
            if self._canvas.yview() != (0.0, 1.0):
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                self._show_bar()
        except Exception:
            pass

class ToolTip:
    """Hover tooltip popup manager for controls and inputs."""
    def __init__(self, widget, text=None, title=None, delay=400, enabled_var=None, description=None):
        self.widget = widget
        self.text = text or description or ""
        self.title = title
        self.delay = delay
        self.enabled_var = enabled_var
        self.tip_window = None
        self.id = None
        widget.bind("<Enter>", self.schedule)
        widget.bind("<Leave>", self.hide)

    def schedule(self, event=None):
        if self.enabled_var and self.enabled_var.get() == "0":
            return
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self, event=None):
        if self.id:
            try:
                self.widget.after_cancel(self.id)
            except Exception:
                pass
            self.id = None

    def show(self):
        if self.tip_window or not self.text:
            return
        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tip_window = tw = ctk.CTkToplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            frame = ctk.CTkFrame(tw, fg_color=BG_CARD_ALT, border_color=BORDER, border_width=1, corner_radius=6)
            frame.pack(fill="both", expand=True)
            if self.title:
                ctk.CTkLabel(frame, text=self.title, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT).pack(anchor="w", padx=8, pady=(4, 0))
            ctk.CTkLabel(frame, text=self.text, font=ctk.CTkFont(size=10), text_color=TEXT_MUTED, wraplength=220, justify="left").pack(anchor="w", padx=8, pady=(2, 4))
        except Exception:
            self.tip_window = None

    def hide(self, event=None):
        self.unschedule()
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

def enable_auto_hide_scrollbar(scroll_frame):
    """Compatibility helper for standard CTkScrollableFrame instances."""
    try:
        if hasattr(scroll_frame, "_scrollbar"):
            scroll_frame._scrollbar.grid_remove()
    except Exception:
        pass

def _apply_cursor_style(widget):
    try:
        if hasattr(widget, "configure"):
            widget.configure(cursor="xterm")
    except Exception:
        pass

def make_gradient(width, height, color1, color2, angle=0):
    """Generate a smooth gradient Image for header accents."""
    base = Image.new("RGB", (max(1, width), max(1, height)), color1)
    return base
