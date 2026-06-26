"""
Tests for app.services.resolver.ResolverService.
Validates routing logic: YouTube URLs → YouTube service, Spotify URLs → Spotify
metadata + YouTube search, plain text → YouTube search.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.resolver import ResolverService
from app.services.youtube import YouTubeService, SearchResult
from app.services.ranking import RankingService
from app.config.settings import Settings
from app.models.enums import SourcePlatform


@pytest.fixture
def mock_resolver():
    """Build a ResolverService with fully-mocked dependencies."""
    settings = Settings()
    youtube = AsyncMock(spec=YouTubeService)
    ranking = MagicMock(spec=RankingService)

    # Import optional services — they may or may not exist yet
    try:
        from app.services.youtube_music import YouTubeMusicService

        youtube_music = AsyncMock(spec=YouTubeMusicService)
    except ImportError:
        youtube_music = AsyncMock()

    try:
        from app.services.spotify import SpotifyService

        spotify = AsyncMock(spec=SpotifyService)
    except ImportError:
        spotify = AsyncMock()

    return ResolverService(settings, youtube, youtube_music, spotify, ranking)


def _fake_search_result(**overrides) -> SearchResult:
    """Quick factory for a SearchResult with defaults."""
    defaults = dict(
        video_id="yt1",
        title="Song",
        uploader="Artist",
        channel_id="c1",
        duration=200,
        view_count=1000,
        url="https://youtube.com/watch?v=yt1",
    )
    defaults.update(overrides)
    return SearchResult(**defaults)


@pytest.mark.asyncio
async def test_youtube_url_routes_to_youtube(mock_resolver):
    """A direct YouTube URL should call extract_metadata on the YouTube service."""
    mock_resolver._youtube.extract_metadata.return_value = {
        "id": "abc",
        "title": "Test",
        "uploader": "Channel",
        "duration": 200,
        "thumbnail": "http://img.com/thumb.jpg",
        "view_count": 1000,
        "upload_date": "20240101",
    }
    result = await mock_resolver.resolve("https://www.youtube.com/watch?v=abc")
    assert result.source_platform == SourcePlatform.YOUTUBE
    mock_resolver._youtube.extract_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_spotify_routes_to_search(mock_resolver):
    """Spotify URLs should pull metadata from Spotify, then find a YouTube match."""
    try:
        from app.services.spotify import SpotifyTrack

        mock_resolver._spotify.extract_metadata.return_value = SpotifyTrack(
            title="Song", artist="Artist", album="Album"
        )
    except ImportError:
        # If SpotifyTrack doesn't exist, use a MagicMock
        mock_track = MagicMock()
        mock_track.title = "Song"
        mock_track.artist = "Artist"
        mock_track.album = "Album"
        mock_resolver._spotify.extract_metadata.return_value = mock_track

    mock_resolver._youtube.search.return_value = [_fake_search_result()]
    mock_resolver._ranking.rank_results.return_value = _fake_search_result()
    mock_resolver._youtube.extract_metadata.return_value = {
        "id": "yt1",
        "title": "Song",
        "uploader": "Artist",
        "duration": 200,
        "thumbnail": None,
        "view_count": 1000,
        "upload_date": None,
    }

    result = await mock_resolver.resolve(
        "https://open.spotify.com/track/abc123"
    )
    assert result.source_platform == SourcePlatform.SPOTIFY
    mock_resolver._spotify.extract_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_plain_text_routes_to_search(mock_resolver):
    """Plain-text queries should go through YouTube search + ranking."""
    mock_resolver._youtube.search.return_value = [
        _fake_search_result(
            title="Believer", uploader="Imagine Dragons", video_id="s1"
        )
    ]
    mock_resolver._ranking.rank_results.return_value = _fake_search_result(
        title="Believer", uploader="Imagine Dragons", video_id="s1"
    )
    mock_resolver._youtube.extract_metadata.return_value = {
        "id": "s1",
        "title": "Believer",
        "uploader": "Imagine Dragons",
        "duration": 200,
        "thumbnail": None,
        "view_count": 1000,
        "upload_date": None,
    }

    result = await mock_resolver.resolve("Believer Imagine Dragons")
    assert result.source_platform == SourcePlatform.SEARCH
    mock_resolver._youtube.search.assert_called_once()
