"""
Audio conversion coordinator service.

Coordinates the end-to-end process of downloading the raw audio file,
converting it to the requested format and quality using FFmpeg, cleaning up
the raw intermediate file, and validating the final file size.
"""

import logging
from pathlib import Path
from typing import Callable

from app.config.settings import Settings
from app.exceptions.handlers import ConversionError
from app.models.enums import AudioFormat, AudioQuality
from app.services.downloader import DownloaderService
from app.services.ffmpeg import FFmpegService
from app.utils.validators import validate_file_size

logger = logging.getLogger(__name__)


class ConverterService:
    """Coordinates downloading and transcoding workflow."""

    def __init__(
        self,
        settings: Settings,
        downloader: DownloaderService,
        ffmpeg: FFmpegService,
    ) -> None:
        """Initialize the converter coordinator.

        Args:
            settings: Injected configuration settings.
            downloader: Injected downloader service.
            ffmpeg: Injected FFmpeg service.
        """
        self._settings = settings
        self._downloader = downloader
        self._ffmpeg = ffmpeg

    async def process(
        self,
        video_id: str,
        output_dir: Path,
        audio_format: AudioFormat,
        quality: AudioQuality,
        filename: str,
        progress_callback: Callable[[float, str, str], None] | None = None,
    ) -> Path:
        """Download raw audio from YouTube and convert it to the desired format.

        Saves the resulting file as ``filename`` in ``output_dir``. Deletes the
        intermediate raw file and verifies that the output size is within
        configured limits.

        Args:
            video_id: The YouTube video identifier.
            output_dir: The directory where the final file should be stored.
            audio_format: Target format (MP3, FLAC, WAV).
            quality: Target audio quality.
            filename: Destination filename.
            progress_callback: Optional progress indicator callback.

        Returns:
            The Path to the final converted audio file.

        Raises:
            ConversionError: If raw download, transcoding, or size validation fails.
        """
        # 1. Download raw audio
        raw_path = await self._downloader.download(
            video_id=video_id,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

        # 2. Define final target path
        output_path = output_dir / filename

        # 3. Transcode raw audio to target container/bitrate
        logger.info(
            "Starting audio transcoding",
            extra={
                "video_id": video_id,
                "format": audio_format.value,
                "quality": quality.value,
                "output_path": str(output_path),
            },
        )

        try:
            # Complete the download phase on progress meter if callback provided
            if progress_callback:
                try:
                    progress_callback(100.0, "0 B/s", "0s")
                except Exception:
                    pass

            await self._ffmpeg.convert(
                input_path=raw_path,
                output_path=output_path,
                audio_format=audio_format,
                quality=quality,
            )
        finally:
            # 4. Cleanup intermediary raw download file
            if raw_path.exists() and raw_path != output_path:
                try:
                    raw_path.unlink()
                    logger.debug("Cleaned up raw input file", extra={"path": str(raw_path)})
                except Exception as exc:
                    logger.warning(
                        "Failed to clean up raw intermediate file",
                        extra={"path": str(raw_path)},
                        exc_info=True,
                    )

        # 5. Verify the resulting file exists and complies with size restrictions
        if not output_path.exists():
            raise ConversionError(f"Transcoding completed but output file not found: {output_path}")

        file_size = output_path.stat().st_size
        validate_file_size(file_size, self._settings.max_file_size_bytes)

        logger.info(
            "Transcoding workflow completed successfully",
            extra={"output_path": str(output_path), "size_bytes": file_size},
        )
        return output_path
