"""Precise root-cause confirmation. Separates 'destroyed' from 'exception'
and finds where AutoHideScrollFrame is actually used."""
import os, sys, traceback, re
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
import customtkinter as ctk
import ComfyUI_App as A

print("=" * 70)
print("PART 1: is AutoHideScrollFrame actually instantiated by the app?")
print("=" * 70)
src = open(r"C:\ComfyUI-Desktop\ComfyUI_App.py", encoding="utf-8", errors="replace").read()
for i, l in enumerate(src.split("\n"), 1):
    if "AutoHideScrollFrame" in l or "CTkScrollableFrame" in l:
        print("  L%-5d %s" % (i, l.strip()[:110]))

print("\n  -- ttk.Scrollbar width support --")
import tkinter as tk
from tkinter import ttk
r0 = tk.Tk(); r0.withdraw()
try:
    ttk.Scrollbar(r0, orient="vertical", width=10)
    print("  ttk.Scrollbar accepts width -> OK")
except Exception as e:
    print("  ttk.Scrollbar(width=10) FAILS: %s" % e)
try:
    ttk.Scrollbar(r0, orient="vertical")
    print("  ttk.Scrollbar without width -> OK")
except Exception as e:
    print("  ttk.Scrollbar plain FAILS: %s" % e)
r0.destroy()

print("\n" + "=" * 70)
print("PART 2: ScalingTracker precise census on the REAL app")
print("=" * 70)
A.ComfyUIApp._start_backend_threads = lambda self: None
A.ComfyUIApp._start_backend = lambda self: None
A.ComfyUIApp._start_vram_watch = lambda self: None
A.os.startfile = lambda p: None

root = ctk.CTk(); root.geometry("1280x1120")
app = A.ComfyUIApp(root)
root.update_idletasks(); root.update()

from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker as ST

def census(tag):
    alive = destroyed = errored = 0
    bad = []
    for win, widgets in ST.window_widgets_dict.items():
        for w in widgets:
            try:
                if w.winfo_exists():
                    alive += 1
                else:
                    destroyed += 1
                    bad.append(type(w).__name__)
            except Exception as e:
                errored += 1
                bad.append("%s!%s" % (type(w).__name__, type(e).__name__))
    print("  [%s] tracked=%d alive=%d destroyed=%d errored=%d"
          % (tag, alive + destroyed + errored, alive, destroyed, errored))
    if bad:
        from collections import Counter
        print("      offenders:", Counter(bad).most_common(8))
    return destroyed + errored

census("fresh build")

print("\n  -- now destroy sidebar like _rebuild_ui does --")
app.sidebar.destroy()
root.update_idletasks()
n = census("after sidebar.destroy()")

print("\n" + "=" * 70)
print("PART 3: does set_widget_scaling touch destroyed widgets?")
print("=" * 70)
import inspect
try:
    print(inspect.getsource(ST.set_widget_scaling))
except Exception as e:
    print("  (source unavailable: %s)" % e)

print("\n  attempting set_widget_scaling with %d dead tracked widgets..." % n)
sys.stdout.flush()
try:
    ctk.set_widget_scaling(1.1)
    root.update_idletasks(); root.update()
    print("  SURVIVED")
except Exception:
    print("  EXCEPTION:\n" + traceback.format_exc())
print("DONE-OK")
