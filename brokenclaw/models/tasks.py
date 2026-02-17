from pydantic import BaseModel


class TaskListInfo(BaseModel):
    id: str
    title: str


class TaskItem(BaseModel):
    id: str
    title: str
    notes: str | None = None
    status: str  # "needsAction" or "completed"
    due: str | None = None
    completed: str | None = None
    parent: str | None = None
    position: str | None = None


class CreateTaskListRequest(BaseModel):
    title: str


class CreateTaskRequest(BaseModel):
    title: str
    notes: str | None = None
    due: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    notes: str | None = None
    status: str | None = None
    due: str | None = None
