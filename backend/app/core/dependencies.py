"""
FastAPI dependency injection functions.

Each function extracts a dependency from ``request.app.state`` or constructs
a service graph on demand. These are used with ``Depends()`` in route handlers
to keep routes thin and testable.

All service constructors follow the pattern of accepting a ``Settings`` instance
and, where needed, other services as constructor arguments.
"""

from fastapi import Request

from app.config.settings import Settings
from app.services.converter import ConverterService
from app.services.downloader import DownloaderService
from app.services.ffmpeg import FFmpegService
from app.services.health_checks import HealthCheckService
from app.services.ranking import RankingService
from app.services.resolver import ResolverService
from app.services.spotify import SpotifyService
from app.services.thumbnail import ThumbnailService
from app.services.youtube import YouTubeService
from app.services.youtube_music import YouTubeMusicService
from app.workers.task_manager import TaskManager


def get_settings(request: Request) -> Settings:
    """Retrieve the shared application settings from app state.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The application-wide ``Settings`` instance.
    """
    return request.app.state.settings


def get_task_manager(request: Request) -> TaskManager:
    """Retrieve the shared task manager from app state.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The application-wide ``TaskManager`` instance.
    """
    return request.app.state.task_manager


def get_health_service(request: Request) -> HealthCheckService:
    """Retrieve the shared health check service from app state.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The application-wide ``HealthCheckService`` instance.
    """
    return request.app.state.health_service


def get_resolver(request: Request) -> ResolverService:
    """Build a ResolverService with all required sub-services.

    Constructs the full resolution pipeline: YouTube, YouTube Music,
    Spotify, and Ranking services are wired together and injected
    into the ResolverService.

    Args:
        request: The incoming FastAPI request.

    Returns:
        A fully-configured ``ResolverService`` instance.
    """
    settings = get_settings(request)
    youtube = YouTubeService(settings)
    youtube_music = YouTubeMusicService(settings, youtube)
    spotify = SpotifyService(settings)
    ranking = RankingService()
    return ResolverService(settings, youtube, youtube_music, spotify, ranking)


def get_converter(request: Request) -> ConverterService:
    """Build a ConverterService with downloader and FFmpeg sub-services.

    Constructs the conversion pipeline: the DownloaderService handles
    yt-dlp audio extraction and the FFmpegService handles format
    transcoding.

    Args:
        request: The incoming FastAPI request.

    Returns:
        A fully-configured ``ConverterService`` instance.
    """
    settings = get_settings(request)
    downloader = DownloaderService(settings)
    ffmpeg = FFmpegService(settings)
    return ConverterService(settings, downloader, ffmpeg)


def get_thumbnail_service(request: Request) -> ThumbnailService:
    """Build a ThumbnailService for fetching and embedding album art.

    Args:
        request: The incoming FastAPI request.

    Returns:
        A configured ``ThumbnailService`` instance.
    """
    settings = get_settings(request)
    return ThumbnailService(settings)
