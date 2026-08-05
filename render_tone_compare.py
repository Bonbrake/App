"""Render a side-by-side mockup of the app chrome in 3 candidate dark tones.
Lets the user pick the exact background hue without a full EXE rebuild."""
import struct
from PIL import Image, ImageDraw, ImageFont

W, H = 820, 580
pad = 18

def font(sz):
    try:
        return ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", sz)
    except Exception:
        return ImageFont.load_default()

def draw_app(d, ox, oy, tone, name, hexv):
    x0, y0 = ox + pad, oy + pad
    x1, y1 = ox + W - pad, oy + H - pad
    # window bg (app tone)
    d.rectangle([x0, y0, x1, y1], fill=tone)
    # left sidebar (black, DO NOT TOUCH)
    sb = (20, 20, 26)
    d.rectangle([x0, y0, x0 + 150, y1], fill=sb)
    # header bar
    hdr = tuple(min(255, c + 14) for c in tone)
    d.rectangle([x0 + 150, y0, x1, y0 + 52], fill=hdr)
    # main card (slightly lifted)
    card = tone
    d.rounded_rectangle([x0 + 172, y0 + 70, x1 - 18, y1 - 92], radius=10, fill=card,
                        outline=(42, 42, 60), width=1)
    # prompt box
    box = tuple(max(0, c - 10) for c in tone)
    d.rounded_rectangle([x0 + 192, y0 + 92, x1 - 38, y0 + 150], radius=6, fill=box,
                        outline=(90, 90, 110), width=1)
    # generate button (brand periwinkle)
    d.rounded_rectangle([x0 + 192, y0 + 165, x0 + 360, y0 + 205], radius=6, fill=(99, 102, 241))
    # status bar
    sb2 = tone
    d.rounded_rectangle([x0 + 150, y1 - 78, x1, y1], radius=10, fill=sb2,
                        outline=(42, 42, 60), width=1)
    # thumb strip on status bar
    ts = (18, 18, 24)
    d.rounded_rectangle([x1 - 200, y1 - 68, x1 - 18, y1 - 12], radius=6, fill=ts)
    # text labels
    f = font(15); fb = font(13)
    d.text((x0 + 172, y0 + 24), "ComfyUI Uncensored", fill=(248, 250, 252), font=fb)
    d.text((x0 + 192, y0 + 100), "prompt...", fill=(148, 163, 184), font=fb)
    d.text((x0 + 200, y0 + 178), "Generate", fill=(255, 255, 255), font=fb)
    d.text((x0 + 172, y1 - 64), "Active Model: epiCRealism XL", fill=(248, 250, 252), font=fb)
    d.text((x0 + 172, y1 - 42), "VRAM: 9% used   |   Server online", fill=(148, 163, 184), font=fb)
    # title label
    d.text((ox + 14, oy + 8), name, fill=(255, 255, 255), font=font(17))
    d.text((ox + 14, oy + 34), hexv, fill=(148, 163, 184), font=fb)

candidates = [
    ("A — Slate (current)", (30, 30, 44), "#1E1E2C  (current)"),
    ("B — Warm Umber", (36, 28, 24), "#241C18  (warm, subtle)"),
    ("C — Warm Cocoa", (44, 33, 26), "#2C211A  (warm, pronounced)"),
]

img = Image.new("RGB", (W * 3, H + 60), (12, 12, 16))
d = ImageDraw.Draw(img)
for i, (name, tone, hexv) in enumerate(candidates):
    draw_app(d, i * W, 50, tone, name, hexv)
d.text((14, 12), "Background tone comparison — pick A, B, or C (or 'keep current')",
       fill=(248, 250, 252), font=font(16))
out = r"C:\ComfyUI-Desktop\tone_compare.png"
img.save(out)
print("wrote", out)
