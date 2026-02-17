import pytest

from brokenclaw.auth import _get_token_store


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
