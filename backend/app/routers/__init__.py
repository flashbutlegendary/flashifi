"""API route modules for the FlashiFi application."""

from app.routers.health import router as health_router
from app.routers.metadata import router as metadata_router
from app.routers.download import router as download_router
from app.routers.progress import router as progress_router

__all__ = ["health_router", "metadata_router", "download_router", "progress_router"]
