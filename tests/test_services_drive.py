import pytest
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.drive import DriveFile, FileContentResponse
from brokenclaw.services import drive as drive_service
from conftest import DRIVE_API_FILE, DRIVE_API_LIST


class TestListFiles:
    def test_returns_list_of_drive_files(self, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = DRIVE_API_LIST
        result = drive_service.list_files(max_results=10)
        assert len(result) == 1
        assert isinstance(result[0], DriveFile)
        assert result[0].id == "file123"
        assert result[0].name == "report.txt"

    def test_empty_results(self, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {"files": []}
        result = drive_service.list_files()
        assert result == []

    def test_no_files_key(self, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {}
        result = drive_service.list_files()
        assert result == []

    def test_forwards_account(self, mock_drive_credentials, mock_drive_build):
        mock_drive_build.files().list().execute.return_value = {}
        drive_service.list_files(account="work")
        mock_drive_credentials.assert_called_with("work")


class TestSearchFiles:
    def test_returns_matching_files(self, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = DRIVE_API_LIST
        result = drive_service.search_files("name contains 'report'")
        assert len(result) == 1
        assert result[0].name == "report.txt"

    def test_empty_search(self, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {"files": []}
        result = drive_service.search_files("nonexistent")
        assert result == []


class TestGetFile:
    def test_returns_file_metadata(self, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = DRIVE_API_FILE
        result = drive_service.get_file("file123")
        assert isinstance(result, DriveFile)
        assert result.id == "file123"
        assert result.mime_type == "text/plain"
        assert result.size == "1024"

    def test_file_without_optional_fields(self, mock_drive_service):
        minimal = {"id": "f1", "name": "test.txt", "mimeType": "text/plain"}
        mock_drive_service.files().get().execute.return_value = minimal
        result = drive_service.get_file("f1")
        assert result.size is None
        assert result.parents is None


class TestGetFileContent:
    def test_reads_plain_text(self, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {"id": "f1", "name": "test.txt", "mimeType": "text/plain"}
        mock_drive_service.files().get_media().execute.return_value = b"file content here"
        result = drive_service.get_file_content("f1")
        assert isinstance(result, FileContentResponse)
        assert result.content == "file content here"

    def test_exports_google_doc(self, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {"id": "f1", "name": "My Doc", "mimeType": "application/vnd.google-apps.document"}
        mock_drive_service.files().export().execute.return_value = b"exported text"
        result = drive_service.get_file_content("f1")
        assert result.content == "exported text"
        assert result.mime_type == "application/vnd.google-apps.document"


class TestCreateFile:
    def test_creates_file(self, mock_drive_service):
        mock_drive_service.files().create().execute.return_value = DRIVE_API_FILE
        result = drive_service.create_file("report.txt", "content")
        assert isinstance(result, DriveFile)
        assert result.id == "file123"


class TestCreateFolder:
    def test_creates_folder(self, mock_drive_service):
        folder = {**DRIVE_API_FILE, "mimeType": "application/vnd.google-apps.folder"}
        mock_drive_service.files().create().execute.return_value = folder
        result = drive_service.create_folder("My Folder")
        assert isinstance(result, DriveFile)
        assert result.mime_type == "application/vnd.google-apps.folder"


class TestErrorHandling:
    def _make_http_error(self, status):
        resp = MagicMock()
        resp.status = status
        return HttpError(resp=resp, content=b"error")

    def test_401_raises_auth_error(self, mock_drive_service):
        mock_drive_service.files().list().execute.side_effect = self._make_http_error(401)
        with pytest.raises(AuthenticationError):
            drive_service.list_files()

    def test_429_raises_rate_limit(self, mock_drive_service):
        mock_drive_service.files().list().execute.side_effect = self._make_http_error(429)
        with pytest.raises(RateLimitError):
            drive_service.list_files()

    def test_500_raises_integration_error(self, mock_drive_service):
        mock_drive_service.files().list().execute.side_effect = self._make_http_error(500)
        with pytest.raises(IntegrationError):
            drive_service.list_files()

    def test_missing_credentials_raises_auth_error(self, mocker):
        mocker.patch("brokenclaw.services.drive.get_drive_credentials", side_effect=RuntimeError("Not authenticated"))
        with pytest.raises(AuthenticationError):
            drive_service.list_files()
