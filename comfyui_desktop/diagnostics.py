"""
ComfyUI Uncensored — Crash & Failure Intelligence (v2 overhaul)
===============================================================

This module is built so that when the app fails or crashes, an AI (or a human)
can find the root cause FAST. Every artifact is plain, self-contained JSON/Markdown
that an LLM can ingest directly.

Key capabilities (over the v1 system):
  1. Full structured crash dumps: exception, full traceback, AND captured
     local variables for every frame (truncated safely), plus system/thread/GPU
     state and a screenshot of the live window at crash time.
  2. A breadcrumb trail — the app emits breadcrumbs at every key action
     (build tab, start generate, post, poll, error). The last N breadcrumbs are
     embedded in every crash dump so an AI sees exactly what the app was doing.
  3. A "known fixes" table: common failure signatures are matched against the
     traceback and a plain-English fix + the exact code location is attached.
  4. A single-file .zip bundle ("debug bundle") that packs crash dumps, the
     latest report, the log tail, console output, and the screenshot — one file
     an AI can be handed.
  5. Tk callback-exception capture (tk.Tk.report_callback_exception) so that
     exceptions raised inside button callbacks / after() timers are ALSO caught
     (the default sys.excepthook misses these).

Usage:
    from comfyui_desktop.diagnostics import init_diagnostics, dump_report, breadcrumb
    init_diagnostics(base_dir, install_crash_hook=True)
    breadcrumb("start_generate", mode="txt2img", seed=12345)
    report = dump_report(app_self, log_tail_lines=200)
    save_report(report, base_dir)
"""

import os
import sys
import json
import datetime
import traceback
import platform
import logging
import threading
import time
import subprocess
from pathlib import Path

# ── Module-level state ───────────────────────────────────────────────
DIAG_DIR = None          # Where crash dumps + reports + bundles are saved
APP_LOG_PATH = None      # Where the structured JSON log lives
BREADCRUMB_PATH = None   # Rolling breadcrumb trail
_CONSOLE_LOG_PATH = None # Raw console capture (stdout/stderr tee)
_initialized = False
_lock = threading.RLock()
_breadcrumbs = []         # in-memory breadcrumb buffer (newest at end)
_breadcrumb_max = 200
_app_self = None          # back-reference to the running ComfyUIApp
_crash_hook_installed = False  # guard so the excepthook is only set once
_last_crash_ts = [None]  # shared, so the GUI can react

# ── Known-fix signatures ────────────────────────────────────────────
# Each entry: (signature_substring, title, plain_english_fix, location_hint)
# Matched against "<ExceptionName>: <msg>\n<traceback text>" (lower-cased).
KNOWN_FIXES = [
    ("Spectrum H3 solver step completed without an H3 model call",
     "MiniMax H3 Spectrum solver not loaded",
     "The Spectrum solver ran without an H3 model call. Restart the backend with Spectrum "
     "disabled once (uncheck 'Spectrum' in the video tab) to confirm, then re-enable. "
     "If it persists, the H3 model checkpoint failed to load on this 8GB VRAM box.",
     "ComfyUI-MiniMaxH3 / MiniMaxH3KSampler.sample"),
    ("No such file or directory",
     "Missing model / path / checkpoint file",
     "A referenced file (model, VAE, input image, or backend python) does not exist. "
     "Verify OUTPUT_DIR, the model files under ComfyUI/models, and PYTHON_PATH. "
     "On this box, backends must be launched with NATIVE C:/ paths (MSYS /c/... paths "
     "resolve wrong and cause this exact error).",
     "backend launch / model loader"),
    ("CUDA out of memory",
     "VRAM exhaustion (OOM)",
     "The GPU ran out of VRAM. Use a lower resolution, shorter duration, enable TeaCache "
     "and BlockSwap, or switch GPU Mode to --lowvram. The app's VRAM guard should auto-free "
     "after each job; if it didn't, restart the backend.",
     "ComfyUI loader / sampler"),
    ("Tk_PhotoImage",
     "Image is too tall/large for Tk PhotoImage",
     "An image exceeded Tk's internal limit. The gallery should thumbnail before display; "
     "if you hit this, the file is likely corrupt or gigantic — delete it from OUTPUT_DIR.",
     "gallery thumbnail loader"),
    ("_tkinter.TclError",
     "Tkinter widget used after destroy",
     "A callback touched a widget that no longer exists (e.g. window closed mid-poll). "
     "All widget access must be guarded by winfo_exists(); the poll loop already does this.",
     "poll/refresh callbacks"),
    ("sys.excepthook",
     "Crash during crash reporting",
     "An exception fired inside the diagnostics path itself. The crash dump may be partial; "
     "check the app.log for the secondary error.",
     "diagnostics.py"),
    ("HTTPConnectionPool",
     "ComfyUI server unreachable",
     "The backend server is not running or not on :8188. Start it from the app (Ctrl+R) or "
     "verify the backend process. Image gen and video gen both POST to COMFYUI_URL.",
     "_start_generate / _start_video_gen"),
    ("KeyError",
     "Workflow node key missing",
     "The generated ComfyUI workflow referenced a node key that wasn't created. This usually "
     "means a conditioning/sampler node variant wasn't wired. Inspect the graph builder for the "
     "missing key.",
     "_build_h3_graph / _video_*_build_and_queue"),
]

# ── Logging ─────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """Logs structured JSON records (one per line) for AI parsing."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "t": datetime.datetime.now().isoformat(),
            "lvl": record.levelname,
            "mod": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exc"] = traceback.format_exception(*record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def _setup_logger(base_dir: str) -> str:
    diag = os.path.join(base_dir, "diagnostics")
    os.makedirs(diag, exist_ok=True)
    log_path = os.path.join(diag, "app.log")

    logger = logging.getLogger("comfyui_diag")
    logger.setLevel(logging.DEBUG)
    # Avoid duplicate handlers if re-init is attempted
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == log_path for h in logger.handlers):
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_path, maxBytes=1_048_576, backupCount=4, encoding="utf-8")
        fh.setFormatter(JsonFormatter())
        logger.addHandler(fh)

    global APP_LOG_PATH
    APP_LOG_PATH = log_path
    return log_path


def _setup_console_capture(base_dir: str) -> str:
    """Tee stdout/stderr to a raw console log so an AI sees raw crashes too."""
    diag = os.path.join(base_dir, "diagnostics")
    os.makedirs(diag, exist_ok=True)
    path = os.path.join(diag, "console.log")

    class _Tee:
        def __init__(self, stream, sink_path):
            self._stream = stream
            self._sink = open(sink_path, "a", encoding="utf-8", buffering=1)
        def write(self, data):
            try:
                self._stream.write(data)
            except Exception:
                pass
            try:
                self._sink.write(data)
                self._sink.flush()
            except Exception:
                pass
        def flush(self):
            try:
                self._stream.flush()
            except Exception:
                pass
            try:
                self._sink.flush()
            except Exception:
                pass
        def __getattr__(self, name):
            return getattr(self._stream, name)

    # Only patch if not already patched
    if not getattr(sys.stdout, "_is_diag_tee", False):
        sys.stdout = _Tee(sys.stdout, path)
        sys.stdout._is_diag_tee = True
    if not getattr(sys.stderr, "_is_diag_tee", False):
        sys.stderr = _Tee(sys.stderr, path)
        sys.stderr._is_diag_tee = True
    return path


# ── Breadcrumbs ─────────────────────────────────────────────────────

def breadcrumb(action: str, **kwargs):
    """Record a lightweight breadcrumb: what the app was doing + when.

    Embedded into crash dumps so an AI sees the last actions before failure.
    """
    entry = {
        "t": datetime.datetime.now().isoformat(),
        "action": action,
    }
    # Only keep small, safe values to avoid dumping massive objects
    safe = {}
    for k, v in kwargs.items():
        s = str(v)
        safe[k] = s[:200]
    if safe:
        entry["data"] = safe
    _breadcrumbs.append(entry)
    if len(_breadcrumbs) > _breadcrumb_max:
        del _breadcrumbs[:len(_breadcrumbs) - _breadcrumb_max]
    # Persist a rolling file (cheap, append-only)
    if BREADCRUMB_PATH:
        try:
            with open(BREADCRUMB_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _recent_breadcrumbs(n: int = 40):
    return _breadcrumbs[-n:]


# ── System / GPU info ───────────────────────────────────────────────

def _system_info() -> dict:
    info = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "cpu": platform.processor() or "unknown",
        "cores": os.cpu_count(),
        "ram_total_mb": _total_ram_mb(),
        "ram_available_mb": _available_ram_mb(),
        "thread_count": threading.active_count(),
        "time_iso": datetime.datetime.now().isoformat(),
    }
    if getattr(sys, "frozen", False):
        try:
            info["bundle_dir"] = getattr(sys, "_MEIPASS", "unknown")
        except Exception:
            pass
    return info


def _total_ram_mb():
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return int(stat.ullTotalPhys // (1024 * 1024))
    except Exception:
        return 0


def _available_ram_mb():
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return int(stat.ullAvailPhys // (1024 * 1024))
    except Exception:
        return 0


def _gpu_info() -> dict:
    """Query GPU via nvidia-smi (best-effort)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            return {
                "name": parts[0] if len(parts) > 0 else "unknown",
                "vram_total_mb": int(parts[1]) if len(parts) > 1 else 0,
                "vram_used_mb": int(parts[2]) if len(parts) > 2 else 0,
                "vram_free_mb": int(parts[3]) if len(parts) > 3 else 0,
                "driver": parts[4] if len(parts) > 4 else "unknown",
            }
    except Exception:
        pass
    return {"error": "nvidia-smi not available"}


def _thread_dump() -> list:
    """Snapshot of all live threads + their current stack frames."""
    frames = sys._current_frames()
    out = []
    for tid, frame in frames.items():
        stack = []
        try:
            for f in traceback.walk_stack(frame):
                stack.append(_frame_summary(f))
        except Exception:
            pass
        out.append({
            "thread_id": tid,
            "stack": stack[-12:],  # keep last 12 frames
        })
    return out


def _frame_summary(frame):
    try:
        return {
            "file": frame.f_code.co_filename,
            "func": frame.f_code.co_name,
            "line": frame.f_lineno,
        }
    except Exception:
        return {"file": "?", "func": "?", "line": 0}


def _safe_repr(value, limit=400):
    try:
        s = repr(value)
    except Exception:
        s = "<repr failed>"
    if len(s) > limit:
        s = s[:limit] + "...[truncated]"
    return s


def _capture_locals(tb) -> list:
    """Capture local variables for each frame in the traceback."""
    frames = []
    for frame, lineno in traceback.walk_tb(tb):
        locals_snapshot = {}
        try:
            for k, v in frame.f_locals.items():
                # Skip obviously huge / unpicklable objects
                if k.startswith("__"):
                    continue
                locals_snapshot[k] = _safe_repr(v)
        except Exception:
            locals_snapshot = {"<capture error>": "true"}
        frames.append({
            "file": frame.f_code.co_filename,
            "func": frame.f_code.co_name,
            "line": lineno,
            "locals": locals_snapshot,
        })
    return frames


def _match_known_fixes(signature: str):
    sig = signature.lower()
    hits = []
    for substr, title, fix, loc in KNOWN_FIXES:
        if substr.lower() in sig:
            hits.append({"title": title, "fix": fix, "location": loc})
    return hits


def _screenshot(path: str) -> bool:
    """Capture the main window to PNG (best-effort). Returns True on success."""
    try:
        import ctypes
        from ctypes import wintypes
        # Try to grab the app window via the root handle if available
        hwnd = None
        if _app_self is not None:
            root = getattr(_app_self, "root", None)
            if root is not None:
                hwnd = root.winfo_id()
        # Use PIL.ImageGrab to capture (whole screen is acceptable fallback)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(path, "PNG")
            return True
        except Exception:
            pass
        # Fallback: attempt via hwnd BitBlt (advanced) — skip if complex
        return False
    except Exception:
        return False


# ── Crash handler ───────────────────────────────────────────────────

def _crash_handler(exc_type, exc_value, exc_tb):
    """Global sys.excepthook — writes a structured crash dump with full context."""
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    signature = "%s: %s\n%s" % (exc_type.__name__, exc_value, tb_text)

    crash = {
        "type": "crash",
        "timestamp": datetime.datetime.now().isoformat(),
        "exception": "%s: %s" % (exc_type.__name__, exc_value),
        "exception_type": exc_type.__name__,
        "traceback": tb_text.splitlines(),
        "frames_with_locals": _capture_locals(exc_tb),
        "system": _system_info(),
        "gpu": _gpu_info(),
        "threads": _thread_dump(),
        "breadcrumbs": _recent_breadcrumbs(40),
        "known_fixes": _match_known_fixes(signature),
        "frozen": bool(getattr(sys, "frozen", False)),
        "argv": sys.argv,
    }

    try:
        save_dir = DIAG_DIR or os.getcwd()
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, "crash_%s.json" % ts)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(crash, f, indent=2, ensure_ascii=False)
        crash["dump_path"] = path

        # Screenshot of the live UI
        shot = os.path.join(save_dir, "crash_%s.png" % ts)
        if _screenshot(shot):
            crash["screenshot"] = shot

        # Also log to the JSON logger
        logger = logging.getLogger("comfyui_diag")
        logger.critical("Unhandled crash: %s", signature.splitlines()[0])
        logger.critical("Crash dump saved to %s", path)
    except Exception:
        pass

    _last_crash_ts[0] = ts

    # Let the GUI react (if app is alive) then re-raise original
    try:
        if _app_self is not None:
            _app_self.root.after(0, lambda: _app_self._on_crash(crash))
    except Exception:
        pass

    sys.__excepthook__(exc_type, exc_value, exc_tb)


def _tk_callback_exception(exc_type, exc_value, exc_tb):
    """Replacement for tk.Tk.report_callback_exception — routes to crash handler."""
    try:
        _crash_handler(exc_type, exc_value, exc_tb)
    except Exception:
        sys.__excepthook__(exc_type, exc_value, exc_tb)


# ── Diagnostics report ──────────────────────────────────────────────

def dump_report(app_self=None, log_tail_lines: int = 100, include_gpu: bool = True) -> dict:
    """Generate a structured diagnostics report."""
    report = {
        "type": "diagnostics",
        "timestamp": datetime.datetime.now().isoformat(),
        "system": _system_info(),
        "breadcrumbs": _recent_breadcrumbs(40),
    }

    if include_gpu:
        report["gpu"] = _gpu_info()

    if app_self is not None:
        app_state = {
            "current_tab": getattr(app_self, "current_tab", None),
            "generate_lock": getattr(app_self, "_generate_lock", None),
            "last_prompt_id": getattr(app_self, "last_prompt_id", None),
            "vram_critical": getattr(app_self, "_vram_critical", None),
            "running": getattr(app_self, "_running", None),
            "backend_pid": getattr(app_self, "backend_pid", None),
        }
        for attr in ("model_var", "gpu_mode_str", "vram_threshold_str", "launch_args_str"):
            obj = getattr(app_self, attr, None)
            if obj is not None and hasattr(obj, "get"):
                app_state[attr] = str(obj.get())
        report["app"] = app_state

    # Recent log tail
    if APP_LOG_PATH and os.path.exists(APP_LOG_PATH):
        try:
            with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            report["log_tail"] = [l.rstrip() for l in lines[-log_tail_lines:]]
            report["log_path"] = APP_LOG_PATH
        except Exception as e:
            report["log_tail_error"] = str(e)

    # Recent crash dumps
    if DIAG_DIR and os.path.isdir(DIAG_DIR):
        crashes = sorted(
            [f for f in os.listdir(DIAG_DIR) if f.startswith("crash_") and f.endswith(".json")],
            reverse=True,
        )[:5]
        crash_data = []
        for fname in crashes:
            try:
                with open(os.path.join(DIAG_DIR, fname), "r", encoding="utf-8") as f:
                    cd = json.load(f)
                    # Trim heavy fields for the summary view
                    cd.pop("frames_with_locals", None)
                    cd.pop("threads", None)
                    crash_data.append(cd)
            except Exception:
                crash_data.append(fname)
        report["recent_crashes"] = crash_data
        report["diag_dir"] = DIAG_DIR

    return report


def save_report(report: dict, base_dir: str = None) -> str:
    """Save a diagnostics report to disk and return its path."""
    save_dir = DIAG_DIR or base_dir or os.getcwd()
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(save_dir, "report_%s.json" % ts)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


def build_debug_bundle(app_self=None, base_dir: str = None) -> str:
    """Create a single .zip 'debug bundle' with everything an AI needs.

    Contains: crash dumps (json), the latest report, the full log, console log,
    and the most recent screenshot. Returns the zip path.
    """
    import zipfile
    save_dir = DIAG_DIR or base_dir or os.getcwd()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(save_dir, "debug_bundle_%s.zip" % ts)
    try:
        report = dump_report(app_self, log_tail_lines=300, include_gpu=True)
        report_path = os.path.join(save_dir, "report_%s.json" % ts)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            # Report
            z.write(report_path, "report.json")
            # App log
            if APP_LOG_PATH and os.path.exists(APP_LOG_PATH):
                z.write(APP_LOG_PATH, "app.log")
            # Console log
            if _CONSOLE_LOG_PATH and os.path.exists(_CONSOLE_LOG_PATH):
                z.write(_CONSOLE_LOG_PATH, "console.log")
            # Crash dumps
            if os.path.isdir(save_dir):
                for f in sorted(os.listdir(save_dir)):
                    if f.startswith("crash_") and (f.endswith(".json") or f.endswith(".png")):
                        z.write(os.path.join(save_dir, f), f)
            # Breadcrumbs
            if BREADCRUMB_PATH and os.path.exists(BREADCRUMB_PATH):
                z.write(BREADCRUMB_PATH, "breadcrumbs.log")
            # A human-readable index
            index = _human_report(report)
            z.writestr("README.txt", index)
        # Clean up the temp report file (it's inside the zip)
        try:
            os.remove(report_path)
        except Exception:
            pass
        return zip_path
    except Exception as e:
        return "ERROR: %s" % e


# ── Initialization ───────────────────────────────────────────────────

def init_diagnostics(base_dir: str, install_crash_hook: bool = True, app_self=None):
    """Initialize the diagnostics system. Safe to call multiple times; the
    crash hook is installed on first call (or whenever requested and not yet
    installed), and app_self is always refreshed if provided."""
    global DIAG_DIR, _initialized, _app_self, BREADCRUMB_PATH, _CONSOLE_LOG_PATH
    with _lock:
        # Always refresh app reference if given
        if app_self is not None:
            _app_self = app_self

        # If already initialized, still ensure the crash hook is installed when
        # explicitly requested (idempotent — guarded inside _install_crash_hook).
        if _initialized:
            if install_crash_hook:
                _install_crash_hook()
            return

        DIAG_DIR = os.path.join(base_dir, "diagnostics")
        os.makedirs(DIAG_DIR, exist_ok=True)
        BREADCRUMB_PATH = os.path.join(DIAG_DIR, "breadcrumbs.log")
        _CONSOLE_LOG_PATH = os.path.join(DIAG_DIR, "console.log")

        _setup_logger(base_dir)
        try:
            _setup_console_capture(base_dir)
        except Exception:
            pass

        if app_self is not None:
            _app_self = app_self

        if install_crash_hook:
            _install_crash_hook()

        logger = logging.getLogger("comfyui_diag")
        logger.info("Diagnostics v2 initialized — base=%s, frozen=%s", base_dir, bool(getattr(sys, "frozen", False)))
        _initialized = True


def _install_crash_hook():
    """Install the global crash hooks (idempotent). Safe to call repeatedly —
    subsequent calls are no-ops once the hooks are in place."""
    global _crash_hook_installed
    with _lock:
        if _crash_hook_installed:
            return
        sys.excepthook = _crash_handler
        # Tk callback exceptions (button handlers, after() timers)
        try:
            import tkinter as _tk
            _tk.Tk.report_callback_exception = staticmethod(_tk_callback_exception)
        except Exception:
            pass
        _crash_hook_installed = True


# ── GUI helpers ─────────────────────────────────────────────────────

def diagnostics_button_command(app_self):
    """Callback for 'Generate Diagnostics Report' button."""
    try:
        report = dump_report(app_self, log_tail_lines=200, include_gpu=True)
        path = save_report(report)
        try:
            app_self.root.clipboard_clear()
            app_self.root.clipboard_append(path)
        except Exception:
            pass
        summary_path = path.replace(".json", ".txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(_human_report(report))
        app_self._set_status("Diagnostics saved → %s (copied)" % path)
    except Exception as e:
        app_self._set_status("Diagnostics error: %s" % e)


def bundle_button_command(app_self):
    """Callback for 'Build Debug Bundle' button (packs everything into one zip)."""
    try:
        path = build_debug_bundle(app_self)
        if path.startswith("ERROR"):
            app_self._set_status("Bundle failed: %s" % path)
            return
        try:
            app_self.root.clipboard_clear()
            app_self.root.clipboard_append(path)
        except Exception:
            pass
        size = os.path.getsize(path) // 1024
        app_self._set_status("Debug bundle → %s (%d KB, copied)" % (path, size))
    except Exception as e:
        app_self._set_status("Bundle error: %s" % e)


# ── Human-readable report ───────────────────────────────────────────

def _human_report(report: dict) -> str:
    lines = []
    lines.append("=" * 64)
    lines.append("ComfyUI Uncensored — Diagnostics Report")
    lines.append("Generated: %s" % report.get("timestamp", "?"))
    lines.append("=" * 64)
    lines.append("")

    sys_info = report.get("system", {})
    lines.append("── System ──")
    lines.append("  Platform:    %s" % sys_info.get("platform", "?"))
    lines.append("  Python:      %s" % sys_info.get("python", "?"))
    lines.append("  Frozen:      %s" % sys_info.get("frozen", "?"))
    lines.append("  PID:         %s" % sys_info.get("pid", "?"))
    lines.append("  Cores:       %s" % sys_info.get("cores", "?"))
    lines.append("  RAM total:   %s MB" % sys_info.get("ram_total_mb", "?"))
    lines.append("  RAM avail:   %s MB" % sys_info.get("ram_available_mb", "?"))
    lines.append("  Threads:     %s" % sys_info.get("thread_count", "?"))
    lines.append("")

    gpu = report.get("gpu", {})
    if gpu.get("error"):
        lines.append("  GPU: %s" % gpu["error"])
    else:
        lines.append("── GPU ──")
        lines.append("  Name:     %s" % gpu.get("name", "?"))
        lines.append("  VRAM:     %s / %s MB free" % (gpu.get("vram_free_mb", "?"), gpu.get("vram_total_mb", "?")))
        lines.append("  Driver:   %s" % gpu.get("driver", "?"))
    lines.append("")

    app_state = report.get("app", {})
    if app_state:
        lines.append("── App State ──")
        for k, v in app_state.items():
            lines.append("  %s: %s" % (k, v))
        lines.append("")

    crumbs = report.get("breadcrumbs", [])
    if crumbs:
        lines.append("── Recent Breadcrumbs (what the app was doing) ──")
        for c in crumbs[-15:]:
            d = c.get("data", {})
            ds = " ".join("%s=%s" % (k, v) for k, v in d.items())
            lines.append("  [%s] %s %s" % (c.get("t", "?"), c.get("action", "?"), ds))
        lines.append("")

    crashes = report.get("recent_crashes", [])
    if crashes:
        lines.append("── Recent Crashes (%d) ──" % len(crashes))
        for c in crashes:
            if isinstance(c, dict):
                lines.append("  [%s] %s" % (c.get("timestamp", "?"), c.get("exception", "?")))
                for fix in c.get("known_fixes", []) or []:
                    lines.append("    ↳ KNOWN FIX: %s" % fix.get("title", ""))
            else:
                lines.append("  %s" % c)
        lines.append("")
    else:
        lines.append("── No recent crashes ──")
        lines.append("")

    log_tail = report.get("log_tail", [])
    if log_tail:
        lines.append("── Log Tail (last %d lines) ──" % len(log_tail))
        for l in log_tail[-50:]:
            lines.append("  %s" % (l.rstrip()[:200]))
        lines.append("")
    else:
        lines.append("── No log data ──")
        lines.append("")

    if report.get("log_path"):
        lines.append("Log path: %s" % report["log_path"])
    if report.get("diag_dir"):
        lines.append("Diag dir: %s" % report["diag_dir"])

    lines.append("=" * 64)
    return "\n".join(lines)
