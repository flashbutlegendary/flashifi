"""
Tests for app.utils.validators.
Covers input-type detection, duration/file-size guards, URL validation, and ID extraction.
"""
import pytest
from app.utils.validators import (
    detect_input_type,
    validate_duration,
    validate_file_size,
    is_valid_youtube_url,
    is_valid_spotify_url,
    is_valid_youtube_music_url,
    extract_youtube_video_id,
    extract_spotify_track_id,
)
from app.models.enums import InputType
from app.exceptions.handlers import VideoTooLongError, FileTooLargeError


# ── detect_input_type ────────────────────────────────────────────────────────


class TestDetectInputType:
    """Group all detect_input_type tests for clarity."""

    def test_detect_youtube_url_standard(self):
        assert (
            detect_input_type("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            == InputType.YOUTUBE
        )

    def test_detect_youtube_url_short(self):
        assert (
            detect_input_type("https://youtu.be/dQw4w9WgXcQ") == InputType.YOUTUBE
        )

    def test_detect_youtube_url_http(self):
        assert (
            detect_input_type("http://youtube.com/watch?v=abc123") == InputType.YOUTUBE
        )

    def test_detect_youtube_music_url(self):
        assert (
            detect_input_type("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
            == InputType.YOUTUBE_MUSIC
        )

    def test_detect_spotify_url(self):
        assert (
            detect_input_type(
                "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
            )
            == InputType.SPOTIFY
        )

    def test_detect_search_plain_text(self):
        assert detect_input_type("Believer Imagine Dragons") == InputType.SEARCH

    def test_detect_search_random_text(self):
        assert detect_input_type("some random text") == InputType.SEARCH


# ── validate_duration ────────────────────────────────────────────────────────


class TestValidateDuration:
    """Duration guardrails."""

    def test_validate_duration_within_limit(self):
        validate_duration(300)  # 5 minutes — should pass silently

    def test_validate_duration_exceeds_limit(self):
        with pytest.raises(VideoTooLongError):
            validate_duration(1500)  # 25 minutes — should raise


# ── validate_file_size ───────────────────────────────────────────────────────


class TestValidateFileSize:
    """File-size guardrails."""

    def test_validate_file_size_within_limit(self):
        validate_file_size(50_000_000)  # 50 MB — should pass

    def test_validate_file_size_exceeds_limit(self):
        with pytest.raises(FileTooLargeError):
            validate_file_size(200_000_000)  # 200 MB — should raise


# ── extract_youtube_video_id ─────────────────────────────────────────────────


class TestExtractYouTubeVideoId:
    """YouTube video-ID extraction from various URL forms."""

    def test_standard_url(self):
        assert (
            extract_youtube_video_id(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
            == "dQw4w9WgXcQ"
        )

    def test_short_url(self):
        assert (
            extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ")
            == "dQw4w9WgXcQ"
        )

    def test_invalid_input_returns_none(self):
        assert extract_youtube_video_id("not a url") is None


# ── extract_spotify_track_id ─────────────────────────────────────────────────


class TestExtractSpotifyTrackId:
    """Spotify track-ID extraction."""

    def test_clean_url(self):
        assert (
            extract_spotify_track_id(
                "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
            )
            == "4uLU6hMCjMI75M1A2tKUQC"
        )

    def test_url_with_query_params(self):
        assert (
            extract_spotify_track_id(
                "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC?si=abc"
            )
            == "4uLU6hMCjMI75M1A2tKUQC"
        )


# ── is_valid_* helpers ───────────────────────────────────────────────────────


class TestUrlValidityHelpers:
    """Boolean URL validators."""

    def test_is_valid_youtube_url_true(self):
        assert is_valid_youtube_url("https://www.youtube.com/watch?v=abc") is True

    def test_is_valid_youtube_url_false(self):
        assert is_valid_youtube_url("not a url") is False

    def test_is_valid_spotify_url_track(self):
        assert is_valid_spotify_url("https://open.spotify.com/track/abc") is True

    def test_is_valid_spotify_url_album_rejected(self):
        assert is_valid_spotify_url("https://open.spotify.com/album/abc") is False

    def test_is_valid_youtube_music_url_true(self):
        assert (
            is_valid_youtube_music_url("https://music.youtube.com/watch?v=abc") is True
        )

    def test_is_valid_youtube_music_url_regular_youtube_rejected(self):
        assert (
            is_valid_youtube_music_url("https://youtube.com/watch?v=abc") is False
        )
