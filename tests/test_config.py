from pathlib import Path

import pytest

from clipper.config import load_config
from clipper.errors import ConfigError

VALID = """
input: "source.mp4"
output_dir: "./out"
clips:
  max_clips: 5
  min_len: 30
  max_len: 60
frame:
  width: 1080
  height: 1920
  crop_style: blur_bars
  blur_strength: 20
logo:
  path: "./assets/mw4_logo.png"
  corner: top_right
  scale: 0.18
  margin: 40
on_screen_text:
  text: "MW4 Open Beta This Weekend"
  font: "./assets/fonts/font.ttf"
  font_size: 64
  color: white
  position: top
  margin: 120
analyze:
  detector: heuristic
  audio_weight: 0.6
  motion_weight: 0.4
encode:
  crf: 19
  preset: medium
"""


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_valid_config(tmp_path):
    cfg = load_config(_write(tmp_path, VALID))
    assert cfg.frame.width == 1080
    assert cfg.frame.height == 1920
    assert cfg.clips.max_clips == 5
    assert cfg.logo.corner == "top_right"
    assert isinstance(cfg.input, Path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_invalid_corner_raises(tmp_path):
    bad = VALID.replace("corner: top_right", "corner: middle")
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))


def test_min_greater_than_max_raises(tmp_path):
    bad = VALID.replace("min_len: 30", "min_len: 90")
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))


@pytest.mark.parametrize(
    "old, new",
    [
        ("crop_style: blur_bars", "crop_style: diagonal"),
        ("position: top", "position: center"),
        ("max_clips: 5", "max_clips: 0"),
        ("min_len: 30", "min_len: 5"),
        ("audio_weight: 0.6", "audio_weight: 1.5"),
        ("motion_weight: 0.4", "motion_weight: -0.1"),
        ("max_clips: 5", "max_clips: abc"),
    ],
)
def test_invalid_config_raises(tmp_path, old, new):
    bad = VALID.replace(old, new)
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))
