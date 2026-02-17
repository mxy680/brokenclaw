import pytest
from unittest.mock import MagicMock

from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.sheets import ReadRangeResponse, SpreadsheetInfo, WriteRangeResponse

SAMPLE_SPREADSHEET = SpreadsheetInfo(
    id="abc123", title="My Sheet", sheets=["Sheet1"],
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


@pytest.fixture(autouse=True)
def mock_svc(mocker):
    return mocker.patch("brokenclaw.mcp_server.sheets_service")


@pytest.fixture(autouse=True)
def mock_store(mocker):
    store = MagicMock()
    store.list_accounts.return_value = ["default"]
    mocker.patch("brokenclaw.mcp_server._get_token_store", return_value=store)
    return store


class TestSheetsGetSpreadsheet:
    def test_returns_dict(self, mock_svc):
        mock_svc.get_spreadsheet.return_value = SAMPLE_SPREADSHEET
        from brokenclaw.mcp_server import sheets_get_spreadsheet
        result = sheets_get_spreadsheet.fn(spreadsheet_id="abc123")
        assert isinstance(result, dict)
        assert result["id"] == "abc123"
        assert result["sheets"] == ["Sheet1"]

    def test_error_returns_dict(self, mock_svc):
        mock_svc.get_spreadsheet.side_effect = AuthenticationError("Not auth")
        from brokenclaw.mcp_server import sheets_get_spreadsheet
        result = sheets_get_spreadsheet.fn(spreadsheet_id="abc123")
        assert result["error"] == "auth_error"

    def test_forwards_account(self, mock_svc):
        mock_svc.get_spreadsheet.return_value = SAMPLE_SPREADSHEET
        from brokenclaw.mcp_server import sheets_get_spreadsheet
        sheets_get_spreadsheet.fn(spreadsheet_id="abc123", account="school")
        mock_svc.get_spreadsheet.assert_called_once_with("abc123", account="school")


class TestSheetsReadRange:
    def test_returns_dict(self, mock_svc):
        mock_svc.read_range.return_value = SAMPLE_READ
        from brokenclaw.mcp_server import sheets_read_range
        result = sheets_read_range.fn(spreadsheet_id="abc123", range="Sheet1!A1:B2")
        assert isinstance(result, dict)
        assert result["values"] == [["Name", "Age"], ["Alice", "30"]]

    def test_error_returns_dict(self, mock_svc):
        mock_svc.read_range.side_effect = RateLimitError("Slow down")
        from brokenclaw.mcp_server import sheets_read_range
        result = sheets_read_range.fn(spreadsheet_id="abc123", range="A1")
        assert result["error"] == "rate_limit"


class TestSheetsWriteRange:
    def test_returns_dict(self, mock_svc):
        mock_svc.write_range.return_value = SAMPLE_WRITE
        from brokenclaw.mcp_server import sheets_write_range
        result = sheets_write_range.fn(spreadsheet_id="abc123", range="A1:B2", values=[["X", "Y"]])
        assert isinstance(result, dict)
        assert result["updated_cells"] == 4

    def test_error_returns_dict(self, mock_svc):
        mock_svc.write_range.side_effect = IntegrationError("API error")
        from brokenclaw.mcp_server import sheets_write_range
        result = sheets_write_range.fn(spreadsheet_id="abc123", range="A1", values=[["X"]])
        assert result["error"] == "integration_error"


class TestSheetsAppendRows:
    def test_returns_dict(self, mock_svc):
        mock_svc.append_rows.return_value = SAMPLE_WRITE
        from brokenclaw.mcp_server import sheets_append_rows
        result = sheets_append_rows.fn(spreadsheet_id="abc123", range="Sheet1!A:B", values=[["Bob", "25"]])
        assert isinstance(result, dict)


class TestSheetsCreateSpreadsheet:
    def test_returns_dict(self, mock_svc):
        mock_svc.create_spreadsheet.return_value = SAMPLE_SPREADSHEET
        from brokenclaw.mcp_server import sheets_create_spreadsheet
        result = sheets_create_spreadsheet.fn(title="New Sheet")
        assert isinstance(result, dict)
        assert result["id"] == "abc123"

    def test_error_returns_dict(self, mock_svc):
        mock_svc.create_spreadsheet.side_effect = AuthenticationError("Not auth")
        from brokenclaw.mcp_server import sheets_create_spreadsheet
        result = sheets_create_spreadsheet.fn(title="New Sheet")
        assert result["error"] == "auth_error"
