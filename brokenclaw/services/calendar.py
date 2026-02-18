import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_calendar_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.calendar import CalendarInfo, EventInfo, EventTime


def _get_calendar_service(account: str = "default"):
    try:
        creds = get_calendar_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Calendar credentials: {e}. Visit /auth/calendar/setup?account={account}."
        ) from e
    return build("calendar", "v3", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Calendar API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Calendar credentials expired or revoked. Visit /auth/calendar/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Calendar API error: {e}") from e


def _parse_event_time(time_dict: dict) -> EventTime:
    return EventTime(
        date_time=time_dict.get("dateTime"),
        date=time_dict.get("date"),
        time_zone=time_dict.get("timeZone"),
    )


def _parse_event(item: dict) -> EventInfo:
    attendees = []
    for a in item.get("attendees", []):
        email = a.get("email")
        if email:
            attendees.append(email)
    return EventInfo(
        id=item["id"],
        summary=item.get("summary"),
        description=item.get("description"),
        location=item.get("location"),
        start=_parse_event_time(item.get("start", {})),
        end=_parse_event_time(item.get("end", {})),
        status=item.get("status"),
        html_link=item.get("htmlLink"),
        creator_email=item.get("creator", {}).get("email"),
        organizer_email=item.get("organizer", {}).get("email"),
        attendees=attendees,
        recurring="recurringEventId" in item or "recurrence" in item,
    )


def list_calendars(max_results: int = 50, account: str = "default") -> list[CalendarInfo]:
    """List all calendars the user has access to."""
    service = _get_calendar_service(account)
    try:
        result = service.calendarList().list(
            maxResults=min(max_results, 250),
        ).execute(num_retries=3)
        calendars = []
        for item in result.get("items", []):
            calendars.append(CalendarInfo(
                id=item["id"],
                summary=item.get("summary", ""),
                description=item.get("description"),
                time_zone=item.get("timeZone"),
                primary=item.get("primary", False),
            ))
        return calendars
    except HttpError as e:
        _handle_api_error(e)


def list_events(
    calendar_id: str = "primary",
    max_results: int = 25,
    time_min: str | None = None,
    time_max: str | None = None,
    query: str | None = None,
    account: str = "default",
) -> list[EventInfo]:
    """List upcoming events. Defaults to events from now onward."""
    service = _get_calendar_service(account)
    try:
        params = {
            "calendarId": calendar_id,
            "maxResults": min(max_results, 250),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min
        else:
            params["timeMin"] = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query
        result = service.events().list(**params).execute(num_retries=3)
        return [_parse_event(item) for item in result.get("items", [])]
    except HttpError as e:
        _handle_api_error(e)


def get_event(calendar_id: str, event_id: str, account: str = "default") -> EventInfo:
    """Get a specific event by ID."""
    service = _get_calendar_service(account)
    try:
        item = service.events().get(calendarId=calendar_id, eventId=event_id).execute(num_retries=3)
        return _parse_event(item)
    except HttpError as e:
        _handle_api_error(e)


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
    """Create a new calendar event."""
    service = _get_calendar_service(account)
    try:
        body = {
            "summary": summary,
            "start": {"dateTime": start_datetime},
            "end": {"dateTime": end_datetime},
        }
        if time_zone:
            body["start"]["timeZone"] = time_zone
            body["end"]["timeZone"] = time_zone
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]
        item = service.events().insert(calendarId=calendar_id, body=body).execute(num_retries=3)
        return _parse_event(item)
    except HttpError as e:
        _handle_api_error(e)


def update_event(
    calendar_id: str,
    event_id: str,
    summary: str | None = None,
    description: str | None = None,
    location: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    time_zone: str | None = None,
    account: str = "default",
) -> EventInfo:
    """Update an existing event. Only provided fields are changed."""
    service = _get_calendar_service(account)
    try:
        existing = service.events().get(calendarId=calendar_id, eventId=event_id).execute(num_retries=3)
        if summary is not None:
            existing["summary"] = summary
        if description is not None:
            existing["description"] = description
        if location is not None:
            existing["location"] = location
        if start_datetime is not None:
            existing["start"] = {"dateTime": start_datetime}
            if time_zone:
                existing["start"]["timeZone"] = time_zone
        if end_datetime is not None:
            existing["end"] = {"dateTime": end_datetime}
            if time_zone:
                existing["end"]["timeZone"] = time_zone
        item = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=existing,
        ).execute(num_retries=3)
        return _parse_event(item)
    except HttpError as e:
        _handle_api_error(e)


def delete_event(calendar_id: str, event_id: str, account: str = "default") -> None:
    """Delete an event."""
    service = _get_calendar_service(account)
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute(num_retries=3)
    except HttpError as e:
        _handle_api_error(e)


def quick_add_event(
    text: str,
    calendar_id: str = "primary",
    account: str = "default",
) -> EventInfo:
    """Create an event from a natural language string (e.g. 'Meeting with Bob tomorrow at 3pm')."""
    service = _get_calendar_service(account)
    try:
        item = service.events().quickAdd(calendarId=calendar_id, text=text).execute(num_retries=3)
        return _parse_event(item)
    except HttpError as e:
        _handle_api_error(e)
