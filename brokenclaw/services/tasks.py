from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_tasks_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.tasks import TaskItem, TaskListInfo


def _get_tasks_service(account: str = "default"):
    try:
        creds = get_tasks_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Tasks credentials: {e}. Visit /auth/tasks/setup?account={account}."
        ) from e
    return build("tasks", "v1", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Tasks API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Tasks credentials expired or revoked. Visit /auth/tasks/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Tasks API error: {e}") from e


def _parse_task(task: dict) -> TaskItem:
    return TaskItem(
        id=task["id"],
        title=task.get("title", ""),
        notes=task.get("notes"),
        status=task.get("status", "needsAction"),
        due=task.get("due"),
        completed=task.get("completed"),
        parent=task.get("parent"),
        position=task.get("position"),
    )


# --- Task Lists ---


def list_task_lists(max_results: int = 20, account: str = "default") -> list[TaskListInfo]:
    """List all task lists for the authenticated user."""
    service = _get_tasks_service(account)
    try:
        result = service.tasklists().list(maxResults=max_results).execute(num_retries=3)
        return [
            TaskListInfo(id=tl["id"], title=tl.get("title", ""))
            for tl in result.get("items", [])
        ]
    except HttpError as e:
        _handle_api_error(e)


def create_task_list(title: str, account: str = "default") -> TaskListInfo:
    """Create a new task list."""
    service = _get_tasks_service(account)
    try:
        tl = service.tasklists().insert(body={"title": title}).execute(num_retries=3)
        return TaskListInfo(id=tl["id"], title=tl.get("title", ""))
    except HttpError as e:
        _handle_api_error(e)


def delete_task_list(tasklist_id: str, account: str = "default") -> None:
    """Delete a task list."""
    service = _get_tasks_service(account)
    try:
        service.tasklists().delete(tasklist=tasklist_id).execute(num_retries=3)
    except HttpError as e:
        _handle_api_error(e)


# --- Tasks ---


def list_tasks(
    tasklist_id: str = "@default",
    max_results: int = 100,
    show_completed: bool = True,
    account: str = "default",
) -> list[TaskItem]:
    """List tasks in a task list. Use '@default' for the user's default list."""
    service = _get_tasks_service(account)
    try:
        result = (
            service.tasks()
            .list(
                tasklist=tasklist_id,
                maxResults=max_results,
                showCompleted=show_completed,
            )
            .execute(num_retries=3)
        )
        return [_parse_task(t) for t in result.get("items", [])]
    except HttpError as e:
        _handle_api_error(e)


def get_task(tasklist_id: str, task_id: str, account: str = "default") -> TaskItem:
    """Get a single task by ID."""
    service = _get_tasks_service(account)
    try:
        task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute(num_retries=3)
        return _parse_task(task)
    except HttpError as e:
        _handle_api_error(e)


def create_task(
    tasklist_id: str = "@default",
    title: str = "",
    notes: str | None = None,
    due: str | None = None,
    account: str = "default",
) -> TaskItem:
    """Create a new task in a task list."""
    service = _get_tasks_service(account)
    body: dict = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    try:
        task = service.tasks().insert(tasklist=tasklist_id, body=body).execute(num_retries=3)
        return _parse_task(task)
    except HttpError as e:
        _handle_api_error(e)


def update_task(
    tasklist_id: str,
    task_id: str,
    title: str | None = None,
    notes: str | None = None,
    status: str | None = None,
    due: str | None = None,
    account: str = "default",
) -> TaskItem:
    """Update an existing task. Only provided fields are changed."""
    service = _get_tasks_service(account)
    try:
        # Fetch current task first to merge fields
        current = service.tasks().get(tasklist=tasklist_id, task=task_id).execute(num_retries=3)
        if title is not None:
            current["title"] = title
        if notes is not None:
            current["notes"] = notes
        if status is not None:
            current["status"] = status
        if due is not None:
            current["due"] = due
        task = service.tasks().update(tasklist=tasklist_id, task=task_id, body=current).execute(num_retries=3)
        return _parse_task(task)
    except HttpError as e:
        _handle_api_error(e)


def delete_task(tasklist_id: str, task_id: str, account: str = "default") -> None:
    """Delete a task."""
    service = _get_tasks_service(account)
    try:
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute(num_retries=3)
    except HttpError as e:
        _handle_api_error(e)


def complete_task(tasklist_id: str, task_id: str, account: str = "default") -> TaskItem:
    """Mark a task as completed."""
    return update_task(tasklist_id, task_id, status="completed", account=account)
