"""
Metadata resolution endpoint.

Exposes a ``GET /metadata`` route that accepts a URL or search query and
returns track metadata (title, artist, duration, thumbnail, etc.) without
initiating a download.
"""

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_resolver
from app.schemas.responses import MetadataResponse
from app.services.resolver import ResolverService

router = APIRouter(tags=["Metadata"])


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    summary="Resolve track metadata",
    description="Accepts a YouTube URL, Spotify URL, YouTube Music URL, or free-text search query and returns track metadata.",
)
async def get_metadata(
    query: str = Query(
        ...,
        min_length=1,
        max_length=500,
        description="YouTube URL, Spotify URL, YouTube Music URL, or search query",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Never Gonna Give You Up"],
    ),
    resolver: ResolverService = Depends(get_resolver),
) -> MetadataResponse:
    """Retrieve metadata for a song without downloading.

    The resolver pipeline:
    1. Detects the input type (YouTube URL, Spotify URL, search query, etc.).
    2. Extracts or searches for track metadata from the appropriate platform.
    3. Returns normalized metadata including title, artist, duration, and thumbnail.

    Args:
        query: A URL or search string identifying the desired track.
        resolver: Injected resolver service.

    Returns:
        A MetadataResponse with ``success=True`` and populated ``metadata``.

    Raises:
        InvalidInputError: If the query cannot be parsed.
        VideoUnavailableError: If the source video/track is unavailable.
    """
    metadata = await resolver.resolve(query)
    return MetadataResponse(success=True, metadata=metadata)
