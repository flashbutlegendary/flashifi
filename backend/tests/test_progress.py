"""
Tests for the /progress/<task_id> endpoint.
Validates 404 on unknown tasks and correct schema for existing tasks.
"""


def test_progress_unknown_task(client):
    """Requesting progress for a non-existent task must return 404."""
    response = client.get("/progress/nonexistent-task-id")
    assert response.status_code == 404


def test_progress_existing_task(client):
    """Progress for a freshly-created task returns correct initial state."""
    from app.core.dependencies import get_task_manager
    from app.workers.task_manager import TaskManager

    tm = TaskManager()
    task_id = tm.create_task()

    client.app.dependency_overrides[get_task_manager] = lambda: tm

    response = client.get(f"/progress/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["stage"] == "preparing"
    assert data["percentage"] == 0.0

    client.app.dependency_overrides.clear()
