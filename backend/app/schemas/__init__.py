"""Request and response schemas for the FlashiFi API.

This package provides Pydantic v2 models for:
- Request validation (MetadataRequest, DownloadRequest)
- Response serialization (HealthResponse, MetadataResponse, etc.)
- Error formatting (ErrorResponse)

Usage::

    from app.schemas import MetadataRequest, DownloadRequest
    from app.schemas import HealthResponse, MetadataResponse
    from app.schemas import ErrorResponse
"""

from app.schemas.requests import MetadataRequest, DownloadRequest
from app.schemas.responses import (
    HealthResponse,
    MetadataResponse,
    TrackMetadata,
    DownloadTaskResponse,
    ProgressResponse,
    VersionInfo,
    DownloadReadyResponse,
)
from app.schemas.errors import ErrorResponse

__all__: list[str] = [
    "MetadataRequest",
    "DownloadRequest",
    "HealthResponse",
    "MetadataResponse",
    "TrackMetadata",
    "DownloadTaskResponse",
    "ProgressResponse",
    "VersionInfo",
    "DownloadReadyResponse",
    "ErrorResponse",
]
