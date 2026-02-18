from fastapi import APIRouter

from brokenclaw.models.calendar import CalendarInfo, EventInfo
from brokenclaw.services import calendar as calendar_service

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/calendars")
def list_calendars(max_results: int = 50, account: str = "default") -> list[CalendarInfo]:
    return calendar_service.list_calendars(max_results, account=account)


@router.get("/events")
def list_events(
    calendar_id: str = "primary",
    max_results: int = 25,
    time_min: str | None = None,
    time_max: str | None = None,
    query: str | None = None,
    account: str = "default",
) -> list[EventInfo]:
    return calendar_service.list_events(calendar_id, max_results, time_min, time_max, query, account=account)


@router.get("/events/{event_id}")
def get_event(event_id: str, calendar_id: str = "primary", account: str = "default") -> EventInfo:
    return calendar_service.get_event(calendar_id, event_id, account=account)


@router.post("/events")
def create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
    time_zone: str | None = None,
    attendees: list[str] | None = None,
    account: str = "default",
) -> EventInfo:
    return calendar_service.create_event(
        summary, start_datetime, end_datetime, calendar_id,
        description, location, time_zone, attendees, account=account,
    )


@router.put("/events/{event_id}")
def update_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    description: str | None = None,
    location: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    time_zone: str | None = None,
    account: str = "default",
) -> EventInfo:
    return calendar_service.update_event(
        calendar_id, event_id, summary, description, location,
        start_datetime, end_datetime, time_zone, account=account,
    )


@router.delete("/events/{event_id}")
def delete_event(event_id: str, calendar_id: str = "primary", account: str = "default"):
    calendar_service.delete_event(calendar_id, event_id, account=account)
    return {"status": "deleted", "event_id": event_id}


@router.post("/events/quick-add")
def quick_add_event(text: str, calendar_id: str = "primary", account: str = "default") -> EventInfo:
    return calendar_service.quick_add_event(text, calendar_id, account=account)
