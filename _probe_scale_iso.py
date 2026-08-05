"""Multi-hypothesis isolation of the set_widget_scaling segfault.
Each hypothesis runs in its OWN subprocess so a segfault doesn't kill the run.
Usage: _probe_scale_iso.py <hypothesis>
"""
import os, sys, traceback
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
H = sys.argv[1] if len(sys.argv) > 1 else "all"

import customtkinter as ctk
print("CTk version:", ctk.__version__)

if H == "h1":
    # H1: plain CTk window + many widgets -> does set_widget_scaling alone crash?
    root = ctk.CTk(); root.geometry("900x700")
    for i in range(40):
        ctk.CTkButton(root, text="b%d" % i).pack()
        ctk.CTkOptionMenu(root, values=["a", "b"]).pack()
    root.update_idletasks(); root.update()
    ctk.set_widget_scaling(1.1)
    root.update_idletasks(); root.update()
    print("H1 RESULT: plain CTk widgets survive set_widget_scaling")
    root.destroy()

elif H == "h2":
    # H2: raw tk.Canvas child (AutoHideScrollFrame pattern)
    import tkinter as tk
    root = ctk.CTk(); root.geometry("900x700")
    import ComfyUI_App as A
    f = A.AutoHideScrollFrame(root); f.pack(fill="both", expand=True)
    for i in range(20):
        ctk.CTkButton(f.inner, text="x%d" % i).pack()
    root.update_idletasks(); root.update()
    ctk.set_widget_scaling(1.1)
    root.update_idletasks(); root.update()
    print("H2 RESULT: AutoHideScrollFrame survives set_widget_scaling")
    root.destroy()

elif H == "h3":
    # H3: raw ImageTk.PhotoImage on a CTkLabel (app's _show_thumb pattern)
    from PIL import Image, ImageTk
    root = ctk.CTk(); root.geometry("900x700")
    lbl = ctk.CTkLabel(root, text="")
    lbl.pack()
    img = Image.new("RGB", (200, 150), (90, 40, 20))
    tkimg = ImageTk.PhotoImage(img)
    lbl.configure(image=tkimg, text="")
    lbl.image = tkimg
    root.update_idletasks(); root.update()
    ctk.set_widget_scaling(1.1)
    root.update_idletasks(); root.update()
    print("H3 RESULT: raw ImageTk.PhotoImage survives set_widget_scaling")
    root.destroy()

elif H == "h4":
    # H4: the glass AcrylicBackground canvas
    import ComfyUI_App as A
    from glass import AcrylicBackground
    root = ctk.CTk(); root.geometry("900x700")
    try:
        g = AcrylicBackground(root)
        root.update_idletasks(); root.update()
        ctk.set_widget_scaling(1.1)
        root.update_idletasks(); root.update()
        print("H4 RESULT: AcrylicBackground survives set_widget_scaling")
    except Exception:
        print("H4 setup error:\n" + traceback.format_exc())
    root.destroy()

elif H == "h5":
    # H5: FULL app, call ctk.set_widget_scaling directly (bypass _set_scaling)
    import ComfyUI_App as A
    A.ComfyUIApp._start_backend_threads = lambda self: None
    A.ComfyUIApp._start_backend = lambda self: None
    A.ComfyUIApp._start_vram_watch = lambda self: None
    A.os.startfile = lambda p: None
    root = ctk.CTk(); root.geometry("1280x1120")
    app = A.ComfyUIApp(root)
    root.update_idletasks(); root.update()
    print("H5: app built, calling set_widget_scaling(1.1)...")
    sys.stdout.flush()
    ctk.set_widget_scaling(1.1)
    print("H5: returned, pumping event loop...")
    sys.stdout.flush()
    root.update_idletasks(); root.update()
    print("H5 RESULT: FULL APP survived set_widget_scaling")
    root.destroy()

elif H == "h6":
    # H6: full app WITHOUT the CTkFont objects being rescaled
    import ComfyUI_App as A
    A.ComfyUIApp._start_backend_threads = lambda self: None
    A.ComfyUIApp._start_backend = lambda self: None
    A.ComfyUIApp._start_vram_watch = lambda self: None
    A.os.startfile = lambda p: None
    root = ctk.CTk(); root.geometry("1280x1120")
    app = A.ComfyUIApp(root)
    root.update_idletasks(); root.update()
    # count tracked widgets
    from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker as ST
    n = sum(len(v) for v in ST.window_widgets_dict.values())
    print("H6: ScalingTracker tracks %d widgets across %d windows"
          % (n, len(ST.window_widgets_dict)))
    dead = 0
    for win, widgets in ST.window_widgets_dict.items():
        for w in widgets:
            try:
                if not w.winfo_exists():
                    dead += 1
            except Exception:
                dead += 1
    print("H6 RESULT: %d DESTROYED-but-still-tracked widgets" % dead)
    print("   -> set_widget_scaling calls _set_scaling on each tracked widget;")
    print("      destroyed widgets => invalid Tcl command => segfault")
    root.destroy()

print("DONE-OK")
