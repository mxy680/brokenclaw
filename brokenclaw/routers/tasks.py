from fastapi import APIRouter

from brokenclaw.models.tasks import (
    CreateTaskListRequest,
    CreateTaskRequest,
    TaskItem,
    TaskListInfo,
    UpdateTaskRequest,
)
from brokenclaw.services import tasks as tasks_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# --- Task Lists ---


@router.get("/lists")
def list_task_lists(max_results: int = 20, account: str = "default") -> list[TaskListInfo]:
    return tasks_service.list_task_lists(max_results, account=account)


@router.post("/lists")
def create_task_list(request: CreateTaskListRequest, account: str = "default") -> TaskListInfo:
    return tasks_service.create_task_list(request.title, account=account)


@router.delete("/lists/{tasklist_id}", status_code=204)
def delete_task_list(tasklist_id: str, account: str = "default"):
    tasks_service.delete_task_list(tasklist_id, account=account)


# --- Tasks ---


@router.get("/lists/{tasklist_id}/tasks")
def list_tasks(
    tasklist_id: str,
    max_results: int = 100,
    show_completed: bool = True,
    account: str = "default",
) -> list[TaskItem]:
    return tasks_service.list_tasks(tasklist_id, max_results, show_completed, account=account)


@router.get("/lists/{tasklist_id}/tasks/{task_id}")
def get_task(tasklist_id: str, task_id: str, account: str = "default") -> TaskItem:
    return tasks_service.get_task(tasklist_id, task_id, account=account)


@router.post("/lists/{tasklist_id}/tasks")
def create_task(tasklist_id: str, request: CreateTaskRequest, account: str = "default") -> TaskItem:
    return tasks_service.create_task(tasklist_id, request.title, request.notes, request.due, account=account)


@router.patch("/lists/{tasklist_id}/tasks/{task_id}")
def update_task(tasklist_id: str, task_id: str, request: UpdateTaskRequest, account: str = "default") -> TaskItem:
    return tasks_service.update_task(
        tasklist_id, task_id, request.title, request.notes, request.status, request.due, account=account,
    )


@router.delete("/lists/{tasklist_id}/tasks/{task_id}", status_code=204)
def delete_task(tasklist_id: str, task_id: str, account: str = "default"):
    tasks_service.delete_task(tasklist_id, task_id, account=account)


@router.post("/lists/{tasklist_id}/tasks/{task_id}/complete")
def complete_task(tasklist_id: str, task_id: str, account: str = "default") -> TaskItem:
    return tasks_service.complete_task(tasklist_id, task_id, account=account)
