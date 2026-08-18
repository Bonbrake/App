"""
ComfyUI Uncensored v5.0 - Async Gallery Engine & Memory Safety
Handles ThreadPool thumbnail decoding, PIL image cache lifecycle, TGA texture exports,
and recursive multi-path Media Vault auto-discovery.
"""
import os
import gc
import math
import logging
from PIL import Image, ImageTk
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ImageCache:
    """Explicit Image Memory Registry that prevents PIL & ImageTk GDI/RAM memory leaks."""
    def __init__(self):
        self._pil_cache = {}
        self._tk_cache = {}

    def register(self, key, pil_image, tk_image=None):
        self.release(key)
        self._pil_cache[key] = pil_image
        if tk_image:
            self._tk_cache[key] = tk_image

    def release(self, key):
        if key in self._pil_cache:
            try:
                img = self._pil_cache.pop(key)
                if hasattr(img, "close"):
                    img.close()
            except Exception as e:
                logger.debug("PIL close error: %s", e)
        if key in self._tk_cache:
            self._tk_cache.pop(key, None)

    def clear(self):
        keys = list(self._pil_cache.keys())
        for k in keys:
            self.release(k)
        self._pil_cache.clear()
        self._tk_cache.clear()
        gc.collect()

# Global ImageCache Instance
image_cache = ImageCache()

def convert_to_game_texture(image_path):
    """Export output image as a Power-of-Two tileable TGA texture for game engines."""
    try:
        if not image_path or not os.path.exists(image_path):
            return False
        image_path = os.path.abspath(image_path)
        with Image.open(image_path) as im:
            w, h = im.size
            # Nearest Power-of-Two dimensions
            pot_w = 2 ** round(math.log2(w)) if w > 0 else 512
            pot_h = 2 ** round(math.log2(h)) if h > 0 else 512
            pot_im = im.resize((pot_w, pot_h), Image.Resampling.LANCZOS)
            tga_path = os.path.splitext(image_path)[0] + ".tga"
            pot_im.save(tga_path, format="TGA")
            pot_im.close()
            return tga_path
    except Exception as e:
        logger.error("Failed to convert texture to TGA: %s", e)
        return False

def discover_media_directories(primary_dir=None, comfyui_dir=None, portable_dir=None):
    """Auto-discover all standard ComfyUI generated output image directories."""
    candidates = []
    if primary_dir:
        candidates.append(os.path.normpath(primary_dir))

    # Standard user ComfyUI Pictures directory
    pics = os.path.normpath(os.path.expanduser(r"~/Pictures"))
    gen_pics = os.path.join(pics, "ComfyUI_Generated")
    candidates.append(gen_pics)

    # ComfyUI installation output dirs
    if comfyui_dir:
        candidates.append(os.path.join(comfyui_dir, "output"))
    if portable_dir:
        candidates.append(os.path.join(portable_dir, "output"))
        candidates.append(os.path.join(portable_dir, "ComfyUI", "output"))
        candidates.append(os.path.join(portable_dir, "ComfyUI_windows_portable", "ComfyUI", "output"))

    # Well-known fallback paths
    candidates.extend([
        r"C:\ComfyUI-Desktop\output",
        r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\output",
        r"C:\ComfyUI_windows_portable\ComfyUI\output",
        r"C:\ComfyUI\output",
        os.path.abspath("output"),
        os.path.normpath(os.path.expanduser(r"~/Documents/ComfyUI/output")),
    ])

    seen = set()
    valid_dirs = []
    for d in candidates:
        if d and os.path.isdir(d):
            norm = os.path.normpath(d)
            if norm not in seen:
                seen.add(norm)
                valid_dirs.append(norm)
    return valid_dirs

TEXTURE_KEYWORDS = (
    "texture", "albedo", "normal", "roughness", "metallic", "height",
    "specular", "diffuse", "pbr", "ambient", "displacement", "emission",
    "mat_", "_tex", "_mat", "orm", "mask"
)

def is_texture_file(filepath: str) -> bool:
    """Determine if a file is an authentic texture/material map."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".tga", ".dds", ".exr"):
        return True
    base = os.path.basename(filepath).lower()
    parent = os.path.basename(os.path.dirname(filepath)).lower()
    if parent in ("textures", "materials", "pbr_maps", "texture_exports"):
        return True
    for kw in TEXTURE_KEYWORDS:
        if kw in base:
            return True
    return False

def scan_all_media_files(directories, recursive=True, max_depth=2, filter_type="all"):
    """Scan given directories for media files, excluding input and cache folders.
    filter_type: 'all', 'images', 'videos', 'textures'
    """
    valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".tga", ".bmp")
    if filter_type == "images":
        valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    elif filter_type == "videos":
        valid_exts = (".mp4", ".webm", ".avi", ".mov", ".gif")
    elif filter_type == "textures":
        valid_exts = (".tga", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".dds")

    valid_files = []
    seen = set()
    ignored_dir_names = {"input", "inputs", "temp", "_temp", "cache", "__pycache__", "thumbnails", "thumbs", ".git", ".cache"}

    for base in directories:
        if not os.path.isdir(base):
            continue
        if not recursive:
            try:
                for f in os.listdir(base):
                    if f.lower().endswith(valid_exts) and not f.lower().startswith("input"):
                        fp = os.path.join(base, f)
                        if os.path.isfile(fp) and fp not in seen:
                            if filter_type == "textures" and not is_texture_file(fp):
                                continue
                            if filter_type == "images" and is_texture_file(fp) and ext == ".tga":
                                continue
                            seen.add(fp)
                            valid_files.append(fp)
            except Exception:
                pass
            continue

        for root, dirs, files in os.walk(base):
            # Prune ignored directory branches
            dirs[:] = [d for d in dirs if d.lower() not in ignored_dir_names]
            lower_root = root.lower()
            if any(ign in lower_root.split(os.sep) for ign in ignored_dir_names):
                continue
            if ("screenshot" in lower_root or "camera roll" in lower_root) and root not in directories:
                continue
            rel = os.path.relpath(root, base)
            if rel != "." and len(rel.split(os.sep)) > max_depth:
                continue
            for f in files:
                if f.lower().endswith(valid_exts) and not f.lower().startswith("input"):
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp) and fp not in seen:
                        ext = os.path.splitext(fp)[1].lower()
                        if filter_type == "textures" and not is_texture_file(fp):
                            continue
                        if filter_type == "images" and is_texture_file(fp) and ext == ".tga":
                            continue
                        seen.add(fp)
                        valid_files.append(fp)

    return valid_files
