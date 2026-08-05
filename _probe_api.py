import json, urllib.request, os
raw = urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=60).read().decode("utf-8", "replace")
oi = json.loads(raw, strict=False)
print("TOTAL NODES:", len(oi))
for node in ["CheckpointLoaderSimple", "SaveImage", "LoadImage", "KSampler",
             "ImageUpscaleWithModel", "UpscaleModelLoader", "VAEEncode",
             "EmptyLatentImage", "CLIPTextEncode", "VAEDecode"]:
    if node not in oi:
        print("###", node, "*** NOT ON SERVER ***")
        continue
    inp = oi[node].get("input", {})
    req = inp.get("required", {}) or {}
    opt = inp.get("optional", {}) or {}
    print("###", node)
    print("   required:", list(req.keys()))
    print("   optional:", list(opt.keys()))
    if node == "CheckpointLoaderSimple":
        print("   ckpts:", req["ckpt_name"][0])
    if node == "UpscaleModelLoader":
        print("   upscale models:", req["model_name"][0])
    if node == "KSampler":
        print("   samplers:", req["sampler_name"][0])
        print("   schedulers:", req["scheduler"][0])

print()
print("=== models_archive ===")
AR = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\models_archive"
CK = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\models\checkpoints"
UP = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\models\upscale_models"
for d in (AR, CK, UP):
    print("--", d, "exists:", os.path.isdir(d))
    if os.path.isdir(d):
        for f in os.listdir(d):
            p = os.path.join(d, f)
            print("     %-60s %12d B  link=%s" % (f, os.path.getsize(p) if os.path.exists(p) else -1, os.path.islink(p)))
