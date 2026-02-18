import datetime

from icalendar import Calendar

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError
from brokenclaw.http_client import get_session
from brokenclaw.models.canvas import CanvasEvent, CanvasUpcoming


def _get_feed_url() -> str:
    url = get_settings().canvas_feed_url
    if not url:
        raise AuthenticationError(
            "Canvas calendar feed URL not configured. "
            "Go to Canvas > Calendar > Calendar Feed, copy the URL, "
            "and set CANVAS_FEED_URL in .env"
        )
    return url


def _fetch_calendar() -> Calendar:
    """Fetch and parse the iCal feed."""
    resp = get_session().get(_get_feed_url())
    if resp.status_code >= 400:
        raise IntegrationError(f"Failed to fetch Canvas calendar feed (HTTP {resp.status_code})")
    return Calendar.from_ical(resp.content)


def _dt_to_str(dt) -> str | None:
    """Convert icalendar date/datetime to ISO string."""
    if dt is None:
        return None
    val = dt.dt if hasattr(dt, "dt") else dt
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    return str(val)


def _parse_event(component) -> CanvasEvent:
    """Parse a VEVENT component into a CanvasEvent."""
    summary = str(component.get("summary", ""))
    description = str(component.get("description", "")) if component.get("description") else None
    url = str(component.get("url", "")) if component.get("url") else None
    location = str(component.get("location", "")) if component.get("location") else None

    # Try to extract course name from description or summary
    # Canvas typically puts course info in the description like "[COURSE NAME]"
    course = None
    if description:
        # Canvas format often has course name in brackets
        import re
        match = re.search(r"\[(.+?)\]", description)
        if match:
            course = match.group(1)

    return CanvasEvent(
        summary=summary,
        description=description,
        start=_dt_to_str(component.get("dtstart")),
        end=_dt_to_str(component.get("dtend")),
        url=url,
        location=location,
        course=course,
    )


def get_upcoming(days: int = 14) -> CanvasUpcoming:
    """Get upcoming assignments and events within the next N days."""
    cal = _fetch_calendar()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    cutoff = now + datetime.timedelta(days=days)

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        if dtstart is None:
            continue
        val = dtstart.dt if hasattr(dtstart, "dt") else dtstart
        # Normalize to datetime for comparison
        if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
            val = datetime.datetime.combine(val, datetime.time.min, tzinfo=datetime.timezone.utc)
        if not val.tzinfo:
            val = val.replace(tzinfo=datetime.timezone.utc)
        if now <= val <= cutoff:
            events.append((val, _parse_event(component)))

    # Sort by start time
    events.sort(key=lambda x: x[0])
    sorted_events = [e for _, e in events]

    return CanvasUpcoming(events=sorted_events, count=len(sorted_events))


def get_all_events() -> CanvasUpcoming:
    """Get all events from the calendar feed (past and future)."""
    cal = _fetch_calendar()

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        val = None
        if dtstart:
            val = dtstart.dt if hasattr(dtstart, "dt") else dtstart
            if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
                val = datetime.datetime.combine(val, datetime.time.min, tzinfo=datetime.timezone.utc)
            if val and not val.tzinfo:
                val = val.replace(tzinfo=datetime.timezone.utc)
        events.append((val or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), _parse_event(component)))

    events.sort(key=lambda x: x[0])
    sorted_events = [e for _, e in events]

    return CanvasUpcoming(events=sorted_events, count=len(sorted_events))
