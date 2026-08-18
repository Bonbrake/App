import psutil, os, subprocess

# Kill the stuck llama-server (PID 14536) — this is LM Studio's backend, NOT ComfyUI
pid = 14536
try:
    p = psutil.Process(pid)
    cmdline = " ".join(p.cmdline())[:100]
    print(f"killing llama-server.exe PID {pid}")
    print(f"  cmdline: {cmdline}")
    p.terminate()
    p.wait(timeout=10)
    print(f"  terminated gracefully")
except psutil.NoSuchProcess:
    print(f"PID {pid} already dead")
    # Find PID listening on port 5120
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
    for line in r.stdout.split("\n"):
        if "5120" in line and "LISTENING" in line:
            parts = line.split()
            pid = int(parts[-1])
            if pid != 0:
                try:
                    proc = psutil.Process(pid)
                    print(f"  killing port 5120 listener: PID {pid} ({proc.name()})")
                    proc.terminate()
                    proc.wait(timeout=10)
                    print(f"  terminated")
                except psutil.NoSuchProcess:
                    print(f"  PID {pid} already dead")
                except Exception as e:
                    print(f"  error killing PID {pid}: {e}")
except Exception as e:
    print(f"error: {e}")

# Verify port 5120 is clear
import requests
try:
    r = requests.get("http://localhost:5120/v1/models", timeout=5)
    print(f"Port 5120 still alive: {r.status_code}")
except:
    print("Port 5120 is clear")
