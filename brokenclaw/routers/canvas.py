from fastapi import APIRouter

from brokenclaw.models.canvas import (
    CanvasAnnouncement,
    CanvasAssignment,
    CanvasCourse,
    CanvasGrade,
    CanvasSubmission,
    CanvasTodoItem,
    CanvasUpcoming,
    CanvasUserProfile,
)
from brokenclaw.services import canvas as canvas_service

router = APIRouter(prefix="/api/canvas", tags=["canvas"])


# --- iCal endpoints (original) ---


@router.get("/upcoming")
def upcoming(days: int = 14, account: str = "default") -> CanvasUpcoming:
    return canvas_service.get_upcoming(days, account=account)


@router.get("/events")
def all_events() -> CanvasUpcoming:
    return canvas_service.get_all_events()


# --- REST API endpoints ---


@router.get("/profile")
def profile(account: str = "default") -> CanvasUserProfile:
    return canvas_service.get_profile(account)


@router.get("/courses")
def courses(enrollment_state: str = "active", account: str = "default") -> list[CanvasCourse]:
    return canvas_service.list_courses(enrollment_state, account)


@router.get("/courses/{course_id}")
def course(course_id: int, account: str = "default") -> CanvasCourse:
    return canvas_service.get_course(course_id, account)


@router.get("/courses/{course_id}/assignments")
def assignments(course_id: int, order_by: str = "due_at", account: str = "default") -> list[CanvasAssignment]:
    return canvas_service.list_assignments(course_id, order_by, account)


@router.get("/courses/{course_id}/assignments/{assignment_id}")
def assignment(course_id: int, assignment_id: int, account: str = "default") -> CanvasAssignment:
    return canvas_service.get_assignment(course_id, assignment_id, account)


@router.get("/announcements")
def announcements(course_ids: str | None = None, account: str = "default") -> list[CanvasAnnouncement]:
    ids = [int(x) for x in course_ids.split(",")] if course_ids else None
    return canvas_service.list_announcements(ids, account)


@router.get("/courses/{course_id}/grades")
def grades(course_id: int, account: str = "default") -> CanvasGrade:
    return canvas_service.get_grades(course_id, account)


@router.get("/courses/{course_id}/assignments/{assignment_id}/submissions")
def submissions(course_id: int, assignment_id: int, account: str = "default") -> list[CanvasSubmission]:
    return canvas_service.list_submissions(course_id, assignment_id, account)


@router.get("/todo")
def todo(account: str = "default") -> list[CanvasTodoItem]:
    return canvas_service.get_todo(account)
