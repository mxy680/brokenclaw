import pytest

from brokenclaw.models.drive import DriveFile, FileContentResponse
from brokenclaw.services import drive as drive_service
from brokenclaw.services.drive import _get_drive_service
from tests.conftest import requires_drive


def _delete_file(file_id: str):
    """Permanently delete a file to clean up after tests."""
    service = _get_drive_service()
    service.files().delete(fileId=file_id).execute()


@requires_drive
class TestListFiles:
    def test_returns_list_of_files(self):
        files = drive_service.list_files(max_results=3)
        assert isinstance(files, list)
        assert len(files) <= 3
        if files:
            f = files[0]
            assert isinstance(f, DriveFile)
            assert f.id
            assert f.name

    def test_respects_max_results(self):
        files = drive_service.list_files(max_results=1)
        assert len(files) <= 1


@requires_drive
class TestSearchFiles:
    def test_search_returns_results(self):
        # Search broadly — should find something
        files = drive_service.search_files("trashed = false", max_results=2)
        assert isinstance(files, list)

    def test_search_with_no_matches(self):
        files = drive_service.search_files("name = 'zzznonexistent_brokenclaw_test_9999'", max_results=5)
        assert files == []


@requires_drive
class TestCreateAndReadFile:
    def test_create_read_delete_file(self):
        # Create
        created = drive_service.create_file(
            name="brokenclaw_test_file.txt",
            content="Hello from brokenclaw tests!",
            mime_type="text/plain",
        )
        assert isinstance(created, DriveFile)
        assert created.id
        assert created.name == "brokenclaw_test_file.txt"

        try:
            # Get metadata
            meta = drive_service.get_file(created.id)
            assert meta.id == created.id
            assert meta.mime_type == "text/plain"

            # Read content
            content = drive_service.get_file_content(created.id)
            assert isinstance(content, FileContentResponse)
            assert content.content == "Hello from brokenclaw tests!"
        finally:
            _delete_file(created.id)


@requires_drive
class TestCreateFolder:
    def test_create_and_delete_folder(self):
        folder = drive_service.create_folder(name="brokenclaw_test_folder")
        assert isinstance(folder, DriveFile)
        assert folder.mime_type == "application/vnd.google-apps.folder"
        _delete_file(folder.id)
