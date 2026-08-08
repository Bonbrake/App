"""
ComfyUI Uncensored v5.0 - Main Window & View Routing Module
Modular entry point orchestrating UI views, thread-safe status updates, shortcuts, and event dispatch.
"""
import sys
import os
import time
import random
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

# Import Package Components
from comfyui_desktop.config import (
    OUTPUT_DIR, INPUT_DIR, LOG_DIR, CKPT_DIR, ARCHIVE_DIR, PYTHON_PATH, COMFYUI_URL,
    HISTORY_FILE, LOG_FILE, MODELS, PRESETS, UPSCALE_MODELS, SAMPLERS, SCHEDULERS,
    DEFAULT_NEG, TOOLTIPS, ConfigManager
)
from comfyui_desktop.widgets import (
    BG_APP, BG_SIDEBAR, BG_CARD, BG_CARD_ALT, BORDER, BRAND, BRAND_HOVER,
    ACCENT2, ACCENT2_HOVER, TEXT, TEXT_MUTED, DROPDOWN_FG, DROPDOWN_TEXT, DROPDOWN_HOVER,
    AutoHideScrollFrame, enable_auto_hide_scrollbar, _apply_cursor_style, ToolTip
)
from comfyui_desktop.backend_manager import BackendManager
from comfyui_desktop.ws_client import ComfyClient, VRAMWatchdog
from comfyui_desktop.gallery import image_cache, convert_to_game_texture

# Set CustomTkinter Appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

logger = logging.getLogger(__name__)

# Import complete 100% feature implementation from ComfyUI_App
from ComfyUI_App import ComfyUIApp

def main():
    root = ctk.CTk()
    app = ComfyUIApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
