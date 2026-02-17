import pytest

from brokenclaw.models.sheets import ReadRangeResponse, SpreadsheetInfo, WriteRangeResponse
from brokenclaw.services import sheets as sheets_service
from brokenclaw.services.sheets import _get_sheets_service
from tests.conftest import requires_sheets


def _delete_spreadsheet(spreadsheet_id: str):
    """Delete spreadsheet via Drive API (Sheets API can't delete)."""
    from brokenclaw.services.drive import _get_drive_service
    service = _get_drive_service()
    service.files().delete(fileId=spreadsheet_id).execute()


@requires_sheets
class TestCreateSpreadsheet:
    def test_create_and_delete(self):
        created = sheets_service.create_spreadsheet(
            title="brokenclaw_test_spreadsheet",
            sheet_names=["Data", "Summary"],
        )
        assert isinstance(created, SpreadsheetInfo)
        assert created.id
        assert created.title == "brokenclaw_test_spreadsheet"
        assert "Data" in created.sheets
        assert "Summary" in created.sheets
        _delete_spreadsheet(created.id)


@requires_sheets
class TestReadWriteAppend:
    """Create a spreadsheet, write/read/append, then clean up."""

    @pytest.fixture(autouse=True)
    def setup_spreadsheet(self):
        self.spreadsheet = sheets_service.create_spreadsheet(
            title="brokenclaw_test_rw",
            sheet_names=["TestSheet"],
        )
        yield
        _delete_spreadsheet(self.spreadsheet.id)

    def test_write_and_read(self):
        sid = self.spreadsheet.id

        # Write
        write_result = sheets_service.write_range(
            sid, "TestSheet!A1:B2",
            values=[["Name", "Age"], ["Alice", "30"]],
        )
        assert isinstance(write_result, WriteRangeResponse)
        assert write_result.updated_cells == 4

        # Read back
        read_result = sheets_service.read_range(sid, "TestSheet!A1:B2")
        assert isinstance(read_result, ReadRangeResponse)
        assert read_result.values == [["Name", "Age"], ["Alice", "30"]]

    def test_append_rows(self):
        sid = self.spreadsheet.id

        # Write initial data
        sheets_service.write_range(sid, "TestSheet!A1:B1", values=[["Name", "Age"]])

        # Append
        append_result = sheets_service.append_rows(
            sid, "TestSheet!A:B",
            values=[["Bob", "25"], ["Charlie", "35"]],
        )
        assert isinstance(append_result, WriteRangeResponse)
        assert append_result.updated_rows == 2

        # Read all
        read_result = sheets_service.read_range(sid, "TestSheet!A1:B3")
        assert len(read_result.values) == 3


@requires_sheets
class TestGetSpreadsheet:
    def test_get_metadata(self):
        created = sheets_service.create_spreadsheet(title="brokenclaw_test_meta")
        try:
            info = sheets_service.get_spreadsheet(created.id)
            assert isinstance(info, SpreadsheetInfo)
            assert info.id == created.id
            assert info.title == "brokenclaw_test_meta"
            assert len(info.sheets) >= 1
        finally:
            _delete_spreadsheet(created.id)
