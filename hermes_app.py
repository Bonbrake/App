#!/usr/bin/env python3
"""
hermes_app.py -- Matrix Local AI HUD
====================================
Professional, single-file PySide6 desktop HUD for the local AI backend served
by local_ai_proxy.py on http://127.0.0.1:5119 (lifecycle owned by
local_ai_daemon.py / scheduled task 'LocalAIDaemon').

Feature set (faithful to the original HUD, defect removed):
- Digital-rain background (CMatrixWidget) with a live system-console log feed
  overlaid at the bottom (add_log / clear_logs).
- Red / Blue / Idle "pill" badges that reflect the active model.
- Tiered model picker: load Qwen3.8-27B (Think Hard / Red Pill) or
  Qwen3.6-35B (Fast / Blue Pill), or go Idle (frees VRAM).
- Live VRAM / GPU / RAM / CPU bars (RAM + CPU measured client-side via psutil;
  VRAM + GPU + tok/s come from the proxy /admin/telemetry endpoint).
- System tray: click to restore, "Clear VRAM", "Exit" (Exit frees VRAM).
- "Clear VRAM" button -> POST /admin/unload_all (nothing lingers when idle).
- Close minimizes to tray (never quits silently); Exit frees VRAM then quits.
- Single-instance guard so double-clicking the .lnk never spawns duplicates.

DEFECT REMOVED (2026-08-17): the old app embedded a Hermes-presence watcher that
tried to re-spawn the backend/Hermes from inside the GUI and broke window
reopen. The backend lifecycle is now owned entirely by local_ai_daemon.py +
local_ai_proxy.py. This HUD only *reads* telemetry and *requests* model loads;
it never controls or restarts processes.
"""

import sys
import os
import json
import time
import random
import urllib.request
import urllib.error
import urllib.parse

try:
    import psutil
    _HAVE_PSUTIL = True
except Exception:
    _HAVE_PSUTIL = False

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSystemTrayIcon, QMenu, QComboBox, QSizePolicy, QFrame, QPlainTextEdit,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import (
    QIcon, QPainter, QColor, QPen, QPixmap, QFont, QAction, QBrush,
    QStandardItemModel, QStandardItem, QLinearGradient, QPainterPath,
    QFontMetrics, QRadialGradient,
)
from PySide6.QtCore import (Qt, QTimer, QPoint, QPointF, QSize, QModelIndex,
                             QRect, QElapsedTimer, QEvent, QThread, QObject, Signal,
                             QMetaObject, QSettings, QByteArray)

# ---------------------------------------------------------------------------
# Crash capture (pythonw has no console; never let a traceback die silently)
# ---------------------------------------------------------------------------
def _log_crash(where, exc):
    try:
        import datetime
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "hud_crash.log"), "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {where}: {type(exc).__name__}: {exc}\n")
    except Exception:
        pass

def _excepthook(exc_type, exc_val, exc_tb):
    try:
        import traceback as _tb
        stamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = _tb.format_exception(exc_type, exc_val, exc_tb)
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "hud_crash.log"), "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] UNCAUGHT: {''.join(lines)}\n")
    except Exception:
        pass

sys.excepthook = _excepthook

# ---------------------------------------------------------------------------
# Backend configuration
# ---------------------------------------------------------------------------
PROXY_BASE = "http://127.0.0.1:5119"
TELEMETRY_URL = f"{PROXY_BASE}/admin/telemetry"
POLL_MS = 2000

# Real models served by the proxy (verified live). The old 9B / 4B-Vision
# aliases were removed because those GGUFs no longer exist on this rig.
MODELS = [
    {"key": "27b", "id": "Qwen3.8-27B-Uncensored", "label": "Qwen3.8-27B - Think Hard", "pill": "RED"},
    {"key": "35b", "id": "Qwen3.6-35B-Uncensored", "label": "Qwen3.6-35B - Fast", "pill": "BLUE"},
]

# Known specs for the locally-served models (from telemetry + verified rig config).
# Used by the Active-Model Spec Card so the HUD shows real arch/quant/ctx, not guesses.
SPEC = {
    "Qwen3.8-27B-Uncensored": "27B dense  -  Q3_K_S  -  128K ctx",
    "Qwen3.6-35B-Uncensored": "35B MoE  -  Q3_K_S  -  128K ctx",
}

# ---------------------------------------------------------------------------
# Theme: the HUD body keeps the classic Matrix GREEN look.
# A separate top-right PILL BADGE carries the red/blue metaphor:
#   27B  -> RED PILL   (Think Hard: deeper, slower, bigger)
#   35B  -> BLUE PILL  (Fast: quick, lighter)
#   idle -> grey (no model resident)
# ---------------------------------------------------------------------------
ACCENTS = {
    "27b": {"base": (57, 255, 140), "light": (87, 255, 170), "dim": (28, 120, 70),
            "rain": (57, 255, 140), "head": (220, 255, 235), "log": (87, 255, 170)},
    "35b": {"base": (57, 255, 140), "light": (87, 255, 170), "dim": (28, 120, 70),
            "rain": (57, 255, 140), "head": (220, 255, 235), "log": (87, 255, 170)},
    "idle": {"base": (57, 255, 140), "light": (87, 255, 170), "dim": (28, 120, 70),
             "rain": (57, 255, 140), "head": (220, 255, 235), "log": (87, 255, 170)},
}


# ---------------------------------------------------------------------------
# Backend client
# ---------------------------------------------------------------------------
def fetch_telemetry():
    """Return the parsed /admin/telemetry dict, or None on failure."""
    try:
        req = urllib.request.Request(TELEMETRY_URL, headers={"User-Agent": "MatrixHUD"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        pass
    return None


def post_admin(path):
    """Fire-and-forget POST to an /admin/* endpoint. Returns True on 2xx."""
    try:
        req = urllib.request.Request(
            f"{PROXY_BASE}{path}", data=b"", method="POST",
            headers={"User-Agent": "MatrixHUD", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def ensure_model(model_id):
    """Bring a model online via the proxy. Returns True on success."""
    return post_admin(f"/admin/ensure?model={urllib.parse.quote(model_id)}")


# ---------------------------------------------------------------------------
# Server Auto-Discovery Catalog & Scanner
# ---------------------------------------------------------------------------
DISCOVER_SERVERS = [
    {"name": "ComfyUI", "port": 8188, "url": "http://127.0.0.1:8188/system_stats", "type": "image"},
    {"name": "Hermes Proxy", "port": 5119, "url": "http://127.0.0.1:5119/admin/telemetry", "type": "llm"},
    {"name": "Ollama", "port": 11434, "url": "http://127.0.0.1:11434/api/tags", "type": "llm"},
    {"name": "LM Studio", "port": 1234, "url": "http://127.0.0.1:1234/v1/models", "type": "llm"},
    {"name": "vLLM / LocalAI", "port": 8000, "url": "http://127.0.0.1:8000/v1/models", "type": "llm"},
    {"name": "Text-Gen WebUI", "port": 7860, "url": "http://127.0.0.1:7860", "type": "llm"},
]

def scan_local_ai_servers():
    """Scan all standard local AI endpoints and return a list of active services."""
    active = []
    for s in DISCOVER_SERVERS:
        try:
            req = urllib.request.Request(s["url"], headers={"User-Agent": "MatrixHUD"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=0.6) as resp:
                lat = int((time.time() - t0) * 1000)
                if resp.status in (200, 404, 401, 403):
                    active.append({**s, "status": "ONLINE", "latency_ms": lat})
        except Exception:
            pass
    return active


# ---------------------------------------------------------------------------
# Background telemetry fetcher
# The blocking HTTP call (urllib.urlopen, up to timeout 1.5s) MUST NOT run on
# the Qt GUI thread -- doing so freezes the rain/bars/input for the full
# timeout every poll cycle. This worker runs the fetch on a separate thread
# and emits the parsed dict (or None) back to the GUI thread via a signal.
# ---------------------------------------------------------------------------
class _TelemetryWorker(QObject):
    result_ready = Signal(object)
    servers_ready = Signal(list)

    def fetch(self):
        self.result_ready.emit(fetch_telemetry())
        try:
            self.servers_ready.emit(scan_local_ai_servers())
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pill badge pixmap
# ---------------------------------------------------------------------------
def make_ultra_hd_pill_pixmap(key, display_size=36):
    color = {
        "27b": QColor(255, 60, 90),
        "35b": QColor(80, 160, 255),
        "idle": QColor(120, 130, 140),
    }.get(key, QColor(120, 130, 140))
    label = {"27b": "RED", "35b": "BLUE", "idle": "IDLE"}.get(key, "IDLE")
    pm = QPixmap(display_size * 2, display_size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(color))
    p.setPen(QPen(QColor(255, 255, 255, 80)))
    r = pm.height() / 2
    p.drawRoundedRect(2, 2, pm.width() - 4, pm.height() - 4, r, r)
    p.setPen(QColor(255, 255, 255))
    p.setFont(QFont("Consolas", 11, QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, label)
    p.end()
    return pm


# ---------------------------------------------------------------------------
# Digital-rain background with live system-console log overlay
# ---------------------------------------------------------------------------
class CMatrixWidget(QWidget):
    GLYPHS = (
        # Katakana — the iconic Matrix glyph set (high density).
        "\u30a2\u30a4\u30a6\u30a8\u30aa\u30ab\u30ad\u30af\u30b1\u30b3"
        "\u30b5\u30b7\u30b9\u30bb\u30bd\u30bf\u30c1\u30c4\u30c6\u30c8"
        "\u30ca\u30cb\u30cc\u30cd\u30ce\u30cf\u30d2\u30d5\u30d8\u30db"
        "\u30de\u30df\u30e0\u30e1\u30e2\u30e4\u30e6\u30e8\u30e9\u30ea"
        "\u30eb\u30ec\u30ed\u30ef\u30f3"
        # Latin digits + a few symbols for contrast (sparse).
        "0123456789"
        "<>/+=*#@$%&"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_lines = []
        self._cols = []
        self._font = QFont("Consolas", 14, QFont.Bold)
        self._font.setHintingPreference(QFont.PreferVerticalHinting)
        self._cell = 11
        self._rebuild()
        # Cohesive default: full Matrix-green even before _apply_theme runs,
        # so nothing flashes slate/blue on first paint.
        self._rain = (57, 255, 140)
        self._head = QColor(220, 255, 235)
        self._log = (87, 255, 170)
        self._paused = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self._elapsed = QElapsedTimer()
        self._elapsed.start()
        # FPS metering (additive QOL: drawn bottom-left, no UI change).
        self._fps = 0.0
        self._last_tick = QElapsedTimer()
        self._last_tick.start()
        self._fps_acc = 0.0
        self._fps_frames = 0

    def _rebuild(self):
        w = max(1, self.width())
        h = max(1, self.height())
        n = max(1, w // self._cell)
        self._cols = [{
            "x": i * self._cell,
            "y": random.randint(-h, h),
            "sp": random.uniform(2.0, 6.0),
            "ln": random.randint(14, 34),
        } for i in range(n)]

    def set_accent(self, rain, head, log):
        self._rain = tuple(rain)
        self._head = QColor(*head) if not isinstance(head, QColor) else head
        self._log = tuple(log)
        self.update()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._rebuild()

    def _tick(self):
        # FPS metering (rolling 500ms window).
        self._fps_frames += 1
        ft = self._last_tick.restart()
        self._fps_acc += ft
        if self._fps_acc >= 500.0:
            self._fps = (self._fps_frames * 1000.0) / max(1.0, self._fps_acc)
            self._fps_acc = 0.0
            self._fps_frames = 0

        dt = self._elapsed.restart()              # ms since last tick
        h = self.height()
        step_per_ms = 0.12                         # ~2px/frame @60fps baseline
        for c in self._cols:
            c["y"] += c["sp"] * step_per_ms * dt
            if c["y"] > h + c["ln"] * self._cell:
                c["y"] = -random.randint(0, 240)
                c["sp"] = random.uniform(2.0, 6.0)
                c["ln"] = random.randint(6, 20)
        self.update()

    def toggle_pause(self):
        # Additive QOL: left-click on the canvas toggles rain pause/resume.
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
        else:
            self._timer.start(30)
            self._elapsed.restart()
            self._last_tick.restart()

    def mousePressEvent(self, ev):
        self.toggle_pause()

    def paintEvent(self, ev):
        p = QPainter(self)
        # Grayscale AA only — subpixel AA on the translucent window produces a
        # warm orange/brown fringe around each glyph. The opaque near-black
        # fill (below) hides this; grayscale rendering keeps it hidden.
        p.setRenderHint(QPainter.Antialiasing, True)

        # Solid near-black background. Opaque fill avoids the warm antialiasing
        # fringe that appears when translucent gray glyphs blend on a layered
        # window surface.
        p.fillRect(self.rect(), QColor(2, 4, 2, 255))

        p.setFont(self._font)
        h = self.height()

        # Rain color from accent (shared with pill/bars for cohesion).
        rg, gg, bg = self._rain

        for c in self._cols:
            base_row = int(c["y"] // self._cell)
            for k in range(c["ln"]):
                row = base_row - k
                yy = row * self._cell
                if 0 <= yy <= h:
                    ch = self._glyph_at(c["x"], row)
                    if k == 0:
                        # Bright leading glyph — classic Matrix white-green head.
                        p.setPen(QPen(QColor(230, 255, 230)))
                    else:
                        # Fade from bright green toward black down the trail.
                        fade = max(0.0, 1.0 - k / c["ln"])
                        r = int(rg * fade * 0.35)
                        g = int(50 + gg * fade * 0.65)
                        b = int(bg * fade * 0.35)
                        alpha = max(70, int(255 * fade))
                        p.setPen(QColor(r, g, b, alpha))
                    p.drawText(c["x"], yy, ch)

        # System-console log overlay — same green family as the rain.
        if getattr(self, "_log_lines", []):
            p.setFont(QFont("Consolas", 9))
            max_lines = max(1, self.height() // 14)
            visible = self._log_lines[-max_lines:]
            for idx, line in enumerate(visible):
                ly = self.height() - (len(visible) - idx) * 14 - 4
                if ly < 12:
                    continue
                p.setPen(QColor(60, 220, 120))
                p.drawText(6, ly, line[:120])

        # FPS meter bottom-left — bright green, matches rain accent.
        p.setFont(QFont("Consolas", 9))
        fps_txt = f"{self._fps:5.1f} FPS" + ("  [PAUSED]" if self._paused else "")
        p.setPen(QPen(QColor(57, 255, 140, 220)))
        p.drawText(8, self.height() - 8, fps_txt)
        p.end()

    def add_log(self, msg):
        if not hasattr(self, "_log_lines"):
            self._log_lines = []
        ts = time.strftime("%H:%M:%S", time.localtime())
        self._log_lines.append(f"[{ts}] {msg}")
        if len(self._log_lines) > 200:
            self._log_lines = self._log_lines[-200:]
        self.update()

    def clear_logs(self):
        self._log_lines = []
        self.update()

    def _glyph_at(self, x, row):
        # Stable per-cell glyph: deterministic per (column,row), so the rain
        # does not flicker/reroll on every paint. Flips smoothly as the
        # stream advances a full cell.
        seed = (int(x) * 73856093) ^ (int(row) * 19349663)
        seed %= len(self.GLYPHS)
        return self.GLYPHS[seed]


# ---------------------------------------------------------------------------
# Custom resource bar.
# QProgressBar was replaced: at low values its ::chunk renders as a tiny
# rounded pill pinned to the left, colliding with the left-aligned label
# text. This widget paints the track, a proportional fill, and the label
# crisply on top so the bar reads correctly at any percentage.
# ---------------------------------------------------------------------------
class LineGraph(QWidget):
    """Rolling moving-line graph (no numbers) — same language as the
    tok/s graph at the bottom. One per resource (VRAM/GPU/RAM/CPU)."""
    def __init__(self, color=QColor(57, 255, 140), name="", parent=None,
                 max_samples=80, fixed_max=None):
        super().__init__(parent)
        self._color = color
        self._ax = color
        self._name = name
        self._max = max_samples
        self._fixed = fixed_max  # None => auto-scale (tok/s); 100 => % graphs
        self._samples = []
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def push(self, value):
        self._samples.append(max(0.0, float(value)))
        if len(self._samples) > self._max:
            self._samples = self._samples[-self._max:]
        self.update()

    def set_theme(self, color):
        self._color = color
        self._ax = color
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # panel
        p.setBrush(QColor(12, 16, 20, 230))
        p.setPen(QPen(QColor(self._ax.red(), self._ax.green(), self._ax.blue(), 35)))
        p.drawRoundedRect(QRect(0, 0, w, h), 6, 6)

        # REAL scale axis (right edge). Percentage graphs show 100/50/0 so the
        # line height is directly readable & verifiable against telemetry.
        name_w = 64
        axis_x = w - 30
        p.setPen(QPen(QColor(self._ax.red(), self._ax.green(), self._ax.blue(), 30)))
        axis_font = QFont("Consolas", 8, QFont.Bold)
        p.setFont(axis_font)
        p.setBrush(Qt.NoBrush)
        for frac, lbl in ((0.0, "100"), (0.5, "50"), (1.0, "0")):
            y = 4 + frac * (h - 8)
            p.drawLine(axis_x, y, axis_x + 6, y)
            p.setPen(QColor(self._ax.red(), self._ax.green(), self._ax.blue(), 55))
            p.drawText(QRect(axis_x + 8, int(y) - 7, 18, 14),
                       Qt.AlignLeft | Qt.AlignVCenter, lbl)
            p.setPen(QPen(QColor(self._ax.red(), self._ax.green(), self._ax.blue(), 30)))

        # baseline grid (faint, 25/50/75) for continuity
        p.setPen(QPen(QColor(self._ax.red(), self._ax.green(), self._ax.blue(), 14)))
        for frac in (0.25, 0.5, 0.75):
            gy = int(4 + frac * (h - 8))
            p.drawLine(name_w, gy, axis_x, gy)

        n = len(self._samples)
        if n >= 2:
            # Fixed-range graphs (percentages) map to a 0..fixed ceiling so the
            # line height reflects the REAL utilization level, not the graph's
            # own running peak. Auto-scale (tok/s) keeps its own peak.
            peak = float(self._fixed) if self._fixed is not None else (max(self._samples) or 1.0)
            plot_w = axis_x - name_w
            step = plot_w / max(1, (self._max - 1))
            off = name_w
            pts = [QPointF(off + i * step, 4 + (1 - v / peak) * (h - 8))
                   for i, v in enumerate(self._samples)]
            # soft fill under the line
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(self._color.red(), self._color.green(),
                                        self._color.blue(), 90))
            grad.setColorAt(1.0, QColor(self._color.red(), self._color.green(),
                                        self._color.blue(), 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawPolygon([QPointF(pts[0].x(), h - 2)] + pts + [QPointF(pts[-1].x(), h - 2)])
            # the moving line
            p.setPen(QPen(self._color, 2))
            p.drawPolyline(pts)
        # name tag (no numbers) — left side, clearly readable
        fnt = QFont("Consolas", 11, QFont.Bold)
        fm = QFontMetrics(fnt)
        tw = fm.horizontalAdvance(self._name) + 12
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 175))
        p.drawRoundedRect(QRect(5, 3, tw, fm.height() + 4), 4, 4)
        p.setPen(QPen(self._color, 1))
        p.setBrush(Qt.NoBrush)
        p.setFont(fnt)
        p.drawText(QRect(5, 3, tw, fm.height() + 4),
                   Qt.AlignCenter, self._name)
        p.end()


# ---------------------------------------------------------------------------
# Status dot (green = model resident / backend online, red = offline)
# ---------------------------------------------------------------------------
class StatusDot(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._accent = QColor(57, 255, 140)
        self._on = False
        self.set_on(False)

    def set_accent(self, color):
        self._accent = color
        self.set_on(self._on)

    def set_on(self, on):
        self._on = on
        color = self._accent if on else QColor("#e0506a")
        self.setStyleSheet(f"QLabel{{background:{color.name()}; border-radius:6px;}}")


# ---------------------------------------------------------------------------
# MiniSpark - rolling tok/s history graph (additive telemetry viz, mono-green)
# ---------------------------------------------------------------------------
class MiniSpark(QWidget):
    def __init__(self, parent=None, max_samples=60):
        super().__init__(parent)
        self._max = max_samples
        self._samples = []
        self._cur = 0.0
        self._color = QColor(87, 255, 170)
        self.setMinimumHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_color(self, color):
        self._color = color
        self.update()

    def push(self, value):
        self._cur = max(0.0, float(value))
        self._samples.append(self._cur)
        if len(self._samples) > self._max:
            self._samples = self._samples[-self._max:]
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QColor(10, 22, 18, 220))
        p.setPen(QPen(QColor(255, 255, 255, 18)))
        p.drawRoundedRect(QRect(0, 0, w, h), 6, 6)
        if len(self._samples) >= 2:
            peak = max(self._samples) or 1.0
            step = w / max(1, (self._max - 1))
            n = len(self._samples)
            pts = [QPointF(i * step, h - 3 - (v / peak) * (h - 6)) for i, v in enumerate(self._samples)]
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(self._color.red(), self._color.green(), self._color.blue(), 120))
            grad.setColorAt(1.0, QColor(self._color.red(), self._color.green(), self._color.blue(), 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            poly = [QPointF(0, h)] + pts + [QPointF((n - 1) * step, h)]
            p.drawPolygon(poly)
            p.setPen(QPen(self._color, 2))
            p.drawPolyline(pts)
        p.end()


# ---------------------------------------------------------------------------
# StatusPill - crisp vector top-right status indicator (replaces the low-res
# pixmap). A small colored core dot + green glass shell, mono-green theme.
# ---------------------------------------------------------------------------
class StatusPill(QWidget):
    """Top-right pill badge: RED (27B) / BLUE (35B) / IDLE.
    Driven by the active model key -- call set_key() to update."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._key = "idle"
        self._ax = QColor(57, 255, 140)
        self.setFixedSize(132, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._map = {
            "27b":  {"core": QColor(255, 70, 90),   "txt": "RED  ·  27B",  "tip": "RED PILL  -  Qwen3.8-27B  (Think Hard)"},
            "35b":  {"core": QColor(70, 150, 255),  "txt": "BLUE  ·  35B", "tip": "BLUE PILL  -  Qwen3.6-35B  (Fast)"},
            "idle": {"core": QColor(150, 162, 178), "txt": "IDLE",         "tip": "IDLE  -  backend ready"},
        }

    def set_key(self, key):
        self._key = key or "idle"
        self.setToolTip(self._map.get(self._key, self._map["idle"])["tip"])
        self.update()

    def set_accent(self, color):
        self._ax = color
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = self._map.get(self._key, self._map["idle"])
        core = m["core"]
        # pill shell: filled in the pill color (low alpha) + bright border
        p.setBrush(QColor(core.red(), core.green(), core.blue(), 40))
        p.setPen(QPen(QColor(core.red(), core.green(), core.blue(), 230), 1.6))
        p.drawRoundedRect(QRect(1, 1, w - 2, h - 2), h / 2, h / 2)
        # glowing status dot
        p.setPen(Qt.NoPen)
        p.setBrush(core)
        p.drawEllipse(QRect(9, h / 2 - 5, 10, 10))
        # label
        p.setPen(QColor(235, 255, 245, 245))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(QRect(24, 0, w - 26, h), Qt.AlignVCenter | Qt.AlignLeft, m["txt"])
        p.end()


# ---------------------------------------------------------------------------
# Main HUD window
# ---------------------------------------------------------------------------
class HermesMatrixApp(QWidget):
    def __init__(self):
        super().__init__()
        self._current_key = "idle"
        self._drag = None
        self._setup_ui()
        self._setup_tray()
        self._start_poll()

        # Fast IPC show-trigger watcher (< 100ms response to ComfyUI / shortcut focus commands)
        self._ipc_trigger_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".show_hud")
        self._ipc_timer = QTimer(self)
        self._ipc_timer.timeout.connect(self._check_ipc_trigger)
        self._ipc_timer.start(100)

    def _check_ipc_trigger(self):
        try:
            if os.path.isfile(self._ipc_trigger_file):
                os.remove(self._ipc_trigger_file)
                self._restore()
        except Exception:
            pass

    def changeEvent(self, ev):
        # QOL: pause the rain while minimized/hidden to avoid a frozen-then-
        # jumps feel on restore, and to save CPU. Additive only.
        if ev.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.rain._timer.stop()
            else:
                self.rain._timer.start(30)
                self.rain._elapsed.restart()
        super().changeEvent(ev)

    # ---- UI ----
    def _setup_ui(self):
        self.setWindowTitle("MATRIX - LOCAL AI")
        self.setMinimumSize(420, 560)
        self.resize(600, 720)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Restore saved geometry (additive QOL). Falls back to default size
        # if no valid saved frame exists yet.
        self._settings = QSettings("LocalCoder", "MatrixHUD")
        geo = self._settings.value("geometry")
        if isinstance(geo, QByteArray) and geo.size() > 0:
            self.restoreGeometry(geo)

        # Validate that window is on a visible screen, else center on primary monitor
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            if not screen.intersects(self.geometry()):
                self.move((screen.width() - 600) // 2, (screen.height() - 720) // 2)
        except Exception:
            pass

        # Background rain
        self.rain = CMatrixWidget(self)
        self.rain.setGeometry(0, 0, self.width(), self.height())

        # Foreground content panel
        self.content = QWidget(self)
        self.content.setGeometry(0, 0, self.width(), self.height())
        # Opaque-ish dark backing (0.90) so the green border sits on a
        # consistent Matrix-dark surface instead of blending with the bright
        # wallpaper behind the translucent window (which read as brown/olive).
        self.content.setStyleSheet(
            "QWidget#content{background:rgba(6,12,10,0.90); border:1px solid rgba(57,255,140,0.45);"
            "border-radius:16px;}")
        self.content.setObjectName("content")
        # Soft drop shadow so the frameless panel floats above the wallpaper.
        shadow = QGraphicsDropShadowEffect(self.content)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.content.setGraphicsEffect(shadow)

        lay = QVBoxLayout(self.content)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # Title row
        top = QHBoxLayout()
        self.title = QLabel("MATRIX  -  LOCAL AI")
        self.title.setStyleSheet(
            "color:#9dffc4; font:bold 14px 'Consolas'; letter-spacing:2px;"
            "text-shadow:0 0 8px rgba(57,255,140,0.7), 0 1px 2px rgba(0,0,0,0.8);")
        self.badge_lbl = StatusPill()
        self.badge_lbl.set_key("idle")
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.badge_lbl)
        lay.addLayout(top)

        # Active-model spec card (replaces plain MODEL label - richer, same info)
        self.spec_card = QFrame()
        self.spec_card.setStyleSheet(
            "QFrame{background:rgba(0,0,0,0.40); border:1px solid rgba(57,255,140,0.45);"
            "border-radius:8px; padding:6px;}")
        sc_lay = QHBoxLayout(self.spec_card)
        sc_lay.setContentsMargins(8, 6, 8, 6)
        sc_lay.setSpacing(8)
        self.spec_dot = StatusDot()
        sc_lay.addWidget(self.spec_dot)
        sc_text = QVBoxLayout()
        sc_text.setSpacing(2)
        self.spec_name = QLabel("MODEL: Idle (Ready)")
        self.spec_name.setStyleSheet("color:#bfffd6; font:bold 12px 'Consolas';")
        self.spec_meta = QLabel("no model loaded")
        self.spec_meta.setStyleSheet("color:#7dffb0; font:10px 'Consolas';")
        sc_text.addWidget(self.spec_name)
        sc_text.addWidget(self.spec_meta)
        sc_lay.addLayout(sc_text)
        lay.addWidget(self.spec_card)

        # Bars (VRAM / GPU / RAM / CPU) — single coherent matrix-green family.
        # All four share the same hue; only lightness/value varies so the HUD
        # reads as one monochrome-green theme, not a rainbow of statuses.
        self.vram_bar = LineGraph(QColor(57, 255, 140), "VRAM", fixed_max=100)
        self.gpu_bar = LineGraph(QColor(46, 224, 120), "GPU", fixed_max=100)
        self.ram_bar = LineGraph(QColor(38, 196, 104), "RAM", fixed_max=100)
        self.cpu_bar = LineGraph(QColor(30, 168, 88), "CPU", fixed_max=100)
        for b in (self.vram_bar, self.gpu_bar, self.ram_bar, self.cpu_bar):
            lay.addWidget(b)

        # Model picker (tiered)
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(
            "QComboBox{background:rgba(8,20,16,0.90); color:#39ff8c; border:1px solid "
            "rgba(57,255,140,0.45); border-radius:8px; padding:6px; font:12px 'Consolas';}"
            "QComboBox QAbstractItemView{background:#0c1814; color:#39ff8c; selection-background-color:#1c4a36;}")
        self._build_model_model()
        self.model_combo.currentIndexChanged.connect(self._on_model_pick)
        lay.addWidget(self.model_combo)

        # Speed line
        self.speed_lbl = QLabel("- tok/s")
        self.speed_lbl.setStyleSheet("color:#39ff8c; font:bold 12px 'Consolas';")
        lay.addWidget(self.speed_lbl)
        # spacer so the speed label doesn't crowd the TOK/S graph name tag
        lay.addSpacing(4)

        # Live tok/s graph (same LineGraph type & size as the resource graphs)
        self.spark = LineGraph(QColor(87, 255, 170), "TOK/S", fixed_max=None)
        lay.addWidget(self.spark)

        # System console (live log feed — restored from the original HUD spec).
        # Read-only, dark backdrop, mono font to match the matrix aesthetic.
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(110)
        self.console.setStyleSheet(
            "QPlainTextEdit{background:rgba(4,10,8,0.85); color:#7dffb0; "
            "border:1px solid rgba(57,255,140,0.45); border-radius:8px; "
            "font:10px 'Consolas'; padding:6px;}")
        lay.addWidget(self.console)

        # Server Auto-Discovery Ribbon
        self.servers_ribbon = QLabel("LOCAL AI: Scanning standard ports (8188, 5119, 11434, 1234, 8000)...")
        self.servers_ribbon.setStyleSheet(
            "QLabel{background:rgba(4,10,8,0.85); color:#7dffb0; "
            "border:1px solid rgba(57,255,140,0.45); border-radius:6px; "
            "font:bold 10px 'Consolas'; padding:5px;}")
        lay.addWidget(self.servers_ribbon)

        lay.addStretch(1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.clear_btn = QPushButton("CLEAR VRAM")
        self.clear_btn.setStyleSheet(self._btn("#39ff8c"))
        self.clear_btn.clicked.connect(self._on_clear)

        self.studio_btn = QPushButton("LAUNCH STUDIO")
        self.studio_btn.setStyleSheet(self._btn("#39ff8c"))
        def _launch_studio():
            import subprocess
            for p in [r"C:\Users\jakeb\AppData\Local\Programs\ComfyUIX\ComfyUIX.exe",
                      r"C:\ComfyUI-Desktop\ComfyUIX.exe",
                      r"C:\Users\jakeb\Documents\antigravity\silly-tesla\ComfyUI_App.py"]:
                if os.path.exists(p):
                    try:
                        if p.endswith(".py"):
                            subprocess.Popen([sys.executable, p])
                        else:
                            subprocess.Popen([p])
                        self.log(f"Launched ComfyUI Studio: {os.path.basename(p)}")
                        return
                    except Exception as err:
                        self.log(f"Launch error: {err}")
        self.studio_btn.clicked.connect(_launch_studio)

        self.feed_btn = QPushButton("CLEAR FEED")
        self.feed_btn.setStyleSheet(self._btn("#39ff8c"))
        self.feed_btn.clicked.connect(lambda: self.console.clear())
        self.hide_btn = QPushButton("HIDE TO TRAY")
        self.hide_btn.setStyleSheet(self._btn("#39ff8c"))
        self.hide_btn.clicked.connect(self.hide)

        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.studio_btn)
        btn_row.addWidget(self.feed_btn)
        btn_row.addWidget(self.hide_btn)
        lay.addLayout(btn_row)

        # Adopt the pill-color theme (replaces the old mono-green look).
        self._apply_theme("idle")

    def _make_bar(self, label, color):
        return MiniBar(label, color)

    def _btn(self, accent):
        return (f"QPushButton{{background:{accent}; border:none; border-radius:8px; "
                f"padding:8px; color:#0a0f0c; font:bold 11px 'Consolas';}} "
                f"QPushButton:hover{{background:#ffffff;}}")

    def _apply_theme(self, key):
        a = ACCENTS.get(key, ACCENTS["idle"])
        base = "#%02x%02x%02x" % a["base"]
        light = "#%02x%02x%02x" % a["light"]
        dim = "#%02x%02x%02x" % a["dim"]
        # Digital rain follows the pill color.
        self.rain.set_accent(a["rain"], a["head"], a["log"])
        # Resource + tok/s graphs follow the pill color.
        self.vram_bar.set_theme(QColor(*a["base"]))
        self.gpu_bar.set_theme(QColor(*a["light"]))
        self.ram_bar.set_theme(QColor(*a["light"]))
        self.cpu_bar.set_theme(QColor(*a["base"]))
        self.spark.set_theme(QColor(*a["light"]))
        # Title.
        self.title.setStyleSheet(
            f"color:{base}; font:bold 14px 'Consolas'; letter-spacing:2px;"
            f"text-shadow:0 0 8px {base}, 0 1px 2px rgba(0,0,0,0.8);")
        # Content panel: opaque dark backing + unified 0.45 green border so the
        # wallpaper no longer bleeds through and muddies the edge to brown.
        self.content.setStyleSheet(
            f"QWidget#content{{background:rgba(6,12,10,0.90); border:1px solid {base}73;"
            f"border-radius:16px;}}")
        # Active-model spec card.
        self.spec_card.setStyleSheet(
            f"QFrame{{background:rgba(0,0,0,0.40); border:1px solid {base}73;"
            f"border-radius:8px; padding:6px;}}")
        # System console.
        self.console.setStyleSheet(
            f"QPlainTextEdit{{background:rgba(4,10,8,0.85); color:{light}; "
            f"border:1px solid {base}73; border-radius:8px; "
            f"font:10px 'Consolas'; padding:6px;}}")
        # Servers ribbon.
        if hasattr(self, "servers_ribbon"):
            self.servers_ribbon.setStyleSheet(
                f"QLabel{{background:rgba(4,10,8,0.85); color:{light}; "
                f"border:1px solid {base}73; border-radius:6px; "
                f"font:bold 10px 'Consolas'; padding:5px;}}")
        # Buttons.
        for b in (self.clear_btn, self.studio_btn, self.feed_btn, self.hide_btn):
            b.setStyleSheet(self._btn(base))
        # Model picker accent.
        self.model_combo.setStyleSheet(
            f"QComboBox{{background:rgba(8,20,16,0.90); color:{base}; border:1px solid "
            f"{base}73; border-radius:8px; padding:6px; font:12px 'Consolas';}}"
            f"QComboBox QAbstractItemView{{background:#0c1814; color:{base}; selection-background-color:{dim};}}")
        # Speed label.
        self.speed_lbl.setStyleSheet(f"color:{base}; font:bold 12px 'Consolas';")
        # Status dot adopts the pill accent when a model is resident.
        self.spec_dot.set_accent(QColor(*a["base"]))
        self.badge_lbl.set_accent(QColor(*a["base"]))

    def _build_model_model(self):
        model = QStandardItemModel()
        cat1 = QStandardItem("Matrix Local AI")
        cat1.setEnabled(False)
        for m in MODELS:
            it = QStandardItem(m["label"])
            it.setData(m["key"], Qt.UserRole)
            cat1.appendRow(it)
        cat2 = QStandardItem("System")
        cat2.setEnabled(False)
        idle = QStandardItem("Idle / Clear VRAM")
        idle.setData("idle", Qt.UserRole)
        cat2.appendRow(idle)
        model.appendRow(cat1)
        model.appendRow(cat2)
        self.model_combo.setModel(model)
        self.model_combo.setRootModelIndex(QModelIndex())
        # Select Idle by default (System root, child row 0)
        sys_idx = self.model_combo.model().index(1, 0)
        self.model_combo.setRootModelIndex(sys_idx)
        self.model_combo.setCurrentIndex(0)

    # ---- Tray ----
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(make_ultra_hd_pill_pixmap("idle", 64)))
        menu = QMenu()
        show_act = QAction("Show HUD", self)
        show_act.triggered.connect(self._restore)
        menu.addAction(show_act)
        clear_act = QAction("Clear VRAM", self)
        clear_act.triggered.connect(self._on_clear)
        menu.addAction(clear_act)
        feed_act = QAction("Clear Feed", self)
        feed_act.triggered.connect(lambda: self.console.clear())
        menu.addAction(feed_act)
        menu.addSeparator()
        quit_act = QAction("Exit", self)
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore()

    def _restore(self):
        try:
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.showNormal()
            self.show()
            self.raise_()
            self.activateWindow()
            if os.name == "nt":
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    # ---- Poll ----
    def _start_poll(self):
        # Run the blocking telemetry HTTP fetch on a worker thread so the
        # GUI event loop never stalls (the old code called urlopen on the
        # GUI thread, freezing the rain/bars for up to the 1.5s timeout
        # every 2s cycle). The result dict is delivered via a signal.
        self._worker = _TelemetryWorker()
        self._worker_thread = QThread(self)
        self._worker.moveToThread(self._worker_thread)
        self._worker.result_ready.connect(self._apply_telemetry)
        self._worker.servers_ready.connect(self._on_servers_ready)
        self._worker_thread.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_safe)
        self._timer.start(POLL_MS)
        self.log("Matrix HUD online.")
        self._poll_safe()

    def _on_servers_ready(self, servers):
        try:
            if not hasattr(self, "servers_ribbon"):
                return
            if not servers:
                self.servers_ribbon.setText("LOCAL SERVERS: Standby (None active)")
                return
            chips = []
            for s in servers:
                chips.append(f"{s['name']}:{s['port']} 🟢 ({s['latency_ms']}ms)")
            self.servers_ribbon.setText("SERVERS:  " + "  •  ".join(chips))
        except Exception:
            pass

    def _poll_safe(self):
        # Non-blocking: hand the fetch to the worker thread.
        if not self._worker_thread.isRunning():
            return
        QMetaObject.invokeMethod(self._worker, "fetch", Qt.QueuedConnection)

    def _apply_telemetry(self, t):
        # Runs on GUI thread with fetched dict; original UI updates preserved.
        try:
            self._render_telemetry(t)
        except Exception as _e:
            _log_crash("_poll", _e)

    def _render_telemetry(self, t):
        if not t:
            self.spec_dot.set_on(False)
            self.spec_name.setText("MODEL: Idle")
            self.spec_meta.setText("backend offline - check LocalAIDaemon")
            self.tray.setIcon(QIcon(make_ultra_hd_pill_pixmap("idle", 64)))
            return

        vtot = t.get("vram_total_mb") or 1
        vused = t.get("vram_used_mb") or 0
        vfree = t.get("vram_free_mb") or 0
        vpct = (vused / vtot) * 100 if vtot else 0
        self.vram_bar.push(vpct)

        gpu = t.get("gpu_util_pct") or 0
        self.gpu_bar.push(gpu)

        # RAM / CPU measured client-side (proxy does not report them)
        if _HAVE_PSUTIL:
            try:
                ram = psutil.virtual_memory().percent
                cpu = psutil.cpu_percent(interval=None)
            except Exception:
                ram, cpu = 0, 0
        else:
            ram, cpu = 0, 0
        self.ram_bar.push(ram)
        self.cpu_bar.push(cpu)

        # Which backends are actually resident on the GPU right now
        loaded = t.get("loaded_backends") or []

        alias = t.get("active_alias") or "Idle"
        tps = t.get("tok_per_sec") or 0.0
        self.speed_lbl.setText(f"{alias}  -  {tps:.1f} tok/s")
        self.spark.push(tps)

        # Pill color from active model
        key = "idle"
        a = (alias or "").lower()
        if "27b" in a:
            key = "27b"
        elif "35b" in a:
            key = "35b"
        if key != self._current_key:
            self._current_key = key
            self.tray.setIcon(QIcon(make_ultra_hd_pill_pixmap(key, 64)))
            self._apply_theme(key)
            self.badge_lbl.set_key(key)
            pill_txt = {"27b": "RED PILL (27B)", "35b": "BLUE PILL (35B)", "idle": "IDLE"}[key]
            self.rain.add_log(f"{pill_txt} active.")
            self.log(f"{pill_txt} active.")

        # Active-Model Spec Card (status dot + name + real specs / loaded)
        self.spec_dot.set_on(bool(loaded))
        self.spec_name.setText(f"MODEL: {alias}")
        free = f"{vfree/1024:.1f}GB free"
        if loaded:
            meta = "LOADED: " + " + ".join(str(b) for b in loaded) + f"  ·  {free}"
        elif alias and alias != "Idle":
            meta = SPEC.get(alias, "ready") + f"  ·  {free}"
        else:
            meta = f"backend OK  ·  {free}"
        self.spec_meta.setText(meta)
        self.tray.setToolTip(
            f"Matrix Local AI: {alias}\nVRAM {vused/1024:.1f}/{vtot/1024:.1f} GB\n"
            f"{tps:.1f} tok/s\nClick pill to restore")

    def log(self, msg):
        # Visible system console (the old HUD's live log feed).
        ts = time.strftime("%H:%M:%S", time.localtime())
        self.console.appendPlainText(f"[{ts}] {msg}")
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum())

    # ---- Actions ----
    def _on_model_pick(self, index):
        model = self.model_combo.model()
        item = model.itemFromIndex(
            model.index(self.model_combo.currentIndex(), 0, self.model_combo.rootModelIndex()))
        if item is None:
            return
        key = item.data(Qt.UserRole)
        if key == "idle":
            self._on_clear()
            return
        m = next((x for x in MODELS if x["key"] == key), None)
        if not m:
            return
        self.rain.add_log(f"Loading {m['id']}...")
        self.log(f"Loading {m['id']}...")
        ok = ensure_model(m["id"])
        if ok:
            self.rain.add_log(f"{m['id']} online.")
            self.log(f"{m['id']} online.")
        else:
            self.rain.add_log(f"ERROR: failed to load {m['id']}.")
            self.log(f"ERROR: failed to load {m['id']}.")

    def _on_clear(self):
        self.clear_btn.setText("FREEING...")
        ok = post_admin("/admin/unload_all")
        self.clear_btn.setText("CLEAR VRAM")
        if ok:
            self.rain.add_log("VRAM freed.")
            self.log("VRAM freed.")
        else:
            self.rain.add_log("ERROR: unload failed.")
            self.log("ERROR: unload failed.")

    def _quit(self):
        post_admin("/admin/unload_all")
        QApplication.instance().quit()

    # ---- Frameless drag + close-to-tray ----
    def _save_geometry(self):
        # Additive QOL: persist window frame (pos+size) across restarts.
        if hasattr(self, "_settings"):
            self._settings.setValue("geometry", self.saveGeometry())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if hasattr(self, "rain"):
            self.rain.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, "content"):
            self.content.setGeometry(0, 0, self.width(), self.height())
        self._save_geometry()

    def moveEvent(self, ev):
        super().moveEvent(ev)
        self._save_geometry()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_global = ev.globalPosition().toPoint()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if getattr(self, "_drag", None) is not None and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and getattr(self, "_drag", None) is not None:
            # Click (not drag) on the canvas toggles rain pause/resume.
            press = getattr(self, "_press_global", None)
            if press is not None:
                dist = (ev.globalPosition().toPoint() - press).manhattanLength()
                if dist < 5:
                    self.rain.toggle_pause()
        self._drag = None
        self._save_geometry()

    # ---- Frameless resizing (native WM_NCHITTEST hit-testing) ----
    _RESIZE_MARGIN = 12

    def nativeEvent(self, eventType, message):  # noqa: N802 (PySide name)
        # Only handle WM_NCHITTEST so the frameless window can be resized
        # from any edge/corner while the body stays drag-movable.
        import ctypes
        try:
            msg = ctypes.wintypes.MSG.from_address(int(message))
        except Exception:
            return super().nativeEvent(eventType, message)
        if msg.message != 0x0084:  # WM_NCHITTEST
            return super().nativeEvent(eventType, message)
        x = msg.lParam & 0xFFFF
        y = (msg.lParam >> 16) & 0xFFFF
        gx = self.frameGeometry()
        m = self._RESIZE_MARGIN
        left = x < gx.left() + m
        right = x > gx.right() - m
        top = y < gx.top() + m
        bottom = y > gx.bottom() - m
        HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
        HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17
        result = 1  # HTCLIENT (drag area)
        if left and top:
            result = HTTOPLEFT
        elif right and top:
            result = HTTOPRIGHT
        elif left and bottom:
            result = HTBOTTOMLEFT
        elif right and bottom:
            result = HTBOTTOMRIGHT
        elif left:
            result = HTLEFT
        elif right:
            result = HTRIGHT
        elif top:
            result = HTTOP
        elif bottom:
            result = HTBOTTOM
        return (True, result)

    def closeEvent(self, ev):
        # External (watchdog) close: perform a real quit so no tray icon or
        # hidden window lingers. User close (clicking X) still minimizes to
        # tray per the original design.
        if os.path.exists(r"C:\LocalCoder\.hud_ext_close"):
            try:
                os.remove(r"C:\LocalCoder\.hud_ext_close")
            except OSError:
                pass
            post_admin("/admin/unload_all")  # free VRAM
            QApplication.instance().quit()    # fully exit (removes tray icon)
            ev.accept()
            return
        # Minimize to tray instead of quitting.
        ev.ignore()
        self.hide()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    # Hide the launcher console (pythonw already hides it; harmless if missing).
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Single-instance guard (replaces the broken embedded Hermes watcher).
    import ctypes
    KERNEL32 = ctypes.windll.kernel32
    mutex = KERNEL32.CreateMutexW(None, False, "LocalCoderHermesMatrixHUD")
    if mutex and KERNEL32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)

    hud = HermesMatrixApp()
    hud.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
