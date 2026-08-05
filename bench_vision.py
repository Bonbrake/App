#!/usr/bin/env python3
"""Vision benchmark with CLI args."""
import requests, base64, time, json, os, struct, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--port", default=51120)
ap.add_argument("--model", default="qwen3-vl-4b-instruct-uncensored-abliterated")
ap.add_argument("--max", type=int, default=400)
ap.add_argument("--img", default=r"C:\Users\jakeb\AppData\Roaming\Hermes\composer-images\composer_2026-08-03_20-32-28-542_974af3.png")
args = ap.parse_args()

URL = f"http://localhost:{args.port}/v1/chat/completions"
MODEL = args.model

with open(args.img,'rb') as f: raw=f.read()
b64=base64.b64encode(raw).decode()
w,h=struct.unpack(">II",raw[16:24])

print(f"Image: {os.path.basename(args.img)} ({w}x{h}, {os.path.getsize(args.img)/1024:.0f} KB)")
t0=time.time()
r=requests.post(URL, json={
  "model":MODEL,"max_tokens":args.max,
  "messages":[{"role":"user","content":[
    {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}},
    {"type":"text","text":"Describe this screenshot in 2-3 sentences. What app/interface is shown?"}]}]},
  timeout=120)
dt=time.time()-t0
j=r.json(); comp=j["choices"][0]["message"]["content"]
u=j.get("usage",{})
ct=u.get("completion_tokens",0); pt=u.get("prompt_tokens",0)
tps=ct/dt if dt>0 else 0
print(f"Status: {r.status_code} | Wall: {dt:.2f}s")
print(f"Prompt tok: {pt} | Completion: {ct} | {tps:.1f} tok/s")
print("--- RESPONSE ---")
print(comp[:300])
