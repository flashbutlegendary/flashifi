"""
YouTube metadata and search service.

Provides search and metadata extraction features via ``yt-dlp``, using thread
executors to keep operations asynchronous and non-blocking.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings
from app.core.cache import cache
from app.exceptions.handlers import (
    DownloadError,
    VideoUnavailableError,
    YTDLPError,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a simplified video result from a YouTube search."""

    video_id: str
    title: str
    uploader: str
    channel_id: str | None
    duration: int  # seconds
    view_count: int
    url: str
    is_official: bool = False
    upload_date: str | None = None


class YouTubeService:
    """Handles communication with YouTube via yt-dlp."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the service with application settings.

        Args:
            settings: The application settings.
        """
        self._settings = settings

    async def extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract full metadata from a YouTube URL.

        Checks the in-memory cache first. If a cache miss occurs, extracts
        metadata in a separate thread to prevent event loop blocking.

        Args:
            url: The YouTube video URL.

        Returns:
            The raw info dictionary returned by yt-dlp.

        Raises:
            VideoUnavailableError: If the video is private, deleted, or missing.
            YTDLPError: For general extraction or connection issues.
        """
        cache_key = f"yt_meta:{url}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Metadata cache hit", extra={"url": url})
            return cached

        logger.info("Extracting YouTube metadata", extra={"url": url})
        ydl_opts = {
            "extract_flat": False,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": self._settings.download_timeout,
        }
        if self._settings.resolved_cookie_file:
            ydl_opts["cookiefile"] = self._settings.resolved_cookie_file
        elif self._settings.cookie_browser:
            ydl_opts["cookiesfrombrowser"] = (self._settings.cookie_browser,)

        try:
            info = await asyncio.to_thread(self._run_ytdlp_extract, url, ydl_opts)
        except Exception as exc:
            exc_str = str(exc).lower()
            if "private" in exc_str or "unavailable" in exc_str or "not found" in exc_str or "sign in" in exc_str:
                raise VideoUnavailableError(f"Video is unavailable or restricted: {exc}") from exc
            raise YTDLPError(f"Failed to extract YouTube metadata: {exc}") from exc

        if not info:
            raise VideoUnavailableError("No video information retrieved")

        # Cache the resulting dictionary
        cache.set(cache_key, info, ttl=self._settings.metadata_cache_ttl)
        return info

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search YouTube for videos matching a query.

        Queries are cached to reduce latency. Official/verified channel state
        is inferred by inspecting channel names and badges.

        Args:
            query: The search query.
            limit: The maximum number of results to retrieve.

        Returns:
            A list of ``SearchResult`` instances.

        Raises:
            YTDLPError: If the search query fails.
        """
        cache_key = f"yt_search:{query}:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Search cache hit", extra={"query": query, "limit": limit})
            return cached

        logger.info("Searching YouTube", extra={"query": query, "limit": limit})
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": self._settings.download_timeout,
        }
        if self._settings.resolved_cookie_file:
            ydl_opts["cookiefile"] = self._settings.resolved_cookie_file
        elif self._settings.cookie_browser:
            ydl_opts["cookiesfrombrowser"] = (self._settings.cookie_browser,)

        search_url = f"ytsearch{limit}:{query}"
        try:
            info = await asyncio.to_thread(self._run_ytdlp_extract, search_url, ydl_opts)
        except Exception as exc:
            raise YTDLPError(f"YouTube search failed: {exc}") from exc

        results: list[SearchResult] = []
        if info and "entries" in info:
            for entry in info["entries"]:
                if not entry:
                    continue

                video_id = entry.get("id") or entry.get("url")
                if not video_id:
                    continue

                title = entry.get("title") or "Unknown Title"
                uploader = entry.get("uploader") or "Unknown Uploader"
                channel_id = entry.get("channel_id")
                duration = int(entry.get("duration") or 0)
                view_count = int(entry.get("view_count") or 0)
                url = self.get_video_url(video_id)
                upload_date = entry.get("upload_date")

                # Infer if official/verified channel based on common patterns
                uploader_lower = uploader.lower()
                is_official = any(
                    kw in uploader_lower
                    for kw in ["official", "vevo", "topic", "records", "music"]
                )

                results.append(
                    SearchResult(
                        video_id=video_id,
                        title=title,
                        uploader=uploader,
                        channel_id=channel_id,
                        duration=duration,
                        view_count=view_count,
                        url=url,
                        is_official=is_official,
                        upload_date=upload_date,
                    )
                )

        cache.set(cache_key, results, ttl=self._settings.search_cache_ttl)
        return results

    def get_video_url(self, video_id: str) -> str:
        """Build a standard YouTube URL from a video ID.

        Args:
            video_id: The YouTube video ID.

        Returns:
            The complete watch URL.
        """
        return f"https://www.youtube.com/watch?v={video_id}"

    def _run_ytdlp_extract(self, url: str, ydl_opts: dict[str, Any]) -> dict[str, Any]:
        """Synchronously execute yt-dlp. Runs inside a worker thread.

        Args:
            url: The URL or query to process.
            ydl_opts: The yt-dlp option dictionary.

        Returns:
            The raw info dictionary.
        """
        import yt_dlp

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
