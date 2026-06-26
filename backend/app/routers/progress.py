"""
Task progress polling endpoint.

Exposes a ``GET /progress/{task_id}`` route that returns the current
stage, percentage, speed, ETA, and status message for an active download task.
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_task_manager
from app.exceptions.handlers import TaskNotFoundError
from app.schemas.responses import ProgressResponse
from app.workers.task_manager import TaskManager

router = APIRouter(tags=["Progress"])


@router.get(
    "/progress/{task_id}",
    response_model=ProgressResponse,
    summary="Poll download progress",
    description="Returns the current progress of a download task identified by task_id.",
    responses={
        200: {"description": "Current task progress"},
        404: {"description": "Task not found"},
    },
)
async def get_progress(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> ProgressResponse:
    """Get the current progress of a download task.

    The client should poll this endpoint at regular intervals (e.g. every
    500ms–1s) to update a progress bar until the stage reaches
    ``COMPLETED`` or ``FAILED``.

    Args:
        task_id: The unique task identifier returned by ``POST /download``.
        task_manager: Injected task manager.

    Returns:
        A ``ProgressResponse`` with the current stage, percentage, speed,
        ETA, and human-readable status message.

    Raises:
        TaskNotFoundError: If no task with the given ID exists.
    """
    task = task_manager.get_task(task_id)
    if task is None:
        raise TaskNotFoundError(f"Task '{task_id}' not found")

    return ProgressResponse(
        task_id=task.task_id,
        stage=task.stage,
        percentage=task.percentage,
        speed=task.speed,
        eta=task.eta,
        message=task.message,
    )
