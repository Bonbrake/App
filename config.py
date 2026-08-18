"""
ComfyUI Uncensored v5.1 - Config & Environment Module
Single source of truth for runtime settings, SOTA model definitions, presets, and paths.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Base Directory Resolution
def _resolve_comfyui_portable_dir() -> Path:
    env = os.environ.get("COMFYUI_PORTABLE_DIR")
    if env:
        return Path(os.path.expanduser(os.path.expandvars(env)))
    here = Path(__file__).resolve().parent
    for cand in (here.parent / "ComfyUI_windows_portable",
                 here.parent.parent / "ComfyUI_windows_portable",
                 Path.cwd() / "ComfyUI_windows_portable",
                 here / "ComfyUI_windows_portable",
                 Path(r"C:\ComfyUI-Desktop")):
        if cand.is_dir():
            return cand
    return here

BASE_DIR = _resolve_comfyui_portable_dir()

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
SESSION_FILE = os.path.join(BASE_DIR, "session_restore.json")

# Ensure required directories exist
for p in (OUTPUT_DIR, INPUT_DIR, LOG_DIR, CKPT_DIR, ARCHIVE_DIR):
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# SOTA 2026 Flagship Diffusion Models
# ---------------------------------------------------------------------------
MODELS = {
    "epiCRealism XL v5": {
        "file": "epicrealismXL_v5.safetensors",
        "value": "epicrealismXL_v5.safetensors",
        "w": 1024, "h": 1024, "steps": 35, "cfg": 6.5, "sampler": "dpmpp_2m", "scheduler": "karras",
        "desc": "SOTA Cinematic Photorealism, natural studio lighting, ultra-fine skin pores and sharp eyes."
    },
    "Juggernaut XL v11": {
        "file": "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
        "value": "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors",
        "w": 1024, "h": 1024, "steps": 30, "cfg": 6.0, "sampler": "dpmpp_2m", "scheduler": "karras",
        "desc": "Industry leading SDXL all-rounder for architecture, detailed portraits, concept art and landscapes."
    },
    "FLUX.1-schnell (4-Step DiT)": {
        "file": "flux1-schnell.safetensors",
        "value": "flux1-schnell.safetensors",
        "w": 1024, "h": 1024, "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple",
        "desc": "Next-Gen 12B Flow Matching Transformer with state-of-the-art text rendering and prompt fidelity."
    },
    "SD 3.5 Large (8B MMDiT)": {
        "file": "sd3.5_large.safetensors",
        "value": "sd3.5_large.safetensors",
        "w": 1024, "h": 1024, "steps": 28, "cfg": 4.5, "sampler": "euler", "scheduler": "sgm_uniform",
        "desc": "Stability AI flagship 8B multimodal DiT with superior typography and complex composition."
    },
    "Illustrious XL / Pony V6": {
        "file": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        "value": "ponyDiffusionV6XL_v6StartWithThisOne.safetensors",
        "w": 832, "h": 1216, "steps": 28, "cfg": 7.0, "sampler": "euler_ancestral", "scheduler": "normal",
        "desc": "SOTA anime, stylized illustration, dynamic character action poses, and vibrant game art."
    },
    "SDXL Turbo (1-Step Fast)": {
        "file": "sd_xl_turbo_1.0_fp16.safetensors",
        "value": "sd_xl_turbo_1.0_fp16.safetensors",
        "w": 512, "h": 512, "steps": 1, "cfg": 1.0, "sampler": "euler", "scheduler": "normal",
        "desc": "Real-time interactive generation in 1 to 4 steps for rapid creative prototyping."
    },
    "CyberRealistic XL v20": {
        "file": "cyberrealisticXL_v20.safetensors",
        "value": "cyberrealisticXL_v20.safetensors",
        "w": 1024, "h": 1024, "steps": 30, "cfg": 6.0, "sampler": "dpmpp_2m", "scheduler": "karras",
        "desc": "Photorealistic portraits with rich contrast and sharp cinematic grading."
    },
}

# ---------------------------------------------------------------------------
# SOTA Generation Presets
# ---------------------------------------------------------------------------
PRESETS = {
    "Photoreal Portrait (8K)": {
        "model": "epiCRealism XL v5", "w": 1024, "h": 1024, "steps": 35, "cfg": 6.5,
        "prompt": "photorealistic 8k portrait, detailed skin texture, micro-details, natural studio lighting, 85mm lens, f/1.8, sharp focus, masterpiece",
        "neg": "blurry, lowres, deformed, bad anatomy, bad hands, plastic skin, watermark, text"
    },
    "Cinematic Film (35mm)": {
        "model": "Juggernaut XL v11", "w": 1344, "h": 768, "steps": 38, "cfg": 6.0,
        "prompt": "cinematic wide anamorphic shot, 35mm film grain, moody volumetric atmosphere, rim lighting, high dynamic range, color graded, masterpiece",
        "neg": "blurry, low quality, oversaturated, amateur, cropped, draft"
    },
    "Next-Gen FLUX DiT": {
        "model": "FLUX.1-schnell (4-Step DiT)", "w": 1024, "h": 1024, "steps": 4, "cfg": 1.0,
        "prompt": "breathtaking digital concept art, intricate architectural details, neon highlights, ultra crisp rendering, masterpiece",
        "neg": "blurry, low quality, artifacts, distorted text"
    },
    "Anime Masterpiece": {
        "model": "Illustrious XL / Pony V6", "w": 832, "h": 1216, "steps": 28, "cfg": 7.0,
        "prompt": "score_9, score_8_up, score_7_up, masterpiece, detailed anime character, dynamic lighting, high resolution, expressive eyes",
        "neg": "score_4_lower, score_5_lower, lowres, bad hands, bad eyes, extra limbs"
    },
    "Seamless PBR Texture": {
        "model": "epiCRealism XL v5", "w": 1024, "h": 1024, "steps": 35, "cfg": 6.5, "format": "Game Texture (TGA)",
        "prompt": "seamless tileable surface texture, top-down flat lighting, high detail PBR material, photorealistic albedo map",
        "neg": "seam, border, frame, text, watermark, perspective distortion, cast shadows"
    },
    "Cyberpunk Cityscape": {
        "model": "Juggernaut XL v11", "w": 1536, "h": 640, "steps": 32, "cfg": 6.5,
        "prompt": "panoramic cyberpunk megacity, holographic billboards, wet asphalt reflections, towering neon skyscrapers, rain atmosphere, ultra detailed",
        "neg": "blurry, lowres, muted colors, flat lighting"
    },
}

# Aspect Ratios with Multiple-of-8 Math
ASPECT_RATIOS = {
    "1:1 Square": {"w": 1024, "h": 1024, "label": "1:1 (1024×1024)"},
    "16:9 Landscape": {"w": 1344, "h": 768, "label": "16:9 (1344×768)"},
    "9:16 Portrait": {"w": 768, "h": 1344, "label": "9:16 (768×1344)"},
    "4:3 Photo": {"w": 1152, "h": 864, "label": "4:3 (1152×864)"},
    "3:4 Portrait": {"w": 864, "h": 1152, "label": "3:4 (864×1152)"},
    "21:9 Cinema": {"w": 1536, "h": 640, "label": "21:9 (1536×640)"},
}

def clamp_to_multiple_of_8(val: int, default: int = 512, min_val: int = 64, max_val: int = 8192) -> int:
    """Ensure dimension is within bounds and divisible by 8 (required by neural latents)."""
    try:
        v = int(val)
        v = max(min_val, min(max_val, v))
        return (v // 8) * 8
    except Exception:
        return default

UPSCALE_MODELS = [
    "4x-UltraSharp.pth",
    "4x-Nomos8k.pth",
    "RealESRGAN_x4plus.pth",
    "4x_NMKD-Superscale_80000G.pth"
]

SAMPLERS = ["dpmpp_2m", "euler", "euler_ancestral", "dpmpp_sde", "dpmpp_2m_sde", "heun", "ddim"]
SCHEDULERS = ["karras", "normal", "simple", "sgm_uniform", "ddim_uniform", "beta"]
DEFAULT_NEG = "blurry, lowres, deformed, bad anatomy, watermark, text, low quality"

# ---------------------------------------------------------------------------
# Comprehensive Cyberpunk Tooltip Dictionary
# ---------------------------------------------------------------------------
TOOLTIPS = {
    "Model": ("Active Diffusion Checkpoint", "Choose the generative AI model checkpoint used for rendering (FLUX.1, SDXL, SD3.5, Pony)."),
    "Preset": ("Creative Style Presets", "Apply 1-click curated generation parameters, prompt templates, and optimal sampler configs."),
    "Prompt": ("Creative Directives (Prompt)", "Describe the desired scene, subjects, lighting, artistic style, and details."),
    "Negative Prompt": ("Negative Directives (Avoid)", "Specify elements, artifacts, or visual flaws to filter out and avoid."),
    "Width": ("Image Width (px)", "Horizontal resolution in pixels (automatically clamped to multiples of 8)."),
    "Height": ("Image Height (px)", "Vertical resolution in pixels (automatically clamped to multiples of 8)."),
    "Swap Dimensions": ("Swap Width & Height", "Quickly swap horizontal and vertical dimensions (Shortcut: Ctrl+Shift+W)."),
    "Steps": ("Sampling Steps", "Number of iterative denoising passes. Higher values refine fine details; 25-35 is optimal for SDXL."),
    "CFG": ("Guidance Scale (CFG)", "How strictly the diffusion model adheres to your prompt directives (3.5-7.5 recommended; 1.0 for FLUX)."),
    "Seed": ("Randomization Seed", "Numeric seed for deterministic reproducibility. Keep 0 or Random checked for fresh variations."),
    "Randomize": ("Seed Randomizer", "Toggle automatic cryptographic seed randomization on every generation run."),
    "Step Seed": ("Seed Step (+1 / -1)", "Increment or decrement current seed to explore slight deterministic variations of a composition."),
    "Copy Seed": ("Copy Seed to Clipboard", "Copy current active numeric seed to system clipboard for sharing or logging."),
    "Batch": ("Batch Generation Size", "Number of independent images generated sequentially in a single job run."),
    "Denoise": ("Denoise Strength", "How much of the source image is replaced during Image-to-Image (0.0 = untouched, 1.0 = full redraw)."),
    "Sampler": ("Sampling Algorithm", "Mathematical differential equation solver used to denoise latent representations (dpmpp_2m, euler, etc.)."),
    "Scheduler": ("Noise Schedule Curve", "Controls how noise variance is distributed across timesteps (karras, normal, simple, sgm_uniform)."),
    "Format": ("Export Asset Format", "Choose standard PNG or Game Engine Power-of-Two TGA for 3D textures."),
    "Model Strength": ("LoRA / Model Weight", "Scale multiplier for active model weights and fine-tuned adjustments (0.0 - 2.0)."),
    "CLIP Strength": ("CLIP Text Encoder Weight", "Scale multiplier for text encoder conditioning and prompt alignment (0.0 - 2.0)."),
    "Upscale Model": ("Super-Resolution Model", "Choose neural upscaling model (4x-UltraSharp, 4x-Nomos8k, RealESRGAN) for crisp texture scaling."),
    "Scale Multiplier": ("Upscale Multiplier", "Scaling factor applied to input dimensions (e.g. 2x, 4x)."),
    "Generate": ("Execute Generation (Ctrl+E)", "Compile the active workflow graph and trigger real-time AI generation via ComfyUI backend."),
    "Open Folder": ("Open Output Vault", "Open the local media storage directory in Windows File Explorer (Ctrl+O)."),
    "Enhance Prompt": ("⚡ Local LLM Prompt Enhancer", "1-Click expand brief concepts into rich, cinematic prompts using local LLM integration."),
    "Rehydrate": ("💧 Parameter Re-Hydration", "Inspect embedded generation metadata in PNG and restore full prompt, seed, model, and sampling configs."),
}

class ConfigManager:
    """Manages persistent application settings in config.json."""
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        self.settings = {
            "output_dir": OUTPUT_DIR,
            "vram_threshold": "90% (Default)",
            "default_format": "PNG",
            "default_sampler": "dpmpp_2m",
            "default_scheduler": "karras",
            "theme_mode": "Dark",
            "window_geometry": "1280x1120+100+100",
            "ui_scaling": "100%",
            "target_engine": "All Styles"
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.settings.update(data)
                global OUTPUT_DIR
                if "output_dir" in data:
                    OUTPUT_DIR = data["output_dir"]
            except Exception as e:
                logging.error("Failed to load config.json: %s", e)

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            global OUTPUT_DIR
            OUTPUT_DIR = self.settings.get("output_dir", OUTPUT_DIR)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            return True
        except Exception as e:
            logging.error("Failed to save config.json: %s", e)
            return False

