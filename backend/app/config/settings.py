"""Application settings backed by Pydantic BaseSettings.

Settings are loaded from environment variables and/or an ``.env`` file.
Every environment variable is prefixed with ``FLASHIFI_`` and is
case-insensitive.  Unknown variables are silently ignored.

Example
-------
Export ``FLASHIFI_DEBUG=true`` or add it to a ``.env`` file next to the
application entry-point to enable debug mode.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, validated application configuration.

    Attributes are grouped by concern.  Sensible defaults are provided so
    the application can start with *zero* configuration in development.

    Notes
    -----
    * ``temp_base_dir`` defaults to the operating-system temporary
      directory when left empty.
    * ``cors_origins`` accepts a JSON-encoded list string in the
      environment (Pydantic handles the parsing).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FLASHIFI_",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "FlashiFi"
    """Human-readable application name used in logs and API responses."""

    debug: bool = False
    """Enable debug mode (verbose logging, auto-reload, etc.)."""

    log_level: str = "INFO"
    """Root logging level.  One of DEBUG, INFO, WARNING, ERROR, CRITICAL."""

    host: str = "0.0.0.0"
    """Network interface the server binds to."""

    port: int = 8000
    """TCP port the server listens on."""

    workers: int = 4
    """Number of Uvicorn worker processes (production only)."""

    cors_origins: list[str] = ["*"]
    """Allowed CORS origins.  ``["*"]`` permits all origins."""

    # ── Limits ───────────────────────────────────────────────────────────
    max_duration_seconds: int = 1200
    """Maximum allowed media duration in seconds (default: 20 minutes)."""

    max_file_size_bytes: int = 104_857_600
    """Maximum allowed output file size in bytes (default: 100 MB)."""

    # ── Storage ──────────────────────────────────────────────────────────
    temp_base_dir: str = ""
    """Base directory for temporary files.  Empty string → OS temp dir."""

    cleanup_interval_seconds: int = 300
    """How often (seconds) the background cleanup task runs."""

    cleanup_max_age_seconds: int = 3600
    """Maximum age (seconds) of temporary files before deletion."""

    # ── External tools ───────────────────────────────────────────────────
    ffmpeg_path: str = "ffmpeg"
    """Path (or bare name on ``$PATH``) of the FFmpeg binary."""

    # ── Cache TTLs ───────────────────────────────────────────────────────
    metadata_cache_ttl: int = 1800
    """Time-to-live (seconds) for cached video/track metadata."""

    search_cache_ttl: int = 900
    """Time-to-live (seconds) for cached search results."""

    thumbnail_cache_ttl: int = 3600
    """Time-to-live (seconds) for cached thumbnail data."""

    # ── Search ───────────────────────────────────────────────────────────
    max_search_results: int = 10
    """Maximum number of search results returned per query."""

    download_timeout: int = 300
    """Per-download timeout in seconds."""

    # ── Derived properties ───────────────────────────────────────────────

    @property
    def temp_dir(self) -> Path:
        """Return the resolved temporary directory for FlashiFi artefacts.

        If :pyattr:`temp_base_dir` is empty the operating-system default
        temporary directory is used.  A ``flashifi`` sub-directory is always
        appended to isolate our files from other applications.

        Returns
        -------
        Path
            Absolute path to the temporary working directory.
        """
        base = (
            Path(self.temp_base_dir)
            if self.temp_base_dir
            else Path(tempfile.gettempdir())
        )
        return base / "flashifi"
