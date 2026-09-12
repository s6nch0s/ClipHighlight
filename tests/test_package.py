import pytest

from clipper.errors import ComplianceError
from clipper.package import (
    CALLOUTS,
    FTC_LINE,
    PREORDER_PHRASE,
    build_caption,
)


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
