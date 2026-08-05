#!/usr/bin/env python3
"""Text/code benchmark with CLI args for model/port/task."""
import requests, time, json, sys, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--port", default=51120)
ap.add_argument("--model", default="qwen3-vl-4b-instruct-uncensored-abliterated")
ap.add_argument("--max", type=int, default=500)
ap.add_argument("--task", default="hull")
args = ap.parse_args()

URL = f"http://localhost:{args.port}/v1/chat/completions"
MODEL = args.model

TASKS = {
  "hull": ("Write a Python function for the convex hull of 2D points using Andrew's monotone chain. Include type hints and docstring.",
           ["def ", "return", "sorted", "cross"]),
  "sort": ("Write a Python quicksort that returns a new sorted list. Include docstring.",
           ["def ", "return", "pivot", "recurs"]),
}
prompt, markers = TASKS.get(args.task, TASKS["hull"])

t0=time.time()
r=requests.post(URL, json={"model":MODEL,"max_tokens":args.max,
  "messages":[{"role":"user","content":prompt}]}, timeout=120)
dt=time.time()-t0
j=r.json(); comp=j["choices"][0]["message"]["content"]
u=j.get("usage",{})
ct=u.get("completion_tokens",0); pt=u.get("prompt_tokens",0)
tps=ct/dt if dt>0 else 0
found=[m for m in markers if m in comp]
print(f"Task: text/code ({args.task})")
print(f"Status: {r.status_code} | Wall: {dt:.2f}s")
print(f"Prompt: {pt} | Completion: {ct} | {tps:.1f} tok/s")
print(f"Quality markers ({'/'.join(markers)}): {len(found)}/{len(markers)}")
print("--- RESPONSE (first 400) ---")
print(comp[:400])
