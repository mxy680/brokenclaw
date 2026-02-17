import pytest

from brokenclaw.models.docs import DocContent, DocInfo
from brokenclaw.services import docs as docs_service
from tests.conftest import requires_docs


def _delete_document(document_id: str):
    """Delete document via Drive API (Docs API can't delete)."""
    from brokenclaw.services.drive import _get_drive_service
    service = _get_drive_service()
    service.files().delete(fileId=document_id).execute()


@requires_docs
class TestCreateDocument:
    def test_create_and_delete(self):
        created = docs_service.create_document(title="brokenclaw_test_doc")
        try:
            assert isinstance(created, DocInfo)
            assert created.id
            assert created.title == "brokenclaw_test_doc"
            assert "docs.google.com" in created.url
        finally:
            _delete_document(created.id)


@requires_docs
class TestGetDocument:
    def test_get_metadata(self):
        created = docs_service.create_document(title="brokenclaw_test_meta_doc")
        try:
            info = docs_service.get_document(created.id)
            assert isinstance(info, DocInfo)
            assert info.id == created.id
            assert info.title == "brokenclaw_test_meta_doc"
        finally:
            _delete_document(created.id)


@requires_docs
class TestInsertAndRead:
    """Create a doc, insert text, read it back, then clean up."""

    @pytest.fixture(autouse=True)
    def setup_document(self):
        self.doc = docs_service.create_document(title="brokenclaw_test_insert")
        yield
        _delete_document(self.doc.id)

    def test_insert_and_read(self):
        docs_service.insert_text(self.doc.id, "Hello, world!")
        content = docs_service.get_document_content(self.doc.id)
        assert isinstance(content, DocContent)
        assert "Hello, world!" in content.body_text


@requires_docs
class TestReplaceText:
    """Create a doc, insert text, replace text, verify."""

    @pytest.fixture(autouse=True)
    def setup_document(self):
        self.doc = docs_service.create_document(title="brokenclaw_test_replace")
        yield
        _delete_document(self.doc.id)

    def test_replace(self):
        docs_service.insert_text(self.doc.id, "Hello, world!")
        docs_service.replace_text(self.doc.id, "world", "docs")
        content = docs_service.get_document_content(self.doc.id)
        assert "Hello, docs!" in content.body_text
        assert "world" not in content.body_text
