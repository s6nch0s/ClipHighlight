from pathlib import Path

import json

import pytest

from clipper.errors import FFmpegError
from clipper.ffmpeg_tools import run
from clipper.ingest import _parse_fps, probe


class _FakeProc:
    def __init__(self, stdout):
        self.stdout = stdout


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


@pytest.mark.parametrize(
    "rate, expected",
    [
        ("30/1", 30.0),
        ("0/0", 0.0),
        ("0/1", 0.0),
        ("", 0.0),
        ("60000/1001", pytest.approx(59.94, rel=1e-3)),
    ],
)
def test_parse_fps(rate, expected):
    assert _parse_fps(rate) == expected


def test_probe_valid_media(tmp_path: Path, monkeypatch):
    src = tmp_path / "sample.mp4"
    src.touch()
    payload = json.dumps({
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30/1",
            },
            {"codec_type": "audio"},
        ],
        "format": {"duration": "12.0"},
    })
    monkeypatch.setattr("clipper.ingest.run", lambda args: _FakeProc(payload))

    meta = probe(src)
    assert meta.width == 1920
    assert meta.height == 1080
    assert meta.fps == 30.0
    assert meta.has_audio is True
    assert meta.duration == 12.0


def test_probe_no_video_stream_raises(tmp_path: Path, monkeypatch):
    src = tmp_path / "sample.mp4"
    src.touch()
    payload = json.dumps({
        "streams": [{"codec_type": "audio"}],
        "format": {"duration": "12.0"},
    })
    monkeypatch.setattr("clipper.ingest.run", lambda args: _FakeProc(payload))

    with pytest.raises(FFmpegError):
        probe(src)


def test_probe_missing_dimensions_raises(tmp_path: Path, monkeypatch):
    src = tmp_path / "sample.mp4"
    src.touch()
    payload = json.dumps({
        "streams": [{"codec_type": "video", "avg_frame_rate": "30/1"}],
        "format": {"duration": "12.0"},
    })
    monkeypatch.setattr("clipper.ingest.run", lambda args: _FakeProc(payload))

    with pytest.raises(FFmpegError):
        probe(src)
