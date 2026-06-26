"""
FastAPI application lifespan manager.

Handles startup and shutdown sequences: configures logging, creates
the temp directory, initialises shared services (TaskManager, CleanupWorker,
HealthCheckService), verifies FFmpeg availability, and tears everything
down gracefully on shutdown.
"""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.config.settings import Settings
from app.services.health_checks import HealthCheckService
from app.workers.cleanup import CleanupWorker
from app.workers.task_manager import TaskManager

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    """Configure application-wide structured logging.

    Sets up a console handler with a timestamp-prefixed format.
    The root logger level is driven by ``settings.log_level``.

    Args:
        settings: Application settings providing the desired log level.
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": (
                        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
                    ),
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["console"],
            },
            "loggers": {
                "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
                "uvicorn.access": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            },
        }
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    **Startup** (before ``yield``):
        1. Load settings and configure structured logging.
        2. Ensure the temporary download directory exists.
        3. Instantiate shared services and store them on ``app.state``.
        4. Start the background cleanup worker.
        5. Verify FFmpeg availability (non-blocking warning on failure).

    **Shutdown** (after ``yield``):
        1. Stop the cleanup worker gracefully.

    Yields:
        Control to the running FastAPI application.
    """
    # ── Startup ──────────────────────────────────────────────────────────
    settings = Settings()
    configure_logging(settings)

    # Ensure temp directory
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Temp directory ready", extra={"path": str(settings.temp_dir)})

    # Initialise shared services
    task_manager = TaskManager()
    cleanup_worker = CleanupWorker(settings, task_manager)
    health_service = HealthCheckService(settings)

    # Attach to app state for dependency injection
    app.state.settings = settings
    app.state.task_manager = task_manager
    app.state.cleanup_worker = cleanup_worker
    app.state.health_service = health_service

    # Start background workers
    cleanup_worker.start()

    # Verify FFmpeg (best-effort)
    try:
        from app.services.ffmpeg import FFmpegService

        ffmpeg = FFmpegService(settings)
        if await ffmpeg.check_available():
            logger.info("FFmpeg is available")
        else:
            logger.warning("FFmpeg is NOT available — audio conversion will fail")
    except Exception:
        logger.warning("Could not verify FFmpeg availability", exc_info=True)

    logger.info(
        "FlashiFi started",
        extra={"app_name": settings.app_name, "debug": settings.debug},
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    await cleanup_worker.stop()
    logger.info("FlashiFi shutdown complete")
