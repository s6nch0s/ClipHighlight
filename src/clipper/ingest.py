from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .errors import FFmpegError
from .ffmpeg_tools import run


@dataclass
class SourceMeta:
    path: Path
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool


def _parse_fps(rate: str) -> float:
    if not rate or rate == "0/0":
        return 0.0
    if "/" in rate:
        num, den = rate.split("/", 1)
        den_f = float(den)
        return float(num) / den_f if den_f else 0.0
    return float(rate)


def probe(video_path: Path) -> SourceMeta:
    video_path = Path(video_path)
    if not video_path.is_file():
        raise FFmpegError(f"Input video not found: {video_path}")
    proc = run([
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path),
    ])
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise FFmpegError(f"No video stream found in {video_path}")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    duration = float(data.get("format", {}).get("duration", 0.0) or 0.0)
    if duration <= 0.0:
        duration = float(video_stream.get("duration", 0.0) or 0.0)

    try:
        width = int(video_stream["width"])
        height = int(video_stream["height"])
    except (KeyError, TypeError, ValueError):
        raise FFmpegError(f"Video stream missing width/height in {video_path}")

    return SourceMeta(
        path=video_path,
        duration=duration,
        width=width,
        height=height,
        fps=_parse_fps(video_stream.get("avg_frame_rate", "0/0")),
        has_audio=has_audio,
    )


def ingest(cfg: Config) -> SourceMeta:
    return probe(cfg.input)
