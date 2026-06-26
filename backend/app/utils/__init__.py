"""Utility helpers for FlashiFi.

Re-exports the most commonly used functions so callers can write::

    from app.utils import detect_input_type, sanitize_filename, format_duration
"""

from app.utils.sanitizers import safe_path_join, sanitize_filename
from app.utils.time_utils import format_duration, format_eta, format_file_size, format_speed
from app.utils.validators import (
    detect_input_type,
    extract_spotify_track_id,
    extract_youtube_video_id,
    is_valid_spotify_url,
    is_valid_youtube_music_url,
    is_valid_youtube_url,
    validate_duration,
    validate_file_size,
)

__all__ = [
    "detect_input_type",
    "extract_spotify_track_id",
    "extract_youtube_video_id",
    "format_duration",
    "format_eta",
    "format_file_size",
    "format_speed",
    "is_valid_spotify_url",
    "is_valid_youtube_music_url",
    "is_valid_youtube_url",
    "safe_path_join",
    "sanitize_filename",
    "validate_duration",
    "validate_file_size",
]
