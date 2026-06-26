"""
Spotify metadata service.

Provides track metadata extraction from Spotify URLs using Spotify's oEmbed API
and HTML scraping, avoiding any need for Spotify API credentials.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config.settings import Settings
from app.core.cache import cache
from app.exceptions.handlers import SpotifyExtractionError

logger = logging.getLogger(__name__)


@dataclass
class SpotifyTrack:
    """Represents metadata extracted for a Spotify track."""

    title: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None
    thumbnail_url: str | None = None


class SpotifyService:
    """Extracts metadata from Spotify track URLs."""

    OEMBED_URL = "https://open.spotify.com/oembed"

    def __init__(self, settings: Settings) -> None:
        """Initialize the service.

        Args:
            settings: Injected application configuration.
        """
        self._settings = settings

    async def extract_metadata(self, url: str) -> SpotifyTrack:
        """Extract metadata for a Spotify track URL.

        Checks the in-memory cache first. If a cache miss occurs, fetches
        oEmbed details and scrapes the public track page to construct a full
        metadata profile.

        Args:
            url: The Spotify track URL.

        Returns:
            A ``SpotifyTrack`` instance.

        Raises:
            SpotifyExtractionError: If metadata cannot be resolved or parsed.
        """
        cache_key = f"spotify_meta:{url}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Spotify metadata cache hit", extra={"url": url})
            return cached

        logger.info("Extracting Spotify metadata", extra={"url": url})

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Initialize default values
        title = ""
        artist = ""
        thumbnail_url = None
        duration_ms = None
        album = None

        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            # 1. Fetch via oEmbed
            try:
                oembed_resp = await client.get(self.OEMBED_URL, params={"url": url})
                if oembed_resp.status_code == 200:
                    data = oembed_resp.json()
                    raw_title = data.get("title", "")
                    thumbnail_url = data.get("thumbnail_url")

                    # oEmbed title can be "Song Title" or "Song Title by Artist"
                    if " by " in raw_title:
                        parts = raw_title.rsplit(" by ", 1)
                        title = parts[0].strip()
                        artist = parts[1].strip()
                    else:
                        title = raw_title.strip()
            except Exception as exc:
                logger.warning("Spotify oEmbed request failed, falling back to scraping", exc_info=True)

            # 2. Fetch public page HTML to scrape metadata tags
            try:
                html_resp = await client.get(url)
                if html_resp.status_code == 200:
                    html = html_resp.text

                    # Regex patterns for meta tags
                    og_title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
                    og_desc_match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
                    og_image_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)

                    if og_title_match and not title:
                        title = og_title_match.group(1).strip()

                    if og_image_match and not thumbnail_url:
                        thumbnail_url = og_image_match.group(1).strip()

                    # Parse description to extract artist/album info
                    # Standard og:description for tracks is:
                    # "Listen to [Song] on Spotify. [Artist] · Song · [Year]." or
                    # "[Artist] · Song · [Year]."
                    if og_desc_match:
                        desc = og_desc_match.group(1).strip()
                        marker = "on Spotify. "
                        if marker in desc:
                            desc = desc.split(marker, 1)[1]

                        # Split on bullet points or middle dots
                        parts = [p.strip() for p in re.split(r'·|•| - ', desc)]
                        if parts:
                            scraped_artist = parts[0]
                            if scraped_artist and not artist:
                                artist = scraped_artist
                            
                            # Often: [Artist] · Song · [Year] or [Artist] · Album · [Year]
                            if len(parts) > 2 and "song" not in parts[1].lower():
                                album = parts[1]

                    # Parse duration if embedded in json metadata
                    duration_match = re.search(r'"durationMS":\s*(\d+)', html)
                    if duration_match:
                        duration_ms = int(duration_match.group(1))
            except Exception as exc:
                logger.warning("Spotify page scraping failed", exc_info=True)

        # Fallbacks if extraction failed
        if not title:
            # Try parsing from URL as last resort
            track_id_match = re.search(r'/track/([A-Za-z0-9]+)', url)
            if track_id_match:
                title = f"Spotify Track {track_id_match.group(1)}"
            else:
                raise SpotifyExtractionError("Failed to extract track title from Spotify URL")

        if not artist:
            artist = "Unknown Artist"

        track = SpotifyTrack(
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            thumbnail_url=thumbnail_url,
        )

        cache.set(cache_key, track, ttl=self._settings.metadata_cache_ttl)
        return track
