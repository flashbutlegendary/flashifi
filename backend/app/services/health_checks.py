"""
Health check service.

Executes diagnostic checks on application dependencies (FFmpeg, yt-dlp), temp directory
permissions, disk availability, and reports overall status.
"""

import asyncio
import logging
import shutil
import subprocess
import time
from pathlib import Path

from app.config.settings import Settings
from app.core.version import get_version_info
from app.schemas.responses import HealthResponse, VersionInfo

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Performs system diagnostics for health monitoring."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the health service.

        Records the instantiation time to track uptime.

        Args:
            settings: Injected configuration settings.
        """
        self._settings = settings
        self._start_time = time.time()

    async def run_checks(self) -> HealthResponse:
        """Run diagnostic checks across all critical components.

        Checks:
            1. FFmpeg availability on PATH.
            2. yt-dlp availability on PATH.
            3. Writable permissions on the temporary workspace directory.
            4. Free disk space on the temporary workspace partition.
            5. Application uptime and version info.

        Returns:
            A populated ``HealthResponse`` instance.
        """
        from app.services.ffmpeg import FFmpegService

        logger.debug("Running system health check diagnostics")

        # 1. Check FFmpeg
        ffmpeg = FFmpegService(self._settings)
        ffmpeg_ok = await ffmpeg.check_available()

        # 2. Check yt-dlp
        ytdlp_ok = await self._check_ytdlp_available()

        # 3. Check if temp directory is writable
        temp_dir = self._settings.temp_dir
        temp_writable = False
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            test_file = temp_dir / f".health_check_{int(time.time())}"
            test_file.write_text("healthcheck")
            test_file.unlink()
            temp_writable = True
        except Exception as exc:
            logger.error("Temporary directory is not writable", extra={"path": str(temp_dir)}, exc_info=True)

        # 4. Determine available disk space in MB
        disk_space_mb = 0.0
        try:
            usage = shutil.disk_usage(temp_dir)
            disk_space_mb = usage.free / (1024 * 1024)
        except Exception as exc:
            logger.warning("Could not check disk usage", extra={"path": str(temp_dir)}, exc_info=True)

        # 5. Compute overall status
        if not temp_writable:
            # Unwritable temp directory is an unrecoverable failure for downloader
            status = "unhealthy"
        elif not ffmpeg_ok or not ytdlp_ok:
            # Missing core dependencies degrades the service
            status = "degraded"
        else:
            status = "healthy"

        # 6. Build Version metadata
        v_info = get_version_info()
        version = VersionInfo(
            app_version=v_info.get("app_version") or "1.0.0",
            build_date=v_info.get("build_date") or "",
            git_commit=v_info.get("git_commit"),
        )

        uptime = time.time() - self._start_time

        return HealthResponse(
            status=status,
            version=version,
            ffmpeg_available=ffmpeg_ok,
            ytdlp_available=ytdlp_ok,
            temp_dir_writable=temp_writable,
            disk_space_mb=round(disk_space_mb, 2),
            uptime_seconds=round(uptime, 2),
        )

    async def _check_ytdlp_available(self) -> bool:
        """Check if the yt-dlp CLI tool is accessible and runnable."""
        if shutil.which("yt-dlp"):
            return True

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
