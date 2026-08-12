"""
ComfyUI Uncensored v5.0 - Config & Environment Module
Single source of truth for runtime settings, model definitions, presets, and paths.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Base Directory Resolution — derived from the app's own location so the
# project is portable and not tied to a hardcoded machine path.
BASE_DIR = Path(__file__).resolve().parent

# System Paths
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INPUT_DIR = os.path.join(BASE_DIR, "input")
LOG_DIR = os.path.join(BASE_DIR, "logs")
COMFYUI_DIR = os.path.join(BASE_DIR, "ComfyUI_windows_portable", "ComfyUI")
PYTHON_PATH = os.path.join(BASE_DIR, "ComfyUI_windows_portable", "python_embeded", "python.exe")
CKPT_DIR = os.path.join(COMFYUI_DIR, "models", "checkpoints")
ARCHIVE_DIR = os.path.join(BASE_DIR, "models_archive")

COMFYUI_URL = "http://127.0.0.1:8188"
HISTORY_FILE = os.path.join(BASE_DIR, "history_snapshot.json")
LOG_FILE = os.path.join(LOG_DIR, "ComfyUI_App.log")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# Ensure required directories exist
for p in (OUTPUT_DIR, INPUT_DIR, LOG_DIR, CKPT_DIR, ARCHIVE_DIR):
    os.makedirs(p, exist_ok=True)

# Data Models & Constants
MODELS = {
    "epicRealism XL": {
        "file": "epicrealismXL_pure.safetensors",
        "w": 768, "h": 768, "steps": 35, "cfg": 6.5, "sampler": "dpmpp_2m", "scheduler": "karras"
    },
    # Optional model — checkpoint file is NOT bundled with the repo; the user
    # must supply cyberrealisticXL_v20.safetensors in models/checkpoints/.
    "CyberRealistic XL": {
        "file": "cyberrealisticXL_v20.safetensors",
        "w": 768, "h": 768, "steps": 30, "cfg": 6.0, "sampler": "dpmpp_2m", "scheduler": "karras"
    },
    "Juggernaut XL": {
        "file": "juggernautXL_v9.safetensors",
        "w": 1024, "h": 1024, "steps": 30, "cfg": 6.0, "sampler": "dpmpp_2m", "scheduler": "karras"
    },
    "Pony Diffusion V6": {
        "file": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        "w": 1024, "h": 1024, "steps": 25, "cfg": 7.0, "sampler": "euler_ancestral", "scheduler": "normal"
    },
}

PRESETS = {
    "Photoreal Portrait": {
        "model": "epicRealism XL", "w": 768, "h": 768, "steps": 35, "cfg": 6.5,
        "prompt": "photorealistic portrait, detailed skin texture, studio lighting, 8k uhd, sharp focus",
        "neg": "blurry, lowres, deformed, bad anatomy, watermark, text"
    },
    "Cinematic Wide": {
        "model": "epicRealism XL", "w": 1216, "h": 832, "steps": 40, "cfg": 7.0,
        "prompt": "cinematic wide shot, epic landscape, volumetric atmosphere, masterpiece, detailed",
        "neg": "blurry, low quality, oversaturated, cropped, draft"
    },
    "Anime Character": {
        "model": "Pony Diffusion V6", "w": 832, "h": 1216, "steps": 28, "cfg": 7.0,
        "prompt": "score_9, score_8_up, score_7_up, masterpiece, detailed anime character, vibrant colors",
        "neg": "score_4_lower, score_5_lower, lowres, bad hands, bad eyes"
    },
    "Game Texture": {
        "model": "epicRealism XL", "w": 1024, "h": 1024, "steps": 35, "cfg": 6.5, "format": "Game Texture (TGA)",
        "prompt": "seamless game texture, tileable surface, PBR materials, high detail",
        "neg": "seam, border, frame, text, watermark, asymmetric"
    },
}

UPSCALE_MODELS = ["4x_NMKD-Superscale_80000G.pth", "4x_RealESRGAN_x4plus.pth", "4x-UltraSharp.pth"]
SAMPLERS = ["dpmpp_2m", "euler", "euler_ancestral", "heun", "ddim"]
SCHEDULERS = ["karras", "normal", "simple", "ddim_uniform"]
DEFAULT_NEG = "blurry, lowres, deformed, watermark, text"

TOOLTIPS = {
    "Model": ("Active Checkpoint", "Choose the diffusion model checkpoint used for rendering."),
    "Preset": ("Quality Presets", "Apply curated generation defaults for various artistic styles."),
    "Prompt": ("Positive Prompt", "Describe what you want to generate in detail."),
    "Negative Prompt": ("Negative Prompt", "Specify elements to avoid in the generation."),
    "Width": ("Image Width", "Resolution width in pixels (multiples of 64)."),
    "Height": ("Image Height", "Resolution height in pixels (multiples of 64)."),
    "Steps": ("Sampling Steps", "Number of denoising iterations. Higher = more detail."),
    "CFG": ("CFG Scale", "How strictly the model adheres to your text prompt."),
    "Seed": ("Random Seed", "Set a specific seed for reproducible output, or 0 for random."),
    "Batch": ("Batch Size", "Number of images to generate per batch."),
    "Denoise": ("Denoise Strength", "Image-to-image transformation strength (0.0 - 1.0)."),
    "Sampler": ("Sampling Algorithm", "Mathematical algorithm used to denoise the latent image."),
    "Scheduler": ("Noise Schedule", "Controls how noise reduction is distributed across steps."),
    "Format": ("Output Format", "Select PNG or Power-of-Two TGA (for game engine textures).")
}

def resolve(path):
    """Expand ~, environment variables, strip whitespace, and normalize separators to the OS-native form."""
    if not path:
        return ""
    return os.path.normpath(os.path.expanduser(os.path.expandvars(str(path).strip())))


class ConfigManager:
    """Manages persistent application settings in config.json."""
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        self.settings = {
            "output_dir": resolve(OUTPUT_DIR),
            "vram_threshold": "90% (Default)",
            "default_format": "PNG",
            "default_sampler": "dpmpp_2m",
            "default_scheduler": "karras",
            "theme_mode": "Dark"
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.settings.update(data)
                global OUTPUT_DIR
                if "output_dir" in data and data["output_dir"]:
                    OUTPUT_DIR = resolve(data["output_dir"])
                    self.settings["output_dir"] = OUTPUT_DIR
            except Exception as e:
                logging.error("Failed to load config.json: %s", e)
                try:
                    corrupt_bak = self.config_path + ".corrupt"
                    if not os.path.exists(corrupt_bak) and os.path.exists(self.config_path):
                        os.replace(self.config_path, corrupt_bak)
                except Exception:
                    pass

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            global OUTPUT_DIR
            OUTPUT_DIR = resolve(self.settings.get("output_dir", OUTPUT_DIR))
            self.settings["output_dir"] = OUTPUT_DIR
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            return True
        except Exception as e:
            logging.error("Failed to save config.json: %s", e)
            return False
