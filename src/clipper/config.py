from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .errors import ConfigError

VALID_CORNERS = {"top_left", "top_right", "bottom_left", "bottom_right"}
VALID_CROP_STYLES = {"blur_bars", "center_crop"}
VALID_TEXT_POSITIONS = {"top", "bottom"}


@dataclass
class ClipsConfig:
    max_clips: int
    min_len: float
    max_len: float


@dataclass
class FrameConfig:
    width: int
    height: int
    crop_style: str
    blur_strength: int


@dataclass
class LogoConfig:
    path: Path | None
    corner: str
    scale: float
    margin: int


@dataclass
class OnScreenTextConfig:
    text: str
    font: Path | None
    font_size: int
    color: str
    position: str
    margin: int


@dataclass
class AnalyzeConfig:
    detector: str
    audio_weight: float
    motion_weight: float


@dataclass
class EncodeConfig:
    crf: int
    preset: str


@dataclass
class Config:
    input: Path
    output_dir: Path
    clips: ClipsConfig
    frame: FrameConfig
    logo: LogoConfig
    on_screen_text: OnScreenTextConfig
    analyze: AnalyzeConfig
    encode: EncodeConfig


def _require(mapping: dict, key: str, section: str):
    if key not in mapping:
        raise ConfigError(f"Missing required key '{section}.{key}'")
    return mapping[key]


def _opt_path(value) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value))


def load_config(path: Path) -> Config:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Could not parse YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping")

    clips_raw = _require(raw, "clips", "root")
    frame_raw = _require(raw, "frame", "root")
    logo_raw = _require(raw, "logo", "root")
    text_raw = _require(raw, "on_screen_text", "root")
    analyze_raw = _require(raw, "analyze", "root")
    encode_raw = _require(raw, "encode", "root")

    clips = ClipsConfig(
        max_clips=int(_require(clips_raw, "max_clips", "clips")),
        min_len=float(_require(clips_raw, "min_len", "clips")),
        max_len=float(_require(clips_raw, "max_len", "clips")),
    )
    frame = FrameConfig(
        width=int(_require(frame_raw, "width", "frame")),
        height=int(_require(frame_raw, "height", "frame")),
        crop_style=str(_require(frame_raw, "crop_style", "frame")),
        blur_strength=int(_require(frame_raw, "blur_strength", "frame")),
    )
    logo = LogoConfig(
        path=_opt_path(logo_raw.get("path")),
        corner=str(_require(logo_raw, "corner", "logo")),
        scale=float(_require(logo_raw, "scale", "logo")),
        margin=int(_require(logo_raw, "margin", "logo")),
    )
    text = OnScreenTextConfig(
        text=str(_require(text_raw, "text", "on_screen_text")),
        font=_opt_path(text_raw.get("font")),
        font_size=int(_require(text_raw, "font_size", "on_screen_text")),
        color=str(_require(text_raw, "color", "on_screen_text")),
        position=str(_require(text_raw, "position", "on_screen_text")),
        margin=int(_require(text_raw, "margin", "on_screen_text")),
    )
    analyze = AnalyzeConfig(
        detector=str(_require(analyze_raw, "detector", "analyze")),
        audio_weight=float(_require(analyze_raw, "audio_weight", "analyze")),
        motion_weight=float(_require(analyze_raw, "motion_weight", "analyze")),
    )
    encode = EncodeConfig(
        crf=int(_require(encode_raw, "crf", "encode")),
        preset=str(_require(encode_raw, "preset", "encode")),
    )

    cfg = Config(
        input=Path(str(_require(raw, "input", "root"))),
        output_dir=Path(str(_require(raw, "output_dir", "root"))),
        clips=clips,
        frame=frame,
        logo=logo,
        on_screen_text=text,
        analyze=analyze,
        encode=encode,
    )
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if cfg.logo.corner not in VALID_CORNERS:
        raise ConfigError(f"logo.corner must be one of {sorted(VALID_CORNERS)}")
    if cfg.frame.crop_style not in VALID_CROP_STYLES:
        raise ConfigError(f"frame.crop_style must be one of {sorted(VALID_CROP_STYLES)}")
    if cfg.on_screen_text.position not in VALID_TEXT_POSITIONS:
        raise ConfigError(f"on_screen_text.position must be one of {sorted(VALID_TEXT_POSITIONS)}")
    if cfg.clips.min_len > cfg.clips.max_len:
        raise ConfigError("clips.min_len must be <= clips.max_len")
    if cfg.clips.min_len < 10:
        raise ConfigError("clips.min_len must be >= 10 (campaign hard floor)")
    if cfg.clips.max_clips < 1:
        raise ConfigError("clips.max_clips must be >= 1")
    if not (0.0 <= cfg.analyze.audio_weight <= 1.0):
        raise ConfigError("analyze.audio_weight must be in [0, 1]")
    if not (0.0 <= cfg.analyze.motion_weight <= 1.0):
        raise ConfigError("analyze.motion_weight must be in [0, 1]")
