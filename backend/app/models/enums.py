"""Enumerations and related lookup tables for FlashiFi.

This module defines every domain-level enumeration used across the
application — input classification, audio codec/quality selection, and
download lifecycle stages.  Companion dictionaries and a helper function
provide runtime validation of format ↔ quality compatibility.
"""

from __future__ import annotations

from enum import Enum


# ── Input / Source enumerations ──────────────────────────────────────────


class InputType(str, Enum):
    """Classification of the raw user query.

    Determined at request time by inspecting the shape of the input
    string (URL host, path structure, or free-text).
    """

    YOUTUBE = "youtube"
    """Standard YouTube video URL (youtube.com, youtu.be)."""

    YOUTUBE_MUSIC = "youtube_music"
    """YouTube Music URL (music.youtube.com)."""

    SPOTIFY = "spotify"
    """Spotify track URL (open.spotify.com/track/…)."""

    SEARCH = "search"
    """Free-text search query — no URL detected."""


class SourcePlatform(str, Enum):
    """Normalised platform identifier written into output metadata.

    Semantically identical to :class:`InputType` but kept separate so the
    download pipeline can evolve independently of input classification.
    """

    YOUTUBE = "youtube"
    YOUTUBE_MUSIC = "youtube_music"
    SPOTIFY = "spotify"
    SEARCH = "search"


# ── Audio format / quality enumerations ──────────────────────────────────


class AudioFormat(str, Enum):
    """Supported output audio container/codec formats."""

    MP3 = "mp3"
    """MPEG-1 Audio Layer III (lossy)."""

    FLAC = "flac"
    """Free Lossless Audio Codec."""

    WAV = "wav"
    """Waveform Audio File Format (uncompressed PCM)."""


class AudioQuality(str, Enum):
    """Target audio bitrate / quality tier.

    Numeric members represent kilobits-per-second for lossy codecs.
    ``LOSSLESS`` requests the highest fidelity available and is the only
    valid choice for lossless containers (FLAC, WAV).
    """

    LOW_128 = "128"
    """128 kbps — acceptable for speech and casual listening."""

    MEDIUM_192 = "192"
    """192 kbps — good balance of size and quality."""

    HIGH_256 = "256"
    """256 kbps — near-transparent for most listeners."""

    ULTRA_320 = "320"
    """320 kbps — maximum CBR quality for MP3."""

    LOSSLESS = "lossless"
    """Bit-perfect copy; required for FLAC and WAV output."""


# ── Download lifecycle ───────────────────────────────────────────────────


class DownloadStage(str, Enum):
    """Discrete stages a download task passes through.

    The stage is surfaced to clients via progress events so they can
    render meaningful status indicators.
    """

    PREPARING = "preparing"
    """Task accepted; allocating resources."""

    RESOLVING = "resolving"
    """Resolving metadata (title, duration, thumbnail …)."""

    DOWNLOADING = "downloading"
    """Fetching the raw audio stream from the source."""

    CONVERTING = "converting"
    """Transcoding / re-muxing to the requested output format."""

    CLEANING = "cleaning"
    """Post-processing: tagging, cleanup of intermediary files."""

    COMPLETED = "completed"
    """Download finished successfully; file is ready."""

    FAILED = "failed"
    """An unrecoverable error occurred during processing."""


# ── Quality validation tables ────────────────────────────────────────────

VALID_QUALITY_FOR_FORMAT: dict[AudioFormat, set[AudioQuality]] = {
    AudioFormat.MP3: {
        AudioQuality.LOW_128,
        AudioQuality.MEDIUM_192,
        AudioQuality.HIGH_256,
        AudioQuality.ULTRA_320,
    },
    AudioFormat.FLAC: {
        AudioQuality.LOSSLESS,
    },
    AudioFormat.WAV: {
        AudioQuality.LOSSLESS,
    },
}
"""Map each :class:`AudioFormat` to its set of permissible qualities.

MP3 supports all *numeric* bitrate tiers.  Lossless containers (FLAC,
WAV) accept only :pyattr:`AudioQuality.LOSSLESS`.
"""


def get_default_quality(fmt: AudioFormat) -> AudioQuality:
    """Return the recommended default quality for *fmt*.

    Parameters
    ----------
    fmt:
        The target audio format.

    Returns
    -------
    AudioQuality
        ``ULTRA_320`` for MP3 (best lossy quality) or ``LOSSLESS`` for
        FLAC / WAV.

    Examples
    --------
    >>> get_default_quality(AudioFormat.MP3)
    <AudioQuality.ULTRA_320: '320'>
    >>> get_default_quality(AudioFormat.FLAC)
    <AudioQuality.LOSSLESS: 'lossless'>
    """
    if fmt is AudioFormat.MP3:
        return AudioQuality.ULTRA_320
    return AudioQuality.LOSSLESS


FORMAT_EXTENSIONS: dict[AudioFormat, str] = {
    AudioFormat.MP3: ".mp3",
    AudioFormat.FLAC: ".flac",
    AudioFormat.WAV: ".wav",
}
"""File extension (including leading dot) for each :class:`AudioFormat`."""
