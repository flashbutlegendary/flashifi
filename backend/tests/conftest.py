"""
Shared test fixtures for FlashiFi backend tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.config.settings import Settings
from app.workers.task_manager import TaskManager
from main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Settings configured for testing — disables background cleanup."""
    return Settings(
        debug=True,
        log_level="DEBUG",
        temp_base_dir="/tmp/flashifi_test",
        cleanup_interval_seconds=99999,  # Don't run cleanup in tests
    )


@pytest.fixture
def task_manager() -> TaskManager:
    """Fresh TaskManager instance for each test."""
    return TaskManager()


@pytest.fixture
def app():
    """Create a fresh FastAPI application instance."""
    application = create_app()
    return application


@pytest.fixture
def client(app) -> TestClient:
    """TestClient wired to the test application."""
    with TestClient(app) as c:
        yield c
