import pytest

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.sheets import ReadRangeResponse, SpreadsheetInfo, WriteRangeResponse

SAMPLE_SPREADSHEET = SpreadsheetInfo(
    id="abc123", title="My Sheet", sheets=["Sheet1", "Sheet2"],
    url="https://docs.google.com/spreadsheets/d/abc123/edit",
)

SAMPLE_READ = ReadRangeResponse(
    spreadsheet_id="abc123", range="Sheet1!A1:B2",
    values=[["Name", "Age"], ["Alice", "30"]],
)

SAMPLE_WRITE = WriteRangeResponse(
    spreadsheet_id="abc123", updated_range="Sheet1!A1:B2",
    updated_rows=2, updated_columns=2, updated_cells=4,
)


@pytest.fixture
def client(mocker):
    mocker.patch("brokenclaw.routers.sheets.sheets_service")
    from brokenclaw.main import api
    from fastapi.testclient import TestClient
    return TestClient(api)


@pytest.fixture
def mock_svc(mocker):
    return mocker.patch("brokenclaw.routers.sheets.sheets_service")


class TestGetSpreadsheet:
    def test_returns_info(self, client, mock_svc):
        mock_svc.get_spreadsheet.return_value = SAMPLE_SPREADSHEET
        resp = client.get("/api/sheets/spreadsheets/abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "abc123"
        assert data["sheets"] == ["Sheet1", "Sheet2"]

    def test_forwards_account(self, client, mock_svc):
        mock_svc.get_spreadsheet.return_value = SAMPLE_SPREADSHEET
        client.get("/api/sheets/spreadsheets/abc123?account=school")
        mock_svc.get_spreadsheet.assert_called_once_with("abc123", account="school")


class TestReadRange:
    def test_returns_values(self, client, mock_svc):
        mock_svc.read_range.return_value = SAMPLE_READ
        resp = client.get("/api/sheets/spreadsheets/abc123/values?range=Sheet1!A1:B2")
        assert resp.status_code == 200
        assert resp.json()["values"] == [["Name", "Age"], ["Alice", "30"]]


class TestWriteRange:
    def test_writes_values(self, client, mock_svc):
        mock_svc.write_range.return_value = SAMPLE_WRITE
        resp = client.post("/api/sheets/spreadsheets/abc123/values", json={"range": "Sheet1!A1:B2", "values": [["X", "Y"]]})
        assert resp.status_code == 200
        assert resp.json()["updated_cells"] == 4


class TestAppendRows:
    def test_appends(self, client, mock_svc):
        mock_svc.append_rows.return_value = SAMPLE_WRITE
        resp = client.post("/api/sheets/spreadsheets/abc123/append", json={"range": "Sheet1!A:B", "values": [["Bob", "25"]]})
        assert resp.status_code == 200


class TestCreateSpreadsheet:
    def test_creates(self, client, mock_svc):
        mock_svc.create_spreadsheet.return_value = SAMPLE_SPREADSHEET
        resp = client.post("/api/sheets/spreadsheets", json={"title": "New Sheet"})
        assert resp.status_code == 200
        assert resp.json()["id"] == "abc123"

    def test_forwards_account(self, client, mock_svc):
        mock_svc.create_spreadsheet.return_value = SAMPLE_SPREADSHEET
        client.post("/api/sheets/spreadsheets?account=work", json={"title": "New"})
        mock_svc.create_spreadsheet.assert_called_once_with("New", None, account="work")


class TestExceptionMapping:
    def test_auth_error_returns_401(self, client, mock_svc):
        mock_svc.get_spreadsheet.side_effect = AuthenticationError("Not authenticated")
        resp = client.get("/api/sheets/spreadsheets/abc123")
        assert resp.status_code == 401

    def test_rate_limit_returns_429(self, client, mock_svc):
        mock_svc.read_range.side_effect = RateLimitError("Rate limited")
        resp = client.get("/api/sheets/spreadsheets/abc123/values?range=A1")
        assert resp.status_code == 429

    def test_integration_error_returns_500(self, client, mock_svc):
        mock_svc.get_spreadsheet.side_effect = IntegrationError("API failed")
        resp = client.get("/api/sheets/spreadsheets/abc123")
        assert resp.status_code == 500
