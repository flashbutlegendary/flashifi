"""
YouTube audio downloader service.

Handles yt-dlp downloads for raw audio streams, executing inside worker threads
and driving a progress callback to communicate real-time progress.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable

from app.config.settings import Settings
from app.exceptions.handlers import DownloadError
from app.utils.time_utils import format_eta, format_speed

logger = logging.getLogger(__name__)


class DownloaderService:
    """Manages audio downloads from YouTube using yt-dlp."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the downloader.

        Args:
            settings: Injected application configuration.
        """
        self._settings = settings

    async def download(
        self,
        video_id: str,
        output_dir: Path,
        progress_callback: Callable[[float, str, str], None] | None = None,
    ) -> Path:
        """Download raw audio from YouTube for a video ID.

        Saves the file to ``output_dir`` using the video ID as the filename
        stem. Runs inside a thread executor to keep operations non-blocking.

        Args:
            video_id: The YouTube video identifier.
            output_dir: Target directory path where the file will be saved.
            progress_callback: Optional function invoked with download metrics.

        Returns:
            The Path to the downloaded raw audio file.

        Raises:
            DownloadError: If download fails or the output file is missing.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info("Starting download", extra={"video_id": video_id, "output_dir": str(output_dir)})

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
            "no_warnings": True,
            "quiet": True,
            "socket_timeout": self._settings.download_timeout,
        }

        if progress_callback:
            ydl_opts["progress_hooks"] = [self._make_progress_hook(progress_callback)]

        try:
            filepath_str = await asyncio.to_thread(self._run_download, url, ydl_opts)
            filepath = Path(filepath_str)

            # Robust fallback check: yt-dlp preparation path might not match final extension
            if not filepath.exists():
                matched_files = list(output_dir.glob(f"{video_id}.*"))
                if matched_files:
                    filepath = matched_files[0]
                else:
                    raise DownloadError(f"Downloaded file was not written to: {filepath_str}")

            logger.info("Download completed successfully", extra={"path": str(filepath)})
            return filepath

        except Exception as exc:
            raise DownloadError(f"Failed to download audio from YouTube: {exc}") from exc

    def _make_progress_hook(
        self, callback: Callable[[float, str, str], None]
    ) -> Callable[[dict[str, Any]], None]:
        """Create a progress hook function matching the yt-dlp API."""
        def hook(d: dict[str, Any]) -> None:
            status = d.get("status")
            if status == "downloading":
                downloaded = d.get("downloaded_bytes") or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

                percentage = 0.0
                if total > 0:
                    percentage = (downloaded / total) * 100

                speed = d.get("speed")
                speed_str = format_speed(speed) if speed is not None else "0 B/s"

                eta = d.get("eta")
                eta_str = format_eta(eta) if eta is not None else "0s"

                try:
                    callback(percentage, speed_str, eta_str)
                except Exception:
                    logger.warning("Downloader progress callback failed", exc_info=True)

            elif status == "finished":
                try:
                    callback(100.0, "0 B/s", "0s")
                except Exception:
                    pass

        return hook

    def _run_download(self, url: str, ydl_opts: dict[str, Any]) -> str:
        """Run yt-dlp in a blocking synchronous fashion."""
        import yt_dlp

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
