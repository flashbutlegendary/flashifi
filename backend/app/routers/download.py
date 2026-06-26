"""
Download initiation and file retrieval endpoints.

Provides two routes:

- ``POST /download``: Accepts a ``DownloadRequest``, creates a background task
  that resolves, downloads, and converts audio, then returns a ``task_id``
  for progress tracking.
- ``GET /download/{task_id}``: Streams the completed audio file with proper
  ``Content-Disposition`` headers for browser download.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from app.config.settings import Settings
from app.core.dependencies import get_converter, get_resolver, get_settings, get_task_manager
from app.exceptions.handlers import TaskNotFoundError
from app.models.enums import DownloadStage, FORMAT_EXTENSIONS
from app.schemas.requests import DownloadRequest
from app.schemas.responses import DownloadTaskResponse
from app.services.converter import ConverterService
from app.services.resolver import ResolverService
from app.utils.sanitizers import sanitize_filename
from app.workers.task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Download"])


# ── Media type mapping for Content-Type headers ─────────────────────────
_MEDIA_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
}


@router.post(
    "/download",
    response_model=DownloadTaskResponse,
    status_code=202,
    summary="Initiate audio download",
    description=(
        "Accepts a download request with query, format, and quality parameters. "
        "Returns a task_id that can be polled via GET /progress/{task_id}."
    ),
)
async def initiate_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    resolver: ResolverService = Depends(get_resolver),
    converter: ConverterService = Depends(get_converter),
    task_manager: TaskManager = Depends(get_task_manager),
    settings: Settings = Depends(get_settings),
) -> DownloadTaskResponse:
    """Initiate a download task.

    Creates an in-memory task record and enqueues a background coroutine
    that will resolve the track, download audio, and convert to the
    requested format.

    Args:
        request: Download parameters (query, format, quality).
        background_tasks: FastAPI background task scheduler.
        resolver: Injected resolver service.
        converter: Injected converter service.
        task_manager: Injected task manager.
        settings: Injected application settings.

    Returns:
        A ``DownloadTaskResponse`` containing the ``task_id``.
    """
    task_id = task_manager.create_task()

    background_tasks.add_task(
        _process_download,
        task_id=task_id,
        request=request,
        resolver=resolver,
        converter=converter,
        task_manager=task_manager,
        settings=settings,
    )

    logger.info(
        "Download task initiated",
        extra={
            "task_id": task_id,
            "query": request.query,
            "format": request.format.value,
            "quality": request.quality.value,
        },
    )

    return DownloadTaskResponse(task_id=task_id)


async def _process_download(
    task_id: str,
    request: DownloadRequest,
    resolver: ResolverService,
    converter: ConverterService,
    task_manager: TaskManager,
    settings: Settings,
) -> None:
    """Background coroutine: resolve → download → convert → finalise.

    This function is scheduled via ``BackgroundTasks`` and runs after the
    HTTP response has been sent. It updates the task manager at each stage
    so the client can poll progress.

    Args:
        task_id: Unique task identifier for progress tracking.
        request: Original download request parameters.
        resolver: Service to resolve track metadata.
        converter: Service to download and convert audio.
        task_manager: Shared task registry for progress updates.
        settings: Application settings.
    """
    try:
        # ── Stage: RESOLVING ─────────────────────────────────────────
        task_manager.update_progress(
            task_id,
            DownloadStage.RESOLVING,
            percentage=10.0,
            message="Resolving source...",
        )
        metadata = await resolver.resolve(request.query)

        # ── Stage: PREPARING ─────────────────────────────────────────
        task_manager.update_progress(
            task_id,
            DownloadStage.PREPARING,
            percentage=20.0,
            message="Preparing workspace...",
        )
        workspace = settings.temp_dir / task_id
        workspace.mkdir(parents=True, exist_ok=True)

        # ── Stage: DOWNLOADING ───────────────────────────────────────
        def progress_callback(pct: float, speed: str, eta: str) -> None:
            """Map yt-dlp progress (0–100) into the 30–70% range."""
            mapped = 30.0 + (pct * 0.4)
            task_manager.update_progress(
                task_id,
                DownloadStage.DOWNLOADING,
                percentage=mapped,
                speed=speed,
                eta=eta,
                message="Downloading audio...",
            )

        task_manager.update_progress(
            task_id,
            DownloadStage.DOWNLOADING,
            percentage=30.0,
            message="Downloading audio...",
        )

        ext = FORMAT_EXTENSIONS.get(request.format, ".mp3")
        filename = sanitize_filename(f"{metadata.artist} - {metadata.title}") + ext

        output_path: Path = await converter.process(
            video_id=metadata.video_id,
            output_dir=workspace,
            audio_format=request.format,
            quality=request.quality,
            filename=filename,
            progress_callback=progress_callback,
        )

        # ── Stage: CLEANING ──────────────────────────────────────────
        task_manager.update_progress(
            task_id,
            DownloadStage.CLEANING,
            percentage=90.0,
            message="Finalizing...",
        )

        file_size = output_path.stat().st_size

        # ── Stage: COMPLETED ─────────────────────────────────────────
        task_manager.mark_completed(task_id, output_path, filename, file_size)

    except Exception as exc:
        logger.exception("Download task failed", extra={"task_id": task_id})
        task_manager.mark_failed(task_id, str(exc))


@router.get(
    "/download/{task_id}",
    summary="Download completed audio file",
    description="Streams the output file for a completed download task.",
    responses={
        200: {
            "description": "Audio file binary stream",
            "content": {"application/octet-stream": {}},
        },
        404: {"description": "Task not found or not yet completed"},
    },
)
async def download_file(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> FileResponse:
    """Download the completed audio file.

    Validates that the task exists, has reached the COMPLETED stage,
    and that the output file is still present on disk.

    Args:
        task_id: The unique task identifier returned by ``POST /download``.
        task_manager: Injected task manager.

    Returns:
        A ``FileResponse`` streaming the audio file with appropriate
        Content-Disposition and Content-Type headers.

    Raises:
        TaskNotFoundError: If the task does not exist, is not completed,
            or the file has been cleaned up.
    """
    task = task_manager.get_task(task_id)

    if task is None:
        raise TaskNotFoundError(f"Task '{task_id}' not found")

    if task.stage != DownloadStage.COMPLETED:
        raise TaskNotFoundError(
            f"Task '{task_id}' is not completed yet (current stage: {task.stage.value})"
        )

    if not task.file_path or not task.file_path.exists():
        raise TaskNotFoundError(
            f"File for task '{task_id}' no longer exists — it may have been cleaned up"
        )

    # Determine the appropriate media type from the file extension
    suffix = task.file_path.suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(task.file_path),
        filename=task.filename,
        media_type=media_type,
    )
