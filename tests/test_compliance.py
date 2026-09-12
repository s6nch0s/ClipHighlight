from clipper.compliance import check_compliance, validate_on_screen_text
from clipper.config import load_config
from tests.test_config import VALID


def _cfg(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return load_config(p)


def test_valid_on_screen_text_passes():
    assert validate_on_screen_text("MW4 Open Beta This Weekend — Gameplay") == []


def test_variant_phrase_passes():
    assert validate_on_screen_text("Insane MW4 Beta Weekend clip") == []


def test_missing_phrase_fails():
    errors = validate_on_screen_text("Just some gameplay")
    assert errors


def test_check_compliance_flags_missing_logo(tmp_path):
    text = VALID.replace('path: "./assets/mw4_logo.png"', 'path: "./assets/missing_logo.png"')
    report = check_compliance(_cfg(tmp_path, text))
    assert report.ok  # text is valid, logo only warns
    assert any("logo" in w.lower() for w in report.warnings)


def test_check_compliance_fails_bad_text(tmp_path):
    text = VALID.replace('text: "MW4 Open Beta This Weekend"', 'text: "just gameplay"')
    report = check_compliance(_cfg(tmp_path, text))
    assert not report.ok
