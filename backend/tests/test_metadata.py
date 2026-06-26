"""
Tests for the /metadata endpoint.
Validates query parameter validation and response schema with mocked resolver.
"""
from unittest.mock import patch, AsyncMock
from app.schemas.responses import TrackMetadata
from app.models.enums import SourcePlatform


def test_metadata_missing_query(client):
    """Metadata endpoint must reject requests with no query parameter."""
    response = client.get("/metadata")
    assert response.status_code == 422


def test_metadata_empty_query(client):
    """Metadata endpoint must reject an empty query string."""
    response = client.get("/metadata?query=")
    assert response.status_code == 422


def test_metadata_returns_correct_schema(client):
    """With a mocked resolver, the metadata endpoint returns correct shape."""
    mock_metadata = TrackMetadata(
        title="Test Song",
        artist="Test Artist",
        duration_seconds=200,
        duration_formatted="3:20",
        video_id="dQw4w9WgXcQ",
        source_platform=SourcePlatform.YOUTUBE,
    )

    with patch("app.routers.metadata.get_resolver") as mock_get_resolver:
        mock_resolver = AsyncMock()
        mock_resolver.resolve.return_value = mock_metadata
        mock_get_resolver.return_value = mock_resolver

        # Override the dependency at the app level
        from app.core.dependencies import get_resolver

        client.app.dependency_overrides[get_resolver] = lambda: mock_resolver

        response = client.get("/metadata?query=test")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["title"] == "Test Song"

        client.app.dependency_overrides.clear()
