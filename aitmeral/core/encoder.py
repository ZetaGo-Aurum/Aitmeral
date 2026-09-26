"""ffmpeg command construction & execution with progress parsing + cancellation."""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from typing import Callable, List, Optional

from aitmeral.core.filters import FilterResult, build_filters
from aitmeral.core.media import MediaInfo
from aitmeral.core.options import Settings
from aitmeral.core.presets import OutputPreset, get_preset
from aitmeral.core.sysinfo import Caps, get_caps

PROGRESS_RE = re.compile(r"^([a-z_]+)=(.*)$")

# Codecs that may be stream-copied into each container
COPY_OK = {
    "mp4": {"aac", "mp3", "ac3", "eac3", "alac", "flac", "opus"},
    "mkv": {"aac", "mp3", "ac3", "eac3", "alac", "flac", "opus", "vorbis", "pcm_s16le", "pcm_s24le", "truehd", "dts"},
    "mov": {"aac", "mp3", "ac3", "eac3", "alac", "pcm_s16le", "pcm_s24le"},
}

# Hardware encoder mapping: software encoder -> hardware encoder candidates (in priority order)
HW_ENCODERS = {
    "libx264": [
        ("h264_nvenc", "NVIDIA NVENC"),
        ("h264_qsv", "Intel QuickSync"),
        ("h264_amf", "AMD AMF"),
        ("h264_videotoolbox", "Apple VideoToolbox"),
    ],
    "libx265": [
        ("hevc_nvenc", "NVIDIA NVENC"),
        ("hevc_qsv", "Intel QuickSync"),
        ("hevc_amf", "AMD AMF"),
        ("hevc_videotoolbox", "Apple VideoToolbox"),
    ],
    "libaom-av1": [
        ("av1_nvenc", "NVIDIA NVENC (Ada Lovelace+)"),
        ("av1_qsv", "Intel QuickSync (Arc+)"),
    ],
    "libsvtav1": [
        ("av1_nvenc", "NVIDIA NVENC (Ada Lovelace+)"),
        ("av1_qsv", "Intel QuickSync (Arc+)"),
    ],
}

# Hardware acceleration mapping for filters
HW_UPLOAD_FILTERS = {
    "cuda": "hwupload_cuda",
    "qsv": "hwupload=extra_hw_frames=64",
    "vaapi": "hwupload",
    "videotoolbox": "hwupload_videotoolbox",
}
HW_DOWNLOAD_FILTERS = {
    "cuda": "hwdownload,format=nv12",
    "qsv": "hwdownload,format=nv12",
    "vaapi": "hwdownload,format=nv12",
    "videotoolbox": "hwdownload,format=nv12",
}


class EncodingError(RuntimeError):
    pass


def _video_args(preset: OutputPreset, container: str, s: Settings, caps: Caps, notes: list,
                hdr_out: bool = False, hwaccel_works: bool = False) -> List[str]:
    args: List[str] = []
    codec = preset.vcodec
    params = list(preset.args)

    # Hardware encoder selection (only if hwaccel works)
    if hwaccel_works:
        hw_codec, hw_name = _select_hw_encoder(codec, caps, s)
        if hw_codec:
            codec = hw_codec
            notes.append(f"Using hardware encoder: {hw_name} ({hw_codec})")
            # Rebuild params for hardware encoder
            params = _build_hw_encoder_params(codec, s, preset, container, notes)

    # HDR signaling (PQ/BT.2020 tags) is only correct when the pipeline really outputs HDR
    if not hdr_out and "-x265-params" in params:
        idx = params.index("-x265-params")
        val = params[idx + 1]
        if "smpte2084" in val:
            del params[idx:idx + 2]
            notes.append("HDR signaling disabled — source/setting does not produce HDR output.")

    # encoder availability fallback chain
    fallbacks = {
        "libx265": ["libx264"],
        "libx264": [],
        "libaom-av1": ["libsvtav1", "libx265", "libx264"],
        "libsvtav1": ["libx265", "libx264"],
        "prores_ks": [],
        "dnxhd": [],
        "ffv1": [],
        "rawvideo": [],
    }
    if codec not in ("rawvideo",) and not caps.has_enc(codec):
        for cand in fallbacks.get(codec, []):
            if caps.has_enc(cand):
                notes.append(f"Encoder {codec} unavailable in this ffmpeg build — falling back to {cand}.")
                codec = cand
                # rebuild args for the fallback
                if cand == "libx264":
                    params = ["-c:v", "libx264", "-crf", "16", "-preset", "medium"]
                elif cand == "libx265":
                    params = ["-c:v", "libx265", "-crf", "17", "-preset", "medium", "-tag:v", "hvc1"]
                elif cand == "libsvtav1":
                    params = ["-c:v", "libsvtav1", "-crf", "26", "-preset", "6"]
                break
        else:
            raise EncodingError(
                f"ffmpeg has no usable encoder for preset '{preset.key}' ({codec}). "
                "Install a full ffmpeg build (apt/brew/winget/pkg install ffmpeg)."
            )

    # CRF override for lossy presets
    if s.crf and preset.crf_default:
        for i, a in enumerate(params):
            if a == "-crf" and i + 1 < len(params):
                params[i + 1] = str(s.crf)
                notes.append(f"CRF overridden to {s.crf}.")

    # container-specific tag
    if container != "mp4":
        params = [a for i, a in enumerate(params) if not (a == "-tag:v" and i + 1 < len(params) and params[i + 1] == "hvc1")]

    args += params
    return args


def _select_hw_encoder(software_codec: str, caps: Caps, s: Settings) -> tuple:
    """Select the best available hardware encoder. Returns (codec_name, display_name) or (None, None)."""
    if s.hwaccel == "off" or s.hwaccel == "auto":
        if s.hwaccel == "off":
            return None, None
        # auto mode - check if hardware encoding is available
        pass
    elif s.hwaccel in ("cuda", "nvenc", "nvidia"):
        return _try_hw_encoder(software_codec, caps, ["cuda", "nvenc"])
    elif s.hwaccel in ("qsv", "intel", "quicksync"):
        return _try_hw_encoder(software_codec, caps, ["qsv"])
    elif s.hwaccel in ("amf", "amd"):
        return _try_hw_encoder(software_codec, caps, ["amf"])
    elif s.hwaccel in ("videotoolbox", "vt", "apple", "macos"):
        return _try_hw_encoder(software_codec, caps, ["videotoolbox"])

    # Auto-detect best hardware encoder
    if caps.has_hwaccel("cuda") or caps.has_hwaccel("nvenc"):
        return _try_hw_encoder(software_codec, caps, ["cuda", "nvenc"])
    if caps.has_hwaccel("qsv"):
        return _try_hw_encoder(software_codec, caps, ["qsv"])
    if caps.has_hwaccel("vaapi"):
        return _try_hw_encoder(software_codec, caps, ["vaapi"])
    if caps.has_hwaccel("amf"):
        return _try_hw_encoder(software_codec, caps, ["amf"])
    if caps.has_hwaccel("videotoolbox"):
        return _try_hw_encoder(software_codec, caps, ["videotoolbox"])
    return None, None


def _try_hw_encoder(software_codec: str, caps: Caps, hwaccel_types: list) -> tuple:
    """Try to find a hardware encoder for the given software codec."""
    candidates = HW_ENCODERS.get(software_codec, [])
    for hw_codec, hw_name in candidates:
        # Extract hwaccel type from encoder name (e.g., h264_nvenc -> nvenc, hevc_qsv -> qsv)
        hw_type = hw_codec.split('_')[-1]
        if hw_type in hwaccel_types and caps.has_enc(hw_codec):
            return hw_codec, hw_name
    return None, None


def _build_hw_encoder_params(codec: str, s: Settings, preset: OutputPreset, container: str, notes: list) -> list:
    """Build parameters for hardware encoder."""
    params = []
    is_hevc = "hevc" in codec or "265" in codec
    is_av1 = "av1" in codec

    if "nvenc" in codec:
        params = ["-c:v", codec]
        if is_hevc:
            params += ["-preset", "p5", "-rc", "vbr", "-cq", str(s.crf or preset.crf_default or 20)]
        else:
            params += ["-preset", "p5", "-rc", "vbr", "-cq", str(s.crf or preset.crf_default or 20)]
        # NVENC supports 10-bit - pix_fmt is set by filter chain
        notes.append("NVENC: using VBR rate control with CQ (constant quality)")

    elif "qsv" in codec:
        params = ["-c:v", codec, "-preset", "medium"]
        if is_hevc:
            params += ["-global_quality", str(s.crf or preset.crf_default or 20)]
        else:
            params += ["-global_quality", str(s.crf or preset.crf_default or 20)]
        params += ["-low_power", "0"]
        notes.append("QuickSync: using ICQ (intelligent constant quality)")

    elif "amf" in codec:
        params = ["-c:v", codec, "-quality", "balanced"]
        if is_hevc:
            params += ["-qp_i", str(s.crf or preset.crf_default or 20)]
        else:
            params += ["-qp_i", str(s.crf or preset.crf_default or 20)]
        notes.append("AMF: using balanced quality preset")

    elif "videotoolbox" in codec:
        params = ["-c:v", codec, "-allow_sw", "0"]
        if is_hevc:
            params += ["-q:v", str(s.crf or preset.crf_default or 20)]
        else:
            params += ["-q:v", str(s.crf or preset.crf_default or 20)]
        notes.append("VideoToolbox: using constant quality")

    else:
        # Fallback to software
        return list(preset.args)

    return params


def _get_thread_count(s: Settings) -> int:
    """Get optimal thread count for encoding."""
    if s.threads > 0:
        return s.threads
    # Auto: use CPU count but cap at 16 for diminishing returns
    import os
    cpu_count = os.cpu_count() or 4
    return min(cpu_count, 16)


def _audio_args(s: Settings, preset: OutputPreset, container: str, info: Optional[MediaInfo], notes: list) -> List[str]:
    if container == "y4m" or preset.audio == "none":
        return ["-an"]
    if info is not None and not info.has_audio:
        return ["-an"]

    mode = s.audio if s.audio != "auto" else ("copy" if preset.audio in ("auto", "copy") else preset.audio)
    src_codec = (info.acodec if info else "") or ""
    copy_ok = src_codec in COPY_OK.get(container, set())

    if mode == "copy":
        if copy_ok:
            return ["-c:a", "copy"]
        notes.append(f"Audio copy not possible ({src_codec or 'unknown codec'} -> {container}); transcoding to a safe default.")
        mode = "auto"
    if mode == "flac":
        if container in ("mkv",):
            return ["-c:a", "flac"]
        notes.append("FLAC not supported by this container — using a safe fallback.")
        mode = "auto"
    if mode == "pcm":
        if container in ("mov", "mkv"):
            return ["-c:a", "pcm_s24le"]
        notes.append("PCM not supported by this container — using AAC 320k.")
        return ["-c:a", "aac", "-b:a", "320k"]
    # auto / aac / fallback
    if copy_ok and s.audio == "auto" and preset.audio in ("auto", "copy"):
        return ["-c:a", "copy"]
    if container == "mp4":
        return ["-c:a", "aac", "-b:a", "320k"]
    if container in ("mov", "mkv"):
        return ["-c:a", "flac"]
    return ["-c:a", "aac", "-b:a", "320k"]


def build_command(src: str, out: str, s: Settings, info: Optional[MediaInfo], caps: Caps = None) -> "tuple[list, FilterResult, list]":
    """Build the full ffmpeg command line. Returns (cmd, filter_result, notes)."""
    caps = caps or get_caps()
    preset = get_preset(s.preset)
    fres = build_filters(s, info, caps)
    notes = list(fres.notes)

    container = preset.container
    if s.extra_args:
        m = re.search(r"(?:^|\s)-(?:f|format)\s+(\S+)", s.extra_args)
        if m:
            container = m.group(1)

    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y"]

    # Hardware acceleration: input-side hwaccel for decoding
    hwaccel = _get_hwaccel_flag(s, caps)
    hwaccel_works = False
    if hwaccel:
        # Test if hwaccel actually works (e.g., CUDA drivers installed)
        if _test_hwaccel(hwaccel):
            cmd += ["-hwaccel", hwaccel]
            hwaccel_works = True
        else:
            notes.append(f"Hardware acceleration '{hwaccel}' not available (drivers missing?) — falling back to software")

    cmd += ["-i", src]

    # Build filter chain with hardware upload/download if using hardware encoder
    filters = list(fres.filters)
    hw_encoder = _get_hw_encoder_type(s, caps, preset.vcodec) if hwaccel_works else None
    if hw_encoder:
        # Add hwupload before filters, hwdownload after filters
        upload_filter = HW_UPLOAD_FILTERS.get(hw_encoder)
        download_filter = HW_DOWNLOAD_FILTERS.get(hw_encoder)
        if upload_filter and download_filter:
            # Insert hwupload at the beginning and hwdownload at the end
            filters.insert(0, upload_filter)
            filters.append(download_filter)
            notes.append(f"Hardware acceleration: {hw_encoder} upload/download enabled")

    if filters:
        cmd += ["-vf", ",".join(filters)]

    cmd += ["-map", "0:v:0", "-map", "0:a?"]
    hdr_out = fres.hdr_expand or (info is not None and info.hdr and not fres.tonemap_down)
    cmd += _video_args(preset, container, s, caps, notes, hdr_out=hdr_out, hwaccel_works=hwaccel_works)
    cmd += ["-pix_fmt", fres.pix_fmt]

    if container == "mkv" and info is not None and info.has_subs:
        cmd += ["-map", "0:s?", "-c:s", "copy"]
    cmd += _audio_args(s, preset, container, info, notes)

    if fres.hdr_expand or (info is not None and info.hdr and not fres.tonemap_down and container in ("mp4", "mkv", "mov")):
        cmd += ["-metadata:s:v:0", "color_primaries=bt2020",
                "-metadata:s:v:0", "color_trc=smpte2084",
                "-metadata:s:v:0", "color_space=bt2020nc"]

    cmd += ["-map_metadata", "0"]
    if container == "mp4":
        cmd += ["-movflags", "+faststart"]

    # Auto-thread detection: use all cores if not specified
    thread_count = _get_thread_count(s)
    cmd += ["-threads", str(thread_count)]
    if thread_count > 1 and s.threads == 0:
        notes.append(f"Auto-threads: using {thread_count} threads")

    if s.extra_args:
        import shlex
        try:
            cmd += shlex.split(s.extra_args)
        except ValueError:
            notes.append("Could not parse --extra-args (quote mismatch) — ignored.")
    cmd += ["-max_muxing_queue_size", "4096", "-stats_period", "1",
            "-progress", "pipe:1", "-nostats", "-loglevel", "warning", out]
    return cmd, fres, notes


def _get_hwaccel_flag(s: Settings, caps: Caps) -> Optional[str]:
    """Get the hwaccel flag for input decoding."""
    if s.hwaccel == "off":
        return None
    if s.hwaccel in ("cuda", "nvenc", "nvidia") and (caps.has_hwaccel("cuda") or caps.has_hwaccel("nvenc")):
        return "cuda"
    if s.hwaccel in ("qsv", "intel", "quicksync") and caps.has_hwaccel("qsv"):
        return "qsv"
    if s.hwaccel in ("vaapi") and caps.has_hwaccel("vaapi"):
        return "vaapi"
    if s.hwaccel in ("amf", "amd") and caps.has_hwaccel("amf"):
        return "amf"
    if s.hwaccel in ("videotoolbox", "vt", "apple", "macos") and caps.has_hwaccel("videotoolbox"):
        return "videotoolbox"

    # Auto-detect
    if s.hwaccel == "auto":
        if caps.has_hwaccel("cuda") or caps.has_hwaccel("nvenc"):
            return "cuda"
        if caps.has_hwaccel("qsv"):
            return "qsv"
        if caps.has_hwaccel("vaapi"):
            return "vaapi"
        if caps.has_hwaccel("amf"):
            return "amf"
        if caps.has_hwaccel("videotoolbox"):
            return "videotoolbox"
    return None


def _test_hwaccel(hwaccel: str) -> bool:
    """Test if hardware acceleration actually works by running a quick ffmpeg probe."""
    import subprocess
    try:
        # Quick test: try to decode a dummy frame with the hwaccel
        result = subprocess.run([
            "ffmpeg", "-hide_banner", "-nostdin", "-v", "error",
            "-init_hw_device", f"{hwaccel}=hw",
            "-f", "lavfi", "-i", "testsrc=duration=0.1:size=32x32:rate=1",
            "-vf", f"hwdownload,format=nv12",
            "-f", "null", "-"
        ], capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def _get_hw_encoder_type(s: Settings, caps: Caps, software_codec: str) -> Optional[str]:
    """Get the hardware encoder type (cuda, qsv, vaapi, etc.) for filter chain."""
    if s.hwaccel == "off":
        return None

    # Check if hardware encoder was selected
    hw_codec, _ = _select_hw_encoder(software_codec, caps, s)
    if not hw_codec:
        return None

    if "nvenc" in hw_codec:
        return "cuda"
    elif "qsv" in hw_codec:
        return "qsv"
    elif "amf" in hw_codec:
        return "vaapi"  # AMF uses VAAPI for filter chain
    elif "videotoolbox" in hw_codec:
        return "videotoolbox"
    return None


def run_ffmpeg(cmd: List[str],
               duration: float = 0.0,
               on_progress: Optional[Callable[[float, float, str], None]] = None,
               cancel_event: Optional[threading.Event] = None,
               proc_hook: Optional[Callable[[subprocess.Popen], None]] = None) -> "tuple[int, list]":
    """Run ffmpeg, parsing -progress output.

    on_progress(fraction_0_1, speed_x, detail)
    Returns (returncode, collected stderr/warning lines).
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    if proc_hook:
        proc_hook(proc)

    log: list = []
    state = {"frac": 0.0, "speed": 0.0}

    def parse_stdout():
        try:
            for line in proc.stdout:
                line = line.strip()
                m = PROGRESS_RE.match(line)
                if not m:
                    continue
                key, val = m.group(1), m.group(2)
                if key == "out_time_us":
                    # NOTE: ffmpeg's out_time_ms is actually microseconds (legacy quirk) —
                    # only out_time_us is trustworthy.
                    try:
                        us = float(val)
                        if duration > 0:
                            state["frac"] = max(0.0, min(1.0, us / 1_000_000.0 / duration))
                    except ValueError:
                        pass
                elif key == "out_time_ms" and duration > 0 and state["frac"] == 0.0:
                    try:  # fallback for builds without out_time_us (value is in µs!)
                        state["frac"] = max(0.0, min(1.0, float(val) / 1_000_000.0 / duration))
                    except ValueError:
                        pass
                elif key == "speed":
                    try:
                        state["speed"] = float(val.replace("x", ""))
                    except ValueError:
                        pass
                elif key == "progress":
                    if on_progress:
                        detail = f"{state['speed']:.2f}x" if state["speed"] else ""
                        on_progress(state["frac"], state["speed"], detail)
        except Exception:
            pass

    def drain_stderr():
        try:
            for line in proc.stderr:
                line = line.rstrip()
                if line:
                    log.append(line)
        except Exception:
            pass

    t1 = threading.Thread(target=parse_stdout, daemon=True)
    t2 = threading.Thread(target=drain_stderr, daemon=True)
    t1.start()
    t2.start()

    try:
        while proc.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                t1.join(timeout=2)
                t2.join(timeout=2)
                return -2, log
            time.sleep(0.15)
    finally:
        pass
    t1.join(timeout=3)
    t2.join(timeout=3)
    rc = proc.returncode
    if on_progress and rc == 0:
        on_progress(1.0, state["speed"], "done")
    return rc, log


def pretty_cmd(cmd: List[str]) -> str:
    quote = lambda a: a if re.match(r"^[\w./:=+,%@-]+$", a) else '"' + a.replace('"', '\\"') + '"'
    return " ".join(quote(a) for a in cmd)
