from PIL import Image
im = Image.open(r"C:\ComfyUI-Desktop\real_app.png").convert("RGB")
W,H = im.size
print("size", W, H)
# Scan bottom-right quarter for orange-ish pixels (R high, G mid, B low)
orange=[]
for y in range(int(H*0.6), H):
    for x in range(int(W*0.6), W):
        r,g,b = im.getpixel((x,y))
        if r>150 and 60<g<190 and b<110 and (r-g)>50:
            orange.append((x,y,r,g,b))
print("orange-ish pixels:", len(orange))
if orange:
    # cluster by proximity
    from collections import defaultdict
    orange.sort()
    xs=[p[0] for p in orange]; ys=[p[1] for p in orange]
    print("x range", min(xs), max(xs), "y range", min(ys), max(ys))
    # print a 20x20 grid of avg around centroid
    cx=(min(xs)+max(xs))//2; cy=(min(ys)+max(ys))//2
    print("centroid", cx, cy)
    # crop 40x40
    crop = im.crop((cx-30, cy-30, cx+30, cy+30))
    crop.save(r"C:\ComfyUI-Desktop\orange_zoom.png")
    print("saved orange_zoom.png")
    # sample colors
    from collections import Counter
    c=Counter(im.getpixel((x,y)) for x,y,*_ in [(p[0],p[1]) for p in orange[:200]])
    for col,cnt in c.most_common(8):
        print(col, cnt)
