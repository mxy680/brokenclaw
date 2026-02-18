from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_slides_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.slides import PresentationContent, PresentationInfo


def _get_slides_service(account: str = "default"):
    try:
        creds = get_slides_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Slides credentials: {e}. Visit /auth/slides/setup?account={account}."
        ) from e
    return build("slides", "v1", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Slides API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Slides credentials expired or revoked. Visit /auth/slides/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Slides API error: {e}") from e


def _extract_slides_text(slides: list[dict]) -> list[str]:
    """Extract plain text from each slide's page elements."""
    result = []
    for slide in slides:
        parts = []
        for element in slide.get("pageElements", []):
            shape = element.get("shape")
            if not shape:
                continue
            text_content = shape.get("text")
            if not text_content:
                continue
            for text_element in text_content.get("textElements", []):
                text_run = text_element.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))
        result.append("".join(parts))
    return result


def _presentation_url(presentation_id: str) -> str:
    return f"https://docs.google.com/presentation/d/{presentation_id}/edit"


def get_presentation(presentation_id: str, account: str = "default") -> PresentationInfo:
    """Get presentation metadata: title, ID, slide count, URL."""
    service = _get_slides_service(account)
    try:
        pres = service.presentations().get(presentationId=presentation_id).execute(num_retries=3)
        return PresentationInfo(
            id=pres["presentationId"],
            title=pres.get("title", ""),
            slides_count=len(pres.get("slides", [])),
            url=_presentation_url(pres["presentationId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def get_presentation_content(presentation_id: str, account: str = "default") -> PresentationContent:
    """Get presentation with full text extracted from each slide."""
    service = _get_slides_service(account)
    try:
        pres = service.presentations().get(presentationId=presentation_id).execute(num_retries=3)
        slides = pres.get("slides", [])
        slides_text = _extract_slides_text(slides)
        return PresentationContent(
            id=pres["presentationId"],
            title=pres.get("title", ""),
            slides_count=len(slides),
            slides_text=slides_text,
            url=_presentation_url(pres["presentationId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def create_presentation(title: str, account: str = "default") -> PresentationInfo:
    """Create a new empty presentation."""
    service = _get_slides_service(account)
    try:
        pres = service.presentations().create(body={"title": title}).execute(num_retries=3)
        return PresentationInfo(
            id=pres["presentationId"],
            title=pres.get("title", ""),
            slides_count=len(pres.get("slides", [])),
            url=_presentation_url(pres["presentationId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def add_slide(
    presentation_id: str,
    layout: str = "BLANK",
    account: str = "default",
) -> PresentationInfo:
    """Add a new slide with the given predefined layout."""
    service = _get_slides_service(account)
    try:
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={
                "requests": [
                    {
                        "createSlide": {
                            "slideLayoutReference": {"predefinedLayout": layout},
                        }
                    }
                ]
            },
        ).execute(num_retries=3)
        return get_presentation(presentation_id, account)
    except HttpError as e:
        _handle_api_error(e)


def replace_text(
    presentation_id: str,
    find: str,
    replace_with: str,
    match_case: bool = True,
    account: str = "default",
) -> PresentationInfo:
    """Find and replace text across all slides."""
    service = _get_slides_service(account)
    try:
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={
                "requests": [
                    {
                        "replaceAllText": {
                            "containsText": {
                                "text": find,
                                "matchCase": match_case,
                            },
                            "replaceText": replace_with,
                        }
                    }
                ]
            },
        ).execute(num_retries=3)
        return get_presentation(presentation_id, account)
    except HttpError as e:
        _handle_api_error(e)
