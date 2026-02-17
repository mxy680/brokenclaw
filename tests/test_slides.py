import pytest

from brokenclaw.models.slides import PresentationContent, PresentationInfo
from brokenclaw.services import slides as slides_service
from tests.conftest import requires_slides


def _delete_presentation(presentation_id: str):
    """Delete presentation via Drive API (Slides API can't delete)."""
    from brokenclaw.services.drive import _get_drive_service
    service = _get_drive_service()
    service.files().delete(fileId=presentation_id).execute()


@requires_slides
class TestCreatePresentation:
    def test_create_and_delete(self):
        created = slides_service.create_presentation(title="brokenclaw_test_slides")
        try:
            assert isinstance(created, PresentationInfo)
            assert created.id
            assert created.title == "brokenclaw_test_slides"
            assert "docs.google.com/presentation" in created.url
            assert created.slides_count >= 0
        finally:
            _delete_presentation(created.id)


@requires_slides
class TestGetPresentation:
    def test_get_metadata(self):
        created = slides_service.create_presentation(title="brokenclaw_test_slides_meta")
        try:
            info = slides_service.get_presentation(created.id)
            assert isinstance(info, PresentationInfo)
            assert info.id == created.id
            assert info.title == "brokenclaw_test_slides_meta"
        finally:
            _delete_presentation(created.id)


@requires_slides
class TestGetContent:
    def test_get_content_empty(self):
        created = slides_service.create_presentation(title="brokenclaw_test_slides_content")
        try:
            content = slides_service.get_presentation_content(created.id)
            assert isinstance(content, PresentationContent)
            assert content.id == created.id
            assert isinstance(content.slides_text, list)
            assert content.slides_count == len(content.slides_text)
        finally:
            _delete_presentation(created.id)


@requires_slides
class TestAddSlide:
    @pytest.fixture(autouse=True)
    def setup_presentation(self):
        self.pres = slides_service.create_presentation(title="brokenclaw_test_add_slide")
        yield
        _delete_presentation(self.pres.id)

    def test_add_slide(self):
        original_count = self.pres.slides_count
        updated = slides_service.add_slide(self.pres.id)
        assert updated.slides_count == original_count + 1


@requires_slides
class TestReplaceText:
    @pytest.fixture(autouse=True)
    def setup_presentation(self):
        self.pres = slides_service.create_presentation(title="brokenclaw_test_replace")
        yield
        _delete_presentation(self.pres.id)

    def test_replace(self):
        # Replace text returns updated info without error even if no matches
        result = slides_service.replace_text(self.pres.id, "placeholder", "replaced")
        assert isinstance(result, PresentationInfo)
        assert result.id == self.pres.id
