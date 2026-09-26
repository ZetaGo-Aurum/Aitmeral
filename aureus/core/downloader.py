"""yt-dlp wrapper — URL/embed-link probing, best-quality download with progress."""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import threading
import time
from typing import Callable, Optional

from aureus.core.media import human_duration, human_size
from aureus.core.sysinfo import ytdlp_path

URL_RE = re.compile(r"^https?://", re.I)
YT_EMBED_RE = re.compile(r"(youtube\.com|youtube-nocookie\.com)/(?:embed|v|shorts|live)/([\w-]{6,})")


class DownloadError(RuntimeError):
    pass


def is_url(source: str) -> bool:
    return bool(URL_RE.match((source or "").strip()))


def normalize_url(url: str) -> str:
    """Turn YouTube embed/shorts/live links into canonical watch URLs (also works with yt-dlp directly)."""
    url = (url or "").strip()
    m = YT_EMBED_RE.search(url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(2)}"
    return url


def require_ytdlp() -> str:
    p = ytdlp_path()
    if not p:
        raise DownloadError(
            "yt-dlp is not installed. Install it with:  pip install yt-dlp  "
            "(or: brew install yt-dlp / winget install yt-dlp.yt-dlp / pkg install yt-dlp)"
        )
    return p


def _run(binpath: str, args: list, timeout: int = 120) -> "subprocess.CompletedProcess":
    try:
        return subprocess.run([binpath] + args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise DownloadError("yt-dlp timed out — check your network or try again.")


def probe_url(url: str) -> dict:
    """Fetch metadata for a URL. Returns dict; raises DownloadError on failure."""
    ytd = require_ytdlp()
    url = normalize_url(url)
    out = _run(ytd, ["-J", "--no-playlist", "--no-warnings", url], timeout=120)
    if out.returncode != 0 or not out.stdout.strip():
        err = (out.stderr or "").strip().splitlines()
        raise DownloadError(err[-1] if err else "yt-dlp could not fetch info for this URL.")
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise DownloadError("yt-dlp returned unreadable metadata.")

    if data.get("_type") == "playlist":
        entries = data.get("entries") or []
        if entries:
            data = entries[0]
    formats = data.get("formats") or []
    best_h = 0
    best_fmt = None
    for fmt in formats:
        h = fmt.get("height") or 0
        if fmt.get("vcodec", "none") != "none" and h and h > best_h:
            best_h, best_fmt = h, fmt
    total = 0
    try:
        total = int(data.get("filesize") or data.get("filesize_approx") or 0)
        if not total and best_fmt:
            total = int(best_fmt.get("filesize") or best_fmt.get("filesize_approx") or 0)
    except (TypeError, ValueError):
        total = 0
    return {
        "url": url,
        "title": data.get("title") or "video",
        "uploader": data.get("uploader") or data.get("channel") or "",
        "duration": float(data.get("duration") or 0),
        "duration_h": human_duration(data.get("duration") or 0),
        "thumbnail": data.get("thumbnail") or "",
        "ext": data.get("ext") or "mp4",
        "best_height": best_h,
        "size": total,
        "size_h": human_size(total) if total else "?",
        "webpage_url": data.get("webpage_url") or url,
        "is_live": bool(data.get("is_live")),
    }


def _format_selector(quality: str) -> str:
    q = (quality or "best").lower()
    if q in ("best", "max", ""):
        return "bestvideo*+bestaudio/best"
    digits = re.sub(r"\D", "", q)
    if digits:
        h = int(digits)
        return f"bestvideo*[height<={h}]+bestaudio/best[height<={h}]/best"
    return "bestvideo*+bestaudio/best"


def download(url: str, out_dir: str, base_name: str, quality: str = "best",
             on_progress: Optional[Callable[[float, str], None]] = None,
             cancel_event: Optional[threading.Event] = None,
             proc_hook: Optional[Callable[[subprocess.Popen], None]] = None) -> str:
    """Download a URL at the requested quality. Returns the local file path."""
    ytd = require_ytdlp()
    url = normalize_url(url)
    os.makedirs(out_dir, exist_ok=True)
    base = re.sub(r"[^\w.\- ]", "_", base_name)[:80].strip() or "aureus_source"
    out_tpl = os.path.join(out_dir, base + ".%(ext)s")

    cmd = [
        ytd,
        "--no-playlist", "--no-warnings", "--newline", "--no-colors",
        "--restrict-filenames",
        "-f", _format_selector(quality),
        "--merge-output-format", "mkv",
        "--no-simulate", "--print", "after_move:filepath",
        "-o", out_tpl,
        url,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    if proc_hook:
        proc_hook(proc)

    pct_re = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")
    final_path = ""

    def pump():
        nonlocal final_path
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                m = pct_re.search(line)
                if m and on_progress:
                    on_progress(float(m.group(1)) / 100.0, line[:110])
                elif line.startswith("[") and on_progress:
                    on_progress(-1.0, line[:110])
                elif os.path.isabs(line) and os.path.exists(line):
                    final_path = line
        except Exception:
            pass

    t = threading.Thread(target=pump, daemon=True)
    t.start()
    try:
        while proc.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise DownloadError("__CANCELLED__")
            time.sleep(0.15)
    finally:
        t.join(timeout=3)

    err = (proc.stderr.read() or "").strip().splitlines()
    if proc.returncode != 0:
        raise DownloadError(err[-1] if err else f"yt-dlp exited with code {proc.returncode}")
    if final_path and os.path.isfile(final_path):
        return final_path
    hits = sorted(glob.glob(os.path.join(out_dir, base + ".*")))
    media = [p for p in hits if os.path.splitext(p)[1] in (".mkv", ".mp4", ".webm", ".mov", ".avi", ".ts")]
    if not media:
        raise DownloadError("Download finished but the output file could not be located.")
    return media[0]
