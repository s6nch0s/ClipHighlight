from __future__ import annotations

HARD_FLOOR = 10.0


def _mean_score(points: list[dict], start: float, end: float) -> float:
    vals = [p["combined"] for p in points if start <= p["t"] < end]
    return sum(vals) / len(vals) if vals else 0.0


def select_windows(
    points: list[dict],
    *,
    step: float,
    video_duration: float,
    min_len: float,
    max_len: float,
    max_clips: int,
) -> list[dict]:
    window_len = min(max_len, video_duration)
    if window_len < HARD_FLOOR:
        return []
    # If the whole video is shorter than min_len, allow one floor-length window.
    effective_min = min(min_len, window_len)

    candidates = []
    start = 0.0
    last_start = max(0.0, video_duration - window_len)
    while start <= last_start + 1e-9:
        end = min(start + window_len, video_duration)
        if end - start >= max(HARD_FLOOR, effective_min) - 1e-9:
            candidates.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "score": _mean_score(points, start, end),
            })
        start += step

    # Rank by score so genuine highlights win, then fill up to max_clips with the
    # best remaining non-overlapping windows — calmer footage still yields clips.
    candidates.sort(key=lambda c: (-c["score"], c["start"]))

    chosen: list[dict] = []
    for cand in candidates:
        if len(chosen) >= max_clips:
            break
        if all(cand["end"] <= c["start"] or cand["start"] >= c["end"] for c in chosen):
            chosen.append(cand)

    chosen.sort(key=lambda c: (-c["score"], c["start"]))
    return [
        {"index": i + 1, "start": c["start"], "end": c["end"], "score": round(c["score"], 6)}
        for i, c in enumerate(chosen)
    ]
