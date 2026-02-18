from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_forms_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.forms import (
    FormDetail,
    FormInfo,
    FormQuestion,
    FormResponseAnswer,
    FormResponseInfo,
)

FORMS_DISCOVERY_URL = "https://forms.googleapis.com/$discovery/rest?version=v1"


def _get_forms_service(account: str = "default"):
    try:
        creds = get_forms_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Forms credentials: {e}. Visit /auth/forms/setup?account={account}."
        ) from e
    return build(
        "forms",
        "v1",
        credentials=creds,
        discoveryServiceUrl=FORMS_DISCOVERY_URL,
        static_discovery=False,
    )


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Forms API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Forms credentials expired or revoked. Visit /auth/forms/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Forms API error: {e}") from e


def _form_url(form_id: str) -> str:
    return f"https://docs.google.com/forms/d/{form_id}/edit"


def _extract_question_type(question: dict) -> str:
    """Determine the question type from the API response."""
    if "textQuestion" in question:
        if question["textQuestion"].get("paragraph", False):
            return "PARAGRAPH"
        return "TEXT"
    if "choiceQuestion" in question:
        return question["choiceQuestion"].get("type", "RADIO")
    if "scaleQuestion" in question:
        return "SCALE"
    if "dateQuestion" in question:
        return "DATE"
    if "timeQuestion" in question:
        return "TIME"
    if "fileUploadQuestion" in question:
        return "FILE_UPLOAD"
    return "UNKNOWN"


def _extract_questions(items: list[dict]) -> list[FormQuestion]:
    """Extract questions from form items."""
    questions = []
    for item in items:
        question_item = item.get("questionItem")
        question_group = item.get("questionGroupItem")
        if question_item:
            q = question_item.get("question", {})
            questions.append(FormQuestion(
                item_id=item.get("itemId", ""),
                title=item.get("title", ""),
                description=item.get("description"),
                question_type=_extract_question_type(q),
            ))
        elif question_group:
            for q in question_group.get("questions", []):
                questions.append(FormQuestion(
                    item_id=item.get("itemId", ""),
                    title=item.get("title", ""),
                    description=item.get("description"),
                    question_type=_extract_question_type(q),
                ))
    return questions


def get_form(form_id: str, account: str = "default") -> FormInfo:
    """Get form metadata: title, description, responder URI."""
    service = _get_forms_service(account)
    try:
        form = service.forms().get(formId=form_id).execute(num_retries=3)
        info = form.get("info", {})
        return FormInfo(
            id=form["formId"],
            title=info.get("title", ""),
            description=info.get("description"),
            responder_uri=form.get("responderUri"),
            url=_form_url(form["formId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def get_form_detail(form_id: str, account: str = "default") -> FormDetail:
    """Get form with all questions."""
    service = _get_forms_service(account)
    try:
        form = service.forms().get(formId=form_id).execute(num_retries=3)
        info = form.get("info", {})
        questions = _extract_questions(form.get("items", []))
        return FormDetail(
            id=form["formId"],
            title=info.get("title", ""),
            description=info.get("description"),
            questions=questions,
            responder_uri=form.get("responderUri"),
            url=_form_url(form["formId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def create_form(title: str, account: str = "default") -> FormInfo:
    """Create a new empty form."""
    service = _get_forms_service(account)
    try:
        form = service.forms().create(body={"info": {"title": title}}).execute(num_retries=3)
        info = form.get("info", {})
        return FormInfo(
            id=form["formId"],
            title=info.get("title", ""),
            description=info.get("description"),
            responder_uri=form.get("responderUri"),
            url=_form_url(form["formId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def _build_question_body(question_type: str, options: list[str] | None) -> dict:
    """Build the question body for the API based on type."""
    if question_type in ("TEXT", "PARAGRAPH"):
        return {"textQuestion": {"paragraph": question_type == "PARAGRAPH"}}
    if question_type in ("RADIO", "CHECKBOX", "DROP_DOWN"):
        choice_options = [{"value": opt} for opt in (options or [])]
        return {"choiceQuestion": {"type": question_type, "options": choice_options}}
    # Default to text
    return {"textQuestion": {"paragraph": False}}


def add_question(
    form_id: str,
    title: str,
    question_type: str = "TEXT",
    options: list[str] | None = None,
    required: bool = False,
    account: str = "default",
) -> FormDetail:
    """Add a question to a form. Returns updated form detail."""
    service = _get_forms_service(account)
    question_body = _build_question_body(question_type, options)
    question_body["required"] = required
    try:
        service.forms().batchUpdate(
            formId=form_id,
            body={
                "requests": [
                    {
                        "createItem": {
                            "item": {
                                "title": title,
                                "questionItem": {"question": question_body},
                            },
                            "location": {"index": 0},
                        }
                    }
                ]
            },
        ).execute(num_retries=3)
        return get_form_detail(form_id, account)
    except HttpError as e:
        _handle_api_error(e)


def list_responses(
    form_id: str,
    max_results: int = 100,
    account: str = "default",
) -> list[FormResponseInfo]:
    """List all responses for a form."""
    service = _get_forms_service(account)
    try:
        result = service.forms().responses().list(formId=form_id).execute(num_retries=3)
        responses = []
        for resp in result.get("responses", []):
            answers = []
            for qid, answer_data in resp.get("answers", {}).items():
                text_answers = None
                ta = answer_data.get("textAnswers")
                if ta:
                    text_answers = [a.get("value", "") for a in ta.get("answers", [])]
                answers.append(FormResponseAnswer(
                    question_id=qid,
                    text_answers=text_answers,
                ))
            responses.append(FormResponseInfo(
                response_id=resp.get("responseId", ""),
                create_time=resp.get("createTime"),
                last_submitted_time=resp.get("lastSubmittedTime"),
                answers=answers,
            ))
        return responses[:max_results]
    except HttpError as e:
        _handle_api_error(e)


def get_response(
    form_id: str,
    response_id: str,
    account: str = "default",
) -> FormResponseInfo:
    """Get a single form response by ID."""
    service = _get_forms_service(account)
    try:
        resp = service.forms().responses().get(
            formId=form_id, responseId=response_id,
        ).execute(num_retries=3)
        answers = []
        for qid, answer_data in resp.get("answers", {}).items():
            text_answers = None
            ta = answer_data.get("textAnswers")
            if ta:
                text_answers = [a.get("value", "") for a in ta.get("answers", [])]
            answers.append(FormResponseAnswer(
                question_id=qid,
                text_answers=text_answers,
            ))
        return FormResponseInfo(
            response_id=resp.get("responseId", ""),
            create_time=resp.get("createTime"),
            last_submitted_time=resp.get("lastSubmittedTime"),
            answers=answers,
        )
    except HttpError as e:
        _handle_api_error(e)
