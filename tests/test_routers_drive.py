import pytest

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.drive import DriveFile

SAMPLE_FILE = DriveFile(
    id="file123", name="report.txt", mime_type="text/plain",
    size="1024", created_time="2025-01-01T00:00:00Z",
    modified_time="2025-01-02T00:00:00Z", parents=["folder789"],
    web_view_link="https://drive.google.com/file/d/file123/view",
)


@pytest.fixture
def client(mocker):
    mocker.patch("brokenclaw.routers.drive.drive_service")
    from brokenclaw.main import api
    from fastapi.testclient import TestClient
    return TestClient(api)


@pytest.fixture
def mock_svc(mocker):
    return mocker.patch("brokenclaw.routers.drive.drive_service")


class TestListFiles:
    def test_returns_files(self, client, mock_svc):
        mock_svc.list_files.return_value = [SAMPLE_FILE]
        resp = client.get("/api/drive/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result_count"] == 1
        assert data["files"][0]["id"] == "file123"

    def test_forwards_params(self, client, mock_svc):
        mock_svc.list_files.return_value = []
        client.get("/api/drive/files?max_results=5&account=work")
        mock_svc.list_files.assert_called_once_with(5, account="work")


class TestSearch:
    def test_returns_results(self, client, mock_svc):
        mock_svc.search_files.return_value = [SAMPLE_FILE]
        resp = client.get("/api/drive/search?query=name+contains+'report'")
        assert resp.status_code == 200
        assert resp.json()["result_count"] == 1

    def test_forwards_params(self, client, mock_svc):
        mock_svc.search_files.return_value = []
        client.get("/api/drive/search?query=test&max_results=3&account=school")
        mock_svc.search_files.assert_called_once_with("test", 3, account="school")


class TestGetFile:
    def test_returns_metadata(self, client, mock_svc):
        mock_svc.get_file.return_value = SAMPLE_FILE
        resp = client.get("/api/drive/files/file123")
        assert resp.status_code == 200
        assert resp.json()["name"] == "report.txt"


class TestGetFileContent:
    def test_returns_content(self, client, mock_svc):
        from brokenclaw.models.drive import FileContentResponse
        mock_svc.get_file_content.return_value = FileContentResponse(
            id="f1", name="test.txt", mime_type="text/plain", content="hello"
        )
        resp = client.get("/api/drive/files/f1/content")
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello"


class TestCreateFile:
    def test_creates_file(self, client, mock_svc):
        mock_svc.create_file.return_value = SAMPLE_FILE
        resp = client.post("/api/drive/files", json={"name": "report.txt", "content": "data"})
        assert resp.status_code == 200

    def test_forwards_account(self, client, mock_svc):
        mock_svc.create_file.return_value = SAMPLE_FILE
        client.post("/api/drive/files?account=work", json={"name": "f.txt", "content": "x"})
        mock_svc.create_file.assert_called_once_with("f.txt", "x", "text/plain", None, account="work")


class TestCreateFolder:
    def test_creates_folder(self, client, mock_svc):
        folder = DriveFile(id="fld1", name="My Folder", mime_type="application/vnd.google-apps.folder")
        mock_svc.create_folder.return_value = folder
        resp = client.post("/api/drive/folders", json={"name": "My Folder"})
        assert resp.status_code == 200


class TestExceptionMapping:
    def test_auth_error_returns_401(self, client, mock_svc):
        mock_svc.list_files.side_effect = AuthenticationError("Not authenticated")
        resp = client.get("/api/drive/files")
        assert resp.status_code == 401

    def test_rate_limit_returns_429(self, client, mock_svc):
        mock_svc.list_files.side_effect = RateLimitError("Rate limited")
        resp = client.get("/api/drive/files")
        assert resp.status_code == 429

    def test_integration_error_returns_500(self, client, mock_svc):
        mock_svc.list_files.side_effect = IntegrationError("API failed")
        resp = client.get("/api/drive/files")
        assert resp.status_code == 500
