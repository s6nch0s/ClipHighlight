from pathlib import Path

import pytest

from clipper.cli import run_pipeline
from clipper.errors import ComplianceError
from tests.test_config import VALID


def _config(tmp_path, src_line, out_dir, text_override=None):
    text = VALID.replace('input: "source.mp4"', f'input: "{src_line}"')
    text = text.replace('output_dir: "./out"', f'output_dir: "{out_dir}"')
    text = text.replace('font: "./assets/fonts/font.ttf"', "font: null")
    if text_override:
        text = text.replace('text: "MW4 Open Beta This Weekend"', f'text: "{text_override}"')
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


@pytest.mark.integration
def test_run_pipeline_end_to_end(tmp_path):
    from clipper.ffmpeg_tools import run
    src = tmp_path / "src.mp4"
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=40",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=40",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(src),
    ])
    out_dir = tmp_path / "out"
    cfg_path = _config(tmp_path, src.as_posix(), out_dir.as_posix())
    manifest = run_pipeline(cfg_path, extra_hashtags=["#ModernWarfare4", "#COD"])
    assert manifest.is_file()
    assert list(out_dir.glob("clip_*.mp4"))
    assert list(out_dir.glob("clip_*_caption.txt"))


def test_run_pipeline_strict_refuses_bad_text(tmp_path):
    cfg_path = _config(tmp_path, "missing.mp4", (tmp_path / "out").as_posix(), text_override="just gameplay")
    with pytest.raises(ComplianceError):
        run_pipeline(cfg_path, strict=True)
