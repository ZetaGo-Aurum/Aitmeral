"""Filter-graph builder — upscaling, shaders/effects, HDR/tone-mapping chains."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

from aureus.core.media import MediaInfo
from aureus.core.options import Settings
from aureus.core.presets import OutputPreset, get_preset
from aureus.core.sysinfo import Caps, get_caps

TARGET_HEIGHTS = {240, 360, 480, 576, 720, 1080, 1440, 2160}
MAX_DIM = 7680

SCALER_FLAGS = {
    "lanczos": "lanczos",
    "spline": "spline",
    "bicubic": "bicubic",
    "gauss": "gauss",
    "neighbor": "neighbor",
}

HQDN3D_LEVELS = {
    1: "hqdn3d=1:1:4:4",
    2: "hqdn3d=2:1.5:6:6",
    3: "hqdn3d=4:3:9:6",
}
NLMEANS_LEVELS = {1: 2.0, 2: 3.5, 3: 6.0}


@dataclass
class FilterResult:
    filters: list = field(default_factory=list)
    target_wh: Optional[Tuple[int, int]] = None
    scale_desc: str = "source"
    hdr_expand: bool = False
    tonemap_down: bool = False
    pix_fmt: str = "yuv420p"
    notes: list = field(default_factory=list)


def resolve_target(s: Settings, info: Optional[MediaInfo]) -> Tuple[Optional[Tuple[int, int]], str]:
    """Return ((w, h) or None, description)."""
    kind, val = s.parse_scale()
    src_w, src_h = (info.width, info.height) if info and info.width else (0, 0)
    if kind == "source":
        return None, "source resolution"
    if kind == "exact":
        return val, f"{val[0]}x{val[1]}"
    if kind == "height":
        h = val
        if src_w and src_h:
            w = int(round(src_w * h / src_h))
            w += w % 2
            return (min(w, MAX_DIM), h), f"{min(w, MAX_DIM)}x{h}"
        return (h * 16 // 9, h), f"{h * 16 // 9}x{h}"
    if kind == "factor":
        if src_w and src_h:
            w, h = src_w * val, src_h * val
            w += w % 2
            h += h % 2
            return (min(w, MAX_DIM), min(h, MAX_DIM)), f"{min(w, MAX_DIM)}x{min(h, MAX_DIM)} ({val}x)"
        return (1920, 1080), "1920x1080 (2x fallback)"
    return None, "source resolution"


def resolve_pixfmt(preset: OutputPreset, s: Settings, hdr_out: bool, tonemap_down: bool) -> str:
    if hdr_out:
        chroma = s.chroma if s.chroma in ("420", "444") else "420"
        return f"yuv{chroma}p10le"
    if tonemap_down:
        return "yuv420p"

    base = preset.pix_fmt
    if preset.key == "y4m" and s.chroma == "rgb":
        s_chroma, note = "444", None  # Y4M has no RGB planar support
    else:
        s_chroma = s.chroma

    m = re.match(r"^yuv(\d{3})p(\d+)", base)
    base_chroma, base_depth = ("420", 8)
    if m:
        base_chroma, base_depth = m.group(1), int(m.group(2))
    elif base.startswith("gbrp"):
        d = re.search(r"(\d+)", base)
        base_chroma, base_depth = "rgb", int(d.group(1)) if d else 8

    depth = int(s.depth) if s.depth != "auto" else base_depth
    depth = max(8, min(depth, 12))
    chroma = s_chroma if s_chroma not in ("auto", None) else base_chroma

    if chroma == "rgb":
        if depth > 8:
            return f"gbrp{depth}le"
        return "gbrp"
    if depth > 8:
        return f"yuv{chroma}p{depth}le"
    return f"yuv{chroma}p"


def build_filters(s: Settings, info: Optional[MediaInfo], caps: Caps = None) -> FilterResult:
    """Build the ffmpeg -vf chain for the given settings and source info."""
    caps = caps or get_caps()
    preset = get_preset(s.preset)
    res = FilterResult()

    source_hdr = bool(info and info.hdr)
    # HDR intent
    res.hdr_expand = (not source_hdr) and s.hdr
    keep_hdr = source_hdr and s.tone_map != "hdr2sdr" and (preset.hdr_ready or preset.lossless or s.tone_map == "off")
    res.tonemap_down = source_hdr and not keep_hdr
    res.pix_fmt = resolve_pixfmt(preset, s, res.hdr_expand or (source_hdr and not res.tonemap_down), res.tonemap_down)

    f: list = []
    notes = res.notes

    # 1. deinterlace first
    if s.deinterlace:
        f.append("yadif=mode=1:parity=auto:deint=all")

    # 2. denoise
    if s.denoise:
        if s.denoiser == "nlmeans" and caps.has_filter("nlmeans"):
            # Use faster NLMeans settings: fewer patches, smaller research window
            p = 7 if s.denoise == 1 else 5  # fewer patches for higher levels
            r = 15 if s.denoise == 1 else 10  # smaller research window
            f.append(f"nlmeans=s={NLMEANS_LEVELS[s.denoise]}:p={p}:r={r}")
            if s.denoise >= 2:
                notes.append(f"NLMeans level {s.denoise} is slow (p={p}, r={r}) — consider hqdn3d for long videos or lower level.")
        else:
            if s.denoiser == "nlmeans" and not caps.has_filter("nlmeans"):
                notes.append("nlmeans unavailable in this ffmpeg build — using hqdn3d.")
            f.append(HQDN3D_LEVELS[s.denoise])

    # 3. deblock (before scaling — works on the compressed artifacts)
    if s.deblock:
        f.append("deblock=filter=weak:block=8")

    # 4. upscale
    target, desc = resolve_target(s, info)
    res.target_wh = target
    res.scale_desc = desc
    if target:
        w, h = target
        if s.scaler in ("xbr2", "xbr4"):
            if caps.has_filter("xbr") and info and info.width:
                factor = 2 if s.scaler == "xbr2" else 4
                f.append(f"xbr={factor}")
                notes.append(f"XBR {factor}x pixel-art scaler applied before final resize.")
            else:
                notes.append("xbr unavailable — using lanczos.")
        flag = SCALER_FLAGS.get(s.scaler if s.scaler in SCALER_FLAGS else "lanczos", "lanczos")
        kind, _ = s.parse_scale()
        if kind == "height":
            f.append(f"scale=-2:{h}:flags={flag}")
        else:
            f.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags={flag}")
        notes.append(f"Upscaled to {desc} with {flag}.")

    # 5. sharpen shaders
    if s.shader != "none" and s.sharpen > 0:
        if s.shader == "cas":
            if caps.has_filter("cas"):
                f.append(f"cas=strength={s.sharpen:.3f}")
            else:
                f.append(f"unsharp=5:5:{0.5 + s.sharpen * 1.5:.2f}:5:5:0.0")
                notes.append("cas filter unavailable — using unsharp instead.")
        else:
            f.append(f"unsharp=5:5:{0.5 + s.sharpen * 1.5:.2f}:5:5:0.0")

    # 6. deband
    if s.deband:
        f.append("deband=range=16:blur=1:coupling=0")

    # 7. color adjustments
    eq_parts = []
    if abs(s.contrast - 1.0) > 0.001:
        eq_parts.append(f"contrast={s.contrast:.3f}")
    if abs(s.brightness) > 0.001:
        eq_parts.append(f"brightness={s.brightness:.3f}")
    if abs(s.saturation - 1.0) > 0.001:
        eq_parts.append(f"saturation={s.saturation:.3f}")
    if abs(s.gamma - 1.0) > 0.001:
        eq_parts.append(f"gamma={s.gamma:.3f}")
    if eq_parts:
        f.append("eq=" + ":".join(eq_parts))

    # 8. film grain
    if s.grain:
        f.append(f"noise=alls={s.grain}:allf=t+u")

    # 9. frame rate
    tfps = s.target_fps()
    if tfps:
        if s.motion_interp and caps.has_filter("minterpolate"):
            # Use faster motion interpolation settings
            f.append(f"minterpolate=fps={tfps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:me=ntss")
            notes.append(f"Motion interpolation to {tfps}fps is very slow — consider using without --motion-interp for 10-50x faster encoding.")
        elif s.motion_interp and not caps.has_filter("minterpolate"):
            f.append(f"fps={tfps}")
            notes.append("minterpolate unavailable — using plain fps change.")
        else:
            f.append(f"fps={tfps}")

    # 10. HDR / tone mapping
    has_z = caps.has_filter("zscale") and caps.has_filter("tonemap")
    # Untagged sources make zimg refuse conversions ("no path between colorspaces")
    src_trc = (info.color_transfer if info else "") or ""
    src_pri = (info.color_primaries if info else "") or ""
    need_tags = bool(info) and (not src_trc or not src_pri)
    tag_sdr = ("setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
               if need_tags else "")

    if res.hdr_expand:
        if has_z:
            if tag_sdr:
                f.append(tag_sdr)
            f += [
                "format=gbrpf32le",
                "zscale=t=linear:npl=100",
                "zscale=p=bt2020",
                "tonemap=tonemap=hable:desat=0",
                "zscale=t=smpte2084:m=bt2020nc:r=tv",
            ]
            notes.append("SDR expanded to 10-bit BT.2020 PQ (HDR container). Result depends on the display.")
        else:
            notes.append("zscale/tonemap unavailable — HDR output uses 10-bit + metadata signaling only (approximate).")

    if res.tonemap_down:
        if has_z:
            if need_tags:
                f.append("setparams=range=tv:color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc")
            f += [
                "format=gbrpf32le",
                "zscale=t=linear:npl=100",
                "zscale=p=bt709",
                "tonemap=tonemap=hable:desat=0",
                "zscale=t=bt709:m=bt709:r=tv",
            ]
        else:
            f += ["format=yuv420p10le", "tonemap=tonemap=hable:desat=0"]
        notes.append("HDR source tone-mapped down to SDR (BT.709).")

    # 11. final pixel format
    f.append(f"format={res.pix_fmt}")

    res.filters = f
    return res
