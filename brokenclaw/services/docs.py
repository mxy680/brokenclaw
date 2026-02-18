from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from brokenclaw.auth import get_docs_credentials
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.docs import DocContent, DocInfo


def _get_docs_service(account: str = "default"):
    try:
        creds = get_docs_credentials(account)
    except FileNotFoundError as e:
        raise AuthenticationError(str(e)) from e
    except Exception as e:
        raise AuthenticationError(
            f"Failed to obtain Docs credentials: {e}. Visit /auth/docs/setup?account={account}."
        ) from e
    return build("docs", "v1", credentials=creds)


def _handle_api_error(e: HttpError):
    if e.resp.status == 429:
        raise RateLimitError("Docs API rate limit exceeded. Try again shortly.") from e
    if e.resp.status in (401, 403):
        raise AuthenticationError(
            "Docs credentials expired or revoked. Visit /auth/docs/setup to re-authenticate."
        ) from e
    raise IntegrationError(f"Docs API error: {e}") from e


def _extract_body_text(body: dict) -> str:
    """Extract plain text from a Google Docs document body."""
    parts = []
    for element in body.get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for pe in paragraph.get("elements", []):
            text_run = pe.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return "".join(parts)


def _doc_url(document_id: str) -> str:
    return f"https://docs.google.com/document/d/{document_id}/edit"


def get_document(document_id: str, account: str = "default") -> DocInfo:
    """Get document metadata: title, ID, URL."""
    service = _get_docs_service(account)
    try:
        doc = service.documents().get(documentId=document_id).execute(num_retries=3)
        return DocInfo(
            id=doc["documentId"],
            title=doc["title"],
            url=_doc_url(doc["documentId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def get_document_content(document_id: str, account: str = "default") -> DocContent:
    """Get document with full text content."""
    service = _get_docs_service(account)
    try:
        doc = service.documents().get(documentId=document_id).execute(num_retries=3)
        body_text = _extract_body_text(doc.get("body", {}))
        return DocContent(
            id=doc["documentId"],
            title=doc["title"],
            body_text=body_text,
            url=_doc_url(doc["documentId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def create_document(title: str, account: str = "default") -> DocInfo:
    """Create a new empty document."""
    service = _get_docs_service(account)
    try:
        doc = service.documents().create(body={"title": title}).execute(num_retries=3)
        return DocInfo(
            id=doc["documentId"],
            title=doc["title"],
            url=_doc_url(doc["documentId"]),
        )
    except HttpError as e:
        _handle_api_error(e)


def insert_text(document_id: str, text: str, index: int = 1, account: str = "default") -> DocInfo:
    """Insert text at the given index (default 1 = start of body)."""
    service = _get_docs_service(account)
    try:
        service.documents().batchUpdate(
            documentId=document_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": index},
                            "text": text,
                        }
                    }
                ]
            },
        ).execute(num_retries=3)
        return get_document(document_id, account)
    except HttpError as e:
        _handle_api_error(e)


def replace_text(
    document_id: str,
    find: str,
    replace_with: str,
    match_case: bool = True,
    account: str = "default",
) -> DocInfo:
    """Find and replace text in the document."""
    service = _get_docs_service(account)
    try:
        service.documents().batchUpdate(
            documentId=document_id,
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
        return get_document(document_id, account)
    except HttpError as e:
        _handle_api_error(e)
