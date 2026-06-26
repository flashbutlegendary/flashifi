"""Request schemas for the FlashiFi API.

This module defines Pydantic v2 models that validate and normalize incoming
API requests for metadata lookups and download initiation.

Classes:
    MetadataRequest: Validates a metadata lookup query.
    DownloadRequest: Validates a download request with format/quality
        cross-validation logic.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from typing import Self

from app.models.enums import (
    AudioFormat,
    AudioQuality,
    VALID_QUALITY_FOR_FORMAT,
    get_default_quality,
)


class MetadataRequest(BaseModel):
    """Request schema for metadata lookup.

    Accepts a YouTube URL, Spotify URL, YouTube Music URL, or a free-text
    search query. The backend will auto-detect the input type and resolve
    it to a playable track.

    Attributes:
        query: The URL or search string to look up. Must be between 1 and
            500 characters.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "YouTube URL, Spotify URL, YouTube Music URL, or search query"
        ),
        examples=[
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8",
            "Never Gonna Give You Up Rick Astley",
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                },
                {
                    "query": "Bohemian Rhapsody Queen",
                },
            ]
        }
    }


class DownloadRequest(BaseModel):
    """Request schema for initiating a download.

    Validates the requested audio format and quality combination. If
    ``quality`` is not provided, the best default quality for the chosen
    format is selected automatically. The validator rejects quality values
    that are incompatible with the requested format (e.g. 320 kbps for
    FLAC).

    Attributes:
        query: The URL or search string identifying the track to download.
        format: The desired output audio format. Defaults to MP3.
        quality: The audio quality / bitrate. When ``None``, the default
            quality for the selected format is used.

    Raises:
        ValueError: If the quality is not valid for the chosen format.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "YouTube URL, Spotify URL, YouTube Music URL, or search query"
        ),
        examples=[
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "Blinding Lights The Weeknd",
        ],
    )
    format: AudioFormat = Field(
        default=AudioFormat.MP3,
        description="Output audio format",
    )
    quality: AudioQuality | None = Field(
        default=None,
        description=(
            "Audio quality/bitrate. Auto-selected based on format if not "
            "provided."
        ),
    )

    @model_validator(mode="after")
    def validate_format_quality(self) -> Self:
        """Ensure the quality is valid for the selected format.

        If no quality was provided, the default quality for the format is
        assigned. If an explicit quality was provided, it is validated
        against the set of allowed qualities for that format.

        Returns:
            The validated ``DownloadRequest`` instance with a guaranteed
            non-``None`` quality.

        Raises:
            ValueError: When the provided quality is incompatible with the
                selected audio format.
        """
        if self.quality is None:
            self.quality = get_default_quality(self.format)
            return self

        valid_qualities: set[AudioQuality] = VALID_QUALITY_FOR_FORMAT.get(
            self.format, set()
        )

        if self.quality not in valid_qualities:
            valid_str = ", ".join(
                sorted(q.value for q in valid_qualities)
            )
            raise ValueError(
                f"Quality '{self.quality.value}' is not valid for format "
                f"'{self.format.value}'. Valid options: {valid_str}"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "format": "mp3",
                    "quality": "320kbps",
                },
                {
                    "query": "Bohemian Rhapsody Queen",
                    "format": "flac",
                    "quality": None,
                },
                {
                    "query": "https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8",
                    "format": "opus",
                    "quality": "128kbps",
                },
            ]
        }
    }
