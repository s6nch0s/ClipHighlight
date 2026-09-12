from pathlib import Path

import pytest

from clipper.config import load_config
from clipper.ffmpeg_tools import run
from clipper.ingest import probe
from clipper.render import (
    build_filtergraph,
    build_render_command,
    escape_drawtext_text,
    escape_filter_path,
    render_all,
)
from tests.test_config import VALID


def _cfg(tmp_path, text=VALID):
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return load_config(p)


def test_escape_drawtext_produces_ffmpeg_valid_quoting():
    out = escape_drawtext_text("It's 100%")
    assert "'\\''" in out           # apostrophe uses close/reopen pattern, not backslash-quote
    assert "\\%" in out             # percent escaped for drawtext expansion
    assert "\\'" not in out.replace("'\\''", "")  # no bare backslash-quote escaping remains


def test_escape_filter_path_handles_windows_drive():
    out = escape_filter_path(Path("C:/fonts/a.ttf"))
    assert "C\\:" in out
    assert "\\\\" not in out or "/" in out  # backslashes converted/escaped, no raw drive colon


def test_filtergraph_targets_1080x1920_and_final_label():
    cfg = _cfg_no_font()
    fg = build_filtergraph(cfg, use_logo=False)
    assert "1080:1920" in fg or "1080" in fg and "1920" in fg
    assert fg.strip().endswith("[v]")


def test_render_command_includes_encode_settings(tmp_path):
    cfg = _cfg(tmp_path)
    cmd = build_render_command(cfg, Path("in.mp4"), 5.0, 20.0, tmp_path / "clip_01.mp4", use_logo=False)
    assert "-crf" in cmd and "19" in cmd
    assert "libx264" in cmd
    assert "+faststart" in cmd
    assert "-ss" in cmd and "-to" in cmd
    assert "-map" in cmd
    assert "0:a?" in cmd
    assert "aac" in cmd


@pytest.mark.integration
def test_render_all_produces_vertical_clip(tmp_path):
    src = tmp_path / "src.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=6",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(src),
    ])
    text = VALID.replace('input: "source.mp4"', f'input: "{src.as_posix()}"')
    text = text.replace('output_dir: "./out"', f'output_dir: "{(tmp_path / "out").as_posix()}"')
    # no font file present -> render must omit fontfile gracefully
    text = text.replace('font: "./assets/fonts/font.ttf"', "font: null")
    cfg = _cfg(tmp_path, text)
    meta = probe(src)
    selection = [{"index": 1, "start": 0.0, "end": 4.0, "score": 1.0}]
    out_paths = render_all(cfg, meta, selection)
    assert len(out_paths) == 1 and out_paths[0].is_file()
    out_meta = probe(out_paths[0])
    assert (out_meta.width, out_meta.height) == (1080, 1920)
    assert out_meta.has_audio is True


def _cfg_no_font():
    import tempfile
    d = Path(tempfile.mkdtemp())
    text = VALID.replace('font: "./assets/fonts/font.ttf"', "font: null")
    p = d / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return load_config(p)
