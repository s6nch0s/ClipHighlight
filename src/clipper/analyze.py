from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .config import Config
from .errors import ConfigError
from .ffmpeg_tools import run
from .ingest import SourceMeta

SAMPLE_STEP = 1.0


def _escape_lavfi_path(path) -> str:
    # lavfi movie/amovie filename arg: normalize to '/' then escape graph metacharacters
    # (notably the Windows drive-colon, which otherwise splits filter options).
    s = str(path).replace("\\", "/")
    for ch in (":", "'", ",", "[", "]", ";"):
        s = s.replace(ch, "\\" + ch)
    return f"'{s}'"


def combine_scores(audio: float, motion: float, audio_weight: float, motion_weight: float) -> float:
    total = audio_weight + motion_weight
    if total <= 0.0:
        return 0.0
    value = (audio * audio_weight + motion * motion_weight) / total
    return max(0.0, min(1.0, value))


def normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo <= 1e-12:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


class Detector(Protocol):
    def score(self, source: SourceMeta, cfg: Config) -> list[dict]:
        ...


class HeuristicDetector:
    def score(self, source: SourceMeta, cfg: Config) -> list[dict]:
        n = max(1, int(source.duration // SAMPLE_STEP))
        times = [i * SAMPLE_STEP for i in range(n)]
        audio_raw = self._audio_loudness(source, times) if source.has_audio else [0.0] * n
        motion_raw = self._motion_energy(source, times)
        audio = normalize(audio_raw)
        motion = normalize(motion_raw)
        points = []
        for i, t in enumerate(times):
            combined = combine_scores(
                audio[i], motion[i], cfg.analyze.audio_weight, cfg.analyze.motion_weight
            )
            points.append({
                "t": round(t, 3),
                "audio_score": round(audio[i], 6),
                "motion_score": round(motion[i], 6),
                "combined": round(combined, 6),
            })
        return points

    def _audio_loudness(self, source: SourceMeta, times: list[float]) -> list[float]:
        # Per-second RMS via astats, one value per frame; bucket into SAMPLE_STEP bins.
        proc = run([
            "ffprobe", "-v", "error", "-f", "lavfi",
            "-i", f"amovie={_escape_lavfi_path(source.path)},astats=metadata=1:reset=1",
            "-show_entries", "frame=pkt_pts_time:frame_tags=lavfi.astats.Overall.RMS_level",
            "-print_format", "json",
        ])
        return self._bucket_rms(proc.stdout, times)

    def _bucket_rms(self, ffprobe_json: str, times: list[float]) -> list[float]:
        data = json.loads(ffprobe_json or "{}")
        buckets = [[] for _ in times]
        for frame in data.get("frames", []):
            t = float(frame.get("pkt_pts_time", frame.get("pts_time", 0.0)) or 0.0)
            tags = frame.get("tags", {})
            rms_db = tags.get("lavfi.astats.Overall.RMS_level")
            if rms_db in (None, "-inf"):
                continue
            idx = int(t // SAMPLE_STEP)
            if 0 <= idx < len(buckets):
                buckets[idx].append(float(rms_db))
        # RMS level is negative dB (louder = closer to 0); use mean, default very quiet.
        return [ (sum(b) / len(b)) if b else -90.0 for b in buckets ]

    def _motion_energy(self, source: SourceMeta, times: list[float]) -> list[float]:
        proc = run([
            "ffprobe", "-v", "error", "-f", "lavfi",
            "-i", f"movie={_escape_lavfi_path(source.path)},select=gt(scene\\,0)",
            "-show_entries", "frame=pkt_pts_time:frame_tags=lavfi.scene_score",
            "-print_format", "json",
        ])
        return self._bucket_scene(proc.stdout, times)

    def _bucket_scene(self, ffprobe_json: str, times: list[float]) -> list[float]:
        data = json.loads(ffprobe_json or "{}")
        buckets = [0.0 for _ in times]
        for frame in data.get("frames", []):
            t = float(frame.get("pkt_pts_time", frame.get("pts_time", 0.0)) or 0.0)
            score = frame.get("tags", {}).get("lavfi.scene_score")
            if score is None:
                continue
            idx = int(t // SAMPLE_STEP)
            if 0 <= idx < len(buckets):
                buckets[idx] = max(buckets[idx], float(score))
        return buckets


def get_detector(name: str) -> Detector:
    if name == "heuristic":
        return HeuristicDetector()
    if name == "ai":
        raise ConfigError(
            "analyze.detector 'ai' is a documented future stage and is not implemented in v1. "
            "Use 'heuristic'."
        )
    raise ConfigError(f"Unknown analyze.detector: {name!r}")


def analyze(cfg: Config, source: SourceMeta) -> Path:
    detector = get_detector(cfg.analyze.detector)
    points = detector.score(source, cfg)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.output_dir / "analysis.json"
    out_path.write_text(
        json.dumps({"step": SAMPLE_STEP, "points": points}, indent=2),
        encoding="utf-8",
    )
    return out_path
