import pytest
from unittest.mock import MagicMock

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.drive import DriveFile, FileContentResponse

SAMPLE_FILE = DriveFile(
    id="file123", name="report.txt", mime_type="text/plain",
    size="1024", created_time="2025-01-01T00:00:00Z",
    modified_time="2025-01-02T00:00:00Z",
)


@pytest.fixture(autouse=True)
def mock_svc(mocker):
    return mocker.patch("brokenclaw.mcp_server.drive_service")


@pytest.fixture(autouse=True)
def mock_store(mocker):
    store = MagicMock()
    store.list_accounts.return_value = ["default"]
    mocker.patch("brokenclaw.mcp_server._get_token_store", return_value=store)
    return store


class TestDriveListFiles:
    def test_returns_dict(self, mock_svc):
        mock_svc.list_files.return_value = [SAMPLE_FILE]
        from brokenclaw.mcp_server import drive_list_files
        result = drive_list_files.fn(max_results=5)
        assert isinstance(result, dict)
        assert result["count"] == 1
        assert result["files"][0]["id"] == "file123"

    def test_forwards_account(self, mock_svc):
        mock_svc.list_files.return_value = []
        from brokenclaw.mcp_server import drive_list_files
        drive_list_files.fn(account="work")
        mock_svc.list_files.assert_called_once_with(20, account="work")

    def test_error_returns_dict_not_raises(self, mock_svc):
        mock_svc.list_files.side_effect = AuthenticationError("Not auth")
        from brokenclaw.mcp_server import drive_list_files
        result = drive_list_files.fn()
        assert isinstance(result, dict)
        assert result["error"] == "auth_error"


class TestDriveSearch:
    def test_returns_dict(self, mock_svc):
        mock_svc.search_files.return_value = [SAMPLE_FILE]
        from brokenclaw.mcp_server import drive_search
        result = drive_search.fn(query="name contains 'report'")
        assert result["count"] == 1

    def test_error_returns_dict(self, mock_svc):
        mock_svc.search_files.side_effect = RateLimitError("Slow down")
        from brokenclaw.mcp_server import drive_search
        result = drive_search.fn(query="test")
        assert result["error"] == "rate_limit"


class TestDriveGetFile:
    def test_returns_dict(self, mock_svc):
        mock_svc.get_file.return_value = SAMPLE_FILE
        from brokenclaw.mcp_server import drive_get_file
        result = drive_get_file.fn(file_id="file123")
        assert isinstance(result, dict)
        assert result["name"] == "report.txt"


class TestDriveReadFile:
    def test_returns_dict_with_content(self, mock_svc):
        mock_svc.get_file_content.return_value = FileContentResponse(
            id="f1", name="test.txt", mime_type="text/plain", content="hello world"
        )
        from brokenclaw.mcp_server import drive_read_file
        result = drive_read_file.fn(file_id="f1")
        assert isinstance(result, dict)
        assert result["content"] == "hello world"

    def test_error_returns_dict(self, mock_svc):
        mock_svc.get_file_content.side_effect = IntegrationError("API error")
        from brokenclaw.mcp_server import drive_read_file
        result = drive_read_file.fn(file_id="f1")
        assert result["error"] == "integration_error"


class TestDriveCreateFile:
    def test_returns_dict(self, mock_svc):
        mock_svc.create_file.return_value = SAMPLE_FILE
        from brokenclaw.mcp_server import drive_create_file
        result = drive_create_file.fn(name="test.txt", content="data")
        assert isinstance(result, dict)
        assert result["id"] == "file123"


class TestDriveCreateFolder:
    def test_returns_dict(self, mock_svc):
        folder = DriveFile(id="fld1", name="My Folder", mime_type="application/vnd.google-apps.folder")
        mock_svc.create_folder.return_value = folder
        from brokenclaw.mcp_server import drive_create_folder
        result = drive_create_folder.fn(name="My Folder")
        assert isinstance(result, dict)
        assert result["mime_type"] == "application/vnd.google-apps.folder"


class TestBrokenclawStatus:
    def test_returns_all_integrations(self, mock_svc, mock_store):
        mock_store.list_accounts.return_value = ["default"]
        from brokenclaw.mcp_server import brokenclaw_status
        result = brokenclaw_status.fn()
        assert "integrations" in result
        assert "gmail" in result["integrations"]
        assert "drive" in result["integrations"]
