"""Pin the EXACT widget in _build_main that makes set_widget_scaling segfault.
Usage: _probe_pin.py <case>
"""
import os, sys, traceback
sys.path.insert(0, r"C:\ComfyUI-Desktop")
os.chdir(r"C:\ComfyUI-Desktop")
import customtkinter as ctk
import ComfyUI_App as A
from ComfyUI_App import (MODELS, PRESETS, BG_APP, BG_CARD_ALT, BORDER, BRAND,
                         BRAND_HOVER, TEXT, DROPDOWN_FG, DROPDOWN_TEXT,
                         DROPDOWN_HOVER, ACCENT2, ACCENT2_HOVER, ToolTip, TOOLTIPS)

case = sys.argv[1]
root = ctk.CTk(); root.geometry("1280x1120")
F = ctk.CTkFont(size=12)

top = ctk.CTkFrame(root, fg_color=BG_APP, corner_radius=0)
top.grid(row=0, column=1, padx=16, pady=12, sticky="nsew")

if case == "optionmenu":
    m = ctk.CTkOptionMenu(top, values=list(MODELS.keys()), font=F,
                          variable=ctk.StringVar(value=list(MODELS.keys())[0]),
                          fg_color=BG_CARD_ALT, button_color=BORDER,
                          button_hover_color=BRAND_HOVER, text_color=TEXT,
                          dropdown_fg_color=DROPDOWN_FG, dropdown_text_color=DROPDOWN_TEXT,
                          dropdown_hover_color=DROPDOWN_HOVER, width=160)
    m.grid(row=0, column=0)

elif case == "optionmenu_tooltip":
    m = ctk.CTkOptionMenu(top, values=list(MODELS.keys()), font=F, width=160)
    m.grid(row=0, column=0)
    ToolTip(m, *TOOLTIPS["Model"])

elif case == "tabview":
    tv = ctk.CTkTabview(top, fg_color="transparent",
                        segmented_button_fg_color=BG_CARD_ALT,
                        segmented_button_selected_color=BRAND,
                        segmented_button_selected_hover_color=BRAND_HOVER,
                        text_color=TEXT)
    tv.grid(row=1, column=0, sticky="nsew")
    tv.add("Text to Image"); tv.add("Image to Image"); tv.add("Upscale")
    tv.set("Text to Image")

elif case == "tabview_override":
    tv = ctk.CTkTabview(top, fg_color="transparent")
    tv.grid(row=1, column=0, sticky="nsew")
    tv.add("A"); tv.add("B"); tv.set("A")
    # the suspicious line 1196
    tv._segmented_button.configure(command=lambda *a: None)

elif case == "header_label":
    lbl = ctk.CTkLabel(top, text="", height=56)
    lbl.grid(row=2, column=0, sticky="nsew")

elif case == "font_shared":
    # Shared CTkFont across many widgets - CTkFont rescales on set_widget_scaling
    shared = ctk.CTkFont(size=12)
    for i in range(30):
        ctk.CTkLabel(top, text="x", font=shared).grid(row=i, column=0)

elif case == "tooltip_only":
    b = ctk.CTkButton(top, text="Generate")
    b.grid(row=0, column=0)
    ToolTip(b, *TOOLTIPS["Generate"])

root.update_idletasks(); root.update()
print("case=%s built" % case); sys.stdout.flush()
ctk.set_widget_scaling(1.1)
print("  returned"); sys.stdout.flush()
root.update_idletasks(); root.update()
print("  SURVIVED %s" % case); sys.stdout.flush()
root.destroy()
print("DONE-OK")
