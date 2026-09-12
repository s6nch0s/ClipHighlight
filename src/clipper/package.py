from __future__ import annotations

import json
from pathlib import Path

from .config import Config
from .errors import ComplianceError
from .ingest import SourceMeta

PREORDER_PHRASE = "Pre-order Modern Warfare 4 today and play day one, October 23rd"
FTC_LINE = "#Ad"
CALLOUTS = "@callofduty"
BASE_BODY = f"Modern Warfare 4 Multiplayer Beta Gameplay — MW4 Open Beta This Weekend {CALLOUTS}"


def build_caption(extra_hashtags: list[str]) -> str:
    if len(extra_hashtags) > 3:
        raise ComplianceError("At most 3 extra hashtags are allowed.")
    for tag in extra_hashtags:
        if not tag.startswith("#"):
            raise ComplianceError(f"Hashtag must start with '#': {tag!r}")
    body = BASE_BODY
    if extra_hashtags:
        body = f"{body} {' '.join(extra_hashtags)}"
    return f"{PREORDER_PHRASE}\n\n{FTC_LINE}\n{body}\n"


def write_captions(cfg: Config, selection: list[dict], extra_hashtags: list[str]) -> list[Path]:
    caption = build_caption(extra_hashtags)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for item in selection:
        p = cfg.output_dir / f"clip_{item['index']:02d}_caption.txt"
        p.write_text(caption, encoding="utf-8")
        paths.append(p)
    return paths


def write_manifest(
    cfg: Config,
    source: SourceMeta,
    selection: list[dict],
    clip_paths: list[Path],
    caption_paths: list[Path],
) -> Path:
    clips = []
    for item, clip, cap in zip(selection, clip_paths, caption_paths):
        clips.append({
            "index": item["index"],
            "start": item["start"],
            "end": item["end"],
            "length": round(item["end"] - item["start"], 3),
            "score": item["score"],
            "clip": clip.name,
            "caption": cap.name,
        })
    manifest = {
        "source": str(source.path),
        "source_duration": source.duration,
        "clips": clips,
    }
    out_path = cfg.output_dir / "manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path
