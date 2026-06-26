"""
Thread-safe in-memory task manager for tracking download task lifecycle.

Provides a centralized registry for creating, updating, and querying download
tasks. All operations are protected by a threading lock to ensure safe access
from both async handlers and background worker threads.
"""

import logging
import time
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.models.enums import DownloadStage

logger = logging.getLogger(__name__)


@dataclass
class TaskState:
    """Represents the current state of a download task.

    Attributes:
        task_id: Unique identifier for the task.
        stage: Current stage in the download pipeline.
        percentage: Download/conversion progress from 0.0 to 100.0.
        speed: Human-readable transfer speed (e.g. "2.5 MB/s").
        eta: Human-readable estimated time remaining (e.g. "00:12").
        message: Status message describing the current operation.
        file_path: Absolute path to the output file when completed.
        filename: Sanitized filename for Content-Disposition headers.
        file_size_bytes: Size of the output file in bytes.
        error: Error description if the task failed.
        created_at: Unix timestamp when the task was created.
        updated_at: Unix timestamp of the last state update.
    """

    task_id: str
    stage: DownloadStage = DownloadStage.PREPARING
    percentage: float = 0.0
    speed: str | None = None
    eta: str | None = None
    message: str = "Task created"
    file_path: Path | None = None
    filename: str | None = None
    file_size_bytes: int = 0
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class TaskManager:
    """Thread-safe in-memory task registry with progress tracking.

    This manager stores all active download tasks and provides methods
    to create, query, update, and remove them. It is designed to be
    shared across async route handlers and synchronous background threads.

    Usage::

        manager = TaskManager()
        task_id = manager.create_task()
        manager.update_progress(task_id, DownloadStage.DOWNLOADING, 42.0)
        manager.mark_completed(task_id, Path("/tmp/out.mp3"), "song.mp3", 4096)
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._lock = threading.Lock()

    def create_task(self) -> str:
        """Create a new task and return its unique ID.

        Returns:
            A UUID4 string identifying the new task.
        """
        task_id = str(uuid.uuid4())
        with self._lock:
            self._tasks[task_id] = TaskState(task_id=task_id)
        logger.info("Task created", extra={"task_id": task_id})
        return task_id

    def get_task(self, task_id: str) -> TaskState | None:
        """Retrieve a task by its ID.

        Args:
            task_id: The unique task identifier.

        Returns:
            The TaskState if found, otherwise None.
        """
        with self._lock:
            return self._tasks.get(task_id)

    def update_progress(
        self,
        task_id: str,
        stage: DownloadStage,
        percentage: float = 0.0,
        speed: str | None = None,
        eta: str | None = None,
        message: str = "",
    ) -> None:
        """Update the progress of an existing task.

        Args:
            task_id: The unique task identifier.
            stage: The current download pipeline stage.
            percentage: Progress percentage (clamped to 0–100).
            speed: Human-readable transfer speed string.
            eta: Human-readable estimated time remaining.
            message: Descriptive status message.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.stage = stage
                task.percentage = max(0.0, min(percentage, 100.0))
                task.speed = speed
                task.eta = eta
                task.message = message
                task.updated_at = time.time()

    def mark_completed(
        self,
        task_id: str,
        file_path: Path,
        filename: str,
        file_size_bytes: int,
    ) -> None:
        """Mark a task as successfully completed.

        Args:
            task_id: The unique task identifier.
            file_path: Absolute path to the output audio file.
            filename: Sanitized filename for download headers.
            file_size_bytes: Final file size in bytes.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.stage = DownloadStage.COMPLETED
                task.percentage = 100.0
                task.file_path = file_path
                task.filename = filename
                task.file_size_bytes = file_size_bytes
                task.message = "Download completed"
                task.updated_at = time.time()
        logger.info(
            "Task completed",
            extra={"task_id": task_id, "download_filename": filename, "size_bytes": file_size_bytes},
        )

    def mark_failed(self, task_id: str, error: str) -> None:
        """Mark a task as failed with an error description.

        Args:
            task_id: The unique task identifier.
            error: Human-readable error description.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.stage = DownloadStage.FAILED
                task.error = error
                task.message = f"Failed: {error}"
                task.updated_at = time.time()
        logger.error("Task failed", extra={"task_id": task_id, "error": error})

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the registry.

        Args:
            task_id: The unique task identifier.
        """
        with self._lock:
            self._tasks.pop(task_id, None)

    def get_stale_tasks(self, max_age_seconds: float) -> list[str]:
        """Return IDs of completed or failed tasks older than the cutoff.

        Args:
            max_age_seconds: Maximum age in seconds before a terminal task
                is considered stale.

        Returns:
            List of task IDs eligible for cleanup.
        """
        cutoff = time.time() - max_age_seconds
        with self._lock:
            return [
                tid
                for tid, state in self._tasks.items()
                if state.updated_at < cutoff
                and state.stage in (DownloadStage.COMPLETED, DownloadStage.FAILED)
            ]

    def get_all_tasks(self) -> dict[str, TaskState]:
        """Return a snapshot of all tasks.

        Returns:
            A shallow copy of the internal task dictionary.
        """
        with self._lock:
            return dict(self._tasks)
