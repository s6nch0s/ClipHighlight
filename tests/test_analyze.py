import json
from pathlib import Path

import pytest

from clipper.analyze import (
    SAMPLE_STEP,
    HeuristicDetector,
    _escape_lavfi_path,
    analyze,
    combine_scores,
    get_detector,
    normalize,
)
from clipper.config import load_config
from clipper.errors import ConfigError
from clipper.ffmpeg_tools import run
from clipper.ingest import probe
from tests.test_config import VALID


def test_combine_scores_weighted_average():
    assert combine_scores(1.0, 0.0, 0.6, 0.4) == pytest.approx(0.6)
    assert combine_scores(0.0, 1.0, 0.6, 0.4) == pytest.approx(0.4)
    assert combine_scores(1.0, 1.0, 0.6, 0.4) == pytest.approx(1.0)


def test_combine_scores_zero_weights_returns_zero():
    assert combine_scores(1.0, 1.0, 0.0, 0.0) == 0.0


def test_normalize_scales_to_unit_range():
    assert normalize([10.0, 20.0, 30.0]) == [0.0, 0.5, 1.0]


def test_normalize_all_equal_returns_zeros():
    assert normalize([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]


def test_get_detector_heuristic():
    assert isinstance(get_detector("heuristic"), HeuristicDetector)


def test_get_detector_ai_not_implemented():
    with pytest.raises(ConfigError):
        get_detector("ai")


def test_get_detector_unknown():
    with pytest.raises(ConfigError):
        get_detector("bogus")


def test_escape_lavfi_path_windows_drive_colon():
    result = _escape_lavfi_path(Path("C:/Users/a/clip.mp4"))
    assert "C\\:/Users/a/clip.mp4" in result


def test_escape_lavfi_path_windows_backslashes():
    result = _escape_lavfi_path("C:\\vids\\clip.mp4")
    assert "C\\:/vids/clip.mp4" in result


def test_escape_lavfi_path_comma():
    result = _escape_lavfi_path("/tmp/a,b/clip.mp4")
    assert "\\," in result


@pytest.mark.integration
def test_analyze_writes_schema(tmp_path):
    src = tmp_path / "src.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=4",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(src),
    ])
    text = VALID.replace('input: "source.mp4"', f'input: "{src.as_posix()}"')
    text = text.replace('output_dir: "./out"', f'output_dir: "{(tmp_path / "out").as_posix()}"')
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(text, encoding="utf-8")
    cfg = load_config(cfg_path)
    out = analyze(cfg, probe(src))
    data = json.loads(Path(out).read_text(encoding="utf-8"))
    assert data["step"] == SAMPLE_STEP
    assert data["points"], "expected non-empty points"
    p0 = data["points"][0]
    assert set(p0.keys()) == {"t", "audio_score", "motion_score", "combined"}
    assert all(0.0 <= p["combined"] <= 1.0 for p in data["points"])
