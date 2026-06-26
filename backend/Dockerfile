# Use Python 3.12 slim image as the base
FROM python:3.12-slim

# Install system dependencies (FFmpeg is required for transcoding; Git is optional for version info)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy source folders
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Set environment variables
# FLASHIFI_WORKERS=1 keeps memory within Render's free tier (512 MB).
# PORT is overridden at runtime by Render's platform.
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONPATH=/app/backend \
    FLASHIFI_HOST=0.0.0.0 \
    FLASHIFI_PORT=8000 \
    FLASHIFI_WORKERS=1

# Expose API port
EXPOSE 8000

# Start application via Uvicorn
# Use shell form so $PORT is expanded at runtime (Render sets this dynamically)
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
