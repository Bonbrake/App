"""Empirically verify the workflow-level defects against the LIVE ComfyUI 0.29 server.
No guessing: every claim below is proven by an actual HTTP response."""
import json, urllib.request, urllib.error, os

URL = "http://127.0.0.1:8188"

def post(path, obj):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(URL + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, r.read().decode("utf-8", "replace")[:600]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:900]
    except Exception as e:
        return -1, repr(e)

CKPT = "epicrealismXL_pure.safetensors"

# Stage the symlink exactly like _ensure_model_loaded does, so ckpt_name validates.
CK = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\models\checkpoints"
AR = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\models_archive"
tgt, src = os.path.join(CK, CKPT), os.path.join(AR, CKPT)
if not os.path.exists(tgt):
    try:
        os.symlink(src, tgt); print("staged symlink ->", tgt)
    except Exception as e:
        print("SYMLINK FAILED:", e)
else:
    print("symlink already present")

def base_wf(denoise=None, fmt=False, extra_ckpt=False):
    ck_in = {"ckpt_name": CKPT}
    if extra_ckpt:
        ck_in.update({"model_strength": 1.0, "clip_strength": 1.0})
    ks = {"sampler_name": "dpmpp_2m", "scheduler": "karras", "steps": 4, "cfg": 6.5,
          "seed": 42, "model": ["LastNode", 0], "positive": ["POS", 0],
          "negative": ["NEG", 0], "latent_image": ["EmptyLatent", 0]}
    if denoise is not None:
        ks["denoise"] = denoise
    save_in = {"images": ["VAEDecode", 0], "filename_prefix": "QA_PROBE"}
    if fmt:
        save_in["format"] = "Game Texture (TGA)"
    return {
        "LastNode": {"class_type": "CheckpointLoaderSimple", "inputs": ck_in},
        "EmptyLatent": {"class_type": "EmptyLatentImage",
                        "inputs": {"width": 256, "height": 256, "batch_size": 1}},
        "KSampler": {"class_type": "KSampler", "inputs": ks},
        "POS": {"class_type": "CLIPTextEncode", "inputs": {"text": "a cube", "clip": ["LastNode", 1]}},
        "NEG": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["LastNode", 1]}},
        "VAEDecode": {"class_type": "VAEDecode", "inputs": {"samples": ["KSampler", 0], "vae": ["LastNode", 2]}},
        "SaveImage": {"class_type": "SaveImage", "inputs": save_in},
    }

print("\n" + "=" * 70)
print("TEST A: current app code -> payload {'prompt': json.dumps(wf)}  (STRING)")
print("=" * 70)
s, b = post("/prompt", {"prompt": json.dumps(base_wf(denoise=1.0)),
                        "client_id": "qa_probe"})
print("HTTP", s, "\n", b)

print("\n" + "=" * 70)
print("TEST B: dict payload but NO denoise (current txt2img graph)")
print("=" * 70)
s, b = post("/prompt", {"prompt": base_wf(denoise=None), "client_id": "qa_probe"})
print("HTTP", s, "\n", b)

print("\n" + "=" * 70)
print("TEST C: dict payload + denoise + extra ckpt params + SaveImage format")
print("=" * 70)
s, b = post("/prompt", {"prompt": base_wf(denoise=1.0, fmt=True, extra_ckpt=True),
                        "client_id": "qa_probe"})
print("HTTP", s, "\n", b)

print("\n" + "=" * 70)
print("TEST D: LoadImage with 'input\\name.png' vs bare 'name.png'")
print("=" * 70)
from PIL import Image
IN = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\input"
os.makedirs(IN, exist_ok=True)
Image.new("RGB", (64, 64), (120, 60, 30)).save(os.path.join(IN, "qa_probe_in.png"))
for name in [os.path.join("input", "qa_probe_in.png"), "qa_probe_in.png"]:
    wf = {"LoadImage": {"class_type": "LoadImage", "inputs": {"image": name}},
          "ModelLoader": {"class_type": "UpscaleModelLoader",
                          "inputs": {"model_name": "4x-UltraSharp.pth"}},
          "Upscale": {"class_type": "ImageUpscaleWithModel",
                      "inputs": {"upscale_model": ["ModelLoader", 0], "image": ["LoadImage", 0]}},
          "SaveImage": {"class_type": "SaveImage",
                        "inputs": {"images": ["Upscale", 0], "filename_prefix": "QA_UP"}}}
    s, b = post("/prompt", {"prompt": wf, "client_id": "qa_probe"})
    print("  image=%-28r -> HTTP %s  %s" % (name, s, b[:260].replace("\n", " ")))

print("\n" + "=" * 70)
print("TEST E: ImageUpscaleWithModel WITH width/height (as app sends)")
print("=" * 70)
wf = {"LoadImage": {"class_type": "LoadImage", "inputs": {"image": "qa_probe_in.png"}},
      "ModelLoader": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}},
      "Upscale": {"class_type": "ImageUpscaleWithModel",
                  "inputs": {"upscale_model": ["ModelLoader", 0], "image": ["LoadImage", 0],
                             "width": 512, "height": 512}},
      "SaveImage": {"class_type": "SaveImage",
                    "inputs": {"images": ["Upscale", 0], "filename_prefix": "QA_UP2"}}}
s, b = post("/prompt", {"prompt": wf, "client_id": "qa_probe"})
print("HTTP", s, "\n", b[:400])
