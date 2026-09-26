"""Output presets — from true RAW/lossless to maximum-compatibility encodes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputPreset:
    key: str
    label: str
    desc: str
    badge: str            # RAW | LOSSLESS | HDR | HQ | COMPAT
    container: str        # mkv | mp4 | mov | y4m
    ext: str
    vcodec: str           # ffmpeg encoder name (for capability checks)
    args: tuple           # default ffmpeg args (video)
    pix_fmt: str          # default pixel format
    audio: str            # default audio mode (auto | copy | flac | pcm | aac | none)
    hdr_ready: bool       # supports HDR signaling (10-bit HEVC)
    lossless: bool
    compat: int           # 1..5 — device playback compatibility
    size_note: str
    crf_default: int = 0  # 0 = N/A (lossless)


PRESETS = {
    "raw": OutputPreset(
        key="raw",
        label="RAW FFV1 — Lossless MKV",
        desc="True lossless archival master. Every pixel of the processed video is preserved bit-exact. Best for editing, archiving and re-encoding later.",
        badge="RAW",
        container="mkv", ext="mkv", vcodec="ffv1",
        args=("-c:v", "ffv1", "-level", "3", "-g", "1", "-slices", "16", "-slicecrc", "1"),
        pix_fmt="yuv444p10le", audio="flac", hdr_ready=False, lossless=True, compat=2,
        size_note="Very large — roughly 2-8 GB per minute at 1080p (depends on content).",
    ),
    "y4m": OutputPreset(
        key="y4m",
        label="RAW Y4M — Uncompressed Stream",
        desc="Completely uncompressed YUV4MPEG2 stream — the rawest possible output. No compression at all. Video only (no audio). For professional pipelines.",
        badge="RAW",
        container="y4m", ext="y4m", vcodec="rawvideo",
        args=("-c:v", "rawvideo", "-strict", "-1", "-f", "yuv4mpegpipe"),
        pix_fmt="yuv444p10le", audio="none", hdr_ready=False, lossless=True, compat=1,
        size_note="Enormous — ~4.5 GB per minute at 1080p 10-bit 444 (~270 GB/hour).",
    ),
    "lossless-x264": OutputPreset(
        key="lossless-x264",
        label="Lossless H.264 (qp=0)",
        desc="Bit-exact lossless H.264 in a broadly compatible 4:2:0 stream. Plays in most modern players/TVs while remaining 100% lossless.",
        badge="LOSSLESS",
        container="mkv", ext="mkv", vcodec="libx264",
        args=("-c:v", "libx264", "-qp", "0", "-preset", "medium"),
        pix_fmt="yuv420p", audio="copy", hdr_ready=False, lossless=True, compat=4,
        size_note="Large — typically 400 MB to 2 GB per minute at 1080p.",
    ),
    "lossless-x265": OutputPreset(
        key="lossless-x265",
        label="Lossless HEVC (lossless=1)",
        desc="Bit-exact lossless HEVC — smaller than lossless H.264 but needs an HEVC-capable player.",
        badge="LOSSLESS",
        container="mkv", ext="mkv", vcodec="libx265",
        args=("-c:v", "libx265", "-x265-params", "lossless=1", "-preset", "medium"),
        pix_fmt="yuv420p", audio="copy", hdr_ready=False, lossless=True, compat=3,
        size_note="Large — typically 300 MB to 1.5 GB per minute at 1080p.",
    ),
    "prores4444": OutputPreset(
        key="prores4444",
        label="Apple ProRes 4444",
        desc="Professionally (visually) lossless 10-bit 4:4:4 — the editing/mastering standard. Perfect for DaVinci Resolve / Final Cut / Premiere workflows, especially on macOS.",
        badge="HQ",
        container="mov", ext="mov", vcodec="prores_ks",
        args=("-c:v", "prores_ks", "-profile:v", "4444", "-vendor", "apl0"),
        pix_fmt="yuv444p10le", audio="pcm", hdr_ready=False, lossless=False, compat=3,
        size_note="~1-2 GB per minute at 1080p.",
    ),
    "dnxhr": OutputPreset(
        key="dnxhr",
        label="Avid DNxHR 444",
        desc="Visually lossless 10-bit 4:4:4 editing codec — the cross-platform standard for Windows/Mac NLEs.",
        badge="HQ",
        container="mov", ext="mov", vcodec="dnxhd",
        args=("-c:v", "dnxhd", "-profile:v", "dnxhr_444"),
        pix_fmt="yuv444p10le", audio="pcm", hdr_ready=False, lossless=False, compat=3,
        size_note="~1-2 GB per minute at 1080p.",
    ),
    "hdr10": OutputPreset(
        key="hdr10",
        label="HDR10 Master — 10-bit HEVC",
        desc="10-bit HEVC with BT.2020 + SMPTE 2084 (PQ) HDR signaling. Use with the HDR effect to expand SDR into an HDR container, or to keep HDR sources HDR.",
        badge="HDR",
        container="mp4", ext="mp4", vcodec="libx265",
        args=("-c:v", "libx265", "-crf", "16", "-preset", "medium",
              "-x265-params", "hdr10-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc"),
        pix_fmt="yuv420p10le", audio="auto", hdr_ready=True, lossless=False, compat=4,
        size_note="~200-600 MB per minute at 1080p (CRF 16).",
        crf_default=16,
    ),
    "hq-hevc": OutputPreset(
        key="hq-hevc",
        label="High Quality HEVC",
        desc="Near-transparent 8-bit HEVC at CRF 17 — small files, high fidelity. For HEVC-capable devices.",
        badge="HQ",
        container="mp4", ext="mp4", vcodec="libx265",
        args=("-c:v", "libx265", "-crf", "17", "-preset", "medium", "-tag:v", "hvc1"),
        pix_fmt="yuv420p", audio="auto", hdr_ready=False, lossless=False, compat=4,
        size_note="~60-200 MB per minute at 1080p.",
        crf_default=17,
    ),
    "superhd": OutputPreset(
        key="superhd",
        label="Super HD H.264 — Max Compatibility",
        desc="High-fidelity H.264 CRF 16 (visually lossless for almost everyone) in the most compatible package possible. Plays on virtually every device.",
        badge="COMPAT",
        container="mp4", ext="mp4", vcodec="libx264",
        args=("-c:v", "libx264", "-crf", "16", "-preset", "medium"),
        pix_fmt="yuv420p", audio="auto", hdr_ready=False, lossless=False, compat=5,
        size_note="~100-350 MB per minute at 1080p.",
        crf_default=16,
    ),
    "av1": OutputPreset(
        key="av1",
        label="AV1 High Quality",
        desc="AV1 (AOM) — highest compression efficiency. Slow to encode; needs an AV1-capable device to play.",
        badge="HQ",
        container="mkv", ext="mkv", vcodec="libsvtav1",
        args=("-c:v", "libsvtav1", "-crf", "26", "-preset", "6", "-svtav1-params", "enable_qm=1:scd=1"),
        pix_fmt="yuv420p", audio="copy", hdr_ready=False, lossless=False, compat=3,
        size_note="~40-150 MB per minute at 1080p.",
        crf_default=24,
    ),
}

ALIASES = {
    "ffv1": "raw",
    "rawvideo": "y4m",
    "yuv4mpeg": "y4m",
    "uncompressed": "y4m",
    "prores": "prores4444",
    "dnxhd": "dnxhr",
    "x264": "superhd",
    "h264": "superhd",
    "compat": "superhd",
    "hevc": "hq-hevc",
    "x265": "hq-hevc",
    "hdr": "hdr10",
    "lossless": "lossless-x264",
    "best": "superhd",
    "web": "superhd",
}


def get_preset(key: str) -> OutputPreset:
    key = (key or "superhd").strip().lower()
    key = ALIASES.get(key, key)
    if key not in PRESETS:
        raise ValueError(
            f"Unknown preset '{key}'. Available: {', '.join(sorted(PRESETS))}"
        )
    return PRESETS[key]


def preset_summaries() -> list:
    """Ordered summaries for --help / TUI / web UI."""
    order = ["raw", "y4m", "lossless-x264", "lossless-x265", "prores4444", "dnxhr",
             "hdr10", "hq-hevc", "superhd", "av1"]
    return [
        {
            "key": PRESETS[k].key,
            "label": PRESETS[k].label,
            "desc": PRESETS[k].desc,
            "badge": PRESETS[k].badge,
            "container": PRESETS[k].container,
            "lossless": PRESETS[k].lossless,
            "hdr_ready": PRESETS[k].hdr_ready,
            "compat": PRESETS[k].compat,
            "size_note": PRESETS[k].size_note,
        }
        for k in order
    ]


EFFECTS = [
    ("denoise", "Denoise", "Spatial+temporal noise reduction (hqdn3d levels, or NLMeans) — removes grain/compression noise and 'cleans' the picture."),
    ("sharpen", "Sharpen Shader", "FidelityFX-style Contrast Adaptive Sharpening (CAS) or classic Unsharp Mask — makes the picture crisper after upscaling."),
    ("deband", "Deband", "Removes color banding / gradient steps in skies and dark scenes."),
    ("deblock", "Deblock", "Softens blocking artifacts from heavily compressed sources."),
    ("deinterlace", "Deinterlace", "Bob deinterlace (yadif) for interlaced DVD/TV material to double-rate progressive."),
    ("grain", "Film Grain", "Adds subtle synthetic film grain (can mask banding and give a cinematic feel)."),
    ("color", "Color Boost", "Adjust saturation / contrast / gamma / brightness (eq filter)."),
    ("hdr", "SDR→HDR Expand", "Expands SDR into a 10-bit BT.2020 PQ container (zimg tone mapping + HDR signaling). Requires an HDR-capable display to see the effect."),
    ("tone-map", "HDR→SDR Tone Map", "Maps HDR sources down to SDR gracefully (hable) for SDR-only devices."),
    ("fps", "Frame Rate", "Set output frame rate, optionally with motion-compensated interpolation (minterpolate) for smooth 60fps."),
    ("scale", "Upscale", "Lanczos/Spline scaling to 720p/1080p/1440p/4K, 2x/4x factors, or pixel-art XBR scaling."),
]


def effect_summaries() -> list:
    return [{"key": k, "label": l, "desc": d} for k, l, d in EFFECTS]
