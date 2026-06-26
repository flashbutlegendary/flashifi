"""Structured exception hierarchy for FlashiFi.

Every exception carries a human-readable ``detail`` message and an HTTP
``status_code`` so that FastAPI error handlers can translate them into
appropriate JSON responses without additional mapping logic.

Hierarchy
---------
::

    FlashiFiError (500)
    ├── InvalidInputError (400)
    ├── VideoTooLongError (400)
    ├── FileTooLargeError (400)
    ├── VideoUnavailableError (404)
    ├── TaskNotFoundError (404)
    ├── RateLimitError (429)
    ├── ConversionError (500)
    ├── DownloadError (500)
    ├── SpotifyExtractionError (502)
    ├── YTDLPError (502)
    └── FFmpegNotFoundError (503)
"""

from __future__ import annotations


class FlashiFiError(Exception):
    """Base exception for all FlashiFi domain errors.

    Parameters
    ----------
    detail:
        A human-readable description of what went wrong.
    status_code:
        The HTTP status code that best represents this error when
        surfaced through the REST API.  Defaults to ``500``.
    """

    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail: str = detail
        self.status_code: int = status_code
        super().__init__(detail)

    def __repr__(self) -> str:  # noqa: D105
        return (
            f"{self.__class__.__name__}(detail={self.detail!r}, "
            f"status_code={self.status_code})"
        )


# ── 400 Bad Request ──────────────────────────────────────────────────────


class InvalidInputError(FlashiFiError):
    """The user-supplied input is malformed or unrecognised.

    Parameters
    ----------
    detail:
        Explanation of why the input was rejected.
    """

    def __init__(self, detail: str = "Invalid input provided.") -> None:
        super().__init__(detail=detail, status_code=400)


class VideoTooLongError(FlashiFiError):
    """The requested media exceeds the maximum allowed duration.

    Parameters
    ----------
    detail:
        Explanation including the actual and maximum durations.
    """

    def __init__(self, detail: str = "Video exceeds the maximum allowed duration.") -> None:
        super().__init__(detail=detail, status_code=400)


class FileTooLargeError(FlashiFiError):
    """The resulting file exceeds the maximum allowed size.

    Parameters
    ----------
    detail:
        Explanation including the actual and maximum sizes.
    """

    def __init__(self, detail: str = "File exceeds the maximum allowed size.") -> None:
        super().__init__(detail=detail, status_code=400)


# ── 404 Not Found ───────────────────────────────────────────────────────


class VideoUnavailableError(FlashiFiError):
    """The requested video/track could not be found or is geo-blocked.

    Parameters
    ----------
    detail:
        Explanation of why the media is unavailable.
    """

    def __init__(self, detail: str = "Video is unavailable.") -> None:
        super().__init__(detail=detail, status_code=404)


class TaskNotFoundError(FlashiFiError):
    """No download task exists with the given identifier.

    Parameters
    ----------
    detail:
        Explanation including the missing task ID.
    """

    def __init__(self, detail: str = "Download task not found.") -> None:
        super().__init__(detail=detail, status_code=404)


# ── 429 Too Many Requests ───────────────────────────────────────────────


class RateLimitError(FlashiFiError):
    """The caller has exceeded the allowed request rate.

    Parameters
    ----------
    detail:
        Explanation including the rate-limit policy.
    """

    def __init__(self, detail: str = "Rate limit exceeded. Please try again later.") -> None:
        super().__init__(detail=detail, status_code=429)


# ── 500 Internal Server Error ────────────────────────────────────────────


class ConversionError(FlashiFiError):
    """Audio format conversion (FFmpeg transcoding) failed.

    Parameters
    ----------
    detail:
        FFmpeg stderr excerpt or a summary of the failure.
    """

    def __init__(self, detail: str = "Audio conversion failed.") -> None:
        super().__init__(detail=detail, status_code=500)


class DownloadError(FlashiFiError):
    """A generic, unrecoverable download failure.

    Parameters
    ----------
    detail:
        Description of the download failure.
    """

    def __init__(self, detail: str = "Download failed.") -> None:
        super().__init__(detail=detail, status_code=500)


# ── 502 Bad Gateway ─────────────────────────────────────────────────────


class SpotifyExtractionError(FlashiFiError):
    """Failed to resolve a Spotify track to a downloadable source.

    Parameters
    ----------
    detail:
        Description of the Spotify extraction failure.
    """

    def __init__(self, detail: str = "Failed to extract track from Spotify.") -> None:
        super().__init__(detail=detail, status_code=502)


class YTDLPError(FlashiFiError):
    """yt-dlp returned a non-zero exit code or raised an exception.

    Parameters
    ----------
    detail:
        The yt-dlp error message or stderr output.
    """

    def __init__(self, detail: str = "yt-dlp encountered an error.") -> None:
        super().__init__(detail=detail, status_code=502)


# ── 503 Service Unavailable ─────────────────────────────────────────────


class FFmpegNotFoundError(FlashiFiError):
    """FFmpeg binary could not be located on the system ``$PATH``.

    Parameters
    ----------
    detail:
        Troubleshooting hint for the operator.
    """

    def __init__(
        self,
        detail: str = "FFmpeg is not installed or not found on PATH.",
    ) -> None:
        super().__init__(detail=detail, status_code=503)
