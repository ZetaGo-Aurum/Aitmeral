"""System & capability detection — cross-platform (Linux, Windows, macOS, Termux)."""

from __future__ import annotations

import ctypes
import os
import platform
import re
import shutil
import subprocess
import sys
import threading

from aureus import MIN_RAM_GB, __version__

_LOCK = threading.Lock()
_CAPS_CACHE = None


# --------------------------------------------------------------- platform
def platform_key() -> str:
    """Return one of: termux | linux | windows | macos."""
    if os.environ.get("TERMUX_VERSION") or os.environ.get("PREFIX", "").startswith("/data/data/com.termux"):
        return "termux"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def platform_name() -> str:
    key = platform_key()
    names = {
        "termux": "Android (Termux)",
        "linux": f"Linux ({platform.system()} {platform.release()})",
        "windows": f"Windows ({platform.release()})",
        "macos": f"macOS {platform.mac_ver()[0]}",
    }
    return names.get(key, platform.platform())


# ------------------------------------------------------------------- ram
def total_ram_gb() -> float:
    """Total physical RAM in GB — best effort across platforms."""
    try:
        import psutil  # type: ignore
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    if platform_key() == "windows":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore
            return stat.ullTotalPhys / (1024 ** 3)
        except Exception:
            pass

    if platform_key() == "macos":
        try:
            out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
            return int(out.stdout.strip()) / (1024 ** 3)
        except Exception:
            pass

    # Linux / Termux / fallbacks
    try:
        with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return float(line.split()[1]) / (1024 ** 2)  # kB -> GB
    except Exception:
        pass

    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
    except Exception:
        return 0.0


def ram_ok() -> bool:
    return total_ram_gb() >= MIN_RAM_GB


# ----------------------------------------------------------------- bins
def find_binary(name: str):
    """Locate an executable, also checking well-known extra locations."""
    p = shutil.which(name)
    if p:
        return p
    extra_dirs = []
    key = platform_key()
    if key == "windows":
        extra_dirs = [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
        ]
    elif key == "macos":
        extra_dirs = ["/opt/homebrew/bin", "/usr/local/bin"]
    elif key == "termux":
        extra_dirs = [os.environ.get("PREFIX", "/data/data/com.termux/files/usr") + "/bin"]
    for d in extra_dirs:
        if not d:
            continue
        for exe in (name + ".exe", name):
            p = os.path.join(d, exe)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None


def ffmpeg_path():
    return find_binary("ffmpeg")


def ffprobe_path():
    return find_binary("ffprobe")


def ytdlp_path():
    return find_binary("yt-dlp")


def binary_version(binpath: str) -> str:
    flag = "--version" if "yt-dlp" in os.path.basename(binpath).lower() else "-version"
    try:
        out = subprocess.run([binpath, flag], capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).splitlines()[0][:120]
    except Exception:
        return "unknown"


class Caps:
    """Which encoders / filters this ffmpeg build supports."""

    def __init__(self, encoders: set, filters: set, ffmpeg: str = "", hwaccels: set = None):
        self.encoders = encoders
        self.filters = filters
        self.ffmpeg = ffmpeg
        self.hwaccels = hwaccels or set()

    def has_enc(self, name: str) -> bool:
        return name in self.encoders

    def has_filter(self, name: str) -> bool:
        return name in self.filters

    def has_hwaccel(self, name: str) -> bool:
        return name in self.hwaccels

    def brief(self) -> dict:
        keys = ["libx264", "libx265", "ffv1", "prores_ks", "dnxhd", "libaom-av1", "libsvtav1"]
        fkeys = ["zscale", "tonemap", "cas", "nlmeans", "minterpolate", "xbr", "deband", "deblock", "hqdn3d", "unsharp"]
        return {
            "encoders": {k: self.has_enc(k) for k in keys},
            "filters": {k: self.has_filter(k) for k in fkeys},
            "hwaccels": sorted(self.hwaccels),
        }


def get_caps(refresh: bool = False) -> Caps:
    """Probe ffmpeg once and cache the result."""
    global _CAPS_CACHE
    with _LOCK:
        if _CAPS_CACHE is not None and not refresh:
            return _CAPS_CACHE
        encoders, filters = set(), set()
        ff = ffmpeg_path()
        if ff:
            try:
                out = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=15)
                for line in out.stdout.splitlines():
                    m = re.match(r"^\s+[A-Z.]{2,8}\s+(\S+)\s+", line)
                    if m and m.group(1) not in ("=", "") and not m.group(1).startswith("="):
                        encoders.add(m.group(1))
            except Exception:
                pass
            try:
                out = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=15)
                for line in out.stdout.splitlines():
                    m = re.match(r"^\s+[A-Z.]{2,8}\s+(\S+)\s+", line)
                    if m and m.group(1) not in ("=", "") and not m.group(1).startswith("="):
                        filters.add(m.group(1))
            except Exception:
                pass
            # Hardware acceleration detection
            hwaccels = set()
            try:
                out = subprocess.run([ff, "-hide_banner", "-hwaccels"], capture_output=True, text=True, timeout=10)
                for line in out.stdout.splitlines():
                    line = line.strip()
                    if line and not line.startswith("Hardware"):
                        hwaccels.add(line)
            except Exception:
                pass
        _CAPS_CACHE = Caps(encoders, filters, ff or "", hwaccels)
        return _CAPS_CACHE


# ---------------------------------------------------------------- report
def system_report() -> "tuple[list, bool]":
    """Build the `aureus doctor` report. Returns (rows, healthy)."""
    ff = ffmpeg_path()
    fp = ffprobe_path()
    ytd = ytdlp_path()
    ram = total_ram_gb()
    caps = get_caps()

    ram_txt = "OK (>= 8 GB requirement)" if ram >= MIN_RAM_GB else "BELOW the 8 GB minimum! Override with --force."
    rows = [
        ("AUREUS", f"v{__version__} — Video Enhancer / Upscaler / RAW Lossless"),
        ("Platform", f"{platform_name()} · Python {sys.version.split()[0]} · {os.cpu_count() or '?'} CPU cores"),
        ("RAM", f"{ram:.2f} GB — {ram_txt}"),
        ("ffmpeg", (f"OK — {binary_version(ff)}" if ff else "NOT FOUND — install: apt install ffmpeg | brew install ffmpeg | winget install Gyan.FFmpeg | pkg install ffmpeg (Termux)")),
        ("ffprobe", ("OK — " + fp) if fp else "NOT FOUND — ships with every ffmpeg package"),
        ("yt-dlp", (f"OK — {binary_version(ytd)}" if ytd else "NOT FOUND (URL download disabled) — install: pip install yt-dlp (or brew/winget)")),
    ]

    if ff:
        enc_bits, fil_bits = [], []
        for name in ("libx264", "libx265", "ffv1", "prores_ks", "dnxhd", "libaom-av1"):
            enc_bits.append(f"{'+' if caps.has_enc(name) else '-'}{name}")
        for name in ("zscale", "tonemap", "cas", "nlmeans", "minterpolate", "xbr", "deband", "deblock"):
            fil_bits.append(f"{'+' if caps.has_filter(name) else '-'}{name}")
        rows.append(("Encoders", "  ".join(enc_bits)))
        rows.append(("Filters", "  ".join(fil_bits)))
        if caps.hwaccels:
            rows.append(("HW Accel", "  ".join(sorted(caps.hwaccels))))
        if not caps.has_filter("zscale"):
            rows.append(("HDR note", "zscale unavailable — SDR→HDR expansion falls back to 10-bit + signaling only"))

    healthy = bool(ff and fp) and ram >= MIN_RAM_GB
    return rows, healthy
