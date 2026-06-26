"""
Tests for the /health endpoint.
Validates health-check response schema, version info, and status values.
"""


def test_health_returns_200(client):
    """Health endpoint must return 200 with all required fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "ffmpeg_available" in data
    assert "ytdlp_available" in data
    assert "temp_dir_writable" in data
    assert "disk_space_mb" in data
    assert "uptime_seconds" in data


def test_health_version_info(client):
    """Version block must contain app_version and build_date."""
    response = client.get("/health")
    data = response.json()
    version = data["version"]
    assert "app_version" in version
    assert "build_date" in version


def test_health_status_values(client):
    """Status field must be one of the three allowed values."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
