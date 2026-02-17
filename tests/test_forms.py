import pytest

from brokenclaw.models.forms import FormDetail, FormInfo, FormResponseInfo
from brokenclaw.services import forms as forms_service
from tests.conftest import requires_forms


def _delete_form(form_id: str):
    """Delete form via Drive API (Forms API can't delete)."""
    from brokenclaw.services.drive import _get_drive_service
    service = _get_drive_service()
    service.files().delete(fileId=form_id).execute()


@requires_forms
class TestCreateForm:
    def test_create_and_delete(self):
        created = forms_service.create_form(title="brokenclaw_test_form")
        try:
            assert isinstance(created, FormInfo)
            assert created.id
            assert created.title == "brokenclaw_test_form"
            assert "docs.google.com/forms" in created.url
        finally:
            _delete_form(created.id)


@requires_forms
class TestGetForm:
    def test_get_metadata(self):
        created = forms_service.create_form(title="brokenclaw_test_form_meta")
        try:
            info = forms_service.get_form(created.id)
            assert isinstance(info, FormInfo)
            assert info.id == created.id
            assert info.title == "brokenclaw_test_form_meta"
        finally:
            _delete_form(created.id)


@requires_forms
class TestFormQuestions:
    @pytest.fixture(autouse=True)
    def setup_form(self):
        self.form = forms_service.create_form(title="brokenclaw_test_questions")
        yield
        _delete_form(self.form.id)

    def test_add_text_question(self):
        detail = forms_service.add_question(
            self.form.id, title="What is your name?", question_type="TEXT",
        )
        assert isinstance(detail, FormDetail)
        assert len(detail.questions) == 1
        assert detail.questions[0].title == "What is your name?"
        assert detail.questions[0].question_type == "TEXT"

    def test_add_choice_question(self):
        detail = forms_service.add_question(
            self.form.id,
            title="Favorite color?",
            question_type="RADIO",
            options=["Red", "Blue", "Green"],
        )
        assert isinstance(detail, FormDetail)
        assert len(detail.questions) >= 1
        q = detail.questions[0]
        assert q.question_type == "RADIO"

    def test_get_detail(self):
        forms_service.add_question(self.form.id, title="Q1", question_type="TEXT")
        detail = forms_service.get_form_detail(self.form.id)
        assert isinstance(detail, FormDetail)
        assert detail.id == self.form.id
        assert len(detail.questions) == 1


@requires_forms
class TestFormResponses:
    @pytest.fixture(autouse=True)
    def setup_form(self):
        self.form = forms_service.create_form(title="brokenclaw_test_responses")
        yield
        _delete_form(self.form.id)

    def test_list_responses_empty(self):
        responses = forms_service.list_responses(self.form.id)
        assert isinstance(responses, list)
        assert len(responses) == 0
