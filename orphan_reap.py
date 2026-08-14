#!/usr/bin/env python3
"""
orphan_reap.py  (Phase 2 - EXE duplicate-server fix)
===================================================
Before the ComfyUI EXE spawns a new :8188 server, reap a LEFTOVER (orphan)
server from a previous EXE run. This kills ONLY an orphan whose launching EXE
is DEAD. A live EXE that still owns its server is NEVER killed (Rule: nothing
the user is using dies).

Uses a SENTINEL FILE written by ComfyUI_App._start_backend:
  %LOCALAPPDATA%/ComfyUI_Desktop/backend_pid.txt  (contains the backend PID)

If a server exists on :8188 but its PID != sentinel PID (and sentinel PID is
dead), it's an orphan from a prior EXE run -> reap it.
Manual launches (no sentinel) are NEVER touched.

Pure stdlib (no psutil) so it imports cleanly into the frozen EXE.

Usage (imported by the EXE):
  import orphan_reap
  orphan_reap.reap_orphan_8188(my_pid=None)   # my_pid = the EXE's own backend PID

Standalone:
  python orphan_reap.py [--dry-run]    # report / optionally reap the orphan
"""
import subprocess
import sys
import time
import os
import ctypes

COMFY_PORT = 8188
SENTINEL = os.path.join(os.getenv("LOCALAPPDATA", os.path.normpath(os.path.expanduser(r"~/AppData/Local"))),
                        "ComfyUI_Desktop", "backend_pid.txt")

def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).stdout
    except Exception:
        return ""

def pid_on_port(port):
    """Return PID listening on 127.0.0.1:port, or None."""
    out = _run(["netstat", "-ano"])
    needle = f":{port} "
    for line in out.splitlines():
        if "LISTENING" in line and needle in line:
            parts = line.split()
            try:
                return int(parts[-1])
            except ValueError:
                pass
    return None

def image_name(pid):
    """Return lowercased image name for pid, or ''."""
    out = _run(["tasklist", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"])
    for tok in out.split('","'):
        tok = tok.strip().strip('"')
        if tok.lower().endswith(".exe"):
            return tok.lower()
    return ""

def parent_pid_of(pid):
    # H1 FIX: wmic is REMOVED on Windows 11. Use PowerShell Get-CimInstance,
    # which is always present and returns ParentProcessId reliably.
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").ParentProcessId"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).stdout
        out = out.strip()
        if out and out.isdigit():
            return int(out)
    except Exception:
        pass
    return None

def pid_alive(pid):
    if not pid:
        return False
    # PRESERVED_LEGACY: Fast Win32 ctypes check (0 subprocesses, <1ms)
    if os.name == "nt":
        try:
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if h:
                code = ctypes.c_ulong()
                ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
                ctypes.windll.kernel32.CloseHandle(h)
                return code.value == 259  # STILL_ACTIVE
            return False
        except Exception:
            pass
    # Use PowerShell (reliable fallback on Win11)
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"if (Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\") {{ \"YES\" }} else {{ \"NO\" }}"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).stdout.strip()
        return out == "YES"
    except Exception:
        pass
    # fallback: strict parse of tasklist
    out = _run(["tasklist", "/fi", f"PID eq {pid}", "/nh"])
    for line in out.splitlines():
        if line.strip().startswith(str(pid)):
            return True
    return False

def read_sentinel():
    """Return sentinel PID (int) or None if file missing/invalid."""
    try:
        with open(SENTINEL, "r", encoding="ascii") as f:
            val = f.read().strip()
            if val.isdigit():
                return int(val)
    except Exception:
        pass
    return None

def write_sentinel(pid):
    """Write backend PID to sentinel file."""
    try:
        os.makedirs(os.path.dirname(SENTINEL), exist_ok=True)
        with open(SENTINEL, "w", encoding="ascii") as f:
            f.write(str(pid))
    except Exception:
        pass

def clear_sentinel():
    try:
        os.remove(SENTINEL)
    except Exception:
        pass

def reap_orphan_8188(my_pid=None, dry_run=False):
    """Terminate an :8188 ComfyUI server that is an ORPHAN from a PREVIOUS EXE
    run. Returns the PID reaped, or None.

    Logic:
    - If no server on :8188 -> nothing to do.
    - If server PID == my_pid -> our own backend, leave it.
    - If server PID == sentinel PID and sentinel PID alive -> current EXE owns it, leave it.
    - If server PID != sentinel PID and sentinel PID is DEAD -> orphan from prior EXE run, REAP.
    - If no sentinel file -> manual launch, NEVER reap.
    """
    pid = pid_on_port(COMFY_PORT)
    if pid is None:
        print(f"[orphan_reap] no process on :{COMFY_PORT}")
        return None
    if my_pid is not None and pid == my_pid:
        print(f"[orphan_reap] :{COMFY_PORT} held by our own PID {pid} - leave it")
        return None
    name = image_name(pid)
    if "python" not in name and "comfy" not in name:
        print(f"[orphan_reap] :{COMFY_PORT} PID {pid} ({name}) is not a ComfyUI server - leave it")
        return None
    # Sentinel logic
    sentinel_pid = read_sentinel()
    if sentinel_pid is not None:
        if sentinel_pid == pid:
            # Current EXE owns the server (or same run)
            print(f"[orphan_reap] :{COMFY_PORT} PID {pid} matches sentinel - current run owns it")
            return None
        # sentinel_pid != pid. Is sentinel process alive?
        if pid_alive(sentinel_pid):
            print(f"[orphan_reap] sentinel PID {sentinel_pid} alive - another EXE owns :{COMFY_PORT}, leave it")
            return None
    # sentinel process dead (or missing), and :8188 held by a different python PID -> orphan, REAP.
    if dry_run:
        print(f"[orphan_reap DRY-RUN] would reap orphan :{COMFY_PORT} PID {pid} (sentinel {sentinel_pid} dead)")
        return pid
    print(f"[orphan_reap] reaping orphan :{COMFY_PORT} PID {pid} (sentinel {sentinel_pid} dead)")
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, timeout=10, creationflags=flags)
    except Exception:
        pass
    try:
        import signal
        os.kill(pid, getattr(signal, "SIGTERM", 15))
    except Exception:
        pass
    time.sleep(1)
    if pid_on_port(COMFY_PORT) is None:
        print(f"[orphan_reap] orphan PID {pid} gone - port clear")
    else:
        print(f"[orphan_reap] WARN: :{COMFY_PORT} still held after reap")
    return pid

# ------------------------------------------------------------------
# HARDENING (Spark plan port): Windows Job Object + psutil tree reap
# ------------------------------------------------------------------
class WindowsJobObject:
    """Assigns child processes to an OS-level Job Object configured with
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. If this EXE crashes or is
    force-killed, the Windows kernel terminates the backend AND all of its
    CUDA/worker grandchildren -- eliminating orphaned :8188 servers.

    Pure ctypes on win32; no-op on other platforms. Never raises in __init__
    (fails soft), but assign() reports via return value so callers know.
    """

    # JOBOBJECT_EXTENDED_LIMIT_INFORMATION = 9
    # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE    = 0x2000
    _KILL_ON_CLOSE = 0x2000

    def __init__(self):
        self.handle = None
        if os.name != "nt":
            return
        try:
            k32 = ctypes.windll.kernel32
            # Correct prototypes: 64-bit handles must be typed or ctypes
            # truncates them to 32 bits (returns a NULL/garbage handle).
            k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
            k32.CreateJobObjectW.restype = ctypes.c_void_p
            k32.SetInformationJobObject.argtypes = [
                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
            k32.SetInformationJobObject.restype = ctypes.c_int
            k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
            k32.OpenProcess.restype = ctypes.c_void_p
            k32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            k32.AssignProcessToJobObject.restype = ctypes.c_int
            k32.CloseHandle.argtypes = [ctypes.c_void_p]
            k32.CloseHandle.restype = ctypes.c_int
            k32.GetLastError.restype = ctypes.c_uint32

            class _BASIC(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", ctypes.c_uint32),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", ctypes.c_uint32),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", ctypes.c_uint32),
                    ("SchedulingClass", ctypes.c_uint32),
                ]

            class _IO(ctypes.Structure):
                _fields_ = [
                    ("ReadOperationCount", ctypes.c_int64),
                    ("WriteOperationCount", ctypes.c_int64),
                    ("OtherOperationCount", ctypes.c_int64),
                    ("ReadTransferCount", ctypes.c_int64),
                    ("WriteTransferCount", ctypes.c_int64),
                    ("OtherTransferCount", ctypes.c_int64),
                ]

            class _EXT(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", _BASIC),
                    ("IoInfo", _IO),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryLimit", ctypes.c_size_t),
                    ("PeakJobMemoryLimit", ctypes.c_size_t),
                ]

            self.handle = k32.CreateJobObjectW(None, None)
            if not self.handle:
                # Guard against passing NULL to SetInformationJobObject below.
                return
            info = _EXT()
            info.BasicLimitInformation.LimitFlags = self._KILL_ON_CLOSE
            if not k32.SetInformationJobObject(
                    self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
                # Non-fatal: job still created, just won't force-kill on close.
                self._kill_on_close = False
            else:
                self._kill_on_close = True
        except Exception:
            self.handle = None

    def assign(self, pid):
        """Assign a process (and its future children) to this job.

        Returns True on success, False if the job is unavailable or the
        assignment failed. Callers (main.start_server) should log the
        failure rather than assume protection is active.
        """
        if not self.handle or not pid:
            return False
        try:
            k32 = ctypes.windll.kernel32
            # PROCESS_SET_QUOTA (0x100) | PROCESS_TERMINATE (0x1) |
            # PROCESS_DUP_HANDLE (0x40) for nested assignment.
            ph = k32.OpenProcess(0x100 | 0x1 | 0x40, False, int(pid))
            if not ph:
                return False
            ok = bool(k32.AssignProcessToJobObject(self.handle, ph))
            k32.CloseHandle(ph)
            return ok
        except Exception:
            return False

    def __del__(self):
        if getattr(self, "handle", None):
            try:
                ctypes.windll.kernel32.CloseHandle(self.handle)
            except Exception:
                pass



def reap_process_tree(pid, timeout=3.0):
    """Recursively terminate a process and all descendants via psutil.

    Belt-and-suspenders complement to taskkill /T /F: covers the case where
    a worker grandchild has already detached from the tracked parent PID.
    """
    if not pid:
        return
    try:
        import psutil
    except Exception:
        return
    try:
        parent = psutil.Process(int(pid))
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return
    try:
        children = parent.children(recursive=True)
    except Exception:
        children = []
    for child in children:
        try:
            child.terminate()
        except Exception:
            pass
    procs = children + [parent]
    gone, alive = psutil.wait_procs(procs, timeout=timeout)
    for proc in alive:
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    dr = "--dry-run" in sys.argv
    reap_orphan_8188(dry_run=dr)
