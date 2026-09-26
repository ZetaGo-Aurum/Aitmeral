"""AUREUS interactive TUI — modern Textual interface with file manager & live queue."""

from __future__ import annotations

import os
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (Button, DataTable, DirectoryTree, Footer, Header,
                             Input, ListItem, ListView, Static, Select, Switch)

from aureus import __version__
from aureus.core import media, sysinfo
from aureus.core.jobs import JobManager
from aureus.core.options import Settings
from aureus.core.presets import get_preset, preset_summaries

LOGO = """[bold #f6d38b]     _    _ _____ __  __ _____ ____      _    _
[/][bold #eec271]    / \\  | |_   _|  \\/  | ____|  _ \\    / \\  | |
[/][bold #dca94f]   / _ \\ | | | | | |\\/| |  _| | |_) |  / _ \\ | |
[/][bold #c69137]  / ___ \\| | | | | |  | | |___|  _ <  / ___ \\| |___
[/][bold #a87625] /_/   \\_\\_| | |_|_|  |_|_____|_| \\_/_/   \\_\\_____|
[/][dim]      Video Enhancer · Upscaler · RAW Lossless[/]"""

NAV = [
    ("dashboard", "◉  Dashboard", "1"),
    ("files", " Folder  File Manager", "2"),
    ("enhance", " Ctrl  Enhance & Convert", "3"),
    ("url", " Link  URL Grabber (YouTube)", "4"),
    ("queue", " Hourglass  Jobs / Queue", "5"),
    ("system", " Gear  System Info", "6"),
]

SCALE_OPTIONS = [("Source (keep)", "source"), ("720p", "720p"), ("1080p", "1080p"),
                 ("1440p", "1440p"), ("4K (2160p)", "2160p"), ("2× factor", "2x"), ("4× factor", "4x")]
SHARPEN_OPTIONS = [("Off", 0.0), ("Light (0.25)", 0.25), ("Medium (0.40)", 0.4),
                   ("Strong (0.55)", 0.55), ("Max (0.75)", 0.75)]
DENOISE_OPTIONS = [("Off", 0), ("Light", 1), ("Medium", 2), ("Strong", 3)]
GRAIN_OPTIONS = [("Off", 0), ("Light (4)", 4), ("Medium (6)", 6), ("Strong (9)", 9)]
FPS_OPTIONS = [("Source", "source"), ("24", "24"), ("30", "30"), ("48", "48"), ("60", "60")]
AUDIO_OPTIONS = [("Auto", "auto"), ("Copy (no re-encode)", "copy"), ("FLAC lossless", "flac"),
                 ("PCM", "pcm"), ("AAC 320k", "aac")]
COLOR_OPTIONS = [("Off", "off"), ("Vivid (sat+)", "sat"), ("Punchy (contrast+)", "con"), ("Vivid + Punchy", "both")]


class ConfirmScreen(ModalScreen[bool]):
    """Small yes/no modal."""

    CSS = """
    ConfirmScreen { align: center middle; }
    #dlg { width: 64; height: auto; background: #10141f; border: round #b98a2f; padding: 1 2; }
    #dlg-msg { padding: 1 1; color: #e9ecf4; }
    #dlg-btns { height: auto; align-horizontal: center; padding-top: 1; }
    """

    def __init__(self, message: str, title: str = "Confirm") -> None:
        super().__init__()
        self.message = message
        self.title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="dlg"):
            yield Static(f"[bold #f0c76a]{self.title}[/]\n\n{self.message}", id="dlg-msg")
            with Horizontal(id="dlg-btns"):
                yield Button("Yes, proceed", id="dlg-yes", variant="warning")
                yield Button("Cancel", id="dlg-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "dlg-yes")


class AureusApp(App):
    TITLE = "AUREUS"
    SUB_TITLE = f"v{__version__} — Video Enhancer & Upscaler"

    CSS = """
    Screen { background: #0a0d14; }
    #body { height: 1fr; }
    #sidebar { width: 34; background: #0d111a; border-right: solid #232a3d; }
    #logo { padding: 1 1 0 1; text-style: none; }
    #nav { padding: 0 0 1 0; background: #0d111a; height: auto; }
    ListItem { padding: 0 1; }
    ListItem.-highlight { background: #1c2333; }
    ListView > ListItem.--hover { background: #161d2c; }
    #content { padding: 0 2 1 2; }
    .pane { height: auto; }
    .hidden { display: none; }
    .sect { padding: 1 0 0 0; }
    .sect-title { color: #f0c76a; text-style: bold; padding: 1 0 0 0; }
    .dim { color: #6b7490; }
    .warn { color: #f2c14e; }
    .ok { color: #7ddc9a; }
    .err { color: #f28c8c; }
    .bignum { padding: 0 1; }
    Input, Select, DirectoryTree, DataTable { border: round #232a3d; }
    Input:focus, Select:focus { border: round #b98a2f; }
    DirectoryTree { height: 1fr; background: #0d111a; }
    DataTable { height: auto; max-height: 1fr; background: #0d111a; }
    .btnrow { height: auto; padding: 1 0; }
    Button { margin: 0 1 0 0; }
    #eh-start { background: #c9932f; color: #141005; text-style: bold; }
    .switchline { height: 3; padding: 0 1; }
    .info-box { border: round #2a3145; padding: 0 1; height: auto; background: #0d111a; }
    #dash-hero { padding: 1 2; border: round #b98a2f; background: #0d111a; height: auto; }
    #queue-detail { height: auto; border: round #2a3145; padding: 0 1; background: #0d111a; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "pane('dashboard')", "Dashboard"),
        ("2", "pane('files')", "Files"),
        ("3", "pane('enhance')", "Enhance"),
        ("4", "pane('url')", "URL"),
        ("5", "pane('queue')", "Queue"),
        ("6", "pane('system')", "System"),
    ]

    def __init__(self, job_manager: JobManager):
        super().__init__()
        self.manager = job_manager
        self._files_selected: Optional[str] = None
        self._url_ok: bool = False
        self._queue_keys: list = []

    # ------------------------------------------------------------ compose
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Static(LOGO, id="logo")
                yield ListView(id="nav", *[
                    ListItem(Static(f"[dim]{key}[/]  {label}"), name=name, id=f"nav-{name}")
                    for name, label, key in NAV
                ])
            with VerticalScroll(id="content"):
                # ---- dashboard ----
                with Vertical(id="pane-dashboard", classes="pane"):
                    yield Static("", id="dash-hero")
                # ---- file manager ----
                with Vertical(id="pane-files", classes="pane hidden"):
                    yield Static("[bold #f0c76a]📁 FILE MANAGER[/]  [dim]pilih file video untuk diproses[/]", classes="sect-title")
                    with Horizontal(classes="btnrow"):
                        yield Input(placeholder="Path (mis. /home/user/videos)", id="files-path")
                        yield Button("Go", id="files-go", variant="primary")
                        yield Button("↑ Up", id="files-up")
                    yield DirectoryTree(os.path.abspath("."), id="files-tree")
                    yield Static("[dim]Pilih file video untuk melihat detail…[/]", id="files-detail", classes="info-box")
                    with Horizontal(classes="btnrow"):
                        yield Button("➜ Gunakan file ini", id="files-use", variant="success")
                        yield Button("Refresh", id="files-refresh")
                # ---- enhance ----
                with Vertical(id="pane-enhance", classes="pane hidden"):
                    yield Static("[bold #f0c76a]🎛 ENHANCE & CONVERT[/]  [dim]file lokal → RAW / lossless / HDR[/]", classes="sect-title")
                    yield Static("Input file", classes="dim")
                    yield Input(placeholder="/path/ke/video.mp4", id="eh-input")
                    with Horizontal(classes="btnrow"):
                        yield Button("📁 Browse…", id="eh-browse")
                    yield Static("Output directory", classes="dim")
                    yield Input(value=self.manager.default_output_dir, id="eh-outdir")
                    with Horizontal(classes="btnrow"):
                        with Vertical():
                            yield Static("Output preset", classes="dim")
                            yield Select(
                                [(p["label"], p["key"]) for p in preset_summaries()],
                                value="superhd", allow_blank=False, id="eh-preset")
                        with Vertical():
                            yield Static("Target resolution", classes="dim")
                            yield Select(SCALE_OPTIONS, value="1080p", allow_blank=False, id="eh-scale")
                    with Horizontal(classes="btnrow"):
                        with Vertical():
                            yield Static("Denoise (menjernihkan)", classes="dim")
                            yield Select(DENOISE_OPTIONS, value=0, allow_blank=False, id="eh-denoise")
                        with Vertical():
                            yield Static("Sharpen shader", classes="dim")
                            yield Select([("CAS (adaptive)", "cas"), ("Unsharp Mask", "unsharp"), ("Off", "none")],
                                         value="cas", allow_blank=False, id="eh-shader")
                        with Vertical():
                            yield Static("Sharpen strength", classes="dim")
                            yield Select(SHARPEN_OPTIONS, value=0.4, allow_blank=False, id="eh-sharpen")
                    with Horizontal(classes="btnrow"):
                        with Vertical():
                            yield Static("Scaler", classes="dim")
                            yield Select([("Lanczos (sharpest)", "lanczos"), ("Spline", "spline"),
                                          ("Bicubic", "bicubic"), ("Gaussian (soft)", "gauss"),
                                          ("XBR 2× (pixel-art)", "xbr2"), ("XBR 4× (pixel-art)", "xbr4")],
                                         value="lanczos", allow_blank=False, id="eh-scaler")
                        with Vertical():
                            yield Static("Frame rate", classes="dim")
                            yield Select(FPS_OPTIONS, value="source", allow_blank=False, id="eh-fps")
                    with Horizontal(classes="btnrow"):
                        with Vertical():
                            yield Static("Film grain", classes="dim")
                            yield Select(GRAIN_OPTIONS, value=0, allow_blank=False, id="eh-grain")
                        with Vertical():
                            yield Static("Color boost", classes="dim")
                            yield Select(COLOR_OPTIONS, value="off", allow_blank=False, id="eh-color")
                        with Vertical():
                            yield Static("Audio", classes="dim")
                            yield Select(AUDIO_OPTIONS, value="auto", allow_blank=False, id="eh-audio")
                    yield Static("[bold #f0c76a]EFFECTS[/]", classes="sect-title")
                    with Horizontal(classes="switchline"):
                        yield Switch(False, id="sw-deband")
                        yield Static("Deband — hapus banding gradasi", classes="dim")
                        yield Switch(False, id="sw-deblock")
                        yield Static("Deblock — hapus artefak blok", classes="dim")
                    with Horizontal(classes="switchline"):
                        yield Switch(False, id="sw-deinterlace")
                        yield Static("Deinterlace — sumber interlaced", classes="dim")
                        yield Switch(False, id="sw-hdr")
                        yield Static("[bold #f0c76a]SDR→HDR[/] expand (10-bit PQ)", classes="dim")
                    with Horizontal(classes="switchline"):
                        yield Switch(False, id="sw-motion")
                        yield Static("Motion interpolation (SANGAT lambat)", classes="dim")
                    yield Static("", id="eh-summary", classes="info-box")
                    with Horizontal(classes="btnrow"):
                        yield Button("▶  START CONVERT", id="eh-start", variant="warning")
                    yield Static("[dim]Tips: preset RAW (FFV1) = lossless total untuk arsip; superhd = paling kompatibel di semua device.[/]", classes="dim")
                # ---- url ----
                with Vertical(id="pane-url", classes="pane hidden"):
                    yield Static("[bold #f0c76a]🌐 URL GRABBER[/]  [dim]YouTube / embed / 1000+ situs[/]", classes="sect-title")
                    yield Input(placeholder="https://youtube.com/watch?v=… atau /embed/…", id="url-input")
                    with Horizontal(classes="btnrow"):
                        yield Button("🔎 Check Info", id="url-check", variant="primary")
                        yield Select([("Best quality", "best"), ("≤ 4K", "2160"), ("≤ 1440p", "1440"),
                                      ("≤ 1080p", "1080"), ("≤ 720p", "720"), ("≤ 480p", "480")],
                                     value="best", allow_blank=False, id="url-quality")
                    yield Static("[dim]Tempel URL lalu Check Info. Enhancement memakai setting di tab Enhance & Convert.[/]",
                                 id="url-info", classes="info-box")
                    with Horizontal(classes="btnrow"):
                        yield Button("⬇  DOWNLOAD + ENHANCE", id="url-start", variant="warning")
                # ---- queue ----
                with Vertical(id="pane-queue", classes="pane hidden"):
                    yield Static("[bold #f0c76a]⧗ JOBS / QUEUE[/]  [dim]auto-refresh setiap 1 detik[/]", classes="sect-title")
                    yield DataTable(id="queue-table", cursor_type="row", zebra_stripes=True)
                    with Horizontal(classes="btnrow"):
                        yield Button("✕ Cancel selected", id="q-cancel", variant="error")
                        yield Button("🗑 Remove selected", id="q-remove")
                        yield Button("↻ Refresh", id="q-refresh")
                    yield Static("[dim]Pilih baris dengan mouse/panah. Output ada di folder aureus_output.[/]", id="queue-detail")
                # ---- system ----
                with Vertical(id="pane-system", classes="pane hidden"):
                    yield Static("[bold #f0c76a]⚙ SYSTEM[/]", classes="sect-title")
                    yield Static("Checking…", id="sys-report", classes="info-box")
                    yield Static("", id="sys-hints", classes="info-box")
        yield Footer()

    # ------------------------------------------------------------ lifecycle
    def on_mount(self) -> None:
        self.show_pane("dashboard")
        table = self.query_one("#queue-table", DataTable)
        table.add_columns("Status", "Source", "Preset", "Res", "Prog", "Stage")
        self.set_interval(1.0, self._tick_queue)
        self._render_dashboard()
        self.run_worker(self._load_system, thread=True, group="sysinfo")

    def show_pane(self, name: str) -> None:
        for pname, _, _ in NAV:
            pane = self.query_one(f"#pane-{pname}")
            if pname == name:
                pane.remove_class("hidden")
            else:
                pane.add_class("hidden")
        nav = self.query_one("#nav", ListView)
        try:
            idx = [n for n, _, _ in NAV].index(name)
            nav.highlighted = idx
        except ValueError:
            pass

    def action_pane(self, name: str) -> None:
        self.show_pane(name)

    # ------------------------------------------------------------ dashboard
    def _render_dashboard(self) -> None:
        ram = sysinfo.total_ram_gb()
        ff = sysinfo.ffmpeg_path()
        ytd = sysinfo.ytdlp_path()
        ram_style = "bold #7ddc9a" if ram >= 8 else "bold #f2c14e"
        ff_style = "bold #7ddc9a" if ff else "bold #f28c8c"
        ytd_style = "bold #7ddc9a" if ytd else "bold #f28c8c"
        hero = f"""{LOGO}

 [dim]Version[/] {__version__}   [dim]·[/]   [dim]Platform[/] {sysinfo.platform_name()}

 [dim]RAM[/]        [{ram_style}]{ram:.1f} GB[/] [dim]({'OK — meets the 8 GB requirement' if ram >= 8 else 'BELOW the 8 GB minimum — jobs need the Proceed-anyway confirm'})[/]
 [dim]ffmpeg[/]     [{ff_style}]{'ready' if ff else 'NOT FOUND — install ffmpeg'}[/]
 [dim]yt-dlp[/]     [{ytd_style}]{'ready' if ytd else 'NOT FOUND (URL download disabled)'}[/]
 [dim]Workers[/]    {self.manager.max_workers} thread(s) · [dim]Output[/] {self.manager.default_output_dir}

 [bold #f0c76a]Getting started[/]
 [dim]2[/] File Manager — pilih video lokal        [dim]4[/] URL Grabber — YouTube & situs lain
 [dim]3[/] Enhance — atur preset, efek & shader    [dim]5[/] Queue — pantau progres job

 [dim]Keys: 1-6 pindah panel · q keluar · tombol mouse sepenuhnya didukung[/]"""
        self.query_one("#dash-hero", Static).update(hero)

    @work(thread=True, group="sysinfo")
    def _load_system(self) -> None:
        rows, healthy = sysinfo.system_report()
        text = "\n".join(f"[bold #f0c76a]{k:<10}[/] {v}" for k, v in rows)
        hints = "[bold #f0c76a]Install hints[/]\n" \
                "Linux : sudo apt install ffmpeg && pip install yt-dlp\n" \
                "macOS : brew install ffmpeg yt-dlp\n" \
                "Win   : winget install Gyan.FFmpeg yt-dlp.yt-dlp\n" \
                "Termux: pkg install ffmpeg python && pip install yt-dlp"
        self.call_from_thread(self._set_system, text, hints, healthy)

    def _set_system(self, text: str, hints: str, healthy: bool) -> None:
        self.query_one("#sys-report", Static).update(text + ("\n\n[bold #7ddc9a]✔ READY[/]" if healthy else "\n\n[bold #f2c14e]⚠ Ada requirement yang belum terpenuhi[/]"))
        self.query_one("#sys-hints", Static).update(hints)

    # ------------------------------------------------------------ navigation
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id and event.item.id.startswith("nav-"):
            self.show_pane(event.item.id[4:])

    # ------------------------------------------------------------ file manager
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = str(event.path)
        self._files_selected = path
        self.query_one("#files-detail", Static).update(f"[dim]Analyzing[/] {os.path.basename(path)}…")
        self.run_worker(lambda: self._probe_file(path), thread=True, group="probe")

    def _probe_file(self, path: str) -> None:
        info = media.probe(path)
        if info.ok:
            txt = (f"[bold #f0c76a]{os.path.basename(path)}[/]\n"
                   f"[dim]Path[/]     {info.path}\n"
                   f"[dim]Res[/]      {info.res} @ {info.fps:.2f} fps   [dim]Codec[/] {info.vcodec} / {info.pix_fmt}\n"
                   f"[dim]Duration[/] {media.human_duration(info.duration)}   [dim]Size[/] {media.human_size(info.size)}"
                   + ("   [bold #f2c14e]HDR SOURCE[/]" if info.hdr else "")
                   + (f"\n[dim]Audio[/]    {info.acodec}" if info.has_audio else ""))
        else:
            txt = f"[#f28c8c]{info.error}[/]"
        self.call_from_thread(self._show_probe, txt)

    def _show_probe(self, text: str) -> None:
        self.query_one("#files-detail", Static).update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "files-go":
            self._goto_path()
        elif bid == "files-up":
            cur = self.query_one("#files-path", Input).value or "."
            self._set_tree(os.path.dirname(os.path.abspath(cur)) or "/")
        elif bid == "files-refresh":
            self._set_tree(self.query_one("#files-path", Input).value or ".")
        elif bid == "files-use":
            if self._files_selected:
                self.query_one("#eh-input", Input).value = self._files_selected
                self.notify("File dimuat ke Enhance panel", title="AUREUS", severity="information")
                self.show_pane("enhance")
        elif bid == "eh-browse":
            self.show_pane("files")
        elif bid == "eh-start":
            self._start_file_job()
        elif bid == "url-check":
            self._check_url()
        elif bid == "url-start":
            self._start_url_job()
        elif bid == "q-cancel":
            self._queue_action("cancel")
        elif bid == "q-remove":
            self._queue_action("remove")
        elif bid == "q-refresh":
            self._tick_queue()

    def _goto_path(self) -> None:
        raw = self.query_one("#files-path", Input).value.strip() or "."
        p = os.path.abspath(os.path.expanduser(raw))
        if os.path.isdir(p):
            self._set_tree(p)
        elif os.path.isfile(p):
            self._set_tree(os.path.dirname(p))
            self._files_selected = p
            self.run_worker(lambda: self._probe_file(p), thread=True, group="probe")
        else:
            self.notify(f"Path tidak ditemukan: {p}", severity="error")

    def _set_tree(self, path: str) -> None:
        self.query_one("#files-path", Input).value = path
        try:
            self.query_one("#files-tree", DirectoryTree).path = path
        except Exception:
            self.notify("Tidak bisa membuka path itu", severity="error")

    # ------------------------------------------------------------ enhance
    def _collect_settings(self) -> dict:
        s = Settings()
        s.preset = self.query_one("#eh-preset", Select).value
        s.scale = self.query_one("#eh-scale", Select).value
        s.scaler = self.query_one("#eh-scaler", Select).value
        s.denoise = int(self.query_one("#eh-denoise", Select).value or 0)
        s.shader = self.query_one("#eh-shader", Select).value
        s.sharpen = float(self.query_one("#eh-sharpen", Select).value or 0)
        s.fps = self.query_one("#eh-fps", Select).value
        s.grain = int(self.query_one("#eh-grain", Select).value or 0)
        s.audio = self.query_one("#eh-audio", Select).value
        color = self.query_one("#eh-color", Select).value
        s.saturation = 1.15 if color in ("sat", "both") else 1.0
        s.contrast = 1.06 if color in ("con", "both") else 1.0
        s.deband = self.query_one("#sw-deband", Switch).value
        s.deblock = self.query_one("#sw-deblock", Switch).value
        s.deinterlace = self.query_one("#sw-deinterlace", Switch).value
        s.hdr = self.query_one("#sw-hdr", Switch).value
        s.motion_interp = self.query_one("#sw-motion", Switch).value
        s.quality = self.query_one("#url-quality", Select).value or "best"
        s.keep_source = True
        return s.to_dict()

    def _update_summary(self) -> None:
        try:
            d = self._collect_settings()
            preset = get_preset(d["preset"])
            parts = [preset.badge, d["scale"].upper() if d["scale"] != "source" else "SOURCE RES"]
            if d["denoise"]:
                parts.append(f"denoise {d['denoise']}")
            if d["shader"] != "none" and d["sharpen"] > 0:
                parts.append(f"{d['shader']} {d['sharpen']}")
            if d["hdr"]:
                parts.append("HDR✨")
            if d["fps"] != "source":
                parts.append(d["fps"] + "fps")
            text = (f"[bold #f0c76a]OUTPUT PLAN[/]\n"
                    f"[dim]Preset[/]  {preset.label}  [dim]({preset.container.upper()}, {'lossless' if preset.lossless else 'high quality'})[/]\n"
                    f"[dim]Chain[/]  {' · '.join(parts)}\n"
                    f"[dim]Size[/]    {preset.size_note}")
            self.query_one("#eh-summary", Static).update(text)
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        self._update_summary()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        self._update_summary()

    def _start_file_job(self) -> None:
        raw = self.query_one("#eh-input", Input).value.strip()
        if not raw:
            self.notify("Pilih file input dulu (File Manager / Browse)", severity="warning")
            return
        path = os.path.abspath(os.path.expanduser(raw))
        if not os.path.isfile(path):
            self.notify(f"File tidak ada: {path}", severity="error")
            return
        self._submit_job("file", path)

    def _start_url_job(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            self.notify("Tempel URL video dulu", severity="warning")
            return
        from aureus.core.downloader import is_url
        if not is_url(url):
            self.notify("URL tidak valid (harus diawali http/https)", severity="error")
            return
        if not sysinfo.ytdlp_path():
            self.notify("yt-dlp belum terpasang — pip install yt-dlp", severity="error")
            return
        self._submit_job("url", url)

    def _submit_job(self, kind: str, source: str) -> None:
        if sysinfo.total_ram_gb() < 8:
            self.push_screen(ConfirmScreen(
                "Perangkat ini RAM-nya di bawah 8 GB (spesifikasi minimum AUREUS).\n"
                "Lanjutkan konversi juga? (proses bisa lambat / tidak stabil)"),
                lambda ok: self._really_submit(kind, source, ok))
        else:
            self._really_submit(kind, source, True)

    def _really_submit(self, kind: str, source: str, ok: bool) -> None:
        if not ok:
            return
        settings = self._collect_settings()
        settings["force"] = sysinfo.total_ram_gb() < 8  # user already confirmed
        outdir = self.query_one("#eh-outdir", Input).value.strip() or self.manager.default_output_dir
        try:
            job = self.manager.submit(kind, source, settings, output_dir=outdir)
            self.notify(f"Job {job.id} masuk queue ✓", title="Started", severity="information")
            self.show_pane("queue")
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Gagal memulai job: {exc}", severity="error")

    # ------------------------------------------------------------ url
    def _check_url(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            return
        self.query_one("#url-info", Static).update("[dim]Menghubungi…[/]")
        self.run_worker(lambda: self._do_check_url(url), thread=True, group="urlprobe")

    def _do_check_url(self, url: str) -> None:
        from aureus.core import downloader
        try:
            d = downloader.probe_url(url)
            txt = (f"[bold #f0c76a]{d['title']}[/]\n"
                   f"[dim]Uploader[/] {d['uploader'] or '-'}   [dim]Durasi[/] {d['duration_h']}   "
                   f"[dim]Best[/] {d['best_height'] or '?'}p   [dim]≈Size[/] {d['size_h']}")
            self._url_ok = True
        except Exception as exc:  # noqa: BLE001
            txt = f"[#f28c8c]✗ {str(exc)[:200]}[/]"
            self._url_ok = False
        self.call_from_thread(self._show_url_info, txt)

    def _show_url_info(self, text: str) -> None:
        self.query_one("#url-info", Static).update(text)

    # ------------------------------------------------------------ queue
    def _tick_queue(self) -> None:
        try:
            table = self.query_one("#queue-table", DataTable)
        except Exception:
            return
        jobs = self.manager.list()
        self._queue_keys = [j.id for j in jobs]
        table.clear()
        for j in reversed(jobs):  # newest first
            preset = (j.settings or {}).get("preset", "")
            scale = (j.settings or {}).get("scale", "")
            status_color = {"done": "#7ddc9a", "error": "#f28c8c", "running": "#f0c76a",
                            "canceled": "#6b7490", "queued": "#6b7490"}.get(j.status, "#e9ecf4")
            table.add_row(
                f"[{status_color}]{j.status.upper()}[/]",
                os.path.basename(j.display)[:38],
                preset, ("" if scale == "source" else scale),
                f"{j.progress:.0f}%", j.stage, key=j.id)
        try:
            sel = self.query_one("#queue-detail", Static)
            active = sum(1 for j in jobs if j.status in ("queued", "running"))
            done = sum(1 for j in jobs if j.status == "done")
            sel.update(f"[dim]{len(jobs)} total · {active} aktif · {done} selesai — output tersimpan di:[/]\n"
                       f"[dim]{self.manager.default_output_dir}[/]")
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            job = self.manager.get(event.row_key.value)
            if job:
                info = (f"[bold #f0c76a]{job.id}[/] [dim]·[/] {job.display}\n"
                        f"[dim]Status[/] {job.status} · {job.progress:.0f}% · {job.stage}\n"
                        + (f"[dim]Output[/] {job.output_path}\n" if job.output_path else "")
                        + (f"[#f28c8c]{job.error[:300]}[/]" if job.error else ""))
                self.query_one("#queue-detail", Static).update(info)

    def _queue_action(self, action: str) -> None:
        table = self.query_one("#queue-table", DataTable)
        if table.cursor_row is None or table.cursor_row < 0:
            self.notify("Pilih baris job dulu", severity="warning")
            return
        try:
            table.get_row_at(table.cursor_row)
        except Exception:
            return
        # resolve the highlighted row's key via its coordinates
        try:
            cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            key = cell_key[0].row_key.value if cell_key else None
        except Exception:
            key = None
        if not key:
            self.notify("Tidak ada job terpilih", severity="warning")
            return
        if action == "cancel":
            ok = self.manager.cancel(key)
            self.notify("Cancel dikirim ✓" if ok else "Tidak bisa cancel", severity="information" if ok else "warning")
        elif action == "remove":
            ok = self.manager.remove(key)
            self.notify("Job dihapus" if ok else "Job masih aktif — cancel dulu", severity="information" if ok else "warning")
        self._tick_queue()
