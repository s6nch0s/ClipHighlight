from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config

REQUIRED_TEXT_PHRASES = ("MW4 Open Beta", "This Weekend")
ACCEPTED_TEXT_VARIANT = "MW4 Beta Weekend"


def validate_on_screen_text(text: str) -> list[str]:
    lowered = text.lower()
    if ACCEPTED_TEXT_VARIANT.lower() in lowered:
        return []
    if all(phrase.lower() in lowered for phrase in REQUIRED_TEXT_PHRASES):
        return []
    return [
        "on_screen_text must contain 'MW4 Open Beta' AND 'This Weekend' "
        "(or the variant 'MW4 Beta Weekend')."
    ]


@dataclass
class ComplianceReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check_compliance(cfg: Config) -> ComplianceReport:
    report = ComplianceReport()
    report.errors.extend(validate_on_screen_text(cfg.on_screen_text.text))
    if cfg.logo.path is None:
        report.warnings.append("No logo.path configured; clips will be NON-COMPLIANT.")
    elif not cfg.logo.path.is_file():
        report.warnings.append(
            f"Logo file missing: {cfg.logo.path}; clips will be NON-COMPLIANT until added."
        )
    if cfg.on_screen_text.font is not None and not cfg.on_screen_text.font.is_file():
        report.warnings.append(
            f"Font file missing: {cfg.on_screen_text.font}; FFmpeg default font will be used."
        )
    return report
