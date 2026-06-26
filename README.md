# ⚡ Flashify

**Flashify** is a modern, high-performance music downloader web app. Search for any song by name, paste a YouTube / YouTube Music / Spotify link, and download it in MP3, FLAC, or WAV — right from your browser.

> Powered by FastAPI + yt-dlp + FFmpeg on the backend, with a fully static frontend served from the same container.

---

## ✨ Features

- 🎵 Download audio from YouTube, YouTube Music, and Spotify (metadata-resolved)
- 🎚️ Choose format: **MP3**, **FLAC**, **WAV**
- 🔍 Plain search queries supported — no URL needed
- 📡 Real-time download progress via polling
- 🌐 Single-container deployment (frontend + backend in one Docker image)
- 🧹 Auto-cleanup of temp files

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.12), Uvicorn |
| **Downloader** | yt-dlp |
| **Transcoder** | FFmpeg |
| **HTTP Client** | httpx (async) |
| **Frontend** | Vite / Vanilla JS (pre-built static) |
| **Container** | Docker (single image, serves both) |

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.12+
- FFmpeg installed and on PATH
- Git

### Run locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/flashify.git
cd flashify

# 2. Set up Python env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate          # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# 5. Run
python main.py
# → http://localhost:8000
```

### Run with Docker

```bash
# Build from repo root (required — copies both backend/ and frontend/)
docker build -t flashify -f backend/Dockerfile .

# Run
docker run -p 8000:8000 --env-file backend/.env flashify
# → http://localhost:8000
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System diagnostics (FFmpeg, yt-dlp, disk, uptime) |
| `GET` | `/metadata?query=` | Resolve track metadata without downloading |
| `POST` | `/download` | Enqueue a download task → returns `task_id` |
| `GET` | `/progress/{task_id}` | Poll download progress & stage |
| `GET` | `/download/{task_id}` | Stream the completed audio file |

Interactive docs: `http://localhost:8000/docs`

---

## ☁️ Deploy to Render (Free)

This repo includes a `render.yaml` for one-click deployment on [Render.com](https://render.com).

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New + → Web Service**
3. Connect your GitHub repo — Render detects `render.yaml` automatically
4. Click **Apply** and wait for the build (~3–5 min)
5. Your app is live at `https://flashify.onrender.com` 🎉

> **Note:** Free tier instances spin down after 15 minutes of inactivity. The first request after sleep takes ~30 seconds (cold start).

---

## 📁 Project Structure

```
flashify/
├── backend/
│   ├── app/
│   │   ├── config/         # Settings (pydantic-settings)
│   │   ├── core/           # Lifespan, version
│   │   ├── middleware/     # Error handler, logging, request ID
│   │   ├── routers/        # API route handlers
│   │   └── services/       # yt-dlp, FFmpeg, cache logic
│   ├── tests/              # pytest suite
│   ├── main.py             # FastAPI app + static file serving
│   ├── Dockerfile          # Docker image (build from repo root)
│   ├── requirements.txt
│   └── .env.example        # Environment variable template
├── frontend/               # Pre-built static frontend
│   ├── index.html
│   └── assets/
├── render.yaml             # Render.com deployment config
└── .gitignore
```

---

## 📄 License

MIT
