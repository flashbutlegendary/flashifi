# FlashiFi Backend API

FlashiFi is a modern, high-performance music downloader API. It allows users to resolve and download audio from standard YouTube URLs, YouTube Music, Spotify tracks, or plain search queries in multiple formats (MP3, FLAC, WAV) and qualities.

Internally, Spotify is used solely for metadata retrieval, and all downloads are resolved to YouTube audio streams, which are then processed and transcoded using `yt-dlp` and `FFmpeg`.

---

## 🛠️ Technology Stack

* **Web Framework**: FastAPI (Python 3.12+)
* **Data Validation**: Pydantic v2
* **Streaming & Search**: `yt-dlp`
* **Transcoding**: `FFmpeg`
* **HTTP Client**: `httpx` (async)
* **Testing Suite**: `pytest` & `pytest-asyncio`

---

## 🚀 Quick Start

### Prerequisites

Ensure you have **Python 3.12+** and **FFmpeg** installed on your system.

```bash
# Check python version
python --version

# Check FFmpeg availability
ffmpeg -version
```

### Installation

1. Clone or navigate to the backend repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and set up your variables:
   ```bash
   cp .env.example .env
   ```

### Running the API

Start the development server with hot-reload enabled:

```bash
python main.py
```

The API will be available at `http://localhost:8000`. You can explore the interactive Swagger documentation at `http://localhost:8000/docs`.

---

## 🧪 Running Tests

A comprehensive unit and integration test suite is provided. Run the tests using `pytest`:

```bash
pytest -v
```

---

## 📡 API Endpoints Reference

### 1. Health & Diagnostics
* **`GET /health`**
  * Returns system diagnostic information including FFmpeg and yt-dlp status, temporary directory permissions, free disk space, and uptime.

### 2. Metadata Resolution
* **`GET /metadata?query=<query>`**
  * Resolves a URL or query (YouTube, YouTube Music, Spotify, search) and returns track metadata (artist, title, duration, thumbnail) without starting a download.

### 3. Audio Download Workflow
* **`POST /download`**
  * Request Body:
    ```json
    {
      "query": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
      "format": "mp3",
      "quality": "320"
    }
    ```
  * Enqueues a download and conversion task. Returns 202 Accepted with a `task_id`.
* **`GET /progress/{task_id}`**
  * Returns the current processing stage (preparing, resolving, downloading, converting, cleaning, completed, failed) and percentage.
* **`GET /download/{task_id}`**
  * Streams the completed audio file for download once the task succeeds.

---

## 🐳 Docker Deployment

To build and run the application inside a container, run the build command from the repository root directory (where both `backend/` and `frontend/` folders live):

```bash
# Build image from repository root
docker build -t flashifi-backend -f backend/Dockerfile .

# Run container
docker run -p 8000:8000 --env-file backend/.env flashifi-backend
```
