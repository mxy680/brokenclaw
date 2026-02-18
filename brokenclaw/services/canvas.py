import datetime
import re

from icalendar import Calendar

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError
from brokenclaw.http_client import get_session
from brokenclaw.models.canvas import (
    CanvasAnnouncement,
    CanvasAssignment,
    CanvasCourse,
    CanvasEvent,
    CanvasGrade,
    CanvasSubmission,
    CanvasTodoItem,
    CanvasUpcoming,
    CanvasUserProfile,
)
from brokenclaw.services.canvas_auth import has_canvas_session
from brokenclaw.services.canvas_client import canvas_get, canvas_get_paginated


# =============================================================================
# iCal feed functions (original, kept as fallback)
# =============================================================================


def _ical_get_feed_url() -> str:
    url = get_settings().canvas_feed_url
    if not url:
        raise AuthenticationError(
            "Canvas calendar feed URL not configured. "
            "Go to Canvas > Calendar > Calendar Feed, copy the URL, "
            "and set CANVAS_FEED_URL in .env"
        )
    return url


def _ical_fetch_calendar() -> Calendar:
    resp = get_session().get(_ical_get_feed_url())
    if resp.status_code >= 400:
        raise IntegrationError(f"Failed to fetch Canvas calendar feed (HTTP {resp.status_code})")
    return Calendar.from_ical(resp.content)


def _dt_to_str(dt) -> str | None:
    if dt is None:
        return None
    val = dt.dt if hasattr(dt, "dt") else dt
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return str(val)


def _parse_event(component) -> CanvasEvent:
    summary = str(component.get("summary", ""))
    description = str(component.get("description", "")) if component.get("description") else None
    url = str(component.get("url", "")) if component.get("url") else None
    location = str(component.get("location", "")) if component.get("location") else None

    course = None
    if description:
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


def _ical_get_upcoming(days: int = 14) -> CanvasUpcoming:
    cal = _ical_fetch_calendar()
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
        if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
            val = datetime.datetime.combine(val, datetime.time.min, tzinfo=datetime.timezone.utc)
        if not val.tzinfo:
            val = val.replace(tzinfo=datetime.timezone.utc)
        if now <= val <= cutoff:
            events.append((val, _parse_event(component)))

    events.sort(key=lambda x: x[0])
    return CanvasUpcoming(events=[e for _, e in events], count=len(events))


def _ical_get_all_events() -> CanvasUpcoming:
    cal = _ical_fetch_calendar()

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
    return CanvasUpcoming(events=[e for _, e in events], count=len(events))


# =============================================================================
# Public API — prefers REST API when session exists, falls back to iCal
# =============================================================================


def get_upcoming(days: int = 14, account: str = "default") -> CanvasUpcoming:
    """Get upcoming assignments/events. Uses REST API if session available, else iCal."""
    if has_canvas_session(account):
        try:
            items = get_todo(account)
            events = []
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            cutoff = now + datetime.timedelta(days=days)
            for item in items:
                if item.due_at:
                    try:
                        due = datetime.datetime.fromisoformat(item.due_at.replace("Z", "+00:00"))
                        if now <= due <= cutoff:
                            events.append(CanvasEvent(
                                summary=item.assignment_name or item.type or "Unknown",
                                start=item.due_at,
                                course=item.course_name,
                                url=item.url,
                            ))
                    except ValueError:
                        pass
            return CanvasUpcoming(events=events, count=len(events))
        except Exception:
            pass  # Fall through to iCal
    return _ical_get_upcoming(days)


def get_all_events() -> CanvasUpcoming:
    """Get all events from iCal feed."""
    return _ical_get_all_events()


# =============================================================================
# REST API service functions
# =============================================================================


def get_profile(account: str = "default") -> CanvasUserProfile:
    """Get the current user's Canvas profile."""
    data = canvas_get("users/self/profile", account)
    return CanvasUserProfile(
        id=data["id"],
        name=data["name"],
        short_name=data.get("short_name"),
        login_id=data.get("login_id"),
        email=data.get("primary_email") or data.get("email"),
        avatar_url=data.get("avatar_url"),
    )


def list_courses(enrollment_state: str = "active", account: str = "default") -> list[CanvasCourse]:
    """List courses for the current user."""
    params = {"enrollment_state": enrollment_state}
    data = canvas_get_paginated("courses", account, params)
    base_url = get_settings().canvas_base_url.rstrip("/")
    courses = []
    for c in data:
        courses.append(CanvasCourse(
            id=c["id"],
            name=c.get("name", ""),
            course_code=c.get("course_code"),
            enrollment_term_id=c.get("enrollment_term_id"),
            start_at=c.get("start_at"),
            end_at=c.get("end_at"),
            workflow_state=c.get("workflow_state"),
            url=f"{base_url}/courses/{c['id']}",
        ))
    return courses


def get_course(course_id: int, account: str = "default") -> CanvasCourse:
    """Get a specific course by ID."""
    c = canvas_get(f"courses/{course_id}", account)
    base_url = get_settings().canvas_base_url.rstrip("/")
    return CanvasCourse(
        id=c["id"],
        name=c.get("name", ""),
        course_code=c.get("course_code"),
        enrollment_term_id=c.get("enrollment_term_id"),
        start_at=c.get("start_at"),
        end_at=c.get("end_at"),
        workflow_state=c.get("workflow_state"),
        url=f"{base_url}/courses/{c['id']}",
    )


def list_assignments(
    course_id: int,
    order_by: str = "due_at",
    account: str = "default",
) -> list[CanvasAssignment]:
    """List assignments for a course."""
    params = {"order_by": order_by}
    data = canvas_get_paginated(f"courses/{course_id}/assignments", account, params)
    base_url = get_settings().canvas_base_url.rstrip("/")
    assignments = []
    for a in data:
        assignments.append(CanvasAssignment(
            id=a["id"],
            name=a.get("name", ""),
            description=a.get("description"),
            due_at=a.get("due_at"),
            points_possible=a.get("points_possible"),
            submission_types=a.get("submission_types"),
            grading_type=a.get("grading_type"),
            url=a.get("html_url") or f"{base_url}/courses/{course_id}/assignments/{a['id']}",
        ))
    return assignments


def get_assignment(
    course_id: int,
    assignment_id: int,
    account: str = "default",
) -> CanvasAssignment:
    """Get a specific assignment."""
    a = canvas_get(f"courses/{course_id}/assignments/{assignment_id}", account)
    base_url = get_settings().canvas_base_url.rstrip("/")
    return CanvasAssignment(
        id=a["id"],
        name=a.get("name", ""),
        description=a.get("description"),
        due_at=a.get("due_at"),
        points_possible=a.get("points_possible"),
        submission_types=a.get("submission_types"),
        grading_type=a.get("grading_type"),
        url=a.get("html_url") or f"{base_url}/courses/{course_id}/assignments/{a['id']}",
    )


def list_announcements(
    course_ids: list[int] | None = None,
    account: str = "default",
) -> list[CanvasAnnouncement]:
    """List announcements for the given courses (or all active courses)."""
    if not course_ids:
        courses = list_courses("active", account)
        course_ids = [c.id for c in courses]

    if not course_ids:
        return []

    # Canvas API requires context_codes like "course_12345"
    params = {"context_codes[]": [f"course_{cid}" for cid in course_ids]}
    data = canvas_get_paginated("announcements", account, params)
    announcements = []
    for a in data:
        author_name = None
        if a.get("author") and isinstance(a["author"], dict):
            author_name = a["author"].get("display_name")
        announcements.append(CanvasAnnouncement(
            id=a["id"],
            title=a.get("title", ""),
            message=a.get("message"),
            posted_at=a.get("posted_at"),
            author_name=author_name,
            course_id=a.get("context_code", "").replace("course_", "") if a.get("context_code") else None,
            url=a.get("html_url"),
        ))
        # Fix course_id to int
        if announcements[-1].course_id is not None:
            try:
                announcements[-1].course_id = int(announcements[-1].course_id)
            except (ValueError, TypeError):
                announcements[-1].course_id = None
    return announcements


def get_grades(course_id: int, account: str = "default") -> CanvasGrade:
    """Get the user's grades for a course."""
    # Get enrollments for this course to find the user's grades
    data = canvas_get(f"courses/{course_id}", account, params={"include[]": "total_scores"})
    course_name = data.get("name", "")

    # Get the user's enrollment to find grades
    enrollments = canvas_get_paginated(
        f"courses/{course_id}/enrollments",
        account,
        params={"user_id": "self", "type[]": "StudentEnrollment"},
    )

    if enrollments:
        e = enrollments[0]
        grades = e.get("grades", {})
        return CanvasGrade(
            course_id=course_id,
            course_name=course_name,
            current_score=grades.get("current_score"),
            final_score=grades.get("final_score"),
            current_grade=grades.get("current_grade"),
            final_grade=grades.get("final_grade"),
        )

    return CanvasGrade(course_id=course_id, course_name=course_name)


def list_submissions(
    course_id: int,
    assignment_id: int,
    account: str = "default",
) -> list[CanvasSubmission]:
    """List the user's submissions for an assignment."""
    data = canvas_get_paginated(
        f"courses/{course_id}/assignments/{assignment_id}/submissions",
        account,
        params={"include[]": "submission_history"},
    )
    submissions = []
    for s in data:
        submissions.append(CanvasSubmission(
            id=s["id"],
            assignment_id=s.get("assignment_id", assignment_id),
            submitted_at=s.get("submitted_at"),
            score=s.get("score"),
            grade=s.get("grade"),
            workflow_state=s.get("workflow_state"),
            late=s.get("late"),
            missing=s.get("missing"),
        ))
    return submissions


def get_todo(account: str = "default") -> list[CanvasTodoItem]:
    """Get the user's Canvas TODO items."""
    data = canvas_get("users/self/todo", account)
    items = []
    for t in data:
        assignment = t.get("assignment") or {}
        course_name = None
        course_id = None
        if t.get("context_type") == "Course":
            course_id = t.get("course_id")
            course_name = t.get("context_name")

        items.append(CanvasTodoItem(
            type=t.get("type"),
            assignment_name=assignment.get("name") or t.get("title"),
            course_id=course_id,
            course_name=course_name,
            due_at=assignment.get("due_at"),
            points_possible=assignment.get("points_possible"),
            url=assignment.get("html_url") or t.get("html_url"),
        ))
    return items
