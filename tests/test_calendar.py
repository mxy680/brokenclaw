import datetime

from brokenclaw.models.calendar import CalendarInfo, EventInfo
from brokenclaw.services import calendar as calendar_service
from tests.conftest import requires_calendar


@requires_calendar
class TestListCalendars:
    def test_returns_list(self):
        calendars = calendar_service.list_calendars(max_results=10)
        assert isinstance(calendars, list)
        assert len(calendars) > 0
        primary = [c for c in calendars if c.primary]
        assert len(primary) == 1
        assert isinstance(primary[0], CalendarInfo)
        assert primary[0].id


@requires_calendar
class TestListEvents:
    def test_list_upcoming(self):
        events = calendar_service.list_events(max_results=5)
        assert isinstance(events, list)
        for event in events:
            assert isinstance(event, EventInfo)
            assert event.id

    def test_list_with_query(self):
        # Just verify the query parameter doesn't error
        events = calendar_service.list_events(query="brokenclaw_nonexistent_xyzzy", max_results=5)
        assert isinstance(events, list)


@requires_calendar
class TestCreateUpdateDeleteEvent:
    def test_full_lifecycle(self):
        # Create an event 1 hour from now
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        start = (now + datetime.timedelta(hours=1)).isoformat()
        end = (now + datetime.timedelta(hours=2)).isoformat()

        created = calendar_service.create_event(
            summary="brokenclaw_test_event",
            start_datetime=start,
            end_datetime=end,
            description="Integration test event",
            location="Test Location",
        )
        try:
            assert isinstance(created, EventInfo)
            assert created.id
            assert created.summary == "brokenclaw_test_event"
            assert created.description == "Integration test event"
            assert created.location == "Test Location"

            # Get the event
            fetched = calendar_service.get_event("primary", created.id)
            assert fetched.id == created.id
            assert fetched.summary == "brokenclaw_test_event"

            # Update the event
            updated = calendar_service.update_event(
                "primary", created.id,
                summary="brokenclaw_test_event_updated",
            )
            assert updated.summary == "brokenclaw_test_event_updated"
        finally:
            calendar_service.delete_event("primary", created.id)

        # After deletion, Calendar API returns event with status "cancelled"
        deleted = calendar_service.get_event("primary", created.id)
        assert deleted.status == "cancelled"


@requires_calendar
class TestQuickAddEvent:
    def test_quick_add(self):
        event = calendar_service.quick_add_event("brokenclaw test meeting tomorrow at 11am")
        try:
            assert isinstance(event, EventInfo)
            assert event.id
        finally:
            calendar_service.delete_event("primary", event.id)
