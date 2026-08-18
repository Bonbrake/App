#!/usr/bin/env python3
"""
🦅 Hermes Vision Model Monitor — Heartbeat & Model Display

Single consolidated entry point for:
  1. Displaying ALL available vision models on disk
  2. Showing which model is ACTIVE (config.yaml + currently loaded)
  3. GPU/VRAM status snapshot
  4. Quick vision_analyze test to confirm the active model works

Usage:
  python vision_model_monitor.py           → full snapshot + live test
  python vision_model_monitor.py --watch   → continuous heartbeat (every 30s)
  python vision_model_monitor.py --quiet   → snapshot only, no live test
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

# ── Constants ────────────────────────────────────────────────────────────────
BIONIC_URL       = "http://localhost:5120/v1"
CONFIG_PATH      = r"C:\Users\jakeb\AppData\Local\hermes\config.yaml"
LM_MODELS_DIR    = r"C:\Users\jakeb\.lmstudio\models"
LMS_CLI          = r"C:\Users\jakeb\AppData\Local\Programs\Bionic\resources\app\.webpack-bionic\lms.exe"
TEST_IMAGE       = r"C:\Users\jakeb\AppData\Roaming\Hermes\composer-images\composer_2026-08-03_17-40-58-807_adb843.png"

# ── Model metadata (from disk inspection + benchmark) ──────────────────────
# Ordered by benchmarked tok/s descending
ALL_VL_MODELS = [
    {
        "name":          "qwen3-vl-4b-instruct-uncensored-abliterated",
        "params":        "4.0B",
        "size_gb":       2.4,
        "tok_per_s":     95.3,
        "chars_output":  1329,
        "quality_rank":  "🥈",
        "speed_rank":    "🥇",
        "notes":         "Fastest — current config default",
    },
    {
        "name":          "ektome-qwen3-vl-4bi-pristinelyuncensored-i1",
        "params":        "4Bi",
        "size_gb":       2.4,
        "tok_per_s":     95.0,
        "chars_output":  1458,
        "quality_rank":  "🥈",
        "speed_rank":    "🥈",
        "notes":         "Pristinely uncensored, close 2nd",
    },
    {
        "name":          "lfm2.5-vl-1.6b",
        "params":        "1.6B",
        "size_gb":       0.9,
        "tok_per_s":     94.1,
        "chars_output":  1337,
        "quality_rank":  "🥉",
        "speed_rank":    "🥉",
        "notes":         "Smallest footprint, clean output",
    },
    {
        "name":          "minicpm5-1b-claude-opus-fable5-v2-thinking-heretic",
        "params":        "1.0B",
        "size_gb":       0.6,
        "tok_per_s":     93.9,
        "chars_output":  1580,
        "quality_rank":  "🥇",
        "speed_rank":    "🥕",
        "notes":         "Best quality/depth (most detailed)",
    },
    {
        "name":          "thesby_qwen2.5-vl-7b-nsfw-caption-v3",
        "params":        "7.0B",
        "size_gb":       4.5,
        "tok_per_s":     93.1,
        "chars_output":  1424,
        "quality_rank":  "🥉",
        "speed_rank":    "🥕",
        "notes":         "7B — detailed but large VRAM",
    },
    {
        "name":          "qwen2.5-vl-3b-instruct-abliterated",
        "params":        "3.0B",
        "size_gb":       1.9,
        "tok_per_s":     83.3,
        "chars_output":  1320,
        "quality_rank":  "🥊",
        "speed_rank":    "🥊",
        "notes":         "Small, but JIT reload needed",
    },
]


def get_gpu_status():
    """Query nvidia-smi for GPU utilization, memory, and temperature."""
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            return {
                "util":  parts[0],
                "mem_used": parts[1].replace(" MiB", ""),
                "mem_total": parts[2].replace(" MiB", ""),
                "temp": parts[3].replace(" C", ""),
                "name": parts[4],
            }
    except Exception:
        pass
    return None


def get_loaded_models():
    """Query the bionic API for currently loaded models."""
    try:
        r = requests.get(f"{BIONIC_URL}/models", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return [m["id"] for m in data.get("data", [])], True
    except Exception:
        pass
    # Fallback: try lms CLI
    try:
        r = subprocess.run([LMS_CLI, "ps"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            loaded = []
            for line in r.stdout.strip().split("\n"):
                for m in ALL_VL_MODELS:
                    if m["name"] in line:
                        loaded.append(m["name"])
            return loaded, True
    except Exception:
        pass
    return [], False


def get_config_model():
    """Read the active vision model from Hermes config.yaml."""
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        vision_cfg = config.get("auxiliary", {}).get("vision", {})
        return vision_cfg.get("model", "unknown")
    except Exception as e:
        print(f"  Warning: could not read config: {e}")
        return "unknown"


def quick_vision_test(model_name, timeout_s=45):
    """Quick vision test to confirm the model is responsive."""
    if not os.path.exists(TEST_IMAGE):
        return None, "no test image found"
    try:
        with open(TEST_IMAGE, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        r = requests.post(f"{BIONIC_URL}/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role":"user","content":[
                    {"type":"text","text":"What app is shown in this terminal? One sentence."},
                    {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64}}
                ]}],
                "max_tokens": 80,
                "reasoning_effort": "none"
            },
            timeout=timeout_s
        )
        if r.status_code == 200:
            data = r.json()
            return True, data["choices"][0]["message"].get("content", "")[:80]
        else:
            return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)[:60]


def print_header(title):
    """Print a section header."""
    print(f"\n  ═ {title} ═")
    print(f"  {'─' * 76}")


def run_snapshot(test_live=True):
    """Run a single snapshot of the vision model system status."""
    os.system("cls" if os.name == "nt" else "clear")

    print("=" * 80)
    print("  🦅 HERMES VISION MODEL MONITOR — System Status")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. Config model (active)
    config_model = get_config_model()

    # 2. Loaded models
    loaded_models, server_alive = get_loaded_models()
    loaded_set = set(loaded_models)

    # 3. GPU status
    gpu = get_gpu_status()

    # ── Section 1: ALL VL Models ─────────────────────────────────────────
    print_header("ALL VISION MODELS")
    print(f"  {'Name':<52} {'Params':>6} {'Size':>6} {'tok/s':>6}  Speed  Quality  Status")
    print(f"  {'─'*52} {'─'*6} {'─'*6} {'─'*6}  ──────  ───────  ──────")
    for m in ALL_VL_MODELS:
        is_active = m["name"] == config_model
        is_loaded = m["name"] in loaded_set
        status_marker = "ACTIVE" if is_active else ("LOADED" if is_loaded else "")
        active_tag = " ✓" if is_active else ""
        loaded_tag = "●" if is_loaded else "○"
        print(f"  {m['name']:<52} {m['params']:>6} {m['size_gb']:>5.1f}G {m['tok_per_s']:>5.1f}  "
              f"{m['speed_rank']:<6} {m['quality_rank']:<8} {loaded_tag} {status_marker}{active_tag}")
    print(f"\n  Legend: ✓ = config active | ● = currently loaded in VRAM | ○ = not loaded")

    # ── Section 2: Server Status ──────────────────────────────────────────
    print_header("SERVER STATUS")
    if server_alive:
        print(f"  ✓ Bionic/LM Studio API: ALIVE (localhost:5120)")
        print(f"  Loaded models: {len(loaded_models)}")
        for m in loaded_models:
            active_tag = " ← CONFIG ACTIVE" if m == config_model else ""
            print(f"    ● {m}{active_tag}")
    else:
        print(f"  ✗ Bionic/LM Studio API: DOWN (localhost:5120)")
        print(f"  → Start with: lms server start")

    # ── Section 3: GPU Status ─────────────────────────────────────────────
    print_header("GPU STATUS")
    if gpu:
        mem_pct = int(gpu["mem_used"]) / int(gpu["mem_total"]) * 100 if int(gpu["mem_total"]) > 0 else 0
        print(f"  GPU:    {gpu['name']}")
        print(f"  Util:   {gpu['util']}  ({gpu['temp']}°C)")
        print(f"  VRAM:   {gpu['mem_used']}/{gpu['mem_total']} MiB ({mem_pct:.0f}%)")
    else:
        print(f"  nvidia-smi not available — cannot check GPU")

    # ── Section 4: Config ─────────────────────────────────────────────────
    print_header("HERMES VISION CONFIG")
    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
        vision = config.get("auxiliary", {}).get("vision", {})
        for k, v in vision.items():
            print(f"  auxiliary.vision.{k}: {v}")
    except Exception as e:
        print(f"  Error reading config: {e}")

    # ── Section 5: Live Test ──────────────────────────────────────────────
    if test_live:
        print_header("LIVE TEST")
        if not server_alive:
            print(f"  Cannot test — server is down")
        elif not loaded_models:
            print(f"  Cannot test — no models loaded. Loading active config model...")
            ok, msg = quick_vision_test(config_model, timeout_s=90)
        else:
            print(f"  Testing: {config_model}")
            t0 = time.time()
            ok, result = quick_vision_test(config_model, timeout_s=60)
            elapsed = time.time() - t0
            if ok:
                print(f"  ✓ Response in {elapsed:.1f}s: \"{result}\"")
            else:
                print(f"  ✗ Failed in {elapsed:.1f}s: {result}")

    # ── Summary ───────────────────────────────────────────────────────────
    print_header("SUMMARY")
    print(f"  Active model:     {config_model}")
    print(f"  Loaded models:    {len(loaded_models)}")
    print(f"  Server alive:     {'yes' if server_alive else 'no'}")
    print(f"  GPU utilization:  {gpu['util'] if gpu else 'unknown'}")
    print(f"  VRAM used:        {gpu['mem_used']+'/'+gpu['mem_total']+' MiB' if gpu else 'unknown'}")
    print(f"  JIT TTL:          120s (auto-unload after 2 min idle)")
    print(f"  Config timeout:   60s | max_tokens: 500 | retries: 2")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="🦅 Hermes Vision Model Monitor — system status & diagnostics"
    )
    parser.add_argument("--watch", action="store_true",
                        help="Continuous monitoring (refresh every 30s)")
    parser.add_argument("--quiet", action="store_true",
                        help="Snapshot only, no live test")
    parser.add_argument("--interval", type=int, default=30,
                        help="Watch refresh interval in seconds (default: 30)")
    args = parser.parse_args()

    if args.watch:
        print("Starting continuous heartbeat monitor. Press Ctrl+C to stop.")
        try:
            while True:
                run_snapshot(test_live=True)
                print(f"\n  Next refresh in {args.interval}s... (Ctrl+C to stop)", end="", flush=True)
                for i in range(args.interval):
                    time.sleep(1)
                    print(".", end="", flush=True)
                print()
        except KeyboardInterrupt:
            print("\n\n  Monitor stopped.")
    else:
        run_snapshot(test_live=not args.quiet)


if __name__ == "__main__":
    main()
