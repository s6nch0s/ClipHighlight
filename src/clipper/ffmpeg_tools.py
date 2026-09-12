from __future__ import annotations

import shutil
import subprocess

from .errors import FFmpegError

REQUIRED_TOOLS = ("ffmpeg", "ffprobe")


def require_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        raise FFmpegError(
            f"Required tool(s) not found on PATH: {', '.join(missing)}. "
            "Install FFmpeg (brew install ffmpeg / winget install ffmpeg)."
        )


def run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError as exc:  # tool vanished between check and call
        raise FFmpegError(str(exc)) from exc
    if proc.returncode != 0:
        raise FFmpegError(
            f"Command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}"
        )
    return proc
