import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


# --- Canned API responses ---

GMAIL_API_MESSAGE = {
    "id": "msg123",
    "threadId": "thread456",
    "snippet": "Hey, just checking in...",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Hello"},
            {"name": "From", "value": "alice@example.com"},
            {"name": "To", "value": "bob@example.com"},
            {"name": "Date", "value": "Mon, 1 Jan 2025 12:00:00 -0500"},
            {"name": "Message-ID", "value": "<abc@example.com>"},
        ],
        "mimeType": "text/plain",
        "body": {
            "data": "SGVsbG8gd29ybGQ=",  # base64("Hello world")
        },
    },
}

GMAIL_API_LIST = {
    "messages": [{"id": "msg123", "threadId": "thread456"}],
}

GMAIL_API_SEND = {"id": "sent789", "threadId": "thread456"}

DRIVE_API_FILE = {
    "id": "file123",
    "name": "report.txt",
    "mimeType": "text/plain",
    "size": "1024",
    "createdTime": "2025-01-01T00:00:00Z",
    "modifiedTime": "2025-01-02T00:00:00Z",
    "parents": ["folder789"],
    "webViewLink": "https://drive.google.com/file/d/file123/view",
}

DRIVE_API_LIST = {
    "files": [DRIVE_API_FILE],
}


@pytest.fixture
def mock_gmail_credentials(mocker):
    return mocker.patch("brokenclaw.services.gmail.get_gmail_credentials", return_value=MagicMock())


@pytest.fixture
def mock_gmail_build(mocker):
    mock_svc = MagicMock()
    mocker.patch("brokenclaw.services.gmail.build", return_value=mock_svc)
    return mock_svc


@pytest.fixture
def mock_gmail_service(mock_gmail_credentials, mock_gmail_build):
    """Fully mocked Gmail API service."""
    return mock_gmail_build


@pytest.fixture
def mock_drive_credentials(mocker):
    return mocker.patch("brokenclaw.services.drive.get_drive_credentials", return_value=MagicMock())


@pytest.fixture
def mock_drive_build(mocker):
    mock_svc = MagicMock()
    mocker.patch("brokenclaw.services.drive.build", return_value=mock_svc)
    return mock_svc


@pytest.fixture
def mock_drive_service(mock_drive_credentials, mock_drive_build):
    """Fully mocked Drive API service."""
    return mock_drive_build


@pytest.fixture
def api_client():
    """FastAPI TestClient for router tests."""
    from brokenclaw.main import api
    return TestClient(api)
