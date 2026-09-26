"""AITMERAL local web server — `aitmeral server`.

Pure standard-library HTTP server (no extra dependencies) serving the web UI
and a JSON API consumed by it. Includes upload, file browsing, job control
and range-request streaming of finished outputs.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from aitmeral import __version__
from aitmeral.core import downloader, media, sysinfo
from aitmeral.core.jobs import ACTIVE, JobManager
from aitmeral.core.options import Settings
from aitmeral.core.presets import effect_summaries, preset_summaries

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

MIME_MAP = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
    ".mkv": "video/x-matroska", ".mov": "video/quicktime", ".avi": "video/x-msvideo",
    ".ts": "video/mp2t", ".y4m": "application/octet-stream", ".flv": "video/x-flv",
    ".wmv": "video/x-ms-wmv", ".mp3": "audio/mpeg", ".flac": "audio/flac",
    ".m4a": "audio/mp4", ".wav": "audio/wav", ".png": "image/png", ".jpg": "image/jpeg",
    ".svg": "image/svg+xml", ".html": "text/html; charset=utf-8", ".js": "text/javascript",
    ".css": "text/css; charset=utf-8",
}


class AureusState:
    def __init__(self, output_dir: str, allow_low_ram: bool = False):
        self.manager = JobManager(output_dir=output_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.uploads_dir = os.path.join(self.output_dir, "_uploads")
        os.makedirs(self.uploads_dir, exist_ok=True)
        self.allow_low_ram = allow_low_ram
        self.started = time.time()


STATE: AureusState = None  # type: ignore


def _job_public(job):
    d = job.to_public()
    d["is_active"] = job.status in ACTIVE
    d["out_size_h"] = ""
    if job.result and job.result.get("summary"):
        d["out_size_h"] = job.result["summary"].get("output_size_h", "")
        d["out_res"] = job.result["summary"].get("output_res", "?")
        d["out_vcodec"] = job.result["summary"].get("output_vcodec", "")
    else:
        d["out_res"] = ""
        d["out_vcodec"] = ""
    return d


class Handler(BaseHTTPRequestHandler):
    server_version = f"Aitmeral/{__version__}"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------ plumbing
    def log_message(self, fmt, *args):  # silence default request logging
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, status=400):
        self._json({"error": str(msg)}, status=status)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _serve_file(self, path: str, download_name: str = None):
        if not os.path.isfile(path):
            self._error("File not found", 404)
            return
        size = os.path.getsize(path)
        mime = MIME_MAP.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        start, end = 0, size - 1

        range_header = self.headers.get("Range")
        partial = False
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2):
                        end = min(int(m.group(2)), size - 1)
                else:  # suffix range: last N bytes
                    start = max(0, size - int(m.group(2)))
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                partial = True

        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", mime)
        self.send_header("Accept-Ranges", "bytes")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download_name:
            try:
                dn = download_name.encode("utf-8").decode("latin-1", "replace")
                self.send_header("Content-Disposition", f"attachment; filename=\"{dn}\"")
            except Exception:
                pass
        self.send_header("Content-Length", str(length))
        self.end_headers()
        try:
            with open(path, "rb") as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(1024 * 512, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # -------------------------------------------------------------- routes
    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path in ("/", "/index.html"):
                with open(os.path.join(STATIC_DIR, "index.html"), "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/favicon.svg":
                svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
                       '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                       '<stop offset="0" stop-color="#f7dc9a"/><stop offset="1" stop-color="#c9932f"/>'
                       '</linearGradient></defs>'
                       '<rect width="64" height="64" rx="14" fill="#0b0e17"/>'
                       '<path d="M32 10 L52 54 H42 L32 30 L22 54 H12 Z" fill="url(#g)"/>'
                       '</svg>').encode()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(svg)))
                self.end_headers()
                self.wfile.write(svg)
            elif path == "/api/system":
                ff = sysinfo.ffmpeg_path()
                caps = sysinfo.get_caps()
                ytd = sysinfo.ytdlp_path()
                self._json({
                    "app": "AITMERAL", "version": __version__,
                    "platform": sysinfo.platform_key(),
                    "platform_name": sysinfo.platform_name(),
                    "python": sys.version.split()[0],
                    "cpu_count": os.cpu_count(),
                    "ram_gb": round(sysinfo.total_ram_gb(), 2),
                    "ram_ok": sysinfo.ram_ok(),
                    "min_ram_gb": 8,
                    "ffmpeg": {"found": bool(ff), "path": ff or "", "version": sysinfo.binary_version(ff) if ff else ""},
                    "ffprobe": bool(sysinfo.ffprobe_path()),
                    "ytdlp": {"found": bool(ytd), "path": ytd or "", "version": sysinfo.binary_version(ytd) if ytd else ""},
                    "caps": caps.brief(),
                    "output_dir": STATE.output_dir,
                    "uptime": int(time.time() - STATE.started),
                })
            elif path == "/api/presets":
                self._json({"presets": preset_summaries()})
            elif path == "/api/effects":
                self._json({"effects": effect_summaries()})
            elif path == "/api/jobs":
                self._json({"jobs": [_job_public(j) for j in STATE.manager.list()]})
            elif path.startswith("/api/jobs/") and not path.endswith("/file"):
                job_id = path.split("/")[3]
                job = STATE.manager.get(job_id)
                if not job:
                    self._error("Unknown job", 404)
                else:
                    self._json(_job_public(job))
            elif path.startswith("/api/jobs/") and path.endswith("/file"):
                job_id = path.split("/")[3]
                job = STATE.manager.get(job_id)
                if not job:
                    self._error("Unknown job", 404)
                    return
                if not job.output_path or not os.path.isfile(job.output_path):
                    self._error("Output not ready", 404)
                    return
                qs = parse_qs(parsed.query)
                self._serve_file(job.output_path, download_name=job.output_name if "dl" in qs else None)
            elif path == "/api/output-dir":
                self._json({"output_dir": STATE.output_dir})
            else:
                self._error("Not found", 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # noqa: BLE001
            try:
                self._error(f"Server error: {exc}", 500)
            except Exception:
                pass

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/probe":
                body = self._read_json()
                source = str(body.get("source") or "").strip()
                if not source:
                    self._error("Missing source")
                    return
                if downloader.is_url(source):
                    info = downloader.probe_url(source)
                    info["kind"] = "url"
                    self._json(info)
                else:
                    p = os.path.abspath(os.path.expanduser(source))
                    d = media.probe_url_safe(p)
                    if not d:
                        self._error("Cannot analyze that file (is it a video? does it exist?)")
                    else:
                        d["kind"] = "file"
                        self._json(d)
            elif path == "/api/browse":
                body = self._read_json()
                target = body.get("path") or STATE.output_dir
                target = os.path.abspath(os.path.expanduser(str(target)))
                if not os.path.isdir(target):
                    self._error("Not a directory")
                    return
                entries = []
                try:
                    for name in sorted(os.listdir(target), key=str.lower):
                        if name.startswith("."):
                            continue
                        full = os.path.join(target, name)
                        if os.path.isdir(full):
                            entries.append({"name": name, "path": full, "is_dir": True, "size": 0, "media": False})
                        else:
                            ext = os.path.splitext(name)[1].lower()
                            entries.append({
                                "name": name, "path": full, "is_dir": False,
                                "size": os.path.getsize(full), "size_h": media.human_size(os.path.getsize(full)),
                                "media": media.is_media_file(full),
                            })
                except PermissionError:
                    self._error("Permission denied")
                    return
                parent = os.path.dirname(target) if target != os.path.abspath(os.sep) else None
                self._json({"path": target, "parent": parent, "entries": entries})
            elif path == "/api/jobs":
                body = self._read_json()
                kind = body.get("kind")
                source = str(body.get("source") or "").strip()
                if kind not in ("url", "file"):
                    self._error("kind must be 'url' or 'file'")
                    return
                if not source:
                    self._error("Missing source")
                    return
                settings = dict(body.get("settings") or {})
                if STATE.allow_low_ram:
                    settings.setdefault("force", True)
                try:
                    job = STATE.manager.submit(kind, source, settings)
                except Exception as exc:  # noqa: BLE001
                    self._error(f"Invalid job: {exc}")
                    return
                self._json({"id": job.id, "job": _job_public(job)})
            elif path.startswith("/api/jobs/") and path.endswith("/cancel"):
                job_id = path.split("/")[3]
                ok = STATE.manager.cancel(job_id)
                self._json({"ok": ok})
            elif path == "/api/upload":
                qs = parse_qs(parsed.query)
                name = os.path.basename(str((qs.get("name") or ["upload.mp4"])[0])) or "upload.mp4"
                name = re.sub(r"[^\w.\- ]", "_", name)[:120]
                dest = os.path.join(STATE.uploads_dir, f"{int(time.time())}_{name}")
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0:
                    self._error("Empty upload")
                    return
                remaining = length
                with open(dest, "wb") as fh:
                    while remaining > 0:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        fh.write(chunk)
                        remaining -= len(chunk)
                self._json({"path": dest, "size": os.path.getsize(dest), "name": name})
            else:
                self._error("Not found", 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # noqa: BLE001
            try:
                self._error(f"Server error: {exc}", 500)
            except Exception:
                pass

    def do_HEAD(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/jobs/") and path.endswith("/file"):
            job_id = path.split("/")[3]
            job = STATE.manager.get(job_id)
            if job and job.output_path and os.path.isfile(job.output_path):
                size = os.path.getsize(job.output_path)
                mime = MIME_MAP.get(os.path.splitext(job.output_path)[1].lower(), "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        m = re.match(r"^/api/jobs/([\w]+)$", path)
        if m:
            ok = STATE.manager.remove(m.group(1))
            self._json({"ok": ok})
            return
        self._error("Not found", 404)


def run_server(host: str, port: int, output_dir: str,
               allow_low_ram: bool = False, open_browser: bool = True) -> int:
    global STATE
    STATE = AureusState(output_dir, allow_low_ram)

    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as exc:
        print(f"[!] Could not bind {host}:{port} — {exc}")
        return 1
    server.daemon_threads = True

    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{port}"
    import rich.console
    console = rich.console.Console()
    console.print()
    console.print("[bold #f6d38b]    A U R E U S   W E B[/bold #f6d38b]  [dim]local video enhancer[/dim]")
    console.print(f"[dim]    ────────────────────────────────────────[/dim]")
    console.print(f"    ▸ URL         : [bold #8fd18f underline]{url}[/bold #8fd18f underline]")
    console.print(f"    ▸ Output dir  : [white]{STATE.output_dir}[/white]")
    console.print(f"    ▸ Jobs        : {STATE.manager.max_workers} worker thread(s)")
    console.print(f"    ▸ Platform    : [white]{sysinfo.platform_name()}[/white]")
    console.print(f"    ▸ RAM         : [white]{sysinfo.total_ram_gb():.1f} GB[/white] "
                  f"({'OK' if sysinfo.ram_ok() else '[bold yellow]below 8 GB — enable Proceed-anyway per job[/bold yellow]'})")
    console.print(f"    ▸ Stop        : [white]Ctrl+C[/white]")
    console.print()

    if open_browser:
        threading.Timer(0.6, lambda: _try_open(url)).start()

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down — waiting for jobs…[/yellow] (Ctrl+C again to force)")
        try:
            server.shutdown()
        except KeyboardInterrupt:
            pass
    finally:
        server.server_close()
    return 0


def _try_open(url: str):
    try:
        webbrowser.open(url)
    except Exception:
        pass
