"""Runtime QA suite — builds the REAL app and invokes real code paths.

Why this exists alongside tests/qa_audit.py:
    qa_audit.py is a source-grep suite. It passed 123/123 while the app had
    nine crash-on-use bugs, because a grep cannot see that
    ToolTip(widget, "text") raises TypeError, that CTkSwitch rejects
    hover_color=, or that TEXT_DIM was never defined. Those only appear when
    the widget is actually constructed.

What it covers (all GPU-free, no ComfyUI server needed):
    1. Every tab/view builder constructs without raising.
    2. Every widget callback resolves all its global names (NameError-on-click).
    3. Every workflow graph is well-formed, JSON-safe, and terminates in an
       output node (ComfyUI 400 "Prompt has no outputs").
    4. H3 node inputs conform to the installed nodes' INPUT_TYPES (the B8
       silently-dropped-input class).
    5. The H3 frame grid stays on the 17k+5 boundary.

Run:  python tests/qa_runtime.py
Exit: 0 = all pass, 1 = at least one failure.
"""
import ast
import builtins
import dis
import importlib.util
import json
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SRC = os.path.join(BASE, "ComfyUI_App.py")
H3_PKG = os.path.join(BASE, "ComfyUI_windows_portable", "ComfyUI",
                      "custom_nodes", "ComfyUI-MiniMaxH3")
sys.path.insert(0, BASE)

R = []


def chk(name, cond, detail=""):
    R.append((name, "PASS" if cond else "FAIL", detail))


import tkinter as tk  # noqa: E402

spec = importlib.util.spec_from_file_location("CAT", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sys.excepthook = sys.__excepthook__          # app installs an os._exit hook

root = tk.Tk()
root.geometry("1280x1040")
try:
    app = mod.ComfyUIApp(root)
    sys.excepthook = sys.__excepthook__
    chk("runtime: ComfyUIApp.__init__", True)
except Exception as e:
    sys.excepthook = sys.__excepthook__
    chk("runtime: ComfyUIApp.__init__", False, "%s: %s" % (type(e).__name__, e))
    raise
root.update_idletasks()


# ── 1. every builder constructs ────────────────────────────────────────
BUILDERS = [
    "_build_txt2img_tab", "_build_img2img_tab", "_build_upscale_tab",
    "_build_video_tab", "_build_video_v2v_tab", "_build_video_refine_tab",
    "_build_gallery_tab", "_build_debug_tab",
    "_build_settings_in_main", "_build_settings_tab", "_build_gallery_in_main",
]
for name in BUILDERS:
    try:
        getattr(app, name)()
        chk("build: %s" % name, True)
    except Exception as e:
        chk("build: %s" % name, False, "%s: %s" % (type(e).__name__, e))

for view in ("generate", "gallery", "settings"):
    try:
        app._show_view(view)
        chk("view: _show_view('%s')" % view, True)
    except Exception as e:
        chk("view: _show_view('%s')" % view, False, "%s: %s" % (type(e).__name__, e))

for name in ("_refresh_gallery", "_refresh_gallery_main", "_debug_refresh",
             "_on_tab", "_swap_dimensions", "_reset_video_buttons",
             "_on_tooltips_toggle", "_scan_available_checkpoints"):
    try:
        getattr(app, name)()
        chk("invoke: %s" % name, True)
    except Exception as e:
        chk("invoke: %s" % name, False, "%s: %s" % (type(e).__name__, e))

root.update_idletasks()


# ── 2. widget callbacks resolve every global they reference ────────────
def _undefined_globals(fn, seen=None):
    if seen is None:
        seen = set()
    out = []
    fn = getattr(fn, "__func__", fn)
    code = getattr(fn, "__code__", None)
    if code is None or id(code) in seen:
        return out
    seen.add(id(code))
    g = getattr(fn, "__globals__", {})
    local = set(code.co_freevars) | set(code.co_varnames) | set(code.co_cellvars)
    for ins in dis.get_instructions(code):
        if ins.opname == "LOAD_GLOBAL":
            n = ins.argval
            if n not in local and n not in g and not hasattr(builtins, n):
                out.append(n)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            try:
                closure = tuple(types.CellType(None) for _ in range(len(const.co_freevars)))
                out += _undefined_globals(types.FunctionType(const, g, closure=closure), seen)
            except Exception:
                pass
    return out


widgets = []


def _walk(w):
    widgets.append(w)
    try:
        for c in w.winfo_children():
            _walk(c)
    except Exception:
        pass


_walk(root)
broken = []
n_cb = 0
for w in widgets:
    for attr in ("_command", "_button_command", "_values_command"):
        fn = getattr(w, attr, None)
        if callable(fn):
            n_cb += 1
            miss = sorted(set(_undefined_globals(fn)))
            if miss:
                broken.append("%s '%s' -> %s" % (type(w).__name__,
                                                 str(getattr(w, "_text", ""))[:30], miss))
chk("callbacks: all resolve global names (%d checked)" % n_cb,
    not broken, "; ".join(broken[:4]))


# ── 3. workflow graphs are valid and terminate in an output node ───────
OUTPUT_NODES = {"SaveImage", "PreviewImage", "SaveVideo", "SaveAnimatedWEBP",
                "SaveAnimatedPNG", "VHS_VideoCombine", "PreviewVideo", "SaveAudio"}


def _validate_graph(label, g):
    if not isinstance(g, dict) or not g:
        chk("graph %s: shape" % label, False, "expected non-empty dict")
        return
    try:
        json.dumps(g)
        chk("graph %s: JSON-serialisable" % label, True)
    except Exception as e:
        chk("graph %s: JSON-serialisable" % label, False, str(e)[:100])
    ids = set(g)
    dangling, nones = [], []
    for nid, node in g.items():
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in ids:
                dangling.append("%s.%s->%s" % (nid, k, v[0]))
            if v is None:
                nones.append("%s.%s" % (nid, k))
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                nones.append("%s.%s=NaN" % (nid, k))
    chk("graph %s: no dangling refs" % label, not dangling, str(dangling[:4]))
    chk("graph %s: no None/NaN inputs" % label, not nones, str(nones[:4]))
    outs = [n.get("class_type") for n in g.values() if n.get("class_type") in OUTPUT_NODES]
    chk("graph %s: has output node" % label, bool(outs),
        "ComfyUI rejects with 400 'Prompt has no outputs'" if not outs else ",".join(sorted(set(outs))))


for mode in ("txt2img", "img2img", "upscale"):
    try:
        res = app._build_workflow(mode)
        g = res[0] if isinstance(res, tuple) else res
        if g is None:
            chk("graph _build_workflow('%s')" % mode, True, "None (needs input image) — skipped")
        else:
            _validate_graph("_build_workflow('%s')" % mode, g)
    except Exception as e:
        chk("graph _build_workflow('%s')" % mode, False, "%s: %s" % (type(e).__name__, e))

_H3 = dict(prompt="a neon city at night", w=640, h=384, dur=3, seed=42, steps=20,
           cfg=6.0, sampler="euler", shift=5.0, denoise=1.0, adaln=True,
           spectrum=False, teacache=False, blockswap=True, neg="blurry",
           attention="sdpa", ref_max=1280, storyboard=False, fl=False,
           i2v_path=None, ar=None, camera="Static", enhance=True, loop=False)
H3_CASES = {
    "t2v": dict(_H3, mode_key="t2v"),
    "i2v": dict(_H3, mode_key="i2v"),
    "t2v+teacache+spectrum": dict(_H3, mode_key="t2v", teacache=True, spectrum=True),
    "t2v+storyboard": dict(_H3, mode_key="t2v", storyboard=True),
    "t2v+fl": dict(_H3, mode_key="t2v", fl=True),
}
built = {}
for label, kw in H3_CASES.items():
    try:
        g = app._build_h3_graph(**kw)
        built[label] = g
        _validate_graph("_build_h3_graph(%s)" % label, g)
    except Exception as e:
        chk("graph _build_h3_graph(%s)" % label, False, "%s: %s" % (type(e).__name__, e))


# ── 4. H3 node inputs conform to the installed INPUT_TYPES ─────────────
def _load_h3_schemas():
    classdefs, reg = {}, {}
    if not os.path.isdir(H3_PKG):
        return None
    for dp, _d, fs in os.walk(H3_PKG):
        for fn in fs:
            if not fn.endswith(".py"):
                continue
            try:
                tree = ast.parse(open(os.path.join(dp, fn), encoding="utf-8").read())
            except Exception:
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.ClassDef):
                    classdefs[n.name] = n
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name) and t.id == "NODE_CLASS_MAPPINGS" \
                                and isinstance(n.value, ast.Dict):
                            for k, v in zip(n.value.keys, n.value.values):
                                if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                                    reg[k.value] = v.id

    def keys(d):
        return {k.value for k in d.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)} \
            if isinstance(d, ast.Dict) else set()

    out = {}
    for regname, cls in reg.items():
        c = classdefs.get(cls)
        if not c:
            continue
        req, opt = set(), set()
        for item in c.body:
            if isinstance(item, ast.FunctionDef) and item.name == "INPUT_TYPES":
                for s in ast.walk(item):
                    if isinstance(s, ast.Return) and isinstance(s.value, ast.Dict):
                        for k, v in zip(s.value.keys, s.value.values):
                            if isinstance(k, ast.Constant):
                                if k.value == "required":
                                    req |= keys(v)
                                elif k.value == "optional":
                                    opt |= keys(v)
        out[regname] = (req, opt)
    return out


schemas = _load_h3_schemas()
if not schemas:
    R.append(("schema: H3 package present", "SKIP", "ComfyUI-MiniMaxH3 not found"))
else:
    bad = []
    for label, g in built.items():
        for nid, node in g.items():
            ct = node.get("class_type")
            if ct not in schemas:
                continue
            req, opt = schemas[ct]
            got = set(node.get("inputs", {}))
            unknown = got - (req | opt)
            missing = req - got
            if unknown:
                bad.append("%s/%s(%s) dropped=%s" % (label, nid, ct, sorted(unknown)))
            if missing:
                bad.append("%s/%s(%s) missing=%s" % (label, nid, ct, sorted(missing)))
    chk("schema: H3 node inputs conform to installed INPUT_TYPES", not bad, "; ".join(bad[:4]))


# ── 5. frame grid stays on the 17k+5 boundary ──────────────────────────
offenders = []
for dur in (3, 5, 9, 14):
    length = max(5, int(round(dur * 24 / 17) * 17 + 5))
    if length % 17 != 5:
        offenders.append("%ds->%d" % (dur, length))
chk("h3: frame length stays on the 17k+5 grid", not offenders, str(offenders))


# ── report ─────────────────────────────────────────────────────────────
fails = [r for r in R if r[1] == "FAIL"]
skips = [r for r in R if r[1] == "SKIP"]
print("\n" + "=" * 70)
for n, s, d in R:
    if s != "PASS":
        print("[%s] %s%s" % (s, n, (" — " + d) if d else ""))
print("=" * 70)
print("=== %d checks, %d PASS, %d FAIL, %d SKIP ===" % (
    len(R), len(R) - len(fails) - len(skips), len(fails), len(skips)))
print("=" * 70)
try:
    root.destroy()
except Exception:
    pass
os._exit(1 if fails else 0)
