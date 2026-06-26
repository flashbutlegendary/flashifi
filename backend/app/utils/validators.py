"""Input validation and URL classification utilities.

Every public function in this module is *pure* (no side-effects, no I/O)
and relies on pre-compiled regular expressions for fast, consistent
pattern matching across the application.
"""

from __future__ import annotations

import re

from app.exceptions.handlers import (
    FileTooLargeError,
    VideoTooLongError,
)
from app.models.enums import InputType

# ── Pre-compiled patterns ────────────────────────────────────────────────

_YOUTUBE_URL_RE: re.Pattern[str] = re.compile(
    r"^(?:https?://)?(?:www\.)?"
    r"(?:youtube\.com/(?:watch\?.*v=|embed/|v/|shorts/)"
    r"|youtu\.be/)"
    r"(?P<id>[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
"""Matches standard YouTube URLs and extracts the video ID."""

_YOUTUBE_MUSIC_URL_RE: re.Pattern[str] = re.compile(
    r"^(?:https?://)?(?:www\.)?music\.youtube\.com/"
    r"watch\?.*v=(?P<id>[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
"""Matches YouTube Music URLs (music.youtube.com/watch?v=…)."""

_SPOTIFY_TRACK_URL_RE: re.Pattern[str] = re.compile(
    r"^(?:https?://)?(?:www\.)?open\.spotify\.com/"
    r"track/(?P<id>[A-Za-z0-9]+)",
    re.IGNORECASE,
)
"""Matches Spotify track URLs and extracts the track ID."""


# ── Input classification ─────────────────────────────────────────────────


def detect_input_type(query: str) -> InputType:
    """Classify a raw user query into an :class:`InputType`.

    The function inspects the string shape — it does **not** perform any
    network requests.  Classification order matters: YouTube Music is
    checked *before* generic YouTube because ``music.youtube.com`` would
    also match the broader YouTube pattern.

    Parameters
    ----------
    query:
        The raw input string supplied by the user (URL or free-text).

    Returns
    -------
    InputType
        The detected input category.

    Examples
    --------
    >>> detect_input_type("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    <InputType.YOUTUBE: 'youtube'>
    >>> detect_input_type("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
    <InputType.YOUTUBE_MUSIC: 'youtube_music'>
    >>> detect_input_type("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
    <InputType.SPOTIFY: 'spotify'>
    >>> detect_input_type("never gonna give you up")
    <InputType.SEARCH: 'search'>
    """
    stripped = query.strip()

    # YouTube Music must be tested first — its domain is a superset match
    # for the generic YouTube pattern.
    if _YOUTUBE_MUSIC_URL_RE.search(stripped):
        return InputType.YOUTUBE_MUSIC

    if _YOUTUBE_URL_RE.search(stripped):
        return InputType.YOUTUBE

    if _SPOTIFY_TRACK_URL_RE.search(stripped):
        return InputType.SPOTIFY

    return InputType.SEARCH


# ── URL validators ───────────────────────────────────────────────────────


def is_valid_youtube_url(url: str) -> bool:
    """Return ``True`` if *url* looks like a valid YouTube video URL.

    Parameters
    ----------
    url:
        The candidate URL string.

    Returns
    -------
    bool
    """
    return _YOUTUBE_URL_RE.search(url.strip()) is not None


def is_valid_spotify_url(url: str) -> bool:
    """Return ``True`` if *url* looks like a valid Spotify track URL.

    Parameters
    ----------
    url:
        The candidate URL string.

    Returns
    -------
    bool
    """
    return _SPOTIFY_TRACK_URL_RE.search(url.strip()) is not None


def is_valid_youtube_music_url(url: str) -> bool:
    """Return ``True`` if *url* looks like a valid YouTube Music URL.

    Parameters
    ----------
    url:
        The candidate URL string.

    Returns
    -------
    bool
    """
    return _YOUTUBE_MUSIC_URL_RE.search(url.strip()) is not None


# ── ID extractors ────────────────────────────────────────────────────────


def extract_youtube_video_id(url: str) -> str | None:
    """Extract the 11-character video ID from a YouTube URL.

    Parameters
    ----------
    url:
        A YouTube or YouTube Music URL.

    Returns
    -------
    str | None
        The video ID if the URL is valid, otherwise ``None``.

    Examples
    --------
    >>> extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ")
    'dQw4w9WgXcQ'
    >>> extract_youtube_video_id("not a url") is None
    True
    """
    stripped = url.strip()

    # Try YouTube Music first
    match = _YOUTUBE_MUSIC_URL_RE.search(stripped)
    if match:
        return match.group("id")

    # Then standard YouTube
    match = _YOUTUBE_URL_RE.search(stripped)
    if match:
        return match.group("id")

    return None


def extract_spotify_track_id(url: str) -> str | None:
    """Extract the 22-character track ID from a Spotify URL.

    Parameters
    ----------
    url:
        A Spotify track URL.

    Returns
    -------
    str | None
        The track ID if the URL is valid, otherwise ``None``.

    Examples
    --------
    >>> extract_spotify_track_id("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
    '4cOdK2wGLETKBW3PvgPWqT'
    >>> extract_spotify_track_id("random text") is None
    True
    """
    match = _SPOTIFY_TRACK_URL_RE.search(url.strip())
    return match.group("id") if match else None


# ── Limit validators ────────────────────────────────────────────────────


def validate_duration(
    duration_seconds: int,
    max_seconds: int = 1200,
) -> None:
    """Raise :class:`VideoTooLongError` if the duration exceeds the limit.

    Parameters
    ----------
    duration_seconds:
        The actual duration of the media in seconds.
    max_seconds:
        The maximum allowed duration in seconds (default ``1200`` = 20 min).

    Raises
    ------
    VideoTooLongError
        When ``duration_seconds > max_seconds``.
    """
    if duration_seconds > max_seconds:
        raise VideoTooLongError(
            f"Duration {duration_seconds}s exceeds the maximum "
            f"allowed duration of {max_seconds}s."
        )


def validate_file_size(
    size_bytes: int,
    max_bytes: int = 104_857_600,
) -> None:
    """Raise :class:`FileTooLargeError` if the file size exceeds the limit.

    Parameters
    ----------
    size_bytes:
        The actual file size in bytes.
    max_bytes:
        The maximum allowed size in bytes (default ``104_857_600`` = 100 MB).

    Raises
    ------
    FileTooLargeError
        When ``size_bytes > max_bytes``.
    """
    if size_bytes > max_bytes:
        raise FileTooLargeError(
            f"File size {size_bytes} bytes exceeds the maximum "
            f"allowed size of {max_bytes} bytes."
        )
