"""
YouTube Music service.

A specialized resolver for music.youtube.com URLs. Resolves tracks by extracting
the underlying video ID and delegating metadata operations to the YouTube service.
"""

import logging
from typing import Any

from app.config.settings import Settings
from app.exceptions.handlers import InvalidInputError
from app.services.youtube import YouTubeService
from app.utils.validators import extract_youtube_video_id

logger = logging.getLogger(__name__)


class YouTubeMusicService:
    """Specialized service for resolving YouTube Music queries."""

    def __init__(self, settings: Settings, youtube_service: YouTubeService) -> None:
        """Initialize the service.

        Args:
            settings: Injected application configuration.
            youtube_service: Injected YouTube service for underlying resolution.
        """
        self._settings = settings
        self._youtube = youtube_service

    async def resolve_video(self, url: str) -> dict[str, Any]:
        """Resolve a YouTube Music URL to full raw metadata.

        Extracts the video ID from the YouTube Music URL, reformats it into a
        standard YouTube watch URL, and fetches its metadata.

        Args:
            url: The YouTube Music URL.

        Returns:
            The raw info dictionary from yt-dlp.

        Raises:
            InvalidInputError: If the URL is not a valid YouTube Music link.
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            raise InvalidInputError(f"Could not extract video ID from YouTube Music URL: {url}")

        logger.info("Resolving YouTube Music URL", extra={"url": url, "video_id": video_id})
        youtube_url = self._youtube.get_video_url(video_id)
        return await self._youtube.extract_metadata(youtube_url)

    def extract_video_id(self, url: str) -> str | None:
        """Extract the 11-character video ID from a YouTube Music URL.

        Args:
            url: The candidate URL string.

        Returns:
            The extracted video ID or ``None`` if parsing fails.
        """
        return extract_youtube_video_id(url)
