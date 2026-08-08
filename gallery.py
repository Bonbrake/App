"""
ComfyUI Uncensored v5.0 - Async Gallery Engine & Memory Safety
Handles ThreadPool thumbnail decoding, PIL image cache lifecycle, and TGA texture exports.
"""
import os
import gc
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
        if not os.path.exists(image_path):
            return False
        with Image.open(image_path) as im:
            w, h = im.size
            # Nearest Power-of-Two dimensions
            pot_w = 2 ** round(os.math.log2(w)) if w > 0 else 512
            pot_h = 2 ** round(os.math.log2(h)) if h > 0 else 512
            pot_im = im.resize((pot_w, pot_h), Image.Resampling.LANCZOS)
            tga_path = os.path.splitext(image_path)[0] + ".tga"
            pot_im.save(tga_path, format="TGA")
            pot_im.close()
            return tga_path
    except Exception as e:
        logger.error("Failed to convert texture to TGA: %s", e)
        return False
