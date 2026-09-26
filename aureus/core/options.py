"""Shared enhancement settings — one contract used by CLI, TUI, Web and the job engine."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields

SCALERS = ["lanczos", "spline", "bicubic", "gauss", "neighbor", "xbr2", "xbr4"]
SHADERS = ["cas", "unsharp", "none"]
DENOISERS = ["hqdn3d", "nlmeans"]
AUDIO_MODES = ["auto", "copy", "flac", "pcm", "aac"]
CHROMA_MODES = ["auto", "420", "422", "444", "rgb"]
DEPTH_MODES = ["auto", "8", "10", "12"]
FPS_MODES = ["source", "24", "25", "30", "48", "50", "60"]
TONE_MAP_MODES = ["auto", "hdr2sdr", "off"]
QUALITY_MODES = ["best", "2160", "1440", "1080", "720", "480"]
SCALE_MODES = ["source", "2x", "4x", "480p", "720p", "1080p", "1440p", "2160p"]
HWACCEL_MODES = ["auto", "off", "cuda", "nvenc", "nvidia", "qsv", "intel", "quicksync", "vaapi", "amf", "amd", "videotoolbox", "vt", "apple", "macos"]


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _to_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return default


def _to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """All user-tunable enhancement settings (serializable to/from a plain dict)."""

    preset: str = "superhd"
    scale: str = "source"        # source | 2x | 4x | 480p | 720p | 1080p | 1440p | 2160p | WxH
    scaler: str = "lanczos"
    denoise: int = 0             # 0=off, 1=light, 2=medium, 3=strong
    denoiser: str = "hqdn3d"     # hqdn3d | nlmeans
    sharpen: float = 0.35        # 0.0..1.0 — CAS / unsharp strength
    shader: str = "cas"          # cas | unsharp | none
    deband: bool = False
    deblock: bool = False
    deinterlace: bool = False
    grain: int = 0               # 0..12 film grain
    saturation: float = 1.0      # 0.5..2.0
    contrast: float = 1.0        # 0.5..2.0
    gamma: float = 1.0           # 0.5..2.0
    brightness: float = 0.0      # -0.3..0.3
    hdr: bool = False            # SDR -> HDR expansion (10-bit + PQ/BT.2020 signaling)
    tone_map: str = "auto"       # auto | hdr2sdr | off  (HDR source handling)
    fps: str = "source"
    motion_interp: bool = False  # motion-compensated interpolation (slow)
    audio: str = "auto"          # auto | copy | flac | pcm | aac
    chroma: str = "auto"         # auto | 420 | 422 | 444 | rgb
    depth: str = "auto"          # auto | 8 | 10 | 12
    quality: str = "best"        # download quality for URLs
    crf: int = 0                 # 0 = use preset default; 14..28 for lossy presets
    threads: int = 0             # 0 = auto (use all cores)
    hwaccel: str = "auto"        # auto | off | cuda | qsv | vaapi | amf | videotoolbox
    keep_source: bool = True     # keep the downloaded source file
    force: bool = False          # bypass the 8 GB RAM requirement
    extra_args: str = ""         # raw extra ffmpeg args (advanced)

    # ------------------------------------------------------------------ io
    @staticmethod
    def from_dict(data: dict) -> "Settings":
        """Tolerant parser: unknown keys ignored, values clamped to sane ranges."""
        data = data or {}
        s = Settings()
        known = {f.name for f in fields(Settings)}
        for key, value in data.items():
            if key not in known:
                continue
            setattr(s, key, value)

        s.preset = str(s.preset).strip().lower() or "superhd"
        s.scale = str(s.scale or "source").strip().lower()
        s.scaler = str(s.scaler).strip().lower() if str(s.scaler).strip().lower() in SCALERS else "lanczos"
        s.denoise = _clamp(_to_int(s.denoise, 0), 0, 3)
        s.denoiser = str(s.denoiser).strip().lower() if str(s.denoiser).strip().lower() in DENOISERS else "hqdn3d"
        s.sharpen = round(_clamp(_to_float(s.sharpen, 0.35), 0.0, 1.0), 3)
        s.shader = str(s.shader).strip().lower() if str(s.shader).strip().lower() in SHADERS else "cas"
        s.deband = _to_bool(s.deband)
        s.deblock = _to_bool(s.deblock)
        s.deinterlace = _to_bool(s.deinterlace)
        s.grain = _clamp(_to_int(s.grain, 0), 0, 12)
        s.saturation = round(_clamp(_to_float(s.saturation, 1.0), 0.0, 3.0), 3)
        s.contrast = round(_clamp(_to_float(s.contrast, 1.0), 0.0, 3.0), 3)
        s.gamma = round(_clamp(_to_float(s.gamma, 1.0), 0.1, 3.0), 3)
        s.brightness = round(_clamp(_to_float(s.brightness, 0.0), -0.5, 0.5), 3)
        s.hdr = _to_bool(s.hdr)
        s.tone_map = str(s.tone_map).strip().lower() if str(s.tone_map).strip().lower() in TONE_MAP_MODES else "auto"
        s.fps = str(s.fps).strip().lower() if str(s.fps).strip().lower() in FPS_MODES else "source"
        s.motion_interp = _to_bool(s.motion_interp)
        s.audio = str(s.audio).strip().lower() if str(s.audio).strip().lower() in AUDIO_MODES else "auto"
        s.chroma = str(s.chroma).strip().lower() if str(s.chroma).strip().lower() in CHROMA_MODES else "auto"
        s.depth = str(s.depth).strip().lower() if str(s.depth).strip().lower() in DEPTH_MODES else "auto"
        s.quality = str(s.quality).strip().lower() if str(s.quality).strip().lower() in QUALITY_MODES else "best"
        s.crf = _clamp(_to_int(s.crf, 0), 0, 51)
        s.threads = _clamp(_to_int(s.threads, 0), 0, 64)
        s.hwaccel = str(s.hwaccel).strip().lower() if str(s.hwaccel).strip().lower() in HWACCEL_MODES else "auto"
        s.keep_source = _to_bool(s.keep_source, True)
        s.force = _to_bool(s.force)
        s.extra_args = str(s.extra_args or "").strip()
        return s

    def to_dict(self) -> dict:
        return asdict(self)

    # ------------------------------------------------------------- helpers
    def parse_scale(self):
        """Return ('source', None) | ('exact', (w, h)) | ('height', h) | ('factor', n)."""
        spec = (self.scale or "source").strip().lower()
        if spec in ("", "source", "keep", "none", "off"):
            return "source", None
        if spec in ("2x", "2X".lower(), "x2"):
            return "factor", 2
        if spec in ("4x", "x4"):
            return "factor", 4
        m = re.match(r"^(\d{3,5})x(\d{3,5})$", spec)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            if 64 <= w <= 7680 and 64 <= h <= 4320:
                return "exact", (w, h)
        digits = re.sub(r"\D", "", spec)
        if digits.isdigit():
            h = int(digits)
            if h in (240, 360, 480, 576, 720, 1080, 1440, 2160):
                return "height", h
            if 120 <= h <= 4320:
                return "height", h
        return "source", None

    def target_fps(self):
        if self.fps in ("source", "", None):
            return None
        try:
            return int(float(self.fps))
        except (TypeError, ValueError):
            return None

    def describe(self) -> str:
        bits = [f"preset={self.preset}"]
        if self.scale and self.scale != "source":
            bits.append(f"scale={self.scale}")
        if self.denoise:
            bits.append(f"denoise={self.denoise}({self.denoiser})")
        if self.shader != "none" and self.sharpen > 0:
            bits.append(f"{self.shader}={self.sharpen}")
        for flag in ("deband", "deblock", "deinterlace", "hdr", "motion_interp"):
            if getattr(self, flag):
                bits.append(flag)
        if self.grain:
            bits.append(f"grain={self.grain}")
        if any(abs(v - 1.0) > 0.001 for v in (self.saturation, self.contrast, self.gamma)) or abs(self.brightness) > 0.001:
            bits.append("color")
        return " ".join(bits)
