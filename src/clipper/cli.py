from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

from .analyze import analyze
from .compliance import check_compliance
from .config import load_config
from .errors import ClipperError, ComplianceError
from .ffmpeg_tools import require_tools
from .ingest import ingest
from .package import write_captions, write_manifest
from .render import render_all
from .select import select_windows


def run_pipeline(
    config_path: Path,
    *,
    extra_hashtags: list[str] | None = None,
    strict: bool = False,
) -> Path:
    cfg = load_config(config_path)

    report = check_compliance(cfg)
    for warn in report.warnings:
        warnings.warn(warn, stacklevel=2)
    if report.errors:
        message = "Compliance errors:\n- " + "\n- ".join(report.errors)
        if strict:
            raise ComplianceError(message)
        warnings.warn(message, stacklevel=2)

    require_tools()
    source = ingest(cfg)

    analysis_path = analyze(cfg, source)
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    selection = select_windows(
        analysis["points"],
        step=analysis["step"],
        video_duration=source.duration,
        min_len=cfg.clips.min_len,
        max_len=cfg.clips.max_len,
        max_clips=cfg.clips.max_clips,
    )
    (cfg.output_dir / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")

    clip_paths = render_all(cfg, source, selection)
    caption_paths = write_captions(cfg, selection, extra_hashtags or [])
    return write_manifest(cfg, source, selection, clip_paths, caption_paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MW4 gameplay clip automation")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--hashtags", default="", help="Comma-separated extra hashtags (max 3), e.g. '#COD,#MW4'"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Refuse to render when compliance errors exist"
    )
    args = parser.parse_args(argv)

    extra = [h.strip() for h in args.hashtags.split(",") if h.strip()]
    try:
        manifest = run_pipeline(Path(args.config), extra_hashtags=extra, strict=args.strict)
    except ClipperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Done. Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
