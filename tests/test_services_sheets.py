import pytest
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.sheets import ReadRangeResponse, SpreadsheetInfo, WriteRangeResponse
from brokenclaw.services import sheets as sheets_service

SPREADSHEET_API_RESPONSE = {
    "spreadsheetId": "abc123",
    "properties": {"title": "My Sheet"},
    "sheets": [
        {"properties": {"title": "Sheet1"}},
        {"properties": {"title": "Sheet2"}},
    ],
    "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/abc123/edit",
}

VALUES_API_RESPONSE = {
    "range": "Sheet1!A1:B2",
    "values": [["Name", "Age"], ["Alice", "30"]],
}

UPDATE_API_RESPONSE = {
    "updatedRange": "Sheet1!A1:B2",
    "updatedRows": 2,
    "updatedColumns": 2,
    "updatedCells": 4,
}

APPEND_API_RESPONSE = {
    "updates": {
        "updatedRange": "Sheet1!A3:B3",
        "updatedRows": 1,
        "updatedColumns": 2,
        "updatedCells": 2,
    }
}


@pytest.fixture
def mock_sheets_credentials(mocker):
    return mocker.patch("brokenclaw.services.sheets.get_sheets_credentials", return_value=MagicMock())


@pytest.fixture
def mock_sheets_build(mocker):
    mock_svc = MagicMock()
    mocker.patch("brokenclaw.services.sheets.build", return_value=mock_svc)
    return mock_svc


@pytest.fixture
def mock_sheets_service(mock_sheets_credentials, mock_sheets_build):
    return mock_sheets_build


class TestGetSpreadsheet:
    def test_returns_spreadsheet_info(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().get().execute.return_value = SPREADSHEET_API_RESPONSE
        result = sheets_service.get_spreadsheet("abc123")
        assert isinstance(result, SpreadsheetInfo)
        assert result.id == "abc123"
        assert result.title == "My Sheet"
        assert result.sheets == ["Sheet1", "Sheet2"]

    def test_forwards_account(self, mock_sheets_credentials, mock_sheets_build):
        mock_sheets_build.spreadsheets().get().execute.return_value = SPREADSHEET_API_RESPONSE
        sheets_service.get_spreadsheet("abc123", account="work")
        mock_sheets_credentials.assert_called_with("work")


class TestReadRange:
    def test_returns_values(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().values().get().execute.return_value = VALUES_API_RESPONSE
        result = sheets_service.read_range("abc123", "Sheet1!A1:B2")
        assert isinstance(result, ReadRangeResponse)
        assert result.values == [["Name", "Age"], ["Alice", "30"]]

    def test_empty_range(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().values().get().execute.return_value = {"range": "Sheet1!A1:A1"}
        result = sheets_service.read_range("abc123", "Sheet1!A1:A1")
        assert result.values == []


class TestWriteRange:
    def test_writes_values(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().values().update().execute.return_value = UPDATE_API_RESPONSE
        result = sheets_service.write_range("abc123", "Sheet1!A1:B2", [["X", "Y"]])
        assert isinstance(result, WriteRangeResponse)
        assert result.updated_cells == 4


class TestAppendRows:
    def test_appends_rows(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().values().append().execute.return_value = APPEND_API_RESPONSE
        result = sheets_service.append_rows("abc123", "Sheet1!A:B", [["Bob", "25"]])
        assert isinstance(result, WriteRangeResponse)
        assert result.updated_rows == 1


class TestCreateSpreadsheet:
    def test_creates_spreadsheet(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().create().execute.return_value = SPREADSHEET_API_RESPONSE
        result = sheets_service.create_spreadsheet("My Sheet")
        assert isinstance(result, SpreadsheetInfo)
        assert result.id == "abc123"

    def test_creates_with_sheet_names(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().create().execute.return_value = SPREADSHEET_API_RESPONSE
        result = sheets_service.create_spreadsheet("My Sheet", sheet_names=["Data", "Summary"])
        assert isinstance(result, SpreadsheetInfo)


class TestErrorHandling:
    def _make_http_error(self, status):
        resp = MagicMock()
        resp.status = status
        return HttpError(resp=resp, content=b"error")

    def test_401_raises_auth_error(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().get().execute.side_effect = self._make_http_error(401)
        with pytest.raises(AuthenticationError):
            sheets_service.get_spreadsheet("abc123")

    def test_429_raises_rate_limit(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().values().get().execute.side_effect = self._make_http_error(429)
        with pytest.raises(RateLimitError):
            sheets_service.read_range("abc123", "A1:B2")

    def test_500_raises_integration_error(self, mock_sheets_service):
        mock_sheets_service.spreadsheets().get().execute.side_effect = self._make_http_error(500)
        with pytest.raises(IntegrationError):
            sheets_service.get_spreadsheet("abc123")

    def test_missing_credentials_raises_auth_error(self, mocker):
        mocker.patch("brokenclaw.services.sheets.get_sheets_credentials", side_effect=RuntimeError("Not authenticated"))
        with pytest.raises(AuthenticationError):
            sheets_service.get_spreadsheet("abc123")
