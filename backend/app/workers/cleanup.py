"""
Background cleanup worker for stale temporary files and completed tasks.

Runs on a configurable interval, removing temporary download directories
and completed/failed task records that have exceeded their maximum age.
Designed to run as an ``asyncio.Task`` throughout the application lifespan.
"""

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

from app.config.settings import Settings

if TYPE_CHECKING:
    from app.workers.task_manager import TaskManager

logger = logging.getLogger(__name__)


class CleanupWorker:
    """Background worker that periodically cleans up stale resources.

    Responsibilities:
        - Remove temporary download directories older than the configured max age.
        - Purge completed/failed task records and their associated files.

    Args:
        settings: Application settings providing temp_dir, cleanup interval, and max age.
        task_manager: Reference to the shared TaskManager instance.

    Usage::

        worker = CleanupWorker(settings, task_manager)
        worker.start()       # call during startup
        await worker.stop()  # call during shutdown
    """

    def __init__(self, settings: Settings, task_manager: "TaskManager") -> None:
        self._settings = settings
        self._task_manager = task_manager
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the cleanup loop as a background asyncio task."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Cleanup worker started",
            extra={
                "interval_seconds": self._settings.cleanup_interval_seconds,
                "max_age_seconds": self._settings.cleanup_max_age_seconds,
            },
        )

    async def stop(self) -> None:
        """Gracefully stop the cleanup loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup worker stopped")

    async def _run_loop(self) -> None:
        """Main loop that sleeps between cleanup passes."""
        while self._running:
            try:
                await asyncio.sleep(self._settings.cleanup_interval_seconds)
                await self.cleanup_once()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error during cleanup pass")

    async def cleanup_once(self) -> None:
        """Execute a single cleanup pass.

        Cleans temporary directories in a thread pool to avoid blocking
        the event loop, then purges stale task records synchronously.
        """
        removed_dirs = await asyncio.to_thread(self._cleanup_temp_dirs)
        removed_tasks = self._cleanup_stale_tasks()
        if removed_dirs or removed_tasks:
            logger.info(
                "Cleanup pass complete",
                extra={"removed_dirs": removed_dirs, "removed_tasks": removed_tasks},
            )

    def _cleanup_temp_dirs(self) -> int:
        """Remove temporary download directories older than the configured max age.

        Returns:
            Number of directories removed.
        """
        temp_dir = self._settings.temp_dir
        if not temp_dir.exists():
            return 0

        cutoff = time.time() - self._settings.cleanup_max_age_seconds
        removed = 0

        for item in temp_dir.iterdir():
            if not item.is_dir():
                continue
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    logger.info("Cleaned up temp directory", extra={"path": str(item)})
                    removed += 1
            except OSError:
                logger.warning(
                    "Failed to stat/remove temp directory",
                    extra={"path": str(item)},
                    exc_info=True,
                )

        return removed

    def _cleanup_stale_tasks(self) -> int:
        """Remove stale completed/failed tasks and their output files.

        Returns:
            Number of tasks removed.
        """
        stale_ids = self._task_manager.get_stale_tasks(self._settings.cleanup_max_age_seconds)
        removed = 0

        for task_id in stale_ids:
            task = self._task_manager.get_task(task_id)
            if task and task.file_path:
                try:
                    if task.file_path.exists():
                        task.file_path.unlink()
                    # Also try to remove the parent workspace directory
                    parent = task.file_path.parent
                    if parent.exists() and parent != self._settings.temp_dir:
                        shutil.rmtree(parent, ignore_errors=True)
                except OSError:
                    logger.warning(
                        "Failed to remove task file",
                        extra={"task_id": task_id, "path": str(task.file_path)},
                        exc_info=True,
                    )
            self._task_manager.remove_task(task_id)
            logger.info("Removed stale task", extra={"task_id": task_id})
            removed += 1

        return removed
