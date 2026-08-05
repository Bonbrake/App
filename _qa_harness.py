"""HEADLESS QA HARNESS - ComfyUI_Uncensored
Instantiates the REAL app, then invokes EVERY button command, menu callback,
key binding and handler, recording pass/fail per feature.

Backend spawning is neutralized so no ComfyUI process is started or killed.
"""
import os, sys, traceback, json, time
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")

import ComfyUI_App as A
import customtkinter as ctk
import tkinter as tk

RESULTS = []
def rec(name, ok, detail=""):
    RESULTS.append((name, ok, str(detail)[:200]))
    print(("  PASS  " if ok else "  FAIL  ") + name + (("  :: " + str(detail)[:160]) if detail else ""))

# --- neutralize process spawning / OS side effects -------------------------
A.ComfyUIApp._start_backend_threads = lambda self: None
A.ComfyUIApp._start_backend = lambda self: None
A.ComfyUIApp._start_vram_watch = lambda self: None
A.ComfyUIApp._check_for_errors = lambda self: None
_started = []
A.os.startfile = lambda p: _started.append(p)
A.subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(AssertionError("Popen called!"))
A.filedialog.askopenfilename = lambda **k: ""
A.messagebox.askyesno = lambda *a, **k: False

root = ctk.CTk()
root.geometry("1280x1120")

print("=" * 78); print("PHASE 1: CONSTRUCTION"); print("=" * 78)
try:
    app = A.ComfyUIApp(root)
    rec("App constructs", True)
except Exception as e:
    rec("App constructs", False, traceback.format_exc())
    raise SystemExit(1)

root.update_idletasks(); root.update()

# ---------------------------------------------------------------- widget walk
def walk(w, depth=0, out=None):
    if out is None: out = []
    out.append((depth, w))
    for c in w.winfo_children():
        walk(c, depth + 1, out)
    return out

allw = walk(root)
print("\ntotal widgets: %d" % len(allw))

print("\n" + "=" * 78); print("PHASE 2: EVERY BUTTON'S COMMAND"); print("=" * 78)
buttons = [w for _, w in allw if isinstance(w, ctk.CTkButton)]
print("buttons found: %d" % len(buttons))
for b in buttons:
    try:
        txt = b.cget("text")
    except Exception:
        txt = "?"
    cmd = getattr(b, "_command", None)
    if cmd is None:
        rec("Button '%s' has command" % txt, False, "NO COMMAND BOUND")
        continue
    try:
        cmd()
        root.update_idletasks()
        rec("Button '%s' invoke" % txt, True)
    except Exception as e:
        rec("Button '%s' invoke" % txt, False, traceback.format_exc().strip().split("\n")[-1])

print("\n" + "=" * 78); print("PHASE 3: EVERY OPTION MENU (all values)"); print("=" * 78)
menus = [w for _, w in allw if isinstance(w, ctk.CTkOptionMenu)]
print("option menus found: %d" % len(menus))
for m in menus:
    try:
        vals = m.cget("values")
    except Exception:
        vals = []
    cmd = getattr(m, "_command", None)
    label = (vals[0] if vals else "?")
    for v in (vals or [])[:12]:
        try:
            m.set(v)
            if cmd:
                cmd(v)
            root.update_idletasks()
            rec("OptionMenu[%s] set '%s'" % (label, v), True)
        except Exception:
            rec("OptionMenu[%s] set '%s'" % (label, v), False,
                traceback.format_exc().strip().split("\n")[-1])

print("\n" + "=" * 78); print("PHASE 4: TAB SWITCHING"); print("=" * 78)
for name in ["Text to Image", "Image to Image", "Upscale", "Text to Image"]:
    try:
        app.tabview.set(name)
        app._on_tab()
        root.update_idletasks()
        got = app.tabview.get()
        vis = app.current_tab
        ok = (got == name)
        rec("Tab set '%s' (visible='%s', current_tab='%s')" % (name, got, vis), ok,
            "" if ok else "tabview.get() != requested")
    except Exception:
        rec("Tab set '%s'" % name, False, traceback.format_exc().strip().split("\n")[-1])
    time.sleep(0.35)

print("\n" + "=" * 78); print("PHASE 5: NAV VIEWS"); print("=" * 78)
for nm, fn in [("generate", app._focus_generate), ("gallery", app._focus_gallery),
               ("settings", app._focus_settings), ("generate", app._focus_generate)]:
    try:
        fn(); root.update_idletasks()
        rec("Nav -> %s" % nm, True)
    except Exception:
        rec("Nav -> %s" % nm, False, traceback.format_exc().strip().split("\n")[-1])

print("\n" + "=" * 78); print("PHASE 6: KEY BINDINGS"); print("=" * 78)
for seq in ["<Control-Return>", "<Shift-Return>", "<Control-e>", "<Control-E>",
            "<Control-r>", "<F5>", "<Control-o>", "<Control-l>", "<F1>",
            "<Control-Shift-V>"]:
    binding = root.bind(seq)
    rec("Key %s bound" % seq, bool(binding), "" if binding else "NOT BOUND")

print("\n" + "=" * 78); print("PHASE 7: HANDLER SMOKE TESTS"); print("=" * 78)
checks = [
    ("_swap_dimensions", lambda: app._swap_dimensions()),
    ("_save_history_simple", lambda: app._save_history_simple()),
    ("_open_last_preview", lambda: app._open_last_preview()),
    ("_refresh_gallery_main", lambda: app._refresh_gallery_main()),
    ("_load_recent_into_preview", lambda: app._load_recent_into_preview()),
    ("_unload_vram", lambda: app._unload_vram()),
    ("_scan_available_checkpoints", lambda: app._scan_available_checkpoints()),
    ("_show_shortcut_modal", lambda: app._show_shortcut_modal()),
    ("_add_style_tag", lambda: app._add_style_tag("neon")),
    ("_gallery_toggle", lambda: app._gallery_toggle("x.png")),
    ("_gallery_select_all", lambda: app._gallery_select_all()),
    ("_gallery_delete_selected", lambda: app._gallery_delete_selected()),
    ("_init_drag_system", lambda: app._init_drag_system()),
    ("_prompt_for_mode(txt2img)", lambda: app._prompt_for_mode("txt2img")),
    ("_prompt_for_mode(upscale)", lambda: app._prompt_for_mode("upscale")),
    ("_cancel_generate", lambda: app._cancel_generate()),
    ("_cleanup_symlinks", lambda: app._cleanup_symlinks()),
    ("_vram_critical", lambda: app._vram_critical()),
]
for nm, fn in checks:
    try:
        fn(); root.update_idletasks()
        rec("Handler %s" % nm, True)
    except Exception:
        rec("Handler %s" % nm, False, traceback.format_exc().strip().split("\n")[-1])

print("\n" + "=" * 78); print("PHASE 8: WORKFLOW BUILDER (all 3 modes)"); print("=" * 78)
for mode in ["txt2img", "img2img", "upscale"]:
    try:
        wf, ckpt = app._build_workflow(mode)
        ks = wf.get("KSampler", {}).get("inputs", {})
        problems = []
        if "KSampler" in wf and "denoise" not in ks:
            problems.append("KSampler MISSING 'denoise' (server requires it)")
        li = wf.get("LoadImage", {}).get("inputs", {}).get("image")
        if li and ("\\" in li or "/" in li):
            problems.append("LoadImage path has separator: %r" % li)
        ci = wf.get("LastNode", {}).get("inputs", {})
        for bad in ("model_strength", "clip_strength"):
            if bad in ci:
                problems.append("CheckpointLoaderSimple has bogus '%s'" % bad)
        si = wf.get("SaveImage", {}).get("inputs", {})
        if "format" in si:
            problems.append("SaveImage has unsupported 'format' input")
        up = wf.get("Upscale", {}).get("inputs", {})
        for bad in ("width", "height"):
            if bad in up:
                problems.append("ImageUpscaleWithModel has bogus '%s'" % bad)
        rec("Workflow build '%s' (nodes=%d)" % (mode, len(wf)), not problems,
            "; ".join(problems))
    except Exception:
        rec("Workflow build '%s'" % mode, False,
            traceback.format_exc().strip().split("\n")[-1])

print("\n" + "=" * 78); print("PHASE 9: DUPLICATE / LAYOUT AUDIT"); print("=" * 78)
sb_kids = app.sidebar.winfo_children() if hasattr(app, "sidebar") else []
print("sidebar children: %d" % len(sb_kids))
for k in sb_kids:
    t = ""
    try: t = k.cget("text")
    except Exception: pass
    try:
        if isinstance(k, ctk.CTkOptionMenu): t = "OPTIONMENU " + str(k.cget("values"))
    except Exception: pass
    print("   %-22s %s" % (type(k).__name__, t))

rec("status_label is inside sidebar (dup of status bar)",
    not (hasattr(app, "status_label") and str(app.status_label).startswith(str(app.sidebar))),
    "status_label parent=%s" % (app.status_label.winfo_parent() if hasattr(app, "status_label") else "?"))

rec("preview_label is NOT aliased to status_label",
    getattr(app, "preview_label", None) is not getattr(app, "status_label", None),
    "preview_label IS status_label -> generated image gets dumped into the status bar")

tf = getattr(app, "thumb_frame", None)
rec("thumb_frame is mapped (visible)", bool(tf and tf.winfo_ismapped()),
    "thumb_frame exists but is never gridded -> invisible thumbnails built every gen")

pt = getattr(app, "preview_thumbs", None)
rec("preview_thumbs 'Recent' strip absent (Gallery covers it)", pt is None,
    "Recent strip present in preview pane = duplicate of Gallery tab")

print("\n" + "=" * 78); print("PHASE 10: TIMER / LOOP AUDIT"); print("=" * 78)
import re
srctxt = open(r"C:\ComfyUI-Desktop\ComfyUI_App.py", encoding="utf-8", errors="replace").read()
anim = len(re.findall(r"after\([^)]*_animate_gradient", srctxt))
hdr = len(re.findall(r"after\([^)]*_start_header_gradient", srctxt))
bkt = len(re.findall(r"after\([^)]*_start_backend_threads", srctxt))
rec("only ONE gradient loop entry point", (anim + hdr) <= 2,
    "_animate_gradient scheduled %dx, _start_header_gradient %dx -> concurrent 20fps repaint loops" % (anim, hdr))
rec("backend threads started once", bkt <= 1,
    "_start_backend_threads scheduled %dx -> duplicate ComfyUI spawn" % bkt)

print("\n" + "=" * 78)
p = sum(1 for _, ok, _ in RESULTS if ok)
f = sum(1 for _, ok, _ in RESULTS if not ok)
print("TOTAL: %d checks | PASS %d | FAIL %d" % (len(RESULTS), p, f))
print("=" * 78)
print("\nFAILURES:")
for n, ok, d in RESULTS:
    if not ok:
        print("  * %s\n      %s" % (n, d))

with open(r"C:\ComfyUI-Desktop\_qa_results.json", "w") as fh:
    json.dump([{"check": n, "pass": ok, "detail": d} for n, ok, d in RESULTS], fh, indent=2)

try:
    root.destroy()
except Exception:
    pass
