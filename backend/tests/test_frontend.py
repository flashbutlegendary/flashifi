"""
Tests for the static files and frontend routes in the FastAPI application.
Ensures that all frontend assets and configuration files are correctly served
from the new dedicated 'frontend' directory.
"""


def test_root_serves_frontend_index(client):
    """The root URL must serve the frontend index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "FlashiFi" in response.text
    assert "High-Quality Music Downloader" in response.text


def test_manifest_served_correctly(client):
    """manifest.json must be served correctly with JSON content type."""
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert data["name"] == "FlashiFi - Modern Audio Downloader"


def test_service_worker_served_correctly(client):
    """sw.js must be served correctly with javascript content type."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")
    assert "flashifi-v1" in response.text


def test_favicon_served_correctly(client):
    """favicon.ico must be served correctly."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200


def test_robots_txt_served_correctly(client):
    """robots.txt must be served correctly."""
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert "User-agent" in response.text


def test_sitemap_xml_served_correctly(client):
    """sitemap.xml must be served correctly."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response.headers.get("content-type", "")
    assert "urlset" in response.text


def test_assets_mounted_correctly(client):
    """Static assets must be served correctly from the mounted /assets route."""
    response = client.get("/assets/css/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    assert "bg-main" in response.text
