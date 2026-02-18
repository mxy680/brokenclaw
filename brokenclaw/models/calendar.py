from pydantic import BaseModel


class CalendarInfo(BaseModel):
    id: str
    summary: str
    description: str | None = None
    time_zone: str | None = None
    primary: bool = False


class EventTime(BaseModel):
    date_time: str | None = None
    date: str | None = None
    time_zone: str | None = None


class EventInfo(BaseModel):
    id: str
    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: EventTime
    end: EventTime
    status: str | None = None
    html_link: str | None = None
    creator_email: str | None = None
    organizer_email: str | None = None
    attendees: list[str] = []
    recurring: bool = False


class CreateEventRequest(BaseModel):
    summary: str
    description: str | None = None
    location: str | None = None
    start_datetime: str
    end_datetime: str
    time_zone: str | None = None
    attendees: list[str] | None = None
