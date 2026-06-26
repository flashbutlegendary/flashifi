"""
Track metadata resolution coordinator.

Acts as the central router for metadata queries, detecting the query type
(YouTube, YouTube Music, Spotify, or text search) and orchestrating search,
retrieval, ranking, and validation.
"""

import logging
from typing import Any

from app.config.settings import Settings
from app.exceptions.handlers import VideoUnavailableError
from app.models.enums import InputType, SourcePlatform
from app.schemas.responses import TrackMetadata
from app.services.ranking import RankingService
from app.services.spotify import SpotifyService
from app.services.youtube import YouTubeService
from app.services.youtube_music import YouTubeMusicService
from app.utils.time_utils import format_duration
from app.utils.validators import detect_input_type, validate_duration

logger = logging.getLogger(__name__)


class ResolverService:
    """Coordinates and routes metadata resolution tasks."""

    def __init__(
        self,
        settings: Settings,
        youtube_service: YouTubeService,
        youtube_music_service: YouTubeMusicService,
        spotify_service: SpotifyService,
        ranking_service: RankingService,
    ) -> None:
        """Initialize the resolver coordinator.

        Args:
            settings: Injected configuration settings.
            youtube_service: Injected YouTube service.
            youtube_music_service: Injected YouTube Music service.
            spotify_service: Injected Spotify service.
            ranking_service: Injected search result ranking service.
        """
        self._settings = settings
        self._youtube = youtube_service
        self._youtube_music = youtube_music_service
        self._spotify = spotify_service
        self._ranking = ranking_service

    async def resolve(self, query: str) -> TrackMetadata:
        """Detect the input type and resolve it to normalized ``TrackMetadata``.

        Args:
            query: The URL or search phrase.

        Returns:
            The normalized ``TrackMetadata`` response schema.
        """
        input_type = detect_input_type(query)
        logger.info(
            "Resolving query",
            extra={"query": query, "detected_type": input_type.value},
        )

        if input_type == InputType.YOUTUBE:
            return await self._resolve_youtube(query)
        elif input_type == InputType.YOUTUBE_MUSIC:
            return await self._resolve_youtube_music(query)
        elif input_type == InputType.SPOTIFY:
            return await self._resolve_spotify(query)
        else:
            return await self._resolve_search(query)

    async def _resolve_youtube(self, url: str) -> TrackMetadata:
        """Resolve a direct YouTube URL."""
        info = await self._youtube.extract_metadata(url)
        duration_seconds = int(info.get("duration") or 0)
        validate_duration(duration_seconds, self._settings.max_duration_seconds)
        return self._build_track_metadata(info, SourcePlatform.YOUTUBE)

    async def _resolve_youtube_music(self, url: str) -> TrackMetadata:
        """Resolve a YouTube Music URL."""
        info = await self._youtube_music.resolve_video(url)
        duration_seconds = int(info.get("duration") or 0)
        validate_duration(duration_seconds, self._settings.max_duration_seconds)
        return self._build_track_metadata(info, SourcePlatform.YOUTUBE_MUSIC)

    async def _resolve_spotify(self, url: str) -> TrackMetadata:
        """Resolve a Spotify URL by extracting metadata and finding a match on YouTube."""
        spotify_meta = await self._spotify.extract_metadata(url)
        search_query = f"{spotify_meta.title} {spotify_meta.artist}"
        search_results = await self._youtube.search(search_query)
        if not search_results:
            raise VideoUnavailableError(f"No YouTube match found for Spotify track: {search_query}")

        target_duration = (
            int(spotify_meta.duration_ms / 1000)
            if spotify_meta.duration_ms
            else None
        )
        best_match = self._ranking.rank_results(
            search_results,
            target_title=spotify_meta.title,
            target_artist=spotify_meta.artist,
            target_duration=target_duration,
        )
        if not best_match:
            raise VideoUnavailableError(f"No suitable YouTube match ranked for: {search_query}")

        video_url = self._youtube.get_video_url(best_match.video_id)
        info = await self._youtube.extract_metadata(video_url)

        duration_seconds = int(info.get("duration") or 0)
        validate_duration(duration_seconds, self._settings.max_duration_seconds)

        return self._build_track_metadata(info, SourcePlatform.SPOTIFY, spotify_meta)

    async def _resolve_search(self, query: str) -> TrackMetadata:
        """Resolve a plain-text search query by searching YouTube."""
        search_results = await self._youtube.search(query)
        if not search_results:
            raise VideoUnavailableError(f"No search results found on YouTube for: {query}")

        # Attempt to split query to target title and artist
        target_title = query
        target_artist = None
        if " - " in query:
            parts = query.split(" - ", 1)
            target_artist = parts[0].strip()
            target_title = parts[1].strip()
        elif " by " in query:
            parts = query.split(" by ", 1)
            target_title = parts[0].strip()
            target_artist = parts[1].strip()

        best_match = self._ranking.rank_results(
            search_results,
            target_title=target_title,
            target_artist=target_artist,
        )
        if not best_match:
            raise VideoUnavailableError(f"No suitable search match ranked for: {query}")

        video_url = self._youtube.get_video_url(best_match.video_id)
        info = await self._youtube.extract_metadata(video_url)

        duration_seconds = int(info.get("duration") or 0)
        validate_duration(duration_seconds, self._settings.max_duration_seconds)

        return self._build_track_metadata(info, SourcePlatform.SEARCH)

    def _build_track_metadata(
        self, info: dict[str, Any], source: SourcePlatform, spotify_meta: Any = None
    ) -> TrackMetadata:
        """Map raw yt-dlp metadata to the TrackMetadata schema."""
        title = info.get("title") or "Unknown Title"
        uploader = info.get("uploader") or "Unknown Channel"

        # Deduce artist from channel name (e.g. clean "Artist - Topic" or "VEVO")
        artist = uploader
        if artist.endswith(" - Topic"):
            artist = artist[:-8]

        album = None

        # Override with Spotify details if available
        if spotify_meta:
            title = spotify_meta.title
            artist = spotify_meta.artist
            album = spotify_meta.album

        duration_seconds = int(info.get("duration") or 0)
        duration_formatted = format_duration(duration_seconds)

        # Retrieve thumbnail URL
        thumbnail_url = info.get("thumbnail")
        if not thumbnail_url and info.get("thumbnails"):
            try:
                thumbnail_url = info["thumbnails"][-1].get("url")
            except (IndexError, KeyError):
                pass

        # Estimate size (320kbps MP3 size estimate)
        bitrate_bps = 320000
        size_bytes = duration_seconds * (bitrate_bps / 8)
        estimated_size_mb = round(size_bytes / (1024 * 1024), 2)

        # Standardise date (YYYYMMDD -> YYYY-MM-DD)
        upload_date = info.get("upload_date")
        if upload_date and len(upload_date) == 8 and upload_date.isdigit():
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        return TrackMetadata(
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            thumbnail_url=thumbnail_url,
            video_id=info.get("id") or "",
            uploader=uploader,
            estimated_size_mb=estimated_size_mb,
            source_platform=source,
            upload_date=upload_date,
            view_count=info.get("view_count"),
        )
