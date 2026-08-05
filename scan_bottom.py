from PIL import Image
im = Image.open(r"C:\ComfyUI-Desktop\real_app.png").convert("RGB")
W,H = im.size
# bottom button row region: y ~ 760-820, full width
crop = im.crop((0, 760, W, 850))
crop.save(r"C:\ComfyUI-Desktop\bottom_row.png")
# Find distinct bright/accent colored regions in this band
from collections import Counter
accents=[]
for y in range(760,850):
    for x in range(0,W):
        r,g,b=im.getpixel((x,y))
        # orange/amber accent (win default)
        if r>140 and 40<g<160 and b<120 and (r-g)>40 and (r-b)>60:
            accents.append((x,y,r,g,b))
print("accent px:",len(accents))
if accents:
    xs=[a[0] for a in accents]; ys=[a[1] for a in accents]
    print("x",min(xs),max(xs),"y",min(ys),max(ys))
    c=Counter((a[2],a[3],a[4]) for a in accents)
    for col,cnt in c.most_common(6): print(col,cnt)
