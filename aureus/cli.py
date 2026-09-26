"""AUREUS command line interface.

    aureus                 → launch the interactive TUI
    aureus convert FILE    → enhance/upscale a local file
    aureus url  LINK       → download (YouTube embed/watch, 1000+ sites) + enhance
    aureus server          → start the local web UI
    aureus doctor          → system & dependency check
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

from aureus import __version__
from aureus.core import media, pipeline, sysinfo
from aureus.core.options import (
    AUDIO_MODES, CHROMA_MODES, DEPTH_MODES, FPS_MODES, SCALERS, SHADERS,
    TONE_MAP_MODES, Settings, HWACCEL_MODES,
)
from aureus.core.presets import get_preset, preset_summaries

# ------------------------------------------------------------------ banner
BANNER = r"""
[c #f6d38b]     _    _ _____ __  __ _____ ____      _    _
[c #eec271]    / \  | |_   _|  \/  | ____|  _ \    / \  | |
[c #dca94f]   / _ \ | | | | | |\/| |  _| | |_) |  / _ \ | |
[c #c69137]  / ___ \| | | | | |  | | |___|  _ <  / ___ \| |___
[c #a87625] /_/   \_\_| | |_|_|  |_|_____|_| \_\/_/   \_\_____|
[c #8f6a1f dim]        Video Enhancer · Upscaler · RAW Lossless[/]
"""

_EFFECT_KEYS = {
    "denoise", "sharpen", "deband", "deblock", "deinterlace", "grain",
    "hdr", "tone-map", "color-boost", "all",
}


def _parse_effects(spec: str, s: Settings):
    """Parse a comma separated effect list like: denoise:2,sharpen:0.5,deband,hdr"""
    if not spec:
        return
    for item in spec.split(","):
        item = item.strip().lower()
        if not item:
            continue
        name, _, arg = item.partition(":")
        if name == "all":
            s.denoise = max(s.denoise, 2)
            s.shader, s.sharpen = "cas", max(s.sharpen, 0.4)
            s.deband = True
            s.deblock = True
            s.saturation = max(s.saturation, 1.12)
            continue
        if name not in _EFFECT_KEYS:
            raise ValueError(f"Unknown effect '{name}'. Valid: {', '.join(sorted(_EFFECT_KEYS))}")
        if name == "denoise":
            s.denoise = int(arg) if arg.isdigit() and 1 <= int(arg) <= 3 else max(s.denoise, 2)
        elif name == "sharpen":
            try:
                s.sharpen = max(0.05, min(1.0, float(arg))) if arg else max(s.sharpen, 0.5)
            except ValueError:
                s.sharpen = 0.5
            if s.shader == "none":
                s.shader = "cas"
        elif name == "grain":
            s.grain = int(arg) if arg.isdigit() and 1 <= int(arg) <= 12 else 5
        elif name == "deband":
            s.deband = True
        elif name == "deblock":
            s.deblock = True
        elif name == "deinterlace":
            s.deinterlace = True
        elif name == "hdr":
            s.hdr = True
        elif name == "tone-map":
            s.tone_map = "hdr2sdr"
        elif name == "color-boost":
            s.saturation = 1.15
            s.contrast = 1.06


def add_common(p: argparse.ArgumentParser):
    p.add_argument("-p", "--preset", default="superhd", metavar="KEY",
                   help="output preset (default: superhd). See `aureus presets`.")
    p.add_argument("-S", "--scale", default="source",
                   help="target resolution: source | 2x | 4x | 480p | 720p | 1080p | 1440p | 2160p | WxH (default: source)")
    p.add_argument("--scaler", default="lanczos", choices=SCALERS, help="scaling algorithm (default: lanczos)")
    p.add_argument("--effects", default="", metavar="LIST",
                   help="comma list: denoise[:1-3], sharpen[:0-1], grain[:1-12], deband, deblock, deinterlace, hdr, tone-map, color-boost, all")
    p.add_argument("--shader", default="cas", choices=SHADERS, help="sharpen shader (default: cas)")
    p.add_argument("--denoise", type=int, default=0, choices=[0, 1, 2, 3], help="denoise level 0-3 (default: 0)")
    p.add_argument("--denoiser", default="hqdn3d", choices=["hqdn3d", "nlmeans"], help="denoiser (default: hqdn3d)")
    p.add_argument("--sharpen", type=float, default=0.0, help="sharpen strength 0.0-1.0 (default 0.35 when shader on)")
    p.add_argument("--saturation", type=float, default=1.0, help="color saturation (default: 1.0)")
    p.add_argument("--contrast", type=float, default=1.0, help="contrast (default: 1.0)")
    p.add_argument("--gamma", type=float, default=1.0, help="gamma (default: 1.0)")
    p.add_argument("--brightness", type=float, default=0.0, help="brightness -0.3..0.3 (default: 0)")
    p.add_argument("--deband", action="store_true", help="remove color banding")
    p.add_argument("--deblock", action="store_true", help="remove blocking artifacts")
    p.add_argument("--deinterlace", action="store_true", help="deinterlace interlaced sources")
    p.add_argument("--grain", type=int, default=0, help="add film grain 0-12 (default: 0)")
    p.add_argument("--hdr", action="store_true", help="SDR→HDR expansion (10-bit BT.2020 PQ; best with hdr10 preset)")
    p.add_argument("--tone-map", default="auto", choices=TONE_MAP_MODES, help="HDR source handling (default: auto)")
    p.add_argument("--fps", default="source", choices=FPS_MODES, help="output frame rate (default: source)")
    p.add_argument("--motion-interp", action="store_true", help="motion-compensated interpolation (slow!)")
    p.add_argument("--audio", default="auto", choices=AUDIO_MODES, help="audio mode (default: auto)")
    p.add_argument("--chroma", default="auto", choices=CHROMA_MODES, help="chroma: auto|420|422|444|rgb (default: auto)")
    p.add_argument("--depth", default="auto", choices=DEPTH_MODES, help="bit depth: auto|8|10|12 (default: auto)")
    p.add_argument("--crf", type=int, default=0, help="override CRF for lossy presets (e.g. 14-22)")
    p.add_argument("--threads", type=int, default=0, help="ffmpeg threads (default: auto)")
    p.add_argument("--hwaccel", default="auto", choices=HWACCEL_MODES, help="hardware acceleration: auto|off|cuda|qsv|vaapi|amf|videotoolbox (default: auto)")
    p.add_argument("--extra-args", default="", help="extra raw ffmpeg args, quoted (advanced)")
    p.add_argument("--force", action="store_true", help="proceed even below the 8 GB RAM requirement")
    p.add_argument("--dry-run", action="store_true", help="print the ffmpeg command without running")


def settings_from_args(args) -> Settings:
    s = Settings()
    s.preset = args.preset
    s.scale = args.scale
    s.scaler = args.scaler
    s.shader = args.shader
    s.denoise = args.denoise
    s.denoiser = args.denoiser
    s.sharpen = args.sharpen if args.sharpen else (0.35 if args.shader != "none" else 0.0)
    s.saturation, s.contrast, s.gamma, s.brightness = args.saturation, args.contrast, args.gamma, args.brightness
    s.deband, s.deblock, s.deinterlace = args.deband, args.deblock, args.deinterlace
    s.grain = args.grain
    s.hdr, s.tone_map = args.hdr, args.tone_map
    s.fps, s.motion_interp = args.fps, args.motion_interp
    s.audio, s.chroma, s.depth = args.audio, args.chroma, args.depth
    s.crf, s.threads = args.crf, args.threads
    s.hwaccel = args.hwaccel
    s.force = args.force
    s.extra_args = args.extra_args
    _parse_effects(args.effects, s)
    return s


# ------------------------------------------------------------------ commands
def cmd_convert(args) -> int:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (BarColumn, Progress, SpinnerColumn,
                               TaskProgressColumn, TextColumn, TimeElapsedColumn)
    from rich.table import Table

    console = Console()
    src = os.path.expanduser(args.input)
    if not os.path.isfile(src):
        console.print(f"[bold red]File not found:[/bold red] {src}")
        return 1
    try:
        settings = settings_from_args(args)
        get_preset(settings.preset)
    except ValueError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        return 1

    info = media.probe(src)
    if info.ok:
        t = Table(title="📥 Input", title_style="bold #f6d38b", show_header=False, border_style="#5a4a20")
        for k, v in [
            ("File", os.path.basename(src)),
            ("Resolution", f"{info.res} @ {info.fps:.2f} fps"),
            ("Video", f"{info.vcodec} / {info.pix_fmt}" + (" [HDR]" if info.hdr else "")),
            ("Audio", info.acodec or "none"),
            ("Duration", media.human_duration(info.duration)),
            ("Size", media.human_size(info.size)),
        ]:
            t.add_row(k, v)
        console.print(t)
    else:
        console.print(f"[yellow]Could not probe input ({info.error}) — continuing anyway.[/yellow]")

    try:
        if args.dry_run:
            result = pipeline.run_job("file", src, settings, args.output or ".", report=None, dry_run=True)
            console.print(Panel.fit(
                "[bold #f6d38b]DRY RUN — ffmpeg command:[/bold #f6d38b]\n\n"
                f"[white]{encoder_pretty(result.command)}[/white]",
                border_style="#b98a2f"))
            if result.notes:
                for n in result.notes:
                    console.print(f"  [dim]• {n}[/dim]")
            return 0

        cancel = threading.Event()
        with Progress(
            SpinnerColumn(style="#f6d38b"), TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40, style="#3a3220", complete_style="#f6d38b", finished_style="#8fd18f"),
            TaskProgressColumn(), TimeElapsedColumn(), console=console, transient=True,
        ) as progress:
            task = progress.add_task("[gold1]Enhancing…", total=100)
            state = {"last": ""}

            def report(stage, frac, detail):
                if stage == "done":
                    progress.update(task, completed=100)
                    return
                label = {"download": "⬇ Downloading", "probe": "🔎 Analyzing", "process": "⚡ Enhancing & Encoding",
                         "finalize": "📦 Finalizing", "prepare": "⚙ Preparing"}.get(stage, stage)
                if frac >= 0:
                    progress.update(task, completed=frac * 100, description=f"[gold1]{label}")
                if detail:
                    state["last"] = detail
                progress.update(task, description=f"[gold1]{label}[/gold1] [dim]{state['last'][:60]}[/dim]")

            try:
                result = pipeline.run_job("file", src, settings,
                                          args.output or os.path.dirname(os.path.abspath(src)) or ".",
                                          report=report, cancel_event=cancel)
            except KeyboardInterrupt:
                cancel.set()
                console.print("[yellow]Cancelling…[/yellow]")
                return 130
    except pipeline.RequirementError as exc:
        console.print(Panel.fit(f"[bold red]REQUIREMENT[/bold red]\n{exc}", border_style="red"))
        return 2
    except Exception as exc:  # noqa: BLE001
        console.print(Panel.fit(f"[bold red]FAILED[/bold red]\n{str(exc)[:800]}", border_style="red"))
        return 1

    oi = result.output_info
    t = Table(title="✅ OUTPUT", title_style="bold #8fd18f", show_header=False, border_style="#2f5a3a")
    for k, v in [
        ("File", os.path.basename(result.output_path)),
        ("Path", result.output_path),
        ("Resolution", oi.res if oi else "?"),
        ("Video", (oi.vcodec if oi else "") + (f" / {oi.pix_fmt}" if oi else "")),
        ("Duration", media.human_duration(oi.duration if oi else 0)),
        ("Size", media.human_size(oi.size if oi else 0)),
        ("Elapsed", f"{result.elapsed:.1f}s"),
    ]:
        t.add_row(k, v)
    console.print(t)
    for n in result.notes:
        console.print(f"  [dim]• {n}[/dim]")
    return 0


def encoder_pretty(cmd):
    from aureus.core.encoder import pretty_cmd
    return pretty_cmd(cmd)


def cmd_url(args) -> int:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    from aureus.core import downloader
    try:
        settings = settings_from_args(args)
        settings.quality = args.quality
        get_preset(settings.preset)
    except ValueError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        return 1
    try:
        console.print("[gold1]🔎 Fetching video info…[/gold1]")
        dinfo = downloader.probe_url(args.url)
    except Exception as exc:  # noqa: BLE001
        console.print(Panel.fit(f"[bold red]URL ERROR[/bold red]\n{exc}", border_style="red"))
        return 1
    console.print(f"[bold #f6d38b]🎬 {dinfo['title']}[/bold #f6d38b]  "
                  f"[dim]{dinfo['duration_h']} · {dinfo['size_h']} · best {dinfo['best_height'] or '?'}p[/dim]")

    if args.dry_run:
        console.print(Panel.fit("[yellow]Dry-run for URLs only validates the link & settings "
                                "(the ffmpeg command depends on the downloaded file).[/yellow]"))
        return 0

    cancel = threading.Event()
    state = {"frac": 0.0, "detail": ""}

    def report(stage, frac, detail):
        if stage == "download":
            state["frac"], state["detail"] = frac * 35.0, detail
        elif stage == "process" and frac >= 0:
            state["frac"], state["detail"] = 35.0 + frac * 65.0, detail
        pct = state["frac"]
        bar = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
        console.print(f"\r[gold1]⚡[/gold1] [{bar}] {pct:5.1f}%  [dim]{state['detail'][:70]}[/dim]", end="")
    try:
        result = pipeline.run_job("url", args.url, settings, args.output or ".", report=report, cancel_event=cancel)
        console.print()
    except KeyboardInterrupt:
        cancel.set()
        console.print("\n[yellow]Cancelling…[/yellow]")
        return 130
    except pipeline.RequirementError as exc:
        console.print(Panel.fit(f"[bold red]REQUIREMENT[/bold red]\n{exc}", border_style="red"))
        return 2
    except Exception as exc:  # noqa: BLE001
        console.print()
        console.print(Panel.fit(f"[bold red]FAILED[/bold red]\n{str(exc)[:800]}", border_style="red"))
        return 1

    oi = result.output_info
    console.print(f"\n[bold #8fd18f]✅ Done in {result.elapsed:.1f}s[/bold #8fd18f]")
    console.print(f"   [white]{result.output_path}[/white]")
    if oi:
        console.print(f"   [dim]{oi.res} · {oi.vcodec} · {media.human_size(oi.size)}[/dim]")
    return 0


def cmd_server(args) -> int:
    from aureus.web.server import run_server
    return run_server(host=args.host, port=args.port,
                      output_dir=os.path.abspath(os.path.expanduser(args.output_dir)),
                      allow_low_ram=args.allow_low_ram, open_browser=not args.no_open)


def cmd_info(args) -> int:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    src = args.source
    if sysinfo.platform_key() == "windows":
        src = src.replace("\\", "/")
    from aureus.core.downloader import is_url
    if is_url(src):
        from aureus.core import downloader
        try:
            d = downloader.probe_url(src)
            t = Table(title="🌐 URL", title_style="bold #f6d38b", show_header=False, border_style="#5a4a20")
            for k, v in [("Title", d["title"]), ("Uploader", d["uploader"]), ("Duration", d["duration_h"]),
                         ("Best", f"{d['best_height'] or '?'}p"), ("Size ≈", d["size_h"]), ("URL", d["url"])]:
                t.add_row(k, v)
            console.print(t)
            return 0
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]URL error:[/bold red] {exc}")
            return 1
    info = media.probe(os.path.expanduser(src))
    if not info.ok:
        console.print(f"[bold red]Cannot probe:[/bold red] {info.error}")
        return 1
    t = Table(title="🎞 Media", title_style="bold #f6d38b", show_header=False, border_style="#5a4a20")
    for k, v in [
        ("File", os.path.basename(info.path)), ("Path", info.path),
        ("Resolution", f"{info.res} @ {info.fps:.3f} fps"),
        ("Video", info.vcodec or "?"), ("Pixel format", info.pix_fmt or "?"),
        ("HDR", ("YES (" + info.color_transfer + ")") if info.hdr else "no"),
        ("Audio", (info.acodec or "none") + (" · subtitles" if info.has_subs else "")),
        ("Duration", media.human_duration(info.duration)),
        ("Size", media.human_size(info.size)),
        ("Bitrate", f"{info.bitrate/1000:,.0f} kb/s" if info.bitrate else "?"),
        ("Container", info.container),
    ]:
        t.add_row(k, v)
    console.print(t)
    return 0


def cmd_doctor(args) -> int:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    sysinfo.get_caps(refresh=True)
    rows, healthy = sysinfo.system_report()
    t = Table(title="🩺 AUREUS System Check", title_style="bold #f6d38b", show_header=False, border_style="#5a4a20")
    for k, v in rows:
        style = "bold red" if ("NOT FOUND" in v or "BELOW" in v) else "white"
        t.add_row(f"[bold #f6d38b]{k}[/bold #f6d38b]", f"[{style}]{v}[/{style}]")
    console.print(t)
    console.print()
    if healthy:
        console.print(Panel.fit("[bold #8fd18f]✔ All requirements satisfied — AUREUS is ready.[/bold #8fd18f]", border_style="#2f5a3a"))
        return 0
    console.print(Panel.fit(
        "[bold yellow]⚠ Some requirements are missing. AUREUS needs ffmpeg + ffprobe to convert, "
        "yt-dlp for URL downloads, and ≥ 8 GB RAM (override with --force).[/bold yellow]",
        border_style="#8f6a1f"))
    return 2


def cmd_presets(args) -> int:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    t = Table(title="✨ Output Presets", title_style="bold #f6d38b", border_style="#5a4a20")
    t.add_column("Key", style="bold #f6d38b")
    t.add_column("Preset")
    t.add_column("Badge")
    t.add_column("Compat", justify="center")
    t.add_column("Size (per min @1080p)")
    for p in preset_summaries():
        badge_color = {"RAW": "bold red", "LOSSLESS": "bold #f6d38b", "HDR": "bold #7ec8ff", "HQ": "bold #c9a0ff", "COMPAT": "bold #8fd18f"}.get(p["badge"], "white")
        stars = "★" * p["compat"] + "☆" * (5 - p["compat"])
        t.add_row(p["key"], p["label"] + f"\n[dim]{p['desc']}[/dim]", f"[{badge_color}]{p['badge']}[/]", stars, p["size_note"])
    console.print(t)
    console.print("[dim]Usage: aureus convert input.mp4 -p raw -S 1080p[/dim]")
    return 0


def cmd_effects(args) -> int:
    from rich.console import Console
    from rich.table import Table

    from aureus.core.presets import effect_summaries
    console = Console()
    t = Table(title="🎛 Effects & Shaders", title_style="bold #f6d38b", border_style="#5a4a20")
    t.add_column("Key", style="bold #f6d38b")
    t.add_column("Effect")
    t.add_column("Description")
    for e in effect_summaries():
        t.add_row(e["key"], e["label"], e["desc"])
    console.print(t)
    console.print("[dim]Usage: aureus convert in.mp4 --effects denoise:2,sharpen:0.5,deband,hdr[/dim]")
    return 0


def cmd_tui(args) -> int:
    return launch_tui()


def launch_tui() -> int:
    try:
        from aureus.tui.app import AureusApp
    except ImportError as exc:
        from rich.console import Console
        Console().print(f"[bold red]TUI dependencies missing:[/bold red] {exc}\n"
                        "Install with: [bold]pip install textual rich[/bold]")
        return 1
    from aureus.core.jobs import JobManager
    app = AureusApp(job_manager=JobManager(output_dir=os.path.abspath("aureus_output")))
    app.run()
    return 0


# ------------------------------------------------------------------ parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aureus",
        description="AUREUS — Video Enhancer, Upscaler & RAW Lossless Converter.\n"
                    "Converts local files and links (YouTube & 1000+ sites) into RAW / lossless / HDR / max-compatibility output.",
        epilog=(
            "examples:\n"
            "  aureus                                   # interactive TUI\n"
            "  aureus server                            # local web UI at http://127.0.0.1:8765\n"
            "  aureus convert video.mp4 -S 1080p -p raw --effects denoise:2,sharpen:0.5\n"
            "  aureus url \"https://youtu.be/xyz\" -S 1080p -p lossless-x264 --quality 1080\n"
            "  aureus convert video.mp4 -p hdr10 --hdr -S 2160p          # SDR→HDR 4K\n"
            "  aureus doctor                            # check system requirements\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-V", "--version", action="version", version=f"AUREUS {__version__}")
    sub = p.add_subparsers(dest="command")

    c = sub.add_parser("convert", help="enhance/upscale a local video file",
                       description="Enhance, upscale and convert a local video file.", formatter_class=argparse.RawDescriptionHelpFormatter)
    c.add_argument("input", help="input video file")
    c.add_argument("-o", "--output", default=None, help="output directory (default: same as input)")
    add_common(c)
    c.set_defaults(func=cmd_convert)

    u = sub.add_parser("url", help="download a link (YouTube etc.) and enhance it",
                       description="Download a video from a link/embed (YouTube, and 1000+ sites via yt-dlp) then enhance & convert it.",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    u.add_argument("url", help="video or embed URL")
    u.add_argument("-o", "--output", default=None, help="output directory (default: current dir)")
    u.add_argument("--quality", default="best", help="download quality: best|2160|1440|1080|720|480 (default: best)")
    add_common(u)
    u.set_defaults(func=cmd_url)

    s = sub.add_parser("server", help="run the local AUREUS web UI",
                       description="Start the local web UI (browser-based interface with uploads, file browser and live progress).")
    s.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    s.add_argument("--port", type=int, default=8765, help="port (default: 8765)")
    s.add_argument("--output-dir", default="aureus_output", help="where outputs are written (default: ./aureus_output)")
    s.add_argument("--allow-low-ram", action="store_true", help="allow jobs on devices with < 8 GB RAM by default")
    s.add_argument("--no-open", action="store_true", help="do not auto-open the browser")
    s.set_defaults(func=cmd_server)

    i = sub.add_parser("info", help="inspect a media file or URL")
    i.add_argument("source", help="local file or URL")
    i.set_defaults(func=cmd_info)

    d = sub.add_parser("doctor", help="check system requirements & capabilities")
    d.set_defaults(func=cmd_doctor)

    ps = sub.add_parser("presets", help="list output presets")
    ps.set_defaults(func=cmd_presets)

    ef = sub.add_parser("effects", help="list effects & shaders")
    ef.set_defaults(func=cmd_effects)

    t = sub.add_parser("tui", help="launch the interactive TUI (same as bare 'aureus')")
    t.set_defaults(func=cmd_tui)

    return p


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv:
        return launch_tui()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        if args.command in ("-h", "--help"):
            parser.parse_args(["--help"])
        return launch_tui()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
