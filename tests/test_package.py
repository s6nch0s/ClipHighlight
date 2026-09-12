import json
from pathlib import Path

import pytest

from clipper.config import load_config
from clipper.errors import ComplianceError
from clipper.ingest import SourceMeta
from clipper.package import (
    CALLOUTS,
    FTC_LINE,
    PREORDER_PHRASE,
    build_caption,
    write_captions,
    write_manifest,
)
from tests.test_config import VALID


def test_caption_contains_exact_phrase_first():
    caption = build_caption(["#ModernWarfare4", "#COD"])
    lines = caption.splitlines()
    assert lines[0] == PREORDER_PHRASE


def test_ftc_line_is_alone_and_first_hashtag():
    caption = build_caption(["#ModernWarfare4"])
    lines = [ln for ln in caption.splitlines()]
    ftc_idx = lines.index(FTC_LINE)
    # FTC on its own line
    assert lines[ftc_idx].strip() == FTC_LINE
    # no hashtag appears before the FTC line
    before = "\n".join(lines[:ftc_idx])
    assert "#" not in before


def test_caption_contains_callouts():
    caption = build_caption([])
    assert CALLOUTS in caption


def test_too_many_hashtags_raises():
    with pytest.raises(ComplianceError):
        build_caption(["#a", "#b", "#c", "#d"])


def test_hashtag_without_hash_raises():
    with pytest.raises(ComplianceError):
        build_caption(["ModernWarfare4"])


def _cfg(tmp_path):
    text = VALID.replace('output_dir: "./out"', f'output_dir: "{(tmp_path / "out").as_posix()}"')
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return load_config(p)


def test_build_caption_allows_exactly_three_hashtags():
    caption = build_caption(["#a", "#b", "#c"])
    assert isinstance(caption, str)
    assert "#a" in caption
    assert "#b" in caption
    assert "#c" in caption


def test_write_captions_names_and_content(tmp_path):
    cfg = _cfg(tmp_path)
    selection = [
        {"index": 1, "start": 0.0, "end": 30.0, "score": 0.9},
        {"index": 2, "start": 40.0, "end": 70.0, "score": 0.8},
    ]
    extra = ["#COD"]
    paths = write_captions(cfg, selection, extra)
    assert len(paths) == 2
    assert paths[0].name == "clip_01_caption.txt"
    assert paths[1].name == "clip_02_caption.txt"
    expected = build_caption(extra)
    for p in paths:
        assert p.exists()
        assert p.read_text(encoding="utf-8") == expected


def test_write_manifest_fields(tmp_path):
    cfg = _cfg(tmp_path)
    selection = [
        {"index": 1, "start": 0.0, "end": 30.0, "score": 0.9},
        {"index": 2, "start": 40.0, "end": 70.0, "score": 0.8},
    ]
    source = SourceMeta(
        path=Path("/tmp/src.mp4"),
        duration=240.0,
        width=1920,
        height=1080,
        fps=30.0,
        has_audio=True,
    )
    clip_paths = [cfg.output_dir / "clip_01.mp4", cfg.output_dir / "clip_02.mp4"]
    caption_paths = [
        cfg.output_dir / "clip_01_caption.txt",
        cfg.output_dir / "clip_02_caption.txt",
    ]
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = write_manifest(cfg, source, selection, clip_paths, caption_paths)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "source" in data
    assert data["source_duration"] == 240.0
    assert len(data["clips"]) == 2
    first = data["clips"][0]
    assert first["index"] == 1
    assert first["length"] == 30.0
    assert first["clip"] == "clip_01.mp4"
    assert first["caption"] == "clip_01_caption.txt"
