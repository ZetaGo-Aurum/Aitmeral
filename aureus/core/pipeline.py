"""Conversion pipeline — shared by CLI, TUI queue and the web server."""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from aureus import MIN_RAM_GB
from aureus.core import downloader, encoder, media
from aureus.core.media import MediaInfo, human_size
from aureus.core.options import Settings
from aureus.core.presets import get_preset
from aureus.core.sysinfo import total_ram_gb

ReportFn = Callable[[str, float, str], None]  # (stage, fraction 0..1 or -1, detail)


class RequirementError(RuntimeError):
    pass


class CancelledError(RuntimeError):
    pass


@dataclass
class JobResult:
    input_path: str = ""
    output_path: str = ""
    source_info: Optional[MediaInfo] = None
    output_info: Optional[MediaInfo] = None
    command: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    elapsed: float = 0.0

    def summary(self) -> dict:
        oi = self.output_info
        return {
            "output_path": self.output_path,
            "output_name": os.path.basename(self.output_path) if self.output_path else "",
            "output_size": oi.size if oi else 0,
            "output_size_h": human_size(oi.size) if oi else "?",
            "output_res": oi.res if oi else "?",
            "output_vcodec": oi.vcodec if oi else "",
            "output_duration": oi.duration if oi else 0,
        }


def sanitize_stem(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = re.sub(r"[^\w.\- ]+", "_", stem).strip() or "video"
    return stem[:70]


def output_filename(src_path: str, s: Settings, fres, preset_key: str) -> str:
    preset = get_preset(preset_key)
    parts = [sanitize_stem(src_path), "aureus"]
    if fres.target_wh:
        parts.append(f"{fres.target_wh[1]}p")
    if fres.hdr_expand:
        parts.append("hdr")
    parts.append(preset.key)
    name = "_".join(p.rstrip("_") for p in parts if p)
    return f"{name}.{preset.ext}"


def unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    for i in range(1, 500):
        cand = f"{stem} ({i}){ext}"
        if not os.path.exists(cand):
            return cand
    return path


def run_job(kind: str,
            source: str,
            settings: Settings,
            output_dir: str,
            report: Optional[ReportFn] = None,
            cancel_event: Optional[threading.Event] = None,
            proc_hook: Optional[Callable] = None,
            dry_run: bool = False) -> JobResult:
    """kind: 'url' | 'file'. Raises RequirementError / CancelledError / EncodingError / DownloadError."""

    def rep(stage: str, frac: float, detail: str = ""):
        if report:
            report(stage, frac, detail)

    # ---- system requirement gate (8 GB) ----------------------------------
    ram = total_ram_gb()
    if ram < MIN_RAM_GB and not settings.force:
        raise RequirementError(
            f"This device has {ram:.2f} GB RAM. AUREUS requires at least {MIN_RAM_GB:.0f} GB "
            "for stable conversion. Re-run with --force (CLI) or enable 'Proceed anyway' to override."
        )
    if ram < MIN_RAM_GB:
        rep("prepare", 0.0, f"Low-RAM override active ({ram:.2f} GB < {MIN_RAM_GB:.0f} GB) — quality/parity is preserved, speed may suffer.")

    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()
    result = JobResult()

    # ---- acquire source ---------------------------------------------------
    src_path = source
    if kind == "url":
        rep("download", 0.0, "Fetching video info…")
        info_url = downloader.probe_url(source)
        rep("download", 0.02, f"Downloading: {info_url['title']}")
        src_path = downloader.download(
            source, output_dir, sanitize_stem(info_url["title"]),
            quality=settings.quality,
            on_progress=lambda f, d: rep("download", max(0.0, f), d),
            cancel_event=cancel_event, proc_hook=proc_hook,
        )
        rep("download", 1.0, f"Downloaded → {os.path.basename(src_path)}")
    else:
        src_path = os.path.abspath(os.path.expanduser(source))
        if not os.path.isfile(src_path):
            raise RequirementError(f"File not found: {src_path}")

    result.input_path = src_path

    # ---- probe -------------------------------------------------------------
    rep("probe", 0.0, "Analyzing source…")
    info = media.probe(src_path)
    if not info.ok and not dry_run:
        raise RequirementError(f"Could not analyze input: {info.error}")
    result.source_info = info

    # ---- build -------------------------------------------------------------
    cmd, fres, notes = encoder.build_command(src_path, "UNUSED_PLACEHOLDER", settings, info if info.ok else None)
    out_name = output_filename(src_path, settings, fres, settings.preset)
    out_path = unique_path(os.path.join(output_dir, out_name))
    cmd[cmd.index("UNUSED_PLACEHOLDER")] = out_path
    result.command = cmd
    result.notes = notes
    rep("prepare", 1.0, f"Output → {os.path.basename(out_path)}")

    if dry_run:
        result.output_path = out_path
        return result

    # ---- encode ------------------------------------------------------------
    duration = info.duration if info.ok else 0.0
    rep("process", 0.0, "Enhancing & encoding…" + (f" ({fres.scale_desc})" if fres.scale_desc != "source resolution" else ""))
    rc, log = encoder.run_ffmpeg(
        cmd, duration=duration,
        on_progress=lambda f, sp, d: rep("process", f, (f"{sp:.2f}x speed · " if sp else "") + "encoding"),
        cancel_event=cancel_event, proc_hook=proc_hook,
    )
    if rc == -2:
        # remove partial output
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except OSError:
            pass
        raise CancelledError("Cancelled by user")
    if rc != 0:
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except OSError:
            pass
        tail = "\n".join(log[-8:]) or "(no ffmpeg output)"
        raise encoder.EncodingError(f"ffmpeg failed (exit {rc}):\n{tail}")

    # ---- verify ------------------------------------------------------------
    rep("finalize", 0.5, "Verifying output…")
    out_info = media.probe(out_path)
    result.output_path = out_path
    result.output_info = out_info
    if not out_info.ok or not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
        raise encoder.EncodingError("Output verification failed — the file is missing or unreadable.")

    # ---- cleanup downloaded source ------------------------------------------
    if kind == "url" and not settings.keep_source:
        try:
            os.remove(src_path)
        except OSError:
            pass

    result.elapsed = time.time() - t0
    rep("done", 1.0, f"Done in {int(result.elapsed)}s → {os.path.basename(out_path)}")
    return result
