import json, urllib.request, time, os

URL = "http://127.0.0.1:8188"
raw = urllib.request.urlopen(URL + "/history", timeout=20).read().decode("utf-8", "replace")
hist = json.loads(raw, strict=False)
print("history entries:", len(hist))

shown = 0
for pid, item in list(hist.items())[-4:]:
    st = item.get("status", {})
    print("\n=== prompt_id", pid[:12], "completed=", st.get("completed"),
          "status_str=", st.get("status_str"))
    outs = item.get("outputs", {})
    for node_id, node_out in outs.items():
        print("   node", node_id, "keys:", list(node_out.keys()))
        print("   node-level .get('type') ->", repr(node_out.get("type")),
              "  <-- app checks THIS")
        for img in node_out.get("images", []) or []:
            print("      image dict:", img, "  <-- 'type' lives HERE")
            shown += 1
print("\nimages found:", shown)

print("\n=== INPUT_DIR mismatch proof ===")
APP_INPUT = r"C:\Users\jakeb\Pictures\ComfyUI_Generated\input"
COMFY_INPUT = r"C:\ComfyUI-Desktop\ComfyUI_windows_portable\ComfyUI\input"
print("app INPUT_DIR   :", APP_INPUT, "exists:", os.path.isdir(APP_INPUT))
print("ComfyUI real in :", COMFY_INPUT, "exists:", os.path.isdir(COMFY_INPUT))
print("SAME DIR?", os.path.normcase(APP_INPUT) == os.path.normcase(COMFY_INPUT))
print("-> LoadImage resolves names against ComfyUI real input dir only.")
