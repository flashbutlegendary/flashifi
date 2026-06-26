"""
Tests for the /download endpoint.
Validates task creation, format/quality validation, and file retrieval errors.
"""
from unittest.mock import AsyncMock


def test_download_returns_task_id(client):
    """POST /download must return 202 with a task_id when inputs are valid."""
    from app.core.dependencies import get_resolver, get_converter

    mock_resolver = AsyncMock()
    mock_converter = AsyncMock()

    client.app.dependency_overrides[get_resolver] = lambda: mock_resolver
    client.app.dependency_overrides[get_converter] = lambda: mock_converter

    response = client.post("/download", json={"query": "test song", "format": "mp3"})
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "accepted"

    client.app.dependency_overrides.clear()


def test_download_invalid_format_quality(client):
    """FLAC format with 320 kbps quality is an invalid combination."""
    response = client.post(
        "/download", json={"query": "test", "format": "flac", "quality": "320"}
    )
    assert response.status_code == 422


def test_download_missing_query(client):
    """POST /download with no query field must fail validation."""
    response = client.post("/download", json={})
    assert response.status_code == 422


def test_download_file_not_found(client):
    """GET /download/<bad-id> must return 404 when the task doesn't exist."""
    response = client.get("/download/nonexistent-task-id")
    assert response.status_code == 404
