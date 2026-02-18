import pytest

from brokenclaw.auth import _get_token_store
from brokenclaw.services.canvas_auth import has_canvas_session


def _is_authenticated(integration: str) -> bool:
    store = _get_token_store()
    return store.has_valid_token(integration)


requires_gmail = pytest.mark.skipif(
    not _is_authenticated("gmail"),
    reason="Gmail not authenticated — run /auth/gmail/setup first",
)

requires_drive = pytest.mark.skipif(
    not _is_authenticated("drive"),
    reason="Drive not authenticated — run /auth/drive/setup first",
)

requires_sheets = pytest.mark.skipif(
    not _is_authenticated("sheets"),
    reason="Sheets not authenticated — run /auth/sheets/setup first",
)

requires_docs = pytest.mark.skipif(
    not _is_authenticated("docs"),
    reason="Docs not authenticated — run /auth/docs/setup first",
)

requires_slides = pytest.mark.skipif(
    not _is_authenticated("slides"),
    reason="Slides not authenticated — run /auth/slides/setup first",
)

requires_tasks = pytest.mark.skipif(
    not _is_authenticated("tasks"),
    reason="Tasks not authenticated — run /auth/tasks/setup first",
)

requires_forms = pytest.mark.skipif(
    not _is_authenticated("forms"),
    reason="Forms not authenticated — run /auth/forms/setup first",
)

requires_youtube = pytest.mark.skipif(
    not _is_authenticated("youtube"),
    reason="YouTube not authenticated — run /auth/youtube/setup first",
)

requires_calendar = pytest.mark.skipif(
    not _is_authenticated("calendar"),
    reason="Calendar not authenticated — run /auth/calendar/setup first",
)

requires_canvas_session = pytest.mark.skipif(
    not has_canvas_session(),
    reason="Canvas session not available — run /auth/canvas/setup first",
)

