import pytest

from brokenclaw.config import get_settings
from brokenclaw.models.canvas import CanvasEvent, CanvasUpcoming
from brokenclaw.services import canvas as canvas_service

requires_canvas = pytest.mark.skipif(
    not get_settings().canvas_feed_url,
    reason="Canvas feed URL not configured — set CANVAS_FEED_URL in .env",
)


@requires_canvas
class TestUpcoming:
    def test_upcoming_returns_model(self):
        result = canvas_service.get_upcoming(days=30)
        assert isinstance(result, CanvasUpcoming)
        assert isinstance(result.events, list)
        assert result.count == len(result.events)

    def test_upcoming_events_have_summary(self):
        result = canvas_service.get_upcoming(days=365)
        for event in result.events:
            assert isinstance(event, CanvasEvent)
            assert event.summary  # every event should have a summary


@requires_canvas
class TestAllEvents:
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
