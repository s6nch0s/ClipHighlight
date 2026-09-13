from __future__ import annotations

import warnings
from pathlib import Path

from .config import Config
from .ffmpeg_tools import run
from .ingest import SourceMeta

_CORNER_POS = {
    "top_left": ("{m}", "{m}"),
    "top_right": ("W-w-{m}", "{m}"),
    "bottom_left": ("{m}", "H-h-{m}"),
    "bottom_right": ("W-w-{m}", "H-h-{m}"),
}


def escape_drawtext_text(text: str) -> str:
    out = text.replace("\\", "\\\\")
    out = out.replace("%", "\\%")
    out = out.replace("'", "'\\''")
    return out


def escape_filter_path(path: Path) -> str:
    # Used inside single-quoted FFmpeg filter option values, e.g. fontfile='...'.
    # Escape the Windows drive colon so the filter parser does not treat it as an
    # option separator. Normalize separators and escape literal single quotes.
    s = str(path).replace("\\", "/")
    s = s.replace(":", "\\:")
    return s.replace("'", "'\\''")


def _drawtext(cfg: Config) -> str:
    t = cfg.on_screen_text
    parts = [
        f"text='{escape_drawtext_text(t.text)}'",
        f"fontsize={t.font_size}",
        f"fontcolor={t.color}",
        "x=(w-text_w)/2",
        (f"y={t.margin}" if t.position == "top" else f"y=h-text_h-{t.margin}"),
        "box=1",
        "boxcolor=black@0.4",
        "boxborderw=20",
    ]
    if t.font is not None:
        parts.insert(1, f"fontfile='{escape_filter_path(t.font)}'")
    return "drawtext=" + ":".join(parts)


def _grade_filter(cfg: Config) -> str:
    # Colour pop + vignette on the gameplay composite, applied BEFORE the logo and
    # text overlays so branding colours stay accurate and legible.
    v = cfg.vfx
    if not v.enabled:
        return ""
    parts = []
    if v.saturation != 1.0 or v.contrast != 1.0:
        parts.append(f"eq=saturation={v.saturation:g}:contrast={v.contrast:g}")
    if v.vignette:
        parts.append("vignette=angle=PI/4")
    return ",".join(parts)


def _zoom_filter(cfg: Config, duration: float | None, fps: float | None) -> str:
    # Slow centred push-in on the gameplay composite, applied BEFORE overlays so the
    # logo and text stay rock-steady while the footage pushes in.
    v = cfg.vfx
    if not v.enabled or v.zoom <= 0 or not duration or not fps:
        return ""
    w, h = cfg.frame.width, cfg.frame.height
    zmax = 1.0 + v.zoom
    total = max(int(round(duration * fps)), 1)
    inc = (zmax - 1.0) / total
    # Pre-scale gives the crop-in resolution headroom (no upscaling blur) and tames
    # zoompan jitter; commas inside the quoted expressions are shielded from the
    # filtergraph parser by the single quotes.
    pw = (int(w * 3 // 2)) // 2 * 2
    ph = (int(h * 3 // 2)) // 2 * 2
    return (
        f"scale={pw}:{ph},"
        f"zoompan=z='min(zoom+{inc:.6f},{zmax:.4f})':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps={fps:g}:s={w}x{h}"
    )


def _fade_filter(cfg: Config, duration: float | None) -> str:
    v = cfg.vfx
    if not v.enabled or v.fade <= 0 or not duration:
        return ""
    out_st = max(duration - v.fade, 0.0)
    return f"fade=t=in:st=0:d={v.fade:g},fade=t=out:st={out_st:.3f}:d={v.fade:g}"


def build_filtergraph(
    cfg: Config,
    *,
    use_logo: bool,
    duration: float | None = None,
    fps: float | None = None,
) -> str:
    w, h = cfg.frame.width, cfg.frame.height
    blur = cfg.frame.blur_strength
    steps = [
        "[0:v]split=2[bg][fg]",
        f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},boxblur={blur}[bgb]",
        f"[fg]scale={w}:-2[fgs]",
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2[framed]",
    ]
    current = "framed"
    grade = _grade_filter(cfg)
    if grade:
        steps.append(f"[{current}]{grade}[graded]")
        current = "graded"
    zoom = _zoom_filter(cfg, duration, fps)
    if zoom:
        steps.append(f"[{current}]{zoom}[zoomed]")
        current = "zoomed"
    if use_logo:
        x_expr, y_expr = _CORNER_POS[cfg.logo.corner]
        m = cfg.logo.margin
        lw = int(round(cfg.logo.scale * w))
        steps.append(f"[1:v]scale={lw}:-1[logo]")
        steps.append(
            f"[{current}][logo]overlay="
            f"{x_expr.format(m=m)}:{y_expr.format(m=m)}[logo_ov]"
        )
        current = "logo_ov"
    fade = _fade_filter(cfg, duration)
    tail = f"{_drawtext(cfg)},{fade}" if fade else _drawtext(cfg)
    steps.append(f"[{current}]{tail}[v]")
    return ";".join(steps)


def build_render_command(
    cfg: Config,
    source: Path,
    start: float,
    end: float,
    out_path: Path,
    *,
    use_logo: bool,
    fps: float | None = None,
) -> list[str]:
    args = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source)]
    if use_logo and cfg.logo.path is not None:
        args += ["-i", str(cfg.logo.path)]
    args += [
        "-filter_complex",
        build_filtergraph(cfg, use_logo=use_logo, duration=end - start, fps=fps),
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-crf", str(cfg.encode.crf),
        "-preset", cfg.encode.preset,
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(out_path),
    ]
    return args


def render_all(cfg: Config, source: SourceMeta, selection: list[dict]) -> list[Path]:
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    use_logo = cfg.logo.path is not None and cfg.logo.path.is_file()
    if cfg.logo.path is not None and not use_logo:
        warnings.warn(
            f"Logo file missing: {cfg.logo.path}. Rendering without logo (NON-COMPLIANT).",
            stacklevel=2,
        )
    out_paths: list[Path] = []
    for item in selection:
        out_path = cfg.output_dir / f"clip_{item['index']:02d}.mp4"
        run(build_render_command(cfg, source.path, item["start"], item["end"], out_path, use_logo=use_logo, fps=source.fps))
        out_paths.append(out_path)
    return out_paths
