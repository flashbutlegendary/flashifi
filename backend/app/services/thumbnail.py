"""
Thumbnail caching and resolution service.

Fetches and caches video thumbnail images / album art to optimize speed and
avoid hitting external source platform rate limits.
"""

import logging
from typing import Any

import httpx

from app.config.settings import Settings
from app.core.cache import cache

logger = logging.getLogger(__name__)


class ThumbnailService:
    """Manages retrieving and caching track thumbnail images."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the thumbnail service.

        Args:
            settings: Injected configuration settings.
        """
        self._settings = settings

    async def fetch_thumbnail_bytes(self, url: str) -> bytes | None:
        """Download and cache thumbnail image bytes from a URL.

        Checks the in-memory cache first to avoid redundant external network
        requests.

        Args:
            url: The absolute HTTP/HTTPS URL of the thumbnail image.

        Returns:
            The image binary bytes or ``None`` if retrieval fails.
        """
        if not url:
            return None

        cache_key = f"thumb_bytes:{url}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Thumbnail bytes cache hit", extra={"url": url})
            return cached

        logger.info("Fetching thumbnail image", extra={"url": url})
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    image_bytes = resp.content
                    # Cache the raw image bytes
                    cache.set(
                        cache_key,
                        image_bytes,
                        ttl=self._settings.thumbnail_cache_ttl,
                    )
                    return image_bytes
                else:
                    logger.warning(
                        "Failed to fetch thumbnail",
                        extra={"url": url, "status_code": resp.status_code},
                    )
        except Exception as exc:
            logger.error("Error fetching thumbnail image", extra={"url": url}, exc_info=True)

        return None

    def get_youtube_thumbnail_url(self, video_id: str) -> str:
        """Return the standard high-quality YouTube thumbnail URL for a video ID.

        Args:
            video_id: The YouTube video ID.

        Returns:
            The URL to the maxresdefault (or hqdefault fallback) image.
        """
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
