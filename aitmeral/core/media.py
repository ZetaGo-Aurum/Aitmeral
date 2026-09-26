"""ffprobe wrapper — MediaInfo about local files."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from aitmeral.core.sysinfo import ffprobe_path

VIDEO_EXTS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m2ts", ".mts",
    ".m4v", ".mpg", ".mpeg", ".wmv", ".3gp", ".vob", ".ogv", ".mxf", ".m2v", ".y4m",
}
IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".avif", ".jxl", ".gif",
}
ALL_MEDIA_EXTS = VIDEO_EXTS | IMAGE_EXTS
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}


def is_image_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def is_media_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in ALL_MEDIA_EXTS


def human_size(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:,.1f} TB"


def human_duration(sec) -> str:
    try:
        sec = float(sec)
    except (TypeError, ValueError):
        return "?"
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@dataclass
class MediaInfo:
    path: str
    ok: bool = False
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    vcodec: str = ""
    acodec: str = ""
    pix_fmt: str = ""
    color_transfer: str = ""
    color_primaries: str = ""
    hdr: bool = False
    bitrate: int = 0
    size: int = 0
    has_audio: bool = False
    has_subs: bool = False
    container: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def res(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "?"


def probe(path: str) -> MediaInfo:
    """Run ffprobe on a local file. Never raises — returns .ok=False on failure."""
    info = MediaInfo(path=path)
    fp = ffprobe_path()
    if not fp:
        info.error = "ffprobe not found. Install ffmpeg (apt/brew/winget/pkg install ffmpeg)."
        return info
    if not os.path.isfile(path):
        info.error = f"File not found: {path}"
        return info
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0 or not out.stdout.strip():
            info.error = (out.stderr or "ffprobe failed").strip().splitlines()[-1] if (out.stderr or "").strip() else "ffprobe failed"
            return info
        data = json.loads(out.stdout)
    except subprocess.TimeoutExpired:
        info.error = "ffprobe timed out"
        return info
    except Exception as exc:
        info.error = f"ffprobe error: {exc}"
        return info

    info.raw = data
    info.ok = True
    fmt = data.get("format", {})
    info.container = fmt.get("format_name", "")
    try:
        info.duration = float(fmt.get("duration") or 0)
    except (TypeError, ValueError):
        info.duration = 0.0
    try:
        info.size = int(fmt.get("size") or os.path.getsize(path))
    except (TypeError, ValueError, OSError):
        info.size = 0
    try:
        info.bitrate = int(fmt.get("bit_rate") or 0)
    except (TypeError, ValueError):
        info.bitrate = 0

    for st in data.get("streams", []):
        ctype = st.get("codec_type")
        if ctype == "video" and not info.vcodec:
            info.vcodec = st.get("codec_name", "")
            info.width = int(st.get("width") or 0)
            info.height = int(st.get("height") or 0)
            info.pix_fmt = st.get("pix_fmt", "")
            info.color_transfer = st.get("color_transfer", "")
            info.color_primaries = st.get("color_primaries", "")
            rate = st.get("avg_frame_rate") or st.get("r_frame_rate") or "0/1"
            try:
                num, den = rate.split("/")
                if float(den) > 0:
                    info.fps = round(float(num) / float(den), 3)
            except (ValueError, ZeroDivisionError):
                pass
            hdr = info.color_transfer in HDR_TRANSFERS
            for side in st.get("side_data_list", []) or []:
                if "MasteringDisplayMetadata" in str(side.get("side_data_type", "")) or "ContentLightLevel" in str(side.get("side_data_type", "")):
                    hdr = True
            info.hdr = hdr
        elif ctype == "audio" and not info.acodec:
            info.acodec = st.get("codec_name", "")
            info.has_audio = True
        elif ctype == "subtitle":
            info.has_subs = True
    return info


def probe_url_safe(path: str) -> Optional[dict]:
    """Probe and return a plain dict for JSON APIs; None on failure."""
    i = probe(path)
    if not i.ok:
        return None
    return {
        "path": i.path, "duration": i.duration, "duration_h": human_duration(i.duration),
        "width": i.width, "height": i.height, "res": i.res, "fps": i.fps,
        "vcodec": i.vcodec, "acodec": i.acodec, "pix_fmt": i.pix_fmt,
        "hdr": i.hdr, "color_transfer": i.color_transfer,
        "size": i.size, "size_h": human_size(i.size), "bitrate": i.bitrate,
        "has_audio": i.has_audio, "has_subs": i.has_subs, "container": i.container,
    }
