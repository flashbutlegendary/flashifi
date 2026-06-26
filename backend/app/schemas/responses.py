"""Response schemas for the FlashiFi API.

This module defines Pydantic v2 models that structure all outgoing API
responses. Every model includes full type hints, field descriptions, and
OpenAPI-compatible metadata.

Classes:
    VersionInfo: Application version metadata.
    HealthResponse: System health check payload.
    TrackMetadata: Detailed metadata for a single audio track.
    MetadataResponse: Wrapper for a successful metadata lookup.
    DownloadTaskResponse: Acknowledgement of a queued download task.
    ProgressResponse: Real-time download/conversion progress update.
    DownloadReadyResponse: Final payload when a download is ready.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import DownloadStage, SourcePlatform


class VersionInfo(BaseModel):
    """Application version metadata.

    Provides build-time information useful for debugging and client-side
    compatibility checks.

    Attributes:
        app_version: Semantic version string (e.g. ``"1.0.0"``).
        build_date: ISO-8601 date string of the build.
        git_commit: Short SHA of the Git commit, if available.
    """

    app_version: str = Field(
        ...,
        description="Semantic version string (e.g. '1.0.0')",
        examples=["1.0.0"],
    )
    build_date: str = Field(
        ...,
        description="ISO-8601 build date",
        examples=["2026-06-25"],
    )
    git_commit: str | None = Field(
        default=None,
        description="Short SHA of the Git commit used for this build",
        examples=["a1b2c3d"],
    )


class HealthResponse(BaseModel):
    """System health check response.

    Reports the operational status of the application and its critical
    dependencies (FFmpeg, yt-dlp, disk space, temp directory).

    Attributes:
        status: Overall health status — ``"healthy"``, ``"degraded"``,
            or ``"unhealthy"``.
        version: Embedded version metadata.
        ffmpeg_available: Whether FFmpeg is reachable on ``PATH``.
        ytdlp_available: Whether yt-dlp is reachable on ``PATH``.
        temp_dir_writable: Whether the configured temp directory is
            writable.
        disk_space_mb: Available disk space in megabytes on the temp
            volume.
        uptime_seconds: Application uptime since startup in seconds.
    """

    status: str = Field(
        ...,
        description="Overall health status: healthy, degraded, unhealthy",
        examples=["healthy"],
    )
    version: VersionInfo = Field(
        ...,
        description="Application version metadata",
    )
    ffmpeg_available: bool = Field(
        ...,
        description="Whether FFmpeg is installed and reachable",
    )
    ytdlp_available: bool = Field(
        ...,
        description="Whether yt-dlp is installed and reachable",
    )
    temp_dir_writable: bool = Field(
        ...,
        description="Whether the temp directory is writable",
    )
    disk_space_mb: float = Field(
        ...,
        ge=0,
        description="Available disk space in MB on the temp volume",
        examples=[10240.5],
    )
    uptime_seconds: float = Field(
        ...,
        ge=0,
        description="Application uptime since startup in seconds",
        examples=[3600.0],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": {
                        "app_version": "1.0.0",
                        "build_date": "2026-06-25",
                        "git_commit": "a1b2c3d",
                    },
                    "ffmpeg_available": True,
                    "ytdlp_available": True,
                    "temp_dir_writable": True,
                    "disk_space_mb": 10240.5,
                    "uptime_seconds": 3600.0,
                }
            ]
        }
    }


class TrackMetadata(BaseModel):
    """Detailed metadata for a single audio track.

    Contains all information extracted from the source platform (YouTube,
    Spotify, YouTube Music) needed by the frontend to display track details
    and initiate a download.

    Attributes:
        title: Track title.
        artist: Primary artist name.
        album: Album name, if available.
        duration_seconds: Track duration in whole seconds.
        duration_formatted: Human-readable duration (e.g. ``"3:45"``).
        thumbnail_url: URL to the track's thumbnail image.
        video_id: Platform-specific video/track identifier.
        uploader: Channel or uploader name.
        estimated_size_mb: Estimated download size in megabytes.
        source_platform: Platform the track was resolved from.
        upload_date: ISO-8601 upload date, if available.
        view_count: Number of views/plays, if available.
    """

    title: str = Field(
        ...,
        description="Track title",
        examples=["Never Gonna Give You Up"],
    )
    artist: str = Field(
        ...,
        description="Primary artist name",
        examples=["Rick Astley"],
    )
    album: str | None = Field(
        default=None,
        description="Album name, if available",
        examples=["Whenever You Need Somebody"],
    )
    duration_seconds: int = Field(
        ...,
        ge=0,
        description="Track duration in whole seconds",
        examples=[212],
    )
    duration_formatted: str = Field(
        ...,
        description="Human-readable duration string (e.g. '3:32')",
        examples=["3:32"],
    )
    thumbnail_url: str | None = Field(
        default=None,
        description="URL to the track's thumbnail image",
        examples=["https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"],
    )
    video_id: str = Field(
        ...,
        description="Platform-specific video or track identifier",
        examples=["dQw4w9WgXcQ"],
    )
    uploader: str | None = Field(
        default=None,
        description="Channel or uploader name",
        examples=["Rick Astley"],
    )
    estimated_size_mb: float | None = Field(
        default=None,
        ge=0,
        description="Estimated download file size in megabytes",
        examples=[4.8],
    )
    source_platform: SourcePlatform = Field(
        ...,
        description="Platform the track was resolved from",
        examples=["youtube"],
    )
    upload_date: str | None = Field(
        default=None,
        description="ISO-8601 upload date, if available",
        examples=["2009-10-25"],
    )
    view_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of views or plays, if available",
        examples=[1_500_000_000],
    )


class MetadataResponse(BaseModel):
    """Wrapper for a successful metadata lookup.

    Returned by the ``/api/v1/metadata`` endpoint upon successful
    resolution of a query to a playable track.

    Attributes:
        success: Always ``True`` for successful responses.
        metadata: The resolved track metadata.
    """

    success: bool = Field(
        default=True,
        description="Indicates the request was successful",
    )
    metadata: TrackMetadata = Field(
        ...,
        description="Resolved track metadata",
    )


class DownloadTaskResponse(BaseModel):
    """Acknowledgement returned when a download task is accepted.

    The client should use the ``task_id`` to poll for progress or
    subscribe to SSE updates.

    Attributes:
        task_id: Unique identifier for the queued download task.
        status: Always ``"accepted"`` upon creation.
        message: Human-readable confirmation message.
    """

    task_id: str = Field(
        ...,
        description="Unique identifier for the queued download task",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    status: str = Field(
        default="accepted",
        description="Task status upon creation",
        examples=["accepted"],
    )
    message: str = Field(
        default="Download task created successfully",
        description="Human-readable confirmation message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "accepted",
                    "message": "Download task created successfully",
                }
            ]
        }
    }


class ProgressResponse(BaseModel):
    """Real-time download/conversion progress update.

    Sent via SSE or returned by the progress polling endpoint to inform
    the client of the current download stage.

    Attributes:
        task_id: The download task identifier.
        stage: Current processing stage.
        percentage: Completion percentage (0–100).
        speed: Human-readable download speed (e.g. ``"1.2 MiB/s"``).
        eta: Estimated time remaining (e.g. ``"0:15"``).
        message: Optional status message for the client.
    """

    task_id: str = Field(
        ...,
        description="Download task identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    stage: DownloadStage = Field(
        ...,
        description="Current processing stage",
        examples=["downloading"],
    )
    percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Completion percentage (0–100)",
        examples=[42.5],
    )
    speed: str | None = Field(
        default=None,
        description="Human-readable download speed",
        examples=["1.2 MiB/s"],
    )
    eta: str | None = Field(
        default=None,
        description="Estimated time remaining",
        examples=["0:15"],
    )
    message: str | None = Field(
        default=None,
        description="Optional status message for the client",
        examples=["Downloading audio stream…"],
    )


class DownloadReadyResponse(BaseModel):
    """Final payload when a download is ready for retrieval.

    Returned once the conversion pipeline has completed and the file is
    available for the client to fetch.

    Attributes:
        task_id: The download task identifier.
        download_url: URL to retrieve the converted file.
        filename: Suggested filename for the downloaded file.
        file_size_mb: Actual file size in megabytes.
    """

    task_id: str = Field(
        ...,
        description="Download task identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    download_url: str = Field(
        ...,
        description="URL to retrieve the converted audio file",
        examples=["/api/v1/downloads/550e8400-e29b-41d4-a716-446655440000/file"],
    )
    filename: str = Field(
        ...,
        description="Suggested filename for the download",
        examples=["Never_Gonna_Give_You_Up-Rick_Astley.mp3"],
    )
    file_size_mb: float = Field(
        ...,
        ge=0,
        description="Actual file size in megabytes",
        examples=[4.7],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "download_url": "/api/v1/downloads/550e8400-e29b-41d4-a716-446655440000/file",
                    "filename": "Never_Gonna_Give_You_Up-Rick_Astley.mp3",
                    "file_size_mb": 4.7,
                }
            ]
        }
    }
