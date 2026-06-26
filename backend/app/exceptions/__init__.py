"""FlashiFi exception hierarchy.

All application-specific exceptions derive from :class:`FlashiFiError`
and carry an HTTP ``status_code`` for seamless FastAPI error-handler
integration::

    from app.exceptions import DownloadError, InvalidInputError
"""

from app.exceptions.handlers import (
    ConversionError,
    DownloadError,
    FFmpegNotFoundError,
    FileTooLargeError,
    FlashiFiError,
    InvalidInputError,
    RateLimitError,
    SpotifyExtractionError,
    TaskNotFoundError,
    VideoTooLongError,
    VideoUnavailableError,
    YTDLPError,
)

__all__ = [
    "ConversionError",
    "DownloadError",
    "FFmpegNotFoundError",
    "FileTooLargeError",
    "FlashiFiError",
    "InvalidInputError",
    "RateLimitError",
    "SpotifyExtractionError",
    "TaskNotFoundError",
    "VideoTooLongError",
    "VideoUnavailableError",
    "YTDLPError",
]
