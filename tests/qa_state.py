"""Behavioural state-machine tests — prove the generate lock always releases.

These drive the real methods with the network stubbed out, then assert on
observable state. A grep can confirm a line exists; only this can confirm the
app is still usable after a failure.

Covers:
  * poll timeout must clear _generate_lock (else every later Generate click is
    silently swallowed and the app looks dead until restart)
  * a failed queue (non-200) must clear the lock AND restore the buttons
  * a successful queue must hand off to the poller and NOT prematurely reset
  * cancel must clear the lock
  * the three video buttons are independent widgets
"""
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SRC = os.path.join(BASE, "ComfyUI_App.py")
sys.path.insert(0, BASE)

import tkinter as tk  # noqa: E402

spec = importlib.util.spec_from_file_location("CAT", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sys.excepthook = sys.__excepthook__

R = []


def chk(name, cond, detail=""):
    R.append((name, "PASS" if cond else "FAIL", detail))


root = tk.Tk()
root.geometry("1280x1040")
app = mod.ComfyUIApp(root)
sys.excepthook = sys.__excepthook__
for m in ("_build_video_tab", "_build_video_v2v_tab", "_build_video_refine_tab"):
    getattr(app, m)()
root.update_idletasks()


# ── the three video buttons must be distinct widgets ───────────────────
ids = {n: id(getattr(app, n, None)) for n in ("vgen", "v2vgen", "rgen")}
chk("buttons: vgen/v2vgen/rgen are distinct widgets",
    len(set(ids.values())) == 3 and None not in [getattr(app, n, None) for n in ids],
    str(ids))
for mode, attr in (("t2v", "vgen"), ("v2v", "v2vgen"), ("refine", "rgen")):
    got = app._video_button_for(mode)
    chk("buttons: _video_button_for('%s') -> self.%s" % (mode, attr),
        got is getattr(app, attr))


# ── poll timeout must release the lock ─────────────────────────────────
app._generate_lock = True
app._poll_attempts = 601
app._running = True
app._poll_history()
chk("lock: poll timeout clears _generate_lock",
    app._generate_lock is False,
    "still locked — every later Generate click is silently swallowed")
chk("lock: poll timeout clears _gen_start_time",
    getattr(app, "_gen_start_time", None) is None)
chk("lock: poll timeout restores video buttons",
    not str(app.vgen.cget("text")).startswith("Cancel"),
    "button text=%r" % app.vgen.cget("text"))


# ── cancel must release the lock ───────────────────────────────────────
app._generate_lock = True
app.last_prompt_id = None
app._cancel_generate()
chk("lock: _cancel_generate clears _generate_lock", app._generate_lock is False)


# ── a FAILED queue must release the lock and restore the buttons ───────
class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}

    def json(self):
        return self._payload


real_post = mod.requests.post
real_get = mod.requests.get
try:
    mod.requests.post = lambda *a, **k: _Resp(500, {"error": {"message": "synthetic failure"}})
    mod.requests.get = lambda *a, **k: _Resp(200, {})
    app._generate_lock = False
    app._last_generate = 0
    app._poll_handoff = False
    app._start_video_gen("t2v")
    chk("lock: failed queue clears _generate_lock", app._generate_lock is False)
    chk("lock: failed queue leaves no poller handoff",
        getattr(app, "_poll_handoff", False) is False)
    chk("buttons: failed queue restores Generate label",
        not str(app.vgen.cget("text")).startswith("Cancel"),
        "button text=%r" % app.vgen.cget("text"))
finally:
    mod.requests.post = real_post
    mod.requests.get = real_get


# ── a SUCCESSFUL queue hands off to the poller ─────────────────────────
try:
    mod.requests.post = lambda *a, **k: _Resp(200, {"prompt_id": "synthetic-123"})
    mod.requests.get = lambda *a, **k: _Resp(200, {})
    app._generate_lock = False
    app._last_generate = 0
    app._poll_handoff = False
    app._start_video_gen("t2v")
    chk("lock: successful queue clears _generate_lock", app._generate_lock is False)
    chk("poller: successful queue sets the handoff flag",
        getattr(app, "_poll_handoff", False) is True,
        "poller must own button state until the job finishes")
    chk("poller: successful queue records prompt_id",
        app.last_prompt_id == "synthetic-123", str(app.last_prompt_id))
finally:
    mod.requests.post = real_post
    mod.requests.get = real_get


# ── /free must be called once per generation, not three times ──────────
calls = {"n": 0}
try:
    def _counting_post(url, *a, **k):
        if url.endswith("/free"):
            calls["n"] += 1
            return _Resp(200, {})
        return _Resp(500, {"error": {"message": "stop here"}})

    mod.requests.post = _counting_post
    mod.requests.get = lambda *a, **k: _Resp(200, {})
    app._generate_lock = False
    app._last_generate = 0
    app._start_video_gen("t2v")
    chk("perf: /free called exactly once per video gen", calls["n"] == 1,
        "called %d times (each has a 5s timeout -> %ds stall when backend is down)"
        % (calls["n"], calls["n"] * 5))
finally:
    mod.requests.post = real_post
    mod.requests.get = real_get


fails = [r for r in R if r[1] == "FAIL"]
print("\n" + "=" * 70)
for n, s, d in R:
    if s != "PASS":
        print("[%s] %s%s" % (s, n, (" — " + d) if d else ""))
print("=" * 70)
print("=== %d checks, %d PASS, %d FAIL ===" % (len(R), len(R) - len(fails), len(fails)))
print("=" * 70)
try:
    root.destroy()
except Exception:
    pass
os._exit(1 if fails else 0)
