from pathlib import Path

import pytest

from clipper.errors import FFmpegError
from clipper.ffmpeg_tools import run
from clipper.ingest import probe


@pytest.mark.integration
def test_probe_reads_synthetic_media(tmp_path: Path):
    src = tmp_path / "sample.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(src),
    ])
    meta = probe(src)
    assert meta.width == 1280
    assert meta.height == 720
    assert meta.has_audio is True
    assert 1.5 <= meta.duration <= 2.5
    assert 25 <= meta.fps <= 35


def test_probe_missing_file_raises(tmp_path: Path):
    with pytest.raises(FFmpegError):
        probe(tmp_path / "does_not_exist.mp4")
