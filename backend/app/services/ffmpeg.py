"""
FFmpeg audio conversion service.

Wraps FFmpeg execution to transcode raw audio downloads to target containers
(MP3, FLAC, WAV) and bitrates.
"""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

from app.config.settings import Settings
from app.exceptions.handlers import ConversionError
from app.models.enums import AudioFormat, AudioQuality

logger = logging.getLogger(__name__)


class FFmpegService:
    """Manages audio format conversion using the external FFmpeg tool."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the FFmpeg service.

        Args:
            settings: Injected configuration settings.
        """
        self._settings = settings
        self._ffmpeg_path = settings.ffmpeg_path

    async def convert(
        self,
        input_path: Path,
        output_path: Path,
        audio_format: AudioFormat,
        quality: AudioQuality,
    ) -> Path:
        """Transcode an audio file to a specified format and quality.

        Args:
            input_path: Path to the raw downloaded audio file.
            output_path: Target path where the converted file should be saved.
            audio_format: Target codec container (e.g. mp3, flac, wav).
            quality: Bitrate quality setting (e.g. 320, lossless).

        Returns:
            The Path to the newly created, converted audio file.

        Raises:
            ConversionError: If the input file is missing, FFmpeg exits with
                a non-zero status, or the output file is not generated.
        """
        if not input_path.exists():
            raise ConversionError(f"Input file not found for conversion: {input_path}")

        args = self.get_ffmpeg_args(input_path, output_path, audio_format, quality)
        logger.info(
            "Executing FFmpeg",
            extra={
                "input_path": str(input_path),
                "output_path": str(output_path),
                "format": audio_format.value,
                "quality": quality.value,
            },
        )

        try:
            result = await asyncio.to_thread(self._run_ffmpeg, args)
        except Exception as exc:
            raise ConversionError(f"Failed to initiate FFmpeg process: {exc}") from exc

        if result.returncode != 0:
            logger.error(
                "FFmpeg transcoding failed",
                extra={"returncode": result.returncode, "stderr": result.stderr},
            )
            raise ConversionError(f"FFmpeg conversion failed: {result.stderr.strip()}")

        if not output_path.exists():
            raise ConversionError(f"FFmpeg finished but output file is missing: {output_path}")

        return output_path

    def get_ffmpeg_args(
        self,
        input_path: Path,
        output_path: Path,
        audio_format: AudioFormat,
        quality: AudioQuality,
    ) -> list[str]:
        """Construct the FFmpeg command line arguments.

        Args:
            input_path: The raw source file.
            output_path: The target destination file.
            audio_format: Target codec format.
            quality: Target quality tier.

        Returns:
            List of command line tokens.

        Raises:
            ConversionError: If the format is not recognized.
        """
        # Base arguments: -i input, -y (overwrite), -vn (disable video stream)
        args = [self._ffmpeg_path, "-i", str(input_path), "-y", "-vn"]

        if audio_format == AudioFormat.MP3:
            # MP3 transcoding using libmp3lame
            args.extend(["-codec:a", "libmp3lame", "-b:a", f"{quality.value}k"])
        elif audio_format == AudioFormat.FLAC:
            # FLAC lossless encoding
            args.extend(["-codec:a", "flac"])
        elif audio_format == AudioFormat.WAV:
            # WAV uncompressed PCM encoding
            args.extend(["-codec:a", "pcm_s16le"])
        else:
            raise ConversionError(f"Unsupported conversion format: {audio_format.value}")

        args.append(str(output_path))
        return args

    async def check_available(self) -> bool:
        """Verify if the FFmpeg executable is available on the system.

        First checks the system path using ``shutil.which``, then executes
        the configured command with ``-version`` to confirm.

        Returns:
            ``True`` if FFmpeg is reachable and functional, otherwise ``False``.
        """
        # 1. Quick check using path resolver
        if shutil.which(self._ffmpeg_path):
            return True

        # 2. Executable validation via execution
        try:
            result = await asyncio.to_thread(
                self._run_ffmpeg, [self._ffmpeg_path, "-version"]
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_ffmpeg(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Synchronously execute the FFmpeg process. Runs inside a worker thread."""
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes safety timeout
        )
