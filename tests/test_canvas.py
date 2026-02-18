import pytest

from brokenclaw.config import get_settings
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
from brokenclaw.services import canvas as canvas_service
from tests.conftest import requires_canvas_session

requires_canvas_feed = pytest.mark.skipif(
    not get_settings().canvas_feed_url,
    reason="Canvas feed URL not configured — set CANVAS_FEED_URL in .env",
)


# =============================================================================
# iCal feed tests (original)
# =============================================================================


@requires_canvas_feed
class TestICalUpcoming:
    def test_upcoming_returns_model(self):
        result = canvas_service.get_upcoming(days=30)
        assert isinstance(result, CanvasUpcoming)
        assert isinstance(result.events, list)
        assert result.count == len(result.events)

    def test_upcoming_events_have_summary(self):
        result = canvas_service.get_upcoming(days=365)
        for event in result.events:
            assert isinstance(event, CanvasEvent)
            assert event.summary


@requires_canvas_feed
class TestICalAllEvents:
    def test_all_events_returns_model(self):
        result = canvas_service.get_all_events()
        assert isinstance(result, CanvasUpcoming)
        assert isinstance(result.events, list)
        assert result.count == len(result.events)

    def test_all_events_not_empty(self):
        result = canvas_service.get_all_events()
        assert result.count > 0, "Expected at least one event in the Canvas calendar"

    def test_events_have_start_time(self):
        result = canvas_service.get_all_events()
        for event in result.events:
            assert event.start is not None, f"Event '{event.summary}' missing start time"


# =============================================================================
# REST API tests (require Canvas session)
# =============================================================================


@requires_canvas_session
class TestProfile:
    def test_profile_returns_model(self):
        result = canvas_service.get_profile()
        assert isinstance(result, CanvasUserProfile)
        assert result.id > 0
        assert result.name


@requires_canvas_session
class TestCourses:
    def test_list_active_courses(self):
        courses = canvas_service.list_courses("active")
        assert isinstance(courses, list)
        for course in courses:
            assert isinstance(course, CanvasCourse)
            assert course.id > 0
            assert course.name

    def test_get_specific_course(self):
        courses = canvas_service.list_courses("active")
        if courses:
            course = canvas_service.get_course(courses[0].id)
            assert isinstance(course, CanvasCourse)
            assert course.id == courses[0].id


@requires_canvas_session
class TestAssignments:
    def test_list_assignments(self):
        courses = canvas_service.list_courses("active")
        if courses:
            assignments = canvas_service.list_assignments(courses[0].id)
            assert isinstance(assignments, list)
            for a in assignments:
                assert isinstance(a, CanvasAssignment)
                assert a.id > 0
                assert a.name


@requires_canvas_session
class TestGrades:
    def test_get_grades(self):
        courses = canvas_service.list_courses("active")
        if courses:
            grades = canvas_service.get_grades(courses[0].id)
            assert isinstance(grades, CanvasGrade)
            assert grades.course_id == courses[0].id


@requires_canvas_session
class TestTodo:
    def test_get_todo_items(self):
        items = canvas_service.get_todo()
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, CanvasTodoItem)


@requires_canvas_session
class TestAnnouncements:
    def test_list_announcements(self):
        courses = canvas_service.list_courses("active")
        if courses:
            announcements = canvas_service.list_announcements([courses[0].id])
            assert isinstance(announcements, list)
            for a in announcements:
                assert isinstance(a, CanvasAnnouncement)
