from pydantic import BaseModel


class CanvasEvent(BaseModel):
    summary: str
    description: str | None = None
    start: str | None = None
    end: str | None = None
    url: str | None = None
    location: str | None = None
    course: str | None = None


class CanvasUpcoming(BaseModel):
    events: list[CanvasEvent]
    count: int
