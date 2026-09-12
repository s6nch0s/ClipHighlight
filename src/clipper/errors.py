class ClipperError(Exception):
    """Base error for all clipper failures."""


class ConfigError(ClipperError):
    """Raised when config is missing, malformed, or invalid."""


class FFmpegError(ClipperError):
    """Raised when FFmpeg/ffprobe is missing or a call fails."""


class ComplianceError(ClipperError):
    """Raised when a hard campaign-compliance rule is violated."""
