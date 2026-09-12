from clipper.select import HARD_FLOOR, select_windows


def _points(step: float, duration: float, hot_ranges: list[tuple[float, float]]):
    pts = []
    t = 0.0
    while t < duration:
        score = 0.05
        for lo, hi in hot_ranges:
            if lo <= t < hi:
                score = 1.0
        pts.append({"t": round(t, 3), "combined": score})
        t += step
    return pts


def test_returns_empty_when_video_too_short():
    pts = _points(1.0, 5.0, [(0.0, 5.0)])
    assert select_windows(pts, step=1.0, video_duration=5.0, min_len=30, max_len=60, max_clips=5) == []


def test_picks_highest_scoring_window_first():
    pts = _points(1.0, 240.0, [(120.0, 180.0)])
    result = select_windows(pts, step=1.0, video_duration=240.0, min_len=30, max_len=60, max_clips=1)
    assert len(result) == 1
    assert result[0]["index"] == 1
    assert result[0]["start"] <= 120.0 < result[0]["end"]


def test_windows_are_non_overlapping():
    pts = _points(1.0, 240.0, [(20.0, 80.0), (150.0, 210.0)])
    result = select_windows(pts, step=1.0, video_duration=240.0, min_len=30, max_len=60, max_clips=5)
    assert len(result) == 2
    a, b = sorted(result, key=lambda w: w["start"])
    assert a["end"] <= b["start"]


def test_respects_max_clips():
    pts = _points(1.0, 600.0, [(30, 60), (150, 180), (300, 330), (450, 480)])
    result = select_windows(pts, step=1.0, video_duration=600.0, min_len=30, max_len=60, max_clips=2)
    assert len(result) == 2


def test_ranks_by_score_desc():
    pts = _points(1.0, 240.0, [(150.0, 210.0)])
    # add a weaker hot zone
    for p in pts:
        if 20.0 <= p["t"] < 80.0:
            p["combined"] = 0.5
    result = select_windows(pts, step=1.0, video_duration=240.0, min_len=30, max_len=60, max_clips=2)
    assert result[0]["score"] >= result[1]["score"]
    assert result[0]["index"] == 1 and result[1]["index"] == 2


def test_short_video_yields_single_floor_window():
    pts = _points(1.0, 15.0, [(0.0, 15.0)])
    result = select_windows(pts, step=1.0, video_duration=15.0, min_len=30, max_len=60, max_clips=5)
    assert len(result) == 1
    assert (result[0]["end"] - result[0]["start"]) >= HARD_FLOOR


def test_secondary_highlight_not_starved():
    pts = _points(1.0, 600.0, [(0.0, 120.0)])
    # add a weaker secondary highlight that a global-mean gate would starve
    for p in pts:
        if 300.0 <= p["t"] < 360.0:
            p["combined"] = 0.2
    result = select_windows(pts, step=1.0, video_duration=600.0, min_len=30, max_len=60, max_clips=3)
    # 120s peak fills two 60s windows, plus the secondary -> 3 clips (secondary kept)
    assert len(result) == 3
    assert any(w["start"] <= 330.0 < w["end"] for w in result)
